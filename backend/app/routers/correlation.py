from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import CorrelationRequest, CorrelationResult
from app.routers.auth import require_verified_user
from app.services import correlation_service, data_service, interpretation_engine

router = APIRouter(prefix="/correlation", tags=["Correlation"])


@router.post("/run", response_model=CorrelationResult)
async def run_correlation(req: CorrelationRequest, current_user: dict = Depends(require_verified_user)):
    try:
        df = data_service.get_dataset(req.dataset_id, owner_id=current_user["id"])
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")

    missing = [v for v in req.variables if v not in df.columns]
    if missing:
        raise HTTPException(400, f"Columns not found: {missing}")

    matrix = correlation_service.correlation_matrix(df, req.variables, req.method)

    x, y = df[req.variables[0]].dropna(), df[req.variables[1]].dropna()
    pair = correlation_service.compute_correlation(x.to_numpy(), y.to_numpy(), req.method)
    interp = interpretation_engine.interpret_correlation(
        pair["r"], pair["p_value"], req.variables[0], req.variables[1], req.method
    )

    return CorrelationResult(
        method=req.method, matrix=matrix, variables=req.variables, interpretation=interp
    )
