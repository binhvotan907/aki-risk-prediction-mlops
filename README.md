# Real-time AKI Risk Prediction

Đồ án xây dựng hệ thống phân tích dữ liệu xét nghiệm theo thời gian thực nhằm dự đoán nguy cơ suy thận cấp. Hệ thống sử dụng dữ liệu MIMIC-IV để xây dựng bộ dữ liệu huấn luyện, so sánh nhiều mô hình học máy và chọn LightGBM làm mô hình triển khai. Bên cạnh chức năng dự đoán, project còn có các thành phần phục vụ quản lý vòng đời mô hình như tracking, registry, monitoring, drift detection, retraining, kiểm thử tự động và public thử nghiệm bằng Cloudflare Tunnel.

## 1. Mục tiêu đề tài

- Xây dựng mô hình dự đoán nguy cơ suy thận cấp dựa trên dữ liệu xét nghiệm lâm sàng.
- Dự đoán nguy cơ trong 24 giờ tiếp theo dựa trên lịch sử xét nghiệm 24 giờ trước đó.
- Triển khai mô hình dưới dạng API dự đoán thời gian thực bằng FastAPI.
- Xây dựng giao diện web cho quản trị viên và bác sĩ.
- Lưu dữ liệu xét nghiệm, lịch sử dự đoán, latency và phiên bản mô hình vào PostgreSQL.
- Theo dõi hoạt động hệ thống, phát hiện drift và hỗ trợ huấn luyện lại mô hình.
- Tích hợp MLflow, Prometheus, Grafana, pgAdmin, Evidently, Pytest và GitHub Actions.

## 2. Dataset

Dataset gốc:

```text
MIMIC-IV v2.1
/kaggle/input/datasets/mangeshwagle/mimic-iv-2-1
```

Các bảng chính được sử dụng:

- `patients.csv`
- `icustays.csv`
- `labevents.csv`

15 chỉ số xét nghiệm đầu vào:

```text
creatinine, bun, sodium, potassium, chloride, bicarbonate,
glucose, calcium, magnesium, phosphate, anion_gap,
hemoglobin, hematocrit, wbc, platelets
```

Do dữ liệu MIMIC-IV có kích thước lớn, bước xử lý dữ liệu thô được thực hiện offline bằng notebook riêng. Project chính sử dụng dataset final đã được chuẩn hóa trong thư mục `data/`.

```text
data/
├── train_dataset_final.parquet
├── val_dataset_final.parquet
├── test_dataset_final.parquet
├── features_dataset_final.json
└── dataset_final_report.json
```

Kích thước dữ liệu final:

| Split | Rows | Columns | Positive rate |
|---|---:|---:|---:|
| Train | 428,997 | 47 | 11.30% |
| Validation | 89,418 | 47 | 11.02% |
| Test | 89,811 | 47 | 11.94% |

Số feature dùng để huấn luyện mô hình: `43`.

## 3. Định nghĩa nhãn AKI

Tại mỗi thời điểm dự đoán, hệ thống lấy dữ liệu xét nghiệm trong 24 giờ trước đó để tạo feature. Nhãn AKI được xác định dựa trên creatinine trong 24 giờ tiếp theo.

Một sample được gán nhãn AKI nếu thỏa một trong hai điều kiện:

```text
future_max_creatinine - baseline_creatinine >= 0.3
```

hoặc:

```text
future_max_creatinine / baseline_creatinine >= 1.5
```

Trong đó:

- `baseline_creatinine`: giá trị creatinine nền trong cửa sổ quá khứ.
- `future_max_creatinine`: giá trị creatinine lớn nhất trong cửa sổ tương lai 24 giờ.

## 4. Feature engineering

Từ 15 chỉ số xét nghiệm gốc, hệ thống tạo các đặc trưng phù hợp cho bài toán dự đoán thời gian thực:

- Feature dạng `_last`: giá trị xét nghiệm gần nhất.
- Feature dạng `_delta`: mức thay đổi so với lần xét nghiệm trước.
- Feature dạng `_is_missing`: đánh dấu dữ liệu thiếu.
- `hours_since_icu_intime`: thời gian kể từ lúc vào ICU.
- `gender_male`: đặc trưng nhị phân biểu diễn giới tính nam.

Ví dụ:

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

## 5. Pipeline tổng thể

```text
MIMIC-IV
  ↓
Offline data processing
  ↓
Final train / validation / test dataset
  ↓
Training and evaluation
  ↓
MLflow tracking / model registry
  ↓
FastAPI realtime serving
  ↓
React dashboard
  ↓
PostgreSQL lab events / prediction logs
  ↓
Monitoring / drift detection
  ↓
Build retraining dataset from lab_events
  ↓
Retraining / promote model
```

## 6. Cấu trúc project

