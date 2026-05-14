import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import apiClient from "../api/client";

const doctorLinks = [
  { to: "/dashboard", icon: "⌂", label: "Tổng quan" },
  { to: "/patients", icon: "▤", label: "Bệnh nhân" },
  { to: "/predict", icon: "+", label: "Dự đoán" },
  { to: "/patient-timeline", icon: "↗", label: "Timeline" },
  { to: "/model-info", icon: "□", label: "Mô hình" },
  { to: "/account", icon: "○", label: "Tài khoản" },
];

const adminLinks = [
  { to: "/monitoring", icon: "◉", label: "Monitoring" },
  { to: "/drift", icon: "◇", label: "Drift" },
  { to: "/retraining", icon: "↻", label: "Retraining" },
  { to: "/users", icon: "▦", label: "Người dùng" },
];

export default function AppLayout({ children }) {
  const username = localStorage.getItem("username") || "user";
  const fullName = localStorage.getItem("full_name") || username;
  const role = localStorage.getItem("role") || "doctor";
  const seenKey = `assignment_seen_${username}`;
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem("sidebar_collapsed") === "true";
  });
  const [assignments, setAssignments] = useState([]);
  const [notificationOpen, setNotificationOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem("sidebar_collapsed", String(collapsed));
  }, [collapsed]);

  useEffect(() => {
    if (role !== "doctor") return;

    let isMounted = true;

    const loadAssignments = async () => {
      try {
        const res = await apiClient.get("/patients/my-assignments");
        if (isMounted) setAssignments(res.data);
      } catch (err) {
        console.error(err);
      }
    };

    loadAssignments();
    const intervalId = window.setInterval(loadAssignments, 30000);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
    };
  }, [role]);

  const logout = () => {
    localStorage.clear();
    window.location.href = "/login";
  };

  const seenAssignmentIds = readSeenIds(seenKey);
  const unreadAssignments = assignments.filter(
    (assignment) => !seenAssignmentIds.includes(assignment.id)
  );
  const visibleDoctorLinks = role === "admin"
    ? doctorLinks.filter((item) => item.to !== "/predict")
    : doctorLinks.filter((item) => item.to !== "/model-info");

  const markAssignmentsAsSeen = () => {
    const allIds = Array.from(new Set(assignments.map((assignment) => assignment.id)));
    localStorage.setItem(seenKey, JSON.stringify(allIds));
    setNotificationOpen(false);
  };

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-mark">AKI</div>
          <div className="sidebar-text">
            <p className="logo-title">AKI Risk</p>
            <p className="logo-subtitle">Realtime Lab MLOps</p>
          </div>
        </div>

        <button
          className="sidebar-toggle"
          type="button"
          onClick={() => setCollapsed((prev) => !prev)}
          title={collapsed ? "Mở menu" : "Thu gọn menu"}
          aria-label={collapsed ? "Mở menu" : "Thu gọn menu"}
        >
          {collapsed ? "›" : "‹"}
        </button>

        <div className="user-card">
          <p className="user-name">{fullName}</p>
          <p className="user-meta">@{username}</p>
          <span className={`role-badge ${role === "admin" ? "admin" : ""}`}>
            {role === "admin" ? "Quản trị viên" : "Bác sĩ"}
          </span>
        </div>

        <nav>
          <NavSection title="Bệnh nhân" links={visibleDoctorLinks} collapsed={collapsed} />

          {role === "admin" && (
            <NavSection title="Quản trị" links={adminLinks} collapsed={collapsed} />
          )}
        </nav>

        <button className="logout-btn" onClick={logout} title="Đăng xuất">
          <span className="nav-icon">×</span>
          <span className="sidebar-text">Đăng xuất</span>
        </button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button
            className="mobile-menu-btn"
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label="Đổi trạng thái menu"
          >
            ☰
          </button>

          <div>
            <p className="topbar-title">Dự đoán nguy cơ suy thận cấp</p>
            <p className="topbar-context">
              {role === "admin" ? "Quản trị hệ thống và vòng đời model" : "Theo dõi bệnh nhân được phân công"}
            </p>
          </div>

          <div className="topbar-right">
            {role === "doctor" && (
              <div className="notification-wrap">
                <button
                  className={`notification-btn ${unreadAssignments.length > 0 ? "has-unread" : ""}`}
                  type="button"
                  onClick={() => setNotificationOpen((prev) => !prev)}
                  aria-label="Thông báo phân công bệnh nhân"
                  title="Thông báo phân công bệnh nhân"
                >
                  <span>!</span>
                  {unreadAssignments.length > 0 && (
                    <span className="notification-badge">
                      {unreadAssignments.length}
                    </span>
                  )}
                </button>

                {notificationOpen && (
                  <div className="notification-panel">
                    <div className="notification-header">
                      <div>
                        <p className="notification-title">Phân công bệnh nhân</p>
                        <p className="notification-subtitle">
                          {unreadAssignments.length > 0
                            ? `${unreadAssignments.length} phân công mới`
                            : "Không có phân công mới"}
                        </p>
                      </div>

                      {assignments.length > 0 && (
                        <button
                          className="notification-clear"
                          type="button"
                          onClick={markAssignmentsAsSeen}
                        >
                          Đã xem
                        </button>
                      )}
                    </div>

                    <div className="notification-list">
                      {assignments.length === 0 ? (
                        <p className="notification-empty">
                          Bạn chưa được phân công bệnh nhân nào.
                        </p>
                      ) : (
                        assignments.slice(0, 5).map((assignment) => (
                          <div
                            className={`notification-item ${
                              seenAssignmentIds.includes(assignment.id) ? "" : "new"
                            }`}
                            key={assignment.id}
                          >
                            <p>
                              Subject <b>{assignment.subject_id}</b> / Stay{" "}
                              <b>{assignment.stay_id}</b>
                            </p>
                            <span>
                              Admin: {assignment.assigned_by || "-"} ·{" "}
                              {formatDateTime(assignment.created_at)}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
            <span className="system-pill">Online</span>
            <span className={`role-badge ${role === "admin" ? "admin" : ""}`}>
              {role === "admin" ? "Admin" : "Doctor"}
            </span>
          </div>
        </header>

        <section className="page-content">{children}</section>
      </main>
    </div>
  );
}

function readSeenIds(key) {
  try {
    const rawValue = localStorage.getItem(key);
    const parsedValue = rawValue ? JSON.parse(rawValue) : [];
    return Array.isArray(parsedValue) ? parsedValue : [];
  } catch {
    return [];
  }
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

function NavSection({ title, links, collapsed }) {
  return (
    <>
      <div className="nav-section-title">{collapsed ? "·" : title}</div>
      {links.map((item) => (
        <NavLink key={item.to} className="nav-link" to={item.to} title={item.label}>
          <span className="nav-icon">{item.icon}</span>
          <span className="sidebar-text">{item.label}</span>
        </NavLink>
      ))}
    </>
  );
}
