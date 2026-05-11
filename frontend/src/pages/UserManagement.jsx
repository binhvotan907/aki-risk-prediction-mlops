import { useEffect, useMemo, useState } from "react";
import PasswordInput from "../components/PasswordInput";
import apiClient from "../api/client";

const initialForm = {
  username: "",
  full_name: "",
  password: "",
  role: "doctor",
};

const initialAssignment = {
  doctor_username: "",
  patient_key: "",
};

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [patients, setPatients] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [assignmentForm, setAssignmentForm] = useState(initialAssignment);
  const [resetPasswords, setResetPasswords] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const doctors = useMemo(
    () => users.filter((user) => user.role === "doctor" && user.is_active),
    [users]
  );

  const loadUsers = async () => {
    const res = await apiClient.get("/auth/users");
    setUsers(res.data);
  };

  const loadPatients = async () => {
    const res = await apiClient.get("/patients");
    setPatients(res.data);
  };

  const loadAssignments = async () => {
    const res = await apiClient.get("/patients/assignments");
    setAssignments(res.data);
  };

  const loadPage = async () => {
    setError("");
    try {
      await Promise.all([loadUsers(), loadPatients(), loadAssignments()]);
    } catch (err) {
      console.error(err);
      setError("Không tải được dữ liệu quản trị người dùng.");
    }
  };

  useEffect(() => {
    loadPage();
  }, []);

  useEffect(() => {
    if (!assignmentForm.doctor_username && doctors.length > 0) {
      setAssignmentForm((prev) => ({
        ...prev,
        doctor_username: doctors[0].username,
      }));
    }
  }, [assignmentForm.doctor_username, doctors]);

  useEffect(() => {
    if (!assignmentForm.patient_key && patients.length > 0) {
      setAssignmentForm((prev) => ({
        ...prev,
        patient_key: toPatientKey(patients[0]),
      }));
    }
  }, [assignmentForm.patient_key, patients]);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleAssignmentChange = (key, value) => {
    setAssignmentForm((prev) => ({ ...prev, [key]: value }));
  };

  const createUser = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!form.username || !form.password) {
      setError("Vui lòng nhập username và mật khẩu tạm.");
      return;
    }

    if (form.password.length < 8) {
      setError("Mật khẩu tạm cần ít nhất 8 ký tự.");
      return;
    }

    setLoading(true);
    try {
      await apiClient.post("/auth/users", form);
      setForm(initialForm);
      setMessage("Tạo tài khoản thành công.");
      await loadUsers();
    } catch (err) {
      console.error(err);
      setError("Tạo tài khoản thất bại. Username có thể đã tồn tại.");
    } finally {
      setLoading(false);
    }
  };

  const createAssignment = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!assignmentForm.doctor_username) {
      setError("Vui lòng chọn bác sĩ cần phân công.");
      return;
    }

    if (!assignmentForm.patient_key) {
      setError("Vui lòng tạo bệnh nhân ở trang Bệnh nhân trước khi phân công.");
      return;
    }

    const [subjectId, stayId] = assignmentForm.patient_key.split(":").map(Number);

    try {
      await apiClient.post("/patients/assignments", {
        doctor_username: assignmentForm.doctor_username,
        subject_id: subjectId,
        stay_id: stayId,
      });
      setMessage("Phân công bệnh nhân thành công.");
      await Promise.all([loadPatients(), loadAssignments()]);
    } catch (err) {
      console.error(err);
      setError("Phân công thất bại. Bệnh nhân này có thể đã được phân công cho bác sĩ.");
    }
  };

  const deleteAssignment = async (assignmentId) => {
    setError("");
    setMessage("");

    try {
      await apiClient.delete(`/patients/assignments/${assignmentId}`);
      setMessage("Đã xóa phân công.");
      await Promise.all([loadPatients(), loadAssignments()]);
    } catch (err) {
      console.error(err);
      setError("Không thể xóa phân công này.");
    }
  };

  const toggleActive = async (userId) => {
    setError("");
    setMessage("");
    try {
      await apiClient.patch(`/auth/users/${userId}/toggle-active`);
      setMessage("Cập nhật trạng thái tài khoản thành công.");
      await loadUsers();
    } catch (err) {
      console.error(err);
      setError("Không thể đổi trạng thái tài khoản này.");
    }
  };

  const deleteUser = async (user) => {
    setError("");
    setMessage("");

    if (user.username === localStorage.getItem("username")) {
      setError("Không thể xóa tài khoản đang đăng nhập.");
      return;
    }

    const confirmed = window.confirm(
      `Xóa tài khoản ${user.username}? Nếu đây là bác sĩ, các phân công bệnh nhân của tài khoản này cũng sẽ bị xóa.`
    );

    if (!confirmed) return;

    try {
      const res = await apiClient.delete(`/auth/users/${user.id}`);
      setMessage(
        `Đã xóa tài khoản ${res.data.username}. Đã xóa ${res.data.deleted_assignments} phân công liên quan.`
      );
      await Promise.all([loadUsers(), loadPatients(), loadAssignments()]);
    } catch (err) {
      console.error(err);
      setError("Không thể xóa tài khoản này.");
    }
  };

  const resetPassword = async (userId) => {
    const newPassword = resetPasswords[userId] || "";
    setError("");
    setMessage("");

    if (newPassword.length < 8) {
      setError("Mật khẩu reset cần ít nhất 8 ký tự.");
      return;
    }

    try {
      await apiClient.post(`/auth/users/${userId}/reset-password`, {
        new_password: newPassword,
      });
      setResetPasswords((prev) => ({ ...prev, [userId]: "" }));
      setMessage("Reset mật khẩu thành công.");
    } catch (err) {
      console.error(err);
      setError("Reset mật khẩu thất bại.");
    }
  };

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Quản trị hệ thống</p>
          <h1 className="page-title">Quản lý người dùng</h1>
          <p className="page-desc">
            Admin tạo tài khoản bác sĩ và phân công bệnh nhân đã có trong hệ thống.
            Bác sĩ chỉ được nhập dự đoán hoặc xem timeline cho các bệnh nhân được phân công.
          </p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <h2 className="section-title">Tạo tài khoản</h2>
      <form className="query-panel" onSubmit={createUser}>
        <Field
          label="username"
          value={form.username}
          onChange={(v) => handleChange("username", v)}
        />
        <Field
          label="họ tên"
          value={form.full_name}
          onChange={(v) => handleChange("full_name", v)}
        />
        <PasswordInput
          label="mật khẩu tạm"
          value={form.password}
          onChange={(v) => handleChange("password", v)}
        />
        <div className="field">
          <label>vai trò</label>
          <select value={form.role} onChange={(e) => handleChange("role", e.target.value)}>
            <option value="doctor">doctor</option>
            <option value="admin">admin</option>
          </select>
        </div>
        <button className="primary-btn" type="submit" disabled={loading}>
          {loading ? "Đang tạo..." : "Tạo tài khoản"}
        </button>
      </form>

      <h2 className="section-title">Phân công bệnh nhân</h2>
      <form className="query-panel" onSubmit={createAssignment}>
        <div className="field">
          <label>bác sĩ</label>
          <select
            value={assignmentForm.doctor_username}
            onChange={(e) => handleAssignmentChange("doctor_username", e.target.value)}
          >
            {doctors.map((doctor) => (
              <option key={doctor.id} value={doctor.username}>
                {doctor.full_name || doctor.username} ({doctor.username})
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label>bệnh nhân</label>
          <select
            value={assignmentForm.patient_key}
            onChange={(e) => handleAssignmentChange("patient_key", e.target.value)}
          >
            {patients.length === 0 ? (
              <option value="">Chưa có bệnh nhân</option>
            ) : (
              patients.map((patient) => (
                <option key={toPatientKey(patient)} value={toPatientKey(patient)}>
                  {patient.subject_id} / {patient.stay_id}
                  {patient.doctor_username ? ` - đã phân công cho ${patient.doctor_username}` : ""}
                </option>
              ))
            )}
          </select>
        </div>
        <button className="primary-btn" type="submit" disabled={patients.length === 0}>
          Phân công
        </button>
      </form>

      <div className="table-card">
        <h2 className="section-title" style={{ marginTop: 0 }}>
          Danh sách phân công
        </h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Bác sĩ</th>
              <th>Subject</th>
              <th>Stay</th>
              <th>Người phân công</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {assignments.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.doctor_username}</td>
                <td>{item.subject_id}</td>
                <td>{item.stay_id}</td>
                <td>{item.assigned_by || "-"}</td>
                <td>
                  <button className="secondary-btn" type="button" onClick={() => deleteAssignment(item.id)}>
                    Xóa phân công
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-card">
        <h2 className="section-title" style={{ marginTop: 0 }}>
          Danh sách tài khoản
        </h2>

        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Họ tên</th>
              <th>Vai trò</th>
              <th>Trạng thái</th>
              <th>Reset mật khẩu</th>
              <th>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.id}</td>
                <td>{user.username}</td>
                <td>{user.full_name || "-"}</td>
                <td>{user.role}</td>
                <td>
                  <span className={user.is_active ? "risk-low" : "risk-high"}>
                    {user.is_active ? "active" : "inactive"}
                  </span>
                </td>
                <td>
                  <div className="inline-actions">
                    <PasswordInput
                      label=""
                      value={resetPasswords[user.id] || ""}
                      onChange={(value) =>
                        setResetPasswords((prev) => ({
                          ...prev,
                          [user.id]: value,
                        }))
                      }
                      className="compact-password-field"
                    />
                    <button className="secondary-btn" type="button" onClick={() => resetPassword(user.id)}>
                      Reset
                    </button>
                  </div>
                </td>
                <td>
                  <div className="inline-actions">
                    <button className="secondary-btn" type="button" onClick={() => toggleActive(user.id)}>
                      {user.is_active ? "Khóa" : "Mở khóa"}
                    </button>
                    {user.username !== localStorage.getItem("username") && (
                      <button className="danger-btn compact-danger-btn" type="button" onClick={() => deleteUser(user)}>
                        Xóa
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function toPatientKey(patient) {
  return `${patient.subject_id}:${patient.stay_id}`;
}
