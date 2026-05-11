from pathlib import Path
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    model_dir: str = "model/lightgbm"
    mlflow_tracking_uri: str = "http://localhost:5000"

    class Config:
        env_file = ENV_PATH
        env_file_encoding = "utf-8"


settings = Settings()