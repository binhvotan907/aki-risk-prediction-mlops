import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import apiClient from "../api/client";

export default function Dashboard() {
  const [modelInfo, setModelInfo] = useState(null);
  const [summary, setSummary] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [error, setError] = useState("");

  const username = localStorage.getItem("username");
  const role = localStorage.getItem("role");

  useEffect(() => {
    async function loadData() {
      try {
        const modelRes = await apiClient.get("/model/info");
        setModelInfo(modelRes.data);

        if (role === "admin") {
          const summaryRes = await apiClient.get("/monitoring/summary");
          setSummary(summaryRes.data);
        } else {
          const assignmentsRes = await apiClient.get("/patients/my-assignments");
          setAssignments(assignmentsRes.data);
        }
      } catch (err) {
        console.error(err);
        setError("Không lấy được dữ liệu tổng quan. Vui lòng kiểm tra máy chủ.");
      }
    }

    loadData();
  }, [role]);

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Tổng quan hệ thống</p>
          <h1 className="page-title">Trung tâm theo dõi nguy cơ AKI</h1>
          <p className="page-desc">
            Xin chào <b>{username}</b>. Trang này cung cấp thông tin tổng quan
            về mô hình đang sử dụng, luồng kiểm thử dự đoán và trạng thái ghi
            nhận kết quả theo thời gian.
          </p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}

      <div className="stat-grid">
        <StatCard
          title="Mô hình hiện tại"
          value={modelInfo?.model_name || "-"}
          hint="Mô hình đang được sử dụng"
        />
        <StatCard
          title="Phiên bản"
          value={modelInfo?.model_version || "-"}
          hint="Phiên bản triển khai"
        />
        <StatCard
          title="Ngưỡng cảnh báo"
          value={modelInfo?.threshold ?? "-"}
          hint="Ngưỡng phân loại nguy cơ"
        />
        <StatCard
          title="Số đặc trưng"
          value={modelInfo?.feature_count || "-"}
          hint="Số biến đầu vào của mô hình"
        />
      </div>

      {summary && (
        <>
          <h2 className="section-title">Tổng quan giám sát</h2>

          <div className="stat-grid">
            <StatCard
              title="Tổng lượt dự đoán"
              value={summary.total_predictions}
              hint="Số bản ghi đã xử lý"
            />
            <StatCard
              title="Ca nguy cơ cao"
              value={summary.high_risk}
              hint="Số lượt được cảnh báo cao"
            />
            <StatCard
              title="Tỷ lệ nguy cơ cao"
              value={`${(summary.high_risk_rate * 100).toFixed(1)}%`}
              hint="Tỷ lệ trong toàn bộ log"
            />
            <StatCard
              title="Độ trễ trung bình"
              value={`${summary.average_latency_ms.toFixed(1)} ms`}
              hint="Thời gian xử lý dự đoán"
            />
          </div>
        </>
      )}

      {role === "doctor" && (
        <>
          <h2 className="section-title">Bệnh nhân được phân công</h2>
          <p className="section-subtitle">
            Danh sách này giúp bác sĩ biết rõ các `subject_id/stay_id` được phép
            nhập dự đoán và xem timeline.
          </p>

          {assignments.length === 0 ? (
            <div className="empty-state">
              <p className="empty-title">Chưa có phân công</p>
              <p>
                Khi admin phân công bệnh nhân, thông báo sẽ xuất hiện ở góc trên
                bên phải và danh sách sẽ được cập nhật tại đây.
              </p>
            </div>
          ) : (
            <div className="assignment-grid">
              {assignments.slice(0, 6).map((assignment) => (
                <Link
                  className="assignment-card"
                  to="/patient-timeline"
                  key={assignment.id}
                >
                  <span className="assignment-kicker">Bệnh nhân</span>
                  <strong>
                    Subject {assignment.subject_id} / Stay {assignment.stay_id}
                  </strong>
                  <span>
                    Phân công bởi {assignment.assigned_by || "admin"} ·{" "}
                    {formatDateTime(assignment.created_at)}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      <h2 className="section-title">Luồng sử dụng đề xuất</h2>
      <p className="section-subtitle">
        Thực hiện theo thứ tự dưới đây để kiểm thử đầy đủ chức năng của hệ thống.
      </p>

      <div className="workflow">
        <WorkflowStep
          index="1"
          title="Đăng nhập bằng tài khoản bác sĩ"
          text="Bác sĩ nhập dữ liệu xét nghiệm và xem diễn biến nguy cơ của bệnh nhân."
        />
        <WorkflowStep
          index="2"
          title="Nhập xét nghiệm lần đầu"
          text="Tạo bản ghi ban đầu cho bệnh nhân và nhận kết quả nguy cơ thấp."
        />
        <WorkflowStep
          index="3"
          title="Nhập xét nghiệm lần tiếp theo"
          text="Giữ cùng bệnh nhân, thay đổi thời điểm và chỉ số xét nghiệm để hệ thống tự tính mức thay đổi."
        />
        <WorkflowStep
          index="4"
          title="Kiểm tra timeline và giám sát"
          text="Xem biểu đồ diễn biến bệnh nhân, sau đó quản trị viên kiểm tra log và độ trễ xử lý."
        />
      </div>

      <div className="action-row">
        {role === "doctor" && (
          <Link className="primary-btn" to="/predict">
            Bắt đầu dự đoán
          </Link>
        )}

        <Link className="secondary-btn" to="/patient-timeline">
          Xem diễn biến bệnh nhân
        </Link>

        <Link className="secondary-btn" to="/model-info">
          Xem thông tin mô hình
        </Link>

        {role === "admin" && (
          <Link className="secondary-btn" to="/monitoring">
            Xem giám sát hệ thống
          </Link>
        )}
      </div>

      <div className="info-box">
        <b>Điểm chính:</b> hệ thống không chỉ trả kết quả dự đoán tại một thời
        điểm. Khi có xét nghiệm mới của cùng bệnh nhân, hệ thống lưu lịch sử và
        tự tạo các đặc trưng theo thời gian như{" "}
        <span className="code-chip">creatinine_delta</span>{" "}
        <span className="code-chip">bun_delta</span>{" "}
        <span className="code-chip">hours_since_icu_intime</span>.
      </div>
    </div>
  );
}

function StatCard({ title, value, hint }) {
  return (
    <div className="stat-card">
      <p className="stat-label">{title}</p>
      <p className="stat-value">{value}</p>
      {hint && <p className="stat-hint">{hint}</p>}
    </div>
  );
}

function WorkflowStep({ index, title, text }) {
  return (
    <div className="workflow-step">
      <div className="workflow-index">{index}</div>
      <p className="workflow-title">{title}</p>
      <p className="workflow-text">{text}</p>
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
