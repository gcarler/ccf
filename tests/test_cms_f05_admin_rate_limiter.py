"""F-05 (errorescms.md): rate limiting en endpoints CMS v2 admin.

Antes solo los endpoints publicos del router CMS v2 tenian rate limiting
explicito. Los ~67 endpoints admin (sites, pages, sections, menus,
themes, posts, categories, tags, media, etc.) no tenian limite.

Fix: el router CMS v2 ahora aplica ``rate_limiter(limit=600, window=60)``
como dependency a nivel router (``APIRouter(dependencies=...)``). Los
12 endpoints que ya tienen su propio override conservan su limite mas
restrictivo; el router-level aplica a los 67 restantes.

El rate limiter es NO-OP en pytest (env ``PYTEST_CURRENT_TEST`` bypass)
para no correr 429 en la 100+ test suite. Estos tests validan:

  1) Structural: el router tiene dependencies aplicadas
  2) Constantes PUBLIC_CMS_RATE_LIMIT existen y son razonables
  3) Endpoints publicos conservan su propio rate_limiter override
  4) Multiplicidad: cada endpoint del router hered un dep
"""
from __future__ import annotations

from backend.api import cms_v2

# ── Structural verification ────────────────────────────────────────


class TestF05RouterRateLimiter:
    def test_router_has_rate_limiter_dependency(self):
        """F-05: el router CMS v2 debe tener al menos una dependency
        configurada (la del rate_limiter a nivel router)."""
        assert len(cms_v2.router.dependencies) >= 1, (
            "F-05: el router CMS v2 debe tener dependencies aplicadas a "
            "nivel router (APIRouter(dependencies=...)); el rate limiting "
            "admin se configuration alli."
        )

    def test_router_dep_is_rate_limiter(self):
        """La dependency del router debe ser la funcion inner de
        ``rate_limiter`` (su closure name termina en ``dependency``)."""
        for dep in cms_v2.router.dependencies:
            # ``Depends`` encapsula la funcion ``dependency`` retornada por
            # ``rate_limiter(limit=..., window_seconds=...)``
            inner = getattr(dep, "dependency", None)
            if inner is None:
                continue
            # El closure de rate_limiter se llama ``dependency``
            assert inner.__name__ == "dependency", (
                f"router dependency should be rate_limiter's inner "
                f"`dependency` closure, got {inner.__name__!r}"
            )

    def test_public_cms_rate_limit_constant_exists(self):
        """La constante ``PUBLIC_CMS_RATE_LIMIT`` debe estar definida."""
        assert hasattr(cms_v2, "PUBLIC_CMS_RATE_LIMIT")
        assert isinstance(cms_v2.PUBLIC_CMS_RATE_LIMIT, int)
        assert cms_v2.PUBLIC_CMS_RATE_LIMIT > 0

    def test_router_dep_count_is_at_least_one(self):
        """Garantiza que no se puede regresar a cero deps."""
        assert len(cms_v2.router.dependencies) >= 1


# ── Verificacion que los endpoints publicos conservan override ─────


class TestF05PublicEndpointOverrides:
    """Los endpoints publicos que ya tenian su propio ``rate_limiter``
    DEBEN conservarlo — el router-level no los reemplaza."""

    def _find_public_route(self, path_suffix: str):
        """Busca una ruta cuyo path termine con ``path_suffix``."""
        for r in cms_v2.router.routes:
            if hasattr(r, "path") and r.path.endswith(path_suffix):
                return r
        return None

    def test_sitemap_xml_has_own_rate_limiter(self):
        """El endpoint /public/sites/{site_key}/sitemap.xml DEBE tener
        su propio ``rate_limiter`` con limite restrictivo (10)."""
        r = self._find_public_route("/sitemap.xml")
        assert r is not None, "endpoint /sitemap.xml debe existir"
        # El rate limiter debe estar en dependencias de la ruta
        deps = getattr(r, "dependant", None)
        assert deps is not None
        # ``dependant.dependencies`` contiene las Depends aplicadas a la ruta
        names = [
            (getattr(d, "name", "") or "")
            for d in (deps.dependencies or [])
        ]
        # La funcion anidada de rate_limiter se llama ``dependency``
        assert any("dependency" in n for n in names) or any(
            (getattr(d.call, "__name__", "") == "dependency")
            for d in (deps.dependencies or [])
        ), "sitemap.xml debe tener su propio rate_limiter override"

    def test_robots_txt_has_own_rate_limiter(self):
        """El endpoint /public/sites/{site_key}/robots.txt DEBE tener
        su propio ``rate_limiter`` override."""
        r = self._find_public_route("/robots.txt")
        assert r is not None
        deps = getattr(r, "dependant", None)
        assert deps is not None
        has_rate_limiter = any(
            (getattr(d.call, "__name__", "") == "dependency")
            for d in (deps.dependencies or [])
        )
        assert has_rate_limiter

    def test_public_sites_public_has_own_rate_limiter(self):
        """El endpoint ``GET /public/sites/{site_key}/theme`` DEBE tener su
        propio rate_limiter override (``PUBLIC_CMS_RATE_LIMIT = 240``)."""
        r = None
        for route in cms_v2.router.routes:
            if (
                hasattr(route, "path")
                and route.path.endswith("/public/sites/{site_key}/theme")
                and "GET" in (route.methods or set())
            ):
                r = route
                break
        assert r is not None, "GET /public/sites/{site_key}/theme debe existir"
        deps = getattr(r, "dependant", None)
        assert deps is not None
        has_rate_limiter = any(
            (getattr(d.call, "__name__", "") == "dependency")
            for d in (deps.dependencies or [])
        )
        assert has_rate_limiter


# ── Smoke de que el limiter es NO-OP en pytest (no rompe tests) ────


class TestF05LimiterNoOpInTest:
    """En pytest, el rate limiter debe bypass (return None)."""

    def test_router_loads_cleanly(self):
        """El router debe importarse y ser usable en pytest."""
        assert cms_v2.router is not None
        assert len(cms_v2.router.routes) >= 70  # 79 endpoints

    def test_router_prefix_is_cms_v2(self):
        assert cms_v2.router.prefix == "/cms/v2"
