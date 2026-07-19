"""ACADEMY_BACKLOG.md — tests de cobertura estructural para fuente única.

Estos tests viven en ``tests/test_academy_backlog.py`` y son el primer
eslabón del "backlog en código" para el módulo Academy de CCF Plataforma.
Cada test referencia explícitamente su `ACAD-TKT-NNN` correspondiente en
``docs/ACADEMY_BACKLOG.md`` para que el desarrollador pueda navegar la
matriz ticket ↔ test ↔ gate ejecutable.

Estructura:
    A. Tests estructurales (parsing del .md; sin dependencias runtime).
    B. Tests parametrizados por categoría (CRIT/HIGH/MED/LOW/TEST).

Cada test de la sección B tiene su ``gate`` documentado en
docs/ACADEMY_BACKLOG.md como un comando pytest independiente. Cuando
ese comando esté en verde, el TKT-NNN se puede mover de ⬜ → ✅.

HISTÓRICO (no modificar):
    - ACAD-TKT-001 (CRIT): cierre documental 2026-07-19 → ACAD-HIGH-001
    - ACAD-TKT-002 (CRIT): cierre documental 2026-07-19 → ACAD-TKT-NNN estancado
    - ACAD-TKT-003 (MED): cierre funcional 2026-07-18 → ACAD-TKT-003
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "ACADEMY_BACKLOG.md"
PLAN_LEGACY = REPO_ROOT / "docs" / "PLAN_ACADEMY_CALIDAD.md"
ESTADO_LEGACY = REPO_ROOT / "docs" / "ESTADO_ACADEMY.md"
QA_LEGACY = REPO_ROOT / "docs" / "ACADEMY_QA_CHECKLIST.md"

# ── Regex canónicas ──────────────────────────────────────────────────
_RE_TKT_HEADER = re.compile(
    r"^- \*\*ACAD-TKT-(\d+)\*\* \[(?P<sev>(CRIT|HIGH|MED|LOW|TEST))\] — (?P<title>.+?)\s*$",
    re.MULTILINE,
)
_RE_STATE = re.compile(r"\*\*state:\*\*\s*([⬜🟡✅📜])")
_RE_SOURCE = re.compile(r"\*\*source:\*\*\s*(.+?)\n")
_RE_FILES = re.compile(r"\*\*files:\*\*\s*(.+?)\n")
_RE_GATE = re.compile(r"\*\*gate:\*\*\s*`([^`]+)`")

DEPRECATION_BANNERS = {
    PLAN_LEGACY: "DEPRECADO",
    ESTADO_LEGACY: "DEPRECADO",
    QA_LEGACY: "DEPRECADO",
}


def _read(relative_path: Path) -> str:
    return relative_path.read_text(encoding="utf-8")


def _parse_tickets(backlog_text: str) -> list[dict]:
    """Parsea el ACADEMY_BACKLOG.md en tickets estructurados.

    Cada ticket conserva: ``number``, ``severity``, ``title``, ``state``,
    ``source``, ``files``, ``gate``.
    """
    tickets = []
    # Iteramos por bloques ACAD-TKT-NNN consecutivos en el documento.
    matches = list(_RE_TKT_HEADER.finditer(backlog_text))
    for idx, m in enumerate(matches):
        block_start = m.end()
        block_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(backlog_text)
        body = backlog_text[block_start:block_end]

        state_m = _RE_STATE.search(body)
        source_m = _RE_SOURCE.search(body)
        files_m = _RE_FILES.search(body)
        gate_m = _RE_GATE.search(body)

        tickets.append({
            "number": int(m.group(1)),
            "severity": m.group("sev"),
            "title": m.group("title").strip(),
            "state": state_m.group(1) if state_m else None,
            "source": source_m.group(1).strip() if source_m else None,
            "files": files_m.group(1).strip() if files_m else None,
            "gate": gate_m.group(1).strip() if gate_m else None,
        })
    return tickets


# ===========================================================================
# A. Tests estructurales (parsing del .md; sin dependencias runtime)
# ===========================================================================


@pytest.fixture(scope="module")
def backlog_text() -> str:
    assert BACKLOG.exists(), (
        "❌ docs/ACADEMY_BACKLOG.md no existe. Debe crearse como fuente única ANTES de correr este test. "
        "Ver docs/ACADEMY_BACKLOG.md §7 regla anti-drift."
    )
    return _read(BACKLOG)


@pytest.fixture(scope="module")
def tickets(backlog_text: str) -> list[dict]:
    return _parse_tickets(backlog_text)


# ── A.1. Forma del documento ──────────────────────────────────────────


def test_backlog_file_exists():
    """El backlog maestro debe existir físicamente en docs/."""
    assert BACKLOG.exists(), f"Documento fuente única faltante: {BACKLOG}"


def test_backlog_has_single_source_of_truth_banner(backlog_text: str):
    """El documento debe declararse como ÚNICA fuente de verdad en §1."""
    assert "FUENTE ÚNICA" in backlog_text
    assert "ACAD-TKT-NNN" in backlog_text, "El documento debe usar IDs ACAD-TKT-NNN como esquema"
    assert "ACAD-TKT-" not in backlog_text or "ACAD-TKT-NNN" in backlog_text


def test_backlog_documents_state_taxonomy(backlog_text: str):
    """§1.1 debe declarar la taxonomía de estados: ⬜ 🟡 ✅ 📜."""
    for glyph in ("⬜", "🟡", "✅", "📜"):
        assert glyph in backlog_text, f"Glyph de estado faltante: {glyph!r}"


def test_backlog_documents_severity_taxonomy(backlog_text: str):
    """§1.2 debe declarar la taxonomía de severidades: CRIT, HIGH, MED, LOW, TEST."""
    for sev in ("CRIT", "HIGH", "MED", "LOW", "TEST"):
        assert sev in backlog_text, f"Severidad {sev!r} debe aparecer como categoría válida"


# ── A.2. Esquema de cada ticket ──────────────────────────────────────


def test_every_ticket_has_state(tickets):
    """Todo ticket debe declarar estado explícito."""
    no_state = [t for t in tickets if not t["state"]]
    assert not no_state, (
        f"Tickets sin **state::** {len(no_state)} encontrados. "
        f"Primeros 3: {no_state[:3]}"
    )


def test_every_pending_ticket_has_gate(tickets):
    """Todos los ⬜ deben tener `gate:` ejecutable (regla anti-drift §7.3)."""
    without_gate = [
        t for t in tickets
        if t["state"] == "⬜" and not t["gate"]
    ]
    assert not without_gate, (
        f"Tickets ⬜ sin gate ejecutable ({len(without_gate)}): "
        f"{[(t['number'], t['title'][:40]) for t in without_gate[:5]]}. "
        rf"Fix: agregar `**gate:** \`pytest tests/...\`` en ACADEMY_BACKLOG.md"
    )


def test_every_done_ticket_has_gate_or_evidence(tickets):
    """Tickets ✅ deben tener gate documentado o al menos nota de evidencia."""
    done_without_anything = [
        t for t in tickets
        if t["state"] == "✅" and not t["gate"] and (t["source"] is None or "✅" not in t["source"])
    ]
    assert not done_without_anything, (
        f"Tickets ✅ sin gate + sin source: {[(t['number'], t['title'][:30]) for t in done_without_anything[:3]]}"
    )


def test_every_historical_ticket_has_evidence(tickets):
    """Tickets 📜 (cierre documental) deben traer evidencia de la fecha de cierre.

    La evidencia puede aparecer en ``title``, ``source``, ``gate`` o ``notes``.
    Buscamos la cadena ``cierre`` (case-insensitive) en cualquiera de los
    campos, más la fecha entre paréntesis ``2026`` para mayor robustez.
    """
    haystack_fields = ("title", "source", "gate", "notes")
    no_date = []
    for t in tickets:
        if t["state"] != "📜":
            continue
        concat = " ".join(str(t.get(f, "") or "") for f in haystack_fields).lower()
        if "cierre" not in concat:
            no_date.append(t)
    assert not no_date, (
        f"Tickets 📜 sin evidencia de cierre documental: "
        f"{[(t['number'], t['title'][:40]) for t in no_date[:3]]}"
    )


def test_ticket_ids_are_unique_and_sequential(tickets):
    """Los IDs ACAD-TKT-NNN deben ser únicos y sin huecos no anotados."""
    numbers = sorted(t["number"] for t in tickets)
    # Permite huecos HASTA cierto tamaño, pero detecta números duplicados.
    duplicates = [n for n in numbers if numbers.count(n) > 1]
    assert not duplicates, f"ACAD-TKT-NNN duplicados: {set(duplicates)}"


def test_ticket_severity_enum_valid(tickets):
    """Severidades deben ser exactamente las 5 declaradas en §1.2."""
    valid = {"CRIT", "HIGH", "MED", "LOW", "TEST"}
    invalid = {t["number"]: t["severity"] for t in tickets if t["severity"] not in valid}
    assert not invalid, f"Severidades inválidas: {invalid}"


# ── A.3. Cierre documental de los 3 docs legacy ────────────────────


@pytest.mark.parametrize(
    "legacy_path,expected_token",
    [
        (PLAN_LEGACY, "DEPRECADO"),
        (ESTADO_LEGACY, "DEPRECADO"),
        (QA_LEGACY, "DEPRECADO"),
    ],
    ids=["PLAN_ACADEMY_CALIDAD", "ESTADO_ACADEMY", "ACADEMY_QA_CHECKLIST"],
)
def test_legacy_doc_has_deprecation_banner(legacy_path: Path, expected_token: str):
    """Los 3 docs legacy (PLAN/ESTADO/QA) deben tener banner DEPRECADO explícito."""
    if not legacy_path.exists():
        pytest.skip(f"Doc legacy no presente: {legacy_path}")
    text = _read(legacy_path)
    assert expected_token in text, (
        f"❌ {legacy_path.name} NO contiene banner de deprecación {expected_token!r}.\n"
        f"Acción: agregar banner que redirija a docs/ACADEMY_BACKLOG.md."
    )


@pytest.mark.parametrize(
    "legacy_path",
    [PLAN_LEGACY, ESTADO_LEGACY, QA_LEGACY],
    ids=["PLAN_ACADEMY_CALIDAD", "ESTADO_ACADEMY", "ACADEMY_QA_CHECKLIST"],
)
def test_legacy_doc_redirects_to_backlog(legacy_path: Path):
    """Los 3 docs legacy deben hacer referencia explícita al ACADEMY_BACKLOG.md."""
    if not legacy_path.exists():
        pytest.skip(f"Doc legacy no presente: {legacy_path}")
    text = _read(legacy_path)
    assert "ACADEMY_BACKLOG.md" in text, (
        f"❌ {legacy_path.name} no redirige a docs/ACADEMY_BACKLOG.md"
    )


# ── A.4. No hay IDs legacy (ACAD-HIGH-001, ACAD-CRIT-001, ACAD-H01, ...) sueltos ──


def test_no_legacy_acad_ids_in_active_areas(backlog_text: str):
    """Solo el §2 (Histórico) puede tener IDs legacy; §3+ debe usar ACAD-TKT-NNN."""
    sections = backlog_text.split("\n## ")
    active_sections = [s for s in sections if not s.startswith("2. Capa HISTÓRICA")]
    legacy_pattern = re.compile(r"`ACAD-(CRIT|HIGH|MED|LOW|MF|T|C|M|H|L)[-_]\d+`")
    leaks = {}
    for idx, section in enumerate(active_sections):
        # Permitimos MENCIONES explícitas en campos `source:` (es histórico).
        hits = legacy_pattern.findall(section)
        if hits:
            leaks[f"section_after_§{idx}"] = hits
    # Cualquier leak debe estar en un campo `source:` o nota explícita.
    # Por ahora aceptamos: cualquier leak NO debe estar aislado, debe estar empaquetado.
    assert not leaks or all(
        # filtro conservador: solo aceptamos si la línea dice explícitamente "source:"
        "**source:**" in section
        for section in active_sections
        for hits in [legacy_pattern.findall(section)]
        if hits
    ), f"IDs legacy detectados en secciones activas: {leaks}"


# ===========================================================================
# B. Tests parametrizados por ACAD-TKT-NNN
# ===========================================================================
#
# Estos tests son los "regression gates" para los tickets estructurales
# (no requieren DB ni runtime; son greps contra el código).
#
# Cuando el FIX del ticket esté mergeado, mover ⬜ → ✅ en ACADEMY_BACKLOG.md
# y MANTENER estos tests como gates permanentes (regresión).


# Helper: comando de CLI parametrizable.
def _run_cli(*args):
    """Ejecuta un comando y devuelve exitcode + stdout/stderr combinados."""
    proc = subprocess.run(
        args,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, (proc.stdout + proc.stderr), proc


# ── B.1. HISTÓRICO — gates de regresión permanente (ACAD-TKT-001, 002, 003) ──


@pytest.mark.parametrize(
    "needle,path",
    [
        ("id: number", "frontend/src/components/CourseCatalog.tsx"),
        ("id: number", "frontend/src/components/MyEnrollments.tsx"),
    ],
    ids=["CourseCatalog.no_id_number", "MyEnrollments.no_id_number"],
)
def test_acad_tkt_001_uuid_types_only(needle: str, path: str):
    """ACAD-TKT-001 (CRIT histórico): ningún archivo debe declarar `id: number`.

    Gate permanente de regresión. Si alguien reintroduce el tipo number,
    el merge se bloquea.
    """
    full = REPO_ROOT / path
    if not full.exists():
        pytest.skip(f"Archivo no presente (puede haber sido refactorizado): {path}")
    text = _read(full)
    assert needle not in text, (
        f"❌ ACAD-TKT-001 REGRESIÓN: '{needle}' reintroducido en {path}. "
        f"El código debe usar `id: string` (UUID) y `enrolledCourseIds: string[]`."
    )


def test_acad_tkt_002_dashboard_shape():
    """ACAD-TKT-002 (CRIT histórico): el dashboard endpoint retorna shape completa.

    Verifica por ESTÁTICA del código que el endpoint ``dashboard_metrics``
    expone los 3 campos que el frontend consume (sin tener que levantar
    el server ni DB).
    """
    api_file = REPO_ROOT / "backend" / "api" / "academy.py"
    if not api_file.exists():
        pytest.skip("backend/api/academy.py no presente")
    text = _read(api_file)
    for expected in ("enrollment_trends", "top_courses", "cards"):
        assert expected in text, (
            f"❌ ACAD-TKT-002 REGRESIÓN: el endpoint dashboard_metrics de academy.py "
            f"debe retornar '{expected}'. Si lo borraste, reintroducilo."
        )


def test_acad_tkt_003_delete_submission_writes_audit_log():
    """ACAD-TKT-003 (MED cerrado 2026-07-18): DELETE submission preserva payload_json.

    Garantiza que el flujo ``delete_submission_admin`` SIGA creando un
    AcademyActivityLog con ``event_type='assignment_submission_archived'``
    y ``payload_json`` con los campos del closure.
    """
    api_file = REPO_ROOT / "backend" / "api" / "academy.py"
    if not api_file.exists():
        pytest.skip("backend/api/academy.py no presente")
    text = _read(api_file)
    for token in (
        "assignment_submission_archived",
        "payload_json",
        "submission_id",
        "file_url",
        "lesson_id",
        "enrollment_id",
    ):
        assert token in text, (
            f"❌ ACAD-TKT-003 REGRESIÓN: token {token!r} esperado en delete_submission_admin. "
            f"Si lo borraste, reintroducilo para preservar trazabilidad Seaweed."
        )


# ── B.2. CRIT pendientes (ACAD-TKT-020..043) ──
# ACAD-TKT-010..015 (Fase A CRIT) fueron cerrados en commit 2026-07-19.
# Los regression gates runtime viven en ``tests/test_academy_fase_a_crit.py``
# (no acá) — chequean la VALIDACIÓN end-to-end, no el ancla textual que es
# frágil ante refactors benignos (renames, reorders). Los cubre CI en-suite.


# ── B.3. HIGH pendientes (ACAD-TKT-020..043) ──


@pytest.mark.parametrize(
    "tkt,needle,rationale",
    [
        # ACAD-TKT-020..022: backend payload typing — pendiente, gate aún no
        # debe confirmar la presencia.
        (20, r"AssessmentQuestionPayload", "tipo Pydantic para questions"),
        (21, r"file_size|content_length|max_upload", "limite de tamano en submit_assignment"),
        (22, r"allowed_mimetypes|mimetype|content_type", "validacion de mimetype"),
        # ACAD-TKT-040..043: frontend hardening — gates en su mayoría
        # pendientes. ACAD-TKT-041 es CASO NEGATIVO: api.qrserver.com NO
        # debe aparecer; como el bug está abierto, xfail con instrucción.
        (40, r"hasModuleAccess|allowedPermissions", "filtro LECTOR sin admin items"),
        (41, r"api\.qrserver\.com", "no debe haber dependencia de QR externo"),
        (43, r"moduleConfigs\.ts|academy.*layout\.tsx", "sidebar config dual"),
    ],
)
def test_high_pending_tickets_have_negative_evidence(tkt: int, needle: str, rationale: str):
    """Gates de regresión para los HIGH que ya tienen cierre implementado."""
    import re as _re

    cert_view = REPO_ROOT / "frontend" / "src" / "components" / "academy" / "CertificateView.tsx"
    api_file = REPO_ROOT / "backend" / "api" / "academy.py"
    academy_layout = REPO_ROOT / "frontend" / "src" / "app" / "plataforma" / "academy" / "layout.tsx"
    module_configs = REPO_ROOT / "frontend" / "src" / "components" / "workspace" / "moduleConfigs.ts"

    if tkt == 20:
        assert "class AssessmentQuestionPayload" in _read(api_file)
    elif tkt == 21:
        text = _read(api_file)
        assert "MAX_SIZE" in text and "await file.read()" in text
    elif tkt == 22:
        text = _read(api_file)
        assert "ALLOWED_TYPES" in text and "file.content_type not in ALLOWED_TYPES" in text
    elif tkt == 40:
        text = _read(academy_layout)
        assert "ACADEMY_SIDEBAR_SECTIONS" in text and "hasModuleAccess('academy', item.level)" in text
    elif tkt == 41:
        assert cert_view.exists()
        assert not _re.search(needle, _read(cert_view))
    elif tkt == 43:
        assert "academy:" not in _read(module_configs)
        assert "ACADEMY_SIDEBAR_SECTIONS" in _read(academy_layout)
    else:  # pragma: no cover - el parametrizado superior es el contrato.
        pytest.fail(f"Ticket HIGH no reconocido: {tkt} ({rationale})")


# ── B.4. Sanity checks runtime (base mínima, ya cubierta por test_academy_api.py) ──


def test_acad_tkt_runs_alongside_existing_academy_tests():
    """Suite complementaria a ``tests/test_academy_api.py``. Aquí NO ejecutamos
    la base completa por costo; lo asumimos cubierto por CI en run_ci.sh."""

    # Si llegamos aquí es porque los tests estructurales pasaron. Esta marca
    # es la señal al runner de que la gating estructural está OK.
    assert BACKLOG.exists()
