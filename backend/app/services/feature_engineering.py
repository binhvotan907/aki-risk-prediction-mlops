import numpy as np
import pandas as pd


LAB_COLUMNS = [
    "creatinine", "bun", "sodium", "potassium", "chloride",
    "bicarbonate", "glucose", "calcium", "magnesium", "phosphate",
    "anion_gap", "hemoglobin", "hematocrit", "wbc", "platelets"
]


def normalize_datetime_value(value):
    """
    Convert datetime value to pandas Timestamp without timezone.
    This avoids mixing tz-aware and tz-naive values.
    """
    ts = pd.to_datetime(value)

    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.tz_localize(None)

    return ts


def normalize_datetime_series(series):
    """
    Convert a pandas Series to datetime and remove timezone safely.
    Works for mixed tz-aware/tz-naive values.
    """
    return series.apply(normalize_datetime_value)


def create_realtime_features(
    lab_input_dict: dict,
    history_df: pd.DataFrame,
    feature_order: list
):
    charttime = normalize_datetime_value(lab_input_dict["charttime"])
    icu_intime = normalize_datetime_value(lab_input_dict["icu_intime"])

    current_row = pd.DataFrame([lab_input_dict])
    current_row["charttime"] = normalize_datetime_series(current_row["charttime"])
    current_row["icu_intime"] = normalize_datetime_series(current_row["icu_intime"])

    if history_df is None or history_df.empty:
        full_history = current_row.copy()
    else:
        history_df = history_df.copy()
        history_df["charttime"] = normalize_datetime_series(history_df["charttime"])
        history_df["icu_intime"] = normalize_datetime_series(history_df["icu_intime"])

        full_history = pd.concat([history_df, current_row], ignore_index=True)

    full_history["charttime"] = normalize_datetime_series(full_history["charttime"])
    full_history["icu_intime"] = normalize_datetime_series(full_history["icu_intime"])

    full_history = full_history.sort_values("charttime")

    lookback_start = charttime - pd.Timedelta(hours=24)

    window = full_history[
        (full_history["charttime"] >= lookback_start) &
        (full_history["charttime"] <= charttime)
    ].copy()

    features = {}

    for lab in LAB_COLUMNS:
        values = window[lab].dropna() if lab in window.columns else pd.Series(dtype=float)

        last_col = f"{lab}_last"
        delta_col = f"{lab}_delta"
        missing_col = f"{lab}_last_is_missing"

        if len(values) == 0:
            features[last_col] = np.nan
            features[delta_col] = np.nan
            features[missing_col] = 1
        else:
            features[last_col] = float(values.iloc[-1])
            features[missing_col] = 0

            if len(values) >= 2:
                features[delta_col] = float(values.iloc[-1] - values.iloc[0])
            else:
                features[delta_col] = 0.0

    features["hours_since_icu_intime"] = (
        charttime - icu_intime
    ).total_seconds() / 3600.0

    features["gender_male"] = 1 if str(
        lab_input_dict["gender"]
    ).lower() in ["male", "m", "nam"] else 0

    final_features = {}

    for col in feature_order:
        final_features[col] = features.get(col, np.nan)

    return final_features