import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.doctor_patient_assignment import DoctorPatientAssignment
from app.models.lab_event import LabEvent
from app.models.model_version import ModelVersion
from app.models.prediction_log import PredictionLog
from app.models.user import User


def seed():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        existing_admin = db.query(User).filter(User.username == "admin").first()
        existing_doctor = db.query(User).filter(User.username == "doctor").first()

        if not existing_admin:
            admin = User(
                username="admin",
                full_name="ML Admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)

        if not existing_doctor:
            doctor = User(
                username="doctor",
                full_name="Demo Doctor",
                password_hash=hash_password("doctor123"),
                role="doctor",
            )
            db.add(doctor)

        db.commit()

        demo_assignment = (
            db.query(DoctorPatientAssignment)
            .filter(
                DoctorPatientAssignment.doctor_username == "doctor",
                DoctorPatientAssignment.subject_id == 10001,
                DoctorPatientAssignment.stay_id == 30001,
            )
            .first()
        )

        if not demo_assignment:
            db.add(
                DoctorPatientAssignment(
                    doctor_username="doctor",
                    subject_id=10001,
                    stay_id=30001,
                    assigned_by="admin",
                )
            )
            db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    seed()
