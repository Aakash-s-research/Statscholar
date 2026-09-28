"""
Visualization — chart-type recommendation.

Inspects the dataset's actual detected column types and returns a ranked
list of chart suggestions, rather than a hardcoded/static list. Kept
deliberately simple (rule-based on column type combinations) — matches
the same "explainable over clever" philosophy as the interpretation engine.
"""
import numpy as np
import pandas as pd

from app.services import data_service


_ID_LIKE_PATTERNS = ("system:index", "unnamed:", "index", " id", "_id", "id_")


def _looks_like_identifier(name: str) -> bool:
    """
    Columns like 'system:index' (common in Google Earth Engine exports),
    pandas' 'Unnamed: 0', or a plain row id are row identifiers, not
    analysis variables — they should never be charted as a measurement,
    and shouldn't win the "time axis" slot just because they happen to be
    sequential.
    """
    name_lower = name.lower().strip()
    return name_lower == "id" or any(p in name_lower for p in _ID_LIKE_PATTERNS)


def _name_suggests_time(name: str) -> bool:
    name_lower = name.lower()
    return any(key in name_lower for key in ("year", "date", "time", "month", "day"))


def _is_monotonic_numeric(series: pd.Series) -> bool:
    if not pd.api.types.is_numeric_dtype(series):
        return False
    values = series.dropna().to_numpy()
    return len(values) > 1 and bool(np.all(np.diff(values) >= 0))


def _pick_time_column(numeric_cols: list[str], df: pd.DataFrame) -> str | None:
    """
    Two-pass selection so a column named 'Year' always wins over an
    incidentally-sequential ID column, regardless of which appears first
    in the file: first look for any column whose *name* suggests time,
    across all columns; only fall back to "just happens to be
    monotonically increasing" if no named candidate exists at all.
    """
    named_match = next((c for c in numeric_cols if _name_suggests_time(c)), None)
    if named_match:
        return named_match
    return next((c for c in numeric_cols if _is_monotonic_numeric(df[c])), None)


def recommend_charts(dataset_id: str, owner_id: int) -> list[dict]:
    df = data_service.get_dataset(dataset_id, owner_id=owner_id)
    summary = data_service.summarize(dataset_id, df)
    columns = summary["columns"]

    all_numeric = [c["name"] for c in columns if c["detected_type"] in ("ratio", "interval", "ordinal")]
    nominal_cols = [c["name"] for c in columns if c["detected_type"] == "nominal" and not _looks_like_identifier(c["name"])]

    # Drop identifier-like columns entirely before any other logic runs —
    # they're metadata, not something worth charting or using as a time axis.
    numeric_cols = [c for c in all_numeric if not _looks_like_identifier(c)]
    time_col = _pick_time_column(numeric_cols, df)

    # Low-cardinality numeric columns (e.g. a quarter/month/group index coded
    # as 0-3 or 1-12) read as grouping labels, not as a measured outcome —
    # treat them like nominal columns for charting purposes rather than as
    # a line/scatter/heatmap target.
    n_rows = len(df)
    measurement_cols, group_like_cols = [], []
    for c in numeric_cols:
        if c == time_col:
            continue
        nunique = df[c].nunique()
        if nunique <= 12 and nunique < n_rows / 3:
            group_like_cols.append(c)
        else:
            measurement_cols.append(c)

    recommendations = []

    # Time series line chart — needs a time-like column plus at least one other numeric column
    if time_col:
        for col in measurement_cols:
            recommendations.append({
                "name": f"{col} over {time_col}",
                "chart_type": "line",
                "columns": [time_col, col],
                "score": "recommended",
                "why": f"'{time_col}' looks like an ordered time index — a line chart shows how '{col}' changes across it.",
            })

    # Scatter plots for numeric pairs, ranked by absolute correlation
    pair_scores = []
    for i in range(len(measurement_cols)):
        for j in range(i + 1, len(measurement_cols)):
            a, b = measurement_cols[i], measurement_cols[j]
            paired = df[[a, b]].dropna()
            if len(paired) < 3:
                continue
            r = float(paired[a].corr(paired[b]))
            pair_scores.append((abs(r), a, b, r))
    pair_scores.sort(reverse=True)
    for rank, (abs_r, a, b, r) in enumerate(pair_scores[:3]):
        recommendations.append({
            "name": f"{a} vs {b}",
            "chart_type": "scatter",
            "columns": [a, b],
            "score": "recommended" if rank == 0 else "suggested",
            "why": f"Correlation of {r:.2f} between '{a}' and '{b}' — {'a fairly strong' if abs_r > 0.4 else 'a visible'} relationship worth visualizing.",
        })

    # Correlation heatmap once there are enough numeric columns to make a table unwieldy
    if len(measurement_cols) >= 3:
        recommendations.append({
            "name": "Correlation heatmap",
            "chart_type": "heatmap",
            "columns": measurement_cols,
            "score": "recommended",
            "why": f"{len(measurement_cols)} numeric columns — a heatmap reads faster than a table of coefficients.",
        })

    # Bar chart for a categorical-like column (nominal, or a low-cardinality
    # numeric grouping label) against a measured numeric outcome
    grouping_candidates = nominal_cols + group_like_cols
    if grouping_candidates and measurement_cols:
        recommendations.append({
            "name": f"{measurement_cols[0]} by {grouping_candidates[0]}",
            "chart_type": "bar",
            "columns": [grouping_candidates[0], measurement_cols[0]],
            "score": "suggested",
            "why": f"'{grouping_candidates[0]}' looks like a grouping variable — a bar chart compares '{measurement_cols[0]}' across its groups.",
        })

    if not recommendations:
        recommendations.append({
            "name": "Not enough structure to recommend a chart yet",
            "chart_type": "none",
            "columns": [],
            "score": "n/a",
            "why": "Add more numeric columns, or a time/date column, for chart suggestions.",
        })

    return recommendations
