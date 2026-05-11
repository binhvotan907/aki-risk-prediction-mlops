from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class DoctorPatientAssignment(Base):
    __tablename__ = "doctor_patient_assignments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_username = Column(String, index=True, nullable=False)
    subject_id = Column(Integer, index=True, nullable=False)
    stay_id = Column(Integer, index=True, nullable=False)
    assigned_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
