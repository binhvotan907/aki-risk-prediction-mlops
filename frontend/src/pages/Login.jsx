import { useState } from "react";
import PasswordInput from "../components/PasswordInput";
import apiClient from "../api/client";

export default function Login() {
  const [username, setUsername] = useState("doctor");
  const [password, setPassword] = useState("doctor123");
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const res = await apiClient.post("/auth/login-json", {
        username,
        password,
      });

      localStorage.setItem("access_token", res.data.access_token);
      localStorage.setItem("role", res.data.role);
      localStorage.setItem("username", res.data.username);
      localStorage.setItem("full_name", res.data.full_name || "");

      window.location.href = "/dashboard";
    } catch (err) {
      console.error(err);
      setError("Đăng nhập thất bại. Vui lòng kiểm tra tài khoản hoặc máy chủ.");
    }
  };

  return (
    <div className="login-page">
      <div className="login-motion" />
      <main className="login-stage">
        <section className="login-hero">
          <div className="login-hero-content">
            <div className="login-brand">
              <div className="logo-mark">AKI</div>
              <div>
                <p className="logo-title">AKI Risk</p>
                <p className="logo-subtitle">Realtime Lab MLOps</p>
              </div>
            </div>

            <p className="eyebrow">Realtime Lab Monitoring</p>

            <h1 className="login-title">
              Dự đoán nguy cơ suy thận cấp từ dữ liệu xét nghiệm
            </h1>

            <p className="login-desc">
              Một dashboard gọn cho bác sĩ và quản trị viên: nhập xét nghiệm,
              xem nguy cơ AKI, theo dõi timeline, monitoring và vòng đời model.
            </p>

            <div className="login-signal-panel">
              <Signal label="Prediction" value="24h horizon" />
              <Signal label="Model" value="LightGBM v1.0" />
              <Signal label="Status" value="Realtime ready" />
            </div>
          </div>
        </section>

        <section className="login-panel">
          <form className="login-card" onSubmit={handleLogin}>
            <p className="eyebrow">Đăng nhập hệ thống</p>
            <h2>Chào mừng trở lại</h2>
            <p className="login-card-desc">
              Sử dụng tài khoản được cấp để truy cập đúng vai trò trong hệ thống.
            </p>

            {error && <div className="error-box">{error}</div>}

            <Field label="Tên đăng nhập" value={username} onChange={setUsername} />

            <PasswordInput
              label="Mật khẩu"
              value={password}
              onChange={setPassword}
              className="login-field"
            />

            <button className="primary-btn login-submit" type="submit">
              Đăng nhập
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}

function Field({ label, value, onChange }) {
  return (
    <div className="field login-field">
      <label>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

function Signal({ label, value }) {
  return (
    <div className="login-signal">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
