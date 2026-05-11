import { useState } from "react";

export default function PasswordInput({ label, value, onChange, className = "" }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className={`field ${className}`}>
      <label>{label}</label>
      <div className="password-input-wrap">
        <input
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="password-toggle"
          aria-label={visible ? "Ẩn mật khẩu" : "Hiển thị mật khẩu"}
          title={visible ? "Ẩn mật khẩu" : "Hiển thị mật khẩu"}
          onClick={() => setVisible((prev) => !prev)}
        >
          {visible ? "◌" : "◉"}
        </button>
      </div>
    </div>
  );
}
