"""TKT-200 regression gate — rate limiting + DoS protection.

Verifica el comportamiento del ``academy_limiter`` (slowapi) instalado en el
módulo Academy:
- ``_academy_key_func`` devuelve ``None`` en pytest (bypass global) y respeta
  ``FORCE_RATE_LIMIT=1`` cuando un test opta-in.
- ``academy_limiter`` está registrado en ``app.state.limiter`` con
  ``headers_enabled=True`` y ``default_limits=()``.
- Los 3 endpoints hot (``submit_assessment``, ``create_forum_thread``,
  ``create_enrollment``) están decorados con ``@academy_limiter.limit(...)``
  y retornan 429 al superar el umbral.
- Usuarios con ``request.state.is_unlimited_user=True`` están exentos del
  rate-limit (manager / admin bypass).
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from backend.app import app
from backend.core.rate_limit import (
    FORCE_RATE_LIMIT_VAR,
    PYTEST_BYPASS_VAR,
    _academy_key_func,
    academy_limiter,
)

# ── helpers ────────────────────────────────────────────────────────────


class _MockState:
    """Stub ``request.state`` con los atributos que ``_academy_key_func`` lee."""

    def __init__(self, *, user_id: str | None = None, is_unlimited: bool = False) -> None:
        self.user_id = user_id
        self.is_unlimited_user = is_unlimited


class _MockRequest:
    """Stub de ``Request`` mínimo para los key_func unit tests.

    Incluye ``client`` (objeto con ``.host``) porque ``slowapi.util
    .get_remote_address`` llama ``request.client.host`` para obtener el IP
    en el fallback de bucket. Usamos ``SimpleNamespace`` en lugar de un
    tuple porque slowapi accede al atributo ``.host``, no por índice.
    """

    def __init__(self, *, user_id: str | None = None, is_unlimited: bool = False) -> None:
        self.state = _MockState(user_id=user_id, is_unlimited=is_unlimited)
        # TestClient envía desde ("testclient", 50000) — replicamos como
        # objeto con atributo ``host`` (no tuple — slowapi rompe con tuple).
        self.client = SimpleNamespace(host="testclient", port=50000)


def _student_dep_key():
    """Extract the ``AcademyStudent`` dependency for ``app.dependency_overrides``.

    ``AcademyStudent = Annotated[Any, Depends(require_module_access("academy", "study"))]``.
    FastAPI's ``Depends`` es una función (no clase) y retorna una instancia
    de ``fastapi.params.Depends`` que tiene el atributo ``dependency``. Usamos
    duck-typing (``hasattr``) porque ``isinstance(meta, Depends)`` falla —
    el segundo arg de isinstance debe ser una clase.
    """
    from backend.api.academy import AcademyStudent

    for meta in AcademyStudent.__metadata__:
        if hasattr(meta, "dependency"):
            return meta.dependency
    raise RuntimeError("AcademyStudent has no Depends metadata")


def _fake_student_user() -> SimpleNamespace:
    """Stand-in para un ``Usuario`` autenticado (rol estudiante).

    Solo define los atributos que tocan ``require_permission._check`` y
    ``get_user_effective_permissions`` para que el guard pase sin DB.
    """

    return SimpleNamespace(
        id=uuid.uuid4(),
        username="test-student",
        email="student@t",
        role="estudiante",
        rol_plataforma=None,
        is_active=True,
        password_hash="",
    )


def _reset_academy_storage() -> None:
    """Reset slowapi's bucket storage before/after each force_limiter test.

    slowapi 0.1.10 expone el storage como ``_storage`` (privado con leading
    underscore); versiones anteriores usaban ``storage``. El doble ``getattr``
    cubre ambos.
    """
    storage_backend = getattr(academy_limiter, "_storage", None) or getattr(
        academy_limiter, "storage", None
    )
    if storage_backend is not None and hasattr(storage_backend, "reset"):
        storage_backend.reset()


@pytest.fixture
def force_limiter(monkeypatch):
    """Activa el limiter bajo pytest: ``FORCE_RATE_LIMIT=1`` + reset bucket."""

    monkeypatch.setenv(FORCE_RATE_LIMIT_VAR, "1")
    _reset_academy_storage()
    yield
    _reset_academy_storage()


# NOTE: NO definimos ``client`` fixture aquí. Usamos la de ``tests/conftest.py``
# que depende de ``db_session`` (crea el schema académico en SQLite in-memory
# via ``Base.metadata.create_all``). Una fixture local que retorne
# ``TestClient(app)`` bypasea el setup del DB y produce
# ``OperationalError: no such table: academy_assessments`` en los tests E2E.


# ── key_func: unit tests ───────────────────────────────────────────────


def test_acad_tkt_200_academy_limiter_is_slowapi_limiter_instance() -> None:
    """``academy_limiter`` es instancia de ``slowapi.Limiter``."""

    assert isinstance(academy_limiter, Limiter)


def test_acad_tkt_200_academy_limiter_has_headers_enabled() -> None:
    """slowapi emitirá ``Retry-After`` y ``X-RateLimit-*`` headers."""

    assert academy_limiter._headers_enabled is True


def test_acad_tkt_200_academy_limiter_default_limits_are_empty() -> None:
    """Solo aplican los límites decorados por endpoint (no default_limits global).

    slowapi 0.1.10 retorna ``_default_limits`` como lista ``[]``; usamos
    ``not defaults`` para tolerar tuple ``()`` o list ``[]``.
    """

    defaults = getattr(academy_limiter, "_default_limits", ())
    assert not defaults, f"_default_limits debería estar vacío, obtuve {defaults!r}"


def test_acad_tkt_200_academy_limiter_storage_uri_is_memory() -> None:
    """Storage es ``memory://`` (single-worker test/dev)."""

    storage_uri = str(getattr(academy_limiter, "_storage_uri", "memory://"))
    assert storage_uri.startswith("memory://"), (
        f"esperaba URI memory://, obtuve {storage_uri!r}"
    )


