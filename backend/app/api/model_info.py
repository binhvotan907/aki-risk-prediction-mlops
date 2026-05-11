from fastapi import APIRouter, Depends
from app.core.security import require_doctor_or_admin
from app.models.user import User
from app.services.model_loader import model_loader


router = APIRouter(prefix="/model", tags=["Model"])


@router.get("/info")
def model_info(current_user: User = Depends(require_doctor_or_admin)):
    return {
        "model_name": model_loader.model_name,
        "model_version": model_loader.model_version,
        "threshold": model_loader.threshold,
        "metrics": model_loader.metrics,
        "feature_count": len(model_loader.feature_order),
        "lookback_hours": model_loader.config.get("lookback_hours"),
        "prediction_horizon_hours": model_loader.config.get("prediction_horizon_hours")
    }