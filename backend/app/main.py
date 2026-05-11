from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.services.model_loader import model_loader

from app.models.user import User
from app.models.lab_event import LabEvent
from app.models.prediction_log import PredictionLog
from app.models.model_version import ModelVersion
from app.models.doctor_patient_assignment import DoctorPatientAssignment
from app.models.patient import Patient

from app.api.auth import router as auth_router
from app.api.predict import router as predict_router
from app.api.monitoring import router as monitoring_router
from app.api.patients import router as patients_router
from app.api.model_info import router as model_router
from app.api.retraining import router as retraining_router


app = FastAPI(
    title="Real-time AKI Risk Prediction MLOps API",
    description="Ứng dụng dự đoán nguy cơ suy thận cấp theo thời gian thực theo hướng MLOps",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    model_loader.load()


@app.get("/")
def root():
    return {
        "message": "Real-time AKI Risk Prediction MLOps API",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_loader.model is not None,
    }


app.include_router(auth_router)
app.include_router(predict_router)
app.include_router(monitoring_router)
app.include_router(patients_router)
app.include_router(model_router)
app.include_router(retraining_router)
