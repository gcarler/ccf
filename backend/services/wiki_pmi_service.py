"""Servicio de doctrina PMI y gestión de páginas canónicas en la Wiki Ministerial.

Carga e indexa los 7 volúmenes canónicos de la biblioteca metodológica PMI
en la tabla `wiki_pages` para consulta universal por los equipos de proyectos.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)

DEFAULT_PMI_KB_DIR = Path(os.environ.get("PMI_KB_DIR", "/root/pmi_knowledge_base"))

CANONICAL_VOLUMES_METADATA = [
    {
        "vol": 0,
        "page_key": "wiki_pmi_00_indice_maestro",
        "file_name": "00_INDICE_MAESTRO_PMI_CCF.md",
        "title": "Compendio Maestro de Dirección de Proyectos (Estándar PMI / PMBOK)",
        "summary": "Índice maestro y arquitectura metodológica del compendio canónico PMI para la plataforma CCF.",
        "tags": ["pmi", "pmbok", "proyectos", "metodologia", "indice"],
    },
    {
        "vol": 1,
        "page_key": "wiki_pmi_01_fundamentos",
        "file_name": "01_FUNDAMENTOS_Y_DEFINICION_PMI.md",
        "title": "Fundamentos Canónicos de la Dirección de Proyectos (Estándar PMI)",
        "summary": "Definición ontológica de proyecto, triple restricción ampliada y principios éticos y profesionales PMI.",
        "tags": ["pmi", "fundamentos", "triple_restriccion", "alcance", "tiempo", "costo"],
    },
    {
        "vol": 2,
        "page_key": "wiki_pmi_02_ciclo_de_vida",
        "file_name": "02_CICLO_DE_VIDA_Y_GRUPOS_DE_PROCESOS.md",
        "title": "Ciclo de Vida del Proyecto y Grupos de Procesos (PMI / PMBOK)",
        "summary": "Los 5 Grupos de Procesos: Iniciación, Planificación, Ejecución, Monitoreo y Control, y Cierre.",
        "tags": ["pmi", "ciclo_de_vida", "grupos_de_procesos", "planificacion", "control"],
    },
    {
        "vol": 3,
        "page_key": "wiki_pmi_03_edt_wbs",
        "file_name": "03_ESTRUCTURA_DESGLOSE_TRABAJO_EDT_WBS.md",
        "title": "Estructura de Desglose del Trabajo (EDT / WBS) — Estándar Canónico PMI",
        "summary": "La Regla del 100%, codificación jerárquica de entregables, paquetes de trabajo y cuentas de control.",
        "tags": ["pmi", "edt", "wbs", "regla_100", "paquetes_trabajo", "entregables"],
    },
    {
        "vol": 4,
        "page_key": "wiki_pmi_04_metricas_evm",
        "file_name": "04_BATERIA_DE_INDICADORES_METRICAS_EVM.md",
        "title": "Batería Canónica de Indicadores y Métricas EVM (Estándar PMI)",
        "summary": "Fórmulas y métricas de Valor Ganado: BAC, PV, EV, AC, CV, SV, CPI, SPI, EAC, ETC, TCPI y Tiempo Ganado (ES).",
        "tags": ["pmi", "evm", "earned_value", "cpi", "spi", "eac", "tcpi", "tiempo_ganado"],
    },
    {
        "vol": 5,
        "page_key": "wiki_pmi_05_matriz_cuadrantes",
        "file_name": "05_MATRIZ_DE_CORRELACIONES_DIAGNOSTICO_Y_CURVA_S.md",
        "title": "Matriz de Correlaciones, Diagnóstico de Salud y Curva S (PMI)",
        "summary": "Matriz diagnóstica de 4 Cuadrantes CPI vs SPI, alertas tempranas (Regla 15%) y Curva S sigmoidea acumulada.",
        "tags": ["pmi", "matriz_cuadrantes", "curva_s", "diagnostico", "alertas_tempranas", "regla_15"],
    },
    {
        "vol": 6,
        "page_key": "wiki_pmi_06_gestion_riesgos",
        "file_name": "06_GESTION_DE_RIESGOS_CALIDAD_Y_ENTREGABLES.md",
        "title": "Gestión de Riesgos, Calidad y Control Integrado de Cambios (PMI)",
        "summary": "Identificación, matriz de probabilidad e impacto, planes de respuesta a riesgos y aseguramiento de calidad.",
        "tags": ["pmi", "riesgos", "calidad", "control_cambios", "contingencia"],
    },
]


def load_volume_markdown_content(file_name: str, base_dir: Optional[Path] = None) -> str:
    """Carga el contenido Markdown de un volumen desde el directorio de doctrina."""
    directory = base_dir or DEFAULT_PMI_KB_DIR
    target_path = directory / file_name

    if target_path.is_file():
        try:
            return target_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("Error leyendo archivo %s: %s", target_path, e)

    # Fallback sintetizado si el archivo físico no estuviese disponible
    return (
        f"# {file_name.replace('.md', '').replace('_', ' ')}\n\n"
        f"Contenido oficial de la Biblioteca Metodológica de Dirección de Proyectos (Estándar PMI).\n"
        f"Consulte el documento maestro en el repositorio central de la plataforma CCF."
    )


def get_canonical_pmi_volumes(base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retorna la lista completa de volúmenes canónicos con sus metadatos y contenido."""
    volumes = []
    for meta in CANONICAL_VOLUMES_METADATA:
        content = load_volume_markdown_content(meta["file_name"], base_dir=base_dir)
        vol_info = dict(meta)
        vol_info["content"] = content
        vol_info["char_count"] = len(content)
        vol_info["word_count"] = len(content.split())
        volumes.append(vol_info)
    return volumes


def seed_pmi_wiki_doctrine(
    db: Session,
    sede_id: Optional[UUID] = None,
    author_id: Optional[UUID] = None,
    force_update: bool = False,
    base_dir: Optional[Path] = None,
) -> List[models.WikiPage]:
    """Siembra o actualiza las 7 páginas canónicas de doctrina PMI en `wiki_pages`.

    Args:
        db: Sesión SQLAlchemy.
        sede_id: ID de la sede o None si es global ministerial.
        author_id: Persona ID del autor responsable.
        force_update: Si es True, sobreescribe páginas existentes aunque ya existan.
        base_dir: Directorio alternativo de lectura de archivos Markdown.

    Returns:
        Lista de páginas WikiPage sincronizadas.
    """
    now = datetime.now(timezone.utc)
    volumes = get_canonical_pmi_volumes(base_dir=base_dir)
    seeded_pages: List[models.WikiPage] = []

    for vol in volumes:
        page_key = vol["page_key"]
        title = vol["title"]
        content = vol["content"]
        category = "proyectos_pmi"
        tags = vol["tags"]

        existing = (
            db.query(models.WikiPage)
            .filter(
                models.WikiPage.page_key == page_key,
                models.WikiPage.sede_id == sede_id,
            )
            .first()
        )

        if existing:
            if force_update or existing.deleted_at is not None:
                # Si el contenido cambió, crear versión de historial antes de actualizar
                if existing.content != content or existing.title != title:
                    version_history = models.WikiPageVersion(
                        wiki_page_id=existing.id,
                        version_number=existing.version,
                        title=existing.title,
                        content=existing.content,
                        created_by_persona_id=author_id,
                        created_at=now,
                    )
                    db.add(version_history)
                    existing.version += 1

                existing.title = title
                existing.content = content
                existing.category = category
                existing.tags = tags
                existing.deleted_at = None
                existing.updated_at = now
                if author_id:
                    existing.author_id = author_id
            seeded_pages.append(existing)
        else:
            new_page = models.WikiPage(
                page_key=page_key,
                title=title,
                content=content,
                version=1,
                category=category,
                tags=tags,
                sede_id=sede_id,
                author_id=author_id,
                created_at=now,
                updated_at=now,
            )
            db.add(new_page)
            seeded_pages.append(new_page)

    db.commit()
    for page in seeded_pages:
        db.refresh(page)

    logger.info("Sincronizadas %d páginas canónicas de Wiki PMI", len(seeded_pages))
    return seeded_pages