```text
cnm-mlops/
├── backend/                         # FastAPI backend phục vụ API, xác thực, dự đoán và ghi log
│   └── app/
│       ├── api/                     # Các endpoint: auth, predict, patients, monitoring, retraining
│       ├── core/                    # Cấu hình hệ thống, database, security, Prometheus metrics
│       ├── models/                  # SQLAlchemy models ánh xạ các bảng PostgreSQL
│       ├── schemas/                 # Pydantic schemas validate dữ liệu request/response
│       └── services/                # Logic nghiệp vụ: feature engineering, load model, kiểm tra quyền
│
├── frontend/                        # React/Vite dashboard cho admin và bác sĩ
│   └── src/
│       ├── api/                     # Axios client gọi backend API
│       ├── components/              # Layout và component dùng chung
│       └── pages/                   # Các màn hình: login, predict, timeline, monitoring, drift...
│
├── mlops/                           # Pipeline huấn luyện, đánh giá, registry và drift report
│   ├── configs/                     # File cấu hình training/model
│   ├── monitoring/                  # Script tạo drift report bằng PSI/Evidently
│   └── training/                    # Script build dataset, train, evaluate và register model
│
├── monitoring/                      # Cấu hình Prometheus và Grafana
│   ├── grafana/                     # Datasource, dashboard và provisioning cho Grafana
│   └── prometheus/                  # Cấu hình scrape metrics từ FastAPI
│
├── data/                            # Dataset final train/val/test và danh sách feature
├── data+model/                      # Notebook xử lý dữ liệu và thử nghiệm các mô hình
├── model/                           # Model production, imputer, feature order, metrics, registry
├── reports/                         # Báo cáo training, evaluation, confusion matrix, drift report
├── tests/                           # Pytest kiểm tra feature engineering, validation, model loader, phân quyền
├── docker-compose.yml               # Chạy toàn bộ stack: backend, frontend, DB và monitoring
└── README.md                        # Tài liệu mô tả project và hướng dẫn chạy hệ thống
```

## 7. Công nghệ sử dụng

| Nhóm | Công nghệ |
|---|---|
| Xử lý dữ liệu | Python, Pandas, NumPy, Parquet, JSON |
| Huấn luyện mô hình | Scikit-learn, LightGBM, XGBoost, Random Forest, Logistic Regression |
| Lưu artifact | Joblib, JSON |
| Backend API | FastAPI, Uvicorn, Pydantic |
| Database | PostgreSQL, SQLAlchemy, pgAdmin |
| Frontend | React, Vite, Axios, Recharts |
| Tracking và registry | MLflow, JSON registry, bảng `model_versions` |
| Monitoring | Prometheus, Grafana, FastAPI monitoring endpoints |
| Drift detection | Pandas, NumPy, Evidently, PSI |
| Kiểm thử | Pytest |
| CI | GitHub Actions |
| Public demo | Cloudflare Tunnel |
| Local deployment | Docker Compose |

## 8. Model training

Các mô hình đã thử nghiệm:

- Logistic Regression
- Random Forest
- XGBoost
- LightGBM

Mô hình được chọn để triển khai là **LightGBM** vì đạt kết quả tổng thể tốt nhất trên tập test.

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

Chạy training:

```powershell
.\.venv\Scripts\python.exe mlops\training\train_pipeline.py
```

Artifacts:

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

## 9. Retraining từ dữ liệu vận hành

Ngoài dataset final trong thư mục `data/`, project hỗ trợ tạo dữ liệu huấn luyện bổ sung từ bảng `lab_events` trong PostgreSQL khi admin kích hoạt retraining.

Luồng retraining:

```text
lab_events trong PostgreSQL
  ↓
Tạo feature từ cửa sổ 24 giờ quá khứ
  ↓
Sinh nhãn AKI từ creatinine trong 24 giờ tương lai
  ↓
Tạo production_labeled_samples.parquet
  ↓
Ghép với train_dataset_final.parquet nếu đủ số sample tối thiểu
  ↓
Train candidate LightGBM
  ↓
So sánh candidate với production model bằng F1-score và PR-AUC
  ↓
Promote nếu đạt, nếu không giữ production model hiện tại
```

Script tạo dataset retraining:

```text
mlops/training/build_dataset_from_postgres.py
```

Khi chạy `POST /retraining/trigger`, backend sẽ tự gọi script trên trước khi train candidate model. Nếu số sample có nhãn từ `lab_events` đạt ngưỡng tối thiểu, hệ thống tạo:

```text
data/retraining/lightgbm_<run_id>/production_labeled_samples.parquet
data/retraining/lightgbm_<run_id>/train_augmented.parquet
```

Nếu chưa đủ dữ liệu mới, hệ thống fallback về dataset final ban đầu để retraining vẫn chạy được trong môi trường demo.

