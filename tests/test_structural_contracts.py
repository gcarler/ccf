import inspect
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
    forbidden_old_api_paths = sorted(
        path
        for path in paths
        if path in {
            "/api/announcements",
            "/api/testimonials",
            "/api/analytics/summary",
            "/api/content",
            "/api/auth/v2",
            "/api/academy/users",
        }
        or path.startswith("/api/content/")
        or path.startswith("/api/auth/v2/")
        or path.startswith("/api/academy/users/")
    )
    assert forbidden_old_api_paths == []


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
        "backend.api.agents": ("/api/agents",),
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


def _dependency_names(route):
    names = set()

    def walk(dependant):
        for dependency in getattr(dependant, "dependencies", []) or []:
            call = getattr(dependency, "call", None)
            if call is not None:
                names.add(getattr(call, "__name__", repr(call)))
            walk(dependency)

    walk(getattr(route, "dependant", None))
    return names


def test_dashboard_routes_require_authenticated_user():
    protected = {
        route.path: _dependency_names(route)
        for route in app.routes
        if getattr(route, "path", "") in {"/api/dashboard/{module}", "/api/dashboard/modules/list"}
    }

    assert protected
    for path, dependencies in protected.items():
        assert dependencies & {"get_current_user", "get_current_active_user"}, path


def test_internal_routes_do_not_accept_client_sede_id_query():
    checked_modules = {
        "backend.api.dashboard",
        "backend.api.agenda_core",
        "backend.api.crm_core",
        "backend.api.evangelism_grupos",
        "backend.api.evangelism_multiplication",
        "backend.api.evangelism_rankings",
    }
    violations = []

    for route in app.routes:
        endpoint = getattr(route, "endpoint", None)
        if endpoint is None or endpoint.__module__ not in checked_modules:
            continue
        if "sede_id" in inspect.signature(endpoint).parameters:
            violations.append(f"{route.path} -> {endpoint.__module__}.{endpoint.__name__}")

    assert violations == []


def test_app_lifespan_does_not_bootstrap_schema_with_create_all():
    app_py = Path(__file__).resolve().parents[1] / "backend" / "app.py"
    assert "create_all(" not in app_py.read_text(encoding="utf-8")


def test_frontend_does_not_add_auth_users_old_consumers():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "frontend" / "src" / "app" / "plataforma",
        root / "frontend" / "src" / "components",
        root / "frontend" / "src" / "hooks",
    ]
    user_list_allowlist = set()
    violations = []

    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = path.relative_to(root).as_posix()
            content = path.read_text(encoding="utf-8")
            if "/auth/users" in content:
                violations.append(f"{rel} uses /auth/users")
            if "/auth/user-list" in content and rel not in user_list_allowlist:
                violations.append(f"{rel} uses /auth/user-list outside allowlist")

    assert violations == []


def test_frontend_does_not_add_academy_user_id_old_consumers():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "frontend" / "src" / "app" / "plataforma",
        root / "frontend" / "src" / "components",
        root / "frontend" / "src" / "hooks",
    ]
    allowlist = set()
    violations = []

    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = path.relative_to(root).as_posix()
            content = path.read_text(encoding="utf-8")
            if "/academy/users/" in content and rel not in allowlist:
                violations.append(f"{rel} uses /academy/users outside allowlist")

    assert violations == []


def test_platform_frontend_uses_persona_uuid_for_cms_and_audit_identity_labels():
    root = Path(__file__).resolve().parents[1]
    files = [
        root / "frontend" / "src" / "app" / "plataforma" / "cms" / "testimonials" / "page.tsx",
        root / "frontend" / "src" / "app" / "plataforma" / "cms" / "testimonials" / "[id]" / "page.tsx",
        root / "frontend" / "src" / "app" / "plataforma" / "admin" / "audit" / "page.tsx",
    ]
    violations = []
    for path in files:
        content = path.read_text(encoding="utf-8")
        rel = path.relative_to(root).as_posix()
        if rel.endswith("cms/testimonials/page.tsx") and "author_persona_id" not in content:
            violations.append(f"{rel} does not use author_persona_id")
        if rel.endswith("cms/testimonials/[id]/page.tsx") and "author_persona_id" not in content:
            violations.append(f"{rel} does not use author_persona_id")
        if rel.endswith("admin/audit/page.tsx") and "actor_persona_id" not in content:
            violations.append(f"{rel} does not use actor_persona_id")
        if "Persona #${" in content or "USR_ID:" in content:
            violations.append(f"{rel} still labels identity with numeric integer")

    assert violations == []


