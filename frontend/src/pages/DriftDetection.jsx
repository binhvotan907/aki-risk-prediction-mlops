import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function DriftDetection() {
  const [drift, setDrift] = useState(null);
  const [error, setError] = useState("");

  const loadDrift = async () => {
    setError("");

    try {
      const res = await apiClient.get("/monitoring/drift");
      setDrift(res.data);
    } catch (err) {
      console.error(err);
      setError("Không lấy được trạng thái drift.");
    }
  };

  useEffect(() => {
    loadDrift();
  }, []);

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">MLOps Monitoring</p>
          <h1 className="page-title">Drift Detection</h1>
          <p className="page-desc">
            Theo dõi thay đổi trong phân phối dự đoán, tỷ lệ cảnh báo và mức thiếu
            feature của dữ liệu production.
          </p>
        </div>

        <button className="primary-btn" onClick={loadDrift}>
          Làm mới
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {drift && (
        <>
          <div className={`status-strip ${drift.drift_detected ? "danger" : "ok"}`}>
            <div>
              <p className="status-title">
                {drift.drift_detected ? "Có tín hiệu drift" : "Chưa phát hiện drift"}
              </p>
              <p className="status-text">
                Trạng thái: <b>{drift.status}</b>
              </p>
            </div>
          </div>

          <div className="stat-grid">
            <Card title="Số prediction" value={drift.total_predictions} />
            <Card
              title="High-risk hiện tại"
              value={`${(drift.current_high_risk_rate * 100).toFixed(1)}%`}
            />
            <Card
              title="Reference AKI"
              value={`${(drift.reference_positive_rate * 100).toFixed(1)}%`}
            />
            <Card
              title="Missing feature TB"
              value={drift.missing_feature_average}
            />
          </div>

          <div className="table-card">
            <h2 className="section-title" style={{ marginTop: 0 }}>
              Tín hiệu kiểm tra
            </h2>
            <table>
              <thead>
                <tr>
                  <th>Tín hiệu</th>
                  <th>Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {drift.checked_signals.map((signal) => (
                  <tr key={signal}>
                    <td>{signal}</td>
                    <td>
                      <span className={drift.drift_detected ? "risk-medium" : "risk-low"}>
                        checked
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {drift.alerts.length > 0 && (
            <div className="info-box warning">
              {drift.alerts.map((alert) => (
                <p key={alert}>{alert}</p>
              ))}
            </div>
          )}
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
