"""
Shared request/response schemas.

One file for v1 since the schema surface is still small — split into
per-module files (schemas/trend.py, schemas/regression.py, ...) once
each module's request shape stabilizes.
"""
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Mode(str, Enum):
    student = "student"
    research = "research"


class VariableType(str, Enum):
    nominal = "nominal"
    ordinal = "ordinal"
    interval = "interval"
    ratio = "ratio"


# ---------- Data Preparation ----------

class ColumnInfo(BaseModel):
    name: str
    detected_type: VariableType
    missing_count: int
    missing_pct: float


class DatasetSummary(BaseModel):
    dataset_id: str
    filename: str
    row_count: int
    columns: list[ColumnInfo]
    quality_score: int = Field(ge=0, le=100)
    preview: list[dict[str, Any]]


# ---------- Interpretation (shared shape returned by every analysis module) ----------

class InterpretationResult(BaseModel):
    student_text: str
    research_text: str
    flags: list[str] = []


# ---------- Trend Analysis ----------

class TrendTestRequest(BaseModel):
    dataset_id: str
    variable: str
    time_column: str
    test: str  # "mann_kendall" | "modified_mann_kendall" | "sens_slope" |
               # "pre_whitening" | "tfpw" | "seasonal_mann_kendall"
    season_column: Optional[str] = None  # required for seasonal_mann_kendall
    alpha: float = 0.05
    mode: Mode = Mode.student


class TrendTestResult(BaseModel):
    test: str
    statistics: dict[str, Any]
    interpretation: InterpretationResult


# ---------- Correlation ----------

class CorrelationRequest(BaseModel):
    dataset_id: str
    variables: list[str]
    method: str  # "pearson" | "spearman" | "kendall"
    mode: Mode = Mode.student


class CorrelationResult(BaseModel):
    method: str
    matrix: list[list[float]]
    variables: list[str]
    interpretation: InterpretationResult


# ---------- Regression ----------

class RegressionRequest(BaseModel):
    dataset_id: str
    predictor: str
    outcome: str
    mode: Mode = Mode.student


class RegressionResult(BaseModel):
    intercept: float
    slope: float
    r_squared: float
    f_statistic: float
    p_value: float
    interpretation: InterpretationResult