def test_academy_persona_backfill_migration_exists():
    root = Path(__file__).resolve().parents[1]
    migration = root / "alembic" / "versions" / "20260605_academy_persona_backfill.py"

    assert migration.exists()
    content = migration.read_text(encoding="utf-8")

    required_fragments = [
        "down_revision: Union[str, None] = \"20260604_personas_scanner_token\"",
        "_backfill(\"enrollments\", \"persona_id\")",
        "_backfill(\"lesson_progress\", \"persona_id\")",
        "_backfill(\"academy_activity_logs\", \"persona_id\")",
        "_backfill(\"formal_actas\", \"closed_by_persona_id\", \"closed_by_user_id\")",
        "uq_persona_course",
        "uq_persona_lesson_progress",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in content]
    assert missing == []


def test_crm_persona_backfill_migration_exists():
    root = Path(__file__).resolve().parents[1]
    migration = root / "alembic" / "versions" / "20260605_crm_persona_backfill.py"

    assert migration.exists()
    content = migration.read_text(encoding="utf-8")

    required_fragments = [
        "down_revision: Union[str, None] = \"20260605_acad_pers_backfill\"",
        "_backfill(\"counseling_tickets\", \"pastor_id\", \"pastor_user_id\")",
        "_backfill(\"consolidation_tasks\", \"assignee_id\", \"assignee_user_id\")",
        "_backfill(\"communication_logs\", \"leader_id\", \"leader_user_id\")",
        "fk_counseling_tickets_pastor_id",
        "fk_consolidation_tasks_assignee_id",
        "fk_communication_logs_leader_id",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in content]
    assert missing == []


def test_cms_persona_backfill_migration_exists():
    root = Path(__file__).resolve().parents[1]
    migration = root / "alembic" / "versions" / "20260605_cms_persona_backfill.py"

    assert migration.exists()
    content = migration.read_text(encoding="utf-8")

    required_fragments = [
        "down_revision: Union[str, None] = \"20260605_crm_persona_backfill\"",
        "(\"content_publications\", \"updated_by_persona_id\", \"updated_by\")",
        "(\"cms_media_items\", \"created_by_persona_id\", \"created_by\")",
        "(\"cms_pages\", \"created_by_persona_id\", \"created_by\")",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in content]
    assert missing == []


def test_agents_governance_persona_backfill_migration_exists():
    root = Path(__file__).resolve().parents[1]
    migration = root / "alembic" / "versions" / "20260605_agents_governance_persona_backfill.py"

    assert migration.exists()
    content = migration.read_text(encoding="utf-8")

    required_fragments = [
        "down_revision: Union[str, None] = \"20260605_cms_persona_backfill\"",
        "(\"agents\", \"created_by_persona_id\", \"created_by\")",
        "(\"agent_roles\", \"created_by_persona_id\", \"created_by\")",
        "(\"agent_journey\", \"triggered_by_persona_id\", \"triggered_by_id\")",
        "(\"agent_conversations\", \"persona_id\", \"user_id\")",
    ]

    missing = [fragment for fragment in required_fragments if fragment not in content]
    assert missing == []


def test_platform_frontend_respects_ccf_ui_contracts():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "frontend" / "src" / "app" / "plataforma",
        root / "frontend" / "src" / "components",
        root / "frontend" / "src" / "design",
    ]
    forbidden = (
        "indigo",
        "violet",
        "purple",
        "Miembro",
        "miembro",
        "Membresía",
        "membresía",
        "@radix-ui/react-dialog",
        "<Dialog",
        "Dialog.",
    )
    violations = []

    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for term in forbidden:
                    if term in line:
                        violations.append(f"{path.relative_to(root)}:{line_no} contains {term}")

    assert violations == []


