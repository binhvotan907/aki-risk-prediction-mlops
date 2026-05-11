import json
import joblib
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3]
MODEL_DIR = BASE_DIR / "model" / "lightgbm"


class ModelLoader:
    def __init__(self):
        self.model = None
        self.imputer = None
        self.feature_order = None
        self.metrics = None
        self.config = None

    def load(self):
        self.model = joblib.load(MODEL_DIR / "lightgbm_model.pkl")
        self.imputer = joblib.load(MODEL_DIR / "lightgbm_imputer.pkl")

        with open(MODEL_DIR / "lightgbm_feature_order.json", "r", encoding="utf-8") as f:
            self.feature_order = json.load(f)

        with open(MODEL_DIR / "metrics.json", "r", encoding="utf-8") as f:
            self.metrics = json.load(f)

        with open(MODEL_DIR / "model_config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)

        return self

    @property
    def threshold(self):
        return self.config.get("threshold", 0.70)

    @property
    def model_name(self):
        return self.config.get("model_name", "LightGBM")

    @property
    def model_version(self):
        return self.config.get("version", "v1.0.0")


model_loader = ModelLoader()