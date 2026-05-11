# Offline Data Preparation

This project keeps the raw MIMIC-IV processing step outside the main serving
application because the original dataset is large and slow to rebuild on a
normal demo machine.

## Raw Dataset

The raw data source used for the project is:

```text
/kaggle/input/datasets/mangeshwagle/mimic-iv-2-1/mimic-iv-2.1
```

The offline notebooks use these MIMIC-IV tables:

```text
hosp/patients.csv
icu/icustays.csv
hosp/labevents.csv
```

## Offline Notebooks

The raw-to-final data flow is:

```text
01-build-dataset-cnm.ipynb
  -> train_final_with_meta.parquet
  -> val_final_with_meta.parquet
  -> test_final_with_meta.parquet

process_data.ipynb
  -> train_dataset_final.parquet
  -> val_dataset_final.parquet
  -> test_dataset_final.parquet
  -> features_dataset_final.json

check_data.ipynb
  -> dataset quality checks
```

## Final Dataset Used By MLOps Pipeline

The main MLOps project starts from the final, validated dataset:

```text
data/train_dataset_final.parquet
data/val_dataset_final.parquet
data/test_dataset_final.parquet
data/features_dataset_final.json
data/dataset_final_report.json
```

This keeps the training, evaluation, registry, serving, monitoring, drift
detection, and retraining workflow reproducible without requiring a full
MIMIC-IV rebuild during every demo.

## Label Definition

Each sample predicts AKI risk in the next 24 hours from the previous 24 hours
of lab data. The positive label is assigned when future creatinine satisfies
at least one condition:

```text
future_max_creatinine - baseline_creatinine >= 0.3
future_max_creatinine / baseline_creatinine >= 1.5
```

## Final Feature Policy

The final realtime-compatible feature set keeps:

```text
*_last
*_delta
*_is_missing
hours_since_icu_intime
gender_male
```

The final feature order is stored in:

```text
data/features_dataset_final.json
model/lightgbm/lightgbm_feature_order.json
```