def test_platform_frontend_does_not_expose_old_identity_contracts():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "frontend" / "src" / "app" / "plataforma",
        root / "frontend" / "src" / "components",
        root / "frontend" / "src" / "context",
        root / "frontend" / "src" / "hooks",
        root / "frontend" / "src" / "lib",
    ]
    forbidden_terms = (
        "Leg" + "acy #",
        "LEG" + "ACY:",
        "actor_user_id",
        "author_id ? 'Persona vinculada'",
        "user_id:",
        ".user_id",
        "v3Data.user_id",
        "lastEvent.user_id",
    )
    violations = []

    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = path.relative_to(root).as_posix()
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "auth_user_id" in line:
                    continue
                for term in forbidden_terms:
                    if term in line:
                        violations.append(f"{rel}:{line_no} contains {term}")

    assert violations == []


def test_active_code_does_not_reintroduce_old_architecture_labels():
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "backend" / "api",
        root / "backend" / "core",
        root / "backend" / "crud",
        root / "backend" / "schemas",
        root / "frontend" / "src",
    ]
    forbidden_terms = (
        "leg" + "acy",
        "Leg" + "acy",
        "LEG" + "ACY",
        "depre" + "cated",
        "Depre" + "cated",
    )
    violations = []

    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            rel = path.relative_to(root).as_posix()
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for term in forbidden_terms:
                    if term in line:
                        violations.append(f"{rel}:{line_no} contains old architecture label")

    assert violations == []


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND AXIOMATIC RULES — REGLAS.md + ESTANDARES_DESARROLLO.md
# ─────────────────────────────────────────────────────────────────────────────

def test_backend_no_jsonb_columns():
    """REGLAS §2.8 — usar JSON no JSONB. JSONB rompe soporte SQLite (tests)."""
    root = Path(__file__).resolve().parents[1]
    violations = []
    for path in (root / "backend").rglob("models*.py"):
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if "JSONB" in line:
                violations.append(f"{path.relative_to(root)}:{line_no}: {line.strip()[:80]}")
    assert violations == [], "Usar JSON en lugar de JSONB para soporte SQLite en tests"


def test_backend_datetime_columns_always_have_timezone():
    """REGLAS §2.D — todos los Column(DateTime) deben incluir timezone=True."""
    root = Path(__file__).resolve().parents[1]
    violations = []
    for path in (root / "backend").rglob("models*.py"):
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Detecta Column(DateTime) o Column(DateTime()) sin timezone=True
            if "Column(DateTime" in line and "timezone=True" not in line:
                violations.append(f"{path.relative_to(root)}:{line_no}: {stripped[:80]}")
    assert violations == [], "Todos los DateTime en modelos deben usar timezone=True"


def test_backend_no_hard_deletes_in_transactional_apis():
    """REGLAS §2.C — prohibido db.delete() en tablas transaccionales. Usar soft delete."""
    root = Path(__file__).resolve().parents[1]
    # Tablas transaccionales históricas — excluir archivos de control/auth que sí usan hard delete legítimo
    ALLOWED_FILES = {
        "backend/api/admin.py",       # asignaciones de roles (tablas de control, no históricas)
        "backend/api/auth.py",        # refresh tokens revocados
        "backend/api/auth_v3.py",     # tokens de sesión
    }
    violations = []
    for scan_dir in [(root / "backend" / "api"), (root / "backend" / "crud")]:
        for path in scan_dir.rglob("*.py"):
            rel = str(path.relative_to(root)).replace("\\", "/")
            if rel in ALLOWED_FILES:
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if "db.delete(" in line:
                    violations.append(f"{rel}:{line_no}: {stripped[:80]}")
    assert violations == [], (
        "Usar soft delete (deleted_at o estado_vital='INACTIVO') en vez de db.delete() "
        "en endpoints transaccionales"
    )


