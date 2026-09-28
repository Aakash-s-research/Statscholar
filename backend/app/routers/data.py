import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models.schemas import DatasetSummary
from app.routers.auth import require_verified_user
from app.services import data_service

router = APIRouter(prefix="/data", tags=["Data Preparation"])


@router.post("/upload", response_model=DatasetSummary)
async def upload_dataset(file: UploadFile = File(...), current_user: dict = Depends(require_verified_user)):
    if not file.filename.lower().endswith((".csv", ".xlsx", ".tsv")):
        raise HTTPException(400, "Unsupported file type. Upload CSV, TSV, or XLSX.")

    if file.filename.lower().endswith(".csv"):
        df = pd.read_csv(file.file)
    elif file.filename.lower().endswith(".tsv"):
        df = pd.read_csv(file.file, sep="\t")
    else:
        df = pd.read_excel(file.file)

    dataset_id = data_service.store_dataset(df, filename=file.filename, owner_id=current_user["id"])
    return data_service.summarize(dataset_id, df)


@router.get("/{dataset_id}", response_model=DatasetSummary)
async def get_dataset_summary(dataset_id: str, current_user: dict = Depends(require_verified_user)):
    try:
        df = data_service.get_dataset(dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")
    return data_service.summarize(dataset_id, df)


@router.get("/{dataset_id}/series")
async def get_series(dataset_id: str, columns: str, current_user: dict = Depends(require_verified_user)):
    """
    Raw column values for charting — the summary endpoint only returns a
    6-row preview, which isn't enough to plot. `columns` is a comma-separated
    list (e.g. "year,discharge_m3s"). Rows with a missing value in ANY
    requested column are dropped so the returned arrays stay aligned —
    the same pairwise-complete-case approach the stats endpoints use.
    """
    try:
        df = data_service.get_dataset(dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")

    col_list = [c.strip() for c in columns.split(",") if c.strip()]
    missing = [c for c in col_list if c not in df.columns]
    if missing:
        raise HTTPException(400, f"Columns not found: {missing}")

    # De-duplicate while preserving order — selecting the same column twice
    # (e.g. a chart asking for [timeColumn, variable] when a user picks the
    # same column for both) otherwise makes df[col_list] return a DataFrame
    # with two identically-named columns, and .tolist() on that breaks.
    unique_cols = list(dict.fromkeys(col_list))
    subset = df[unique_cols].dropna()
    values = {c: subset[c].tolist() for c in unique_cols}
    return {c: values[c] for c in col_list}  # echo back in the originally requested shape/order
