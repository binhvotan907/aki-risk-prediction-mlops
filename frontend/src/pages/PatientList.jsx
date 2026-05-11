import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/client";

export default function PatientList() {
  const [patients, setPatients] = useState([]);
  const [search, setSearch] = useState("");
  const [patientForm, setPatientForm] = useState({
    subject_id: "",
    stay_id: "",
    gender: "male",
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const role = localStorage.getItem("role") || "doctor";

  const loadPatients = async () => {
    setError("");
    setLoading(true);

    try {
      const res = await apiClient.get("/patients");
      setPatients(res.data);
    } catch (err) {
      console.error(err);
      setError("Không tải được danh sách bệnh nhân. Vui lòng kiểm tra máy chủ.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPatients();
  }, []);

  const filteredPatients = useMemo(() => {
    const keyword = search.trim().toLowerCase();

    if (!keyword) return patients;

    return patients.filter((patient) => {
      return [
        patient.subject_id,
        patient.stay_id,
        patient.doctor_username,
        patient.latest_risk_level,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword));
    });
  }, [patients, search]);

  const highRiskCount = patients.filter(
    (patient) => patient.latest_risk_level === "High"
  ).length;
  const activeCount = patients.filter((patient) => patient.lab_event_count > 0).length;

  const createPatient = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!patientForm.subject_id || !patientForm.stay_id) {
      setError("Vui lòng nhập subject_id và stay_id.");
      return;
    }

    try {
      await apiClient.post("/patients", {
        subject_id: Number(patientForm.subject_id),
        stay_id: Number(patientForm.stay_id),
        gender: patientForm.gender || null,
      });
      setMessage("Đã thêm bệnh nhân vào hệ thống.");
      setPatientForm({ subject_id: "", stay_id: "", gender: "male" });
      await loadPatients();
    } catch (err) {
      console.error(err);
      setError("Không thể thêm bệnh nhân. Cặp subject_id/stay_id có thể đã tồn tại.");
    }
  };

  const deletePatient = async (patient) => {
    setError("");
    setMessage("");

    const subjectId = Number(patient.subject_id);
    const stayId = Number(patient.stay_id);

    const confirmed = window.confirm(
      `Xóa bệnh nhân ${subjectId}/${stayId} khỏi danh sách? Thao tác này sẽ xóa phân công, dữ liệu xét nghiệm và lịch sử dự đoán.`
    );

    if (!confirmed) return;

    try {
      const res = await apiClient.delete(`/patients/${subjectId}/${stayId}`);
      setMessage(
        `Đã xóa bệnh nhân ${subjectId}/${stayId}: ${res.data.deleted_patients} hồ sơ, ${res.data.deleted_assignments} phân công, ${res.data.deleted_lab_events} xét nghiệm và ${res.data.deleted_prediction_logs} log dự đoán.`
      );
      await loadPatients();
    } catch (err) {
      console.error(err);
      setError("Không thể xóa bệnh nhân này.");
    }
  };

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Quản lý bệnh nhân</p>
          <h1 className="page-title">Danh sách bệnh nhân</h1>
          <p className="page-desc">
            {role === "admin"
              ? "Admin xem toàn bộ bệnh nhân đã được phân công hoặc đã có dữ liệu xét nghiệm trong hệ thống."
              : "Bác sĩ chỉ nhìn thấy các bệnh nhân được admin phân công quản lý."}
          </p>
        </div>

        <button className="primary-btn" type="button" onClick={loadPatients}>
          {loading ? "Đang tải..." : "Làm mới"}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="stat-grid">
        <Card title="Tổng bệnh nhân" value={patients.length} />
        <Card title="Đã có xét nghiệm" value={activeCount} />
        <Card title="Nguy cơ cao" value={highRiskCount} />
        <Card
          title="Vai trò hiện tại"
          value={role === "admin" ? "Admin" : "Doctor"}
        />
      </div>

      {role === "admin" && (
        <>
          <h2 className="section-title">Thêm bệnh nhân</h2>
          <form className="query-panel" onSubmit={createPatient}>
            <div className="field">
              <label>subject_id</label>
              <input
                value={patientForm.subject_id}
                onChange={(event) =>
                  setPatientForm((prev) => ({ ...prev, subject_id: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label>stay_id</label>
              <input
                value={patientForm.stay_id}
                onChange={(event) =>
                  setPatientForm((prev) => ({ ...prev, stay_id: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label>gender</label>
              <select
                value={patientForm.gender}
                onChange={(event) =>
                  setPatientForm((prev) => ({ ...prev, gender: event.target.value }))
                }
              >
                <option value="male">male</option>
                <option value="female">female</option>
              </select>
            </div>
            <button className="primary-btn" type="submit">
              Thêm bệnh nhân
            </button>
          </form>
        </>
      )}

      <div className="query-panel patient-search-panel">
        <div className="field patient-search-field">
          <label>Tìm kiếm</label>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Nhập subject_id, stay_id, bác sĩ hoặc mức nguy cơ"
          />
        </div>
      </div>

      {filteredPatients.length === 0 ? (
        <div className="empty-state">
          <p className="empty-title">Chưa có bệnh nhân phù hợp</p>
          <p>
            Admin có thể phân công bệnh nhân trong trang Người dùng. Sau khi bác sĩ nhập dự đoán,
            số xét nghiệm và nguy cơ mới nhất sẽ xuất hiện tại đây.
          </p>
        </div>
      ) : (
        <div className="table-card">
          <h2 className="section-title" style={{ marginTop: 0 }}>
            Bảng bệnh nhân
          </h2>

          <table>
            <thead>
              <tr>
                <th>Subject</th>
                <th>Stay</th>
                <th>Giới tính</th>
                <th>Bác sĩ phụ trách</th>
                <th>Số xét nghiệm</th>
                <th>Số dự đoán</th>
                <th>Nguy cơ mới nhất</th>
                <th>Xác suất</th>
                <th>Cập nhật gần nhất</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {filteredPatients.map((patient) => (
                <tr key={`${patient.subject_id}-${patient.stay_id}`}>
                  <td>{patient.subject_id}</td>
                  <td>{patient.stay_id}</td>
                  <td>{patient.gender || "-"}</td>
                  <td>{patient.doctor_username || "Chưa phân công"}</td>
                  <td>{patient.lab_event_count}</td>
                  <td>{patient.prediction_count}</td>
                  <td>
                    <span className={getRiskClass(patient.latest_risk_level)}>
                      {patient.latest_risk_level || "Chưa có"}
                    </span>
                  </td>
                  <td>
                    {patient.latest_probability !== null
                      ? `${(patient.latest_probability * 100).toFixed(2)}%`
                      : "-"}
                  </td>
                  <td>{formatDateTime(patient.latest_charttime)}</td>
                  <td>
                    <div className="inline-actions">
                      <Link
                        className="secondary-btn"
                        to={`/patient-timeline?subject_id=${patient.subject_id}&stay_id=${patient.stay_id}`}
                      >
                        Timeline
                      </Link>
                      {role === "doctor" && (
                        <Link className="secondary-btn" to="/predict">
                          Dự đoán
                        </Link>
                      )}
                      {role === "admin" && (
                        <button
                          className="danger-btn compact-danger-btn"
                          type="button"
                          onClick={() => deletePatient(patient)}
                        >
                          Xóa bệnh nhân
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
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
  if (riskLevel === "Low") return "risk-low";
  return "";
}
