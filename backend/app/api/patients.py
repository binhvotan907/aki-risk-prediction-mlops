from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin, require_doctor_or_admin
from app.models.doctor_patient_assignment import DoctorPatientAssignment
from app.models.lab_event import LabEvent
from app.models.patient import Patient
from app.models.prediction_log import PredictionLog
from app.models.user import User
from app.services.access_control import require_patient_access


router = APIRouter(prefix="/patients", tags=["Patients"])


class AssignmentRequest(BaseModel):
    doctor_username: str
    subject_id: int
    stay_id: int


class PatientRequest(BaseModel):
    subject_id: int
    stay_id: int
    gender: str | None = None


@router.get("")
def list_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    assigned_rows_query = db.query(DoctorPatientAssignment)

    if current_user.role != "admin":
        assigned_rows_query = assigned_rows_query.filter(
            DoctorPatientAssignment.doctor_username == current_user.username
        )

    assigned_rows = assigned_rows_query.all()
    patient_keys = {
        (row.subject_id, row.stay_id)
        for row in assigned_rows
    }

    if current_user.role == "admin":
        registered_keys = db.query(Patient.subject_id, Patient.stay_id).distinct().all()
        lab_keys = db.query(LabEvent.subject_id, LabEvent.stay_id).distinct().all()
        prediction_keys = (
            db.query(PredictionLog.subject_id, PredictionLog.stay_id)
            .distinct()
            .all()
        )
        patient_keys.update((row[0], row[1]) for row in registered_keys)
        patient_keys.update((row[0], row[1]) for row in lab_keys)
        patient_keys.update((row[0], row[1]) for row in prediction_keys)

    assignments_by_key = {}
    for row in assigned_rows:
        assignments_by_key[(row.subject_id, row.stay_id)] = row

    patients = []

    for subject_id, stay_id in sorted(patient_keys):
        assignment = assignments_by_key.get((subject_id, stay_id))
        registered_patient = (
            db.query(Patient)
            .filter(Patient.subject_id == subject_id, Patient.stay_id == stay_id)
            .first()
        )
        lab_count = (
            db.query(LabEvent)
            .filter(LabEvent.subject_id == subject_id, LabEvent.stay_id == stay_id)
            .count()
        )
        prediction_count = (
            db.query(PredictionLog)
            .filter(PredictionLog.subject_id == subject_id, PredictionLog.stay_id == stay_id)
            .count()
        )
        latest_prediction = (
            db.query(PredictionLog)
            .filter(PredictionLog.subject_id == subject_id, PredictionLog.stay_id == stay_id)
            .order_by(PredictionLog.charttime.desc(), PredictionLog.created_at.desc())
            .first()
        )

        patients.append({
            "subject_id": subject_id,
            "stay_id": stay_id,
            "gender": registered_patient.gender if registered_patient else None,
            "registered_at": registered_patient.created_at if registered_patient else None,
            "doctor_username": assignment.doctor_username if assignment else None,
            "assigned_by": assignment.assigned_by if assignment else None,
            "assigned_at": assignment.created_at if assignment else None,
            "lab_event_count": lab_count,
            "prediction_count": prediction_count,
            "latest_charttime": latest_prediction.charttime if latest_prediction else None,
            "latest_probability": round(latest_prediction.aki_probability, 4) if latest_prediction else None,
            "latest_risk_level": latest_prediction.risk_level if latest_prediction else None,
        })

    patients.sort(
        key=lambda item: (
            item["latest_charttime"] or item["assigned_at"]
        ).isoformat() if (item["latest_charttime"] or item["assigned_at"]) else "",
        reverse=True,
    )

    return patients


