from datetime import datetime

import pandas as pd

from mlops.training.build_dataset_from_postgres import build_labeled_samples


FEATURE_ORDER = [
    "creatinine_last",
    "creatinine_delta",
    "creatinine_last_is_missing",
    "bun_last",
    "bun_delta",
    "bun_last_is_missing",
    "hours_since_icu_intime",
    "gender_male",
]


def test_build_labeled_samples_uses_future_creatinine_window():
    events = pd.DataFrame([
        {
            "subject_id": 10001,
            "stay_id": 30001,
            "gender": "male",
            "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
            "charttime": datetime.fromisoformat("2026-04-25T10:00:00"),
            "creatinine": 1.0,
            "bun": 15,
        },
        {
            "subject_id": 10001,
            "stay_id": 30001,
            "gender": "male",
            "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
            "charttime": datetime.fromisoformat("2026-04-25T18:00:00"),
            "creatinine": 1.4,
            "bun": 25,
        },
    ])

    samples = build_labeled_samples(events, FEATURE_ORDER)

    assert len(samples) == 1
    assert samples.iloc[0]["label"] == 1
    assert samples.iloc[0]["creatinine_last"] == 1.0
    assert samples.iloc[0]["hours_since_icu_intime"] == 2


def test_build_labeled_samples_skips_rows_without_future_creatinine():
    events = pd.DataFrame([
        {
            "subject_id": 10001,
            "stay_id": 30001,
            "gender": "female",
            "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
            "charttime": datetime.fromisoformat("2026-04-25T10:00:00"),
            "creatinine": 1.0,
            "bun": 15,
        }
    ])

    samples = build_labeled_samples(events, FEATURE_ORDER)

    assert samples.empty
