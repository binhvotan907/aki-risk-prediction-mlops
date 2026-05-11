import { useEffect, useState } from "react";
import apiClient from "../api/client";

export default function ModelInfo() {
  const [modelInfo, setModelInfo] = useState(null);
  const [error, setError] = useState("");

  const loadModelInfo = async () => {
    setError("");

    try {
      const res = await apiClient.get("/model/info");
      setModelInfo(res.data);
    } catch (err) {
      console.error(err);
      setError("Không lấy được thông tin mô hình.");
    }
  };

  useEffect(() => {
    loadModelInfo();
  }, []);

  if (error) {
    return (
      <div className="page-card">
        <div className="error-box">{error}</div>
      </div>
    );
  }

  if (!modelInfo) {
    return (
      <div className="page-card">
        <p>Đang tải thông tin mô hình...</p>
      </div>
    );
  }

  const metrics = modelInfo.metrics || {};

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Quản trị mô hình</p>
          <h1 className="page-title">Thông tin mô hình</h1>
          <p className="page-desc">
            Thông tin phiên bản mô hình, cấu hình dự đoán và các chỉ số đánh giá.
          </p>
        </div>

        <button className="primary-btn" onClick={loadModelInfo}>
          Làm mới
        </button>
      </div>

      <h2 className="section-title">Thông tin triển khai</h2>

      <div className="stat-grid">
        <Card title="Tên mô hình" value={modelInfo.model_name} />
        <Card title="Phiên bản" value={modelInfo.model_version} />
        <Card title="Ngưỡng cảnh báo" value={modelInfo.threshold} />
        <Card title="Số đặc trưng" value={modelInfo.feature_count} />
        <Card title="Cửa sổ dữ liệu" value={`${modelInfo.lookback_hours} giờ`} />
        <Card
          title="Khoảng dự đoán"
          value={`${modelInfo.prediction_horizon_hours} giờ`}
        />
      </div>

      <h2 className="section-title">Chỉ số đánh giá</h2>

      <div className="stat-grid">
        <Card title="ROC-AUC" value={formatMetric(metrics.test_roc_auc)} />
        <Card title="PR-AUC" value={formatMetric(metrics.test_pr_auc)} />
        <Card title="Precision" value={formatMetric(metrics.test_precision)} />
        <Card title="Recall" value={formatMetric(metrics.test_recall)} />
        <Card title="F1-score" value={formatMetric(metrics.test_f1)} />
      </div>

      <div className="info-box">
        <h2 style={{ marginTop: 0 }}>Ý nghĩa trong quản trị mô hình</h2>
        <p style={{ marginBottom: 0 }}>
          Trang này hiển thị thông tin mô hình đang được sử dụng trong hệ thống,
          bao gồm phiên bản, ngưỡng cảnh báo, số lượng đặc trưng đầu vào và các
          chỉ số đánh giá trên tập kiểm thử. Thông tin này giúp người quản trị
          biết chính xác mô hình nào đang được triển khai và chất lượng đánh giá
          của mô hình đó.
        </p>
      </div>

      <div className="table-card">
        <h2 className="section-title" style={{ marginTop: 0 }}>
          Dữ liệu cấu hình mô hình
        </h2>

        <pre className="pre-block">{JSON.stringify(modelInfo, null, 2)}</pre>
      </div>
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

function formatMetric(value) {
  if (value === undefined || value === null) return "-";
  return Number(value).toFixed(3);
}