import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
import yaml
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT_DIR / "mlops" / "configs" / "model_config.yaml"


def resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return ROOT_DIR / path


def load_config(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_model(config: dict, model_dir: Path | None = None, output_path: Path | None = None) -> dict:
    target_col = config.get("target_col", "label")
    data_cfg = config["data"]
    model_dir = model_dir or resolve_path(config["output"]["model_dir"])
    reports_dir = resolve_path(config["output"]["reports_dir"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path or reports_dir / "evaluation_report.json"

    test_df = pd.read_parquet(resolve_path(data_cfg["test_path"]))
    feature_cols = load_json(resolve_path(data_cfg["features_path"]))
    model_config = load_json(model_dir / "model_config.json")

    missing = [c for c in feature_cols + [target_col] if c not in test_df.columns]
    if missing:
        raise ValueError(f"Test dataset is missing required columns: {missing}")

    model = joblib.load(model_dir / "lightgbm_model.pkl")
    imputer = joblib.load(model_dir / "lightgbm_imputer.pkl")

    X_test = test_df[feature_cols].copy()
    y_test = test_df[target_col].copy()
    X_test_ready = imputer.transform(X_test)

    threshold = float(model_config.get("threshold", 0.7))
    y_prob = model.predict_proba(X_test_ready)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_test, y_pred)

    report = {
        "model_name": model_config.get("model_name", "LightGBM"),
        "model_version": model_config.get("version", "unknown"),
        "threshold": threshold,
        "test_shape": list(test_df.shape),
        "feature_count": len(feature_cols),
        "metrics": {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1_score": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_prob)),
            "pr_auc": float(average_precision_score(y_test, y_prob)),
        },
        "confusion_matrix": {
            "tn": int(cm[0, 0]),
            "fp": int(cm[0, 1]),
            "fn": int(cm[1, 0]),
            "tp": int(cm[1, 1]),
        },
        "classification_report": classification_report(
            y_test,
            y_pred,
            output_dict=True,
            zero_division=0,
        ),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    pd.DataFrame(cm, index=["true_0", "true_1"], columns=["pred_0", "pred_1"]).to_csv(
        reports_dir / "confusion_matrix.csv"
    )

    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate the trained LightGBM AKI model.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to model_config.yaml")
    parser.add_argument("--model-dir", default=None, help="Directory containing model artifacts")
    parser.add_argument("--output", default=None, help="Output evaluation report path")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    report = evaluate_model(
        config=config,
        model_dir=Path(args.model_dir) if args.model_dir else None,
        output_path=Path(args.output) if args.output else None,
    )

    print("Evaluation completed.")
    print(f"Model: {report['model_name']} {report['model_version']}")
    print(f"Threshold: {report['threshold']}")
    print("Metrics:")
    for key, value in report["metrics"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
