from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from collections import defaultdict

from app.core.database import get_db
from app.core.security import require_admin
from app.models.user import User
from app.models.prediction_log import PredictionLog


router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


def percentile(values: list[float], q: float):
    clean_values = sorted(v for v in values if v is not None)
    if not clean_values:
        return 0

    index = (len(clean_values) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(clean_values) - 1)
    weight = index - lower
    return clean_values[lower] * (1 - weight) + clean_values[upper] * weight


@router.get("/summary")
def monitoring_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total = db.query(PredictionLog).count()

    if total == 0:
        return {
            "total_predictions": 0,
            "low_risk": 0,
            "medium_risk": 0,
            "high_risk": 0,
            "high_risk_rate": 0,
            "average_probability": 0,
            "average_latency_ms": 0
        }

    low = db.query(PredictionLog).filter(PredictionLog.risk_level == "Low").count()
    medium = db.query(PredictionLog).filter(PredictionLog.risk_level == "Medium").count()
    high = db.query(PredictionLog).filter(PredictionLog.risk_level == "High").count()

    avg_prob = db.query(func.avg(PredictionLog.aki_probability)).scalar() or 0
    avg_latency = db.query(func.avg(PredictionLog.latency_ms)).scalar() or 0

    latest = (
        db.query(PredictionLog)
        .order_by(PredictionLog.created_at.desc())
        .first()
    )

    return {
        "total_predictions": total,
        "low_risk": low,
        "medium_risk": medium,
        "high_risk": high,
        "high_risk_rate": round(high / total, 4),
        "average_probability": round(float(avg_prob), 4),
        "average_latency_ms": round(float(avg_latency), 2),
        "last_prediction_time": latest.created_at if latest else None,
        "current_model_version": latest.model_version if latest else None
    }


@router.get("/advanced")
def advanced_monitoring(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    rows = (
        db.query(PredictionLog)
        .order_by(PredictionLog.created_at.asc())
        .all()
    )

    if not rows:
        return {
            "total_predictions": 0,
            "latency": {
                "average_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0,
            },
            "missing_feature": {
                "average": 0,
                "max": 0,
            },
            "risk_distribution": [],
            "model_version_distribution": [],
            "daily_trend": [],
        }

    latencies = [row.latency_ms for row in rows if row.latency_ms is not None]
    missing_counts = [
        row.missing_feature_count
        for row in rows
        if row.missing_feature_count is not None
    ]

    risk_counts = defaultdict(int)
    version_counts = defaultdict(int)
    daily = defaultdict(lambda: {
        "date": None,
        "total_predictions": 0,
        "high_risk": 0,
        "average_probability_sum": 0.0,
        "average_latency_sum": 0.0,
        "latency_count": 0,
    })

    for row in rows:
        risk_counts[row.risk_level] += 1
        version_counts[row.model_version] += 1

        date_key = row.created_at.date().isoformat() if row.created_at else "unknown"
        daily_row = daily[date_key]
        daily_row["date"] = date_key
        daily_row["total_predictions"] += 1
        daily_row["average_probability_sum"] += row.aki_probability
        if row.risk_level == "High":
            daily_row["high_risk"] += 1
        if row.latency_ms is not None:
            daily_row["average_latency_sum"] += row.latency_ms
            daily_row["latency_count"] += 1

    daily_trend = []
    for item in daily.values():
        total = item["total_predictions"]
        latency_count = item["latency_count"]
        daily_trend.append({
            "date": item["date"],
            "total_predictions": total,
            "high_risk": item["high_risk"],
            "high_risk_rate": round(item["high_risk"] / total, 4) if total else 0,
            "average_probability": round(item["average_probability_sum"] / total, 4) if total else 0,
            "average_latency_ms": round(item["average_latency_sum"] / latency_count, 2) if latency_count else 0,
        })

    return {
        "total_predictions": len(rows),
        "latency": {
            "average_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "p95_ms": round(percentile(latencies, 0.95), 2),
            "p99_ms": round(percentile(latencies, 0.99), 2),
        },
        "missing_feature": {
            "average": round(sum(missing_counts) / len(missing_counts), 2) if missing_counts else 0,
            "max": max(missing_counts) if missing_counts else 0,
        },
        "risk_distribution": [
            {"risk_level": risk, "count": count}
            for risk, count in sorted(risk_counts.items())
        ],
        "model_version_distribution": [
            {"model_version": version, "count": count}
            for version, count in sorted(version_counts.items())
        ],
        "daily_trend": sorted(daily_trend, key=lambda item: item["date"]),
    }


@router.get("/recent")
def recent_predictions(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    rows = (
        db.query(PredictionLog)
        .order_by(PredictionLog.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": r.id,
            "subject_id": r.subject_id,
            "stay_id": r.stay_id,
            "charttime": r.charttime,
            "aki_probability": round(r.aki_probability, 4),
            "risk_level": r.risk_level,
            "model_version": r.model_version,
            "latency_ms": r.latency_ms,
            "created_by": r.created_by,
            "created_at": r.created_at
        }
        for r in rows
    ]


@router.get("/drift")
def drift_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total = db.query(PredictionLog).count()

    if total == 0:
        return {
            "status": "insufficient_data",
            "drift_detected": False,
            "total_predictions": 0,
            "reference_positive_rate": 0.1194,
            "current_high_risk_rate": 0,
            "average_probability": 0,
            "missing_feature_average": 0,
            "checked_signals": [
                "prediction_volume",
                "high_risk_rate",
                "average_probability",
                "missing_feature_count"
            ],
            "alerts": []
        }

    high = db.query(PredictionLog).filter(PredictionLog.risk_level == "High").count()
    avg_prob = db.query(func.avg(PredictionLog.aki_probability)).scalar() or 0
    avg_missing = db.query(func.avg(PredictionLog.missing_feature_count)).scalar() or 0

    high_risk_rate = high / total
    alerts = []

    if total < 30:
        alerts.append("Cần thêm dữ liệu production để kết luận drift ổn định.")

    if abs(high_risk_rate - 0.1194) > 0.15:
        alerts.append("Tỷ lệ cảnh báo nguy cơ cao lệch đáng kể so với test set.")

    if float(avg_missing) > 10:
        alerts.append("Số feature thiếu trung bình cao.")

    drift_detected = any("lệch" in alert or "thiếu" in alert for alert in alerts)

    return {
        "status": "warning" if drift_detected else "stable",
        "drift_detected": drift_detected,
        "total_predictions": total,
        "reference_positive_rate": 0.1194,
        "current_high_risk_rate": round(high_risk_rate, 4),
        "average_probability": round(float(avg_prob), 4),
        "missing_feature_average": round(float(avg_missing), 2),
        "checked_signals": [
            "prediction_volume",
            "high_risk_rate",
            "average_probability",
            "missing_feature_count"
        ],
        "alerts": alerts
    }
