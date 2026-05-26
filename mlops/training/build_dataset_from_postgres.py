import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.models.lab_event import LabEvent
from app.services.feature_engineering import create_realtime_features


LAB_COLUMNS = [
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


def resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def lab_events_to_dataframe() -> pd.DataFrame:
    db = SessionLocal()
    try:
        rows = (
            db.query(LabEvent)
            .order_by(LabEvent.subject_id.asc(), LabEvent.stay_id.asc(), LabEvent.charttime.asc())
            .all()
        )
    finally:
        db.close()

    records = []
    for row in rows:
        record = {
            "subject_id": row.subject_id,
            "stay_id": row.stay_id,
            "gender": row.gender,
            "icu_intime": row.icu_intime,
            "charttime": row.charttime,
        }
        for lab in LAB_COLUMNS:
            record[lab] = getattr(row, lab)
        records.append(record)

    return pd.DataFrame(records)


def remove_timezone(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series).apply(
        lambda value: value.tz_localize(None) if getattr(value, "tzinfo", None) is not None else value
    )


def build_labeled_samples(events_df: pd.DataFrame, feature_order: list[str]) -> pd.DataFrame:
    if events_df.empty:
        return pd.DataFrame(columns=feature_order + ["label"])

    events_df = events_df.copy()
    events_df["charttime"] = remove_timezone(events_df["charttime"])
    events_df["icu_intime"] = remove_timezone(events_df["icu_intime"])
    events_df = events_df.sort_values(["subject_id", "stay_id", "charttime"])

    samples = []
    for (_, _), group in events_df.groupby(["subject_id", "stay_id"]):
        group = group.sort_values("charttime").reset_index(drop=True)

        for idx, row in group.iterrows():
            charttime = row["charttime"]
            lookback_start = charttime - pd.Timedelta(hours=24)
            future_end = charttime + pd.Timedelta(hours=24)

            history = group.iloc[:idx].copy()
            past_window = group[
                (group["charttime"] >= lookback_start)
                & (group["charttime"] <= charttime)
            ]
            future_window = group[
                (group["charttime"] > charttime)
                & (group["charttime"] <= future_end)
            ]

            baseline_values = past_window["creatinine"].dropna()
            future_values = future_window["creatinine"].dropna()
            if baseline_values.empty or future_values.empty:
                continue

            baseline_creatinine = float(baseline_values.iloc[-1])
            if baseline_creatinine <= 0:
                continue

            future_max_creatinine = float(future_values.max())
            label = int(
                (future_max_creatinine - baseline_creatinine >= 0.3)
                or (future_max_creatinine / baseline_creatinine >= 1.5)
            )

            lab_input = row.to_dict()
            features = create_realtime_features(
                lab_input_dict=lab_input,
                history_df=history,
                feature_order=feature_order,
            )
            features["label"] = label
            samples.append(features)

    return pd.DataFrame(samples, columns=feature_order + ["label"])


def build_augmented_dataset(config: dict, output_dir: Path, min_samples: int) -> dict:
    data_cfg = config["data"]
    train_path = resolve_path(data_cfg["train_path"])
    feature_order = read_json(resolve_path(data_cfg["features_path"]))

    train_df = pd.read_parquet(train_path)
    events_df = lab_events_to_dataframe()
    production_df = build_labeled_samples(events_df, feature_order)

    output_dir.mkdir(parents=True, exist_ok=True)
    production_path = output_dir / "production_labeled_samples.parquet"
    augmented_train_path = output_dir / "train_augmented.parquet"

    summary = {
        "source_lab_events": int(len(events_df)),
        "labeled_production_samples": int(len(production_df)),
        "min_samples": int(min_samples),
        "used_for_training": False,
        "original_train_path": str(train_path),
        "augmented_train_path": None,
        "production_samples_path": None,
    }

    if not production_df.empty:
        production_df.to_parquet(production_path, index=False)
        summary["production_samples_path"] = str(production_path)

    if len(production_df) < min_samples:
        return summary

    augmented_train_df = pd.concat([train_df, production_df], ignore_index=True)
    augmented_train_df.to_parquet(augmented_train_path, index=False)

    summary.update({
        "used_for_training": True,
        "augmented_train_path": str(augmented_train_path),
        "original_train_rows": int(len(train_df)),
        "augmented_train_rows": int(len(augmented_train_df)),
        "production_positive_rate": float(production_df["label"].mean()),
    })
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Build labeled AKI training samples from PostgreSQL lab_events."
    )
    parser.add_argument("--config", required=True, help="Training config YAML path")
    parser.add_argument("--output-dir", required=True, help="Directory for generated parquet files")
    parser.add_argument("--summary", required=True, help="Output summary JSON path")
    parser.add_argument("--min-samples", type=int, default=30)
    args = parser.parse_args()

    config = read_yaml(Path(args.config))
    summary = build_augmented_dataset(
        config=config,
        output_dir=resolve_path(args.output_dir),
        min_samples=args.min_samples,
    )
    write_json(resolve_path(args.summary), summary)

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
