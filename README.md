# Real-time AKI Risk Prediction MLOps

Đồ án xây dựng hệ thống phân tích dữ liệu xét nghiệm theo thời gian thực nhằm dự đoán nguy cơ suy thận cấp, theo hướng MLOps. Hệ thống sử dụng dữ liệu MIMIC-IV để xây dựng bộ dữ liệu huấn luyện, huấn luyện và đánh giá nhiều mô hình học máy, chọn mô hình LightGBM tốt nhất để triển khai dự đoán realtime qua API và giao diện web.

## 1. Mục Tiêu Đề Tài

Mục tiêu chính của project:

- Xây dựng mô hình dự đoán nguy cơ suy thận cấp dựa trên dữ liệu xét nghiệm lâm sàng.
- Dự đoán nguy cơ trong khoảng 24 giờ tiếp theo dựa trên lịch sử xét nghiệm 24 giờ trước đó.
- Triển khai mô hình dưới dạng API realtime.
- Ghi nhận lịch sử dự đoán, theo dõi bệnh nhân và giám sát hoạt động hệ thống.
- Chuẩn hóa quy trình MLOps gồm data, training, evaluation, model registry, serving và monitoring.

## 2. Dataset

Dataset gốc được sử dụng:

```text
MIMIC-IV v2.1
/kaggle/input/datasets/mangeshwagle/mimic-iv-2-1
```

Các bảng chính được sử dụng trong quá trình xử lý dữ liệu:

- `patients.csv`
- `icustays.csv`
- `labevents.csv`

Các xét nghiệm được chọn gồm:

```text
creatinine, bun, sodium, potassium, chloride, bicarbonate,
glucose, calcium, magnesium, phosphate, anion_gap,
hemoglobin, hematocrit, wbc, platelets
```

Do dữ liệu MIMIC-IV có kích thước lớn, bước xử lý raw data ban đầu được thực hiện offline bằng notebook riêng. Project này sử dụng dataset final đã được chuẩn hóa trong thư mục `data/`.

Dataset final:

```text
data/
├── train_dataset_final.parquet
├── val_dataset_final.parquet
├── test_dataset_final.parquet
├── features_dataset_final.json
└── dataset_final_report.json
```

Kích thước dữ liệu:

| Split | Rows | Columns | Positive Rate |
|---|---:|---:|---:|
| Train | 428,997 | 47 | 11.30% |
| Validation | 89,418 | 47 | 11.02% |
| Test | 89,811 | 47 | 11.94% |

Số feature dùng để train model: `43`.

## 3. Định Nghĩa Nhãn AKI

Tại mỗi thời điểm dự đoán `time_t`, hệ thống lấy dữ liệu xét nghiệm trong 24 giờ trước đó để tạo feature. Nhãn `label` được xác định dựa trên creatinine trong 24 giờ tiếp theo.

Một sample được gán nhãn nguy cơ AKI nếu:

```text
future_max_creatinine - baseline_creatinine >= 0.3
```

hoặc:

```text
future_max_creatinine / baseline_creatinine >= 1.5
```

Trong đó:

- `baseline_creatinine`: giá trị creatinine gần nhất trong cửa sổ quá khứ.
- `future_max_creatinine`: giá trị creatinine lớn nhất trong cửa sổ tương lai 24 giờ.

## 4. Feature Engineering

Từ notebook xử lý dữ liệu ban đầu, nhiều thống kê được tạo cho từng xét nghiệm. Sau đó project chọn bộ feature final phù hợp với realtime serving, gồm:

- Các feature kết thúc bằng `_last`
- Các feature kết thúc bằng `_delta`
- Các feature missing indicator `_is_missing`
- `hours_since_icu_intime`
- `gender_male`

Ví dụ feature quan trọng:

```text
creatinine_last
creatinine_delta
bun_last
bun_delta
anion_gap_last
phosphate_last
hours_since_icu_intime
gender_male
```

File thứ tự feature:

```text
data/features_dataset_final.json
model/lightgbm/lightgbm_feature_order.json
```

## 5. Kiến Trúc Hệ Thống

Luồng tổng thể:

```text
MIMIC-IV Raw Data
        ↓
Offline Data Processing Notebook
        ↓
Final Train / Val / Test Dataset
        ↓
Training Pipeline
        ↓
Evaluation Report
        ↓
Model Registry
        ↓
FastAPI Model Serving
        ↓
React Dashboard
        ↓
Prediction Logs / Monitoring
```

Các thành phần chính:

