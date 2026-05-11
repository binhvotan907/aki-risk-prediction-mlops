import time
import pandas as pd
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_doctor
from app.models.lab_event import LabEvent
from app.models.prediction_log import PredictionLog
from app.models.user import User
from app.schemas.lab_schema import LabInput
from app.services.access_control import require_patient_access
from app.services.feature_engineering import create_realtime_features
from app.services.model_loader import model_loader


router = APIRouter(prefix="/predict", tags=["Prediction"])


def get_history_dataframe(db: Session, subject_id: int, stay_id: int):
    rows = (
        db.query(LabEvent)
        .filter(LabEvent.subject_id == subject_id, LabEvent.stay_id == stay_id)
        .order_by(LabEvent.charttime.asc())
        .all()
    )

    if not rows:
        return pd.DataFrame()

    data = []
    for r in rows:
        data.append({
            "subject_id": r.subject_id,
            "stay_id": r.stay_id,
            "gender": r.gender,
            "icu_intime": r.icu_intime,
            "charttime": r.charttime,
            "creatinine": r.creatinine,
            "bun": r.bun,
            "sodium": r.sodium,
            "potassium": r.potassium,
            "chloride": r.chloride,
            "bicarbonate": r.bicarbonate,
            "glucose": r.glucose,
            "calcium": r.calcium,
            "magnesium": r.magnesium,
            "phosphate": r.phosphate,
            "anion_gap": r.anion_gap,
            "hemoglobin": r.hemoglobin,
            "hematocrit": r.hematocrit,
            "wbc": r.wbc,
            "platelets": r.platelets,
        })

    return pd.DataFrame(data)


@router.post("")
def predict(
    payload: LabInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    start = time.time()
    require_patient_access(db, current_user, payload.subject_id, payload.stay_id)

    input_dict = payload.model_dump()

    history_df = get_history_dataframe(
        db=db,
        subject_id=payload.subject_id,
        stay_id=payload.stay_id,
    )

    features = create_realtime_features(
        lab_input_dict=input_dict,
        history_df=history_df,
        feature_order=model_loader.feature_order,
    )

    X = pd.DataFrame([features], columns=model_loader.feature_order)
    missing_feature_count = int(X.isna().sum(axis=1).iloc[0])

    X_imputed = model_loader.imputer.transform(X)

    probability = float(model_loader.model.predict_proba(X_imputed)[0][1])
    prediction = 1 if probability >= model_loader.threshold else 0

    if probability < 0.30:
        risk_level = "Low"
        message = "Nguy cơ AKI thấp."
    elif probability < model_loader.threshold:
        risk_level = "Medium"
        message = "Nguy cơ AKI trung bình, cần tiếp tục theo dõi."
    else:
        risk_level = "High"
        message = "Nguy cơ AKI cao, cần theo dõi sát chức năng thận."

    lab_event = LabEvent(
        **input_dict,
        created_by=current_user.username,
    )
    db.add(lab_event)

    latency_ms = (time.time() - start) * 1000

    log = PredictionLog(
        subject_id=payload.subject_id,
        stay_id=payload.stay_id,
        charttime=payload.charttime,
        model_name=model_loader.model_name,
        model_version=model_loader.model_version,
        threshold=model_loader.threshold,
        aki_probability=probability,
        prediction=prediction,
        risk_level=risk_level,
        latency_ms=latency_ms,
        missing_feature_count=missing_feature_count,
        created_by=current_user.username,
    )
    db.add(log)

    db.commit()

    return {
        "subject_id": payload.subject_id,
        "stay_id": payload.stay_id,
        "aki_probability": round(probability, 4),
        "prediction": prediction,
        "risk_level": risk_level,
        "threshold": model_loader.threshold,
        "model_name": model_loader.model_name,
        "model_version": model_loader.model_version,
        "latency_ms": round(latency_ms, 2),
        "missing_feature_count": missing_feature_count,
        "message": message,
        "generated_features_preview": {
            "creatinine_last": features.get("creatinine_last"),
            "creatinine_delta": features.get("creatinine_delta"),
            "bun_last": features.get("bun_last"),
            "bun_delta": features.get("bun_delta"),
            "hours_since_icu_intime": features.get("hours_since_icu_intime"),
            "gender_male": features.get("gender_male"),
        },
    }
