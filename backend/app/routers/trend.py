from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import TrendTestRequest, TrendTestResult
from app.routers.auth import require_verified_user
from app.services import data_service, interpretation_engine, trend_service

router = APIRouter(prefix="/trend", tags=["Trend Analysis"])


@router.post("/run", response_model=TrendTestResult)
async def run_trend_test(req: TrendTestRequest, current_user: dict = Depends(require_verified_user)):
    try:
        df = data_service.get_dataset(req.dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")

    if req.variable not in df.columns:
        raise HTTPException(400, f"Column '{req.variable}' not found")

    values = df[req.variable].dropna().to_numpy()
    time = df[req.time_column].dropna().to_numpy()

    if req.test == "mann_kendall":
        stats_result = trend_service.mann_kendall(values, alpha=req.alpha)
        autocorr = trend_service.lag1_autocorrelation(values)
        interp = interpretation_engine.interpret_mann_kendall(stats_result, req.variable)
        interp["flags"] = interpretation_engine.interpret_autocorrelation_flag(autocorr)
        stats_result["autocorrelation"] = autocorr

    elif req.test == "sens_slope":
        stats_result = trend_service.sens_slope(time, values)
        interp = interpretation_engine.interpret_sens_slope(stats_result, req.variable, unit="units")

    elif req.test == "modified_mann_kendall":
        stats_result = trend_service.modified_mann_kendall(values, alpha=req.alpha)
        interp = interpretation_engine.interpret_modified_mann_kendall(stats_result, req.variable)

    elif req.test == "pre_whitening":
        stats_result = trend_service.pre_whitening(values, alpha=req.alpha)
        interp = interpretation_engine.interpret_pre_whitening(stats_result, req.variable)

    elif req.test == "tfpw":
        stats_result = trend_service.trend_free_pre_whitening(time, values, alpha=req.alpha)
        interp = interpretation_engine.interpret_trend_free_pre_whitening(stats_result, req.variable)

    elif req.test == "seasonal_mann_kendall":
        if not req.season_column:
            raise HTTPException(400, "seasonal_mann_kendall requires season_column")
        if req.season_column not in df.columns:
            raise HTTPException(400, f"Column '{req.season_column}' not found")
        season_ids = df[req.season_column].dropna().to_numpy()
        if len(season_ids) != len(values):
            raise HTTPException(400, "variable and season_column must have the same length (no independent missing rows)")
        try:
            stats_result = trend_service.seasonal_mann_kendall(values, season_ids, alpha=req.alpha)
        except ValueError as e:
            raise HTTPException(400, str(e))
        interp = interpretation_engine.interpret_seasonal_mann_kendall(stats_result, req.variable)

    else:
        raise HTTPException(400, f"Unknown test '{req.test}'")

    return TrendTestResult(test=req.test, statistics=stats_result, interpretation=interp)