```text
backend/      FastAPI, database, authentication, prediction API
frontend/     React/Vite dashboard
mlops/        training, evaluation, model registry scripts
model/        trained model artifacts
data/         final dataset artifacts
reports/      training and evaluation reports
```

## 6. Cấu Trúc Project

```text
cnm-mlops/
├── backend/
│   └── app/
│       ├── api/
│       ├── core/
│       ├── models/
│       ├── schemas/
│       └── services/
│
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       └── pages/
│
├── mlops/
│   ├── configs/
│   │   └── model_config.yaml
│   └── training/
│       ├── train_pipeline.py
│       ├── evaluate.py
│       └── register_model.py
│
├── data/
├── model/
├── reports/
├── docker-compose.yml
└── README.md
```

## 7. Model Training

Project đã thử nghiệm các mô hình:

- Logistic Regression
- Random Forest
- XGBoost
- LightGBM

Mô hình được chọn để triển khai là **LightGBM**, vì đạt kết quả tổng thể tốt nhất trên tập test.

Cấu hình LightGBM:

```yaml
n_estimators: 300
learning_rate: 0.05
max_depth: -1
num_leaves: 31
subsample: 0.8
colsample_bytree: 0.8
objective: binary
class_weight: balanced
random_state: 42
```

Training pipeline nằm tại:

```text
mlops/training/train_pipeline.py
```

Chạy training:

```powershell
.\.venv\Scripts\python.exe mlops\training\train_pipeline.py
```

Output sau khi train:

```text
model/lightgbm/
├── lightgbm_model.pkl
├── lightgbm_imputer.pkl
├── lightgbm_feature_order.json
├── metrics.json
└── model_config.json
```

Reports:

```text
reports/
├── training_summary.json
├── lightgbm_threshold_tuning.csv
└── lightgbm_feature_importance.csv
```

## 8. Evaluation

Chạy evaluate:

```powershell
.\.venv\Scripts\python.exe mlops\training\evaluate.py
```

Kết quả LightGBM trên test set:

| Metric | Value |
|---|---:|
| Threshold | 0.70 |
| Accuracy | 0.8592 |
| Precision | 0.4331 |
| Recall | 0.5818 |
| F1-score | 0.4966 |
| ROC-AUC | 0.8414 |
| PR-AUC | 0.4645 |

Confusion matrix:

| | Pred 0 | Pred 1 |
|---|---:|---:|
| True 0 | 70,924 | 8,165 |
| True 1 | 4,484 | 6,238 |

Evaluation output:

```text
reports/evaluation_report.json
reports/confusion_matrix.csv
```

## 9. Model Registry

Model registry đơn giản được lưu dưới dạng JSON:

```text
model/model_registry.json
```

Register model:

```powershell
.\.venv\Scripts\python.exe mlops\training\register_model.py --backend file --status production
```

Script cũng hỗ trợ ghi vào database:

```powershell
.\.venv\Scripts\python.exe mlops\training\register_model.py --backend database --status production
```

Bảng database tương ứng:

```text
model_versions
```

## 10. Backend API

Backend sử dụng:

- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT authentication
- LightGBM model serving

Các endpoint chính:

| Endpoint | Chức năng |
|---|---|
| `POST /auth/login-json` | Đăng nhập |
| `GET /auth/me` | Lấy thông tin user |
| `POST /auth/change-password` | Đổi mật khẩu cá nhân |
| `GET /auth/users` | Admin xem danh sách người dùng |
| `POST /auth/users` | Admin tạo tài khoản bác sĩ/admin |
| `PATCH /auth/users/{user_id}/toggle-active` | Admin khóa/mở tài khoản |
| `POST /auth/users/{user_id}/reset-password` | Admin reset mật khẩu |
| `POST /predict` | Dự đoán nguy cơ AKI |
| `GET /patients/{subject_id}/{stay_id}/timeline` | Timeline bệnh nhân |
| `GET /patients/assignments` | Admin xem phân công bác sĩ - bệnh nhân |
| `POST /patients/assignments` | Admin phân công bệnh nhân cho bác sĩ |
| `DELETE /patients/assignments/{assignment_id}` | Admin xóa phân công |
| `GET /monitoring/summary` | Tổng quan monitoring |
| `GET /monitoring/recent` | Lịch sử dự đoán gần đây |
| `GET /monitoring/drift` | Kiểm tra tín hiệu drift |
| `GET /model/info` | Thông tin model đang triển khai |
| `GET /retraining/status` | Trạng thái retraining/model registry |
| `POST /retraining/trigger` | Kích hoạt retraining |