def test_acad_tkt_200_key_func_returns_none_in_pytest_without_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin ``FORCE_RATE_LIMIT``, el key_func evita rate-limitar la suite."""

    monkeypatch.delenv(FORCE_RATE_LIMIT_VAR, raising=False)
    monkeypatch.setenv(PYTEST_BYPASS_VAR, "1")  # mimetiza pytest
    req = _MockRequest(user_id="abc", is_unlimited=False)
    assert _academy_key_func(req) is None


def test_acad_tkt_200_key_func_returns_user_key_when_force_and_authenticated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Con ``FORCE_RATE_LIMIT=1``, key_func retorna ``user:<id>``."""

    monkeypatch.setenv(FORCE_RATE_LIMIT_VAR, "1")
    monkeypatch.setenv(PYTEST_BYPASS_VAR, "1")
    req = _MockRequest(user_id="user-42", is_unlimited=False)
    assert _academy_key_func(req) == "user:user-42"


def test_acad_tkt_200_key_func_returns_none_for_unlimited_user_with_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Manager/admin corta el rate-limit incluso con FORCE_RATE_LIMIT=1."""

    monkeypatch.setenv(FORCE_RATE_LIMIT_VAR, "1")
    monkeypatch.setenv(PYTEST_BYPASS_VAR, "1")
    req = _MockRequest(user_id="admin-1", is_unlimited=True)
    assert _academy_key_func(req) is None


def test_acad_tkt_200_key_func_falls_back_to_ip_when_no_user_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin user_id y sin is_unlimited → ``ip:<remote>`` (defensa DoS)."""

    monkeypatch.setenv(FORCE_RATE_LIMIT_VAR, "1")
    monkeypatch.setenv(PYTEST_BYPASS_VAR, "1")
    req = _MockRequest(user_id=None, is_unlimited=False)
    out = _academy_key_func(req)
    assert out is not None
    assert out.startswith("ip:")


# ── app registration: integration unit ─────────────────────────────────


def test_acad_tkt_200_limiter_registered_in_app_state() -> None:
    """``app.state.limiter`` es ``academy_limiter`` (contract slowapi)."""

    assert getattr(app.state, "limiter", None) is academy_limiter


def test_acad_tkt_200_rate_limit_exceeded_handler_registered() -> None:
    """slowapi's ``RateLimitExceeded`` handler está en ``app.exception_handlers``."""

    handlers = app.exception_handlers
    assert RateLimitExceeded in handlers, (
        "TKT-200 regresión: RateLimitExceeded handler no está registrado. "
        "Asegúrate de que ``app.add_exception_handler(RateLimitExceeded, ...)`` "
        "se llamó en backend/app.py."
    )


