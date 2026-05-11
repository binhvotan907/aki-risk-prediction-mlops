from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, index=True)

    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)

    artifact_path = Column(String, nullable=False)
    threshold = Column(Float, nullable=False)

    roc_auc = Column(Float, nullable=True)
    pr_auc = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1 = Column(Float, nullable=True)

    status = Column(String, default="production")  # staging, production, archived
    created_at = Column(DateTime(timezone=True), server_default=func.now())