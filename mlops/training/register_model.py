import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_MODEL_DIR = ROOT_DIR / "model" / "lightgbm"
DEFAULT_REGISTRY_PATH = ROOT_DIR / "model" / "model_registry.json"
DEFAULT_MLFLOW_TRACKING_URI = "http://localhost:5000"
DEFAULT_MLFLOW_MODEL_NAME = "AKI-LightGBM"


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def build_registry_record(model_dir: Path, status: str) -> dict:
    metrics = load_json(model_dir / "metrics.json")
    model_config = load_json(model_dir / "model_config.json")

    test_metrics = metrics.get("test", {})
    return {
        "model_name": model_config.get("model_name", metrics.get("model_name", "LightGBM")),
        "model_version": model_config.get("version", metrics.get("version", "unknown")),
        "model_type": "binary_classifier",
        "artifact_path": str(model_dir),
        "threshold": float(model_config.get("threshold", metrics.get("threshold", 0.7))),
        "roc_auc": test_metrics.get("roc_auc", metrics.get("test_roc_auc")),
        "pr_auc": test_metrics.get("pr_auc", metrics.get("test_pr_auc")),
        "precision": test_metrics.get("precision", metrics.get("test_precision")),
        "recall": test_metrics.get("recall", metrics.get("test_recall")),
        "f1": test_metrics.get("f1_score", metrics.get("test_f1")),
        "status": status,
    }


def register_to_file(record: dict, registry_path: Path):
    if registry_path.exists():
        registry = load_json(registry_path)
    else:
        registry = []

    registry = [
        r
        for r in registry
        if not (
            r.get("model_name") == record["model_name"]
            and r.get("model_version") == record["model_version"]
        )
    ]

    if record["status"] == "production":
        for item in registry:
            if item.get("model_name") == record["model_name"] and item.get("status") == "production":
                item["status"] = "archived"

    registry.append(record)
    write_json(registry_path, registry)
    return registry_path


def register_to_database(record: dict):
    sys.path.insert(0, str(BACKEND_DIR))

    from app.core.database import Base, SessionLocal, engine
    from app.models.model_version import ModelVersion

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if record["status"] == "production":
            existing_production = (
                db.query(ModelVersion)
                .filter(
                    ModelVersion.model_name == record["model_name"],
                    ModelVersion.status == "production",
                )
                .all()
            )
            for item in existing_production:
                item.status = "archived"

        existing = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.model_name == record["model_name"],
                ModelVersion.model_version == record["model_version"],
            )
            .first()
        )

        if existing:
            existing.model_type = record["model_type"]
            existing.artifact_path = record["artifact_path"]
            existing.threshold = record["threshold"]
            existing.roc_auc = record["roc_auc"]
            existing.pr_auc = record["pr_auc"]
            existing.precision = record["precision"]
            existing.recall = record["recall"]
            existing.f1 = record["f1"]
            existing.status = record["status"]
        else:
            db.add(ModelVersion(**record))

        db.commit()
    finally:
        db.close()


def register_to_mlflow(
    record: dict,
    model_dir: Path,
    tracking_uri: str = DEFAULT_MLFLOW_TRACKING_URI,
    registered_model_name: str = DEFAULT_MLFLOW_MODEL_NAME,
):
    try:
        import mlflow
        from mlflow.tracking import MlflowClient
    except ImportError as exc:
        raise RuntimeError("mlflow package is not installed") from exc

    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)

    try:
        client.get_registered_model(registered_model_name)
    except Exception:
        client.create_registered_model(
            registered_model_name,
            tags={
                "project": "aki-risk-mlops",
                "model_type": record["model_type"],
            },
            description="LightGBM model for real-time AKI risk prediction.",
        )

    with mlflow.start_run(run_name=f"register-{record['model_version']}") as run:
        mlflow.log_params({
            "model_name": record["model_name"],
            "model_version": record["model_version"],
            "model_type": record["model_type"],
            "threshold": record["threshold"],
            "registry_status": record["status"],
        })

        metric_values = {
            "roc_auc": record.get("roc_auc"),
            "pr_auc": record.get("pr_auc"),
            "precision": record.get("precision"),
            "recall": record.get("recall"),
            "f1": record.get("f1"),
        }
        mlflow.log_metrics({
            key: float(value)
            for key, value in metric_values.items()
            if value is not None
        })

        for artifact_name in [
            "lightgbm_model.pkl",
            "lightgbm_imputer.pkl",
            "lightgbm_feature_order.json",
            "metrics.json",
            "model_config.json",
        ]:
            artifact_path = model_dir / artifact_name
            if artifact_path.exists():
                mlflow.log_artifact(str(artifact_path), artifact_path="model")

        source = f"runs:/{run.info.run_id}/model"
        model_version = client.create_model_version(
            name=registered_model_name,
            source=source,
            run_id=run.info.run_id,
            tags={
                "status": record["status"],
                "threshold": str(record["threshold"]),
                "project": "aki-risk-mlops",
                "model_version": record["model_version"],
            },
            description=(
                f"{record['model_name']} {record['model_version']} "
                f"registered with status {record['status']}."
            ),
        )

        client.set_registered_model_tag(
            registered_model_name,
            "current_status",
            record["status"],
        )
        client.set_registered_model_tag(
            registered_model_name,
            "latest_project_version",
            record["model_version"],
        )

        return {
            "registered_model_name": registered_model_name,
            "mlflow_model_version": model_version.version,
            "run_id": run.info.run_id,
            "tracking_uri": tracking_uri,
        }


def main():
    parser = argparse.ArgumentParser(description="Register a trained model version.")
    parser.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR), help="Directory containing model artifacts")
    parser.add_argument(
        "--status",
        default="production",
        choices=["staging", "production", "archived"],
        help="Model registry status",
    )
    parser.add_argument(
        "--backend",
        choices=["file", "database", "mlflow", "both"],
        default="file",
        help="Registry backend. Use mlflow or both to create a MLflow Registered Model.",
    )
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH), help="JSON registry path")
    parser.add_argument("--mlflow-tracking-uri", default=DEFAULT_MLFLOW_TRACKING_URI)
    parser.add_argument("--mlflow-model-name", default=DEFAULT_MLFLOW_MODEL_NAME)
    args = parser.parse_args()

    model_dir = Path(args.model_dir)
    record = build_registry_record(model_dir, args.status)

    if args.backend == "database":
        register_to_database(record)
        print("Registered model to database.")
    elif args.backend == "mlflow":
        mlflow_result = register_to_mlflow(
            record=record,
            model_dir=model_dir,
            tracking_uri=args.mlflow_tracking_uri,
            registered_model_name=args.mlflow_model_name,
        )
        print("Registered model to MLflow Model Registry.")
        print(json.dumps(mlflow_result, indent=2, ensure_ascii=False))
    elif args.backend == "both":
        path = register_to_file(record, Path(args.registry_path))
        mlflow_result = register_to_mlflow(
            record=record,
            model_dir=model_dir,
            tracking_uri=args.mlflow_tracking_uri,
            registered_model_name=args.mlflow_model_name,
        )
        print(f"Registered model to file registry: {path}")
        print("Registered model to MLflow Model Registry.")
        print(json.dumps(mlflow_result, indent=2, ensure_ascii=False))
    else:
        path = register_to_file(record, Path(args.registry_path))
        print(f"Registered model to file registry: {path}")

    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
