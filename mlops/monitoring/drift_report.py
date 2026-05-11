import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_REFERENCE_PATH = ROOT_DIR / "data" / "train_dataset_final.parquet"
DEFAULT_FEATURES_PATH = ROOT_DIR / "data" / "features_dataset_final.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "reports" / "drift_report.json"

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

RAW_REQUIRED_COLUMNS = [
    "subject_id",
    "stay_id",
    "gender",
    "icu_intime",
    "charttime",
    *LAB_COLUMNS,
]


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def resolve_path(path_value: str | None) -> Path | None:
    if not path_value:
        return None

    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix in [".csv", ".txt"]:
        return pd.read_csv(path)
    raise ValueError(f"Unsupported current data format: {path.suffix}")


def load_lab_events_from_database(limit: int | None = None) -> pd.DataFrame:
    sys.path.insert(0, str(BACKEND_DIR))

    from app.core.database import SessionLocal
    from app.models.lab_event import LabEvent

    db = SessionLocal()
    try:
        query = db.query(LabEvent).order_by(
            LabEvent.subject_id.asc(),
            LabEvent.stay_id.asc(),
            LabEvent.charttime.asc(),
        )
        if limit:
            query = query.limit(limit)

        rows = query.all()
    finally:
        db.close()

    data = []
    for row in rows:
        data.append({
            "subject_id": row.subject_id,
            "stay_id": row.stay_id,
            "gender": row.gender,
            "icu_intime": row.icu_intime,
            "charttime": row.charttime,
            "creatinine": row.creatinine,
            "bun": row.bun,
            "sodium": row.sodium,
            "potassium": row.potassium,
            "chloride": row.chloride,
            "bicarbonate": row.bicarbonate,
            "glucose": row.glucose,
            "calcium": row.calcium,
            "magnesium": row.magnesium,
            "phosphate": row.phosphate,
            "anion_gap": row.anion_gap,
            "hemoglobin": row.hemoglobin,
            "hematocrit": row.hematocrit,
            "wbc": row.wbc,
            "platelets": row.platelets,
        })

    return pd.DataFrame(data)


def raw_labs_to_features(raw_df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    missing = [col for col in RAW_REQUIRED_COLUMNS if col not in raw_df.columns]
    if missing:
        raise ValueError(f"Current raw lab data is missing required columns: {missing}")

    sys.path.insert(0, str(BACKEND_DIR))
    from app.services.feature_engineering import create_realtime_features

    raw_df = raw_df.copy()
    raw_df["charttime"] = pd.to_datetime(raw_df["charttime"], errors="coerce")
    raw_df["icu_intime"] = pd.to_datetime(raw_df["icu_intime"], errors="coerce")
    raw_df = raw_df.dropna(subset=["subject_id", "stay_id", "charttime", "icu_intime"])
    raw_df = raw_df.sort_values(["subject_id", "stay_id", "charttime"])

    feature_rows = []
    histories: dict[tuple[int, int], list[dict]] = {}

    for record in raw_df.to_dict(orient="records"):
        key = (int(record["subject_id"]), int(record["stay_id"]))
        history_df = pd.DataFrame(histories.get(key, []))
        features = create_realtime_features(
            lab_input_dict=record,
            history_df=history_df,
            feature_order=feature_cols,
        )
        feature_rows.append(features)
        histories.setdefault(key, []).append(record)

    return pd.DataFrame(feature_rows, columns=feature_cols)


def load_current_features(
    feature_cols: list[str],
    current_path: Path | None,
    limit: int | None,
) -> pd.DataFrame:
    if current_path:
        current_df = read_table(current_path)
    else:
        current_df = load_lab_events_from_database(limit=limit)

    if current_df.empty:
        return pd.DataFrame(columns=feature_cols)

    if all(col in current_df.columns for col in feature_cols):
        return current_df[feature_cols].copy()

    return raw_labs_to_features(current_df, feature_cols)


def psi(reference: pd.Series, current: pd.Series, bins: int = 10) -> float:
    reference = pd.to_numeric(reference, errors="coerce").dropna()
    current = pd.to_numeric(current, errors="coerce").dropna()

    if reference.empty or current.empty:
        return 0.0

    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.nanquantile(reference, quantiles))

    if len(edges) < 2:
        return 0.0

    edges[0] = -np.inf
    edges[-1] = np.inf

    reference_counts, _ = np.histogram(reference, bins=edges)
    current_counts, _ = np.histogram(current, bins=edges)

    reference_pct = np.maximum(reference_counts / max(reference_counts.sum(), 1), 1e-6)
    current_pct = np.maximum(current_counts / max(current_counts.sum(), 1), 1e-6)

    return float(np.sum((current_pct - reference_pct) * np.log(current_pct / reference_pct)))


