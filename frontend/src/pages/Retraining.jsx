import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function Retraining() {
  const [status, setStatus] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const loadStatus = async () => {
    setError("");

    try {
      const res = await apiClient.get("/retraining/status");
      setStatus(res.data);
    } catch (err) {
      console.error(err);
      setError("Không lấy được trạng thái retraining.");
    }
  };

  const triggerRetraining = async () => {
    setRunning(true);
    setError("");

    try {
      await apiClient.post("/retraining/trigger");
      await loadStatus();
    } catch (err) {
      console.error(err);
      setError("Retraining thất bại. Vui lòng kiểm tra backend log.");
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const summary = status?.last_training_summary;
  const model = status?.production_model;

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Model Lifecycle</p>
          <h1 className="page-title">Retraining</h1>
          <p className="page-desc">
            Kích hoạt lại pipeline huấn luyện LightGBM, đánh giá trên test set và cập
            nhật model registry.
          </p>
        </div>

        <button className="primary-btn" onClick={triggerRetraining} disabled={running}>
          {running ? "Đang chạy..." : "Chạy retraining"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="stat-grid">
        <Card title="Production model" value={model?.model_name || "LightGBM"} />
        <Card title="Version" value={model?.model_version || "-"} />
        <Card title="Threshold" value={model?.threshold ?? summary?.best_threshold ?? "-"} />
        <Card title="Registry records" value={status?.registry_count ?? "-"} />
      </div>

      {summary && (
        <>
          <h2 className="section-title">Kết quả lần train gần nhất</h2>
          <div className="stat-grid">
            <Card title="ROC-AUC" value={formatMetric(summary.test_metrics.roc_auc)} />
            <Card title="PR-AUC" value={formatMetric(summary.test_metrics.pr_auc)} />
            <Card title="Precision" value={formatMetric(summary.test_metrics.precision)} />
            <Card title="Recall" value={formatMetric(summary.test_metrics.recall)} />
            <Card title="F1-score" value={formatMetric(summary.test_metrics.f1_score)} />
            <Card title="Test rows" value={summary.test_shape?.[0]} />
            <Card title="Features" value={summary.feature_count} />
            <Card title="Positive rate" value={`${(summary.positive_rate_test * 100).toFixed(1)}%`} />
          </div>
        </>
      )}
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{title}</p>
      <p className="stat-value">{value ?? "-"}</p>
    </div>
  );
}

function formatMetric(value) {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(3);
}
