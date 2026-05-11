from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)

    subject_id = Column(Integer, index=True, nullable=False)
    stay_id = Column(Integer, index=True, nullable=False)
    charttime = Column(DateTime(timezone=True), nullable=False)

    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)

    aki_probability = Column(Float, nullable=False)
    prediction = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)

    latency_ms = Column(Float, nullable=True)
    missing_feature_count = Column(Integer, nullable=True)

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())