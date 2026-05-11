from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class LabEvent(Base):
    __tablename__ = "lab_events"

    id = Column(Integer, primary_key=True, index=True)

    subject_id = Column(Integer, index=True, nullable=False)
    stay_id = Column(Integer, index=True, nullable=False)

    gender = Column(String, nullable=False)
    icu_intime = Column(DateTime(timezone=True), nullable=False)
    charttime = Column(DateTime(timezone=True), nullable=False)

    creatinine = Column(Float, nullable=True)
    bun = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    chloride = Column(Float, nullable=True)
    bicarbonate = Column(Float, nullable=True)
    glucose = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    magnesium = Column(Float, nullable=True)
    phosphate = Column(Float, nullable=True)
    anion_gap = Column(Float, nullable=True)
    hemoglobin = Column(Float, nullable=True)
    hematocrit = Column(Float, nullable=True)
    wbc = Column(Float, nullable=True)
    platelets = Column(Float, nullable=True)

    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())