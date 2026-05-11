import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";
import apiClient from "../api/client";

function getApiErrorMessage(err) {
  if (err?.response?.status === 403) {
    return "Bạn chưa được phân công bệnh nhân này. Vui lòng liên hệ quản trị viên để được cấp quyền.";
  }

  return "Không tải được dữ liệu bệnh nhân. Vui lòng kiểm tra mã bệnh nhân hoặc máy chủ.";
}

export default function PatientTimeline() {
  const [searchParams] = useSearchParams();
  const [subjectId, setSubjectId] = useState(
    searchParams.get("subject_id") || "10001"
  );
  const [stayId, setStayId] = useState(searchParams.get("stay_id") || "30001");
  const [timeline, setTimeline] = useState([]);
  const [loadedPatient, setLoadedPatient] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadTimeline = async () => {
    setError("");
    setLoading(true);
    setTimeline([]);
    setLoadedPatient(null);

    try {
      const res = await apiClient.get(
        `/patients/${subjectId}/${stayId}/timeline`
      );

      const formatted = res.data.timeline.map((row) => ({
        ...row,
        time: formatCharttime(row.charttime),
        aki_percent:
          row.aki_probability !== null
            ? Number((row.aki_probability * 100).toFixed(2))
            : null,
      }));

      setTimeline(formatted);
      setLoadedPatient({
        subject_id: res.data.subject_id,
        stay_id: res.data.stay_id,
      });
    } catch (err) {
      console.error(err);
      setError(getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const exportCsv = () => {
    if (timeline.length === 0) return;

    const columns = [
      "charttime",
      "creatinine",
      "bun",
      "bicarbonate",
      "phosphate",
      "anion_gap",
      "aki_probability",
      "risk_level",
    ];

    const csvRows = [
      columns.join(","),
      ...timeline.map((row) =>
        columns
          .map((col) => {
            const value = row[col] ?? "";
            return `"${String(value).replaceAll('"', '""')}"`;
          })
          .join(",")
      ),
    ];

    const blob = new Blob([csvRows.join("\n")], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `patient_${loadedPatient.subject_id}_${loadedPatient.stay_id}_timeline.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const latest = timeline[timeline.length - 1];

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Theo dõi bệnh nhân</p>
          <h1 className="page-title">Dữ liệu và timeline bệnh nhân</h1>
          <p className="page-desc">
            Bác sĩ và quản trị viên có thể tải dữ liệu theo `subject_id` và
            `stay_id` để xem xét nghiệm, xác suất nguy cơ và diễn biến theo thời gian.
          </p>
        </div>
      </div>

      <div className="query-panel">
        <Input label="subject_id" value={subjectId} onChange={setSubjectId} />
        <Input label="stay_id" value={stayId} onChange={setStayId} />

        <button className="primary-btn" onClick={loadTimeline} disabled={loading}>
          {loading ? "Đang tải..." : "Tải dữ liệu bệnh nhân"}
        </button>

        <button
          className="secondary-btn"
          onClick={exportCsv}
          disabled={timeline.length === 0}
        >
          Xuất CSV
        </button>
      </div>

      {error && <div className="error-box" style={{ marginTop: 20 }}>{error}</div>}

      {!loading && !error && timeline.length === 0 && (
        <div className="empty-state">
          <p className="empty-title">Chưa có dữ liệu được tải</p>
          <p>
            Nhập `subject_id` và `stay_id`, sau đó bấm tải dữ liệu để xem timeline
            của bệnh nhân. Dữ liệu sẽ xuất hiện sau khi bệnh nhân có ít nhất một lần
            dự đoán trong hệ thống.
          </p>
        </div>
      )}

      {timeline.length > 0 && (
        <>
          <div className="status-strip">
            <div>
              <p className="status-title">
                Patient {loadedPatient.subject_id} · Stay {loadedPatient.stay_id}
              </p>
              <p className="status-text">
                Đã tải {timeline.length} bản ghi xét nghiệm và dự đoán.
              </p>
            </div>
          </div>

          <div className="stat-grid">
            <Card title="Số bản ghi" value={timeline.length} />
            <Card title="Nguy cơ mới nhất" value={latest.risk_level || "-"} />
            <Card
              title="Xác suất mới nhất"
              value={latest.aki_percent !== null ? `${latest.aki_percent}%` : "-"}
            />
            <Card title="Creatinine mới nhất" value={latest.creatinine ?? "-"} />
          </div>

          <div className="table-card">
            <h2 className="section-title" style={{ marginTop: 0 }}>
              Xác suất nguy cơ theo thời gian
            </h2>

            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="aki_percent"
                    name="Xác suất nguy cơ (%)"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="table-card">
            <h2 className="section-title" style={{ marginTop: 0 }}>
              Creatinine và BUN theo thời gian
            </h2>

            <div style={{ width: "100%", height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="creatinine"
                    name="Creatinine"
                    stroke="#dc2626"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="bun"
                    name="BUN"
                    stroke="#16a34a"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="table-card">
            <h2 className="section-title" style={{ marginTop: 0 }}>
              Bảng dữ liệu chi tiết
            </h2>

            <table>
              <thead>
                <tr>
                  <th>Thời điểm</th>
                  <th>Creatinine</th>
                  <th>BUN</th>
                  <th>Bicarbonate</th>
                  <th>Phosphate</th>
                  <th>Anion Gap</th>
                  <th>Xác suất</th>
                  <th>Mức nguy cơ</th>
                </tr>
              </thead>
              <tbody>
                {timeline.map((row, index) => (
                  <tr key={`${row.charttime}-${index}`}>
                    <td>{row.time}</td>
                    <td>{row.creatinine ?? "-"}</td>
                    <td>{row.bun ?? "-"}</td>
                    <td>{row.bicarbonate ?? "-"}</td>
                    <td>{row.phosphate ?? "-"}</td>
                    <td>{row.anion_gap ?? "-"}</td>
                    <td>{row.aki_percent !== null ? `${row.aki_percent}%` : "-"}</td>
                    <td>
                      <span className={getRiskClass(row.risk_level)}>
                        {row.risk_level || "-"}
                      </span>
                    </td>
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

function Input({ label, value, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{title}</p>
      <p className="stat-value">{value}</p>
    </div>
  );
}

function getRiskClass(riskLevel) {
  if (riskLevel === "High") return "risk-high";
  if (riskLevel === "Medium") return "risk-medium";
  if (riskLevel === "Low") return "risk-low";
  return "";
}

function formatCharttime(value) {
  if (!value) return "-";

  const match = String(value).match(
    /^(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})/
  );

  if (!match) return String(value);

  const [, , month, day, hour, minute] = match;
  return `${hour}:${minute} ${day}-${month}`;
}
