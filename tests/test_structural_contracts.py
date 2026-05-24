import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app import app
from backend.core.config import Settings

ALLOWED_NON_API_PATHS = {
    "/",
    "/healthz",
    "/docs",
    "/docs/oauth2-redirect",
    "/openapi.json",
    "/redoc",
}

FORBIDDEN_ROOT_PREFIXES = (
    "/agents",
    "/messaging",
    "/governance",
    "/auth",
)


def test_all_application_routes_stay_under_api_tree_or_explicit_exceptions():
    paths = {route.path for route in app.routes if getattr(route, "path", None)}

    invalid_paths = sorted(
        path
        for path in paths
        if not path.startswith("/api/") and path not in ALLOWED_NON_API_PATHS
    )

    assert invalid_paths == []

    forbidden_aliases = sorted(
        path
        for path in paths
        if any(
            path == prefix or path.startswith(prefix + "/")
            for prefix in FORBIDDEN_ROOT_PREFIXES
        )
    )

    assert forbidden_aliases == []
    forbidden_legacy_api_paths = sorted(
        path
        for path in paths
        if path in {"/api/announcements", "/api/testimonials", "/api/analytics/summary"}
    )
    assert forbidden_legacy_api_paths == []


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_settings_rejects_trivial_secret_keys_in_restricted_environments(
    environment: str,
):
    for secret in ("", "change-me", "replace-me", "ci-test-only-key"):
        with pytest.raises(ValidationError):
            Settings(environment=environment, secret_key=secret)


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_settings_force_secure_access_cookie_in_restricted_environments(
    environment: str,
):
    settings = Settings(
        environment=environment,
        secret_key="strong-secret-value",
        encryption_key="dummy-key-for-test",
        database_url="postgresql://user:pass@remote-db:5432/db",
        redis_url="redis://remote-redis:6379/0",
        access_token_cookie_secure=False,
    )
    assert settings.access_token_cookie_secure is True


def test_settings_accepts_env_alias_input():
    settings = Settings.model_validate(
        {
            "ENV": "staging",
            "secret_key": "strong-secret-value",
            "encryption_key": "dummy-key-for-test",
            "database_url": "postgresql://user:pass@remote-db:5432/db",
            "redis_url": "redis://remote-redis:6379/0",
        }
    )
    assert settings.environment == "staging"


import pytest


@pytest.mark.skip(reason="No se usa Docker en este proyecto")
def test_docker_compose_requires_mandatory_secrets_and_canonical_environment_key():
    compose = Path(__file__).resolve().parents[1] / "docker-compose.yml"
    content = compose.read_text(encoding="utf-8")

    assert "SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY}" in content
    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}" in content
    assert (
        "MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?set MINIO_ROOT_PASSWORD}"
        in content
    )
    assert "environment: production" in content
    assert "ENV: production" not in content


def test_routes_do_not_collide_by_method_and_normalized_path():
    seen: dict[tuple[str, tuple[str, ...]], list[str]] = {}

    for route in app.routes:
        path = getattr(route, "path", None)
        methods = tuple(sorted(getattr(route, "methods", []) or []))
        endpoint = getattr(route, "endpoint", None)
        if not path or endpoint is None:
            continue

        normalized_path = re.sub(r"\{[^}]+\}", "{}", path)
        key = (normalized_path, methods)
        seen.setdefault(key, []).append(
            f"{path} -> {endpoint.__module__}.{endpoint.__name__}"
        )

    collisions = {
        f"{methods} {path}": owners
        for (path, methods), owners in seen.items()
        if len(owners) > 1
    }

    assert collisions == {}


def test_domain_modules_expose_only_expected_canonical_prefixes():
    module_prefix_rules = {
        "backend.api.cms": ("/api/cms/", "/api/admin/"),
        "backend.api.cms_v2": ("/api/cms/v2/",),
        "backend.api.content": ("/api/content",),
        "backend.api.agents": ("/api/agents/",),
        "backend.api.assets": ("/api/assets",),
        "backend.api.spiritual_life": ("/api/spiritual-life/",),
        "backend.api.community": ("/api/community/",),
        "backend.api.dashboard": ("/api/dashboard/",),
        "backend.api.analytics": ("/api/analytics/",),
    }

    violations: dict[str, list[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        if not path or endpoint is None:
            continue

        module = endpoint.__module__
        expected_prefixes = module_prefix_rules.get(module)
        if not expected_prefixes:
            continue

        if not any(path.startswith(prefix) for prefix in expected_prefixes):
            violations.setdefault(module, []).append(path)

    assert violations == {}