## 11. Frontend

Frontend sử dụng:

- React
- Vite
- Axios
- Recharts

Các màn hình chính:

- Login
- Dashboard
- Predict
- Patient Timeline
- Monitoring
- Model Info
- Drift Detection
- Retraining
- Account
- User Management

## 12. Cách Chạy Project

### 12.1. Chạy PostgreSQL

```powershell
docker compose up -d
```

PostgreSQL được cấu hình trong `docker-compose.yml`:

```text
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aki_mlops
PORT=5432
```

### 12.2. Cấu Hình Environment

Tạo file `.env` ở thư mục gốc:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aki_mlops
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
MODEL_DIR=model/lightgbm
MLFLOW_TRACKING_URI=http://localhost:5000
```

### 12.3. Cài Backend Dependencies

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Nếu LightGBM lỗi DLL trên Windows, cài **Microsoft Visual C++ Redistributable 2015-2022 x64** rồi kiểm tra:

```powershell
.\.venv\Scripts\python.exe -c "import lightgbm; print(lightgbm.__version__)"
```

### 12.4. Seed User Demo

```powershell
.\.venv\Scripts\python.exe backend\app\seed.py
```

Tài khoản demo:

| Role | Username | Password |
|---|---|---|
| Doctor | `doctor` | `doctor123` |
| Admin | `admin` | `admin123` |

Trong môi trường bệnh viện, bác sĩ không tự đăng ký công khai. Quản trị viên tạo tài khoản mới trong màn `Người dùng`, cấp mật khẩu tạm và có thể khóa/mở tài khoản khi cần. Người dùng đăng nhập xong có thể đổi mật khẩu trong màn `Tài khoản`.

Quản trị viên cũng phân công bệnh nhân cho bác sĩ theo cặp `subject_id` và `stay_id`. Admin có quyền xem tất cả bệnh nhân, còn doctor chỉ được dự đoán hoặc xem timeline của bệnh nhân đã được phân công.

### 12.5. Chạy Backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

API chạy tại:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

### 12.6. Chạy Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend chạy tại:

```text
http://localhost:5173
```

## 13. Quy Trình MLOps Trong Project

Các bước MLOps hiện có:

1. **Data validation**  
   Dataset final được kiểm tra leakage, missing, duplicate, infinite value và patient overlap.

2. **Training pipeline**  
   Script `train_pipeline.py` train LightGBM từ dataset final và lưu artifact.

3. **Threshold tuning**  
   Threshold được chọn trên validation set theo F1-score. Threshold tốt nhất là `0.70`.

4. **Evaluation**  
   Script `evaluate.py` đánh giá model trên test set và sinh report.

5. **Model registry**  
   Script `register_model.py` đăng ký model production vào registry.

6. **Serving**  
   FastAPI load model artifact và phục vụ realtime prediction.

7. **Monitoring**  
   Hệ thống lưu prediction logs, latency, risk level và hiển thị trên dashboard admin.

8. **Drift detection và retraining**  
   Admin có thể xem tín hiệu drift cơ bản và kích hoạt lại pipeline train/register model từ giao diện web.

## 14. Ghi Chú

- Project hiện sử dụng dataset final đã được xử lý offline để giảm thời gian chạy.
- Bước raw data processing từ MIMIC-IV được lưu ở notebook riêng và có thể trình bày trong phụ lục báo cáo.
- Model production hiện tại là `LightGBM v1.0.0`.
- Threshold cảnh báo hiện tại là `0.70`.

## 15. Bổ Sung MLOps

Project đã bổ sung thêm các thành phần MLOps nâng cao:

- **Experiment tracking**: `train_pipeline.py` hỗ trợ log params, metrics và artifacts lên MLflow nếu `mlflow.enabled=true` và MLflow server/package sẵn sàng.
- **Automated tests**: thư mục `tests/` kiểm tra feature engineering, input validation, model loader và phân quyền predict.
- **CI/CD**: workflow `.github/workflows/ci.yml` chạy backend tests và frontend build trên GitHub Actions.
- **Model promotion rule**: retraining train model candidate riêng, chỉ promote lên production nếu F1 và PR-AUC không thấp hơn model production hiện tại.
- **Monitoring nâng cao**: endpoint `/monitoring/advanced` cung cấp latency p95/p99, missing feature, phân phối model version và xu hướng theo ngày.
- **Offline raw data documentation**: `mlops/data/README.md` mô tả rõ quy trình xử lý MIMIC-IV offline và dataset final dùng trong project chính.
