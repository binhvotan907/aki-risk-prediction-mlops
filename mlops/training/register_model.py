import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
DEFAULT_MODEL_DIR = ROOT_DIR / "model" / "lightgbm"
DEFAULT_REGISTRY_PATH = ROOT_DIR / "model" / "model_registry.json"


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
        choices=["file", "database"],
        default="file",
        help="Registry backend. File is simplest for offline MLOps reports.",
    )
    parser.add_argument("--registry-path", default=str(DEFAULT_REGISTRY_PATH), help="JSON registry path")
    args = parser.parse_args()

    record = build_registry_record(Path(args.model_dir), args.status)

    if args.backend == "database":
        register_to_database(record)
        print("Registered model to database.")
    else:
        path = register_to_file(record, Path(args.registry_path))
        print(f"Registered model to file registry: {path}")

    print(json.dumps(record, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
