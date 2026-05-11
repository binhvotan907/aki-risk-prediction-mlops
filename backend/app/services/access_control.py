from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.doctor_patient_assignment import DoctorPatientAssignment
from app.models.user import User


def has_patient_access(db: Session, user: User, subject_id: int, stay_id: int) -> bool:
    if user.role == "admin":
        return True

    assignment = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.doctor_username == user.username,
            DoctorPatientAssignment.subject_id == subject_id,
            DoctorPatientAssignment.stay_id == stay_id,
        )
        .first()
    )

    return assignment is not None


def require_patient_access(db: Session, user: User, subject_id: int, stay_id: int):
    if not has_patient_access(db, user, subject_id, stay_id):
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this patient stay",
        )
