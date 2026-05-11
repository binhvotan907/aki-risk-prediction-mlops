import pytest
from fastapi import HTTPException

from app.core.security import require_doctor
from app.models.user import User


def test_admin_cannot_use_doctor_prediction_permission():
    admin = User(username="admin", role="admin", is_active=True)

    with pytest.raises(HTTPException) as exc:
        require_doctor(admin)

    assert exc.value.status_code == 403


def test_doctor_can_use_prediction_permission():
    doctor = User(username="doctor", role="doctor", is_active=True)

    assert require_doctor(doctor) is doctor
