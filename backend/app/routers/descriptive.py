from fastapi import APIRouter, Depends, HTTPException
from scipy import stats

from app.routers.auth import require_verified_user
from app.services import data_service

router = APIRouter(prefix="/descriptive", tags=["Descriptive Statistics"])


@router.get("/{dataset_id}/{variable}")
async def describe_variable(dataset_id: str, variable: str, current_user: dict = Depends(require_verified_user)):
    try:
        df = data_service.get_dataset(dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")
    if variable not in df.columns:
        raise HTTPException(400, f"Column '{variable}' not found")

    series = df[variable].dropna()
    return {
        "variable": variable,
        "mean": round(float(series.mean()), 3),
        "median": round(float(series.median()), 3),
        "sd": round(float(series.std()), 3),
        "variance": round(float(series.var()), 3),
        "skewness": round(float(stats.skew(series)), 3),
        "kurtosis": round(float(stats.kurtosis(series)), 3),
        "min": round(float(series.min()), 3),
        "max": round(float(series.max()), 3),
        "shapiro_wilk_p": round(float(stats.shapiro(series).pvalue), 4),
    }
