from functools import lru_cache
from typing import Dict, List

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration."""

    environment: str = Field(default="local", validation_alias=AliasChoices("environment", "ENV"))
    database_url: str = Field(
        default="postgresql+pg8000://postgres:admin123@localhost:5435/ccf_db"
    )
    secret_key: str = Field(default="change-me")
    encryption_key: str | None = Field(default=None)
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=30)
    access_token_cookie_name: str = Field(default="mesh_access")
    access_token_cookie_secure: bool = Field(default=False)

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    kafka_bootstrap_servers: str = Field(default="localhost:19092")

    uploads_dir: str = Field(default="uploads")
    analytics_db_path: str = Field(default="analytics/warehouse.duckdb")
    enable_otel: bool = Field(default=False)
    otel_endpoint: str = Field(default="http://localhost:4317")
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    password_reset_expire_minutes: int = Field(default=60)
    email_verification_expire_hours: int = Field(default=48)
    run_startup_schema_fixes: bool = Field(default=False)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_security_defaults(self) -> "Settings":
        env = (self.environment or "local").strip().lower()
        insecure_secrets = {"", "change-me", "replace-me", "ci-test-only-key"}

        if env in {"production", "prod", "staging"} and self.secret_key in insecure_secrets:
            raise ValueError("SECRET_KEY must be set to a strong value outside local/test environments")

        if env in {"production", "prod", "staging"} and not self.access_token_cookie_secure:
            self.access_token_cookie_secure = True

        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")

        if self.refresh_token_expire_days <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than zero")

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
