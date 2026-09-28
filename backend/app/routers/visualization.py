from fastapi import APIRouter, Depends, HTTPException

from app.routers.auth import require_verified_user
from app.services import data_service, visualization_service

router = APIRouter(prefix="/visualization", tags=["Visualization"])


@router.get("/{dataset_id}/recommend")
async def recommend_charts(dataset_id: str, current_user: dict = Depends(require_verified_user)):
    try:
        return {"recommendations": visualization_service.recommend_charts(dataset_id, owner_id=current_user["id"])}
    except KeyError:
        raise HTTPException(404, "Dataset not found")
    except data_service.NotOwnedError:
        raise HTTPException(403, "This dataset does not belong to you")
