"""Cierre arquitectonico v3.0.1 — tests contractuales ejecutables.

Convierte los gates del cierre en tests pytest para que el estado "100%
Axioma 3 multi-tenant" se audite solo, sin depender de ``rg``/``find``
ad-hoc en pipelines heterogeneos.

Estos tests son el **complemento ejecutable** de:

- ``docs/ESTADO_ARQUITECTURA_CCF.md`` → seccion "Gate De Cierre (auditable)"
- ``docs/CIERRE_ARQUITECTURA_CCF.md`` → seccion "Validacion Ejecutada"
- ``REGLAS.md`` → secciones 4.1, 4.2, 9.1, 9.2, 11

Politica de proteccion:

- Si una de estas aserciones falla en CI, el cierre **NO esta completo**.
  Cualquier regresion debe ser tratada como bug arquitectonico (no como
  issue cosmetico).
- Los baselines numericos (ej. ``>= 194`` refs multi-tenant) reflejan el
  estado del cierre v3.0.1 (2026-07-01). Si baja sin una justificacion
  documentada en ``docs/CIERRE_ARQUITECTURA_CCF.md``, hay regresion.

Chicken-and-egg / exclusion self-aware:

- Estos tests nombran literalmente las cadenas prohibidas (e.g.
  ``CCF-MBR``, ``ForeignKey("users.id")``, ``/api/v2/academy``) para
  auditarlas. Por lo tanto:
  1. Los comandos de busqueda **excluyen** este archivo via glob
     ``-g '!tests/test_arquitectura*'``.
  2. Las cadenas prohibidas se construyen por concatenacion runtime
     para que un grep estatico ingenuo no las detecte en el auditor.
  3. "Live code" excluye: ``alembic/versions/``, ``docs/``, ``REGLAS.md``
     y ``tests/test_arquitectura*`` (este archivo).
- Companion exacto: ``docs/ESTADO_ARQUITECTURA_CCF.md`` debe usar las
  MISMAS exclusiones. Fuente unica de verdad.

Notas de implementacion:

- Usamos ``subprocess`` sobre ``rg`` (con fallback sin ripgrep via
  Path + ``is_live_code``).
- Excluimos ``__init__.py`` para evitar doble conteo por re-exports
  de helpers (Helpers definidos en ``_shared.py`` + re-export en
  ``__init__.py``).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


# ── Half-strings obfuscation (anti self-detection) ─────────────────────────
# Auditor arma las cadenas prohibidas en runtime. Esto evita que un grep
# trivial ejecutado sobre este archivo (sin las exclusiones de glob)
# detecte self-violation. La deteccion real SI pasa tras aplicar las
# exclusiones canonicales (ver is_live_code y los glob -g).

_BAN_FK = "ForeignKey(" + '"us' + 'ers.' + 'id' + '")'
_BAN_PREFIX = "CCF-" + "MBR"
_BAN_V2 = "/api/v" + "2/academy"
_BAN_TMP_PREFIXES = ("_tmp_", "_scratch_", "_validate_legacy_")


# ── Live-code classifier (single source of truth) ──────────────────────────
# self-reference (no wildcard) — este archivo Y solo este se autoexcluye.
# Futuros auditores deben anadirse a esta lista explicitamente; un glob
# ancho autoexcluiria bugs reales.


_THIS_AUDIT_FILE = str(Path(__file__).resolve().as_posix())
_STRUCTURAL_CONTRACTS = "tests/test_structural_contracts.py"


_EXCLUDED_PATHS = frozenset({
    _THIS_AUDIT_FILE,  # Self-reference (no wildcard).
    str((ROOT / "tests" / "structural_contracts.py").as_posix()),  # Legacy name.
    str((ROOT / _STRUCTURAL_CONTRACTS).as_posix()),
    "alembic/versions",  # Legacy migrations — REGLAS §9.1.
    "docs/",  # Definicion de la regla, no su uso.
    "REGLAS.md",
    ".venv/",
    "venv/",
    "node_modules/",
    "__pycache__/",
})


def is_live_code(path: Path) -> bool:
    """True si el archivo es "live code" sujeto a auditar.

    "Live code" = codigo de aplicacion activo donde una violacion REGLAS
    seria un bug. Excluye:

    - ``alembic/versions/`` (legacy migrations — REGLAS §9.1)
    - ``docs/`` y ``REGLAS.md`` (definicion de la regla, no uso)
    - El propio archivo de auditor (self-reference, NO wildcard glob)
    - ``tests/test_structural_contracts.py`` (assert estructural ausencia)
    - caches / venvs / node_modules

    Para anadir un NUEVO auditor al cierre, editar la lista
    ``_EXCLUDED_PATHS`` explicitamente. NO usar wildcard.
    """
    s = path.as_posix()
    return not any(excl in s for excl in _EXCLUDED_PATHS)


def _run(cmd: str) -> str:
    """Run shell command y devuelve stdout. Empty si no hay matches."""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return result.stdout.strip()


# ── Gate 1: Sin FK users.id en codigo vivo (REGLAS §1) ─────────────────────


def test_no_legacy_users_fk_in_live_code():
    """REGLAS §1 (Kernel de Personas): CERO ForeignKey("users.id") en live
    code. Permitido: legacy migrations (0024, 0025) son memoria inmutable.
    NO permitido: nuevos modelos, schemas o fixtures referenciando
    ``users.id`` para representar personas.
    """
    rg = shutil.which("rg")
    if rg:
        # Las exclusiones DEBEN ser espejos de docs/ESTADO_ARQUITECTURA.
        out = _run(
            f'rg -n "{_BAN_FK}" '
            "backend frontend/src tests scripts "
            "-g '!alembic/versions/*.py' "
            "-g '!tests/test_arquitectura*.py' "
            "-g '!tests/test_structural_contracts.py'"
        )
    else:
        out = ""
        for path in ROOT.rglob("*.py"):
            if path.name in {"__init__.py", "__pycache__"}:
                continue
            if any(s in path.as_posix() for s in ("__pycache__", ".venv/", "venv/", "node_modules/")):
                continue
            if path.name.startswith("test_arquitectura") or path.name.startswith("test_structural"):
                continue
            if "alembic/versions" in path.as_posix():
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            if _BAN_FK in content:
                out += str(path) + "\n"

    out = out.strip()
    assert out == "", (
        f"REGLAS §1 violada: ForeignKey(\"users.id\") en codigo vivo:\n{out}"
    )


# ── Gate 2: CCF-MBR solo en migraciones legacy (REGLAS §9.1) ──────────────


def test_no_legacy_ccf_mbr_in_live_code():
    """REGLAS §9.1 (Inmutabilidad): la cadena ``CCF-MBR`` solo puede existir
    en ``alembic/versions/0024_prod_hardening3.py`` y ``0025_prod_final.py``.
    Cualquier otro lugar es regresion. Ver el signed calout en REGLAS.md
    seccion 9.1.1 para la justificacion explicita.
    """
    rg = shutil.which("rg")
    if rg:
        out = _run(
            f"rg -n {_BAN_PREFIX!r} "
            "backend frontend/src tests scripts "
            "-g '!alembic/versions/*.py' "
            "-g '!tests/test_arquitectura*.py'"
        )
    else:
        out = ""
        for path in ROOT.rglob("*"):
            if path.is_dir():
                continue
            if "alembic/versions" in path.as_posix():
                continue
            if path.name.startswith("test_arquitectura"):
                continue
            if any(s in path.as_posix() for s in ("__pycache__", ".venv/", "venv/", "node_modules/")):
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            if _BAN_PREFIX in content:
                out += str(path) + "\n"

    out = out.strip()
    assert out == "", (
        f"REGLAS §9.1 violada: CCF-MBR en codigo vivo:\n{out}"
    )


# ── Gate 3: Sin rutas /api/v2/academy (REGLAS §7) ──────────────────────────


def test_no_legacy_api_v2_academy():
    """REGLAS §7 (Modulos Canonicos): Academy vive solo en ``/api/academy``.
    Excluido por diseno: ``tests/test_structural_contracts.py`` (assert de
    ausencia — comportamiento correcto).
    """
    rg = shutil.which("rg")
    if rg:
        out = _run(
            f"rg -n {_BAN_V2!r} "
            "backend frontend/src tests scripts "
            "-g '!tests/test_arquitectura*.py' "
            "-g '!tests/test_structural_contracts.py'"
        )
    else:
        out = ""
        for path in ROOT.rglob("*.py"):
            if path.name.startswith("test_arquitectura") or path.name.startswith("test_structural"):
                continue
            if any(s in path.as_posix() for s in ("__pycache__", ".venv/", "venv/", "node_modules/")):
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            if _BAN_V2 in content:
                out += str(path) + "\n"

    out = out.strip()
    assert out == "", (
        f"REGLAS §7 violada: /api/v2/academy en codigo vivo:\n{out}"
    )


# ── Gate 4: Sin scripts _tmp_/_scratch_/_validate_legacy_ (REGLAS §9.2) ───


def test_no_legacy_operational_scripts():
    """REGLAS §9.2: prohibidos prefijos ``_tmp_``, ``_scratch_``,
    ``_validate_legacy_`` en ``scripts/``. Cleanup del cierre v3.0.1 ya
    elimino los 2 archivos existentes.
    """
    scripts_dir = ROOT / "scripts"
    if not scripts_dir.exists():
        return
    offenders: list[str] = []
    for path in scripts_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if path.name == "__pycache__":
            continue
        if any(prefix in path.name for prefix in _BAN_TMP_PREFIXES):
            offenders.append(str(path))
    assert not offenders, (
        f"REGLAS §9.2 violada: scripts legacy operacionales:\n"
        + "\n".join(offenders)
    )


# ── Gate 5: Cobertura multi-tenant >= 194 refs (cierre v3.0.1) ─────────────


def test_multitenant_coverage_refs_baseline():
    """Cobertura cuantificada del Axioma 3: >= 194 ocurrencias de los helpers
    de scope multi-tenant (``get_user_sede_id`` / ``_scope_*`` /
    ``_get_scoped_*``) en ``backend/``.

    Baseline al cierre v3.0.1 = 194 refs (2026-07-01).

    Excluimos ``__init__.py`` para evitar doble conteo por re-exports.
    Metrica: contamos **lineas unicas** con match (no ocurrencias), igual
    que ``rg -c``. Esto alinea la semantica entre ripgrep y fallback.
    """
    rg = shutil.which("rg")
    baseline = 194  # Cierre v3.0.1 (2026-07-01).
    if rg:
        out = _run(
            "rg -c 'get_user_sede_id|_scope_|_get_scoped_' backend "
            "-g '!**/__init__.py'"
        )
    else:
        # Fallback: contamos lineas unicas con match, alineado con rg -c.
        out_lines: list[str] = []
        total = 0
        for path in (ROOT / "backend").rglob("*.py"):
            if path.name == "__init__.py":
                continue
            try:
                content = path.read_text(errors="ignore")
            except Exception:
                continue
            # Cuenta lineas unicas con match.
            line_count = sum(
                1
                for line in content.splitlines()
                if (
                    "get_user_sede_id" in line
                    or "_scope_" in line
                    or "_get_scoped_" in line
                )
            )
            if line_count > 0:
                total += line_count
                out_lines.append(f"{path.as_posix()}:{line_count}")
        out = "\n".join(out_lines)

    total = 0
    for line in out.splitlines():
        if ":" in line:
            try:
                total += int(line.rsplit(":", 1)[1].strip())
            except ValueError:
                continue
    assert total >= baseline, (
        f"Cobertura multi-tenant refs={total} < baseline {baseline}. "
        f"Regresion detectada: Axioma 3 multi-tenant ha perdido cobertura. "
        f"Investigar: revisar ultimos commits; sin justificacion documentada "
        f"en docs/CIERRE_ARQUITECTURA_CCF.md, es bug."
    )


# ── Gate 6: Helpers CMS bien nombrados (anti-naming-drift) ─────────────────


def test_cms_helpers_module_structure():
    """El package ``backend/api/_cms_helpers/`` debe tener exactamente
    ``__init__.py`` + ``_shared.py``. Cualquier archivo extra es derivado
    ad-hoc del cierre y debe volver a ``_shared.py`` para consistencia.
    """
    pkg = ROOT / "backend" / "api" / "_cms_helpers"
    if not pkg.exists():
        return
    expected = {"__init__.py", "_shared.py", "__pycache__"}
    actual = {p.name for p in pkg.iterdir()}
    extras = sorted(actual - expected)
    assert not extras, (
        f"backend/api/_cms_helpers/ contiene archivos inesperados: "
        f"{extras}. Mover su contenido a _shared.py para evitar drift."
    )


# ── Gate 7: Migration 20260701 existe y es reversible (REGLAS §9) ─────────


def test_cms_sede_id_migration_present_and_reversible():
    """La migration que cierra Axioma 3 en CMS (20260701_0001) debe estar
    presente y tener ``downgrade()`` definido (regla REGLAS §9).
    """
    mig_path = (
        ROOT / "alembic" / "versions" / "20260701_0001_cms_content_sede_id.py"
    )
    assert mig_path.exists(), (
        f"Migration de cierre v3.0.1 no encontrada: {mig_path}"
    )
    src = mig_path.read_text()
    assert "def upgrade()" in src, (
        "Migration 20260701_0001 carece de upgrade()"
    )
    assert "def downgrade()" in src, (
        "Migration 20260701_0001 carece de downgrade() — REGLAS §9 violada"
    )


# ── Gate 8: Triple de coherencia documental (REGLAS ↔ ESTADO ↔ CIERRE) ────


def test_closure_v301_docs_synced():
    """REGLAS + ESTADO + CIERRE deben referenciarse mutuamente y contener
    las reglas clave del cierre v3.0.1. Anchors especificos (no substrings
    debiles).
    """
    reglas = (ROOT / "REGLAS.md").read_text()
    estado = (ROOT / "docs" / "ESTADO_ARQUITECTURA_CCF.md").read_text()
    cierre = (ROOT / "docs" / "CIERRE_ARQUITECTURA_CCF.md").read_text()

    expected_anchors = [
        "## 4.1",  # Politica orphan
        "## 9.1",  # Inmutabilidad migraciones cerradas
        "## 9.2",  # Scripts manuales prohibidos
        "### 9.1.1",  # Calout firmado del cierre
    ]
    for needle in expected_anchors:
        assert needle in reglas, f"REGLAS.md no contiene anchor {needle}"

    assert "Axioma 3" in estado, (
        "ESTADO_ARQUITECTURA_CCF.md no menciona Axioma 3"
    )
    assert "v3.0.1" in cierre and "2026-07-01" in cierre, (
        "CIERRE_ARQUITECTURA_CCF.md no declara el cierre v3.0.1 fechado"
    )


# ── Gate 9: Auth v3 — auth_users.id usa el mismo UUID que personas.id ──────


def test_auth_v3_uses_personas_uuid():
    """REGLAS §2 (Auth v3): ``auth_users.id`` es del mismo tipo que
    ``personas.id`` (UUID). Auditado por introspeccion SQLAlchemy directa
    (NO regex, que es fragil bajo refactors de formato).

    Politica de skip explicito: si los modelos no son importables
    (pre-cierre / modelo no materializado), ``pytest.skip()`` con reason
    explicito. Nunca ``return`` silencioso (eso pasaria como PASS sin
    auditar la regla).
    """
    import pytest
    from sqlalchemy import UUID as SA_UUID
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID

    # Lista cerrada de tipos UUID validos. NO usamos ``type().__name__``
    # porque aceptar clases con "uuid" en el nombre es un over-match
    # (e.g. ``MyUuidWrapper`` pasaria falsamente).
    _VALID_UUID_TYPES = (SA_UUID, PG_UUID)

    def _column_is_uuid(table_obj) -> bool:
        try:
            col_type = table_obj.c.id.type
        except (AttributeError, KeyError):
            return False
        return isinstance(col_type, _VALID_UUID_TYPES)

    try:
        # Import lazy: si Backend tiene modelos no consolidados,
        # marcamos SKIP explicito (no PASS silencioso).
        from backend.models_identity import Persona  # type: ignore
        from backend.models_auth import AuthUser  # type: ignore
    except ImportError as exc:
        pytest.skip(
            f"Gate 9 (Auth v3) requiere modelos consolidados: {exc}. "
            f"Pre-cierre: skip explicito."
        )

    assert _column_is_uuid(Persona.__table__), (
        "REGLAS §1 violada: personas.id no es Column(UUID) — "
        f"tipo={type(Persona.__table__.c.id.type).__name__}"
    )
    assert _column_is_uuid(AuthUser.__table__), (
        "REGLAS §2 violada: auth_users.id no es UUID — "
        "Kernel compartido con personas.id esta roto"
    )
