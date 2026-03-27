from functools import lru_cache
from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration."""

    environment: str = Field(default="local")
    database_url: str = Field(
        default="postgresql+pg8000://postgres:admin123@localhost:5435/ccf_db"
    )
    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = Field(default=60 * 24)
    refresh_token_expire_days: int = Field(default=30)
    access_token_cookie_name: str = Field(default="mesh_access")
    access_token_cookie_secure: bool = Field(default=False)

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    redis_url: str = Field(default="redis://localhost:6379/0")
    kafka_bootstrap_servers: str = Field(default="localhost:19092")

    uploads_dir: str = Field(default="uploads")
    analytics_db_path: str = Field(default="analytics/warehouse.duckdb")
    enable_otel: bool = Field(default=False)
    otel_endpoint: str = Field(default="http://localhost:4317")
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    password_reset_expire_minutes: int = Field(default=60)
    email_verification_expire_hours: int = Field(default=48)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
