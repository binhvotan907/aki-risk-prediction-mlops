import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from drift_report import load_current_features, load_json, resolve_path


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_PATH = ROOT_DIR / "data" / "train_dataset_final.parquet"
DEFAULT_FEATURES_PATH = ROOT_DIR / "data" / "features_dataset_final.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "reports" / "evidently_drift_report.html"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def build_evidently_report(
    reference_path: Path,
    features_path: Path,
    current_path: Path | None,
    output_path: Path,
    reference_sample: int,
    current_limit: int | None,
):
    try:
        from evidently.legacy.metric_preset import DataDriftPreset
        from evidently.legacy.pipeline.column_mapping import ColumnMapping
        from evidently.legacy.report import Report
    except ImportError as exc:
        raise RuntimeError(
            "Evidently is not installed. Install it with: pip install evidently"
        ) from exc

    feature_cols = load_json(features_path)
    reference_df = pd.read_parquet(reference_path, columns=feature_cols)

    if reference_sample and len(reference_df) > reference_sample:
        reference_df = reference_df.sample(reference_sample, random_state=42)

    current_df = load_current_features(
        feature_cols=feature_cols,
        current_path=current_path,
        limit=current_limit,
    )

    if current_df.empty:
        raise ValueError(
            "No current production data is available. Run a few predictions first, "
            "or pass --current-path with a parquet/csv file."
        )

    column_mapping = ColumnMapping(
        numerical_features=feature_cols,
        categorical_features=[],
        target=None,
        prediction=None,
    )

    report = Report(metrics=[DataDriftPreset()])
    report.run(
        reference_data=reference_df,
        current_data=current_df[feature_cols],
        column_mapping=column_mapping,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.save_html(str(output_path))

    json_output = output_path.with_suffix(".json")
    try:
        report_json = json.loads(report.json())
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(report_json, f, indent=2, ensure_ascii=False)
    except Exception:
        json_output = None

    return {
        "reference_rows": int(len(reference_df)),
        "current_rows": int(len(current_df)),
        "feature_count": len(feature_cols),
        "html_report": str(output_path),
        "json_report": str(json_output) if json_output else None,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate an Evidently HTML drift report for AKI feature data."
    )
    parser.add_argument("--reference-path", default=str(DEFAULT_REFERENCE_PATH))
    parser.add_argument("--features-path", default=str(DEFAULT_FEATURES_PATH))
    parser.add_argument(
        "--current-path",
        default=None,
        help="Optional parquet/csv current data. If omitted, reads backend lab_events from the database.",
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--reference-sample",
        type=int,
        default=5000,
        help="Sample size from reference data to keep report generation fast.",
    )
    parser.add_argument(
        "--current-limit",
        type=int,
        default=None,
        help="Optional max rows when reading current lab_events from the database.",
    )
    args = parser.parse_args()

    result = build_evidently_report(
        reference_path=resolve_path(args.reference_path),
        features_path=resolve_path(args.features_path),
        current_path=resolve_path(args.current_path),
        output_path=resolve_path(args.output),
        reference_sample=args.reference_sample,
        current_limit=args.current_limit,
    )

    print("Evidently drift report generated.")
    print(f"Reference rows: {result['reference_rows']}")
    print(f"Current rows: {result['current_rows']}")
    print(f"Features: {result['feature_count']}")
    print(f"HTML report: {result['html_report']}")
    if result["json_report"]:
        print(f"JSON report: {result['json_report']}")


if __name__ == "__main__":
    main()