def audit_pmi_wiki_doctrine_completeness(base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Audita la completitud de la doctrina PMI en disco (función pura, sin E/S de DB).

    Inspecciona `CANONICAL_VOLUMES_METADATA` y `get_canonical_pmi_volumes(
    base_dir=base_dir)` y retorna:
    - `expected_volumes`: número de volúmenes canónicos (7).
    - `loaded_from_disk_count`: cuántos archivos físicos existen en
      `(base_dir or DEFAULT_PMI_KB_DIR) / meta['file_name']`.
    - `fallback_synthesized_count`: volúmenes servidos por el fallback
      sintetizado (expected - loaded).
    - `completeness_pct`: porcentaje de volúmenes cargados desde disco
      (2 decimales; 100.0 si no hay volúmenes esperados).
    - `total_words`: suma de `word_count` de todos los volúmenes
      (incluye fallback sintetizado).
    - `missing_files`: lista ordenada de `file_name` ausentes en disco.
    - `status`: 'complete' si los 7 archivos están en disco, 'partial' si
      se cargó al menos uno, 'fallback_only' si ninguno.
    """
    directory = base_dir or DEFAULT_PMI_KB_DIR
    expected_volumes = len(CANONICAL_VOLUMES_METADATA)

    loaded_from_disk_count = 0
    missing_files: List[str] = []
    for meta in CANONICAL_VOLUMES_METADATA:
        if (directory / meta["file_name"]).is_file():
            loaded_from_disk_count += 1
        else:
            missing_files.append(meta["file_name"])
    missing_files.sort()

    fallback_synthesized_count = expected_volumes - loaded_from_disk_count
    completeness_pct = (
        round((loaded_from_disk_count / expected_volumes) * 100.0, 2)
        if expected_volumes > 0
        else 100.0
    )

    total_words = sum(vol["word_count"] for vol in get_canonical_pmi_volumes(base_dir=base_dir))

    if fallback_synthesized_count == 0:
        status = "complete"
    elif loaded_from_disk_count > 0:
        status = "partial"
    else:
        status = "fallback_only"

    return {
        "expected_volumes": expected_volumes,
        "loaded_from_disk_count": loaded_from_disk_count,
        "fallback_synthesized_count": fallback_synthesized_count,
        "completeness_pct": completeness_pct,
        "total_words": total_words,
        "missing_files": missing_files,
        "status": status,
    }


def search_canonical_pmi_volumes(
    query: Optional[str] = None,
    tag_filter: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Consulta y clasifica por relevancia los 7 volúmenes canónicos de doctrina PMI (PMBOK §4.4 Manage Project Knowledge)."""
    volumes = get_canonical_pmi_volumes(base_dir=base_dir)
    q_norm = (query or "").strip().lower()
    tag_norm = (tag_filter or "").strip().lower()

    matched: List[Dict[str, Any]] = []
    for vol in volumes:
        tags_normalized = [str(t).strip().lower() for t in vol.get("tags", [])]
        if tag_norm and tag_norm not in tags_normalized:
            continue

        if not q_norm:
            score = 1
        else:
            score = 0
            title_low = str(vol.get("title", "")).lower()
            key_low = str(vol.get("page_key", "")).lower()
            if q_norm in title_low or q_norm in key_low:
                score += 3
            if any(q_norm in str(t).lower() for t in vol.get("tags", [])):
                score += 2
            if q_norm in str(vol.get("summary", "")).lower():
                score += 2
            if q_norm in str(vol.get("content", "")).lower():
                score += 1
            if score == 0:
                continue

        vol_copy = dict(vol)
        vol_copy["match_score"] = score
        matched.append(vol_copy)

    matched.sort(key=lambda item: (-int(item["match_score"]), int(item["vol"])))
    return matched


SUPPORTED_PMI_SLASH_COMMANDS = {
    "evm",
    "wbs",
    "charter",
    "raid",
    "raci",
    "ccb",
    "dod",
    "pert",
    "cpm",
    "lessons",
}

SLASH_COMMAND_RE = re.compile(r"/([a-z][a-z0-9_-]{1,31})\b")


def extract_wiki_slash_commands_inventory(markdown_text: Optional[str]) -> Dict[str, Any]:
    """Inventario de invocaciones de comandos slash PMI (PMBOK §4.4).

    Escanea `markdown_text` (None o vacío → conteos en 0) detectando tokens
    `/comando` con formato `/([a-z][a-z0-9_-]{1,31})` que aparezcan al inicio
    de línea o inmediatamente después de un espacio. Se ignoran:
    - bloques de código cercados (``` y ~~~);
    - URLs (http://…, https://…) y rutas de sistema (/root/…, /srv/…):
      cualquier token cuyo interior contenga otro '/' además del slash
      inicial (o que no empiece por '/') no es una invocación de comando.
    Los comandos se normalizan a minúsculas y se separan en soportados
    (SUPPORTED_PMI_SLASH_COMMANDS) y no soportados:
    - 'empty' si total_invocations == 0;
    - 'valid_pmi_commands' si len(unsupported_commands) == 0;
    - 'contains_unsupported' si len(unsupported_commands) > 0.
    """
    text = str(markdown_text or "")
    total_invocations = 0
    detected_in_order: List[str] = []

    inside_fence = False
    fence_marker: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not inside_fence:
            fence_open = re.match(r"^(`{3,}|~{3,})\S*\s*$", stripped)
            if fence_open:
                inside_fence = True
                fence_marker = fence_open.group(1)[:3]
                continue
            for token in re.split(r"\s+", line):
                if not token.startswith("/"):
                    continue
                name_match = re.match(r"/([a-z][a-z0-9_-]{1,31})\b", token)
                if not name_match:
                    continue
                if token.count("/") != 1:
                    continue  # URL (https://…) o ruta de sistema (/root/…)
                detected_in_order.append(name_match.group(1).lower())
                total_invocations += 1
        else:
            fence_close = re.match(r"^(`{3,}|~{3,})\s*$", stripped)
            if fence_close and fence_close.group(1)[:3] == fence_marker:
                inside_fence = False
            fence_marker = fence_marker

    unique_commands = sorted(set(detected_in_order))
    supported_commands = sorted(
        {cmd for cmd in unique_commands if cmd in SUPPORTED_PMI_SLASH_COMMANDS}
    )
    unsupported_commands = sorted(
        {cmd for cmd in unique_commands if cmd not in SUPPORTED_PMI_SLASH_COMMANDS}
    )
    command_counts: Dict[str, int] = {}
    for cmd in detected_in_order:
        command_counts[cmd] = command_counts.get(cmd, 0) + 1
    command_counts = {cmd: count for cmd, count in sorted(command_counts.items())}

    if total_invocations == 0:
        syntax_status = "empty"
    elif not unsupported_commands:
        syntax_status = "valid_pmi_commands"
    else:
        syntax_status = "contains_unsupported"

    return {
        "total_invocations": total_invocations,
        "unique_commands": unique_commands,
        "supported_commands": supported_commands,
        "unsupported_commands": unsupported_commands,
        "command_counts": command_counts,
        "syntax_status": syntax_status,
    }


def audit_wiki_page_knowledge_hygiene(
    title: Optional[str],
    content: Optional[str],
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evalúa la higiene estructural, etiquetado taxonómico y referencias cruzadas de una página Wiki según PMI PMBOK §4.4."""
    title_norm = (title or "").strip()
    content_norm = (content or "").strip()
    normalized_tags = sorted(
        {str(t).strip().lower() for t in (tags or []) if str(t).strip()}
    )
    word_count = len(content_norm.split())
    cross_links_count = len(
        re.findall(r"\[[^\]]+\]\([^)]+\)|\[\[[^\]]+\]\]", content_norm)
    )
    section_headings_count = len(re.findall(r"(?m)^#{1,6}\s+\S+", content_norm))

    hygiene_gaps: List[str] = []
    if len(title_norm) < 3:
        hygiene_gaps.append("missing_title")
    if word_count < 25:
        hygiene_gaps.append("thin_content")
    if section_headings_count < 1:
        hygiene_gaps.append("unstructured_sections")
    if len(normalized_tags) < 1:
        hygiene_gaps.append("untagged_page")

    hygiene_score_pct = round(((4 - len(hygiene_gaps)) / 4) * 100.0, 2)

    if len(hygiene_gaps) == 0 and cross_links_count >= 1:
        knowledge_hygiene_status = "exemplary_reference"
    elif len(hygiene_gaps) == 0 and cross_links_count == 0:
        knowledge_hygiene_status = "compliant_article"
    elif 1 <= len(hygiene_gaps) <= 2:
        knowledge_hygiene_status = "needs_enrichment"
    else:
        knowledge_hygiene_status = "stub_or_incomplete"

    return {
        "has_valid_title": len(title_norm) >= 3,
        "word_count": word_count,
        "section_headings_count": section_headings_count,
        "cross_links_count": cross_links_count,
        "normalized_tags": normalized_tags,
        "hygiene_gaps": hygiene_gaps,
        "hygiene_score_pct": hygiene_score_pct,
        "knowledge_hygiene_status": knowledge_hygiene_status,
    }


def summarize_wiki_revision_history_velocity(
    revisions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evalúa la evolución colaborativa, coautoría y magnitud de cambios en el historial de versiones de una página Wiki según PMI PMBOK §4.4."""
    valid_revisions = [r for r in (revisions or []) if isinstance(r, dict)]
    unique_authors_set: set[str] = set()
    word_counts: List[int] = []

    for rev in valid_revisions:
        author = str(
            rev.get("author_id")
            or rev.get("changed_by")
            or rev.get("updated_by")
            or ""
        ).strip()
        if author:
            unique_authors_set.add(author)
        content_text = str(rev.get("content") or rev.get("markdown") or "").strip()
        word_counts.append(len(content_text.split()))

    total_revisions = len(valid_revisions)
    unique_authors_count = len(unique_authors_set)
    latest_word_count = word_counts[-1] if word_counts else 0
    initial_word_count = word_counts[0] if word_counts else 0
    net_word_growth = latest_word_count - initial_word_count

    if total_revisions == 0:
        curation_status = "unversioned"
    elif total_revisions == 1:
        curation_status = "single_draft"
    elif total_revisions >= 2 and unique_authors_count >= 2:
        curation_status = "multi_author_curated"
    else:
        curation_status = "iteratively_refined"

    return {
        "total_revisions": total_revisions,
        "unique_authors_count": unique_authors_count,
        "initial_word_count": initial_word_count,
        "latest_word_count": latest_word_count,
        "net_word_growth": net_word_growth,
        "curation_status": curation_status,
    }


def audit_wiki_crosslink_reference_integrity(
    content: str | None,
    known_slugs: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    """Audita la integridad de referencias cruzadas [[slug]] / [[slug|label]] y (wiki:slug) según PMI PMBOK §4.4.

    - Los slugs se normalizan en minúsculas y sin espacios antes de comparar.
    - `total_references`: ocurrencias totales encontradas (con repetidos).
    - `unique_targets`: slugs únicos en orden de aparición.
    - `resolved_targets`: targets presentes en `known_slugs` (o todos si es
      None); `broken_targets`: ausentes (o [] si es None).
    - `integrity_pct`: % de targets resueltos (2 decimales; 100.0 sin targets).
    - `posture`: 'ISOLATED_NO_CROSSLINKS' sin referencias;
      'BROKEN_KNOWLEDGE_LINKS' con algún target roto; y
      'CONNECTED_KNOWLEDGE_GRAPH' en otro caso.
    """
    content_norm = str(content or "")
    referenced: list[str] = []
    for match in re.finditer(
        r"\[\[([^\]]+?)\s*(?:\|[^\]]*)?\]\]|\(\s*wiki:([^)\s]+)\s*\)",
        content_norm,
    ):
        raw_slug = match.group(1) if match.group(1) is not None else match.group(2)
        if raw_slug is None:
            continue
        referenced.append(re.sub(r"\s+", "", str(raw_slug)).strip().lower())

    total_references = len(referenced)
    unique_targets: list[str] = list(dict.fromkeys(referenced))

    if known_slugs is None:
        resolved_targets = list(unique_targets)
        broken_targets: list[str] = []
    else:
        known_norm = {
            re.sub(r"\s+", "", str(slug)).strip().lower() for slug in known_slugs
        }
        resolved_targets = [t for t in unique_targets if t in known_norm]
        broken_targets = [t for t in unique_targets if t not in known_norm]

    integrity_pct = (
        round((len(resolved_targets) / len(unique_targets)) * 100.0, 2)
        if unique_targets
        else 100.0
    )

    if not unique_targets:
        posture = "ISOLATED_NO_CROSSLINKS"
    elif len(broken_targets) > 0:
        posture = "BROKEN_KNOWLEDGE_LINKS"
    else:
        posture = "CONNECTED_KNOWLEDGE_GRAPH"

    return {
        "total_references": total_references,
        "unique_targets": unique_targets,
        "resolved_targets": resolved_targets,
        "broken_targets": broken_targets,
        "integrity_pct": integrity_pct,
        "posture": posture,
    }


def audit_wiki_stakeholder_signoffs(
    signoffs: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita la matriz de aprobación y firmas de interesados en páginas Wiki según PMI PMBOK §13.3 y §10.2."""
    valid_items = [item for item in (signoffs or []) if isinstance(item, dict)]
    total_reviewers = len(valid_items)

    approved_tokens = ("approved", "aprobado", "signed_off", "accepted", "firmado")
    rejected_tokens = ("rejected", "rechazado", "changes_requested", "observado")

    approved_count = 0
    rejected_or_changes_requested_count = 0

    for item in valid_items:
        val = str(item.get("status") or item.get("decision") or "").strip().lower()
        if val in approved_tokens:
            approved_count += 1
        elif val in rejected_tokens:
            rejected_or_changes_requested_count += 1

    pending_count = max(
        0, total_reviewers - approved_count - rejected_or_changes_requested_count
    )
    approval_rate = (
        round((approved_count / total_reviewers) * 100.0, 2)
        if total_reviewers > 0
        else 0.0
    )

    if total_reviewers == 0:
        posture = "NO_REVIEWERS_ASSIGNED"
    elif rejected_or_changes_requested_count > 0:
        posture = "BLOCKED_BY_REJECTION"
    elif approved_count == total_reviewers:
        posture = "FULLY_SIGNED_OFF"
    else:
        posture = "PENDING_STAKEHOLDER_SIGNOFF"

    return {
        "total_reviewers": total_reviewers,
        "approved_count": approved_count,
        "rejected_or_changes_requested_count": rejected_or_changes_requested_count,
        "pending_count": pending_count,
        "approval_rate": approval_rate,
        "posture": posture,
    }


def audit_wiki_template_section_compliance(
    content: str | None,
    required_sections: list[str] | None = None,
) -> dict[str, Any]:
    """Audita secciones obligatorias de plantillas PMO en una página Wiki (PMBOK §4.4 / §10.2).

    Extrae encabezados Markdown (#..######) fuera de bloques de código cercados y,
    normalizando sin tildes (NFKD/ascii) y en minúsculas, verifica si cada sección
    requerida aparece como subcadena de algún encabezado:
    - `total_required`: secciones exigidas (default PMBOK: Objetivo, Alcance,
      Riesgos, Criterios de Aceptacion).
    - `present_sections` / `missing_sections`: hallazgo por sección, orden
      según required_sections.
    - `compliance_pct`: % de secciones presentes (2 decimales; 100.0 sin exigidas).
    - `posture`: 'EMPTY_WIKI_CONTENT' con contenido vacío;
      'PMO_TEMPLATE_COMPLIANT' con compliance == 100.0;
      'PARTIAL_TEMPLATE_COMPLIANCE' con compliance >= 50.0; y
      'NON_COMPLIANT_STRUCTURE' en otro caso.
    """
    text = (content or "").strip()
    required = list(required_sections) if required_sections is not None else [
        "Objetivo",
        "Alcance",
        "Riesgos",
        "Criterios de Aceptacion",
    ]
    total_required = len(required)

    def _normalize(value: str) -> str:
        stripped = unicodedata.normalize("NFKD", str(value))
        return stripped.encode("ascii", "ignore").decode("ascii").strip().lower()

    headings: list[str] = []
    in_fenced_block = False
    for line in text.splitlines():
        if re.match(r"^\s*```", line):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue
        heading_match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            headings.append(heading_match.group(1))

    normalized_headings = {_normalize(h) for h in headings}

    present_sections: list[str] = []
    missing_sections: list[str] = []
    for section in required:
        normalized_section = _normalize(section)
        if normalized_section in normalized_headings or any(
            normalized_section in normalized_heading
            for normalized_heading in normalized_headings
        ):
            present_sections.append(section)
        else:
            missing_sections.append(section)

    compliance_pct = (
        round((len(present_sections) / total_required) * 100.0, 2)
        if total_required > 0
        else 100.0
    )

    if not text:
        posture = "EMPTY_WIKI_CONTENT"
    elif compliance_pct == 100.0:
        posture = "PMO_TEMPLATE_COMPLIANT"
    elif compliance_pct >= 50.0:
        posture = "PARTIAL_TEMPLATE_COMPLIANCE"
    else:
        posture = "NON_COMPLIANT_STRUCTURE"

    return {
        "total_required": total_required,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "compliance_pct": compliance_pct,
        "posture": posture,
    }


def audit_wiki_decision_log_entries(
    decisions: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Audita la trazabilidad de registros de decisiones (Decision Log / RAID) en la Wiki según PMI PMBOK §10.2 y §4.4."""
    items = [item for item in (decisions or []) if isinstance(item, dict)]
    total_decisions = len(items)

    rationale_documented_count = 0
    decider_assigned_count = 0
    date_recorded_count = 0
    fully_traceable_count = 0

    for item in items:
        rationale_str = str(
            item.get("rationale")
            or item.get("justificacion")
            or item.get("reason")
            or ""
        ).strip()
        decider_str = str(
            item.get("decided_by")
            or item.get("owner")
            or item.get("aprobador")
            or ""
        ).strip()
        date_str = str(
            item.get("decision_date")
            or item.get("date")
            or item.get("fecha")
            or ""
        ).strip()

        has_rationale = len(rationale_str) >= 10
        has_decider = bool(decider_str)
        has_date = bool(date_str)

        if has_rationale:
            rationale_documented_count += 1
        if has_decider:
            decider_assigned_count += 1
        if has_date:
            date_recorded_count += 1
        if has_rationale and has_decider and has_date:
            fully_traceable_count += 1

    traceability_rate = (
        round((fully_traceable_count / total_decisions) * 100.0, 2)
        if total_decisions > 0
        else 0.0
    )

    if total_decisions == 0:
        posture = "NO_DECISIONS_LOGGED"
    elif traceability_rate >= 80.0:
        posture = "AUDIT_READY_DECISION_LOG"
    elif traceability_rate >= 40.0:
        posture = "PARTIAL_DECISION_TRACEABILITY"
    else:
        posture = "OPAQUE_UNTRACEABLE_DECISIONS"

    return {
        "total_decisions": total_decisions,
        "rationale_documented_count": rationale_documented_count,
        "decider_assigned_count": decider_assigned_count,
        "date_recorded_count": date_recorded_count,
        "fully_traceable_count": fully_traceable_count,
        "traceability_rate": traceability_rate,
        "posture": posture,
    }


def audit_wiki_raid_register_tables(
    markdown_text: Optional[str],
) -> dict[str, Any]:
    """Audita tablas Markdown GFM de registros RAID (Riesgos, Problemas, Acciones, Dependencias) según PMI PMBOK §11.2 y §4.4."""
    text = str(markdown_text or "")
    raid_prefix_re = re.compile(
        r"^(?:RISK|RSK|ISS|ISSUE|ACT|DEP)-\w+",
        re.IGNORECASE,
    )
    separator_cell_re = re.compile(r"^:?-{2,}:?$")
    severity_re = re.compile(
        r"\b(?:HIGH|MEDIUM|LOW|CRITICAL|ALTA|MEDIA|BAJA|CRITICA|CRÍTICA)\b",
        re.IGNORECASE,
    )

    invalid_placeholders = {"", "TBD", "N/A", "NA", "SIN ASIGNAR", "-", "NONE", "UNASSIGNED"}
    owner_header_keywords = (
        "owner",
        "propietario",
        "responsable",
        "asignado",
        "assigned",
        "lider",
        "líder",
    )
    mitigation_header_keywords = (
        "mitigacion",
        "mitigación",
        "mitigation",
        "respuesta",
        "response",
        "plan",
        "accion",
        "acción",
        "action",
        "contingencia",
    )

    total_raid_rows = 0
    fully_specified_count = 0
    unassigned_raid_ids: list[str] = []
    unmitigated_raid_ids: list[str] = []

    in_fence = False
    owner_col_idx: Optional[int] = None
    mitigation_col_idx: Optional[int] = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if not (stripped.startswith("|") and stripped.endswith("|")):
            if not stripped:
                owner_col_idx = None
                mitigation_col_idx = None
            continue

        cells = [c.strip() for c in stripped[1:-1].split("|")]
        if not cells or all(not c for c in cells):
            continue

        if all(separator_cell_re.match(c) for c in cells if c):
            continue

        first_cell_clean = re.sub(r"^[*`\s]+|[*`\s]+$", "", cells[0]).strip()
        if not raid_prefix_re.match(first_cell_clean):
            owner_col_idx = None
            mitigation_col_idx = None
            for idx, col_name in enumerate(cells):
                col_lower = col_name.lower()
                if owner_col_idx is None and any(
                    kw in col_lower for kw in owner_header_keywords
                ):
                    owner_col_idx = idx
                if mitigation_col_idx is None and any(
                    kw in col_lower for kw in mitigation_header_keywords
                ):
                    mitigation_col_idx = idx
            continue

        total_raid_rows += 1
        raid_id = first_cell_clean

        has_severity = any(bool(severity_re.search(c)) for c in cells[1:])

        has_owner = False
        if any(bool(re.search(r"@[A-Za-z0-9_.-]+", c)) for c in cells[1:]):
            has_owner = True
        elif owner_col_idx is not None and owner_col_idx < len(cells):
            candidate_owner = cells[owner_col_idx].strip()
            has_owner = candidate_owner.upper() not in invalid_placeholders
        else:
            fallback_owner_idx = 3 if len(cells) >= 5 else (2 if len(cells) == 4 else None)
            if fallback_owner_idx is not None and fallback_owner_idx < len(cells):
                candidate_owner = cells[fallback_owner_idx].strip()
                has_owner = candidate_owner.upper() not in invalid_placeholders

        has_mitigation = False
        if mitigation_col_idx is not None and mitigation_col_idx < len(cells):
            candidate_mit = cells[mitigation_col_idx].strip()
            has_mitigation = (
                len(candidate_mit) >= 8
                and candidate_mit.upper() not in invalid_placeholders
            )
        elif len(cells) >= 3:
            candidate_mit = cells[-1].strip()
            has_mitigation = (
                len(candidate_mit) >= 8
                and candidate_mit.upper() not in invalid_placeholders
            )

        if not has_owner:
            unassigned_raid_ids.append(raid_id)
        if not has_mitigation:
            unmitigated_raid_ids.append(raid_id)
        if has_severity and has_owner and has_mitigation:
            fully_specified_count += 1

    completeness_rate = (
        round((fully_specified_count / total_raid_rows) * 100.0, 2)
        if total_raid_rows > 0
        else 0.0
    )

    recommendations: list[str] = []
    if total_raid_rows == 0:
        raid_table_posture = "NO_RAID_TABLE_ROWS"
        recommendations.append(
            "Incorporar tabla Markdown de registro RAID con prefijos canónicos (RISK-, ISS-, ACT-, DEP-) según PMI PMBOK §11.2."
        )
    elif len(unassigned_raid_ids) > 0:
        raid_table_posture = "UNASSIGNED_RAID_OWNERSHIP"
        recommendations.append(
            f"Asignar propietario responsable (@usuario o rol nominal) a los ítems RAID huérfanos: {', '.join(unassigned_raid_ids)}."
        )
    elif completeness_rate >= 80.0:
        raid_table_posture = "GOVERNED_RAID_MATRIX"
        recommendations.append(
            "Matriz RAID adecuadamente gobernada con severidad, propietario y planes de respuesta documentados."
        )
    else:
        raid_table_posture = "INCOMPLETE_MITIGATION_PLANS"
        recommendations.append(
            "Completar planes de respuesta/mitigación (>= 8 caracteres) y severidad explícita en las filas RAID incompletas."
        )

    return {
        "total_raid_rows": total_raid_rows,
        "fully_specified_count": fully_specified_count,
        "unassigned_raid_ids": unassigned_raid_ids,
        "unmitigated_raid_ids": unmitigated_raid_ids,
        "completeness_rate": completeness_rate,
        "raid_table_posture": raid_table_posture,
        "recommendations": recommendations,
    }


def audit_wiki_meeting_minutes_governance(
    markdown_text: Optional[str],
) -> dict[str, Any]:
    """Audita actas de reunión (Meeting Minutes) y seguimiento de acciones en Wiki Markdown según PMI PMBOK §10.2 y §4.3."""
    text = markdown_text if isinstance(markdown_text, str) else ""

    mention_re = re.compile(r"(?<!\w)@([a-zA-Z0-9_.-]+)")
    date_re = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
    heading_re = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
    decision_code_re = re.compile(r"\bDEC-\d+\b", re.IGNORECASE)
    action_item_re = re.compile(r"^\s*[-*+]\s+\[(?P<state>[ xX])\]\s+(?P<text>.+)$")

    agenda_keywords = (
        "agenda",
        "objetivos",
        "orden del dia",
        "orden del día",
        "temas",
    )
    decision_keywords = ("decisiones", "acuerdos", "decisions")

    attendees_set: set[str] = set()
    dates_set: set[str] = set()
    has_agenda_section = False
    has_decisions_record = False
    total_action_items = 0
    unassigned_open_actions = 0

    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for m in mention_re.finditer(line):
            cleaned_user = m.group(1).rstrip(".").lower()
            if cleaned_user:
                attendees_set.add(cleaned_user)

        for d in date_re.finditer(line):
            dates_set.add(d.group(1))

        if decision_code_re.search(line):
            has_decisions_record = True

        h_match = heading_re.match(line)
        if h_match:
            h_lower = h_match.group("title").lower()
            if any(kw in h_lower for kw in agenda_keywords):
                has_agenda_section = True
            if any(kw in h_lower for kw in decision_keywords):
                has_decisions_record = True

        act_match = action_item_re.match(line)
        if act_match:
            total_action_items += 1
            state = act_match.group("state").lower()
            item_body = act_match.group("text")
            if state != "x":
                has_mention = any(
                    bool(m.group(1).rstrip(".")) for m in mention_re.finditer(item_body)
                )
                if not has_mention:
                    unassigned_open_actions += 1

    attendees_mentions = sorted(attendees_set)
    detected_dates = sorted(dates_set)

    recommendations: list[str] = []
    if (
        len(detected_dates) == 0
        and len(attendees_mentions) == 0
        and not has_agenda_section
    ):
        minutes_posture = "NOT_A_MEETING_MINUTE"
        recommendations.append(
            "Incluir fecha ISO (YYYY-MM-DD), menciones de asistentes (@usuario) y sección de Agenda/Objetivos para estructurar un acta de reunión formal (PMBOK §10.2)."
        )
    elif unassigned_open_actions > 0:
        minutes_posture = "UNASSIGNED_ACTION_ITEMS"
        recommendations.append(
            f"Asignar responsable explícito (@usuario) a las {unassigned_open_actions} acciones abiertas (`- [ ]`) para garantizar trazabilidad de ejecución (PMBOK §4.3 / §10.2)."
        )
    elif (
        len(attendees_mentions) < 2
        or not has_agenda_section
        or not has_decisions_record
    ):
        minutes_posture = "INCOMPLETE_MINUTES_STRUCTURE"
        if len(attendees_mentions) < 2:
            recommendations.append(
                "Registrar al menos 2 participantes (@usuario) para acreditar quórum de la sesión (PMBOK §10.2)."
            )
        if not has_agenda_section:
            recommendations.append(
                "Añadir encabezado de Agenda u Orden del Día (`# Agenda` / `# Objetivos`)."
            )
        if not has_decisions_record:
            recommendations.append(
                "Documentar sección de Decisiones/Acuerdos (`# Decisiones`) o códigos `DEC-XX`."
            )
    else:
        minutes_posture = "GOVERNED_MEETING_MINUTES"
        recommendations.append(
            "Acta de reunión completa con quórum, agenda, registro de decisiones y compromisos asignados conforme a PMI PMBOK §10.2."
        )

    return {
        "attendees_mentions": attendees_mentions,
        "detected_dates": detected_dates,
        "has_agenda_section": has_agenda_section,
        "has_decisions_record": has_decisions_record,
        "total_action_items": total_action_items,
        "unassigned_open_actions": unassigned_open_actions,
        "minutes_posture": minutes_posture,
        "recommendations": recommendations,
    }


def audit_wiki_operational_runbook_readiness(
    markdown_text: Optional[str],
) -> dict:
    """Audita la preparación de un Runbook / SOP operativo en la Wiki (PMBOK §4.4 / §8.2).

    Analiza encabezados y pasos numerados ignorando bloques de código cercados
    (triple backtick) y calcula:
    - `has_prerequisites_section`: encabezado con prerrequisitos/prerequisites/
      pre-condiciones/precondiciones (sin tildes, case-insensitive).
    - `has_rollback_section`: encabezado con rollback/reversion/reversión/
      contingencia/recovery.
    - `has_verification_section`: encabezado con verificacion/verification/
      validacion/validación/smoke test.
    - `numbered_steps_count`: pasos 'N. ' fuera de bloques cercados.
    - `code_blocks_count`: cantidad de bloques cercados.
    - `readiness_score_pct`: promedio de los 4 pilares (prerrequisitos,
      >= 2 pasos numerados, rollback, verificación) en % (2 decimales;
      0.0 sin contenido).
    - `runbook_posture`: 'EMPTY_RUNBOOK_CONTENT' sin contenido;
      'MISSING_ROLLBACK_PROCEDURE' sin rollback;
      'INCOMPLETE_SOP_STRUCTURE' con rollback pero score < 100.0; y
      'PRODUCTION_READY_RUNBOOK' con score == 100.0.
    - `recommendations`: acciones por pilar faltante o feedback positivo.
    """
    text = str(markdown_text or "").strip()

    def _norm(value: str) -> str:
        stripped = unicodedata.normalize("NFKD", str(value))
        return stripped.encode("ascii", "ignore").decode("ascii").lower()

    PREREQ_TOKENS = ("prerrequisitos", "prerequisites", "pre-condiciones", "precondiciones")
    ROLLBACK_TOKENS = ("rollback", "reversion", "reversión", "contingencia", "recovery")
    VERIFICATION_TOKENS = ("verificacion", "verification", "validacion", "validación", "smoke test")

    headings_norm: list[str] = []
    numbered_steps_count = 0
    code_blocks_count = 0
    in_fenced_block = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            if not in_fenced_block:
                code_blocks_count += 1
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue
        heading_match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            headings_norm.append(_norm(heading_match.group(1)))
        if re.match(r"^\s*\d+\.\s", line):
            numbered_steps_count += 1

    def _has_section(tokens: tuple[str, ...]) -> bool:
        return any(
            any(token in heading for token in tokens)
            for heading in headings_norm
        )

    has_prerequisites_section = _has_section(PREREQ_TOKENS)
    has_rollback_section = _has_section(ROLLBACK_TOKENS)
    has_verification_section = _has_section(VERIFICATION_TOKENS)

    pillars = [
        has_prerequisites_section,
        numbered_steps_count >= 2,
        has_rollback_section,
        has_verification_section,
    ]
    readiness_score_pct = (
        round((sum(pillars) / len(pillars)) * 100.0, 2)
        if text
        else 0.0
    )

    if not text:
        runbook_posture = "EMPTY_RUNBOOK_CONTENT"
    elif not has_rollback_section:
        runbook_posture = "MISSING_ROLLBACK_PROCEDURE"
    elif readiness_score_pct < 100.0:
        runbook_posture = "INCOMPLETE_SOP_STRUCTURE"
    else:
        runbook_posture = "PRODUCTION_READY_RUNBOOK"

    recommendations: list[str] = []
    if not text:
        recommendations.append(
            "Redactar el runbook con prerrequisitos, pasos numerados, rollback y verificación."
        )
    else:
        if not has_prerequisites_section:
            recommendations.append(
                "Añadir la sección de Prerrequisitos con accesos, credenciales y ambiente destino."
            )
        if numbered_steps_count < 2:
            recommendations.append(
                "Numerar los pasos del procedimiento (mínimo 2 pasos 'N.' fuera de código)."
            )
        if not has_rollback_section:
            recommendations.append(
                "Documentar el procedimiento de rollback/contingencia antes de autorizar el SOP en producción."
            )
        if not has_verification_section:
            recommendations.append(
                "Incluir la verificación post-ejecución (verificación/validación o smoke test)."
            )
        if not recommendations:
            recommendations.append(
                "Runbook listo para producción: validar el rollback y la verificación en el último drill."
            )

    return {
        "has_prerequisites_section": has_prerequisites_section,
        "has_rollback_section": has_rollback_section,
        "has_verification_section": has_verification_section,
        "numbered_steps_count": numbered_steps_count,
        "code_blocks_count": code_blocks_count,
        "readiness_score_pct": readiness_score_pct,
        "runbook_posture": runbook_posture,
        "recommendations": recommendations,
    }


def audit_wiki_postmortem_incident_rca(
    pages: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audita la gobernanza de páginas Post-Mortem / RCA de incidentes (PMBOK §4.4 / §8.3).

    Cada página declara `id`/`page_id`/`slug` (fallbar: 'PAGE-{idx}') y
    `content`/`body`/`markdown`, normalizado sin acentos en minúsculas:
    - `has_timeline`: menciona timeline/cronología/línea de tiempo/impacto
      temporal/detección.
    - `has_root_cause`: menciona root cause/causa raiz/5 whys/factor causal.
    - `has_capa_actions`: menciona CAPA/acciones y, además, responsable
      ('@'/'owner'/'responsable').
    - `missing_*_page_ids`: encontrados por pilar ausente.
    - `complete_rca_count` / `completeness_rate_pct` (2 decimales; 0.0 sin páginas).
    - `is_compliant`: las 3 listas de faltantes vacías.
    - `rca_posture`: 'NO_POSTMORTEM_PAGES' sin páginas;
      'MISSING_ROOT_CAUSE_ANALYSIS'; 'MISSING_PREVENTIVE_CAPA_ACTIONS';
      'MISSING_INCIDENT_TIMELINE'; y 'COMPLIANT_BLAMELESS_POSTMORTEM'.
    """
    TIMELINE_TOKENS = (
        "timeline", "cronologia", "linea de tiempo", "impacto temporal", "deteccion"
    )
    ROOT_CAUSE_TOKENS = (
        "root cause", "causa raiz", "5 whys", "5 porques", "cinco porques", "factor causal"
    )
    CAPA_TOKENS = (
        "capa", "accion correctiva", "accion preventiva", "remediacion",
        "action item", "acciones",
    )

    valid_pages = [p for p in (pages or []) if isinstance(p, dict)]
    total_postmortems = len(valid_pages)

    missing_timeline_page_ids: List[str] = []
    missing_root_cause_page_ids: List[str] = []
    missing_capa_page_ids: List[str] = []
    complete_rca_count = 0

    def _norm(value: str) -> str:
        stripped = unicodedata.normalize("NFKD", str(value))
        return stripped.encode("ascii", "ignore").decode("ascii").strip().lower()

    for idx, item in enumerate(valid_pages, start=1):
        page_id = str(
            item.get("id") or item.get("page_id") or item.get("slug") or ""
        ).strip() or f"PAGE-{idx}"
        content = str(
            item.get("content") or item.get("body") or item.get("markdown") or ""
        ).strip()
        norm = _norm(content)

        has_timeline = any(token in norm for token in TIMELINE_TOKENS)
        has_root_cause = any(token in norm for token in ROOT_CAUSE_TOKENS)
        has_capa_actions = (
            any(token in norm for token in CAPA_TOKENS)
            and ("@" in norm or "responsable" in norm or "owner" in norm)
        )

        if not has_timeline:
            missing_timeline_page_ids.append(page_id)
        if not has_root_cause:
            missing_root_cause_page_ids.append(page_id)
        if not has_capa_actions:
            missing_capa_page_ids.append(page_id)
        if has_timeline and has_root_cause and has_capa_actions:
            complete_rca_count += 1

    completeness_rate_pct = (
        round((complete_rca_count / total_postmortems) * 100.0, 2)
        if total_postmortems > 0
        else 0.0
    )
    is_compliant = bool(
        not missing_timeline_page_ids
        and not missing_root_cause_page_ids
        and not missing_capa_page_ids
    )

    if total_postmortems == 0:
        rca_posture = "NO_POSTMORTEM_PAGES"
    elif missing_root_cause_page_ids:
        rca_posture = "MISSING_ROOT_CAUSE_ANALYSIS"
    elif missing_capa_page_ids:
        rca_posture = "MISSING_PREVENTIVE_CAPA_ACTIONS"
    elif missing_timeline_page_ids:
        rca_posture = "MISSING_INCIDENT_TIMELINE"
    else:
        rca_posture = "COMPLIANT_BLAMELESS_POSTMORTEM"

    return {
        "total_postmortems": total_postmortems,
        "complete_rca_count": complete_rca_count,
        "completeness_rate_pct": completeness_rate_pct,
        "missing_timeline_page_ids": missing_timeline_page_ids,
        "missing_root_cause_page_ids": missing_root_cause_page_ids,
        "missing_capa_page_ids": missing_capa_page_ids,
        "is_compliant": is_compliant,
        "rca_posture": rca_posture,
    }


def audit_wiki_lessons_learned_taxonomy(
    entries: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audita el registro de lecciones aprendidas y su taxonomía accionable (PMBOK §4.4).

    Cada entrada declara `id`/`entry_id`/`lesson_id` (fallback 'LL-{idx}'),
    categoría/dominio (`category`/`domain`/`knowledge_area`, normalizada sin
    acentos), contexto (`situation`/`context`/`description`, >= 10 chars) y
    recomendación (`recommendation`/`actionable_advice`/`leccion`, >= 10 chars):
    - `actionable_entries_count` / `actionable_rate_pct` (2 decimales; 0.0 sin entradas).
    - `uncategorized_entry_ids` / `shallow_context_entry_ids` /
      `missing_recommendation_entry_ids`: entradas deficientes por pilar.
    - `is_compliant`: las 3 listas de faltantes vacías.
    - `lessons_posture`: 'NO_LESSONS_RECORDED' sin entradas;
      'MISSING_ACTIONABLE_RECOMMENDATIONS'; 'UNCATEGORIZED_KNOWLEDGE_ENTRIES';
      'SHALLOW_LESSON_CONTEXT'; 'INSTITUTIONALIZED_LESSONS_LEARNED'.
    """
    INVALID_CATEGORY_TOKENS = {"tbd", "n/a", "na", "unknown", "none", "sin categoria"}
    valid_entries = [e for e in (entries or []) if isinstance(e, dict)]
    total_entries = len(valid_entries)
    if total_entries == 0:
        return {
            "total_entries": 0,
            "actionable_entries_count": 0,
            "actionable_rate_pct": 0.0,
            "uncategorized_entry_ids": [],
            "shallow_context_entry_ids": [],
            "missing_recommendation_entry_ids": [],
            "is_compliant": True,
            "lessons_posture": "NO_LESSONS_RECORDED",
        }

    uncategorized_entry_ids: List[str] = []
    shallow_context_entry_ids: List[str] = []
    missing_recommendation_entry_ids: List[str] = []
    actionable_entries_count = 0

    for idx, item in enumerate(valid_entries, start=1):
        entry_id = str(
            item.get("id") or item.get("entry_id") or item.get("lesson_id") or ""
        ).strip() or f"LL-{idx}"
        cat = str(
            item.get("category") or item.get("domain") or item.get("knowledge_area") or ""
        ).strip()
        cat_norm = unicodedata.normalize("NFKD", cat).encode("ascii", "ignore").decode("ascii").lower()
        has_cat = bool(cat_norm and cat_norm not in INVALID_CATEGORY_TOKENS)
        ctx = str(
            item.get("situation") or item.get("context") or item.get("description") or ""
        ).strip()
        has_ctx = len(ctx) >= 10
        rec = str(
            item.get("recommendation") or item.get("actionable_advice") or item.get("leccion") or ""
        ).strip()
        has_rec = len(rec) >= 10

        if not has_cat:
            uncategorized_entry_ids.append(entry_id)
        if not has_ctx:
            shallow_context_entry_ids.append(entry_id)
        if not has_rec:
            missing_recommendation_entry_ids.append(entry_id)
        if has_cat and has_ctx and has_rec:
            actionable_entries_count += 1

    actionable_rate_pct = round((actionable_entries_count / total_entries) * 100.0, 2)
    is_compliant = bool(
        not uncategorized_entry_ids
        and not shallow_context_entry_ids
        and not missing_recommendation_entry_ids
    )

    if missing_recommendation_entry_ids:
        lessons_posture = "MISSING_ACTIONABLE_RECOMMENDATIONS"
    elif uncategorized_entry_ids:
        lessons_posture = "UNCATEGORIZED_KNOWLEDGE_ENTRIES"
    elif shallow_context_entry_ids:
        lessons_posture = "SHALLOW_LESSON_CONTEXT"
    else:
        lessons_posture = "INSTITUTIONALIZED_LESSONS_LEARNED"

    return {
        "total_entries": total_entries,
        "actionable_entries_count": actionable_entries_count,
        "actionable_rate_pct": actionable_rate_pct,
        "uncategorized_entry_ids": uncategorized_entry_ids,
        "shallow_context_entry_ids": shallow_context_entry_ids,
        "missing_recommendation_entry_ids": missing_recommendation_entry_ids,
        "is_compliant": is_compliant,
        "lessons_posture": lessons_posture,
    }


_VALID_ADR_STATUSES = frozenset(
    {
        "proposed",
        "accepted",
        "deprecated",
        "superseded",
        "propuesto",
        "aceptado",
        "deprecado",
        "reemplazado",
    }
)
_SUPERSEDED_ADR_STATUSES = frozenset({"superseded", "reemplazado"})
_ACCEPTED_ADR_STATUSES = frozenset({"accepted", "aceptado"})


def audit_wiki_adr_lifecycle_traceability(
    adrs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audita el ciclo de vida y trazabilidad de reemplazo de Registros de Decisiones de Arquitectura (ADR) (PMI §4.4 / §10.2)."""
    valid_adrs = [item for item in (adrs or []) if isinstance(item, dict)]
    total_adrs = len(valid_adrs)
    if total_adrs == 0:
        return {
            "total_adrs": 0,
            "accepted_adrs_count": 0,
            "invalid_status_adr_ids": [],
            "broken_supersession_adr_ids": [],
            "incomplete_accepted_adr_ids": [],
            "is_traceable": True,
            "adr_posture": "NO_ADRS_REGISTERED",
        }

    known_adr_ids: set[str] = set()
    resolved_adrs: List[tuple[str, Dict[str, Any]]] = []
    for idx, item in enumerate(valid_adrs, start=1):
        adr_id = (
            str(item.get("id") or item.get("adr_id") or item.get("code") or "").strip()
            or f"ADR-{idx}"
        )
        known_adr_ids.add(adr_id)
        resolved_adrs.append((adr_id, item))

    accepted_adrs_count = 0
    invalid_status_adr_ids: List[str] = []
    broken_supersession_adr_ids: List[str] = []
    incomplete_accepted_adr_ids: List[str] = []

    for adr_id, item in resolved_adrs:
        raw_status = str(item.get("status") or "").strip().lower()
        if raw_status not in _VALID_ADR_STATUSES:
            invalid_status_adr_ids.append(adr_id)

        if raw_status in _SUPERSEDED_ADR_STATUSES:
            target_id = str(
                item.get("superseded_by") or item.get("replaced_by") or ""
            ).strip()
            if (
                not target_id
                or target_id == adr_id
                or target_id not in known_adr_ids
            ):
                broken_supersession_adr_ids.append(adr_id)

        if raw_status in _ACCEPTED_ADR_STATUSES:
            accepted_adrs_count += 1
            has_ctx = bool(
                str(item.get("context") or item.get("problem") or "").strip()
            )
            has_conseq = bool(
                str(item.get("consequences") or item.get("impact") or "").strip()
            )
            if not (has_ctx and has_conseq):
                incomplete_accepted_adr_ids.append(adr_id)

    is_traceable = bool(
        len(invalid_status_adr_ids) == 0
        and len(broken_supersession_adr_ids) == 0
        and len(incomplete_accepted_adr_ids) == 0
    )

    if len(invalid_status_adr_ids) > 0:
        adr_posture = "INVALID_ADR_LIFECYCLE_STATUS"
    elif len(broken_supersession_adr_ids) > 0:
        adr_posture = "BROKEN_ADR_SUPERSESSION_CHAIN"
    elif len(incomplete_accepted_adr_ids) > 0:
        adr_posture = "INCOMPLETE_ACCEPTED_ADR_RATIONALE"
    else:
        adr_posture = "TRACEABLE_ADR_ARCHITECTURE_LOG"

    return {
        "total_adrs": total_adrs,
        "accepted_adrs_count": accepted_adrs_count,
        "invalid_status_adr_ids": invalid_status_adr_ids,
        "broken_supersession_adr_ids": broken_supersession_adr_ids,
        "incomplete_accepted_adr_ids": incomplete_accepted_adr_ids,
        "is_traceable": is_traceable,
        "adr_posture": adr_posture,
    }


def audit_wiki_communication_matrix_governance(
    channels: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audita la Matriz de Comunicaciones y el SLA de escalamiento (PMBOK §10.1.3.1).

    Cada canal declara `id`/`channel_id`/`name` (fallback 'CH-{idx}'),
    audiencia (`audience`/`stakeholders`/`recipients`), cadencia
    (`frequency`/`cadence`/`frecuencia`), responsable (`owner`/`sender`/
    `responsable`), tipo (`channel_type`/`purpose`) y, para canales de
    esalamiento/incidente, `escalation_sla_hours`/`sla_hours`:
    - `missing_audience_channel_ids` / `missing_cadence_channel_ids` /
      `unowned_channel_ids` / `missing_escalation_sla_channel_ids`.
    - `is_compliant`: las 4 listas de faltantes vacías.
    - `matrix_posture`: 'NO_COMMUNICATION_CHANNELS' sin canales;
      'MISSING_ESCALATION_SLA_PATH'; 'UNOWNED_COMMUNICATION_CHANNELS';
      'INCOMPLETE_AUDIENCE_OR_CADENCE'; 'COMPLIANT_COMMUNICATIONS_MATRIX'.
    """
    ESCALATION_TYPES = {"escalation", "incident", "crisis", "escalamiento", "incidente"}
    valid_channels = [c for c in (channels or []) if isinstance(c, dict)]
    total_channels = len(valid_channels)
    if total_channels == 0:
        return {
            "total_channels": 0,
            "complete_channels_count": 0,
            "missing_audience_channel_ids": [],
            "missing_cadence_channel_ids": [],
            "unowned_channel_ids": [],
            "missing_escalation_sla_channel_ids": [],
            "is_compliant": True,
            "matrix_posture": "NO_COMMUNICATION_CHANNELS",
        }

    missing_audience_channel_ids: List[str] = []
    missing_cadence_channel_ids: List[str] = []
    unowned_channel_ids: List[str] = []
    missing_escalation_sla_channel_ids: List[str] = []
    complete_channels_count = 0

    for idx, item in enumerate(valid_channels, start=1):
        ch_id = str(item.get("id") or item.get("channel_id") or item.get("name") or "").strip() or f"CH-{idx}"
        aud = str(item.get("audience") or item.get("stakeholders") or item.get("recipients") or "").strip()
        cad = str(item.get("frequency") or item.get("cadence") or item.get("frecuencia") or "").strip()
        own = str(item.get("owner") or item.get("sender") or item.get("responsable") or "").strip()
        ctype = str(item.get("channel_type") or item.get("purpose") or "").strip().lower()
        is_esc = bool(
            item.get("is_escalation") is True or ctype in ESCALATION_TYPES
        )
        try:
            sla = float(
                item.get("escalation_sla_hours")
                if item.get("escalation_sla_hours") is not None
                else (item.get("sla_hours") or 0.0)
            )
        except (TypeError, ValueError):
            sla = 0.0

        if not aud:
            missing_audience_channel_ids.append(ch_id)
        if not cad:
            missing_cadence_channel_ids.append(ch_id)
        if not own:
            unowned_channel_ids.append(ch_id)
        if is_esc and sla <= 0.0:
            missing_escalation_sla_channel_ids.append(ch_id)
        if aud and cad and own and (not is_esc or sla > 0.0):
            complete_channels_count += 1

    is_compliant = bool(
        not missing_audience_channel_ids
        and not missing_cadence_channel_ids
        and not unowned_channel_ids
        and not missing_escalation_sla_channel_ids
    )

    if len(missing_escalation_sla_channel_ids) > 0:
        matrix_posture = "MISSING_ESCALATION_SLA_PATH"
    elif len(unowned_channel_ids) > 0:
        matrix_posture = "UNOWNED_COMMUNICATION_CHANNELS"
    elif len(missing_audience_channel_ids) > 0 or len(missing_cadence_channel_ids) > 0:
        matrix_posture = "INCOMPLETE_AUDIENCE_OR_CADENCE"
    else:
        matrix_posture = "COMPLIANT_COMMUNICATIONS_MATRIX"

    return {
        "total_channels": total_channels,
        "complete_channels_count": complete_channels_count,
        "missing_audience_channel_ids": missing_audience_channel_ids,
        "missing_cadence_channel_ids": missing_cadence_channel_ids,
        "unowned_channel_ids": unowned_channel_ids,
        "missing_escalation_sla_channel_ids": missing_escalation_sla_channel_ids,
        "is_compliant": is_compliant,
        "matrix_posture": matrix_posture,
    }


class WikiPMIService:
    """Fachada canónica de doctrina y gobernanza documental Wiki PMI."""

    @staticmethod
    def load_volume_markdown_content(
        file_name: str, base_dir: Optional[Path] = None
    ) -> str:
        return load_volume_markdown_content(file_name, base_dir=base_dir)

    @staticmethod
    def get_canonical_pmi_volumes(
        base_dir: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        return get_canonical_pmi_volumes(base_dir=base_dir)

    @staticmethod
    def seed_pmi_wiki_doctrine(
        db: Session,
        sede_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
        force_update: bool = False,
        base_dir: Optional[Path] = None,
    ) -> List[models.WikiPage]:
        return seed_pmi_wiki_doctrine(
            db,
            sede_id=sede_id,
            author_id=author_id,
            force_update=force_update,
            base_dir=base_dir,
        )

    @staticmethod
    def audit_pmi_wiki_doctrine_completeness(
        base_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        return audit_pmi_wiki_doctrine_completeness(base_dir=base_dir)

    @staticmethod
    def search_canonical_pmi_volumes(
        query: Optional[str] = None,
        tag_filter: Optional[str] = None,
        base_dir: Optional[Path] = None,
    ) -> List[Dict[str, Any]]:
        return search_canonical_pmi_volumes(
            query=query, tag_filter=tag_filter, base_dir=base_dir
        )

    @staticmethod
    def extract_wiki_slash_commands_inventory(
        markdown_text: Optional[str],
    ) -> Dict[str, Any]:
        return extract_wiki_slash_commands_inventory(markdown_text)

    @staticmethod
    def audit_wiki_page_knowledge_hygiene(
        title: Optional[str],
        content: Optional[str],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_page_knowledge_hygiene(title, content, tags=tags)

    @staticmethod
    def summarize_wiki_revision_history_velocity(
        revisions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return summarize_wiki_revision_history_velocity(revisions)

    @staticmethod
    def audit_wiki_crosslink_reference_integrity(
        content: str | None,
        known_slugs: list[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        return audit_wiki_crosslink_reference_integrity(content, known_slugs)

    @staticmethod
    def audit_wiki_stakeholder_signoffs(
        signoffs: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return audit_wiki_stakeholder_signoffs(signoffs)

    @staticmethod
    def audit_wiki_template_section_compliance(
        content: str | None,
        required_sections: list[str] | None = None,
    ) -> dict[str, Any]:
        return audit_wiki_template_section_compliance(content, required_sections)

    @staticmethod
    def audit_wiki_decision_log_entries(
        decisions: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return audit_wiki_decision_log_entries(decisions)

    @staticmethod
    def audit_wiki_raid_register_tables(
        markdown_text: Optional[str],
    ) -> dict[str, Any]:
        return audit_wiki_raid_register_tables(markdown_text)

    @staticmethod
    def audit_wiki_meeting_minutes_governance(
        markdown_text: Optional[str],
    ) -> dict[str, Any]:
        return audit_wiki_meeting_minutes_governance(markdown_text)

    @staticmethod
    def audit_wiki_postmortem_incident_rca(
        pages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_postmortem_incident_rca(pages)

    @staticmethod
    def audit_wiki_lessons_learned_taxonomy(
        entries: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_lessons_learned_taxonomy(entries)

    @staticmethod
    def audit_wiki_communication_matrix_governance(
        channels: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_communication_matrix_governance(channels)

    @staticmethod
    def audit_wiki_operational_runbook_readiness(
        markdown_text: Optional[str],
    ) -> dict:
        return audit_wiki_operational_runbook_readiness(markdown_text)

    @staticmethod
    def audit_wiki_adr_lifecycle_traceability(
        adrs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_adr_lifecycle_traceability(adrs)


__all__ = [
    "DEFAULT_PMI_KB_DIR",
    "CANONICAL_VOLUMES_METADATA",
    "SUPPORTED_PMI_SLASH_COMMANDS",
    "SLASH_COMMAND_RE",
    "load_volume_markdown_content",
    "get_canonical_pmi_volumes",
    "seed_pmi_wiki_doctrine",
    "audit_pmi_wiki_doctrine_completeness",
    "search_canonical_pmi_volumes",
    "extract_wiki_slash_commands_inventory",
    "audit_wiki_page_knowledge_hygiene",
    "summarize_wiki_revision_history_velocity",
    "audit_wiki_crosslink_reference_integrity",
    "audit_wiki_stakeholder_signoffs",
    "audit_wiki_template_section_compliance",
    "audit_wiki_decision_log_entries",
    "audit_wiki_raid_register_tables",
    "audit_wiki_meeting_minutes_governance",
    "audit_wiki_postmortem_incident_rca",
    "audit_wiki_lessons_learned_taxonomy",
    "audit_wiki_communication_matrix_governance",
    "audit_wiki_operational_runbook_readiness",
    "audit_wiki_adr_lifecycle_traceability",
    "WikiPMIService",
]

