"""Servicio de doctrina PMI y gestión de páginas canónicas en la Wiki Ministerial.

Carga e indexa los 7 volúmenes canónicos de la biblioteca metodológica PMI
en la tabla `wiki_pages` para consulta universal por los equipos de proyectos.
"""

from __future__ import annotations

import logging
import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
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


def _audit_wiki_meeting_minutes_markdown(
    markdown_text: Optional[str],
) -> dict[str, Any]:
    """Audita el contenido Markdown individual de un acta de reunión (Meeting Minutes) según PMI PMBOK §10.2 y §4.3."""
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


def audit_wiki_meeting_minutes_governance(
    meetings: list[dict[str, Any]] | str | None = None,
    min_attendance_rate_pct: float = 75.0,
) -> dict[str, Any]:
    """Audita la gobernanza de actas de reunión (Meeting Minutes), quórum, decisiones y compromisos según PMI PMBOK §10.2 y §4.4."""
    if isinstance(meetings, str):
        return _audit_wiki_meeting_minutes_markdown(meetings)

    total_meetings = 0
    low_quorum_meeting_ids: list[str] = []
    undocumented_outcome_meeting_ids: list[str] = []
    unassigned_action_item_meeting_ids: list[str] = []

    for item in meetings or []:
        if not isinstance(item, dict):
            continue
        meeting_id = str(item.get("id") or item.get("meeting_id") or "").strip()
        if not meeting_id:
            continue

        invited = max(0, int(item.get("invited_count") or 0))
        attended = max(0, int(item.get("attended_count") or 0))
        summary = str(item.get("summary") or "").strip()
        decisions = item.get("decisions") if isinstance(item.get("decisions"), list) else []
        action_items = (
            item.get("action_items") if isinstance(item.get("action_items"), list) else []
        )

        total_meetings += 1
        att_rate = (attended / invited) * 100.0 if invited > 0 else 0.0

        if invited <= 0 or att_rate + 1e-6 < float(min_attendance_rate_pct):
            low_quorum_meeting_ids.append(meeting_id)

        if not summary and len(decisions) == 0:
            undocumented_outcome_meeting_ids.append(meeting_id)

        has_unassigned_ai = any(
            isinstance(ai, dict)
            and (
                not str(ai.get("owner_id") or "").strip()
                or not str(ai.get("due_date") or "").strip()
            )
            for ai in action_items
        )
        if has_unassigned_ai:
            unassigned_action_item_meeting_ids.append(meeting_id)

    is_meeting_governance_valid = bool(
        total_meetings > 0
        and len(low_quorum_meeting_ids) == 0
        and len(undocumented_outcome_meeting_ids) == 0
        and len(unassigned_action_item_meeting_ids) == 0
    )

    if total_meetings == 0:
        meeting_posture = "NO_MEETING_MINUTES"
    elif len(unassigned_action_item_meeting_ids) > 0:
        meeting_posture = "UNASSIGNED_MEETING_ACTION_ITEMS"
    elif len(undocumented_outcome_meeting_ids) > 0:
        meeting_posture = "UNDOCUMENTED_MEETING_OUTCOMES"
    elif len(low_quorum_meeting_ids) > 0:
        meeting_posture = "INSUFFICIENT_MEETING_QUORUM"
    else:
        meeting_posture = "GOVERNED_MEETING_MINUTES"

    return {
        "total_meetings": total_meetings,
        "low_quorum_meeting_ids": low_quorum_meeting_ids,
        "undocumented_outcome_meeting_ids": undocumented_outcome_meeting_ids,
        "unassigned_action_item_meeting_ids": unassigned_action_item_meeting_ids,
        "is_meeting_governance_valid": is_meeting_governance_valid,
        "meeting_posture": meeting_posture,
    }


def _audit_wiki_operational_runbook_markdown(
    markdown_text: Optional[str],
) -> dict[str, Any]:
    """Audita el contenido Markdown de un Runbook / SOP individual."""
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