def test_acad_tkt_200_permissions_check_populates_state_is_unlimited_user() -> None:
    """``require_permission._check`` popula ``request.state.is_unlimited_user=True``
    cuando permission termina en ``:manage`` o rol es admin/gestor.

    Este test cierra el gap de cobertura del side-effect introducido en
    backend/core/permissions.py. Es lo que ``_academy_key_func`` luego lee
    en ``request.state`` para decidir bypass. Si el side-effect se rompe
    en el futuro, este test atrapa el regression antes de que llegue a HTTP.
    """

    from backend.core.permissions import require_permission

    req = SimpleNamespace(state=SimpleNamespace(user_id=None, is_unlimited_user=False))
    fake_admin = SimpleNamespace(
        id=uuid.uuid4(),
        role="administrador",
        username="fake-admin",
        email="admin@t",
        rol_plataforma=None,
        is_active=True,
        password_hash="",
    )
    # El ``_check`` retorna el current_user si el permission es válido (admin bypass).
    closure = require_permission("academy:manage")
    # Llamamos directamente el closure con request + current_user + db=None;
    # el side-effect debe poblar ``request.state`` antes de retornar.
    import asyncio as _asyncio

    closed = _asyncio.run(closure(req, current_user=fake_admin, db=None))
    assert closed is fake_admin
    assert req.state.is_unlimited_user is True, (
        "Side-effect roto: require_permission._check no popula "
        "request.state.is_unlimited_user para admin/manage — bypass "
        "manager/admin en runtime se rompe"
    )
    assert req.state.user_id == str(fake_admin.id), (
        "Side-effect roto: request.state.user_id no fue poblado"
    )


# ── endpoint decorator presence ───────────────────────────────────────


def test_acad_tkt_200_submit_assessment_has_rate_limit_decorator() -> None:
    """``submit_assessment`` debe estar decorada con ``@academy_limiter.limit``.

    slowapi envuelve la función con ``__wrapped__``; su presencia indica
    que el decorator aplicó.
    """

    from backend.api.academy import submit_assessment

    assert getattr(submit_assessment, "__wrapped__", None) is not None, (
        "submit_assessment no tiene @academy_limiter.limit aplicado"
    )


def test_acad_tkt_200_create_forum_thread_has_rate_limit_decorator() -> None:
    from backend.api.academy import create_forum_thread

    assert getattr(create_forum_thread, "__wrapped__", None) is not None


def test_acad_tkt_200_create_enrollment_has_rate_limit_decorator() -> None:
    from backend.api.academy import create_enrollment

    assert getattr(create_enrollment, "__wrapped__", None) is not None


# ── 429 end-to-end (gate) ──────────────────────────────────────────────


def test_acad_tkt_200_submit_assessment_returns_429_after_threshold(
    client, force_limiter
) -> None:
    """El 11er ``POST /assessments/<uuid>/submit`` dentro de 1 min → 429.

    El assessment no existe (404), pero el limiter corre ANTES de la query
    DB; los primeros 10 hits devuelven 404, el 11+ devuelve 429."""

    dep_key = _student_dep_key()
    app.dependency_overrides[dep_key] = lambda: _fake_student_user()
    try:
        fake_id = str(uuid.uuid4())
        statuses: list[int] = []
        for _ in range(15):
            r = client.post(
                f"/api/academy/assessments/{fake_id}/submit",
                json={"answers": []},
                headers={"Authorization": "Bearer fake"},
            )
            statuses.append(r.status_code)
        n_429 = sum(1 for s in statuses if s == 429)
        n_not_429 = sum(1 for s in statuses if s != 429)
        assert n_429 >= 1, (
            f"Esperaba al menos un 429 después de superar 10/min: {statuses}"
        )
        assert n_not_429 == 10, (
            f"Esperaba 10 hits no-429 (los previos al 11vo), obtuve {n_not_429}: {statuses}"
        )
    finally:
        app.dependency_overrides.pop(dep_key, None)


def test_acad_tkt_200_429_response_includes_retry_after_header(
    client, force_limiter
) -> None:
    """El 429 de slowapi incluye ``Retry-After`` (headers_enabled=True)."""

    dep_key = _student_dep_key()
    app.dependency_overrides[dep_key] = lambda: _fake_student_user()
    try:
        fake_id = str(uuid.uuid4())
        last_429 = None
        for _ in range(12):
            r = client.post(
                f"/api/academy/assessments/{fake_id}/submit",
                json={"answers": []},
                headers={"Authorization": "Bearer fake"},
            )
            if r.status_code == 429:
                last_429 = r
        assert last_429 is not None, "No se obtuvo ningún 429 tras 12 hits"
        retry_after = last_429.headers.get("Retry-After") or last_429.headers.get(
            "retry-after"
        )
        assert retry_after is not None, (
            f"429 sin Retry-After. Headers: {dict(last_429.headers)!r}"
        )
    finally:
        app.dependency_overrides.pop(dep_key, None)


