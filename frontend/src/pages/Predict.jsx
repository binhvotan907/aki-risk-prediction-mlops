import { useState } from "react";
import apiClient from "../api/client";

const initialForm = {
  subject_id: 10001,
  stay_id: 30001,
  gender: "male",
  icu_intime: "2026-04-25T08:00:00",
  charttime: "2026-04-25T10:00:00",
  creatinine: 1.1,
  bun: 20,
  sodium: 139,
  potassium: 4.2,
  chloride: 101,
  bicarbonate: 24,
  glucose: 120,
  calcium: 8.8,
  magnesium: 2.0,
  phosphate: 3.2,
  anion_gap: 12,
  hemoglobin: 12.5,
  hematocrit: 37,
  wbc: 8.5,
  platelets: 220,
};

const patientFields = ["subject_id", "stay_id", "gender", "icu_intime", "charttime"];

const labFields = [
  "creatinine",
  "bun",
  "sodium",
  "potassium",
  "chloride",
  "bicarbonate",
  "glucose",
  "calcium",
  "magnesium",
  "phosphate",
  "anion_gap",
  "hemoglobin",
  "hematocrit",
  "wbc",
  "platelets",
];

const templateFields = [...patientFields, ...labFields];
const requiredFields = [...patientFields, ...labFields];

const templateSample = {
  subject_id: 10002,
  stay_id: 30002,
  gender: "male",
  icu_intime: "2026-04-25T08:00:00",
  charttime: "2026-04-25T10:00:00",
  creatinine: 0.9,
  bun: 14,
  sodium: 139,
  potassium: 4.2,
  chloride: 101,
  bicarbonate: 24,
  glucose: 120,
  calcium: 8.8,
  magnesium: 2,
  phosphate: 3.2,
  anion_gap: 12,
  hemoglobin: 12.5,
  hematocrit: 37,
  wbc: 8.5,
  platelets: 220,
};

function getApiErrorMessage(err) {
  if (err?.response?.status === 403) {
    return "Bạn chưa được phân công bệnh nhân này. Vui lòng liên hệ quản trị viên để được cấp quyền.";
  }

  if (err?.response?.status === 422) {
    return "Dữ liệu chưa hợp lệ hoặc còn thiếu thông tin bắt buộc. Vui lòng kiểm tra lại toàn bộ form.";
  }

  return "Dự đoán thất bại. Vui lòng kiểm tra dữ liệu nhập hoặc máy chủ.";
}