def classify_psi(value: float) -> str:
    if value >= 0.25:
        return "major"
    if value >= 0.10:
        return "moderate"
    return "stable"


def build_drift_report(
    reference_path: Path,
    features_path: Path,
    current_path: Path | None,
    output_path: Path,
    limit: int | None,
) -> dict:
    feature_cols = load_json(features_path)
    reference_df = pd.read_parquet(reference_path)

    missing_reference_cols = [col for col in feature_cols if col not in reference_df.columns]
    if missing_reference_cols:
        raise ValueError(f"Reference data is missing feature columns: {missing_reference_cols}")

    reference_features = reference_df[feature_cols].copy()
    current_features = load_current_features(
        feature_cols=feature_cols,
        current_path=current_path,
        limit=limit,
    )

    if current_features.empty:
        report = {
            "status": "insufficient_data",
            "drift_detected": False,
            "reference_path": str(reference_path),
            "current_source": str(current_path) if current_path else "database:lab_events",
            "n_reference_rows": int(len(reference_features)),
            "n_current_rows": 0,
            "n_features_checked": len(feature_cols),
            "n_drifted_features": 0,
            "drifted_features": [],
            "feature_results": [],
            "alerts": ["No current production lab data is available for drift calculation."],
        }
        write_json(output_path, report)
        return report

    feature_results = []
    for feature in feature_cols:
        psi_value = psi(reference_features[feature], current_features[feature])
        reference_missing = float(reference_features[feature].isna().mean())
        current_missing = float(current_features[feature].isna().mean())
        missing_rate_diff = current_missing - reference_missing

        feature_results.append({
            "feature": feature,
            "psi": psi_value,
            "drift_level": classify_psi(psi_value),
            "reference_missing_rate": reference_missing,
            "current_missing_rate": current_missing,
            "missing_rate_diff": missing_rate_diff,
        })

    drifted_features = [
        row["feature"]
        for row in feature_results
        if row["drift_level"] in ["moderate", "major"] or abs(row["missing_rate_diff"]) >= 0.20
    ]
    feature_results = sorted(feature_results, key=lambda row: row["psi"], reverse=True)

    alerts = []
    major_count = sum(row["drift_level"] == "major" for row in feature_results)
    if major_count:
        alerts.append(f"{major_count} features have major PSI drift.")
    if len(current_features) < 30:
        alerts.append("Current production sample is small; interpret drift results cautiously.")

    report = {
        "status": "warning" if drifted_features else "stable",
        "drift_detected": bool(drifted_features),
        "reference_path": str(reference_path),
        "current_source": str(current_path) if current_path else "database:lab_events",
        "n_reference_rows": int(len(reference_features)),
        "n_current_rows": int(len(current_features)),
        "n_features_checked": len(feature_cols),
        "n_drifted_features": len(drifted_features),
        "drifted_features": drifted_features,
        "top_drifted_features": feature_results[:10],
        "feature_results": feature_results,
        "alerts": alerts,
    }

    write_json(output_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate a data drift report for AKI features.")
    parser.add_argument("--reference-path", default=str(DEFAULT_REFERENCE_PATH))
    parser.add_argument("--features-path", default=str(DEFAULT_FEATURES_PATH))
    parser.add_argument(
        "--current-path",
        default=None,
        help="Optional parquet/csv current data. If omitted, reads backend lab_events from the database.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--limit", type=int, default=None, help="Optional max rows when reading lab_events.")
    args = parser.parse_args()

    report = build_drift_report(
        reference_path=resolve_path(args.reference_path),
        features_path=resolve_path(args.features_path),
        current_path=resolve_path(args.current_path),
        output_path=resolve_path(args.output),
        limit=args.limit,
    )

    print("Drift report generated.")
    print(f"Status: {report['status']}")
    print(f"Current rows: {report['n_current_rows']}")
    print(f"Drifted features: {report['n_drifted_features']}")
    print(f"Saved to: {resolve_path(args.output)}")


if __name__ == "__main__":
    main()
