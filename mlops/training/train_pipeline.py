import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from lightgbm import LGBMClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
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


def load_config(config_path: Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_feature_order(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_datasets(config: dict):
    data_cfg = config["data"]
    train_df = pd.read_parquet(resolve_path(data_cfg["train_path"]))
    val_df = pd.read_parquet(resolve_path(data_cfg["val_path"]))
    test_df = pd.read_parquet(resolve_path(data_cfg["test_path"]))
    feature_cols = load_feature_order(resolve_path(data_cfg["features_path"]))
    return train_df, val_df, test_df, feature_cols


def validate_columns(df: pd.DataFrame, feature_cols: list[str], target_col: str, name: str):
    missing = [c for c in feature_cols + [target_col] if c not in df.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def evaluate_threshold(y_true, y_prob, threshold: float) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    cm = confusion_matrix(y_true, y_pred)

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }


def threshold_values(config: dict) -> np.ndarray:
    cfg = config["threshold_tuning"]
    return np.round(
        np.arange(float(cfg["start"]), float(cfg["stop"]) + 1e-9, float(cfg["step"])),
        10,
    )


def log_to_mlflow(config: dict, metrics: dict, model_dir: Path, reports_dir: Path, summary: dict):
    mlflow_cfg = config.get("mlflow", {})
    if not mlflow_cfg.get("enabled", False):
        return {"enabled": False, "status": "disabled"}

    try:
        import mlflow
    except ImportError:
        return {
            "enabled": True,
            "status": "skipped",
            "reason": "mlflow package is not installed",
        }

    try:
        mlflow.set_tracking_uri(mlflow_cfg.get("tracking_uri", "http://localhost:5000"))
        mlflow.set_experiment(mlflow_cfg.get("experiment_name", "aki-risk-prediction"))

        with mlflow.start_run(run_name=mlflow_cfg.get("run_name")):
            mlflow.log_params({
                "model_name": config["model_name"],
                "model_version": config["model_version"],
                "random_state": config.get("random_state", 42),
                "feature_count": summary["feature_count"],
                "threshold_metric": summary["best_metric"],
                **{f"lightgbm_{k}": v for k, v in config["lightgbm"].items()},
            })

            mlflow.log_metrics({
                "best_threshold": metrics["threshold"],
                "val_f1": metrics["validation"]["f1_score"],
                "val_roc_auc": metrics["validation"]["roc_auc"],
                "val_pr_auc": metrics["validation"]["pr_auc"],
                "test_accuracy": metrics["test"]["accuracy"],
                "test_precision": metrics["test"]["precision"],
                "test_recall": metrics["test"]["recall"],
                "test_f1": metrics["test"]["f1_score"],
                "test_roc_auc": metrics["test"]["roc_auc"],
                "test_pr_auc": metrics["test"]["pr_auc"],
                "positive_rate_train": summary["positive_rate_train"],
                "positive_rate_val": summary["positive_rate_val"],
                "positive_rate_test": summary["positive_rate_test"],
            })

            model_artifacts = [
                model_dir / "lightgbm_model.pkl",
                model_dir / "lightgbm_imputer.pkl",
                model_dir / "lightgbm_feature_order.json",
                model_dir / "metrics.json",
                model_dir / "model_config.json",
            ]
            report_artifacts = [
                reports_dir / "lightgbm_threshold_tuning.csv",
                reports_dir / "lightgbm_feature_importance.csv",
                reports_dir / "training_summary.json",
            ]

            for artifact_path in model_artifacts:
                if artifact_path.exists():
                    mlflow.log_artifact(str(artifact_path), artifact_path="model")

            for artifact_path in report_artifacts:
                if artifact_path.exists():
                    mlflow.log_artifact(str(artifact_path), artifact_path="reports")

        return {"enabled": True, "status": "logged"}
    except Exception as exc:
        return {
            "enabled": True,
            "status": "failed",
            "reason": str(exc),
        }


def train(config: dict) -> dict:
    target_col = config.get("target_col", "label")
    random_state = int(config.get("random_state", 42))

    train_df, val_df, test_df, feature_cols = load_datasets(config)
    for name, df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        validate_columns(df, feature_cols, target_col, name)

    X_train = train_df[feature_cols].copy()
    y_train = train_df[target_col].copy()
    X_val = val_df[feature_cols].copy()
    y_val = val_df[target_col].copy()
    X_test = test_df[feature_cols].copy()
    y_test = test_df[target_col].copy()

    imputer = SimpleImputer(strategy="median")
    X_train_ready = imputer.fit_transform(X_train)
    X_val_ready = imputer.transform(X_val)
    X_test_ready = imputer.transform(X_test)

    lightgbm_cfg = dict(config["lightgbm"])
    model = LGBMClassifier(
        **lightgbm_cfg,
        random_state=random_state,
    )
    model.fit(X_train_ready, y_train)

    val_prob = model.predict_proba(X_val_ready)[:, 1]
    test_prob = model.predict_proba(X_test_ready)[:, 1]

    tuning_rows = [
        evaluate_threshold(y_val, val_prob, float(threshold))
        for threshold in threshold_values(config)
    ]
    tuning_df = pd.DataFrame(tuning_rows)
    metric_name = config["threshold_tuning"].get("metric", "f1_score")
    best_idx = tuning_df[metric_name].idxmax()
    best_threshold = float(tuning_df.loc[best_idx, "threshold"])

    val_metrics = evaluate_threshold(y_val, val_prob, best_threshold)
    test_metrics = evaluate_threshold(y_test, test_prob, best_threshold)

    model_dir = resolve_path(config["output"]["model_dir"])
    reports_dir = resolve_path(config["output"]["reports_dir"])
    model_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_dir / "lightgbm_model.pkl")
    joblib.dump(imputer, model_dir / "lightgbm_imputer.pkl")

    with open(model_dir / "lightgbm_feature_order.json", "w", encoding="utf-8") as f:
        json.dump(feature_cols, f, indent=2, ensure_ascii=False)

    metrics = {
        "model_name": config["model_name"],
        "version": config["model_version"],
        "threshold": best_threshold,
        "validation": val_metrics,
        "test": test_metrics,
        "test_accuracy": test_metrics["accuracy"],
        "test_precision": test_metrics["precision"],
        "test_recall": test_metrics["recall"],
        "test_f1": test_metrics["f1_score"],
        "test_roc_auc": test_metrics["roc_auc"],
        "test_pr_auc": test_metrics["pr_auc"],
    }

    model_config = {
        "model_name": config["model_name"],
        "version": config["model_version"],
        "threshold": best_threshold,
        "lookback_hours": 24,
        "prediction_horizon_hours": 24,
        "feature_count": len(feature_cols),
        "selected_model_reason": "Best overall ROC-AUC, PR-AUC and F1-score among tested models",
    }

    with open(model_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    with open(model_dir / "model_config.json", "w", encoding="utf-8") as f:
        json.dump(model_config, f, indent=2, ensure_ascii=False)

    tuning_df.to_csv(reports_dir / "lightgbm_threshold_tuning.csv", index=False)

    importance_df = pd.DataFrame(
        {
            "feature": feature_cols,
            "importance": model.feature_importances_,
        }
    ).sort_values("importance", ascending=False)
    importance_df.to_csv(reports_dir / "lightgbm_feature_importance.csv", index=False)

    summary = {
        "train_shape": list(train_df.shape),
        "val_shape": list(val_df.shape),
        "test_shape": list(test_df.shape),
        "feature_count": len(feature_cols),
        "positive_rate_train": float(y_train.mean()),
        "positive_rate_val": float(y_val.mean()),
        "positive_rate_test": float(y_test.mean()),
        "best_threshold": best_threshold,
        "best_metric": metric_name,
        "test_metrics": test_metrics,
        "model_dir": str(model_dir),
        "reports_dir": str(reports_dir),
    }

    summary["mlflow"] = {"enabled": config.get("mlflow", {}).get("enabled", False), "status": "pending"}

    with open(reports_dir / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    summary["mlflow"] = log_to_mlflow(
        config=config,
        metrics=metrics,
        model_dir=model_dir,
        reports_dir=reports_dir,
        summary=summary,
    )

    with open(reports_dir / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Train the LightGBM AKI risk model.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to model_config.yaml")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    summary = train(config)

    print("Training completed.")
    print(f"Best threshold: {summary['best_threshold']:.2f}")
    print("Test metrics:")
    for key, value in summary["test_metrics"].items():
        print(f"  {key}: {value}")
    print(f"Saved model artifacts to: {summary['model_dir']}")
    print(f"Saved reports to: {summary['reports_dir']}")


if __name__ == "__main__":
    main()
