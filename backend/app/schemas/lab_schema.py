from typing import Optional
from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator


LAB_VALUE_FIELDS = [
    "creatinine",
    "bun",
    "sodium",
    "potassium",
    "chloride",
    "bicarbonate",
    "glucose",
    "calcium",
    "magnesium",
    "phosphate",
    "anion_gap",
    "hemoglobin",
    "hematocrit",
    "wbc",
    "platelets",
]

VALID_GENDERS = {"male", "female", "m", "f", "nam", "nu", "nữ"}


class LabInput(BaseModel):
    subject_id: int
    stay_id: int

    gender: str
    icu_intime: datetime
    charttime: datetime

    creatinine: Optional[float] = None
    bun: Optional[float] = None
    sodium: Optional[float] = None
    potassium: Optional[float] = None
    chloride: Optional[float] = None
    bicarbonate: Optional[float] = None
    glucose: Optional[float] = None
    calcium: Optional[float] = None
    magnesium: Optional[float] = None
    phosphate: Optional[float] = None
    anion_gap: Optional[float] = None
    hemoglobin: Optional[float] = None
    hematocrit: Optional[float] = None
    wbc: Optional[float] = None
    platelets: Optional[float] = None

    @field_validator("subject_id", "stay_id")
    @classmethod
    def validate_positive_identifier(cls, value: int):
        if value <= 0:
            raise ValueError("subject_id and stay_id must be positive integers")
        return value

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str):
        normalized = value.strip().lower()
        if normalized not in VALID_GENDERS:
            raise ValueError("gender must be male/female, m/f, nam/nu")
        return value

    @field_validator(*LAB_VALUE_FIELDS)
    @classmethod
    def validate_lab_value(cls, value: Optional[float]):
        if value is not None and value < 0:
            raise ValueError("lab values cannot be negative")
        return value

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.charttime < self.icu_intime:
            raise ValueError("charttime must be greater than or equal to icu_intime")
        return self