def audit_wiki_operational_runbook_readiness(
    runbooks: list[dict[str, Any]] | str | None = None,
    max_drill_age_days: int = 90,
) -> dict[str, Any]:
    """Audita la preparación de Runbooks operativos y SOPs en la Wiki (PMBOK §4.4 / §8.2 / §4.7).

    Para cada registro (dict) en `runbooks or []`:
    - `runbook_id`: `str(item.get("id") or item.get("runbook_id") or "").strip()` (ignorar si vacío).
    - `rollback_procedure`: `str(item.get("rollback_procedure") or "").strip()`
    - `verification_steps`: `str(item.get("verification_steps") or "").strip()`
    - `oncall_contact`: `str(item.get("oncall_contact") or "").strip()`
    - `days_since_last_drill`: `int(item.get("days_since_last_drill") if item.get("days_since_last_drill") is not None else -1)`
    """
    if isinstance(runbooks, str):
        return _audit_wiki_operational_runbook_markdown(runbooks)

    total_runbooks = 0
    missing_rollback_or_verification_ids: list[str] = []
    missing_oncall_contact_ids: list[str] = []
    stale_drill_runbook_ids: list[str] = []
    max_age = max(1, int(max_drill_age_days))

    for item in runbooks or []:
        if not isinstance(item, dict):
            continue
        runbook_id = str(item.get("id") or item.get("runbook_id") or "").strip()
        if not runbook_id:
            continue

        total_runbooks += 1
        rollback_procedure = str(item.get("rollback_procedure") or "").strip()
        verification_steps = str(item.get("verification_steps") or "").strip()
        oncall_contact = str(item.get("oncall_contact") or "").strip()
        raw_drill_days = item.get("days_since_last_drill")
        try:
            days_since_last_drill = (
                int(raw_drill_days) if raw_drill_days is not None else -1
            )
        except (TypeError, ValueError):
            days_since_last_drill = -1

        if not rollback_procedure or not verification_steps:
            missing_rollback_or_verification_ids.append(runbook_id)
        if not oncall_contact:
            missing_oncall_contact_ids.append(runbook_id)
        if days_since_last_drill < 0 or days_since_last_drill > max_age:
            stale_drill_runbook_ids.append(runbook_id)

    is_runbook_suite_ready = bool(
        total_runbooks > 0
        and len(missing_rollback_or_verification_ids) == 0
        and len(missing_oncall_contact_ids) == 0
        and len(stale_drill_runbook_ids) == 0
    )

    if total_runbooks == 0:
        runbook_posture = "NO_OPERATIONAL_RUNBOOKS"
    elif len(missing_rollback_or_verification_ids) > 0:
        runbook_posture = "MISSING_ROLLBACK_OR_VERIFICATION_STEPS"
    elif len(missing_oncall_contact_ids) > 0:
        runbook_posture = "MISSING_ONCALL_ESCALATION_CONTACT"
    elif len(stale_drill_runbook_ids) > 0:
        runbook_posture = "STALE_RUNBOOK_DRILL_VALIDATION"
    else:
        runbook_posture = "OPERATIONS_READY_RUNBOOK_SUITE"

    return {
        "total_runbooks": total_runbooks,
        "missing_rollback_or_verification_ids": missing_rollback_or_verification_ids,
        "missing_oncall_contact_ids": missing_oncall_contact_ids,
        "stale_drill_runbook_ids": stale_drill_runbook_ids,
        "is_runbook_suite_ready": is_runbook_suite_ready,
        "runbook_posture": runbook_posture,
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


def audit_wiki_project_glossary_governance(
    glossary_entries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita el glosario de proyecto, sigas ambiguas y dominio (PMBOK §4.4 y §10.1).

    Cada entrada declara `term`/`acronym`/`name` (fallback 'TERM-{idx}'),
    definición (`definition`/`description`/`meaning`, >= 10 chars) y dominio
    (`domain`/`category`/`knowledge_area`):
    - `duplicate_terms`: términos repetidos (clave case-insensitive).
    - `incomplete_definition_terms`: definición < 10 chars.
    - `circular_definition_terms`: definición que solo repite el término o
      arranca con '<term> is/es <term>'.
    - `uncategorized_terms`: sin dominio.
    - `is_glossary_compliant`: las 4 listas vacías.
    - `glossary_posture`: 'EMPTY_PROJECT_GLOSSARY' sin entradas;
      'DUPLICATE_AMBIGUOUS_ACRONYM'; 'INCOMPLETE_OR_CIRCULAR_DEFINITION';
      'UNCATEGORIZED_DOMAIN_TERMS'; 'GOVERNED_PROJECT_GLOSSARY'.
    """
    records = [g for g in (glossary_entries or []) if isinstance(g, dict)]
    if not records:
        return {
            "total_entries": 0,
            "duplicate_terms": [],
            "incomplete_definition_terms": [],
            "circular_definition_terms": [],
            "uncategorized_terms": [],
            "is_glossary_compliant": True,
            "glossary_posture": "EMPTY_PROJECT_GLOSSARY",
        }

    total_entries = len(records)
    duplicate_terms: list[str] = []
    incomplete_definition_terms: list[str] = []
    circular_definition_terms: list[str] = []
    uncategorized_terms: list[str] = []
    seen_term_keys: set[str] = set()

    def _strip_punct(value: str) -> str:
        return value.strip(" .:")

    for idx, item in enumerate(records, start=1):
        term = str(item.get("term") or item.get("acronym") or item.get("name") or f"TERM-{idx}").strip()
        term_key = term.lower()
        definition = str(item.get("definition") or item.get("description") or item.get("meaning") or "").strip()
        domain = str(item.get("domain") or item.get("category") or item.get("knowledge_area") or "").strip()

        if term_key in seen_term_keys and term not in duplicate_terms:
            duplicate_terms.append(term)
        seen_term_keys.add(term_key)

        if len(definition) < 10:
            incomplete_definition_terms.append(term)
        normalized_definition = _strip_punct(definition.lower())
        if len(definition) >= 10 and (
            normalized_definition == term_key
            or definition.lower().startswith(f"{term_key} is {term_key}")
            or definition.lower().startswith(f"{term_key} es {term_key}")
        ):
            circular_definition_terms.append(term)
        if not domain:
            uncategorized_terms.append(term)

    is_glossary_compliant = bool(
        len(duplicate_terms) == 0
        and len(incomplete_definition_terms) == 0
        and len(circular_definition_terms) == 0
        and len(uncategorized_terms) == 0
    )

    if total_entries == 0:
        glossary_posture = "EMPTY_PROJECT_GLOSSARY"
    elif duplicate_terms:
        glossary_posture = "DUPLICATE_AMBIGUOUS_ACRONYM"
    elif incomplete_definition_terms or circular_definition_terms:
        glossary_posture = "INCOMPLETE_OR_CIRCULAR_DEFINITION"
    elif uncategorized_terms:
        glossary_posture = "UNCATEGORIZED_DOMAIN_TERMS"
    else:
        glossary_posture = "GOVERNED_PROJECT_GLOSSARY"

    return {
        "total_entries": total_entries,
        "duplicate_terms": duplicate_terms,
        "incomplete_definition_terms": incomplete_definition_terms,
        "circular_definition_terms": circular_definition_terms,
        "uncategorized_terms": uncategorized_terms,
        "is_glossary_compliant": is_glossary_compliant,
        "glossary_posture": glossary_posture,
    }


def audit_wiki_knowledge_bus_factor_and_freshness_v1(
    articles: list[dict[str, Any]] | None = None,
    max_stale_days: int = 90,
) -> dict[str, Any]:
    """Audita retención de conocimiento, bus-factor y frescura de revisiones (PMBOK §4.4).

    Contrato v1 conservado para compatibilidad; la variante canónica vigente
    es ``audit_wiki_knowledge_bus_factor_and_freshness`` (dominio por
    ``domain_criticality`` y separación de single-author / unreviewed).

    Cada artículo declara `id`/`article_id`/`slug` (fallback 'ART-{idx}'),
    contribuidores (`contributors`/`authors`/`editors`, lista/tuple/set o
    string con comas; alternativa `author`/`created_by` individual), flag de
    tema crítico (`is_critical`/`critical_knowledge`/`core_architecture`),
    antigüedad de revisión (`days_since_review`/`age_days`/`stale_days`) y
    peer review (`peer_reviewed`/`reviewed_by`/`sme_approved`):
    - `orphaned_article_ids`: sin contribuidores únicos no vacíos.
    - `bus_factor_risk_article_ids`: tema crítico con un único autor y sin peer review.
    - `stale_article_ids`: review > max_stale_days.
    - `is_knowledge_resilient`: las 3 listas vacías.
    - `knowledge_resilience_posture`: 'NO_ARTICLES_EVALUATED' sin artículos;
      'ORPHANED_KNOWLEDGE_ASSET'; 'CRITICAL_BUS_FACTOR_EXPOSURE';
      'STALE_KNOWLEDGE_REVIEW_OVERDUE'; 'RESILIENT_KNOWLEDGE_REPOSITORY'.
    """
    records = [a for a in (articles or []) if isinstance(a, dict)]
    if not records:
        return {
            "total_articles": 0,
            "bus_factor_risk_article_ids": [],
            "stale_article_ids": [],
            "orphaned_article_ids": [],
            "is_knowledge_resilient": True,
            "knowledge_resilience_posture": "NO_ARTICLES_EVALUATED",
        }

    total_articles = len(records)
    bus_factor_risk_article_ids: list[str] = []
    stale_article_ids: list[str] = []
    orphaned_article_ids: list[str] = []

    for idx, item in enumerate(records, start=1):
        art_id = str(item.get("id") or item.get("article_id") or item.get("slug") or f"ART-{idx}").strip()

        raw_contributors = (
            item.get("contributors")
            if item.get("contributors") is not None
            else (item.get("authors") if item.get("authors") is not None else item.get("editors"))
        )
        contributors: list[str]
        if isinstance(raw_contributors, (list, tuple, set)):
            contributors = [str(c).strip() for c in raw_contributors if str(c).strip()]
        elif isinstance(raw_contributors, str) and raw_contributors.strip():
            contributors = [part.strip() for part in raw_contributors.split(",") if part.strip()]
        else:
            single_author = str(item.get("author") or item.get("created_by") or "").strip()
            contributors = [single_author] if single_author else []
        contributors_count = len(set(contributors))

        is_critical_topic = bool(
            item.get("is_critical") or item.get("critical_knowledge") or item.get("core_architecture")
        )
        try:
            days_since_review = float(
                item.get("days_since_review")
                if item.get("days_since_review") is not None
                else (item.get("age_days") if item.get("age_days") is not None else (item.get("stale_days") or 0.0))
            )
        except (TypeError, ValueError):
            days_since_review = 0.0
        peer_reviewed = bool(
            item.get("peer_reviewed") or item.get("reviewed_by") or item.get("sme_approved")
        )

        if contributors_count == 0:
            orphaned_article_ids.append(art_id)
        if is_critical_topic and contributors_count == 1 and not peer_reviewed:
            bus_factor_risk_article_ids.append(art_id)
        if days_since_review > float(max_stale_days) + 1e-9:
            stale_article_ids.append(art_id)

    is_knowledge_resilient = bool(
        len(bus_factor_risk_article_ids) == 0
        and len(stale_article_ids) == 0
        and len(orphaned_article_ids) == 0
    )

    if total_articles == 0:
        knowledge_resilience_posture = "NO_ARTICLES_EVALUATED"
    elif orphaned_article_ids:
        knowledge_resilience_posture = "ORPHANED_KNOWLEDGE_ASSET"
    elif bus_factor_risk_article_ids:
        knowledge_resilience_posture = "CRITICAL_BUS_FACTOR_EXPOSURE"
    elif stale_article_ids:
        knowledge_resilience_posture = "STALE_KNOWLEDGE_REVIEW_OVERDUE"
    else:
        knowledge_resilience_posture = "RESILIENT_KNOWLEDGE_REPOSITORY"

    return {
        "total_articles": total_articles,
        "bus_factor_risk_article_ids": bus_factor_risk_article_ids,
        "stale_article_ids": stale_article_ids,
        "orphaned_article_ids": orphaned_article_ids,
        "is_knowledge_resilient": is_knowledge_resilient,
        "knowledge_resilience_posture": knowledge_resilience_posture,
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
        meetings: list[dict[str, Any]] | str | None = None,
        min_attendance_rate_pct: float = 75.0,
    ) -> dict[str, Any]:
        return audit_wiki_meeting_minutes_governance(
            meetings, min_attendance_rate_pct=min_attendance_rate_pct
        )

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
    def audit_wiki_project_glossary_governance(
        glossary_entries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return audit_wiki_project_glossary_governance(glossary_entries)

    @staticmethod
    def audit_wiki_knowledge_bus_factor_and_freshness(
        article_records: Sequence[Mapping[str, Any]] | None = None,
        *,
        max_stale_days: int = 90,
    ) -> dict[str, Any]:
        return audit_wiki_knowledge_bus_factor_and_freshness(
            article_records, max_stale_days=max_stale_days
        )

    @staticmethod
    def audit_wiki_operational_runbook_readiness(
        runbooks: list[dict[str, Any]] | str | None = None,
        max_drill_age_days: int = 90,
    ) -> dict[str, Any]:
        return audit_wiki_operational_runbook_readiness(
            runbooks, max_drill_age_days=max_drill_age_days
        )

    @staticmethod
    def audit_wiki_adr_lifecycle_traceability(
        adrs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return audit_wiki_adr_lifecycle_traceability(adrs)

    @staticmethod
    def audit_wiki_raci_matrix_governance(
        deliverable_assignments: Sequence[Mapping[str, Any]] | None = None,
        *,
        max_consulted_per_deliverable: int = 5,
    ) -> dict[str, Any]:
        return audit_wiki_raci_matrix_governance(
            deliverable_assignments,
            max_consulted_per_deliverable=max_consulted_per_deliverable,
        )

    @staticmethod
    def audit_wiki_raci_matrix_governance_v1(
        raci_rows: list[dict[str, Any]] | None = None,
        max_consulted_per_row: int = 5,
    ) -> dict[str, Any]:
        return audit_wiki_raci_matrix_governance_v1(
            raci_rows, max_consulted_per_row=max_consulted_per_row
        )


def audit_wiki_raci_matrix_governance_v1(
    raci_rows: list[dict[str, Any]] | None = None,
    max_consulted_per_row: int = 5,
) -> dict[str, Any]:
    """Audita la Matriz RACI de la Wiki verificando responsabilidad única (Single Accountable) y claridad de roles según PMI PMBOK §9.1.2.2 (contrato v1)."""
    valid_rows = [item for item in (raci_rows or []) if isinstance(item, dict)]
    total_rows = len(valid_rows)
    if total_rows == 0:
        return {
            "total_rows": 0,
            "valid_rows_count": 0,
            "missing_accountable_row_ids": [],
            "multiple_accountable_row_ids": [],
            "missing_responsible_row_ids": [],
            "over_consulted_row_ids": [],
            "is_raci_compliant": True,
            "raci_posture": "NO_RACI_ROWS_EVALUATED",
        }

    def _normalize_role_list(
        item: dict[str, Any], keys: tuple[str, ...]
    ) -> list[str]:
        val: Any = None
        for k in keys:
            if item.get(k) is not None:
                val = item.get(k)
                break
        if val is None or isinstance(val, bool):
            return []
        if isinstance(val, (list, tuple, set)):
            return [str(x).strip() for x in val if str(x or "").strip()]
        if isinstance(val, str):
            return [s.strip() for s in val.split(",") if s.strip()]
        text = str(val).strip()
        return [text] if text else []

    try:
        max_c = int(max_consulted_per_row)
    except (TypeError, ValueError):
        max_c = 5

    valid_rows_count = 0
    missing_accountable_row_ids: list[str] = []
    multiple_accountable_row_ids: list[str] = []
    missing_responsible_row_ids: list[str] = []
    over_consulted_row_ids: list[str] = []

    for idx, item in enumerate(valid_rows, start=1):
        row_id = (
            str(
                item.get("id")
                or item.get("activity_id")
                or item.get("deliverable")
                or item.get("task")
                or f"RACI-{idx}"
            ).strip()
            or f"RACI-{idx}"
        )
        accountable_list = _normalize_role_list(item, ("accountable", "A", "a"))
        responsible_list = _normalize_role_list(item, ("responsible", "R", "r"))
        consulted_list = _normalize_role_list(item, ("consulted", "C", "c"))
        _normalize_role_list(item, ("informed", "I", "i"))

        has_issue = False
        if len(accountable_list) == 0:
            missing_accountable_row_ids.append(row_id)
            has_issue = True
        elif len(accountable_list) > 1:
            multiple_accountable_row_ids.append(row_id)
            has_issue = True

        if len(responsible_list) == 0:
            missing_responsible_row_ids.append(row_id)
            has_issue = True

        if len(consulted_list) > max_c:
            over_consulted_row_ids.append(row_id)
            has_issue = True

        if not has_issue:
            valid_rows_count += 1

    is_raci_compliant = bool(
        len(missing_accountable_row_ids) == 0
        and len(multiple_accountable_row_ids) == 0
        and len(missing_responsible_row_ids) == 0
        and len(over_consulted_row_ids) == 0
    )

    if len(multiple_accountable_row_ids) > 0:
        raci_posture = "MULTIPLE_ACCOUNTABLE_CONFLICT"
    elif len(missing_accountable_row_ids) > 0:
        raci_posture = "MISSING_ACCOUNTABLE_OWNER"
    elif len(missing_responsible_row_ids) > 0:
        raci_posture = "MISSING_RESPONSIBLE_EXECUTOR"
    elif len(over_consulted_row_ids) > 0:
        raci_posture = "CONSULTED_BOTTLENECK_WARNING"
    else:
        raci_posture = "COMPLIANT_RACI_GOVERNANCE"

    return {
        "total_rows": total_rows,
        "valid_rows_count": valid_rows_count,
        "missing_accountable_row_ids": missing_accountable_row_ids,
        "multiple_accountable_row_ids": multiple_accountable_row_ids,
        "missing_responsible_row_ids": missing_responsible_row_ids,
        "over_consulted_row_ids": over_consulted_row_ids,
        "is_raci_compliant": is_raci_compliant,
        "raci_posture": raci_posture,
    }


_VALID_WIKI_ADR_STATUSES = {"PROPOSED", "ACCEPTED", "SUPERSEDED", "DEPRECATED"}


def audit_wiki_adr_governance_hygiene(
    adrs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita el catálogo de Architecture Decision Records (ADRs) en la Wiki verificando estados, secciones obligatorias y cadenas de supersesión según PMI PMBOK §4.4 y §10.2."""
    raw_items = [item for item in (adrs or []) if isinstance(item, dict)]

    normalized: list[dict[str, str]] = []
    adr_status_map: dict[str, str] = {}

    for item in raw_items:
        adr_id = str(item.get("id") or item.get("adr_id") or "").strip()
        if not adr_id:
            continue
        status = str(item.get("status") or "").strip().upper()
        context = str(item.get("context") or "").strip()
        decision = str(item.get("decision") or "").strip()
        consequences = str(item.get("consequences") or "").strip()
        superseded_by_id = str(item.get("superseded_by_id") or "").strip()
        normalized.append(
            {
                "adr_id": adr_id,
                "status": status,
                "context": context,
                "decision": decision,
                "consequences": consequences,
                "superseded_by_id": superseded_by_id,
            }
        )
        adr_status_map[adr_id] = status

    total_adrs = len(normalized)
    accepted_adrs_count = 0
    invalid_status_adr_ids: list[str] = []
    incomplete_section_adr_ids: list[str] = []
    broken_supersession_adr_ids: list[str] = []

    for rec in normalized:
        adr_id = rec["adr_id"]
        status = rec["status"]
        if status == "ACCEPTED":
            accepted_adrs_count += 1
        if status not in _VALID_WIKI_ADR_STATUSES:
            invalid_status_adr_ids.append(adr_id)
        if not rec["context"] or not rec["decision"] or not rec["consequences"]:
            incomplete_section_adr_ids.append(adr_id)
        if status == "SUPERSEDED":
            target_id = rec["superseded_by_id"]
            if (
                not target_id
                or target_id == adr_id
                or target_id not in adr_status_map
                or adr_status_map[target_id] != "ACCEPTED"
            ):
                broken_supersession_adr_ids.append(adr_id)

    is_adr_catalog_governed = bool(
        total_adrs > 0
        and len(invalid_status_adr_ids) == 0
        and len(incomplete_section_adr_ids) == 0
        and len(broken_supersession_adr_ids) == 0
    )

    if total_adrs == 0:
        adr_posture = "EMPTY_ADR_CATALOG"
    elif len(broken_supersession_adr_ids) > 0:
        adr_posture = "BROKEN_ADR_SUPERSESSION_CHAIN"
    elif len(incomplete_section_adr_ids) > 0:
        adr_posture = "INCOMPLETE_ADR_SECTIONS"
    elif len(invalid_status_adr_ids) > 0:
        adr_posture = "INVALID_ADR_STATUS"
    else:
        adr_posture = "GOVERNED_ADR_CATALOG"

    return {
        "total_adrs": total_adrs,
        "accepted_adrs_count": accepted_adrs_count,
        "invalid_status_adr_ids": invalid_status_adr_ids,
        "incomplete_section_adr_ids": incomplete_section_adr_ids,
        "broken_supersession_adr_ids": broken_supersession_adr_ids,
        "is_adr_catalog_governed": is_adr_catalog_governed,
        "adr_posture": adr_posture,
    }


WikiPMIService.audit_wiki_adr_governance_hygiene = staticmethod(
    audit_wiki_adr_governance_hygiene
)


def audit_wiki_postmortem_root_cause_governance(
    postmortems: List[Dict[str, Any]] | None = None,
    min_whys_depth: int = 3,
) -> Dict[str, Any]:
    """PMI PMBOK 4.4 / 8.2 — gobernanza de post-mortems de incidentes en Wiki.

    Evalúa profundidad 5-Whys (mínimo ``min_whys_depth``), línea de tiempo
    del incidente y accionabilidad CAPA (cada acción con dueño y fecha).
    """
    if not isinstance(postmortems, list):
        postmortems = []

    total_postmortems = 0
    shallow_rca_postmortem_ids: List[str] = []
    missing_timeline_postmortem_ids: List[str] = []
    unactionable_capa_postmortem_ids: List[str] = []

    try:
        depth_floor = max(1, int(min_whys_depth))
    except (TypeError, ValueError):
        depth_floor = 3

    for item in postmortems:
        if not isinstance(item, dict):
            continue
        pm_id = str(item.get("id") or item.get("postmortem_id") or "").strip()
        if not pm_id:
            continue
        total_postmortems += 1

        whys_chain = [str(w).strip() for w in (item.get("whys_chain") or []) if str(w).strip()]
        has_timeline = bool(str(item.get("incident_timeline") or "").strip())
        raw_capa = item.get("capa_items")
        capa_items = raw_capa if isinstance(raw_capa, list) else []

        if len(whys_chain) < depth_floor:
            shallow_rca_postmortem_ids.append(pm_id)

        if not has_timeline:
            missing_timeline_postmortem_ids.append(pm_id)

        capa_unactionable = len(capa_items) == 0 or any(
            (not isinstance(capa_item, dict))
            or (not str(capa_item.get("owner_id") or "").strip())
            or (not str(capa_item.get("due_date") or "").strip())
            for capa_item in capa_items
        )
        if capa_unactionable:
            unactionable_capa_postmortem_ids.append(pm_id)

    is_postmortem_governance_valid = (
        total_postmortems > 0
        and not shallow_rca_postmortem_ids
        and not missing_timeline_postmortem_ids
        and not unactionable_capa_postmortem_ids
    )

    if total_postmortems == 0:
        postmortem_posture = "NO_POSTMORTEMS_RECORDED"
    elif unactionable_capa_postmortem_ids:
        postmortem_posture = "UNACTIONABLE_POSTMORTEM_CAPA"
    elif shallow_rca_postmortem_ids:
        postmortem_posture = "SHALLOW_ROOT_CAUSE_ANALYSIS"
    elif missing_timeline_postmortem_ids:
        postmortem_posture = "MISSING_INCIDENT_TIMELINE"
    else:
        postmortem_posture = "GOVERNED_BLAMELESS_POSTMORTEMS"

    return {
        "total_postmortems": total_postmortems,
        "shallow_rca_postmortem_ids": shallow_rca_postmortem_ids,
        "missing_timeline_postmortem_ids": missing_timeline_postmortem_ids,
        "unactionable_capa_postmortem_ids": unactionable_capa_postmortem_ids,
        "is_postmortem_governance_valid": is_postmortem_governance_valid,
        "postmortem_posture": postmortem_posture,
    }


WikiPMIService.audit_wiki_postmortem_root_cause_governance = staticmethod(
    audit_wiki_postmortem_root_cause_governance
)


def audit_wiki_benefits_realization_governance(
    benefit_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Audita registros del Plan de Gestión de Beneficios (PMI Benefits Management Plan §1.2.6 & §4.4)."""
    valid_cadences = {
        "monthly",
        "quarterly",
        "semi_annual",
        "annual",
        "milestone",
    }
    evaluated_benefit_count = 0
    unowned_benefit_ids: list[str] = []
    unquantified_target_ids: list[str] = []
    missing_cadence_ids: list[str] = []
    unaligned_benefit_ids: list[str] = []
    attainments: list[float] = []

    for item in benefit_records or []:
        if not isinstance(item, Mapping):
            continue
        benefit_id = str(item.get("benefit_id") or "").strip()
        if not benefit_id:
            continue

        evaluated_benefit_count += 1
        benefit_owner = str(item.get("benefit_owner") or "").strip()
        if not benefit_owner:
            unowned_benefit_ids.append(benefit_id)

        raw_baseline = item.get("baseline_value")
        raw_target = item.get("target_value")
        raw_realized = item.get("realized_value")

        baseline_val: float | None = None
        target_val: float | None = None
        realized_val: float | None = None

        if raw_baseline is not None and not isinstance(raw_baseline, bool):
            try:
                baseline_val = float(raw_baseline)
            except (TypeError, ValueError):
                baseline_val = None
        if raw_target is not None and not isinstance(raw_target, bool):
            try:
                target_val = float(raw_target)
            except (TypeError, ValueError):
                target_val = None
        if raw_realized is not None and not isinstance(raw_realized, bool):
            try:
                realized_val = float(raw_realized)
            except (TypeError, ValueError):
                realized_val = None

        if (
            baseline_val is None
            or target_val is None
            or target_val == baseline_val
        ):
            unquantified_target_ids.append(benefit_id)
            delta_target = 0.0
        else:
            delta_target = target_val - baseline_val

        measurement_cadence = (
            str(item.get("measurement_cadence") or "").strip().lower()
        )
        if measurement_cadence not in valid_cadences:
            missing_cadence_ids.append(benefit_id)

        strategic_alignment_linked = bool(
            item.get("strategic_alignment_linked", False)
        )
        if not strategic_alignment_linked:
            unaligned_benefit_ids.append(benefit_id)

        if (
            baseline_val is not None
            and target_val is not None
            and delta_target != 0.0
            and realized_val is not None
        ):
            attainment_pct = max(
                0.0,
                min(
                    100.0,
                    ((realized_val - baseline_val) / delta_target) * 100.0,
                ),
            )
        else:
            attainment_pct = 0.0
        attainments.append(attainment_pct)

    average_attainment_pct = (
        round(sum(attainments) / evaluated_benefit_count, 2)
        if evaluated_benefit_count > 0
        else 0.0
    )
    is_governed = bool(
        evaluated_benefit_count > 0
        and len(unowned_benefit_ids) == 0
        and len(unquantified_target_ids) == 0
        and len(missing_cadence_ids) == 0
        and len(unaligned_benefit_ids) == 0
    )

    return {
        "evaluated_benefit_count": evaluated_benefit_count,
        "unowned_benefit_ids": unowned_benefit_ids,
        "unquantified_target_ids": unquantified_target_ids,
        "missing_cadence_ids": missing_cadence_ids,
        "unaligned_benefit_ids": unaligned_benefit_ids,
        "average_attainment_pct": average_attainment_pct,
        "is_governed": is_governed,
    }


WikiPMIService.audit_wiki_benefits_realization_governance = staticmethod(
    audit_wiki_benefits_realization_governance
)


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
    "audit_wiki_project_glossary_governance",
    "audit_wiki_knowledge_bus_factor_and_freshness",
    "audit_wiki_operational_runbook_readiness",
    "audit_wiki_adr_lifecycle_traceability",
    "audit_wiki_raci_matrix_governance",
    "audit_wiki_adr_governance_hygiene",
    "audit_wiki_risk_breakdown_structure_coverage",
    "audit_wiki_postmortem_root_cause_governance",
    "audit_wiki_benefits_realization_governance",
    "audit_wiki_raid_log_traceability_governance",
    "audit_wiki_definition_of_ready_gate_hygiene",
    "audit_wiki_retrospective_action_closure_governance",
    "audit_wiki_monte_carlo_contingency_governance",
    "audit_wiki_make_or_buy_and_source_selection_governance",
    "audit_wiki_opa_template_versioning_governance",
    "audit_wiki_onboarding_and_kt_handover_readiness",
    "audit_wiki_vendor_sla_and_penalty_clause_governance",
    "WikiPMIService",
]



def audit_wiki_knowledge_bus_factor_and_freshness(
    article_records: Sequence[Mapping[str, Any]] | None,
    *,
    max_stale_days: int = 90,
) -> dict[str, Any]:
    """PMI PMBOK 4.4.3.1 — resiliencia de conocimiento organizacional (bus-factor y vigencia OPA).

    Para cada artículo con ``article_id`` válido:
    - contribuyentes únicos limpios (ignorando ``None``); sin autores ->
      ``unauthored_article_ids``.
    - ``domain_criticality`` en {'high', 'critical'} con <= 1 contribuyente ->
      ``single_author_critical_article_ids``.
    - crítico sin ``peer_reviewed`` -> ``unreviewed_critical_article_ids``.
    - ``days_since_last_review`` > ``max_stale_days`` -> ``stale_article_ids``.
    """
    if not isinstance(article_records, (list, tuple)):
        article_records = []

    evaluated_article_count = 0
    unauthored_article_ids: list[str] = []
    single_author_critical_article_ids: list[str] = []
    unreviewed_critical_article_ids: list[str] = []
    stale_article_ids: list[str] = []

    for item in article_records:
        if not isinstance(item, Mapping):
            continue
        article_id = str(item.get("article_id") or "").strip()
        if not article_id:
            continue
        evaluated_article_count += 1

        raw_contributors = item.get("contributor_ids")
        if not isinstance(raw_contributors, (list, tuple, set)):
            raw_contributors = []
        contributors: set[str] = {
            str(contributor).strip()
            for contributor in raw_contributors
            if contributor is not None and str(contributor).strip()
        }

        domain_criticality = str(item.get("domain_criticality") or "standard").strip().lower()
        is_domain_critical = domain_criticality in {"high", "critical"}

        try:
            days_since_last_review = float(item.get("days_since_last_review", 0))
        except (TypeError, ValueError):
            days_since_last_review = 0.0
        peer_reviewed = bool(item.get("peer_reviewed", False))

        if len(contributors) == 0:
            unauthored_article_ids.append(article_id)

        if is_domain_critical and len(contributors) <= 1:
            single_author_critical_article_ids.append(article_id)

        if is_domain_critical and not peer_reviewed:
            unreviewed_critical_article_ids.append(article_id)

        if days_since_last_review > float(max_stale_days):
            stale_article_ids.append(article_id)

    is_resilient = bool(
        evaluated_article_count > 0
        and len(unauthored_article_ids) == 0
        and len(single_author_critical_article_ids) == 0
        and len(unreviewed_critical_article_ids) == 0
        and len(stale_article_ids) == 0
    )

    return {
        "evaluated_article_count": evaluated_article_count,
        "unauthored_article_ids": unauthored_article_ids,
        "single_author_critical_article_ids": single_author_critical_article_ids,
        "unreviewed_critical_article_ids": unreviewed_critical_article_ids,
        "stale_article_ids": stale_article_ids,
        "is_resilient": is_resilient,
    }


def audit_wiki_raci_matrix_governance(
    deliverable_assignments: Sequence[Mapping[str, Any]] | None,
    *,
    max_consulted_per_deliverable: int = 5,
) -> dict[str, Any]:
    """Audita la Matriz de Asignación de Responsabilidades RACI en la Wiki (RAM / RACI Chart PMI PMBOK §9.1.2.2 y §4.4)."""
    if not isinstance(deliverable_assignments, (list, tuple)):
        deliverable_assignments = []

    def _clean_unique_ids(raw_seq: Any) -> list[str]:
        if not isinstance(raw_seq, (list, tuple, set)):
            return []
        unique: list[str] = []
        for entry in raw_seq:
            if entry is None or isinstance(entry, bool):
                continue
            cleaned = str(entry).strip()
            if cleaned and cleaned not in unique:
                unique.append(cleaned)
        return unique

    evaluated_deliverable_count = 0
    missing_accountable_deliverable_ids: list[str] = []
    multiple_accountable_deliverable_ids: list[str] = []
    missing_responsible_deliverable_ids: list[str] = []
    excessive_consulted_deliverable_ids: list[str] = []

    for item in deliverable_assignments:
        if not isinstance(item, Mapping):
            continue
        deliverable_id = str(item.get("deliverable_id") or "").strip()
        if not deliverable_id:
            continue
        evaluated_deliverable_count += 1

        responsibles = _clean_unique_ids(item.get("responsible_ids"))
        accountables = _clean_unique_ids(item.get("accountable_ids"))
        consulteds = _clean_unique_ids(item.get("consulted_ids"))
        _clean_unique_ids(item.get("informed_ids"))

        if len(accountables) == 0:
            missing_accountable_deliverable_ids.append(deliverable_id)
        elif len(accountables) > 1:
            multiple_accountable_deliverable_ids.append(deliverable_id)

        if len(responsibles) == 0:
            missing_responsible_deliverable_ids.append(deliverable_id)

        if len(consulteds) > int(max_consulted_per_deliverable):
            excessive_consulted_deliverable_ids.append(deliverable_id)

    is_raci_compliant = bool(
        evaluated_deliverable_count > 0
        and len(missing_accountable_deliverable_ids) == 0
        and len(multiple_accountable_deliverable_ids) == 0
        and len(missing_responsible_deliverable_ids) == 0
        and len(excessive_consulted_deliverable_ids) == 0
    )

    return {
        "evaluated_deliverable_count": evaluated_deliverable_count,
        "missing_accountable_deliverable_ids": missing_accountable_deliverable_ids,
        "multiple_accountable_deliverable_ids": multiple_accountable_deliverable_ids,
        "missing_responsible_deliverable_ids": missing_responsible_deliverable_ids,
        "excessive_consulted_deliverable_ids": excessive_consulted_deliverable_ids,
        "is_raci_compliant": is_raci_compliant,
    }


def audit_wiki_raid_log_traceability_governance(
    raid_entries: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """PMBOK §4.4 / §11.2 — trazabilidad WBS y gobernanza de acciones del RAID log.

    - Categoría fuera de {'risk','assumption','issue','dependency'} ->
      ``invalid_category_entry_ids``.
    - Sin ``owner_id`` o sin ``linked_wbs_code`` -> ``untraceable_entry_ids``.
    - Entradas abiertas (no closed/resolved/retired) vencidas o sin plan de
      resolución -> ``at_risk_open_entry_ids``.
    """
    if not isinstance(raid_entries, (list, tuple)):
        raid_entries = []

    total_entries = 0
    invalid_category_entry_ids: list[str] = []
    untraceable_entry_ids: list[str] = []
    at_risk_open_entry_ids: list[str] = []

    for item in raid_entries:
        if not isinstance(item, Mapping):
            continue
        entry_id = str(item.get("entry_id") or "").strip()
        if not entry_id:
            continue
        total_entries += 1

        category = str(item.get("category") or "").strip().lower()
        owner_id = str(item.get("owner_id") or "").strip()
        linked_wbs_code = str(item.get("linked_wbs_code") or "").strip()
        resolution_plan = str(item.get("resolution_plan") or "").strip()
        is_overdue = bool(item.get("is_overdue", False))
        status = str(item.get("status") or "").strip().lower()

        if category not in {"risk", "assumption", "issue", "dependency"}:
            invalid_category_entry_ids.append(entry_id)

        if not owner_id or not linked_wbs_code:
            untraceable_entry_ids.append(entry_id)

        if (
            status not in {"closed", "resolved", "retired"}
            and (is_overdue or not resolution_plan)
        ):
            at_risk_open_entry_ids.append(entry_id)

    traceable_count = total_entries - len(untraceable_entry_ids)
    traceability_rate_pct = (
        round((traceable_count / total_entries) * 100.0, 2)
        if total_entries > 0
        else 0.0
    )
    is_raid_governance_compliant = bool(
        total_entries > 0
        and not invalid_category_entry_ids
        and not untraceable_entry_ids
        and not at_risk_open_entry_ids
    )

    return {
        "total_entries": total_entries,
        "invalid_category_entry_ids": invalid_category_entry_ids,
        "untraceable_entry_ids": untraceable_entry_ids,
        "at_risk_open_entry_ids": at_risk_open_entry_ids,
        "traceability_rate_pct": traceability_rate_pct,
        "is_raid_governance_compliant": is_raid_governance_compliant,
    }


WikiPMIService.audit_wiki_raid_log_traceability_governance = staticmethod(
    audit_wiki_raid_log_traceability_governance
)


def audit_wiki_definition_of_ready_gate_hygiene(
    backlog_items: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Audit wiki backlog items for PMI PMBOK §8.1 & §4.4 Definition of Ready (DoR) gate hygiene."""
    if (
        not backlog_items
        or not isinstance(backlog_items, Sequence)
        or isinstance(backlog_items, (str, bytes, Mapping))
    ):
        return {
            "total_items": 0,
            "missing_acceptance_criteria_item_ids": [],
            "unestimated_item_ids": [],
            "blocked_dependency_item_ids": [],
            "missing_spec_link_item_ids": [],
            "dor_pass_rate_pct": 0.0,
            "is_sprint_ready": False,
        }

    total_items = 0
    ready_count = 0
    missing_acceptance_criteria_item_ids: list[str] = []
    unestimated_item_ids: list[str] = []
    blocked_dependency_item_ids: list[str] = []
    missing_spec_link_item_ids: list[str] = []

    for item in backlog_items:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("item_id") or "").strip()
        if not item_id:
            continue

        total_items += 1
        try:
            acceptance_criteria_count = max(
                0, int(item.get("acceptance_criteria_count", 0) or 0)
            )
        except (TypeError, ValueError):
            acceptance_criteria_count = 0

        story_points_estimated = bool(item.get("story_points_estimated", False))
        dependencies_cleared = bool(item.get("dependencies_cleared", False))
        ux_or_tech_spec_linked = bool(item.get("ux_or_tech_spec_linked", False))

        has_ac = acceptance_criteria_count >= 1
        if not has_ac:
            missing_acceptance_criteria_item_ids.append(item_id)
        if not story_points_estimated:
            unestimated_item_ids.append(item_id)
        if not dependencies_cleared:
            blocked_dependency_item_ids.append(item_id)
        if not ux_or_tech_spec_linked:
            missing_spec_link_item_ids.append(item_id)

        if (
            has_ac
            and story_points_estimated
            and dependencies_cleared
            and ux_or_tech_spec_linked
        ):
            ready_count += 1

    dor_pass_rate_pct = (
        round((ready_count / total_items) * 100.0, 2) if total_items > 0 else 0.0
    )
    is_sprint_ready = bool(total_items > 0 and ready_count == total_items)

    return {
        "total_items": total_items,
        "missing_acceptance_criteria_item_ids": missing_acceptance_criteria_item_ids,
        "unestimated_item_ids": unestimated_item_ids,
        "blocked_dependency_item_ids": blocked_dependency_item_ids,
        "missing_spec_link_item_ids": missing_spec_link_item_ids,
        "dor_pass_rate_pct": dor_pass_rate_pct,
        "is_sprint_ready": is_sprint_ready,
    }


WikiPMIService.audit_wiki_definition_of_ready_gate_hygiene = staticmethod(
    audit_wiki_definition_of_ready_gate_hygiene
)


def audit_wiki_retrospective_action_closure_governance(
    retro_actions: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """PMBOK §4.4 / §8.2 — cierre de acciones de retro y verificación de impacto.

    - Sin ``owner_id`` -> ``unassigned_action_ids``.
    - Abiertas (no closed/done/verified) vencidas (current > due) ->
      ``overdue_sprint_action_ids``.
    - Cerradas sin ``impact_verified`` -> ``unverified_closure_action_ids``.
    - ``closure_effectiveness_pct`` = cerradas con impacto verificado / total.
    """
    if not isinstance(retro_actions, (list, tuple)):
        retro_actions = []

    total_actions = 0
    verified_closed_count = 0
    unassigned_action_ids: list[str] = []
    overdue_sprint_action_ids: list[str] = []
    unverified_closure_action_ids: list[str] = []

    for item in retro_actions:
        if not isinstance(item, Mapping):
            continue
        action_id = str(item.get("action_id") or "").strip()
        if not action_id:
            continue

        owner_id = str(item.get("owner_id") or "").strip()
        try:
            due_sprint = int(item.get("due_sprint", 0) or 0)
        except (TypeError, ValueError):
            due_sprint = 0
        try:
            current_sprint = int(item.get("current_sprint", 0) or 0)
        except (TypeError, ValueError):
            current_sprint = 0
        status = str(item.get("status") or "").strip().lower()
        impact_verified = bool(item.get("impact_verified", False))

        total_actions += 1

        if not owner_id:
            unassigned_action_ids.append(action_id)

        if (
            status not in {"closed", "done", "verified"}
            and due_sprint > 0
            and current_sprint > due_sprint
        ):
            overdue_sprint_action_ids.append(action_id)

        if status in {"closed", "done", "verified"} and not impact_verified:
            unverified_closure_action_ids.append(action_id)

        if owner_id and status in {"closed", "done", "verified"} and impact_verified:
            verified_closed_count += 1

    closure_effectiveness_pct = (
        round((verified_closed_count / total_actions) * 100.0, 2)
        if total_actions > 0
        else 0.0
    )
    is_retrospective_governance_healthy = bool(
        total_actions > 0
        and not unassigned_action_ids
        and not overdue_sprint_action_ids
        and not unverified_closure_action_ids
    )

    return {
        "total_actions": total_actions,
        "unassigned_action_ids": unassigned_action_ids,
        "overdue_sprint_action_ids": overdue_sprint_action_ids,
        "unverified_closure_action_ids": unverified_closure_action_ids,
        "closure_effectiveness_pct": closure_effectiveness_pct,
        "is_retrospective_governance_healthy": is_retrospective_governance_healthy,
    }


WikiPMIService.audit_wiki_retrospective_action_closure_governance = staticmethod(
    audit_wiki_retrospective_action_closure_governance
)


def audit_wiki_monte_carlo_contingency_governance(
    simulation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Audita la simulación Monte Carlo y cobertura de reserva de contingencia en P80 documentada en la Wiki (PMI PMBOK §11.4 y §4.4)."""
    sim: Mapping[str, Any] = (
        simulation if isinstance(simulation, Mapping) else {}
    )

    try:
        iterations = max(0, int(sim.get("iterations", 0) or 0))
    except (TypeError, ValueError):
        iterations = 0

    try:
        p50_cost = round(max(0.0, float(sim.get("p50_cost", 0.0) or 0.0)), 2)
    except (TypeError, ValueError):
        p50_cost = 0.0

    try:
        p80_cost = round(max(0.0, float(sim.get("p80_cost", 0.0) or 0.0)), 2)
    except (TypeError, ValueError):
        p80_cost = 0.0

    try:
        p90_cost = round(max(0.0, float(sim.get("p90_cost", 0.0) or 0.0)), 2)
    except (TypeError, ValueError):
        p90_cost = 0.0

    try:
        allocated_contingency = round(
            max(0.0, float(sim.get("allocated_contingency", 0.0) or 0.0)), 2
        )
    except (TypeError, ValueError):
        allocated_contingency = 0.0

    try:
        base_estimate = round(
            max(0.0, float(sim.get("base_estimate", 0.0) or 0.0)), 2
        )
    except (TypeError, ValueError):
        base_estimate = 0.0

    required_p80_contingency = round(max(0.0, p80_cost - base_estimate), 2)
    contingency_shortfall = round(
        max(0.0, required_p80_contingency - allocated_contingency), 2
    )

    governance_gaps: list[str] = []
    if iterations < 1000:
        governance_gaps.append("insufficient_simulation_iterations")
    if base_estimate <= 0.0 or not (
        base_estimate <= p50_cost <= p80_cost <= p90_cost
    ):
        governance_gaps.append("non_monotonic_percentile_curve")
    if allocated_contingency < required_p80_contingency:
        governance_gaps.append("contingency_below_p80_threshold")

    is_simulation_governance_valid = bool(len(governance_gaps) == 0)

    return {
        "iterations": iterations,
        "required_p80_contingency": required_p80_contingency,
        "allocated_contingency": allocated_contingency,
        "contingency_shortfall": contingency_shortfall,
        "governance_gaps": governance_gaps,
        "is_simulation_governance_valid": is_simulation_governance_valid,
    }


WikiPMIService.audit_wiki_monte_carlo_contingency_governance = staticmethod(
    audit_wiki_monte_carlo_contingency_governance
)


def audit_wiki_make_or_buy_and_source_selection_governance(
    decisions: Sequence[Mapping[str, Any]] | None,
    weight_tolerance_pct: float = 0.5,
) -> dict[str, Any]:
    """Audita decisiones Make-or-Buy y matrices de criterios de selección de proveedores en la Wiki según PMI PMBOK §12.1 y §4.4."""
    if (
        not decisions
        or not isinstance(decisions, Sequence)
        or isinstance(decisions, (str, bytes, Mapping))
    ):
        items: Sequence[Any] = []
    else:
        items = decisions

    def _is_positive_cost(val: Any) -> bool:
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return False
        return float(val) > 0.0

    def _extract_positive_weights(raw_weights: Any) -> list[float]:
        weights: list[float] = []
        if isinstance(raw_weights, Mapping):
            for val in raw_weights.values():
                if not isinstance(val, bool) and isinstance(val, (int, float)) and float(val) > 0.0:
                    weights.append(float(val))
        elif isinstance(raw_weights, Sequence) and not isinstance(
            raw_weights, (str, bytes, Mapping)
        ):
            for entry in raw_weights:
                if not isinstance(entry, Mapping):
                    continue
                w_val = entry.get(
                    "weight_pct", entry.get("weight")
                )
                if not isinstance(w_val, bool) and isinstance(w_val, (int, float)) and float(w_val) > 0.0:
                    weights.append(float(w_val))
        return weights

    total_evaluated = 0
    buy_or_lease_count = 0
    unquantified_tco_item_ids: list[str] = []
    core_competency_outsourced_without_mitigation_ids: list[str] = []
    unbalanced_criteria_weight_item_ids: list[str] = []
    missing_independent_estimate_item_ids: list[str] = []

    external_decisions = {"buy", "lease", "hybrid"}
    tol = float(weight_tolerance_pct)

    for item in items:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("item_id") or item.get("id") or "").strip()
        if not item_id:
            continue

        total_evaluated += 1
        decision = str(item.get("decision") or "make").strip().lower()

        has_internal = _is_positive_cost(item.get("internal_cost_estimate"))
        has_external = _is_positive_cost(item.get("external_cost_estimate"))
        if not has_internal or (decision in external_decisions and not has_external):
            unquantified_tco_item_ids.append(item_id)

        if (
            bool(item.get("strategic_core_competency") is True)
            and decision in {"buy", "lease"}
            and not str(item.get("ip_protection_strategy") or "").strip()
        ):
            core_competency_outsourced_without_mitigation_ids.append(item_id)

        if decision in external_decisions:
            buy_or_lease_count += 1
            weights = _extract_positive_weights(
                item.get("evaluation_criteria_weights")
            )
            if not weights or abs(sum(weights) - 100.0) > tol:
                unbalanced_criteria_weight_item_ids.append(item_id)

            if not bool(item.get("independent_estimate_prepared") is True):
                missing_independent_estimate_item_ids.append(item_id)

    is_procurement_governance_compliant = bool(
        len(unquantified_tco_item_ids) == 0
        and len(core_competency_outsourced_without_mitigation_ids) == 0
        and len(unbalanced_criteria_weight_item_ids) == 0
        and len(missing_independent_estimate_item_ids) == 0
    )

    recommendations: list[str] = []
    if unquantified_tco_item_ids:
        recommendations.append(
            "Cuantificar el Costo Total de Propiedad (TCO) interno y externo antes de formalizar decisiones Make-or-Buy."
        )
    if core_competency_outsourced_without_mitigation_ids:
        recommendations.append(
            "Definir estrategia de protección de propiedad intelectual (NDA, escrow o retención de núcleo) antes de externalizar competencias estratégicas."
        )
    if unbalanced_criteria_weight_item_ids:
        recommendations.append(
            "Normalizar los pesos de la matriz de criterios de selección de proveedores para que sumen exactamente 100%."
        )
    if missing_independent_estimate_item_ids:
        recommendations.append(
            "Elaborar una estimación independiente de costos (Should-Cost / Independent Cost Estimate) para contrastar las propuestas de proveedores."
        )

    if (
        len(unquantified_tco_item_ids) > 0
        or len(core_competency_outsourced_without_mitigation_ids) > 0
    ):
        status = "critical"
    elif (
        len(unbalanced_criteria_weight_item_ids) > 0
        or len(missing_independent_estimate_item_ids) > 0
    ):
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_evaluated": total_evaluated,
        "buy_or_lease_count": buy_or_lease_count,
        "unquantified_tco_item_ids": unquantified_tco_item_ids,
        "core_competency_outsourced_without_mitigation_ids": core_competency_outsourced_without_mitigation_ids,
        "unbalanced_criteria_weight_item_ids": unbalanced_criteria_weight_item_ids,
        "missing_independent_estimate_item_ids": missing_independent_estimate_item_ids,
        "is_procurement_governance_compliant": is_procurement_governance_compliant,
        "status": status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_make_or_buy_and_source_selection_governance = staticmethod(
    audit_wiki_make_or_buy_and_source_selection_governance
)


_OPA_TEMPLATE_SEMVER_RE = re.compile(r"^\d+\.\d+(\.\d+)?(-[A-Za-z0-9._-]+)?$")


def audit_wiki_opa_template_versioning_governance(
    templates: Sequence[Mapping[str, Any]] | None,
    max_review_age_days: float = 365.0,
) -> dict[str, Any]:
    """Audita el versionado semántico, custodia PMO y deprecación de plantillas de Activos de los Procesos de la Organización (OPA) según PMI PMBOK §2.5 y §4.4."""
    if (
        not templates
        or not isinstance(templates, Sequence)
        or isinstance(templates, (str, bytes, Mapping))
    ):
        items: Sequence[Any] = []
    else:
        items = templates

    total_templates = 0
    invalid_semver_template_ids: list[str] = []
    deprecated_without_replacement_ids: list[str] = []
    active_usage_on_deprecated_template_ids: list[str] = []
    stale_or_unowned_active_template_ids: list[str] = []

    for item in items:
        if not isinstance(item, Mapping):
            continue
        template_id = str(
            item.get("template_id") or item.get("id") or ""
        ).strip()
        if not template_id:
            continue

        total_templates += 1
        semver = str(item.get("semver") or item.get("version") or "").strip()
        if not _OPA_TEMPLATE_SEMVER_RE.match(semver):
            invalid_semver_template_ids.append(template_id)

        status = str(item.get("status") or "active").strip().lower()
        if status in {"deprecated", "superseded"}:
            if not str(item.get("replacement_template_id") or "").strip():
                deprecated_without_replacement_ids.append(template_id)

            try:
                active_projects_using_count = int(
                    item.get("active_projects_using_count") or 0
                )
            except (TypeError, ValueError):
                active_projects_using_count = 0

            if active_projects_using_count > 0:
                active_usage_on_deprecated_template_ids.append(template_id)

        elif status == "active":
            try:
                days_since_last_review = float(
                    item.get("days_since_last_review") or 0.0
                )
            except (TypeError, ValueError):
                days_since_last_review = 0.0

            if (
                days_since_last_review > float(max_review_age_days)
                or not str(item.get("pmo_steward") or "").strip()
            ):
                stale_or_unowned_active_template_ids.append(template_id)

    is_opa_governance_compliant = bool(
        len(invalid_semver_template_ids) == 0
        and len(deprecated_without_replacement_ids) == 0
        and len(active_usage_on_deprecated_template_ids) == 0
        and len(stale_or_unowned_active_template_ids) == 0
    )

    recommendations: list[str] = []
    if invalid_semver_template_ids:
        recommendations.append(
            "Estandarizar el versionado semántico (MAJOR.MINOR[.PATCH]) en las plantillas OPA: "
            + ", ".join(invalid_semver_template_ids)
            + "."
        )
    if deprecated_without_replacement_ids:
        recommendations.append(
            "Vincular un identificador de plantilla sustituta (replacement_template_id) a toda plantilla deprecada o superada."
        )
    if active_usage_on_deprecated_template_ids:
        recommendations.append(
            "Migrar los proyectos activos que continúan utilizando plantillas OPA deprecadas hacia la versión vigente."
        )
    if stale_or_unowned_active_template_ids:
        recommendations.append(
            "Designar custodio PMO (pmo_steward) y ejecutar la revisión periódica anual de las plantillas OPA activas."
        )

    if (
        len(invalid_semver_template_ids) > 0
        or len(deprecated_without_replacement_ids) > 0
        or len(active_usage_on_deprecated_template_ids) > 0
    ):
        overall_status = "critical"
    elif len(stale_or_unowned_active_template_ids) > 0:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return {
        "total_templates": total_templates,
        "invalid_semver_template_ids": invalid_semver_template_ids,
        "deprecated_without_replacement_ids": deprecated_without_replacement_ids,
        "active_usage_on_deprecated_template_ids": active_usage_on_deprecated_template_ids,
        "stale_or_unowned_active_template_ids": stale_or_unowned_active_template_ids,
        "is_opa_governance_compliant": is_opa_governance_compliant,
        "status": overall_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_opa_template_versioning_governance = staticmethod(
    audit_wiki_opa_template_versioning_governance
)



def audit_wiki_risk_breakdown_structure_coverage(
    rbs_categories: object,
    *,
    min_risks_per_category: int = 1,
) -> dict[str, object]:
    """Audita cobertura de categorías de la Risk Breakdown Structure (RBS), dueños de riesgo y condiciones disparadoras documentadas en wikis según PMI PMBOK §11.1 y §11.2."""
    total_evaluated = 0
    blind_spot_category_ids: list[str] = []
    unowned_risk_category_ids: list[str] = []
    missing_trigger_category_ids: list[str] = []

    min_risks = int(min_risks_per_category)
    categories: Sequence[Any] = (
        rbs_categories
        if isinstance(rbs_categories, Sequence)
        and not isinstance(rbs_categories, (str, bytes, bytearray, Mapping))
        else []
    )

    for item in categories:
        if not isinstance(item, Mapping):
            continue
        cat_id = str(item.get("category_code") or item.get("id") or "").strip()
        if not cat_id:
            continue

        total_evaluated += 1

        is_applicable = bool(item.get("is_applicable", True))
        try:
            risks_identified_count = int(item.get("risks_identified_count", 0) or 0)
        except (TypeError, ValueError):
            risks_identified_count = 0
        has_assigned_risk_owner = bool(item.get("has_assigned_risk_owner", False))
        has_trigger_conditions_documented = bool(
            item.get("has_trigger_conditions_documented", False)
        )

        if is_applicable and risks_identified_count < min_risks:
            blind_spot_category_ids.append(cat_id)

        if (
            is_applicable
            and risks_identified_count > 0
            and not has_assigned_risk_owner
        ):
            unowned_risk_category_ids.append(cat_id)

        if (
            is_applicable
            and risks_identified_count > 0
            and not has_trigger_conditions_documented
        ):
            missing_trigger_category_ids.append(cat_id)

    is_rbs_coverage_complete = bool(
        len(blind_spot_category_ids) == 0
        and len(unowned_risk_category_ids) == 0
        and len(missing_trigger_category_ids) == 0
    )

    return {
        "total_evaluated": total_evaluated,
        "blind_spot_category_ids": blind_spot_category_ids,
        "unowned_risk_category_ids": unowned_risk_category_ids,
        "missing_trigger_category_ids": missing_trigger_category_ids,
        "is_rbs_coverage_complete": is_rbs_coverage_complete,
    }


WikiPMIService.audit_wiki_risk_breakdown_structure_coverage = staticmethod(
    audit_wiki_risk_breakdown_structure_coverage
)


def audit_wiki_onboarding_and_kt_handover_readiness(
    kt_packages: object,
    *,
    max_onboarding_days: int = 10,
) -> dict[str, object]:
    """Audita playbooks de onboarding y paquetes de transferencia de conocimiento (Knowledge Transfer - KT) del equipo en la Wiki según PMI PMBOK §4.4 y §9.4."""
    total_evaluated = 0
    incomplete_documentation_package_ids: list[str] = []
    unverified_handover_package_ids: list[str] = []
    excessive_rampup_package_ids: list[str] = []

    if isinstance(kt_packages, Sequence) and not isinstance(
        kt_packages, (str, bytes, bytearray)
    ):
        for item in kt_packages:
            if not isinstance(item, Mapping):
                continue
            pkg_id = str(item.get("package_id") or item.get("id") or "").strip()
            if not pkg_id:
                continue

            total_evaluated += 1
            has_architecture_walkthrough = bool(
                item.get("has_architecture_walkthrough", False)
            )
            has_local_env_setup_guide = bool(
                item.get("has_local_env_setup_guide", False)
            )
            try:
                shadowing_sessions_completed = int(
                    item.get("shadowing_sessions_completed", 0) or 0
                )
            except (TypeError, ValueError):
                shadowing_sessions_completed = 0

            successor_signoff_confirmed = bool(
                item.get("successor_signoff_confirmed", False)
            )
            try:
                estimated_rampup_days = int(
                    item.get("estimated_rampup_days", 0) or 0
                )
            except (TypeError, ValueError):
                estimated_rampup_days = 0

            if (
                not has_architecture_walkthrough
                or not has_local_env_setup_guide
            ):
                incomplete_documentation_package_ids.append(pkg_id)

            if (
                shadowing_sessions_completed < 1
                or not successor_signoff_confirmed
            ):
                unverified_handover_package_ids.append(pkg_id)

            if estimated_rampup_days <= 0 or estimated_rampup_days > int(
                max_onboarding_days
            ):
                excessive_rampup_package_ids.append(pkg_id)

    return {
        "total_evaluated": total_evaluated,
        "incomplete_documentation_package_ids": incomplete_documentation_package_ids,
        "unverified_handover_package_ids": unverified_handover_package_ids,
        "excessive_rampup_package_ids": excessive_rampup_package_ids,
        "is_kt_handover_ready": (
            len(incomplete_documentation_package_ids) == 0
            and len(unverified_handover_package_ids) == 0
            and len(excessive_rampup_package_ids) == 0
        ),
    }


WikiPMIService.audit_wiki_onboarding_and_kt_handover_readiness = staticmethod(
    audit_wiki_onboarding_and_kt_handover_readiness
)


def audit_wiki_vendor_sla_and_penalty_clause_governance(
    sla_agreements: object,
) -> dict[str, object]:
    """Audita acuerdos de nivel de servicio (SLA) de proveedores, límites de disponibilidad/respuesta, cláusulas de penalización/créditos y telemetría automatizada en la Wiki según PMI PMBOK §12.1 y §12.2."""
    total_evaluated = 0
    invalid_target_bounds_sla_ids: list[str] = []
    toothless_penalty_clause_sla_ids: list[str] = []
    unmonitored_sla_ids: list[str] = []

    if isinstance(sla_agreements, Sequence) and not isinstance(
        sla_agreements, (str, bytes, bytearray)
    ):
        for item in sla_agreements:
            if not isinstance(item, Mapping):
                continue
            sla_id = str(item.get("sla_id") or item.get("id") or "").strip()
            if not sla_id:
                continue

            total_evaluated += 1
            try:
                uptime_target_pct = float(
                    item.get("uptime_target_pct", 0.0) or 0.0
                )
            except (TypeError, ValueError):
                uptime_target_pct = 0.0

            try:
                max_incident_response_minutes = int(
                    item.get("max_incident_response_minutes", 0) or 0
                )
            except (TypeError, ValueError):
                max_incident_response_minutes = 0

            has_service_credit_or_penalty_clause = bool(
                item.get("has_service_credit_or_penalty_clause", False)
            )
            breach_termination_threshold_defined = bool(
                item.get("breach_termination_threshold_defined", False)
            )
            measurement_telemetry_automated = bool(
                item.get("measurement_telemetry_automated", False)
            )

            if (
                uptime_target_pct < 95.0
                or uptime_target_pct > 100.0
                or max_incident_response_minutes <= 0
            ):
                invalid_target_bounds_sla_ids.append(sla_id)

            if (
                not has_service_credit_or_penalty_clause
                or not breach_termination_threshold_defined
            ):
                toothless_penalty_clause_sla_ids.append(sla_id)

            if not measurement_telemetry_automated:
                unmonitored_sla_ids.append(sla_id)

    return {
        "total_evaluated": total_evaluated,
        "invalid_target_bounds_sla_ids": invalid_target_bounds_sla_ids,
        "toothless_penalty_clause_sla_ids": toothless_penalty_clause_sla_ids,
        "unmonitored_sla_ids": unmonitored_sla_ids,
        "is_vendor_sla_governance_sound": (
            len(invalid_target_bounds_sla_ids) == 0
            and len(toothless_penalty_clause_sla_ids) == 0
            and len(unmonitored_sla_ids) == 0
        ),
    }


WikiPMIService.audit_wiki_vendor_sla_and_penalty_clause_governance = staticmethod(
    audit_wiki_vendor_sla_and_penalty_clause_governance
)