## 10. Evaluation

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

## 11. Model registry

Project hỗ trợ hai mức registry:

- `model/model_registry.json`: registry dạng file JSON.
- `model_versions`: bảng database lưu thông tin phiên bản mô hình.
- MLflow Model Registry: đăng ký model `AKI-LightGBM` khi chạy script register.

Register model:

```powershell
.\.venv\Scripts\python.exe mlops\training\register_model.py --backend file --status production
```

Hoặc ghi vào database:

```powershell
.\.venv\Scripts\python.exe mlops\training\register_model.py --backend database --status production
```

## 12. Backend API

Backend sử dụng FastAPI, SQLAlchemy, PostgreSQL, JWT authentication và LightGBM model serving.

Các endpoint chính:

| Endpoint | Chức năng |
|---|---|
| `POST /auth/login` | Đăng nhập OAuth2 cho Swagger |
| `POST /auth/login-json` | Đăng nhập từ frontend |
| `GET /auth/me` | Lấy thông tin người dùng hiện tại |
| `POST /auth/change-password` | Đổi mật khẩu cá nhân |
| `GET /auth/users` | Admin xem danh sách người dùng |
| `POST /auth/users` | Admin tạo tài khoản |
| `PATCH /auth/users/{user_id}/toggle-active` | Admin khóa hoặc mở tài khoản |
| `POST /auth/users/{user_id}/reset-password` | Admin reset mật khẩu |
| `DELETE /auth/users/{user_id}` | Admin xóa tài khoản |
| `GET /patients` | Danh sách bệnh nhân |
| `POST /patients` | Admin tạo bệnh nhân |
| `GET /patients/assignments` | Admin xem danh sách phân công |
| `POST /patients/assignments` | Admin phân công bệnh nhân cho bác sĩ |
| `DELETE /patients/assignments/{assignment_id}` | Admin xóa phân công |
| `DELETE /patients/{subject_id}/{stay_id}/records` | Admin xóa dữ liệu xét nghiệm và prediction logs |
| `DELETE /patients/{subject_id}/{stay_id}` | Admin xóa bệnh nhân, phân công và dữ liệu liên quan |
| `GET /patients/my-assignments` | Bác sĩ xem bệnh nhân được phân công |
| `GET /patients/{subject_id}/{stay_id}/timeline` | Timeline bệnh nhân |
| `POST /predict` | Bác sĩ dự đoán nguy cơ AKI |
| `GET /model/info` | Admin xem thông tin model đang triển khai |
| `GET /monitoring/summary` | Tổng quan monitoring |
| `GET /monitoring/advanced` | Monitoring nâng cao |
| `GET /monitoring/recent` | Lịch sử dự đoán gần đây |
| `GET /monitoring/drift` | Kiểm tra tín hiệu drift |
| `GET /retraining/status` | Trạng thái retraining/model registry |
| `POST /retraining/trigger` | Kích hoạt retraining |
| `GET /metrics` | Metrics cho Prometheus |

## 13. Frontend

Frontend sử dụng React, Vite, Axios và Recharts.

Màn hình chung:

- Login
- Dashboard
- Bệnh nhân
- Timeline
- Tài khoản

Màn hình dành cho bác sĩ:

- Dự đoán nguy cơ AKI
- Xem bệnh nhân được phân công
- Xem timeline bệnh nhân

Màn hình dành cho quản trị viên:

- Quản lý bệnh nhân
- Quản lý người dùng
- Thông tin mô hình
- Monitoring
- Drift Detection
- Retraining

Frontend gọi backend qua biến môi trường:

```text
VITE_API_BASE_URL
```

Nếu không cấu hình biến này, frontend mặc định gọi:

```text
http://127.0.0.1:8000
```

## 14. Chạy nhanh bằng Docker Compose

Nếu muốn chạy toàn bộ hệ thống bằng một lệnh, dùng:

```powershell
docker-compose up --build -d
```

Lệnh trên sẽ khởi động các thành phần sau:

| Thành phần | URL |
|---|---|
| React App | `http://localhost:5173` |
| FastAPI Backend | `http://127.0.0.1:8000` |
| FastAPI Swagger | `http://127.0.0.1:8000/docs` |
| PostgreSQL | `localhost:5432` |
| pgAdmin | `http://localhost:5050` |
| MLflow | `http://localhost:5000` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

Sau khi chạy lệnh trên, service `seed` sẽ tự tạo tài khoản demo:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Doctor | `doctor` | `doctor123` |

Kiểm tra trạng thái container:

```powershell
docker-compose ps
```

Dừng toàn bộ hệ thống:

```powershell
docker-compose down
```

## 15. Chạy project local thủ công

### 15.1. Chạy Docker services

```powershell
docker-compose up -d
```

