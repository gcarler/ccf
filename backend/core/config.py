from functools import lru_cache
from typing import Dict, List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration."""

    environment: str = Field(default="local")
    database_url: str = Field(
        default="sqlite:///" + __file__.replace("config.py", "../ccf_final.db")
    )
    secret_key: str = Field(default="change-me")
    access_token_expire_minutes: int = Field(default=60 * 24)
    refresh_token_expire_days: int = Field(default=30)

    cors_origins: List[str] = Field(default_factory=lambda: ["*"])
    redis_url: str = Field(default="redis://localhost:6379/0")
    kafka_bootstrap_servers: str = Field(default="localhost:19092")

    uploads_dir: str = Field(default="uploads")
    analytics_db_path: str = Field(default="analytics/warehouse.duckdb")
    enable_otel: bool = Field(default=False)
    otel_endpoint: str = Field(default="http://localhost:4317")
    feature_flags: Dict[str, bool] = Field(default_factory=dict)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
