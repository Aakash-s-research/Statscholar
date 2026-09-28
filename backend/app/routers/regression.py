import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import RegressionRequest, RegressionResult
from app.routers.auth import require_verified_user
from app.services import data_service, interpretation_engine, regression_service

router = APIRouter(prefix="/regression", tags=["Regression"])


@router.post("/run", response_model=RegressionResult)
async def run_regression(req: RegressionRequest, current_user: dict = Depends(require_verified_user)):
    try:
        df = data_service.get_dataset(req.dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")

    for col in (req.predictor, req.outcome):
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    x = df[req.predictor].dropna().to_numpy()
    y = df[req.outcome].dropna().to_numpy()

    result = regression_service.simple_linear_regression(x, y)
    y_pred = result["intercept"] + result["slope"] * x
    assumptions = regression_service.check_assumptions(np.array(result["residuals"]), y_pred)

    interp = interpretation_engine.interpret_regression(result, req.predictor, req.outcome)
    interp["flags"] = interp["flags"] + assumptions["flags"]

    return RegressionResult(
        intercept=result["intercept"],
        slope=result["slope"],
        r_squared=result["r_squared"],
        f_statistic=result["f_statistic"],
        p_value=result["p_value"],
        interpretation=interp,
    )
