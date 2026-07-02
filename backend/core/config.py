from functools import lru_cache
from typing import Dict, List

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime configuration.

    Security defaults are intentionally weak for local dev.
    The model_validator enforces strong values in staging/prod.
    """

    environment: str = Field(default="local")
    database_url: str = Field(
        default="sqlite:///./ccf_dev.db",
        description="DB URL - must be PostgreSQL in prod/staging (enforced by validator).",
    )
    secret_key: str = Field(default="change-me")
    encryption_key: str | None = Field(default=None)
    access_token_expire_minutes: int = Field(
        default=15
    )  # 15 min sessions; refresh via HttpOnly cookies
    refresh_token_expire_days: int = Field(
        default=180
    )  # 180 days refresh window (Gmail-like)
    access_token_cookie_name: str = Field(default="mesh_access")
    refresh_token_cookie_name: str = Field(default="mesh_refresh")
    access_token_cookie_secure: bool = Field(default=False)

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3005",
            "http://127.0.0.1:3005",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    kafka_bootstrap_servers: str = Field(default="localhost:19092")

    uploads_dir: str = Field(default="uploads")
    image_max_width: int = Field(default=1920, description="Max width for image optimization (px)")
    image_quality: int = Field(default=82, description="WebP quality 1-100 for optimized images")
    analytics_db_path: str = Field(default="analytics/warehouse.duckdb")
    enable_otel: bool = Field(default=False)
    otel_endpoint: str = Field(default="http://localhost:4317")
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    password_reset_expire_minutes: int = Field(default=60)
    email_verification_expire_hours: int = Field(default=48)

    # SMTP Email
    smtp_host: str = Field(default="localhost")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="noreply@ccfministerio.com")
    smtp_from_name: str = Field(default="CCF Ministerio")
    smtp_use_tls: bool = Field(default=True)
    frontend_url: str = Field(default="http://localhost:3000")

    # Stub / Mock mode — bloquea comunicaciones externas (email, SMS, WhatsApp)
    # True = ningún mensaje sale al exterior (solo se registra en CommunicationLog)
    # Excepción: email a TEST_EMAIL_OVERRIDE si está configurado
    stub_comms: bool = Field(default=False, description="Block all external communications; log only")
    test_email_override: str = Field(
        default="",
        description="Email exception for stub mode — only this address receives real email",
    )

    # Google OAuth
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")

    # MercadoPago
    mercadopago_access_token: str = Field(default="")
    mercadopago_public_key: str = Field(default="")

    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/auth/google/callback"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @model_validator(mode="after")
    def validate_security_defaults(self) -> "Settings":
        env = (self.environment or "local").strip().lower()
        insecure_secrets = {"", "change-me", "replace-me", "ci-test-only-key"}

        if (
            env in {"production", "prod", "staging"}
            and self.secret_key in insecure_secrets
        ):
            raise ValueError(
                "SECRET_KEY must be set to a strong value outside local/test"
                " environments"
            )

        if env in {"production", "prod", "staging"} and not self.encryption_key:
            raise ValueError("ENCRYPTION_KEY must be set in production environments")

        # Warn if encryption_key is missing in non-local envs (staging already
        # blocked above; this covers custom env names like "qa", "pre-prod", etc.)
        if env not in {"local", "test", "testing", "ci"} and not self.encryption_key:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "ENCRYPTION_KEY is not set - encryption will fall back to SECRET_KEY. "
                "Set ENCRYPTION_KEY for proper key separation."
            )

        # Warn if SMTP is unconfigured in non-local environments
        if env not in {"local", "test", "testing", "ci"} and (
            not self.smtp_host or self.smtp_host == "localhost"
        ):
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "SMTP is not configured - email verification and password reset "
                "emails will not be delivered. Configure SMTP_HOST / SMTP_USER / SMTP_PASSWORD."
            )

        if (
            env in {"production", "prod", "staging"}
            and not self.access_token_cookie_secure
        ):
            self.access_token_cookie_secure = True

        if env not in {"local", "test", "testing", "ci"} and self.database_url.startswith("sqlite"):
            raise ValueError("SQLite is not supported in non-local environments")

        if self.access_token_expire_minutes <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be greater than zero")

        if self.refresh_token_expire_days <= 0:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be greater than zero")

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()