@router.post("")
def create_patient(
    payload: PatientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = (
        db.query(Patient)
        .filter(
            Patient.subject_id == payload.subject_id,
            Patient.stay_id == payload.stay_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Patient already exists")

    patient = Patient(
        subject_id=payload.subject_id,
        stay_id=payload.stay_id,
        gender=payload.gender,
        created_by=current_user.username,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return {
        "id": patient.id,
        "subject_id": patient.subject_id,
        "stay_id": patient.stay_id,
        "gender": patient.gender,
        "created_by": patient.created_by,
        "created_at": patient.created_at,
    }


@router.get("/assignments")
def list_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    rows = (
        db.query(DoctorPatientAssignment)
        .order_by(DoctorPatientAssignment.created_at.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "doctor_username": row.doctor_username,
            "subject_id": row.subject_id,
            "stay_id": row.stay_id,
            "assigned_by": row.assigned_by,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/assignments")
def create_assignment(
    payload: AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    doctor = (
        db.query(User)
        .filter(
            User.username == payload.doctor_username,
            User.role == "doctor",
            User.is_active == True,
        )
        .first()
    )
    if not doctor:
        raise HTTPException(status_code=404, detail="Active doctor not found")

    patient = (
        db.query(Patient)
        .filter(
            Patient.subject_id == payload.subject_id,
            Patient.stay_id == payload.stay_id,
        )
        .first()
    )
    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found. Please create patient before assigning doctor.",
        )

    existing = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.subject_id == payload.subject_id,
            DoctorPatientAssignment.stay_id == payload.stay_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Patient already assigned")

    assignment = DoctorPatientAssignment(
        doctor_username=payload.doctor_username,
        subject_id=payload.subject_id,
        stay_id=payload.stay_id,
        assigned_by=current_user.username,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "id": assignment.id,
        "doctor_username": assignment.doctor_username,
        "subject_id": assignment.subject_id,
        "stay_id": assignment.stay_id,
        "assigned_by": assignment.assigned_by,
        "created_at": assignment.created_at,
    }


@router.delete("/assignments/{assignment_id}")
def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    assignment = (
        db.query(DoctorPatientAssignment)
        .filter(DoctorPatientAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    db.delete(assignment)
    db.commit()

    return {"message": "Assignment deleted"}


@router.delete("/{subject_id}/{stay_id}/records")
def delete_patient_records(
    subject_id: int,
    stay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    deleted_predictions = (
        db.query(PredictionLog)
        .filter(
            PredictionLog.subject_id == subject_id,
            PredictionLog.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    deleted_labs = (
        db.query(LabEvent)
        .filter(
            LabEvent.subject_id == subject_id,
            LabEvent.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    return {
        "message": "Patient records deleted",
        "subject_id": subject_id,
        "stay_id": stay_id,
        "deleted_lab_events": deleted_labs,
        "deleted_prediction_logs": deleted_predictions,
    }


@router.delete("/{subject_id}/{stay_id}")
def delete_patient(
    subject_id: int,
    stay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    deleted_predictions = (
        db.query(PredictionLog)
        .filter(
            PredictionLog.subject_id == subject_id,
            PredictionLog.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    deleted_labs = (
        db.query(LabEvent)
        .filter(
            LabEvent.subject_id == subject_id,
            LabEvent.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    deleted_assignments = (
        db.query(DoctorPatientAssignment)
        .filter(
            DoctorPatientAssignment.subject_id == subject_id,
            DoctorPatientAssignment.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    deleted_patients = (
        db.query(Patient)
        .filter(
            Patient.subject_id == subject_id,
            Patient.stay_id == stay_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    return {
        "message": "Patient deleted",
        "subject_id": subject_id,
        "stay_id": stay_id,
        "deleted_lab_events": deleted_labs,
        "deleted_prediction_logs": deleted_predictions,
        "deleted_assignments": deleted_assignments,
        "deleted_patients": deleted_patients,
    }


@router.get("/my-assignments")
def list_my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    query = db.query(DoctorPatientAssignment)

    if current_user.role != "admin":
        query = query.filter(
            DoctorPatientAssignment.doctor_username == current_user.username
        )

    rows = query.order_by(DoctorPatientAssignment.created_at.desc()).all()

    return [
        {
            "id": row.id,
            "doctor_username": row.doctor_username,
            "subject_id": row.subject_id,
            "stay_id": row.stay_id,
            "assigned_by": row.assigned_by,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/{subject_id}/{stay_id}/timeline")
def patient_timeline(
    subject_id: int,
    stay_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    require_patient_access(db, current_user, subject_id, stay_id)

    labs = (
        db.query(LabEvent)
        .filter(LabEvent.subject_id == subject_id, LabEvent.stay_id == stay_id)
        .order_by(LabEvent.charttime.asc())
        .all()
    )

    preds = (
        db.query(PredictionLog)
        .filter(PredictionLog.subject_id == subject_id, PredictionLog.stay_id == stay_id)
        .order_by(PredictionLog.charttime.asc())
        .all()
    )

    pred_map = {p.charttime: p for p in preds}

    timeline = []

    for lab in labs:
        pred = pred_map.get(lab.charttime)

        timeline.append({
            "charttime": lab.charttime,
            "creatinine": lab.creatinine,
            "bun": lab.bun,
            "bicarbonate": lab.bicarbonate,
            "phosphate": lab.phosphate,
            "anion_gap": lab.anion_gap,
            "aki_probability": round(pred.aki_probability, 4) if pred else None,
            "risk_level": pred.risk_level if pred else None,
        })

    return {
        "subject_id": subject_id,
        "stay_id": stay_id,
        "timeline": timeline,
    }