Các service trong Docker Compose:

| Service | URL |
|---|---|
| PostgreSQL | `localhost:5432` |
| pgAdmin | `http://localhost:5050` |
| MLflow | `http://localhost:5000` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |

Tài khoản Grafana:

```text
admin / admin123
```

Tài khoản pgAdmin:

```text
admin@example.com / admin123
```

### 15.2. Cấu hình `.env`

Tạo file `.env` ở thư mục gốc:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aki_mlops
SECRET_KEY=aki-mlops-secret-key-2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

MODEL_DIR=model/lightgbm
MLFLOW_TRACKING_URI=http://localhost:5000
```

### 15.3. Cài backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Nếu LightGBM lỗi DLL trên Windows, cài Microsoft Visual C++ Redistributable 2015-2022 x64.

### 15.4. Seed tài khoản demo

```powershell
.\.venv\Scripts\python.exe backend\app\seed.py
```

Tài khoản demo:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Doctor | `doctor` | `doctor123` |

### 15.5. Chạy backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### 15.6. Chạy frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## 16. Public thử nghiệm bằng Cloudflare Tunnel

Cloudflare Tunnel được dùng để public tạm thời frontend và backend ra internet mà không cần thuê server cloud.

### 16.1. Cài cloudflared

```powershell
winget install --id Cloudflare.cloudflared
cloudflared --version
```

### 16.2. Tạo tunnel cho backend

Đảm bảo backend đang chạy tại `http://127.0.0.1:8000`, sau đó mở PowerShell mới:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflare sẽ sinh URL dạng:

```text
https://<backend-tunnel>.trycloudflare.com
```

Kiểm tra:

```text
https://<backend-tunnel>.trycloudflare.com/docs
```

### 16.3. Chạy frontend với backend tunnel

```powershell
cd frontend
$env:VITE_API_BASE_URL="https://<backend-tunnel>.trycloudflare.com"
npm run dev -- --host 127.0.0.1
```

### 16.4. Tạo tunnel cho frontend

Mở PowerShell mới:

```powershell
cloudflared tunnel --url http://127.0.0.1:5173
```

Cloudflare sẽ sinh URL dạng:

```text
https://<frontend-tunnel>.trycloudflare.com
```

Đây là link public để demo giao diện web.

Lưu ý:

- Link quick tunnel có thể thay đổi mỗi lần chạy.
- Cần giữ terminal `cloudflared` mở trong lúc demo.
- Đây là public thử nghiệm, không phải deployment production cố định.

## 17. Kiểm thử

Chạy test local:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

Chạy test bằng Docker Compose:

```powershell
docker-compose run --rm backend pytest tests
```

Các nhóm test chính:

- Feature engineering.
- Input validation.
- Model loader.
- Phân quyền predict.
- Tạo dataset retraining từ `lab_events` và sinh nhãn AKI từ creatinine tương lai.

## 18. CI bằng GitHub Actions

Workflow:

```text
.github/workflows/ci.yml
```

CI kiểm tra:

- Backend tests bằng Pytest.
- Frontend build bằng Vite.

## 19. Quy trình vận hành mô hình trong project

1. **Data validation**: kiểm tra leakage, missing, duplicate, infinite value và patient overlap.
2. **Training pipeline**: huấn luyện LightGBM từ dataset final.
3. **Threshold tuning**: chọn threshold trên validation set theo F1-score.
4. **Evaluation**: đánh giá model trên test set.
5. **Model registry**: đăng ký model production.
6. **Serving**: FastAPI load model artifact và phục vụ dự đoán thời gian thực.
7. **Logging**: lưu lab events và prediction logs vào PostgreSQL.
8. **Monitoring**: theo dõi prediction count, risk level, latency, missing feature và model version.
9. **Drift detection**: kiểm tra tín hiệu drift bằng dashboard và Evidently report.
10. **Build retraining dataset**: tạo sample huấn luyện bổ sung từ `lab_events` nếu có đủ dữ liệu 24 giờ tương lai để sinh nhãn AKI.
11. **Retraining**: admin kích hoạt huấn luyện lại candidate model và promote model nếu đạt điều kiện.

## 20. Ghi chú

- Project sử dụng dataset final đã xử lý offline để giảm thời gian chạy.
- Retraining hiện là admin-triggered; tự động chạy định kỳ bằng scheduler/Airflow là hướng mở rộng tiếp theo.
- Notebook xử lý raw MIMIC-IV và notebook huấn luyện thử nghiệm được lưu ở workspace riêng.
- Model production hiện tại là `LightGBM v1.0.0`.
- Threshold cảnh báo hiện tại là `0.70`.
- Cloudflare Tunnel chỉ dùng để demo truy cập từ bên ngoài, không thay thế deployment production.
