import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import require_admin
from app.models.user import User

'''
Cho phép admin kích hoạt huấn luyện lại model, 
đánh giá candidate model 
và promote nếu kết quả đạt yêu cầu.
'''

router = APIRouter(prefix="/retraining", tags=["Retraining"])

ROOT_DIR = Path(__file__).resolve().parents[3]
REPORTS_DIR = ROOT_DIR / "reports"
TRAINING_SUMMARY_PATH = REPORTS_DIR / "training_summary.json"
REGISTRY_PATH = ROOT_DIR / "model" / "model_registry.json"
MODEL_CONFIG_PATH = ROOT_DIR / "mlops" / "configs" / "model_config.yaml"
PRODUCTION_MODEL_DIR = ROOT_DIR / "model" / "lightgbm"
PROMOTION_METRICS = ["f1", "pr_auc"]
MIN_PRODUCTION_RETRAINING_SAMPLES = 30


def read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def write_yaml(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def read_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def current_production_model():
    registry = read_json(REGISTRY_PATH) or []
    return next(
        (item for item in reversed(registry) if item.get("status") == "production"),
        None,
    )


def should_promote(candidate_summary: dict, production_model: dict | None) -> tuple[bool, dict]:
    candidate_metrics = candidate_summary.get("test_metrics", {})
    candidate = {
        "f1": candidate_metrics.get("f1_score"),
        "pr_auc": candidate_metrics.get("pr_auc"),
    }

    if not production_model:
        return True, {
            "decision": "promote",
            "reason": "No production model exists",
            "candidate": candidate,
            "production": None,
        }

    production = {
        "f1": production_model.get("f1"),
        "pr_auc": production_model.get("pr_auc"),
    }

    passed = all(
        candidate.get(metric) is not None
        and production.get(metric) is not None
        and candidate[metric] >= production[metric]
        for metric in PROMOTION_METRICS
    )

    return passed, {
        "decision": "promote" if passed else "keep_current_production",
        "rule": "candidate f1 and pr_auc must be greater than or equal to production",
        "candidate": candidate,
        "production": production,
    }


def copy_candidate_to_production(candidate_model_dir: Path):
    PRODUCTION_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for file_name in [
        "lightgbm_model.pkl",
        "lightgbm_imputer.pkl",
        "lightgbm_feature_order.json",
        "metrics.json",
        "model_config.json",
    ]:
        shutil.copy2(candidate_model_dir / file_name, PRODUCTION_MODEL_DIR / file_name)


@router.get("/status")
def retraining_status(current_user: User = Depends(require_admin)):
    summary = read_json(TRAINING_SUMMARY_PATH)
    registry = read_json(REGISTRY_PATH) or []
    production_model = current_production_model()

    return {
        "last_training_summary": summary,
        "production_model": production_model,
        "registry_count": len(registry),
    }


@router.post("/trigger")
def trigger_retraining(current_user: User = Depends(require_admin)):
    started_at_dt = datetime.utcnow()
    started_at = started_at_dt.isoformat()
    run_id = started_at_dt.strftime("%Y%m%d%H%M%S")
    candidate_model_dir = ROOT_DIR / "model" / "candidates" / f"lightgbm_{run_id}"
    candidate_reports_dir = REPORTS_DIR / "candidates" / f"lightgbm_{run_id}"
    candidate_config_path = ROOT_DIR / "mlops" / "configs" / f"candidate_{run_id}.yaml"
    production_dataset_dir = ROOT_DIR / "data" / "retraining" / f"lightgbm_{run_id}"
    production_dataset_summary_path = candidate_reports_dir / "production_dataset_summary.json"

    config = read_yaml(MODEL_CONFIG_PATH)
    config["model_version"] = f"{config.get('model_version', 'v1.0.0')}-{run_id}"
    config["output"]["model_dir"] = str(candidate_model_dir.relative_to(ROOT_DIR))
    config["output"]["reports_dir"] = str(candidate_reports_dir.relative_to(ROOT_DIR))
    if config.get("mlflow"):
        config["mlflow"]["run_name"] = f"retraining-{run_id}"
    write_yaml(candidate_config_path, config)

    dataset_result = subprocess.run(
        [
            sys.executable,
            "mlops/training/build_dataset_from_postgres.py",
            "--config",
            str(candidate_config_path),
            "--output-dir",
            str(production_dataset_dir.relative_to(ROOT_DIR)),
            "--summary",
            str(production_dataset_summary_path.relative_to(ROOT_DIR)),
            "--min-samples",
            str(MIN_PRODUCTION_RETRAINING_SAMPLES),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )

    if dataset_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Building production retraining dataset failed",
                "stdout": dataset_result.stdout,
                "stderr": dataset_result.stderr,
            },
        )

    production_dataset_summary = read_json(production_dataset_summary_path) or {}
    if production_dataset_summary.get("used_for_training"):
        config["data"]["train_path"] = str(
            Path(production_dataset_summary["augmented_train_path"]).relative_to(ROOT_DIR)
        )
        write_yaml(candidate_config_path, config)

    train_result = subprocess.run(
        [
            sys.executable,
            "mlops/training/train_pipeline.py",
            "--config",
            str(candidate_config_path),
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )

    if train_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Retraining failed",
                "stdout": train_result.stdout,
                "stderr": train_result.stderr,
            },
        )

    candidate_summary = read_json(candidate_reports_dir / "training_summary.json")
    if candidate_summary:
        candidate_summary["candidate_model_dir"] = str(candidate_model_dir)
        candidate_summary["candidate_reports_dir"] = str(candidate_reports_dir)
        candidate_summary["production_dataset"] = production_dataset_summary
        candidate_summary["trained_at"] = datetime.utcnow().isoformat()
        write_json(TRAINING_SUMMARY_PATH, candidate_summary)

    production_model = current_production_model()
    promote, promotion_report = should_promote(candidate_summary or {}, production_model)

    if not promote:
        register_result = subprocess.run(
            [
                sys.executable,
                "mlops/training/register_model.py",
                "--model-dir",
                str(candidate_model_dir),
                "--backend",
                "file",
                "--status",
                "staging",
            ],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if register_result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Candidate model staging registration failed",
                    "stdout": register_result.stdout,
                    "stderr": register_result.stderr,
                },
            )

        return {
            "status": "completed_not_promoted",
            "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "candidate_model_dir": str(candidate_model_dir),
            "training_summary": candidate_summary,
            "production_dataset": production_dataset_summary,
            "promotion": promotion_report,
        }

    copy_candidate_to_production(candidate_model_dir)

    register_result = subprocess.run(
        [
            sys.executable,
            "mlops/training/register_model.py",
            "--model-dir",
            str(PRODUCTION_MODEL_DIR),
            "--backend",
            "file",
            "--status",
            "production",
        ],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )

    if register_result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Model registration failed",
                "stdout": register_result.stdout,
                "stderr": register_result.stderr,
            },
        )

    return {
        "status": "completed_promoted",
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat(),
        "candidate_model_dir": str(candidate_model_dir),
        "training_summary": candidate_summary,
        "production_dataset": production_dataset_summary,
        "promotion": promotion_report,
    }
