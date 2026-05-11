import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page-card not-found">
      <p className="eyebrow">404</p>
      <h1 className="page-title">Không tìm thấy trang</h1>
      <p className="page-desc">
        Đường dẫn này không tồn tại hoặc bạn không có quyền truy cập vào khu vực
        tương ứng.
      </p>
      <div className="action-row">
        <Link className="primary-btn" to="/dashboard">
          Về tổng quan
        </Link>
      </div>
    </div>
  );
}