export default function Predict() {
  const [form, setForm] = useState(initialForm);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [uploadMessage, setUploadMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  const handleChange = (key, value) => {
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    setForm({
      ...form,
      [key]: value,
    });
  };

  const parseNumber = (value) => {
    if (value === "" || value === null || value === undefined) return null;
    return Number(String(value).replace(",", "."));
  };

  const validateForm = () => {
    const nextErrors = {};

    requiredFields.forEach((key) => {
      const value = form[key];
      if (value === "" || value === null || value === undefined) {
        nextErrors[key] = "Bắt buộc nhập";
      }
    });

    ["subject_id", "stay_id", ...labFields].forEach((key) => {
      const value = form[key];
      if (value === "" || value === null || value === undefined) return;
      const numberValue = Number(String(value).replace(",", "."));
      if (!Number.isFinite(numberValue)) {
        nextErrors[key] = "Phải là số hợp lệ";
      }
    });

    setFieldErrors(nextErrors);
    return nextErrors;
  };

  const handlePredict = async (e) => {
    e.preventDefault();
    setError("");
    setResult(null);
    setUploadMessage("");

    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setError(
        `Vui lòng nhập đầy đủ thông tin trước khi dự đoán. Các trường cần kiểm tra: ${Object.keys(validationErrors).join(", ")}.`
      );
      return;
    }

    const payload = {
      ...form,
      subject_id: Number(String(form.subject_id).replace(",", ".")),
      stay_id: Number(String(form.stay_id).replace(",", ".")),
    };

    labFields.forEach((key) => {
      payload[key] = parseNumber(payload[key]);
    });

    try {
      const res = await apiClient.post("/predict", payload);
      setResult(res.data);
    } catch (err) {
      console.error(err);
      setError(getApiErrorMessage(err));
    }
  };

  const downloadTemplate = () => {
    const headerCells = templateFields
      .map((field) => `<th>${escapeHtml(field)}</th>`)
      .join("");
    const valueCells = templateFields
      .map((field) => `<td>${escapeHtml(templateSample[field])}</td>`)
      .join("");
    const excelHtml = `
      <html>
        <head>
          <meta charset="utf-8" />
        </head>
        <body>
          <table>
            <tr>${headerCells}</tr>
            <tr>${valueCells}</tr>
          </table>
        </body>
      </html>
    `;
    const blob = new Blob([excelHtml], {
      type: "application/vnd.ms-excel;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aki_lab_prediction_template.xls";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    setError("");
    setResult(null);
    setUploadMessage("");

    if (!file) return;

    const fileName = file.name.toLowerCase();

    if (fileName.endsWith(".xlsx")) {
      setError(
        "Hiện tại hệ thống hỗ trợ file Excel mẫu .xls và CSV. Vui lòng tải file mẫu .xls hoặc lưu dữ liệu dưới dạng CSV trước khi upload."
      );
      event.target.value = "";
      return;
    }

    try {
      const text = await file.text();
      const parsedRow = parseUploadedFile(text);
      setForm((prev) => ({ ...prev, ...parsedRow }));
      setUploadMessage(
        `Đã map ${Object.keys(parsedRow).length} cột từ file ${file.name} vào form.`
      );
    } catch (err) {
      console.error(err);
      setError(err.message || "Không đọc được file upload. Vui lòng kiểm tra file mẫu.");
    } finally {
      event.target.value = "";
    }
  };

  return (
    <div className="page-card">
      <div className="page-title-row">
        <div>
          <p className="eyebrow">Dự đoán nguy cơ</p>
          <h1 className="page-title">Dự đoán nguy cơ suy thận cấp</h1>
          <p className="page-desc">
            Nhập dữ liệu xét nghiệm tại một thời điểm để hệ thống tính toán đặc
            trưng realtime và trả về mức nguy cơ AKI.
          </p>
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {uploadMessage && <div className="success-box">{uploadMessage}</div>}

      <form onSubmit={handlePredict}>
        <div className="upload-panel">
          <div>
            <p className="upload-title">Nhập nhanh bằng file Excel</p>
            <p className="upload-desc">
              Tải file mẫu CSV, mở bằng Excel, điền một dòng dữ liệu xét nghiệm
              rồi upload lại để hệ thống tự động map vào các ô bên dưới.
            </p>
          </div>

          <div className="upload-actions">
            <button className="secondary-btn" type="button" onClick={downloadTemplate}>
              Tải file mẫu
            </button>

            <label className="file-upload-btn">
              Upload file
              <input
                type="file"
                accept=".xls,.csv,text/csv,.txt"
                onChange={handleFileUpload}
              />
            </label>
          </div>
        </div>

        <h2 className="section-title">Thông tin bệnh nhân</h2>

        <div className="form-grid-5">
          <Input
            label="subject_id"
            value={form.subject_id}
            onChange={(v) => handleChange("subject_id", v)}
            error={fieldErrors.subject_id}
          />

          <Input
            label="stay_id"
            value={form.stay_id}
            onChange={(v) => handleChange("stay_id", v)}
            error={fieldErrors.stay_id}
          />

          <Input
            label="gender"
            value={form.gender}
            onChange={(v) => handleChange("gender", v)}
            error={fieldErrors.gender}
          />

          <Input
            label="icu_intime"
            value={form.icu_intime}
            onChange={(v) => handleChange("icu_intime", v)}
            error={fieldErrors.icu_intime}
          />

          <Input
            label="charttime"
            value={form.charttime}
            onChange={(v) => handleChange("charttime", v)}
            error={fieldErrors.charttime}
          />
        </div>

        <h2 className="section-title">Thông tin xét nghiệm</h2>

        <div className="form-grid-5">
          {labFields.map((field) => (
            <Input
              key={field}
              label={field}
              value={form[field]}
              onChange={(v) => handleChange(field, v)}
              error={fieldErrors[field]}
            />
          ))}
        </div>

        <div className="action-row">
          <button className="primary-btn" type="submit">
            Dự đoán nguy cơ
          </button>
        </div>
      </form>

      {result && (
        <div
          className={`result-panel ${
            result.risk_level === "High"
              ? "high"
              : result.risk_level === "Low"
              ? "low"
              : ""
          }`}
        >
          <h2 className="section-title" style={{ marginTop: 0 }}>
            Kết quả dự đoán
          </h2>

          <div className="stat-grid">
            <Card
              title="Xác suất nguy cơ"
              value={`${(result.aki_probability * 100).toFixed(2)}%`}
            />

            <Card title="Mức nguy cơ" value={result.risk_level} />

            <Card
              title="Kết luận"
              value={result.prediction === 1 ? "Có nguy cơ" : "Chưa cảnh báo"}
            />

            <Card
              title="Mô hình"
              value={`${result.model_name} ${result.model_version}`}
            />
          </div>

          <div className="info-box">
            <b>Nhận xét:</b> {result.message}
          </div>

          <h3 className="section-title">Đặc trưng được tính tự động</h3>

          <pre className="pre-block">
            {JSON.stringify(result.generated_features_preview, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange, error }) {
  return (
    <div className={`field ${error ? "field-error" : ""}`}>
      <label>
        {label} <span className="required-mark">*</span>
      </label>
      <input
        type="text"
        step="any"
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={Boolean(error)}
      />
      {error && <span className="field-error-text">{error}</span>}
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseUploadedFile(text) {
  if (/<table[\s>]/i.test(text)) {
    return parseUploadedHtmlTable(text);
  }

  return parseUploadedCsv(text);
}

function parseUploadedHtmlTable(text) {
  const doc = new DOMParser().parseFromString(text, "text/html");
  const rows = Array.from(doc.querySelectorAll("tr")).map((row) =>
    Array.from(row.querySelectorAll("th,td")).map((cell) => cell.textContent.trim())
  );

  if (rows.length < 2) {
    throw new Error("File Excel mẫu cần có dòng tiêu đề và ít nhất một dòng dữ liệu.");
  }

  return mapRowToForm(rows[0], rows[1]);
}

function parseUploadedCsv(text) {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .filter((line) => line.trim() !== "");

  if (lines.length < 2) {
    throw new Error("File cần có dòng tiêu đề và ít nhất một dòng dữ liệu.");
  }

  const delimiter = detectDelimiter(lines[0]);
  const headers = splitDelimitedLine(lines[0], delimiter);
  const values = splitDelimitedLine(lines[1], delimiter);

  return mapRowToForm(headers, values);
}

function mapRowToForm(headers, values) {
  const row = {};

  headers.map(normalizeHeader).forEach((header, index) => {
    if (templateFields.includes(header)) {
      row[header] = values[index] ?? "";
    }
  });

  const missingRequired = requiredFields.filter((field) => !row[field]);

  if (missingRequired.length > 0) {
    throw new Error(`File thiếu cột bắt buộc: ${missingRequired.join(", ")}.`);
  }

  if (Object.keys(row).length === 0) {
    throw new Error("Không tìm thấy cột hợp lệ trong file upload.");
  }

  return row;
}

function detectDelimiter(headerLine) {
  const candidates = [",", ";", "\t"];
  return candidates.reduce((best, current) => {
    const currentCount = splitDelimitedLine(headerLine, current).length;
    const bestCount = splitDelimitedLine(headerLine, best).length;
    return currentCount > bestCount ? current : best;
  }, ",");
}

function splitDelimitedLine(line, delimiter) {
  const values = [];
  let current = "";
  let insideQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"' && insideQuotes && nextChar === '"') {
      current += '"';
      i += 1;
    } else if (char === '"') {
      insideQuotes = !insideQuotes;
    } else if (char === delimiter && !insideQuotes) {
      values.push(current.trim());
      current = "";
    } else {
      current += char;
    }
  }

  values.push(current.trim());
  return values;
}

function normalizeHeader(value) {
  return String(value)
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/-/g, "_");
}