@pytest.mark.skip(
    reason="slowapi 0.1.10 pathology: ``__limit_decorator`` captura "
    "``self._key_func`` como variable local en decoration-time (closure). "
    "``setattr(academy_limiter, '_key_func', ...)`` aplicado POST-module-load "
    "no afecta a los decoradores ``@academy_limiter.limit(...)`` ya aplicados. "
    "El contrato de bypass al nivel más bajo posible está verificado en "
    "``test_acad_tkt_200_key_func_returns_none_for_unlimited_user_with_force``. "
    "Refactor pendiente Fase 7+: ``SlowAPIMiddleware`` o ``_make_key_func(is_unlimited_predicate)`` "
    "que NO capture en closure (factory pattern)."
)
def test_acad_tkt_200_unlimited_user_is_not_rate_limited(
    client, force_limiter
) -> None:
    """Manager / admin bypass NUNCA recibe 429 — placeholder, ver skip arriba.

    Estrategia intentada: monkey-patch directo de ``academy_limiter._key_func``
    para retornar ``None``. NO FUNCIONA en slowapi 0.1.10 porque captura
    la referencia en decoration-time, no request-time.
    """

    original_key_func = academy_limiter._key_func

    def _bypass_key_func(_request) -> None:
        return None

    academy_limiter._key_func = _bypass_key_func
    try:
        dep_key = _student_dep_key()
        app.dependency_overrides[dep_key] = lambda: _fake_student_user()
        try:
            fake_id = str(uuid.uuid4())
            seen_429 = 0
            for _ in range(25):
                r = client.post(
                    f"/api/academy/assessments/{fake_id}/submit",
                    json={"answers": []},
                    headers={"Authorization": "Bearer fake"},
                )
                if r.status_code == 429:
                    seen_429 += 1
            assert seen_429 == 0, (
                f"Manager bypass roto: {seen_429} hits dispararon 429 con "
                f"key_func=None'bypass"
            )
        finally:
            app.dependency_overrides.pop(dep_key, None)
    finally:
        academy_limiter._key_func = original_key_func


# ── CI guard: regression check on version pin ────────────────────────────────


def test_acad_tkt_200_ci_guard_slowapi_and_limits_versions_pinned() -> None:
    """``requirements.txt`` debe pinear ``slowapi==0.1.10`` y ``limits==5.8.0``.

    Sin este guard, un refactor accidental podría remover el pin y producir
    ``ModuleNotFoundError`` en producción si la transitive ``limits`` decide
    cambiar su API (rate limiting silenciosamente roto). Este test verifica:

    1. Los paquetes están instalados en el runtime actual (no removidos).
    2. El ``requirements.txt`` contiene el pin explícito de cada uno.

    Si se actualiza slowapi o limits, este test falla y obliga a actualizar
    ambos archivos (test + requirements) en un solo commit coordinado.
    """

    from importlib.metadata import version
    from pathlib import Path

    # Side-effect import: verifica que ``backend.core.rate_limit`` carga sin
    # errores en runtime. No necesitamos un símbolo; el import es la prueba.
    import backend.core.rate_limit  # noqa: F401

    assert version("slowapi") == "0.1.10", (
        f"slowapi runtime != 0.1.10: {version('slowapi')}. "
        f"Actualiza requirements.txt o revierte slowapi."
    )
    assert version("limits") == "5.8.0", (
        f"limits runtime != 5.8.0: {version('limits')}. "
        f"limits es transitive de slowapi; pinear explícitamente para evitar drift."
    )

    _repo_root = Path(__file__).resolve().parents[1]
    req_path = _repo_root / "requirements.txt"
    try:
        text = req_path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        pytest.fail(f"requirements.txt no encontrado en {req_path}: {e}")
    req_lines = text.splitlines()
    assert "slowapi==0.1.10" in text, (
        f"requirements.txt no contiene 'slowapi==0.1.10'. Lineas relevantes: "
        f"{[line for line in req_lines if 'slowapi' in line.lower()]}"
    )
    assert "limits==5.8.0" in text, (
        f"requirements.txt no contiene 'limits==5.8.0'. Lineas relevantes: "
        f"{[line for line in req_lines if 'limits' in line.lower()]}"
    )

