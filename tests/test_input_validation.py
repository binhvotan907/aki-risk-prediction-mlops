from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.lab_schema import LabInput


def valid_payload(**overrides):
    payload = {
        "subject_id": 10002,
        "stay_id": 30002,
        "gender": "male",
        "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
        "charttime": datetime.fromisoformat("2026-04-25T10:00:00"),
        "creatinine": 0.9,
        "bun": 14,
    }
    payload.update(overrides)
    return payload


def test_lab_input_accepts_valid_payload():
    payload = LabInput(**valid_payload())

    assert payload.subject_id == 10002
    assert payload.creatinine == 0.9


@pytest.mark.parametrize(
    "overrides",
    [
        {"subject_id": 0},
        {"stay_id": -1},
        {"gender": "unknown"},
        {"creatinine": -0.1},
        {"charttime": datetime.fromisoformat("2026-04-25T07:00:00")},
    ],
)
def test_lab_input_rejects_invalid_payload(overrides):
    with pytest.raises(ValidationError):
        LabInput(**valid_payload(**overrides))
