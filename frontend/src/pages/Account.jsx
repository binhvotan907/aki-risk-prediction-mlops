import { useEffect, useState } from "react";
import PasswordInput from "../components/PasswordInput";
import apiClient from "../api/client";

const initialForm = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

export default function Account() {
  const [me, setMe] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function loadMe() {
      try {
        const res = await apiClient.get("/auth/me");
        setMe(res.data);
      } catch (err) {
        console.error(err);
        setError("Không lấy được thông tin tài khoản.");
      }
    }

    loadMe();
  }, []);

  const handleChange = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (form.new_password.length < 8) {
      setError("Mật khẩu mới cần dài hơn hoặc bằng 8 ký tự.");
      return;
    }

    if (form.current_password === form.new_password) {
      setError("Mật khẩu mới phải khác mật khẩu hiện tại.");
      return;
    }

    if (form.new_password !== form.confirm_password) {
      setError("Xác nhận mật khẩu không khớp với mật khẩu mới.");
      return;
    }

    setSaving(true);
    try {
      await apiClient.post("/auth/change-password", {
        current_password: form.current_password,
        new_password: form.new_password,
      });
      setForm(initialForm);
      setMessage("Đổi mật khẩu thành công.");
    } catch (err) {
      console.error(err);
      setError("Đổi mật khẩu thất bại. Vui lòng kiểm tra mật khẩu hiện tại và điều kiện mật khẩu mới.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Tài khoản</p>
          <h1 className="page-title">Thông tin cá nhân</h1>
          <p className="page-desc">
            Người dùng có thể xem thông tin tài khoản và tự đổi mật khẩu sau khi
            được quản trị viên cấp quyền truy cập.
          </p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="stat-grid">
        <Card title="Tên đăng nhập" value={me?.username || "-"} />
        <Card title="Họ tên" value={me?.full_name || "-"} />
        <Card title="Vai trò" value={me?.role || "-"} />
        <Card title="Trạng thái" value={me?.is_active ? "Đang hoạt động" : "-"} />
      </div>

      <form className="table-card account-form" onSubmit={changePassword}>
        <h2 className="section-title" style={{ marginTop: 0 }}>
          Đổi mật khẩu
        </h2>
        <p className="section-subtitle">
          Mật khẩu mới phải có ít nhất 8 ký tự và khác mật khẩu hiện tại.
        </p>

        <div className="form-grid-4">
          <PasswordInput
            label="Mật khẩu hiện tại"
            value={form.current_password}
            onChange={(v) => handleChange("current_password", v)}
          />
          <PasswordInput
            label="Mật khẩu mới"
            value={form.new_password}
            onChange={(v) => handleChange("new_password", v)}
          />
          <PasswordInput
            label="Xác nhận mật khẩu"
            value={form.confirm_password}
            onChange={(v) => handleChange("confirm_password", v)}
          />
        </div>

        <button className="primary-btn" type="submit" disabled={saving}>
          {saving ? "Đang lưu..." : "Cập nhật mật khẩu"}
        </button>
      </form>
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
