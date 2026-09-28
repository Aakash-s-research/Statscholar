"""
Data Preparation — upload handling, variable-type detection, quality scoring.

Datasets are cached in memory for speed, and persisted to the database
(their CSV content stored as a text column — see core/db.py) so an
uploaded dataset survives a backend restart AND works on hosting
platforms with an ephemeral filesystem, where local disk files would be
wiped on every redeploy. Each dataset is tagged with the id of the user
who uploaded it (`owner_id`), and `get_dataset` enforces that only the
owner can retrieve it — this is what makes per-user accounts actually
mean something, rather than everyone still sharing one data pool behind
a login screen.
"""
import io
import time
import uuid

import pandas as pd
from sqlalchemy import insert, select

from app.core.db import datasets_table, engine

_DATASETS: dict[str, pd.DataFrame] = {}
_META: dict[str, dict] = {}  # dataset_id -> {"filename": str, "owner_id": int}


class NotOwnedError(Exception):
    """Raised when a dataset exists but doesn't belong to the requesting user."""


def store_dataset(df: pd.DataFrame, filename: str, owner_id: int) -> str:
    dataset_id = str(uuid.uuid4())
    meta = {"filename": filename, "owner_id": owner_id}
    _DATASETS[dataset_id] = df
    _META[dataset_id] = meta

    csv_content = df.to_csv(index=False)
    with engine.begin() as conn:
        conn.execute(
            insert(datasets_table).values(
                id=dataset_id, owner_id=owner_id, filename=filename,
                csv_content=csv_content, created_at=time.time(),
            )
        )

    return dataset_id


def _load_meta(dataset_id: str) -> dict:
    if dataset_id in _META:
        return _META[dataset_id]
    with engine.connect() as conn:
        row = conn.execute(
            select(datasets_table.c.filename, datasets_table.c.owner_id)
            .where(datasets_table.c.id == dataset_id)
        ).fetchone()
    if row is None:
        return {}
    meta = {"filename": row[0], "owner_id": row[1]}
    _META[dataset_id] = meta
    return meta


def get_dataset(dataset_id: str, owner_id: int) -> pd.DataFrame:
    """Returns the dataset only if it exists AND belongs to owner_id.
    Raises KeyError if it doesn't exist at all, NotOwnedError if it exists
    but belongs to someone else — callers map these to 404 and 403."""
    meta = _load_meta(dataset_id)
    if not meta:
        raise KeyError(f"No dataset found for id {dataset_id}")
    if meta.get("owner_id") != owner_id:
        raise NotOwnedError(f"Dataset {dataset_id} does not belong to this user")

    if dataset_id in _DATASETS:
        return _DATASETS[dataset_id]

    with engine.connect() as conn:
        row = conn.execute(
            select(datasets_table.c.csv_content).where(datasets_table.c.id == dataset_id)
        ).fetchone()
    df = pd.read_csv(io.StringIO(row[0]))
    _DATASETS[dataset_id] = df
    return df


def get_filename(dataset_id: str) -> str:
    return _load_meta(dataset_id).get("filename", "dataset.csv")


def detect_type(series: pd.Series) -> str:
    if pd.api.types.is_numeric_dtype(series):
        # heuristic: few unique small integers -> likely ordinal, otherwise ratio/interval
        if series.nunique() <= 10 and (series.dropna() % 1 == 0).all():
            return "ordinal"
        return "ratio"
    return "nominal"


def summarize(dataset_id: str, df: pd.DataFrame) -> dict:
    columns = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        columns.append({
            "name": col,
            "detected_type": detect_type(df[col]),
            "missing_count": missing,
            "missing_pct": round(missing / len(df) * 100, 2),
        })

    total_missing_pct = sum(c["missing_pct"] for c in columns) / max(len(columns), 1)
    quality_score = max(0, round(100 - total_missing_pct * 2))

    return {
        "dataset_id": dataset_id,
        "filename": get_filename(dataset_id),
        "row_count": len(df),
        "columns": columns,
        "quality_score": quality_score,
        "preview": df.head(6).to_dict(orient="records"),
    }