def test_backend_new_models_use_uuid_not_integer_pk_for_persona_linked_tables():
    """REGLAS §2.A — tablas con FK a personas.id deben usar UUID como PK, no Integer.

    Deuda técnica conocida (pre-existente, no bloquea pero se monitorea):
    Las clases listadas en KNOWN_VIOLATIONS tienen Integer PK con FK a personas.id.
    Deben migrarse a UUID en el ciclo de deuda técnica Q3-2026.
    NO AÑADIR nuevas clases a esta lista sin aprobación de arquitectura.
    """
    root = Path(__file__).resolve().parents[1]

    # Deuda técnica existente — NO AMPLIAR esta lista
    KNOWN_VIOLATIONS = {
        "ProgresoLeccion", "AsistenciaClase", "ActaFormal",
        "HiloForo", "ComentarioForo", "LogAuditoria",
    }

    target_models = [
        root / "backend" / "models_academy_core.py",
        root / "backend" / "models_evangelism.py",
    ]
    new_violations = []
    for path in target_models:
        if not path.exists():
            continue
        in_class = False
        has_persona_fk = False
        has_integer_pk = False
        class_name = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("class ") and "(Base)" in line:
                if in_class and has_persona_fk and has_integer_pk:
                    bare = class_name.split("(")[0].replace("class ", "").strip()
                    if bare not in KNOWN_VIOLATIONS:
                        new_violations.append(f"{path.name}::{bare}")
                in_class = True
                class_name = line.strip()
                has_persona_fk = False
                has_integer_pk = False
            if in_class:
                if 'ForeignKey("personas.id")' in line or "ForeignKey('personas.id')" in line:
                    has_persona_fk = True
                if "primary_key=True" in line and "Integer" in line:
                    has_integer_pk = True
        if in_class and has_persona_fk and has_integer_pk:
            bare = class_name.split("(")[0].replace("class ", "").strip()
            if bare not in KNOWN_VIOLATIONS:
                new_violations.append(f"{path.name}::{bare}")

    assert new_violations == [], (
        "NUEVAS tablas vinculadas a personas.id con PK Integer detectadas. "
        "Usar UUID(as_uuid=True) como PK. Ver REGLAS §2.A"
    )


def test_frontend_no_direct_fetch_calls():
    """AGENTS_FRONTEND §8 — usar apiFetch() de @/lib/http, nunca fetch() directo.

    Excepciones legítimas donde fetch() directo ES correcto:
    - Descargas de blob/binarios (CSV, PDF) donde se necesita .blob()
    - Upload de FormData (archivos adjuntos, multimedia)
    - Componentes públicos (CMS renderer) con submits de formulario nativos
    """
    root = Path(__file__).resolve().parents[1]
    scan_roots = [
        root / "frontend" / "src" / "app" / "plataforma",
        root / "frontend" / "src" / "components",
    ]
    # Archivos con uso legítimo de fetch() directo (descargas blob / FormData uploads)
    ALLOWED_FILES = {
        # Exportaciones binarias (CSV/JSON blob downloads)
        "frontend/src/app/plataforma/admin/settings/system/page.tsx",
        "frontend/src/app/plataforma/admin/analytics/web-vitals/page.tsx",
        # Upload de archivos adjuntos (FormData multipart)
        "frontend/src/components/projects/TaskDetailPanel.tsx",
        # Formularios públicos nativos del CMS (sin auth header)
        "frontend/src/components/public/cms/PublicSectionRenderer.tsx",
    }
    violations = []
    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            rel = str(path.relative_to(root)).replace("\\", "/")
            if rel in ALLOWED_FILES:
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("//") or stripped.startswith("*"):
                    continue
                if (
                    ("await fetch(" in line or "= fetch(" in line or "return fetch(" in line)
                    and "apiFetch" not in line
                    and "nativeFetch" not in line
                ):
                    violations.append(f"{rel}:{line_no}: {stripped[:80]}")
    assert violations == [], "Usar apiFetch() de @/lib/http en vez de fetch() directo"
