from datetime import datetime

import pandas as pd

from app.services.feature_engineering import create_realtime_features


def test_create_realtime_features_uses_history_delta():
    feature_order = [
        "creatinine_last",
        "creatinine_delta",
        "creatinine_last_is_missing",
        "bun_last",
        "bun_delta",
        "bun_last_is_missing",
        "hours_since_icu_intime",
        "gender_male",
    ]
    history = pd.DataFrame([
        {
            "subject_id": 10002,
            "stay_id": 30002,
            "gender": "male",
            "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
            "charttime": datetime.fromisoformat("2026-04-25T10:00:00"),
            "creatinine": 0.9,
            "bun": 14,
        }
    ])
    current = {
        "subject_id": 10002,
        "stay_id": 30002,
        "gender": "male",
        "icu_intime": datetime.fromisoformat("2026-04-25T08:00:00"),
        "charttime": datetime.fromisoformat("2026-04-25T14:00:00"),
        "creatinine": 1.4,
        "bun": 28,
    }

    features = create_realtime_features(current, history, feature_order)

    assert features["creatinine_last"] == 1.4
    assert round(features["creatinine_delta"], 4) == 0.5
    assert features["creatinine_last_is_missing"] == 0
    assert features["bun_last"] == 28
    assert features["bun_delta"] == 14
    assert features["hours_since_icu_intime"] == 6
    assert features["gender_male"] == 1
