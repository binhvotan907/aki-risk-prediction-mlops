import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function Monitoring() {
  const [summary, setSummary] = useState(null);
  const [advanced, setAdvanced] = useState(null);
  const [recent, setRecent] = useState([]);
  const [error, setError] = useState("");

  const loadMonitoring = async () => {
    setError("");

    try {
      const summaryRes = await apiClient.get("/monitoring/summary");
      const advancedRes = await apiClient.get("/monitoring/advanced");
      const recentRes = await apiClient.get("/monitoring/recent?limit=20");

      setSummary(summaryRes.data);
      setAdvanced(advancedRes.data);
      setRecent(recentRes.data);
    } catch (err) {
      console.error(err);
      setError("Không lấy được dữ liệu giám sát. Vui lòng đăng nhập bằng tài khoản quản trị viên.");
    }
  };

  useEffect(() => {
    loadMonitoring();
  }, []);

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Quản trị hệ thống</p>
          <h1 className="page-title">Giám sát dự đoán</h1>
          <p className="page-desc">
            Theo dõi lịch sử dự đoán, phân bố mức nguy cơ và thời gian xử lý của
            hệ thống.
          </p>
        </div>

        <button className="primary-btn" onClick={loadMonitoring}>
          Làm mới
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {summary && (
        <>
          <div className="stat-grid">
            <Card title="Tổng lượt dự đoán" value={summary.total_predictions} />
            <Card title="Nguy cơ thấp" value={summary.low_risk} />
            <Card title="Nguy cơ trung bình" value={summary.medium_risk} />
            <Card title="Nguy cơ cao" value={summary.high_risk} />

            <Card
              title="Tỷ lệ nguy cơ cao"
              value={`${(summary.high_risk_rate * 100).toFixed(1)}%`}
            />

            <Card
              title="Xác suất trung bình"
              value={`${(summary.average_probability * 100).toFixed(1)}%`}
            />

            <Card
              title="Độ trễ trung bình"
              value={`${summary.average_latency_ms.toFixed(1)} ms`}
            />

            <Card
              title="Phiên bản mô hình"
              value={summary.current_model_version}
            />
          </div>

          {advanced && (
            <>
              <h2 className="section-title">Chỉ số vận hành nâng cao</h2>

              <div className="stat-grid">
                <Card
                  title="Latency p95"
                  value={`${advanced.latency.p95_ms.toFixed(1)} ms`}
                />
                <Card
                  title="Latency p99"
                  value={`${advanced.latency.p99_ms.toFixed(1)} ms`}
                />
                <Card
                  title="Missing feature TB"
                  value={advanced.missing_feature.average}
                />
                <Card
                  title="Missing feature max"
                  value={advanced.missing_feature.max}
                />
              </div>

              <div className="table-card">
                <h2 className="section-title" style={{ marginTop: 0 }}>
                  Xu hướng theo ngày
                </h2>

                <table>
                  <thead>
                    <tr>
                      <th>Ngày</th>
                      <th>Số dự đoán</th>
                      <th>Ca nguy cơ cao</th>
                      <th>Tỷ lệ nguy cơ cao</th>
                      <th>Xác suất TB</th>
                      <th>Latency TB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {advanced.daily_trend.map((row) => (
                      <tr key={row.date}>
                        <td>{row.date}</td>
                        <td>{row.total_predictions}</td>
                        <td>{row.high_risk}</td>
                        <td>{(row.high_risk_rate * 100).toFixed(1)}%</td>
                        <td>{(row.average_probability * 100).toFixed(1)}%</td>
                        <td>{row.average_latency_ms.toFixed(1)} ms</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          <div className="table-card">
            <h2 className="section-title" style={{ marginTop: 0 }}>
              Lịch sử dự đoán gần đây
            </h2>

            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Subject</th>
                  <th>Stay</th>
                  <th>Thời điểm xét nghiệm</th>
                  <th>Xác suất</th>
                  <th>Mức nguy cơ</th>
                  <th>Độ trễ</th>
                  <th>Người tạo</th>
                  <th>Thời điểm ghi nhận</th>
                </tr>
              </thead>

              <tbody>
                {recent.map((row) => (
                  <tr key={row.id}>
                    <td>{row.id}</td>
                    <td>{row.subject_id}</td>
                    <td>{row.stay_id}</td>
                    <td>{formatDateTime(row.charttime)}</td>
                    <td>{(row.aki_probability * 100).toFixed(2)}%</td>
                    <td>
                      <span className={getRiskClass(row.risk_level)}>
                        {row.risk_level}
                      </span>
                    </td>
                    <td>{row.latency_ms.toFixed(1)} ms</td>
                    <td>{row.created_by}</td>
                    <td>{formatDateTime(row.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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

function formatDateTime(value) {
  if (!value) return "-";

  return new Date(value).toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function getRiskClass(riskLevel) {
  if (riskLevel === "High") return "risk-high";
  if (riskLevel === "Medium") return "risk-medium";
  return "risk-low";
}
