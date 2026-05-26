from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

'''
Định nghĩa schema dữ liệu xét nghiệm đầu vào 
và kiểm tra giá trị hợp lệ trước khi dự đoán.
'''


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

    creatinine: float
    bun: float
    sodium: float
    potassium: float
    chloride: float
    bicarbonate: float
    glucose: float
    calcium: float
    magnesium: float
    phosphate: float
    anion_gap: float
    hemoglobin: float
    hematocrit: float
    wbc: float
    platelets: float

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
    def validate_lab_value(cls, value: float):
        if value < 0:
            raise ValueError("lab values cannot be negative")
        return value

    @model_validator(mode="after")
    def validate_time_order(self):
        if self.charttime < self.icu_intime:
            raise ValueError("charttime must be greater than or equal to icu_intime")
        return self
