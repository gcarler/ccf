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
    "audit_wiki_assumption_and_constraint_log_governance",
    "audit_wiki_issue_log_escalation_and_aging_sla",
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
    "audit_wiki_cost_of_quality_prevention_vs_failure_balance",
    "audit_wiki_communication_confidentiality_and_channel_security",
    "audit_wiki_lessons_learned_actionable_opa_transfer",
    "audit_wiki_risk_trigger_early_warning_and_fallback",
    "audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration",
    "audit_wiki_requirements_bidirectional_traceability_and_gold_plating",
    "audit_wiki_decision_log_daci_accountability_and_reversal",
    "audit_wiki_assumptions_and_constraints_empirical_validation",
    "audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness",
    "audit_wiki_communications_matrix_cadence_and_escalation",
    "audit_wiki_definition_of_ready_and_backlog_grooming",
    "audit_wiki_blameless_postmortem_and_systemic_prevention",
    "audit_wiki_opa_and_eef_catalog_freshness",
    "audit_wiki_adr_superseded_chain_and_consequences_hygiene",
    "audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness",
    "audit_wiki_communication_matrix_cadence_and_escalation",
    "audit_wiki_slo_error_budget_and_runbook_linkage",
    "audit_wiki_chaos_gameday_resilience_and_action_closure",
    "audit_wiki_api_deprecation_sunset_and_migration_readiness",
    "audit_wiki_operational_runbook_idempotency_and_preflight_hygiene",
    "audit_wiki_database_migration_expand_contract_and_lock_safety",
    "audit_wiki_blameless_postmortem_five_whys_and_action_sla",
    "audit_wiki_on_call_rotation_burnout_and_escalation_readiness",
    "audit_wiki_adr_immutability_and_superseded_chain_integrity",
    "audit_wiki_bus_factor_spok_and_cross_training_coverage",
    "audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene",
    "audit_wiki_quarterly_attestation_and_orphan_page_archival",
    "audit_wiki_dr_tabletop_exercise_and_communication_tree",
    "audit_wiki_api_deprecation_sunset_and_consumer_migration",
    "audit_wiki_runbook_automation_toil_and_idempotency",
    "audit_wiki_chaos_gameday_hypothesis_and_blast_radius",
    "audit_wiki_observability_cardinality_and_trace_sampling",
    "audit_wiki_service_catalog_ownership_and_dependency_graph",
    "audit_wiki_tls_certificate_expiration_and_acme_renewal",
    "audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction",
    "audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience",
    "audit_wiki_db_read_replica_lag_and_split_brain_fencing",
    "audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection",
    "audit_wiki_object_storage_worm_lock_and_ransomware_airgap",
    "audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover",
    "audit_wiki_secrets_vault_lease_rotation_and_root_token_seal",
    "audit_wiki_ntp_clock_drift_and_leap_second_smearing",
    "audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety",
    "audit_wiki_otel_tail_sampling_baggage_and_span_drop",
    "audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing",
    "audit_wiki_graph_backlink_reciprocity_and_orphan_clusters",
    "audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock",
    "audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle",
    "audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker",
    "audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio",
    "audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound",
    "audit_wiki_s3_erasure_coding_quorum_and_object_lock_worm",
    "audit_wiki_redis_cluster_hash_slot_coverage_and_aof_eviction",
    "audit_wiki_kms_envelope_key_rotation_and_hsm_tamper_seal",
    "audit_wiki_webhook_ssrf_cidr_blocklist_and_dns_rebinding_guard",
    "audit_wiki_outbox_cdc_debezium_connector_lag_and_tombstone_hygiene",
    "audit_wiki_sso_saml_oidc_assertion_signature_and_replay_guard",
    "audit_wiki_vector_rag_index_drift_and_acl_prefilter_guard",
    "audit_wiki_websocket_presence_backpressure_and_zombie_socket_hygiene",
    "audit_wiki_distributed_lock_fencing_token_and_split_brain_guard",
    "audit_wiki_graphql_query_depth_alias_budget_and_introspection_guard",
    "audit_wiki_presigned_url_ttl_and_bucket_public_acl_guard",
    "audit_wiki_fts_bm25_index_bloat_and_reindex_lock_guard",
    "audit_wiki_crdt_vector_clock_divergence_and_tombstone_gc_guard",
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



def audit_wiki_assumption_and_constraint_log_governance(
    log_entries: list[dict[str, object]],
    *,
    max_validation_cycle_days: int = 30,
) -> dict[str, object]:
    """Audita validación y vigencia (staleness) del registro de supuestos y restricciones en wikis según PMI PMBOK §4.1 y §11.2."""
    total_entries = 0
    assumption_count = 0
    constraint_count = 0
    invalid_type_entry_ids: list[str] = []
    unassigned_or_unscoped_entry_ids: list[str] = []
    unconverted_false_assumption_ids: list[str] = []
    stale_unreviewed_entry_ids: list[str] = []

    max_days = float(max_validation_cycle_days)
    entries: Sequence[Any] = (
        log_entries
        if isinstance(log_entries, Sequence)
        and not isinstance(log_entries, (str, bytes, bytearray, Mapping))
        else []
    )

    for item in entries:
        if not isinstance(item, Mapping):
            continue
        entry_id = str(item.get("entry_id") or "").strip()
        if not entry_id:
            continue

        total_entries += 1

        entry_type = str(item.get("entry_type") or "").strip().lower()
        if entry_type == "assumption":
            assumption_count += 1
        elif entry_type == "constraint":
            constraint_count += 1
        else:
            invalid_type_entry_ids.append(entry_id)

        owner_id = str(item.get("owner_id") or "").strip()
        impact_domain = str(item.get("impact_domain") or "").strip()
        if not owner_id or not impact_domain:
            unassigned_or_unscoped_entry_ids.append(entry_id)

        validation_status = str(item.get("validation_status") or "").strip().lower()
        converted_risk_id = str(item.get("converted_risk_id") or "").strip()

        if (
            entry_type == "assumption"
            and validation_status == "invalidated_false"
            and not converted_risk_id
        ):
            unconverted_false_assumption_ids.append(entry_id)

        try:
            days_since_last_review = float(item.get("days_since_last_review", 0) or 0)
        except (TypeError, ValueError):
            days_since_last_review = 0.0
        if (
            validation_status != "retired"
            and days_since_last_review > max_days
        ):
            stale_unreviewed_entry_ids.append(entry_id)

    is_assumption_log_compliant = bool(
        len(invalid_type_entry_ids) == 0
        and len(unassigned_or_unscoped_entry_ids) == 0
        and len(unconverted_false_assumption_ids) == 0
        and len(stale_unreviewed_entry_ids) == 0
    )

    return {
        "total_entries": total_entries,
        "assumption_count": assumption_count,
        "constraint_count": constraint_count,
        "invalid_type_entry_ids": invalid_type_entry_ids,
        "unassigned_or_unscoped_entry_ids": unassigned_or_unscoped_entry_ids,
        "unconverted_false_assumption_ids": unconverted_false_assumption_ids,
        "stale_unreviewed_entry_ids": stale_unreviewed_entry_ids,
        "is_assumption_log_compliant": is_assumption_log_compliant,
    }


WikiPMIService.audit_wiki_assumption_and_constraint_log_governance = staticmethod(
    audit_wiki_assumption_and_constraint_log_governance
)


def audit_wiki_cost_of_quality_prevention_vs_failure_balance(
    quality_ledger_items: list[dict[str, object]],
    *,
    min_conformance_share_pct: float = 65.0,
    max_external_failure_share_pct: float = 10.0,
) -> dict[str, object]:
    """Audita el balance del Costo de la Calidad (CoQ: prevención y evaluación vs fallas internas y externas) y la vinculación de acciones correctivas según PMI PMBOK §8.1 y §8.2."""
    valid_categories = {
        "prevention",
        "appraisal",
        "internal_failure",
        "external_failure",
    }

    try:
        min_conf_pct = float(min_conformance_share_pct)
    except (TypeError, ValueError):
        min_conf_pct = 65.0

    try:
        max_ext_fail_pct = float(max_external_failure_share_pct)
    except (TypeError, ValueError):
        max_ext_fail_pct = 10.0

    conformance_cost = 0.0
    nonconformance_cost = 0.0
    external_failure_cost = 0.0
    invalid_category_or_amount_ids: list[str] = []
    unlinked_failure_cost_ids: list[str] = []

    if isinstance(quality_ledger_items, Sequence) and not isinstance(
        quality_ledger_items, (str, bytes, bytearray)
    ):
        for item in quality_ledger_items:
            if not isinstance(item, Mapping):
                continue
            item_id = str(item.get("item_id") or item.get("id") or "").strip()
            if not item_id:
                continue

            coq_category = (
                str(item.get("coq_category") or "").strip().lower()
            )
            raw_amount = item.get("amount")
            if raw_amount is None or isinstance(raw_amount, bool):
                amount = -1.0
            else:
                try:
                    amount = float(raw_amount)
                except (TypeError, ValueError):
                    amount = -1.0

            if coq_category not in valid_categories or amount < 0.0:
                invalid_category_or_amount_ids.append(item_id)
                continue

            corrective_action_linked = bool(
                item.get("corrective_action_linked", False)
            )
            if coq_category in {"prevention", "appraisal"}:
                conformance_cost += amount
            else:
                nonconformance_cost += amount
                if coq_category == "external_failure":
                    external_failure_cost += amount
                if amount > 0.0 and not corrective_action_linked:
                    unlinked_failure_cost_ids.append(item_id)

    total_coq = round(conformance_cost + nonconformance_cost, 2)
    conformance_share_pct = (
        round((conformance_cost / total_coq) * 100.0, 2)
        if total_coq > 0.0
        else 100.0
    )
    external_failure_share_pct = (
        round((external_failure_cost / total_coq) * 100.0, 2)
        if total_coq > 0.0
        else 0.0
    )
    below_conformance_investment_threshold = (
        total_coq > 0.0 and conformance_share_pct < min_conf_pct
    )
    exceeds_external_failure_cap = (
        total_coq > 0.0 and external_failure_share_pct > max_ext_fail_pct
    )

    return {
        "total_coq": total_coq,
        "conformance_share_pct": conformance_share_pct,
        "external_failure_share_pct": external_failure_share_pct,
        "below_conformance_investment_threshold": below_conformance_investment_threshold,
        "exceeds_external_failure_cap": exceeds_external_failure_cap,
        "invalid_category_or_amount_ids": invalid_category_or_amount_ids,
        "unlinked_failure_cost_ids": unlinked_failure_cost_ids,
        "is_coq_balance_compliant": (
            len(invalid_category_or_amount_ids) == 0
            and len(unlinked_failure_cost_ids) == 0
            and not below_conformance_investment_threshold
            and not exceeds_external_failure_cap
        ),
    }


WikiPMIService.audit_wiki_cost_of_quality_prevention_vs_failure_balance = staticmethod(
    audit_wiki_cost_of_quality_prevention_vs_failure_balance
)


def audit_wiki_issue_log_escalation_and_aging_sla(
    issue_entries: list[dict[str, object]],
    *,
    critical_sla_days: int = 3,
    high_sla_days: int = 7,
) -> dict[str, object]:
    """Audita escalamiento de severidad, workarounds y SLA de resolución del Issue Log en wikis según PMI PMBOK §4.3 y §9.5."""
    total_issues = 0
    active_issue_count = 0
    invalid_issue_metadata_ids: list[str] = []
    unassigned_active_issue_ids: list[str] = []
    overdue_sla_issue_ids: list[str] = []
    unescalated_critical_blocker_ids: list[str] = []

    critical_sla = float(critical_sla_days)
    high_sla = float(high_sla_days)
    active_statuses = {"open", "in_progress", "escalated"}
    valid_severities = {"critical", "high", "medium", "low"}
    valid_statuses = {"open", "in_progress", "escalated", "resolved", "closed"}
    items: Sequence[Any] = (
        issue_entries
        if isinstance(issue_entries, Sequence)
        and not isinstance(issue_entries, (str, bytes, bytearray, Mapping))
        else []
    )

    for item in items:
        if not isinstance(item, Mapping):
            continue
        issue_id = str(item.get("issue_id") or "").strip()
        if not issue_id:
            continue

        total_issues += 1

        severity = str(item.get("severity") or "").strip().lower()
        status = str(item.get("status") or "").strip().lower()
        owner_id = str(item.get("owner_id") or "").strip()
        try:
            age_days = float(item.get("age_days", 0.0) or 0.0)
        except (TypeError, ValueError):
            age_days = 0.0
        workaround_documented = bool(item.get("workaround_documented", False))
        escalated_to_sponsor_or_ccb = bool(
            item.get("escalated_to_sponsor_or_ccb", False)
        )

        if (
            severity not in valid_severities
            or status not in valid_statuses
            or age_days < 0.0
        ):
            invalid_issue_metadata_ids.append(issue_id)
            continue

        if status in active_statuses:
            active_issue_count += 1

            if not owner_id:
                unassigned_active_issue_ids.append(issue_id)

            if severity == "critical" and age_days > critical_sla:
                overdue_sla_issue_ids.append(issue_id)
                if not escalated_to_sponsor_or_ccb or not workaround_documented:
                    unescalated_critical_blocker_ids.append(issue_id)

            if severity == "high" and age_days > high_sla:
                overdue_sla_issue_ids.append(issue_id)

    is_issue_log_sla_compliant = bool(
        len(invalid_issue_metadata_ids) == 0
        and len(unassigned_active_issue_ids) == 0
        and len(overdue_sla_issue_ids) == 0
        and len(unescalated_critical_blocker_ids) == 0
    )

    return {
        "total_issues": total_issues,
        "active_issue_count": active_issue_count,
        "invalid_issue_metadata_ids": invalid_issue_metadata_ids,
        "unassigned_active_issue_ids": unassigned_active_issue_ids,
        "overdue_sla_issue_ids": overdue_sla_issue_ids,
        "unescalated_critical_blocker_ids": unescalated_critical_blocker_ids,
        "is_issue_log_sla_compliant": is_issue_log_sla_compliant,
    }


WikiPMIService.audit_wiki_issue_log_escalation_and_aging_sla = staticmethod(
    audit_wiki_issue_log_escalation_and_aging_sla
)


def audit_wiki_communication_confidentiality_and_channel_security(
    communication_channels: list[dict[str, object]],
) -> dict[str, object]:
    """Audita la clasificación de confidencialidad, controles de cifrado/DLP, políticas de retención y exposición externa en los canales del Plan de Gestión de las Comunicaciones según PMI PMBOK §10.1 y §10.3."""
    valid_levels = {"public", "internal", "confidential", "restricted"}

    total_channels = 0
    invalid_classification_or_retention_ids: list[str] = []
    unprotected_sensitive_channel_ids: list[str] = []
    external_exposure_restricted_channel_ids: list[str] = []

    if isinstance(communication_channels, Sequence) and not isinstance(
        communication_channels, (str, bytes, bytearray)
    ):
        for item in communication_channels:
            if not isinstance(item, Mapping):
                continue
            channel_id = str(
                item.get("channel_id") or item.get("id") or ""
            ).strip()
            if not channel_id:
                continue

            total_channels += 1
            level = (
                str(item.get("confidentiality_level") or "").strip().lower()
            )
            raw_retention = item.get("retention_policy_days", 0)
            if raw_retention is None or isinstance(raw_retention, bool):
                retention_days = 0.0
            else:
                try:
                    retention_days = float(raw_retention)
                except (TypeError, ValueError):
                    retention_days = 0.0

            if level not in valid_levels or retention_days <= 0.0:
                invalid_classification_or_retention_ids.append(channel_id)
                continue

            encrypted = bool(item.get("encryption_at_rest_and_transit", False))
            guest_access = bool(
                item.get("external_guest_access_enabled", False)
            )
            dlp_enabled = bool(item.get("dlp_and_audit_logging_enabled", False))

            if level in {"confidential", "restricted"} and (
                not encrypted or not dlp_enabled
            ):
                unprotected_sensitive_channel_ids.append(channel_id)

            if level == "restricted" and guest_access:
                external_exposure_restricted_channel_ids.append(channel_id)

    return {
        "total_channels": total_channels,
        "invalid_classification_or_retention_ids": invalid_classification_or_retention_ids,
        "unprotected_sensitive_channel_ids": unprotected_sensitive_channel_ids,
        "external_exposure_restricted_channel_ids": external_exposure_restricted_channel_ids,
        "is_communication_security_compliant": (
            len(invalid_classification_or_retention_ids) == 0
            and len(unprotected_sensitive_channel_ids) == 0
            and len(external_exposure_restricted_channel_ids) == 0
        ),
    }


WikiPMIService.audit_wiki_communication_confidentiality_and_channel_security = staticmethod(
    audit_wiki_communication_confidentiality_and_channel_security
)


def audit_wiki_lessons_learned_actionable_opa_transfer(
    lessons_entries: list[dict[str, object]],
) -> dict[str, object]:
    """PMBOK §4.4 / §12.3 — auditoría de recomendaciones accionables y transferencia a OPA de lecciones aprendidas."""
    if not isinstance(lessons_entries, Sequence) or isinstance(
        lessons_entries, (str, bytes)
    ):
        return {
            "total_lessons": 0,
            "captured_only_at_closure_anti_pattern": False,
            "invalid_phase_lesson_ids": [],
            "vague_or_incomplete_lesson_ids": [],
            "untransferred_opa_lesson_ids": [],
            "is_lessons_learned_governance_compliant": True,
        }

    valid_phases = {
        "initiating",
        "planning",
        "executing",
        "monitoring_controlling",
        "closing",
    }

    total_lessons = 0
    invalid_phase_lesson_ids: list[str] = []
    vague_or_incomplete_lesson_ids: list[str] = []
    untransferred_opa_lesson_ids: list[str] = []
    valid_phase_list: list[str] = []

    for item in lessons_entries:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("lesson_id")
        if raw_id is None:
            continue
        lesson_id = str(raw_id).strip()
        if not lesson_id:
            continue

        total_lessons += 1

        phase = str(item.get("phase_captured") or "").strip().lower()
        if phase not in valid_phases:
            invalid_phase_lesson_ids.append(lesson_id)
            continue

        valid_phase_list.append(phase)

        rc_context = str(item.get("root_cause_context") or "").strip()
        recommendation = str(item.get("actionable_recommendation") or "").strip()
        if len(rc_context) < 10 or len(recommendation) < 10:
            vague_or_incomplete_lesson_ids.append(lesson_id)

        opa_updated = bool(item.get("opa_template_updated", False))
        raw_owner = item.get("assigned_follow_up_owner_id")
        owner_id = str(raw_owner).strip() if raw_owner is not None else ""
        if not opa_updated and not owner_id:
            untransferred_opa_lesson_ids.append(lesson_id)

    captured_only_at_closure_anti_pattern = (
        len(valid_phase_list) >= 3
        and all(p == "closing" for p in valid_phase_list)
    )

    return {
        "total_lessons": total_lessons,
        "captured_only_at_closure_anti_pattern": captured_only_at_closure_anti_pattern,
        "invalid_phase_lesson_ids": invalid_phase_lesson_ids,
        "vague_or_incomplete_lesson_ids": vague_or_incomplete_lesson_ids,
        "untransferred_opa_lesson_ids": untransferred_opa_lesson_ids,
        "is_lessons_learned_governance_compliant": (
            len(invalid_phase_lesson_ids) == 0
            and len(vague_or_incomplete_lesson_ids) == 0
            and len(untransferred_opa_lesson_ids) == 0
            and not captured_only_at_closure_anti_pattern
        ),
    }


WikiPMIService.audit_wiki_lessons_learned_actionable_opa_transfer = staticmethod(
    audit_wiki_lessons_learned_actionable_opa_transfer
)


def audit_wiki_risk_trigger_early_warning_and_fallback(
    risk_triggers: list[dict[str, Any]],
) -> dict[str, Any]:
    """PMBOK §11.7 / §11.2 — auditoría de indicadores de alerta temprana (EWI) y activación de fallback."""
    if not isinstance(risk_triggers, Sequence) or isinstance(
        risk_triggers, (str, bytes)
    ):
        return {
            "total_monitored_risks": 0,
            "compliant_risks_count": 0,
            "missing_trigger_or_owner_count": 0,
            "breached_triggers_count": 0,
            "unactivated_breached_trigger_count": 0,
            "failed_primary_without_fallback_count": 0,
            "ewi_governance_status": "HEALTHY",
            "violations": [],
        }

    total_monitored_risks = 0
    compliant_risks_count = 0
    missing_trigger_or_owner_count = 0
    breached_triggers_count = 0
    unactivated_breached_trigger_count = 0
    failed_primary_without_fallback_count = 0
    violations: list[dict[str, Any]] = []

    for item in risk_triggers:
        if not isinstance(item, Mapping):
            continue
        raw_id = item.get("risk_id")
        if raw_id is None:
            continue
        risk_id = str(raw_id).strip()
        if not risk_id:
            continue

        total_monitored_risks += 1

        trigger_defined = bool(item.get("trigger_condition_defined", False))
        owner_assigned = bool(item.get("risk_owner_assigned", False))
        breached = bool(item.get("trigger_breached", False))
        primary_activated = bool(item.get("primary_response_activated", False))
        primary_effective = bool(item.get("primary_response_effective", False))
        fallback_documented = bool(item.get("fallback_plan_documented", False))
        fallback_activated = bool(item.get("fallback_plan_activated", False))

        if breached:
            breached_triggers_count += 1

        missing_trigger_or_owner = (not trigger_defined) or (not owner_assigned)
        unactivated_breached_trigger = breached and (not primary_activated)
        failed_primary_without_fallback = (
            breached
            and primary_activated
            and (not primary_effective)
            and ((not fallback_documented) or (not fallback_activated))
        )

        reasons: list[str] = []
        if missing_trigger_or_owner:
            missing_trigger_or_owner_count += 1
            reasons.append("missing_trigger_or_owner")
        if unactivated_breached_trigger:
            unactivated_breached_trigger_count += 1
            reasons.append("unactivated_breached_trigger")
        if failed_primary_without_fallback:
            failed_primary_without_fallback_count += 1
            reasons.append("failed_primary_without_fallback")

        if not reasons:
            compliant_risks_count += 1
        else:
            violations.append({"risk_id": risk_id, "reasons": reasons})

    if (
        missing_trigger_or_owner_count == 0
        and unactivated_breached_trigger_count == 0
        and failed_primary_without_fallback_count == 0
    ):
        status = "HEALTHY"
    elif (
        unactivated_breached_trigger_count > 0
        or failed_primary_without_fallback_count > 0
    ):
        status = "CRITICAL"
    else:
        status = "AT_RISK"

    return {
        "total_monitored_risks": total_monitored_risks,
        "compliant_risks_count": compliant_risks_count,
        "missing_trigger_or_owner_count": missing_trigger_or_owner_count,
        "breached_triggers_count": breached_triggers_count,
        "unactivated_breached_trigger_count": unactivated_breached_trigger_count,
        "failed_primary_without_fallback_count": failed_primary_without_fallback_count,
        "ewi_governance_status": status,
        "violations": violations,
    }


WikiPMIService.audit_wiki_risk_trigger_early_warning_and_fallback = staticmethod(
    audit_wiki_risk_trigger_early_warning_and_fallback
)




def audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration(
    knowledge_domains: list[dict],
    *,
    min_bus_factor: int = 2,
    max_sme_edit_share_pct: float = 80.0,
    max_days_without_peer_review: int = 45,
) -> dict:
    """Audita bus factor y concentración SME del conocimiento en la wiki (PMBOK §4.4 y §9.4).

    Cada dominio aporta domain_id, qualified_contributors_count,
    primary_author_edit_share_pct, shadowing_or_cross_training_completed,
    runbook_documented y days_since_last_peer_review:
    - spof: contributores calificados < min_bus_factor sin shadowing.
    - sme_silo: concentración de ediciones del autor primario > limit
      sin shadowing.
    - missing_runbook_or_stale_review: runbook ausente o revisión por
      pares vencida (> max días).
    - knowledge_resilience_pct: % de dominios sin anomalías (2 dec, 100.0
      si vacío); bus_factor_governance_status HEALTHY/CRITICAL/AT_RISK;
      violations con {domain_id, reasons}.
    """
    if not isinstance(knowledge_domains, list):
        knowledge_domains = []
    domains = [d for d in knowledge_domains if isinstance(d, dict)]

    total_domains = len(domains)
    resilient_domains_count = 0
    spof_domains_count = 0
    sme_silo_domains_count = 0
    missing_runbook_or_stale_review_count = 0
    violations: list[dict] = []

    for idx, domain in enumerate(domains, start=1):
        domain_id = str(domain.get("domain_id", f"DOMAIN-{idx}"))
        reasons: list[str] = []
        has_spof = False
        has_sme_silo = False
        has_missing_runbook_or_stale_review = False

        shadowing = bool(domain.get("shadowing_or_cross_training_completed", False))
        raw_contributors = domain.get("qualified_contributors_count")
        try:
            contributors = int(raw_contributors if raw_contributors is not None else 0)
        except (TypeError, ValueError):
            contributors = 0
        raw_share = domain.get("primary_author_edit_share_pct")
        try:
            primary_share = float(raw_share if raw_share is not None else 0.0)
        except (TypeError, ValueError):
            primary_share = 0.0
        raw_days = domain.get("days_since_last_peer_review")
        try:
            days_since_review = int(raw_days if raw_days is not None else 0)
        except (TypeError, ValueError):
            days_since_review = 0

        if contributors < int(min_bus_factor) and not shadowing:
            has_spof = True
            reasons.append(
                f"SPOF_BUS_FACTOR ({contributors}<{min_bus_factor}, sin shadowing)"
            )
        if primary_share > float(max_sme_edit_share_pct) and not shadowing:
            has_sme_silo = True
            reasons.append(
                f"SME_SILO ({primary_share}>{max_sme_edit_share_pct}, sin shadowing)"
            )
        if (not bool(domain.get("runbook_documented", False))) or days_since_review > int(
            max_days_without_peer_review
        ):
            has_missing_runbook_or_stale_review = True
            if not domain.get("runbook_documented", False):
                reasons.append("RUNBOOK_MISSING")
            if days_since_review > int(max_days_without_peer_review):
                reasons.append(
                    f"PEER_REVIEW_STALE ({days_since_review}>{max_days_without_peer_review})"
                )

        if has_spof:
            spof_domains_count += 1
        if has_sme_silo:
            sme_silo_domains_count += 1
        if has_missing_runbook_or_stale_review:
            missing_runbook_or_stale_review_count += 1
        if not (has_spof or has_sme_silo or has_missing_runbook_or_stale_review):
            resilient_domains_count += 1
        if reasons:
            violations.append({"domain_id": domain_id, "reasons": reasons})

    knowledge_resilience_pct = (
        round(resilient_domains_count / total_domains * 100.0, 2) if total_domains > 0 else 100.0
    )
    bus_factor_governance_status = (
        "CRITICAL"
        if spof_domains_count > 0
        else (
            "AT_RISK"
            if sme_silo_domains_count > 0 or missing_runbook_or_stale_review_count > 0
            else "HEALTHY"
        )
    )

    return {
        "total_domains": total_domains,
        "resilient_domains_count": resilient_domains_count,
        "spof_domains_count": spof_domains_count,
        "sme_silo_domains_count": sme_silo_domains_count,
        "missing_runbook_or_stale_review_count": missing_runbook_or_stale_review_count,
        "knowledge_resilience_pct": knowledge_resilience_pct,
        "bus_factor_governance_status": bus_factor_governance_status,
        "violations": violations,
    }


WikiPMIService.audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration = staticmethod(
    audit_wiki_knowledge_transfer_bus_factor_and_sme_concentration
)


def audit_wiki_requirements_bidirectional_traceability_and_gold_plating(
    requirements_trace_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audita trazabilidad bidireccional RTM y detecta gold-plating / alcance huerfano (PMBOK §5.2, §5.6)."""
    if not isinstance(requirements_trace_items, list):
        requirements_trace_items = []

    total_items = 0
    fully_traced_items_count = 0
    unverified_or_unbuilt_requirements_count = 0
    gold_plating_or_orphan_scope_count = 0
    violations: list[dict[str, Any]] = []

    for raw in requirements_trace_items:
        if not isinstance(raw, dict):
            continue
        total_items += 1
        item_id = str(raw.get("item_id") or "").strip() or f"REQ-{total_items}"
        linked_business_objective_id = raw.get("linked_business_objective_id")
        linked_wbs_deliverable_id = raw.get("linked_wbs_deliverable_id")
        linked_test_case_id = raw.get("linked_test_case_id")
        ccb_approved_baseline = raw.get("ccb_approved_baseline")

        has_wbs = bool(str(linked_wbs_deliverable_id or "").strip())
        has_test = bool(str(linked_test_case_id or "").strip())
        has_obj = bool(str(linked_business_objective_id or "").strip())
        has_ccb = bool(ccb_approved_baseline)

        forward_gap = (not has_wbs) or (not has_test)
        gold_plating_or_orphan = (not has_obj) or (not has_ccb)

        reasons: list[str] = []
        if not has_wbs:
            reasons.append("missing_linked_wbs_deliverable_id")
        if not has_test:
            reasons.append("missing_linked_test_case_id")
        if not has_obj:
            reasons.append("missing_linked_business_objective_id")
        if not has_ccb:
            reasons.append("unapproved_ccb_baseline_gold_plating")

        if forward_gap:
            unverified_or_unbuilt_requirements_count += 1
        if gold_plating_or_orphan:
            gold_plating_or_orphan_scope_count += 1

        if not forward_gap and not gold_plating_or_orphan:
            fully_traced_items_count += 1
        else:
            violations.append(
                {
                    "item_id": item_id,
                    "reasons": reasons,
                }
            )

    bidirectional_traceability_pct = (
        round((fully_traced_items_count / total_items) * 100.0, 2)
        if total_items > 0
        else 100.0
    )
    if (
        unverified_or_unbuilt_requirements_count == 0
        and gold_plating_or_orphan_scope_count == 0
    ):
        traceability_governance_status = "HEALTHY"
    elif gold_plating_or_orphan_scope_count > 0:
        traceability_governance_status = "CRITICAL"
    else:
        traceability_governance_status = "AT_RISK"

    return {
        "total_items": total_items,
        "fully_traced_items_count": fully_traced_items_count,
        "unverified_or_unbuilt_requirements_count": unverified_or_unbuilt_requirements_count,
        "gold_plating_or_orphan_scope_count": gold_plating_or_orphan_scope_count,
        "bidirectional_traceability_pct": bidirectional_traceability_pct,
        "traceability_governance_status": traceability_governance_status,
        "violations": violations,
    }


WikiPMIService.audit_wiki_requirements_bidirectional_traceability_and_gold_plating = staticmethod(
    audit_wiki_requirements_bidirectional_traceability_and_gold_plating
)



def audit_wiki_decision_log_daci_accountability_and_reversal(
    decisions: list[dict],
    *,
    max_pending_decision_days: int = 10,
) -> dict:
    """Audita gobernanza DACI/RACI y reversiones en la bitácora de decisiones (PMBOK §4.4 y §9.1).

    Cada decisión aporta decision_id, status, approvers_count,
    driver_assigned, alternatives_documented_count, days_pending,
    was_reversed y reversal_impact_documented:
    - ambiguous_accountability: approvers_count != 1 o sin driver.
    - stalled_or_unjustified: PENDING con días > SLA o menos de 2
      alternativas documentadas.
    - undocumented_reversal: decisión revertida sin impacto documentado.
    - decision_governance_status: 'HEALTHY' sin hallazgos; 'CRITICAL'
      con ambigüedad de responsabilidad o reversiones sin documentar;
      'AT_RISK' en otro caso; violations con {decision_id, reasons}.
    """
    if not isinstance(decisions, list):
        decisions = []
    rows = [d for d in decisions if isinstance(d, dict)]

    total_decisions = len(rows)
    compliant_decisions_count = 0
    ambiguous_accountability_count = 0
    stalled_or_unjustified_decisions_count = 0
    undocumented_reversals_count = 0
    violations: list[dict] = []

    for idx, row in enumerate(rows, start=1):
        decision_id = str(row.get("decision_id", f"DECISION-{idx}"))
        reasons: list[str] = []
        has_ambiguous = False
        has_stalled = False
        has_unreversed_doc = False

        status = str(row.get("status") or "").strip().upper()
        raw_approvers = row.get("approvers_count")
        try:
            approvers = int(raw_approvers if raw_approvers is not None else 0)
        except (TypeError, ValueError):
            approvers = 0
        raw_alternatives = row.get("alternatives_documented_count")
        try:
            alternatives = int(raw_alternatives if raw_alternatives is not None else 0)
        except (TypeError, ValueError):
            alternatives = 0
        raw_days = row.get("days_pending")
        try:
            days_pending = int(raw_days if raw_days is not None else 0)
        except (TypeError, ValueError):
            days_pending = 0
        driver_assigned = bool(row.get("driver_assigned", False))
        was_reversed = bool(row.get("was_reversed", False))
        reversal_documented = bool(row.get("reversal_impact_documented", False))

        if approvers != 1 or not driver_assigned:
            has_ambiguous = True
            if approvers != 1:
                reasons.append(f"DACI_APPROVERS_COUNT_AMBIGUOUS ({approvers} != 1)")
            if not driver_assigned:
                reasons.append("DACI_DRIVER_NO_ASSIGNED")

        if (status == "PENDING" and days_pending > int(max_pending_decision_days)) or alternatives < 2:
            has_stalled = True
            if status == "PENDING" and days_pending > int(max_pending_decision_days):
                reasons.append(
                    f"PENDING_STALLED ({days_pending}>{max_pending_decision_days})",
                )
            if alternatives < 2:
                reasons.append(f"ALTERNATIVES_UNDERDOCUMENTED ({alternatives}<2)")

        if was_reversed and not reversal_documented:
            has_unreversed_doc = True
            reasons.append("REVERSAL_IMPACT_UNDOCUMENTED")

        if has_ambiguous:
            ambiguous_accountability_count += 1
        if has_stalled:
            stalled_or_unjustified_decisions_count += 1
        if has_unreversed_doc:
            undocumented_reversals_count += 1
        if not (has_ambiguous or has_stalled or has_unreversed_doc):
            compliant_decisions_count += 1
        if reasons:
            violations.append({"decision_id": decision_id, "reasons": reasons})

    decision_governance_status = (
        "CRITICAL"
        if ambiguous_accountability_count > 0 or undocumented_reversals_count > 0
        else (
            "AT_RISK"
            if stalled_or_unjustified_decisions_count > 0
            else "HEALTHY"
        )
    )

    return {
        "total_decisions": total_decisions,
        "compliant_decisions_count": compliant_decisions_count,
        "ambiguous_accountability_count": ambiguous_accountability_count,
        "stalled_or_unjustified_decisions_count": stalled_or_unjustified_decisions_count,
        "undocumented_reversals_count": undocumented_reversals_count,
        "decision_governance_status": decision_governance_status,
        "violations": violations,
    }


WikiPMIService.audit_wiki_decision_log_daci_accountability_and_reversal = staticmethod(
    audit_wiki_decision_log_daci_accountability_and_reversal
)


def audit_wiki_assumptions_and_constraints_empirical_validation(
    assumption_entries: Sequence[Mapping[str, Any]] | None,
    *,
    max_unvalidated_days: int = 21,
    require_validation_method: bool = True,
    require_risk_or_cr_on_false: bool = True,
) -> dict[str, Any]:
    """Audita validación empírica de supuestos y conversión de supuestos invalidados a riesgos/CR según PMI PMBOK §11.2 y §5.3."""
    if (
        assumption_entries is None
        or isinstance(assumption_entries, (str, bytes))
        or not isinstance(assumption_entries, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = assumption_entries

    try:
        max_days = int(max_unvalidated_days)
    except (TypeError, ValueError):
        max_days = 21

    total_entries = 0
    compliant_entries = 0
    validated_or_intact_count = 0

    unowned_or_missing_method_ids: list[str] = []
    stale_unvalidated_assumption_ids: list[str] = []
    unconverted_invalidated_assumption_ids: list[str] = []
    breached_constraint_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_entries += 1

        assumption_id = (
            str(raw.get("id") or raw.get("assumption_id") or "").strip()
            or "ASM-UNKNOWN"
        )
        entry_type = (
            str(raw.get("entry_type") or "assumption").strip().lower()
            or "assumption"
        )
        validation_status = (
            str(raw.get("validation_status") or "unvalidated").strip().lower()
        )

        try:
            days_open = max(0, int(raw.get("days_open") or 0))
        except (TypeError, ValueError):
            days_open = 0

        owner = str(raw.get("owner") or "").strip()
        validation_method = str(raw.get("validation_method") or "").strip()
        linked_risk_or_cr_id = str(raw.get("linked_risk_or_cr_id") or "").strip()

        raw_buf = raw.get("constraint_buffer_pct")
        try:
            constraint_buffer_pct = (
                float(raw_buf) if raw_buf is not None else 10.0
            )
        except (TypeError, ValueError):
            constraint_buffer_pct = 10.0

        is_unowned_or_missing_method = (not owner) or (
            bool(require_validation_method)
            and entry_type == "assumption"
            and not validation_method
        )
        is_stale_unvalidated = (
            entry_type == "assumption"
            and validation_status == "unvalidated"
            and days_open > max_days
        )
        is_unconverted_invalidated = (
            validation_status == "invalidated_false"
            and bool(require_risk_or_cr_on_false)
            and not linked_risk_or_cr_id
        )
        is_breached_constraint = (
            entry_type == "constraint" and constraint_buffer_pct < 0.0
        )

        if is_unowned_or_missing_method:
            unowned_or_missing_method_ids.append(assumption_id)
        if is_stale_unvalidated:
            stale_unvalidated_assumption_ids.append(assumption_id)
        if is_unconverted_invalidated:
            unconverted_invalidated_assumption_ids.append(assumption_id)
        if is_breached_constraint:
            breached_constraint_ids.append(assumption_id)

        if (
            not is_unowned_or_missing_method
            and not is_stale_unvalidated
            and not is_unconverted_invalidated
            and not is_breached_constraint
        ):
            compliant_entries += 1

        if validation_status in {"validated_true", "invalidated_false"} or (
            entry_type == "constraint" and constraint_buffer_pct >= 0.0
        ):
            validated_or_intact_count += 1

    validation_rate_pct = (
        100.0
        if total_entries == 0
        else round((validated_or_intact_count / total_entries) * 100.0, 2)
    )

    is_compliant = (
        len(unowned_or_missing_method_ids) == 0
        and len(stale_unvalidated_assumption_ids) == 0
        and len(unconverted_invalidated_assumption_ids) == 0
        and len(breached_constraint_ids) == 0
    )

    if is_compliant:
        governance_health = "healthy"
    elif (
        len(unconverted_invalidated_assumption_ids) > 0
        or len(breached_constraint_ids) > 0
    ):
        governance_health = "critical"
    else:
        governance_health = "at_risk"

    recommendations: list[str] = []
    if unowned_or_missing_method_ids:
        recommendations.append(
            f"Asignar propietario (owner) y método de validación empírica (validation_method) en {unowned_or_missing_method_ids}."
        )
    if stale_unvalidated_assumption_ids:
        recommendations.append(
            f"Ejecutar validación empírica de supuestos abiertos por más de {max_days} días en {stale_unvalidated_assumption_ids}."
        )
    if unconverted_invalidated_assumption_ids:
        recommendations.append(
            f"Convertir supuestos demostrados falsos {unconverted_invalidated_assumption_ids} en riesgos activos o solicitudes de cambio CCB (linked_risk_or_cr_id)."
        )
    if breached_constraint_ids:
        recommendations.append(
            f"Escalar violación de restricciones duras (constraint_buffer_pct < 0) en {breached_constraint_ids} al comité de control de cambios."
        )

    return {
        "total_entries": total_entries,
        "compliant_entries": compliant_entries,
        "unowned_or_missing_method_ids": unowned_or_missing_method_ids,
        "stale_unvalidated_assumption_ids": stale_unvalidated_assumption_ids,
        "unconverted_invalidated_assumption_ids": unconverted_invalidated_assumption_ids,
        "breached_constraint_ids": breached_constraint_ids,
        "validation_rate_pct": validation_rate_pct,
        "governance_health": governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_assumptions_and_constraints_empirical_validation = staticmethod(
    audit_wiki_assumptions_and_constraints_empirical_validation
)


def audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness(
    runbooks: Sequence[Mapping[str, Any]] | None,
    *,
    max_days_since_drill: int = 90,
) -> dict[str, Any]:
    """PMI PMBOK 4.4 & 11.5 — preparación de runbooks y playbooks de contingencia.

    Auditoría pura sobre la lista ``runbooks``. Entradas no-lista/``None`` se
    tratan como lista vacía y los elementos no-dict se ignoran. Para cada
    runbook se verifican:

    1. ``rto_or_rpo_sla_breach``: ``target_rto_minutes <= 0`` OR
       ``target_rpo_minutes < 0`` OR ``measured_drill_rto_minutes >
       target_rto_minutes`` OR ``measured_drill_rpo_minutes >
       target_rpo_minutes``.
    2. ``stale_or_untested_drill``: ``days_since_last_drill < 0`` OR
       ``days_since_last_drill > max_days_since_drill``.
    3. ``missing_rollback_or_escalation``: ``not rollback_steps_documented``
       OR ``not oncall_escalation_assigned``.

    Retorna total_runbooks, compliant_runbooks_count, los 3 conteos de
    violación, runbook_readiness_status (HEALTHY/AT_RISK/CRITICAL) y
    ``violations`` (lista de dicts con ``runbook_id`` y ``reasons``).
    """
    items = runbooks if isinstance(runbooks, list) else []

    total = 0
    breach_count = 0
    stale_count = 0
    missing_count = 0
    compliant_count = 0
    violations: list[dict[str, Any]] = []

    for entry in items:
        if not isinstance(entry, Mapping):
            continue
        total += 1

        runbook_id = entry.get("runbook_id")
        reasons: list[str] = []

        target_rto = entry.get("target_rto_minutes")
        target_rpo = entry.get("target_rpo_minutes")
        measured_rto = entry.get("measured_drill_rto_minutes")
        measured_rpo = entry.get("measured_drill_rpo_minutes")

        if target_rto is not None and target_rto <= 0:
            reasons.append("rto_or_rpo_sla_breach")
        if target_rpo is not None and target_rpo < 0:
            reasons.append("rto_or_rpo_sla_breach")
        if (
            measured_rto is not None
            and target_rto is not None
            and measured_rto > target_rto
        ):
            reasons.append("rto_or_rpo_sla_breach")
        if (
            measured_rpo is not None
            and target_rpo is not None
            and measured_rpo > target_rpo
        ):
            reasons.append("rto_or_rpo_sla_breach")

        days_since = entry.get("days_since_last_drill")
        if days_since is not None and (
            days_since < 0 or days_since > max_days_since_drill
        ):
            reasons.append("stale_or_untested_drill")

        if not entry.get("rollback_steps_documented") or not entry.get(
            "oncall_escalation_assigned"
        ):
            reasons.append("missing_rollback_or_escalation")

        # Dedup preservando orden de primeras apariciones.
        ordered_reasons = list(dict.fromkeys(reasons))
        if not ordered_reasons:
            compliant_count += 1
            continue

        if "rto_or_rpo_sla_breach" in ordered_reasons:
            breach_count += 1
        if "stale_or_untested_drill" in ordered_reasons:
            stale_count += 1
        if "missing_rollback_or_escalation" in ordered_reasons:
            missing_count += 1

        violations.append(
            {
                "runbook_id": runbook_id,
                "reasons": ordered_reasons,
            }
        )

    if breach_count > 0 or missing_count > 0:
        status = "CRITICAL"
    elif stale_count > 0:
        status = "AT_RISK"
    else:
        status = "HEALTHY"

    return {
        "total_runbooks": total,
        "compliant_runbooks_count": compliant_count,
        "rto_or_rpo_sla_breach_count": breach_count,
        "stale_or_untested_drill_count": stale_count,
        "missing_rollback_or_escalation_count": missing_count,
        "runbook_readiness_status": status,
        "violations": violations,
    }


WikiPMIService.audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness = staticmethod(
    audit_wiki_runbook_incident_playbook_and_rto_rpo_readiness
)


def audit_wiki_communications_matrix_cadence_and_escalation(
    comm_artifacts: Sequence[Mapping[str, Any]] | None,
    *,
    max_delivery_delay_days: int = 3,
    min_interactive_ack_rate_pct: float = 80.0,
) -> dict[str, Any]:
    """Audita la Matriz de Gestión de Comunicaciones en Wiki: definición de método (interactive/push/pull), responsable, audiencia, ruta de escalamiento, adherencia a cadencia y tasa de confirmación interactiva (PMI PMBOK §10.1 y §10.3)."""
    if (
        comm_artifacts is None
        or isinstance(comm_artifacts, (str, bytes))
        or not isinstance(comm_artifacts, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = comm_artifacts

    try:
        max_delay = int(max_delivery_delay_days)
    except (TypeError, ValueError):
        max_delay = 3

    try:
        min_ack_pct = float(min_interactive_ack_rate_pct)
    except (TypeError, ValueError):
        min_ack_pct = 80.0

    allowed_methods = {"interactive", "push", "pull"}

    total_artifacts = 0
    compliant_artifacts = 0
    incomplete_matrix_definition_ids: list[str] = []
    cadence_delivery_overdue_ids: list[str] = []
    low_interactive_engagement_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_artifacts += 1

        comm_id = (
            str(raw.get("id") or raw.get("comm_id") or "").strip()
            or "COM-UNKNOWN"
        )
        method = str(raw.get("method") or "").strip().lower()
        sender_owner = str(raw.get("sender_owner") or "").strip()
        target_audience = str(raw.get("target_audience") or "").strip()
        escalation_path_defined = bool(raw.get("escalation_path_defined"))

        try:
            delivery_delay_days = max(
                0, int(raw.get("delivery_delay_days") or 0)
            )
        except (TypeError, ValueError):
            delivery_delay_days = 0

        raw_ack = raw.get("recipient_ack_rate_pct")
        if raw_ack is None:
            recipient_ack_rate_pct = 100.0
        else:
            try:
                recipient_ack_rate_pct = max(
                    0.0, min(100.0, float(raw_ack))
                )
            except (TypeError, ValueError):
                recipient_ack_rate_pct = 100.0

        is_incomplete = (
            not sender_owner
            or not target_audience
            or method not in allowed_methods
            or not escalation_path_defined
        )
        is_overdue = delivery_delay_days > max_delay
        is_low_ack = (
            method == "interactive" and recipient_ack_rate_pct < min_ack_pct
        )

        if is_incomplete:
            incomplete_matrix_definition_ids.append(comm_id)
        if is_overdue:
            cadence_delivery_overdue_ids.append(comm_id)
        if is_low_ack:
            low_interactive_engagement_ids.append(comm_id)

        if not is_incomplete and not is_overdue and not is_low_ack:
            compliant_artifacts += 1

    is_compliant = (
        len(incomplete_matrix_definition_ids) == 0
        and len(cadence_delivery_overdue_ids) == 0
        and len(low_interactive_engagement_ids) == 0
    )

    if is_compliant:
        communications_governance_health = "healthy"
    elif len(incomplete_matrix_definition_ids) > 0:
        communications_governance_health = "critical"
    else:
        communications_governance_health = "at_risk"

    recommendations: list[str] = []
    if incomplete_matrix_definition_ids:
        recommendations.append(
            f"Completar responsable emisor, audiencia, método canónico (interactive/push/pull) y ruta de escalamiento en {incomplete_matrix_definition_ids}."
        )
    if cadence_delivery_overdue_ids:
        recommendations.append(
            f"Regularizar retrasos en la cadencia de distribución (> {max_delay} días) en {cadence_delivery_overdue_ids}."
        )
    if low_interactive_engagement_ids:
        recommendations.append(
            f"Reforzar participación y confirmación de receptores (>= {min_ack_pct}%) en canales interactivos de {low_interactive_engagement_ids}."
        )

    return {
        "total_artifacts": total_artifacts,
        "compliant_artifacts": compliant_artifacts,
        "incomplete_matrix_definition_ids": incomplete_matrix_definition_ids,
        "cadence_delivery_overdue_ids": cadence_delivery_overdue_ids,
        "low_interactive_engagement_ids": low_interactive_engagement_ids,
        "communications_governance_health": communications_governance_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_communications_matrix_cadence_and_escalation = staticmethod(
    audit_wiki_communications_matrix_cadence_and_escalation
)


def audit_wiki_definition_of_ready_and_backlog_grooming(
    backlog_candidates: Sequence[Mapping[str, Any]] | None,
    *,
    max_story_points_for_sprint: int = 13,
    min_acceptance_criteria_count: int = 2,
) -> dict[str, Any]:
    """Audita el cumplimiento de Definition of Ready (DoR) y refinamiento de backlog (criterios INVEST: tamaño/estimación en Story Points, criterios de aceptación verificables, enlace a especificación y ausencia de bloqueos al comprometer al sprint) (PMI Agile Practice Guide y PMBOK §5.3 / §6.2)."""
    if (
        backlog_candidates is None
        or isinstance(backlog_candidates, (str, bytes))
        or not isinstance(backlog_candidates, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = backlog_candidates

    try:
        max_pts = int(max_story_points_for_sprint)
    except (TypeError, ValueError):
        max_pts = 13

    try:
        min_ac = int(min_acceptance_criteria_count)
    except (TypeError, ValueError):
        min_ac = 2

    total_candidates = 0
    ready_candidates = 0

    unestimated_or_oversized_epic_ids: list[str] = []
    insufficient_acceptance_criteria_or_spec_ids: list[str] = []
    blocked_item_committed_to_sprint_ids: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_candidates += 1

        item_id = (
            str(raw.get("id") or raw.get("item_id") or "").strip()
            or "BKL-UNKNOWN"
        )
        committed_to_sprint = bool(raw.get("committed_to_sprint"))

        try:
            story_points = max(0, int(raw.get("story_points") or 0))
        except (TypeError, ValueError):
            story_points = 0

        try:
            acceptance_criteria_count = max(
                0, int(raw.get("acceptance_criteria_count") or 0)
            )
        except (TypeError, ValueError):
            acceptance_criteria_count = 0

        try:
            blocking_dependencies_count = max(
                0, int(raw.get("blocking_dependencies_count") or 0)
            )
        except (TypeError, ValueError):
            blocking_dependencies_count = 0

        ux_or_arch_spec_linked = bool(raw.get("ux_or_arch_spec_linked"))

        is_unestimated_or_oversized = (
            story_points <= 0 or story_points > max_pts
        )
        is_insufficient_ac_or_spec = (
            acceptance_criteria_count < min_ac or not ux_or_arch_spec_linked
        )
        is_blocked_committed = committed_to_sprint and (
            blocking_dependencies_count > 0
            or story_points <= 0
            or acceptance_criteria_count < min_ac
        )

        if is_unestimated_or_oversized:
            unestimated_or_oversized_epic_ids.append(item_id)
        if is_insufficient_ac_or_spec:
            insufficient_acceptance_criteria_or_spec_ids.append(item_id)
        if is_blocked_committed:
            blocked_item_committed_to_sprint_ids.append(item_id)

        if (
            not is_unestimated_or_oversized
            and not is_insufficient_ac_or_spec
            and not is_blocked_committed
        ):
            ready_candidates += 1

    is_compliant = (
        len(unestimated_or_oversized_epic_ids) == 0
        and len(insufficient_acceptance_criteria_or_spec_ids) == 0
        and len(blocked_item_committed_to_sprint_ids) == 0
    )

    if is_compliant:
        dor_readiness_health = "healthy"
    elif len(blocked_item_committed_to_sprint_ids) > 0:
        dor_readiness_health = "critical"
    else:
        dor_readiness_health = "at_risk"

    recommendations: list[str] = []
    if unestimated_or_oversized_epic_ids:
        recommendations.append(
            f"Estimar y descomponer épicas/historias para que tengan entre 1 y {max_pts} Story Points (INVEST Small/Estimable) en {unestimated_or_oversized_epic_ids}."
        )
    if insufficient_acceptance_criteria_or_spec_ids:
        recommendations.append(
            f"Definir al menos {min_ac} criterios de aceptación verificables y vincular especificación UX/arquitectura en {insufficient_acceptance_criteria_or_spec_ids}."
        )
    if blocked_item_committed_to_sprint_ids:
        recommendations.append(
            f"Retirar del compromiso de sprint o despejar dependencias bloqueantes, estimación y criterios de aceptación en {blocked_item_committed_to_sprint_ids}."
        )

    return {
        "total_candidates": total_candidates,
        "ready_candidates": ready_candidates,
        "unestimated_or_oversized_epic_ids": unestimated_or_oversized_epic_ids,
        "insufficient_acceptance_criteria_or_spec_ids": insufficient_acceptance_criteria_or_spec_ids,
        "blocked_item_committed_to_sprint_ids": blocked_item_committed_to_sprint_ids,
        "dor_readiness_health": dor_readiness_health,
        "is_compliant": is_compliant,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_definition_of_ready_and_backlog_grooming = staticmethod(
    audit_wiki_definition_of_ready_and_backlog_grooming
)


def audit_wiki_blameless_postmortem_and_systemic_prevention(
    postmortem_records: list[dict[str, Any]],
    *,
    require_five_whys_depth: int = 3,
    require_systemic_preventive_action: bool = True,
    max_days_to_publish: int = 5,
) -> dict[str, Any]:
    """Audita post-mortems sin culpa (Blameless Post-Mortem) en la Wiki: profundidad de análisis 5-Whys, ausencia de lenguaje punitivo, acciones preventivas sistémicas con responsable y SLA de publicación (PMI PMBOK §11.1 y §8.1)."""
    if (
        postmortem_records is None
        or isinstance(postmortem_records, (str, bytes))
        or not isinstance(postmortem_records, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = postmortem_records

    try:
        min_whys = int(require_five_whys_depth)
    except (TypeError, ValueError):
        min_whys = 3

    try:
        max_pub_days = int(max_days_to_publish)
    except (TypeError, ValueError):
        max_pub_days = 5

    total_postmortems = 0
    shallow_root_cause_ids: list[str] = []
    blame_violation_ids: list[str] = []
    missing_preventive_action_ids: list[str] = []
    late_publication_ids: list[str] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_postmortems += 1

        incident_id = (
            str(raw.get("incident_id") or raw.get("id") or "").strip()
            or f"INC-{total_postmortems}"
        )

        raw_depth = raw.get("whys_chain_depth")
        try:
            whys_chain_depth = int(raw_depth) if raw_depth is not None else 0
        except (TypeError, ValueError):
            whys_chain_depth = 0

        has_blameless_language_violation = bool(
            raw.get("has_blameless_language_violation")
        )
        has_systemic_preventive_action = bool(
            raw.get("has_systemic_preventive_action")
        )
        action_owner_assigned = bool(raw.get("action_owner_assigned"))

        raw_days = raw.get("days_to_publish")
        try:
            days_to_publish = int(raw_days) if raw_days is not None else 0
        except (TypeError, ValueError):
            days_to_publish = 0

        if whys_chain_depth < min_whys:
            shallow_root_cause_ids.append(incident_id)
            issues.append(
                f"Post-mortem '{incident_id}' presenta profundidad 5-Whys insuficiente ({whys_chain_depth} < {min_whys})."
            )

        if has_blameless_language_violation:
            blame_violation_ids.append(incident_id)
            issues.append(
                f"Post-mortem '{incident_id}' infringe la política Blameless al incluir lenguaje de culpabilización individual."
            )

        if (
            bool(require_systemic_preventive_action)
            and not has_systemic_preventive_action
        ) or not action_owner_assigned:
            missing_preventive_action_ids.append(incident_id)
            issues.append(
                f"Post-mortem '{incident_id}' carece de acción preventiva sistémica o de propietario asignado."
            )

        if days_to_publish > max_pub_days:
            late_publication_ids.append(incident_id)
            issues.append(
                f"Post-mortem '{incident_id}' fue publicado fuera de SLA ({days_to_publish}d > {max_pub_days}d)."
            )

    if len(blame_violation_ids) > 0 or len(missing_preventive_action_ids) > 0:
        learning_culture_status = "NON_COMPLIANT"
    elif len(shallow_root_cause_ids) > 0 or len(late_publication_ids) > 0:
        learning_culture_status = "NEEDS_COACHING"
    else:
        learning_culture_status = "EXEMPLARY"

    return {
        "total_postmortems": total_postmortems,
        "shallow_root_cause_ids": shallow_root_cause_ids,
        "blame_violation_ids": blame_violation_ids,
        "missing_preventive_action_ids": missing_preventive_action_ids,
        "late_publication_ids": late_publication_ids,
        "learning_culture_status": learning_culture_status,
        "is_compliant": learning_culture_status == "EXEMPLARY",
        "issues": issues,
    }


WikiPMIService.audit_wiki_blameless_postmortem_and_systemic_prevention = staticmethod(
    audit_wiki_blameless_postmortem_and_systemic_prevention
)


def audit_wiki_opa_and_eef_catalog_freshness(
    catalog_entries: list[dict[str, Any]],
    *,
    max_review_age_days: int = 180,
    require_steward_owner: bool = True,
) -> dict[str, Any]:
    """Audita la vigencia del catálogo de Activos de Procesos de la Organización (OPA) y Factores Ambientales de la Empresa (EEF) en la Wiki: clasificación válida, antigüedad de revisión, responsable custodio (steward) y retiro de activos deprecados en plantillas activas (PMI PMBOK §2.2, §2.3 y §4.4)."""
    if (
        catalog_entries is None
        or isinstance(catalog_entries, (str, bytes))
        or not isinstance(catalog_entries, Sequence)
    ):
        items: Sequence[Any] = ()
    else:
        items = catalog_entries

    try:
        max_age_days = int(max_review_age_days)
    except (TypeError, ValueError):
        max_age_days = 180

    total_catalog_entries = 0
    invalid_category_asset_ids: list[str] = []
    stale_asset_ids: list[str] = []
    unowned_asset_ids: list[str] = []
    deprecated_in_use_asset_ids: list[str] = []
    issues: list[str] = []

    for raw in items:
        if not isinstance(raw, Mapping):
            continue
        total_catalog_entries += 1

        asset_id = (
            str(raw.get("asset_id") or raw.get("id") or "").strip()
            or f"ASSET-{total_catalog_entries}"
        )
        asset_category = str(raw.get("asset_category") or "").strip().upper()

        raw_days = raw.get("days_since_last_review")
        if raw_days is None or isinstance(raw_days, bool):
            days_since_last_review = 0
        else:
            try:
                days_since_last_review = int(raw_days)
            except (TypeError, ValueError):
                days_since_last_review = 0

        steward_owner_id = str(raw.get("steward_owner_id") or "").strip()
        is_deprecated = bool(raw.get("is_deprecated"))

        raw_refs = raw.get("active_templates_referencing_count")
        if raw_refs is None or isinstance(raw_refs, bool):
            active_templates_referencing_count = 0
        else:
            try:
                active_templates_referencing_count = int(raw_refs)
            except (TypeError, ValueError):
                active_templates_referencing_count = 0

        if asset_category not in {"OPA", "EEF"}:
            invalid_category_asset_ids.append(asset_id)
            issues.append(
                f"Activo '{asset_id}' declara categoría inválida ('{asset_category}'); debe ser 'OPA' o 'EEF'."
            )

        if not is_deprecated and days_since_last_review > max_age_days:
            stale_asset_ids.append(asset_id)
            issues.append(
                f"Activo '{asset_id}' supera la antigüedad máxima de revisión ({days_since_last_review}d > {max_age_days}d)."
            )

        if (
            bool(require_steward_owner)
            and not is_deprecated
            and not steward_owner_id
        ):
            unowned_asset_ids.append(asset_id)
            issues.append(
                f"Activo vigente '{asset_id}' carece de responsable custodio (steward_owner_id)."
            )

        if is_deprecated and active_templates_referencing_count > 0:
            deprecated_in_use_asset_ids.append(asset_id)
            issues.append(
                f"Activo deprecado '{asset_id}' continúa referenciado por {active_templates_referencing_count} plantilla(s) activa(s)."
            )

    if (
        len(deprecated_in_use_asset_ids) > 0
        or len(invalid_category_asset_ids) > 0
    ):
        catalog_health_status = "CRITICAL_DRIFT"
    elif len(stale_asset_ids) > 0 or len(unowned_asset_ids) > 0:
        catalog_health_status = "STALE_OR_UNOWNED"
    else:
        catalog_health_status = "GOVERNED"

    return {
        "total_catalog_entries": total_catalog_entries,
        "invalid_category_asset_ids": invalid_category_asset_ids,
        "stale_asset_ids": stale_asset_ids,
        "unowned_asset_ids": unowned_asset_ids,
        "deprecated_in_use_asset_ids": deprecated_in_use_asset_ids,
        "catalog_health_status": catalog_health_status,
        "is_catalog_governed": catalog_health_status == "GOVERNED",
        "issues": issues,
    }


WikiPMIService.audit_wiki_opa_and_eef_catalog_freshness = staticmethod(
    audit_wiki_opa_and_eef_catalog_freshness
)



def audit_wiki_adr_superseded_chain_and_consequences_hygiene(
    adr_records: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """PMBOK 4.4 & 5.3 — cadenas ADR superseded y completitud de secciones.

    Auditoría pura sobre ``adr_records``. Entradas no-lista/None se tratan
    como lista vacía y elementos no-dict se ignoran. Cada elemento:
    ``adr_id``, ``status`` (proposed/accepted/superseded/deprecated/
    rejected), ``superseded_by_adr_id``, y flags de secciones
    (``has_context_section``, ``has_decision_section``,
    ``has_consequences_section``). Reglas:

    1. ``invalid_status_adr_ids``: status fuera del catálogo aceptado (case-
       insensitive con strip()).
    2. ``incomplete_sections_adr_ids``: faltante de context/decision/
       consequences.
    3. ``broken_superseded_link_adr_ids``: status 'superseded' con destino
       vacío, auto-referencial, inexistente o destino no 'accepted'.
    4. ``contradictory_superseded_adr_ids``: status distinto de 'superseded'
       con ``superseded_by_adr_id`` presente.

    ``adr_governance_status``: CHAIN_OR_STATUS_BROKEN si (1), (3) o (4);
    INCOMPLETE_DOCUMENTATION si solo (2); COMPLIANT en caso contrario.
    ``is_adr_log_healthy`` = status == 'COMPLIANT'.
    """
    valid_statuses = {"proposed", "accepted", "superseded", "deprecated", "rejected"}

    def _status(entry: Mapping[str, Any]) -> str:
        raw = entry.get("status")
        return str(raw).strip().lower() if raw is not None else ""

    raw_items = adr_records if isinstance(adr_records, list) else []
    items = [entry for entry in raw_items if isinstance(entry, Mapping)]

    adr_entry_by_lower: dict[str, Mapping[str, Any]] = {}
    for entry in items:
        adr_id_raw = entry.get("adr_id")
        if isinstance(adr_id_raw, str) and adr_id_raw.strip():
            adr_entry_by_lower[adr_id_raw.strip().lower()] = entry

    invalid_status_adr_ids: list[str] = []
    incomplete_sections_adr_ids: list[str] = []
    broken_superseded_link_adr_ids: list[str] = []
    contradictory_superseded_adr_ids: list[str] = []

    for entry in items:
        adr_id = entry.get("adr_id")
        status = _status(entry)
        superseded_by = entry.get("superseded_by_adr_id")
        superseded_by_clean = (
            str(superseded_by).strip()
            if isinstance(superseded_by, str)
            else ("" if superseded_by is None else None)
        )
        has_target = bool(superseded_by_clean)

        if status not in valid_statuses:
            invalid_status_adr_ids.append(adr_id)

        if (
            entry.get("has_context_section") is not True
            or entry.get("has_decision_section") is not True
            or entry.get("has_consequences_section") is not True
        ):
            incomplete_sections_adr_ids.append(adr_id)

        if status == "superseded":
            target_lookup = (
                superseded_by_clean.strip().lower()
                if isinstance(superseded_by_clean, str)
                else None
            )
            target_status = (
                _status(adr_entry_by_lower[target_lookup])
                if target_lookup in adr_entry_by_lower
                else None
            )
            broken = (
                (not has_target)
                or (
                    target_lookup is not None
                    and str(entry.get("adr_id")).strip().lower() == target_lookup
                )
                or (target_lookup is None or target_lookup not in adr_entry_by_lower)
                or (target_status != "accepted")
            )
            if broken:
                broken_superseded_link_adr_ids.append(adr_id)
        elif has_target:
            contradictory_superseded_adr_ids.append(adr_id)

    if invalid_status_adr_ids or broken_superseded_link_adr_ids or contradictory_superseded_adr_ids:
        adr_governance_status = "CHAIN_OR_STATUS_BROKEN"
    elif incomplete_sections_adr_ids:
        adr_governance_status = "INCOMPLETE_DOCUMENTATION"
    else:
        adr_governance_status = "COMPLIANT"

    return {
        "total_adr_records": len(items),
        "invalid_status_adr_ids": invalid_status_adr_ids,
        "incomplete_sections_adr_ids": incomplete_sections_adr_ids,
        "broken_superseded_link_adr_ids": broken_superseded_link_adr_ids,
        "contradictory_superseded_adr_ids": contradictory_superseded_adr_ids,
        "adr_governance_status": adr_governance_status,
        "is_adr_log_healthy": adr_governance_status == "COMPLIANT",
    }


WikiPMIService.audit_wiki_adr_superseded_chain_and_consequences_hygiene = staticmethod(
    audit_wiki_adr_superseded_chain_and_consequences_hygiene
)


def audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness(
    knowledge_domains: list[dict[str, Any]],
    *,
    max_onboarding_ramp_days: int = 14,
    min_shadow_sessions_completed: int = 2,
) -> dict[str, Any]:
    """Audita playbooks de onboarding en Wiki y preparación de transferencia de conocimiento (PMI PMBOK §4.4 / §9.4)."""
    if not isinstance(knowledge_domains, list):
        return {
            "total_domains": 0,
            "missing_playbook_domain_ids": [],
            "excessive_ramp_domain_ids": [],
            "insufficient_shadowing_domain_ids": [],
            "kt_readiness_status": "READY_FOR_HANDOVER",
            "is_kt_ready": True,
            "issues": [],
        }

    max_ramp = int(
        max_onboarding_ramp_days if max_onboarding_ramp_days is not None else 14
    )
    min_shadows = int(
        min_shadow_sessions_completed
        if min_shadow_sessions_completed is not None
        else 2
    )

    total_domains = 0
    missing_playbook_domain_ids: list[str] = []
    excessive_ramp_domain_ids: list[str] = []
    insufficient_shadowing_domain_ids: list[str] = []
    issues: list[str] = []

    for idx, item in enumerate(knowledge_domains):
        if not isinstance(item, dict):
            continue
        total_domains += 1
        domain_id = str(item.get("domain_id") or f"DOM-{idx + 1}").strip()
        has_playbook = bool(item.get("has_up_to_date_playbook", False))
        local_setup_ok = bool(item.get("local_setup_verified_under_max_days", False))
        ramp_days = int(item.get("estimated_ramp_days") or 0)
        shadows = int(item.get("shadow_sessions_completed") or 0)
        signoff = bool(item.get("independent_signoff_achieved", False))

        if not has_playbook or not local_setup_ok:
            missing_playbook_domain_ids.append(domain_id)
            issues.append(
                f"Dominio '{domain_id}' carece de playbook actualizado o verificación de entorno local."
            )

        if ramp_days > max_ramp:
            excessive_ramp_domain_ids.append(domain_id)
            issues.append(
                f"Dominio '{domain_id}' excede el tiempo máximo de rampa de onboarding ({ramp_days}d > {max_ramp}d)."
            )

        if shadows < min_shadows or not signoff:
            insufficient_shadowing_domain_ids.append(domain_id)
            issues.append(
                f"Dominio '{domain_id}' presenta sesiones shadow insuficientes ({shadows} < {min_shadows}) o falta signoff independiente."
            )

    if len(missing_playbook_domain_ids) > 0:
        kt_readiness_status = "KT_BLOCKED"
    elif (
        len(excessive_ramp_domain_ids) > 0
        or len(insufficient_shadowing_domain_ids) > 0
    ):
        kt_readiness_status = "RAMP_OR_SHADOW_DEFICIT"
    else:
        kt_readiness_status = "READY_FOR_HANDOVER"

    return {
        "total_domains": total_domains,
        "missing_playbook_domain_ids": missing_playbook_domain_ids,
        "excessive_ramp_domain_ids": excessive_ramp_domain_ids,
        "insufficient_shadowing_domain_ids": insufficient_shadowing_domain_ids,
        "kt_readiness_status": kt_readiness_status,
        "is_kt_ready": kt_readiness_status == "READY_FOR_HANDOVER",
        "issues": issues,
    }


WikiPMIService.audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness = staticmethod(
    audit_wiki_onboarding_playbook_and_knowledge_transfer_readiness
)


def audit_wiki_communication_matrix_cadence_and_escalation(
    communication_channels: list[dict[str, Any]],
    *,
    max_days_since_dispatch: int = 14,
    min_open_rate_pct: float = 65.0,
) -> dict[str, Any]:
    """Audit PMI PMBOK §10.1 & §13.3 stakeholder communication matrix cadence, channel redundancy, and escalation paths."""
    overdue_dispatch_channel_ids: list[str] = []
    single_point_of_failure_channel_ids: list[str] = []
    unowned_escalation_channel_ids: list[str] = []
    low_engagement_channel_ids: list[str] = []
    recommendations: list[str] = []

    valid_channels = (
        [
            c
            for c in communication_channels
            if isinstance(c, dict) and str(c.get("channel_id", "")).strip()
        ]
        if isinstance(communication_channels, list)
        else []
    )

    for channel in valid_channels:
        channel_id = str(channel.get("channel_id", "")).strip()

        stakeholder_tier = str(channel.get("stakeholder_tier", "CORE_TEAM")).strip().upper()
        cadence_days = int(channel.get("cadence_days", 7) or 7)
        days_since_last_dispatch = int(channel.get("days_since_last_dispatch", 0) or 0)
        has_fallback_channel = bool(channel.get("has_fallback_channel", False))
        has_escalation_owner = bool(channel.get("has_escalation_owner", True))
        open_ack_rate_pct = float(
            channel.get("open_ack_rate_pct", 100.0)
            if channel.get("open_ack_rate_pct") is not None
            else 100.0
        )

        if days_since_last_dispatch > cadence_days or days_since_last_dispatch > max_days_since_dispatch:
            overdue_dispatch_channel_ids.append(channel_id)

        if stakeholder_tier == "EXECUTIVE" and not has_fallback_channel:
            single_point_of_failure_channel_ids.append(channel_id)

        if not has_escalation_owner:
            unowned_escalation_channel_ids.append(channel_id)

        if open_ack_rate_pct < min_open_rate_pct:
            low_engagement_channel_ids.append(channel_id)

    if unowned_escalation_channel_ids:
        recommendations.append(
            f"Assign explicit escalation owners to communication channels: {', '.join(unowned_escalation_channel_ids)}."
        )
    if single_point_of_failure_channel_ids:
        recommendations.append(
            f"Configure redundant fallback channels for EXECUTIVE tier communications: {', '.join(single_point_of_failure_channel_ids)}."
        )
    if overdue_dispatch_channel_ids:
        recommendations.append(
            f"Trigger overdue stakeholder dispatches and restore cadence on channels: {', '.join(overdue_dispatch_channel_ids)}."
        )
    if low_engagement_channel_ids:
        recommendations.append(
            f"Revise communication format or delivery schedule to boost engagement (<{min_open_rate_pct:.1f}%) on: {', '.join(low_engagement_channel_ids)}."
        )

    if (
        unowned_escalation_channel_ids
        or single_point_of_failure_channel_ids
        or len(overdue_dispatch_channel_ids) > 1
    ):
        communication_health_status = "CRITICAL"
    elif len(overdue_dispatch_channel_ids) == 1 or low_engagement_channel_ids:
        communication_health_status = "WARNING"
    else:
        communication_health_status = "HEALTHY"

    return {
        "total_channels": len(valid_channels),
        "overdue_dispatch_channel_ids": overdue_dispatch_channel_ids,
        "single_point_of_failure_channel_ids": single_point_of_failure_channel_ids,
        "unowned_escalation_channel_ids": unowned_escalation_channel_ids,
        "low_engagement_channel_ids": low_engagement_channel_ids,
        "communication_health_status": communication_health_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_communication_matrix_cadence_and_escalation = staticmethod(
    audit_wiki_communication_matrix_cadence_and_escalation
)


def audit_wiki_slo_error_budget_and_runbook_linkage(
    services_catalog: list[dict[str, Any]],
    *,
    max_burn_rate_threshold: float = 1.5,
    min_remaining_error_budget_pct: float = 20.0,
) -> dict[str, Any]:
    """Audit PMI PMBOK §8.2 & §4.4 Service Level Objectives (SLO), error budget burn rate, and runbook linkage."""
    slo_breached_service_ids: list[str] = []
    unfrozen_exhausted_budget_service_ids: list[str] = []
    high_burn_rate_service_ids: list[str] = []
    missing_runbook_service_ids: list[str] = []
    recommendations: list[str] = []

    valid_services = (
        [
            s
            for s in services_catalog
            if isinstance(s, dict) and str(s.get("service_id", "")).strip()
        ]
        if isinstance(services_catalog, list)
        else []
    )

    for svc in valid_services:
        service_id = str(svc.get("service_id", "")).strip()
        target_slo_pct = float(svc.get("target_slo_pct", 99.9) or 99.9)
        current_sli_pct = float(
            svc.get("current_sli_pct", target_slo_pct)
            if svc.get("current_sli_pct") is not None
            else target_slo_pct
        )
        remaining_error_budget_pct = float(
            svc.get("remaining_error_budget_pct", 100.0)
            if svc.get("remaining_error_budget_pct") is not None
            else 100.0
        )
        burn_rate_24h = float(svc.get("burn_rate_24h", 0.0) or 0.0)
        has_linked_runbook = (
            bool(svc.get("has_linked_runbook", True))
            if svc.get("has_linked_runbook") is not None
            else True
        )
        feature_freeze_enforced = bool(svc.get("feature_freeze_enforced", False))

        if current_sli_pct < target_slo_pct or remaining_error_budget_pct <= 0.0:
            slo_breached_service_ids.append(service_id)

        if remaining_error_budget_pct <= 0.0 and not feature_freeze_enforced:
            unfrozen_exhausted_budget_service_ids.append(service_id)

        if burn_rate_24h > max_burn_rate_threshold or (
            0.0 < remaining_error_budget_pct < min_remaining_error_budget_pct
        ):
            high_burn_rate_service_ids.append(service_id)

        if not has_linked_runbook:
            missing_runbook_service_ids.append(service_id)

    if slo_breached_service_ids:
        recommendations.append(
            f"Prioritize reliability remediation for services breaching SLO or error budget: {', '.join(slo_breached_service_ids)}."
        )
    if unfrozen_exhausted_budget_service_ids:
        recommendations.append(
            f"Enforce immediate feature freeze on services with exhausted error budgets: {', '.join(unfrozen_exhausted_budget_service_ids)}."
        )
    if high_burn_rate_service_ids:
        recommendations.append(
            f"Investigate elevated 24h error budget burn rate or low remaining budget on: {', '.join(high_burn_rate_service_ids)}."
        )
    if missing_runbook_service_ids:
        recommendations.append(
            f"Link verified incident response runbooks in the Wiki for services: {', '.join(missing_runbook_service_ids)}."
        )

    if slo_breached_service_ids or unfrozen_exhausted_budget_service_ids:
        slo_governance_status = "CRITICAL"
    elif high_burn_rate_service_ids or missing_runbook_service_ids:
        slo_governance_status = "WARNING"
    else:
        slo_governance_status = "HEALTHY"

    return {
        "total_services": len(valid_services),
        "slo_breached_service_ids": slo_breached_service_ids,
        "unfrozen_exhausted_budget_service_ids": unfrozen_exhausted_budget_service_ids,
        "high_burn_rate_service_ids": high_burn_rate_service_ids,
        "missing_runbook_service_ids": missing_runbook_service_ids,
        "slo_governance_status": slo_governance_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_slo_error_budget_and_runbook_linkage = staticmethod(
    audit_wiki_slo_error_budget_and_runbook_linkage
)


def audit_wiki_chaos_gameday_resilience_and_action_closure(
    experiments: list[dict[str, Any]],
    *,
    max_days_between_gamedays: int = 90,
    max_remediation_age_days: int = 30,
) -> dict[str, Any]:
    """Audit PMI PMBOK §11.2 & §8.2 Chaos Engineering / GameDay resilience experiments and remediation action closure."""
    unsafe_experiment_ids: list[str] = []
    stale_gameday_experiment_ids: list[str] = []
    unmitigated_failure_experiment_ids: list[str] = []
    untracked_failure_experiment_ids: list[str] = []
    recommendations: list[str] = []

    valid_experiments = (
        [
            e
            for e in experiments
            if isinstance(e, dict) and str(e.get("experiment_id", "")).strip()
        ]
        if isinstance(experiments, list)
        else []
    )

    for exp in valid_experiments:
        experiment_id = str(exp.get("experiment_id", "")).strip()
        steady_state_hypothesis_defined = bool(
            exp.get("steady_state_hypothesis_defined", False)
        )
        abort_stop_condition_defined = bool(
            exp.get("abort_stop_condition_defined", False)
        )
        days_since_executed = int(exp.get("days_since_executed", 0) or 0)
        hypothesis_validated = bool(exp.get("hypothesis_validated", False))
        open_remediation_items = int(exp.get("open_remediation_items", 0) or 0)
        oldest_remediation_age_days = int(
            exp.get("oldest_remediation_age_days", 0) or 0
        )
        remediation_completed = bool(exp.get("remediation_completed", False))

        if not steady_state_hypothesis_defined or not abort_stop_condition_defined:
            unsafe_experiment_ids.append(experiment_id)

        if days_since_executed > max_days_between_gamedays:
            stale_gameday_experiment_ids.append(experiment_id)

        if (
            not hypothesis_validated
            and open_remediation_items > 0
            and oldest_remediation_age_days > max_remediation_age_days
        ):
            unmitigated_failure_experiment_ids.append(experiment_id)

        if (
            not hypothesis_validated
            and open_remediation_items == 0
            and not remediation_completed
        ):
            untracked_failure_experiment_ids.append(experiment_id)

    if unsafe_experiment_ids:
        recommendations.append(
            f"Define explicit steady-state hypotheses and automated abort/stop conditions for GameDay experiments: {', '.join(unsafe_experiment_ids)}."
        )
    if unmitigated_failure_experiment_ids:
        recommendations.append(
            f"Close overdue resilience remediation items (>{max_remediation_age_days}d) from failed GameDays: {', '.join(unmitigated_failure_experiment_ids)}."
        )
    if untracked_failure_experiment_ids:
        recommendations.append(
            f"Create tracked CAPA/remediation items for unvalidated GameDay hypotheses: {', '.join(untracked_failure_experiment_ids)}."
        )
    if stale_gameday_experiment_ids:
        recommendations.append(
            f"Re-run stale Chaos Engineering GameDay scenarios (>{max_days_between_gamedays}d since execution): {', '.join(stale_gameday_experiment_ids)}."
        )

    if (
        unsafe_experiment_ids
        or unmitigated_failure_experiment_ids
        or untracked_failure_experiment_ids
    ):
        gameday_governance_status = "CRITICAL"
    elif stale_gameday_experiment_ids:
        gameday_governance_status = "WARNING"
    else:
        gameday_governance_status = "RESILIENT"

    return {
        "total_experiments": len(valid_experiments),
        "unsafe_experiment_ids": unsafe_experiment_ids,
        "stale_gameday_experiment_ids": stale_gameday_experiment_ids,
        "unmitigated_failure_experiment_ids": unmitigated_failure_experiment_ids,
        "untracked_failure_experiment_ids": untracked_failure_experiment_ids,
        "gameday_governance_status": gameday_governance_status,
        "is_gameday_compliant": gameday_governance_status == "RESILIENT",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_chaos_gameday_resilience_and_action_closure = staticmethod(
    audit_wiki_chaos_gameday_resilience_and_action_closure
)


def audit_wiki_api_deprecation_sunset_and_migration_readiness(
    deprecated_endpoints: list[dict[str, Any]],
    *,
    min_sunset_notice_days: int = 60,
    max_unmigrated_traffic_pct: float = 5.0,
) -> dict[str, Any]:
    """Audit PMI PMBOK §4.6 & §10.2 API/interface deprecation sunset window, migration guide linkage, and consumer cutover readiness."""
    insufficient_notice_endpoint_ids: list[str] = []
    missing_migration_guide_endpoint_ids: list[str] = []
    imminent_breaking_removal_endpoint_ids: list[str] = []
    high_residual_traffic_endpoint_ids: list[str] = []
    recommendations: list[str] = []

    valid_endpoints = (
        [
            ep
            for ep in deprecated_endpoints
            if isinstance(ep, dict) and str(ep.get("endpoint_id", "")).strip()
        ]
        if isinstance(deprecated_endpoints, list)
        else []
    )

    for ep in valid_endpoints:
        endpoint_id = str(ep.get("endpoint_id", "")).strip()
        sunset_notice_days_given = int(ep.get("sunset_notice_days_given", 0) or 0)
        days_until_removal = (
            int(ep.get("days_until_removal", 0))
            if ep.get("days_until_removal") is not None
            else 0
        )
        has_migration_guide_url = bool(ep.get("has_migration_guide_url", False))
        unmigrated_consumer_count = int(ep.get("unmigrated_consumer_count", 0) or 0)
        active_traffic_share_pct = float(ep.get("active_traffic_share_pct", 0.0) or 0.0)

        if sunset_notice_days_given < min_sunset_notice_days:
            insufficient_notice_endpoint_ids.append(endpoint_id)

        if not has_migration_guide_url:
            missing_migration_guide_endpoint_ids.append(endpoint_id)

        if days_until_removal <= 14 and (
            unmigrated_consumer_count > 0
            or active_traffic_share_pct > max_unmigrated_traffic_pct
        ):
            imminent_breaking_removal_endpoint_ids.append(endpoint_id)

        if active_traffic_share_pct > max_unmigrated_traffic_pct:
            high_residual_traffic_endpoint_ids.append(endpoint_id)

    if imminent_breaking_removal_endpoint_ids:
        recommendations.append(
            f"Postpone imminent endpoint removal (<=14d) until active consumers and traffic are migrated: {', '.join(imminent_breaking_removal_endpoint_ids)}."
        )
    if missing_migration_guide_endpoint_ids:
        recommendations.append(
            f"Publish Wiki migration guides with payload mappings and code examples for deprecated endpoints: {', '.join(missing_migration_guide_endpoint_ids)}."
        )
    if insufficient_notice_endpoint_ids:
        recommendations.append(
            f"Extend sunset notice windows to at least {min_sunset_notice_days} days for: {', '.join(insufficient_notice_endpoint_ids)}."
        )
    if high_residual_traffic_endpoint_ids:
        recommendations.append(
            f"Accelerate consumer cutover to reduce residual traffic below {max_unmigrated_traffic_pct:.1f}% on: {', '.join(high_residual_traffic_endpoint_ids)}."
        )

    if imminent_breaking_removal_endpoint_ids or missing_migration_guide_endpoint_ids:
        deprecation_governance_status = "BREAKING_RISK"
    elif insufficient_notice_endpoint_ids or high_residual_traffic_endpoint_ids:
        deprecation_governance_status = "WARNING"
    else:
        deprecation_governance_status = "SAFE_TO_SUNSET"

    return {
        "total_deprecated_endpoints": len(valid_endpoints),
        "insufficient_notice_endpoint_ids": insufficient_notice_endpoint_ids,
        "missing_migration_guide_endpoint_ids": missing_migration_guide_endpoint_ids,
        "imminent_breaking_removal_endpoint_ids": imminent_breaking_removal_endpoint_ids,
        "high_residual_traffic_endpoint_ids": high_residual_traffic_endpoint_ids,
        "deprecation_governance_status": deprecation_governance_status,
        "is_sunset_compliant": deprecation_governance_status == "SAFE_TO_SUNSET",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_api_deprecation_sunset_and_migration_readiness = staticmethod(
    audit_wiki_api_deprecation_sunset_and_migration_readiness
)


def audit_wiki_operational_runbook_idempotency_and_preflight_hygiene(
    runbooks: list[dict[str, Any]],
    *,
    max_days_since_dry_run: int = 90,
    max_manual_steps_count: int = 8,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.2 — Wiki Operational Runbook Idempotency, Pre-Flight Check & Rollback Verification Auditor."""
    valid_runbooks: list[dict[str, Any]] = []
    for item in runbooks or []:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("runbook_id") or "").strip()
        if not rid:
            continue
        valid_runbooks.append({**item, "_rid": rid})

    if not valid_runbooks:
        return {
            "total_runbooks": 0,
            "missing_preflight_or_rollback_ids": [],
            "non_idempotent_runbook_ids": [],
            "toil_heavy_runbook_ids": [],
            "stale_dry_run_runbook_ids": [],
            "unlinked_alert_runbook_ids": [],
            "runbook_governance_status": "PRODUCTION_GRADE",
            "is_runbook_production_ready": True,
            "recommendations": [],
        }

    missing_preflight_or_rollback_ids: list[str] = []
    non_idempotent_runbook_ids: list[str] = []
    toil_heavy_runbook_ids: list[str] = []
    stale_dry_run_runbook_ids: list[str] = []
    unlinked_alert_runbook_ids: list[str] = []

    for rb in valid_runbooks:
        rid = rb["_rid"]
        has_preflight = bool(rb.get("has_preflight_validation_checks", False))
        is_idempotent = bool(rb.get("is_idempotent_or_reentrant", False))
        has_rollback = bool(rb.get("has_explicit_rollback_commands", False))
        manual_steps = max(0, int(rb.get("manual_steps_count", 0) or 0))
        days_since_dry_run = max(0, int(rb.get("days_since_last_dry_run", 0) or 0))

        if "linked_alert_rule_id" in rb:
            raw_alert = rb.get("linked_alert_rule_id")
            alert_id = str(raw_alert).strip() if raw_alert is not None else ""
        else:
            alert_id = "ALERT-DEFAULT"

        if not has_preflight or not has_rollback:
            missing_preflight_or_rollback_ids.append(rid)
        if not is_idempotent:
            non_idempotent_runbook_ids.append(rid)
        if manual_steps > max_manual_steps_count:
            toil_heavy_runbook_ids.append(rid)
        if days_since_dry_run > max_days_since_dry_run:
            stale_dry_run_runbook_ids.append(rid)
        if not alert_id:
            unlinked_alert_runbook_ids.append(rid)

    recommendations: list[str] = []
    if missing_preflight_or_rollback_ids:
        recommendations.append(
            f"Add pre-flight validation checks and explicit rollback commands for runbook(s): {', '.join(missing_preflight_or_rollback_ids)}."
        )
    if non_idempotent_runbook_ids:
        recommendations.append(
            f"Refactor non-idempotent operational steps to be safely re-entrant in runbook(s): {', '.join(non_idempotent_runbook_ids)}."
        )
    if toil_heavy_runbook_ids:
        recommendations.append(
            f"Automate repetitive manual steps exceeding threshold ({max_manual_steps_count}) in runbook(s): {', '.join(toil_heavy_runbook_ids)}."
        )
    if stale_dry_run_runbook_ids:
        recommendations.append(
            f"Execute dry-run verification (> {max_days_since_dry_run} days elapsed) for runbook(s): {', '.join(stale_dry_run_runbook_ids)}."
        )
    if unlinked_alert_runbook_ids:
        recommendations.append(
            f"Link monitoring/alert rules to operational runbook(s): {', '.join(unlinked_alert_runbook_ids)}."
        )

    if missing_preflight_or_rollback_ids or non_idempotent_runbook_ids:
        runbook_governance_status = "UNSAFE_RUNBOOK"
    elif (
        toil_heavy_runbook_ids
        or stale_dry_run_runbook_ids
        or unlinked_alert_runbook_ids
    ):
        runbook_governance_status = "WARNING"
    else:
        runbook_governance_status = "PRODUCTION_GRADE"

    return {
        "total_runbooks": len(valid_runbooks),
        "missing_preflight_or_rollback_ids": missing_preflight_or_rollback_ids,
        "non_idempotent_runbook_ids": non_idempotent_runbook_ids,
        "toil_heavy_runbook_ids": toil_heavy_runbook_ids,
        "stale_dry_run_runbook_ids": stale_dry_run_runbook_ids,
        "unlinked_alert_runbook_ids": unlinked_alert_runbook_ids,
        "runbook_governance_status": runbook_governance_status,
        "is_runbook_production_ready": runbook_governance_status == "PRODUCTION_GRADE",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_operational_runbook_idempotency_and_preflight_hygiene = staticmethod(
    audit_wiki_operational_runbook_idempotency_and_preflight_hygiene
)


def audit_wiki_database_migration_expand_contract_and_lock_safety(
    migrations: Any,
    *,
    max_lock_timeout_ms: int = 3000,
) -> Dict[str, object]:
    """Auditoría PMBOK 4.6 y 8.2: migraciones zero-downtime (expand-contract).

    Evalúa por migración la reversibilidad (downgrade), el patrón
    expand-contract para operaciones destructivas, el lock timeout
    configurado (0 o por encima del máximo = riesgo) y la creación
    concurrente de índices, determinando el estado de seguridad
    (ZERO_DOWNTIME_SAFE / WARNING / OUTAGE_RISK).
    """
    entries = migrations if isinstance(migrations, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    irreversible_migration_ids: List[str] = []
    unsafe_destructive_migration_ids: List[str] = []
    missing_lock_timeout_migration_ids: List[str] = []
    blocking_index_migration_ids: List[str] = []

    for item in rows:
        migration_id = item.get("migration_id")

        if item.get("has_reversible_downgrade", False) is not True:
            irreversible_migration_ids.append(migration_id)

        if (
            item.get("contains_destructive_drop_or_rename", False) is True
            and item.get("uses_expand_contract_pattern", True) is not True
        ):
            unsafe_destructive_migration_ids.append(migration_id)

        lock_timeout_ms = item.get("lock_timeout_ms_configured", 2000)
        if (
            not isinstance(lock_timeout_ms, (int, float))
            or lock_timeout_ms == 0
            or lock_timeout_ms > max_lock_timeout_ms
        ):
            missing_lock_timeout_migration_ids.append(migration_id)

        if item.get("index_created_concurrently", True) is not True:
            blocking_index_migration_ids.append(migration_id)

    if (
        irreversible_migration_ids
        or unsafe_destructive_migration_ids
        or blocking_index_migration_ids
    ):
        migration_governance_status = "OUTAGE_RISK"
    elif missing_lock_timeout_migration_ids:
        migration_governance_status = "WARNING"
    else:
        migration_governance_status = "ZERO_DOWNTIME_SAFE"

    recommendations: List[str] = []
    if irreversible_migration_ids:
        recommendations.append(
            "Add a reversible downgrade() to migrations: "
            + ", ".join(str(m) for m in irreversible_migration_ids)
        )
    if unsafe_destructive_migration_ids:
        recommendations.append(
            "Split destructive drop/rename into expand-contract phases for migrations: "
            + ", ".join(str(m) for m in unsafe_destructive_migration_ids)
        )
    if missing_lock_timeout_migration_ids:
        recommendations.append(
            f"Configure lock_timeout_ms between 1 and {max_lock_timeout_ms} ms for migrations: "
            + ", ".join(str(m) for m in missing_lock_timeout_migration_ids)
        )
    if blocking_index_migration_ids:
        recommendations.append(
            "Create indexes CONCURRENTLY in migrations: "
            + ", ".join(str(m) for m in blocking_index_migration_ids)
        )

    return {
        "total_migrations": len(rows),
        "irreversible_migration_ids": irreversible_migration_ids,
        "unsafe_destructive_migration_ids": unsafe_destructive_migration_ids,
        "missing_lock_timeout_migration_ids": missing_lock_timeout_migration_ids,
        "blocking_index_migration_ids": blocking_index_migration_ids,
        "migration_governance_status": migration_governance_status,
        "is_migration_safe": migration_governance_status == "ZERO_DOWNTIME_SAFE",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_database_migration_expand_contract_and_lock_safety = staticmethod(
    audit_wiki_database_migration_expand_contract_and_lock_safety
)


def audit_wiki_blameless_postmortem_five_whys_and_action_sla(
    postmortems: list[dict[str, Any]],
    *,
    min_why_depth: int = 3,
    max_publish_delay_hours: float = 48.0,
) -> dict[str, Any]:
    """PMI PMBOK §11.2 & §10.2 — Wiki Post-Incident Review (PIR) Blameless Postmortem Timeline, Root Cause Five-Whys & Action Item SLA Auditor."""
    valid_pirs: list[dict[str, Any]] = []
    for item in postmortems or []:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("postmortem_id") or "").strip()
        if not pid:
            continue
        valid_pirs.append({**item, "_pid": pid})

    if not valid_pirs:
        return {
            "total_postmortems_evaluated": 0,
            "shallow_root_cause_ids": [],
            "late_published_ids": [],
            "blameful_culture_violation_ids": [],
            "unactionable_postmortem_ids": [],
            "pir_governance_status": "BLAMELESS_EXEMPLARY",
            "is_pir_compliant": True,
            "recommendations": [],
        }

    shallow_root_cause_ids: list[str] = []
    late_published_ids: list[str] = []
    blameful_culture_violation_ids: list[str] = []
    unactionable_postmortem_ids: list[str] = []

    for pir in valid_pirs:
        pid = pir["_pid"]
        sev = str(pir.get("incident_severity") or "").strip().upper()
        why_depth = int(pir.get("why_analysis_depth", 0) or 0)
        delay_hrs = float(pir.get("hours_to_publish_draft", 0.0) or 0.0)
        blameful = bool(pir.get("contains_blameful_language", False))
        has_action = bool(
            pir.get("has_preventive_action_with_owner_and_due_date", False)
        )
        has_timeline = bool(pir.get("has_timeline_with_utc_timestamps", False))

        if why_depth < min_why_depth:
            shallow_root_cause_ids.append(pid)
        if sev in {"SEV1", "SEV2"} and delay_hrs > max_publish_delay_hours:
            late_published_ids.append(pid)
        if blameful:
            blameful_culture_violation_ids.append(pid)
        if not has_action or not has_timeline:
            unactionable_postmortem_ids.append(pid)

    recommendations: list[str] = []
    if blameful_culture_violation_ids:
        recommendations.append(
            f"Rewrite blameful statements to focus on systemic factors in postmortem(s): {', '.join(blameful_culture_violation_ids)}."
        )
    if unactionable_postmortem_ids:
        recommendations.append(
            f"Add UTC incident timeline and owner-assigned preventive action items with due dates in postmortem(s): {', '.join(unactionable_postmortem_ids)}."
        )
    if shallow_root_cause_ids:
        recommendations.append(
            f"Deepen 5-Whys root-cause analysis to at least {min_why_depth} levels in postmortem(s): {', '.join(shallow_root_cause_ids)}."
        )
    if late_published_ids:
        recommendations.append(
            f"Enforce {max_publish_delay_hours}-hour postmortem draft publication SLA for SEV1/SEV2 incident(s): {', '.join(late_published_ids)}."
        )

    if blameful_culture_violation_ids or unactionable_postmortem_ids:
        pir_governance_status = "CULTURE_OR_ACTION_BREACH"
    elif shallow_root_cause_ids or late_published_ids:
        pir_governance_status = "ANALYTICAL_OR_SLA_WARNING"
    else:
        pir_governance_status = "BLAMELESS_EXEMPLARY"

    return {
        "total_postmortems_evaluated": len(valid_pirs),
        "shallow_root_cause_ids": shallow_root_cause_ids,
        "late_published_ids": late_published_ids,
        "blameful_culture_violation_ids": blameful_culture_violation_ids,
        "unactionable_postmortem_ids": unactionable_postmortem_ids,
        "pir_governance_status": pir_governance_status,
        "is_pir_compliant": pir_governance_status == "BLAMELESS_EXEMPLARY",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_blameless_postmortem_five_whys_and_action_sla = staticmethod(
    audit_wiki_blameless_postmortem_five_whys_and_action_sla
)


def audit_wiki_on_call_rotation_burnout_and_escalation_readiness(
    rotations: list[dict[str, Any]],
    *,
    min_responders_in_pool: int = 4,
    max_after_hours_pages_per_shift: int = 8,
) -> dict[str, Any]:
    """PMI PMBOK §9.4 & §11.2 — Wiki On-Call Rotation Burnout Load, Shift Handoff Completeness & Pager Escalation Tree Auditor."""
    understaffed_rotation_ids: list[str] = []
    burnout_overload_rotation_ids: list[str] = []
    single_point_escalation_ids: list[str] = []
    missing_handoff_rotation_ids: list[str] = []

    valid_rotations = (
        [
            r
            for r in rotations
            if isinstance(r, dict) and str(r.get("rotation_id", "")).strip()
        ]
        if isinstance(rotations, list)
        else []
    )

    for rot in valid_rotations:
        rotation_id = str(rot.get("rotation_id", "")).strip()
        active_responders_count = int(rot.get("active_responders_count", 0) or 0)
        after_hours_pages_count = int(rot.get("after_hours_pages_count", 0) or 0)
        has_secondary_backup_escalation = (
            bool(rot.get("has_secondary_backup_escalation", True))
            if rot.get("has_secondary_backup_escalation") is not None
            else True
        )
        has_shift_handoff_notes_logged = (
            bool(rot.get("has_shift_handoff_notes_logged", True))
            if rot.get("has_shift_handoff_notes_logged") is not None
            else True
        )

        if active_responders_count < min_responders_in_pool:
            understaffed_rotation_ids.append(rotation_id)

        if after_hours_pages_count > max_after_hours_pages_per_shift:
            burnout_overload_rotation_ids.append(rotation_id)

        if not has_secondary_backup_escalation:
            single_point_escalation_ids.append(rotation_id)

        if not has_shift_handoff_notes_logged:
            missing_handoff_rotation_ids.append(rotation_id)

    if (
        single_point_escalation_ids
        or understaffed_rotation_ids
        or burnout_overload_rotation_ids
    ):
        on_call_governance_status = "ESCALATION_OR_BURNOUT_CRISIS"
    elif missing_handoff_rotation_ids:
        on_call_governance_status = "HANDOFF_HYGIENE_WARNING"
    else:
        on_call_governance_status = "ROTATION_SUSTAINABLE"

    return {
        "total_rotations_evaluated": len(valid_rotations),
        "understaffed_rotation_ids": understaffed_rotation_ids,
        "burnout_overload_rotation_ids": burnout_overload_rotation_ids,
        "single_point_escalation_ids": single_point_escalation_ids,
        "missing_handoff_rotation_ids": missing_handoff_rotation_ids,
        "on_call_governance_status": on_call_governance_status,
        "is_on_call_compliant": on_call_governance_status == "ROTATION_SUSTAINABLE",
    }


WikiPMIService.audit_wiki_on_call_rotation_burnout_and_escalation_readiness = staticmethod(
    audit_wiki_on_call_rotation_burnout_and_escalation_readiness
)


def audit_wiki_adr_immutability_and_superseded_chain_integrity(
    adrs: list[dict[str, Any]],
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — Wiki Architecture Decision Record (ADR) Immutability, Superseded Chain & Context-Consequences Completeness Auditor."""
    valid_adrs: list[dict[str, Any]] = []
    if isinstance(adrs, (list, tuple)):
        for item in adrs:
            if not isinstance(item, dict):
                continue
            aid = str(item.get("adr_id") or "").strip()
            if not aid:
                continue
            valid_adrs.append({**item, "_aid": aid})

    if not valid_adrs:
        return {
            "total_adrs_evaluated": 0,
            "mutated_in_place_adr_ids": [],
            "broken_superseded_link_adr_ids": [],
            "incomplete_structure_adr_ids": [],
            "adr_governance_status": "ADR_LOG_INTEGRITY_VERIFIED",
            "is_adr_log_compliant": True,
            "recommendations": [],
        }

    known_adr_ids = {a["_aid"] for a in valid_adrs}
    mutated_in_place_adr_ids: list[str] = []
    broken_superseded_link_adr_ids: list[str] = []
    incomplete_structure_adr_ids: list[str] = []

    for adr in valid_adrs:
        aid = adr["_aid"]
        status = str(adr.get("status") or "").strip().upper()
        raw_sup = adr.get("superseded_by_adr_id")
        sup_id = str(raw_sup).strip() if raw_sup is not None else ""
        mutated = bool(adr.get("was_mutated_in_place_after_acceptance", False))
        has_sections = bool(
            adr.get("has_context_decision_and_consequences_sections", True)
        )
        has_deciders = bool(adr.get("has_deciders_and_date_recorded", True))

        if mutated:
            mutated_in_place_adr_ids.append(aid)

        if status == "SUPERSEDED":
            if not sup_id or sup_id == aid or sup_id not in known_adr_ids:
                broken_superseded_link_adr_ids.append(aid)

        if not has_sections or not has_deciders:
            incomplete_structure_adr_ids.append(aid)

    recommendations: list[str] = []
    if mutated_in_place_adr_ids:
        recommendations.append(
            f"Restore immutability on accepted ADR(s) and issue new superseding ADR(s) instead of mutating in place: {', '.join(mutated_in_place_adr_ids)}."
        )
    if broken_superseded_link_adr_ids:
        recommendations.append(
            f"Repair broken or self-referencing `superseded_by_adr_id` chain links on ADR(s): {', '.join(broken_superseded_link_adr_ids)}."
        )
    if incomplete_structure_adr_ids:
        recommendations.append(
            f"Complete Context, Decision, Consequences, Deciders, and Date sections in ADR(s): {', '.join(incomplete_structure_adr_ids)}."
        )

    if mutated_in_place_adr_ids or broken_superseded_link_adr_ids:
        adr_governance_status = "IMMUTABILITY_OR_CHAIN_BREACH"
    elif incomplete_structure_adr_ids:
        adr_governance_status = "STRUCTURE_INCOMPLETE_WARNING"
    else:
        adr_governance_status = "ADR_LOG_INTEGRITY_VERIFIED"

    return {
        "total_adrs_evaluated": len(valid_adrs),
        "mutated_in_place_adr_ids": mutated_in_place_adr_ids,
        "broken_superseded_link_adr_ids": broken_superseded_link_adr_ids,
        "incomplete_structure_adr_ids": incomplete_structure_adr_ids,
        "adr_governance_status": adr_governance_status,
        "is_adr_log_compliant": adr_governance_status
        == "ADR_LOG_INTEGRITY_VERIFIED",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_adr_immutability_and_superseded_chain_integrity = staticmethod(
    audit_wiki_adr_immutability_and_superseded_chain_integrity
)


def audit_wiki_bus_factor_spok_and_cross_training_coverage(
    domains: list[dict[str, Any]],
    *,
    min_bus_factor_contributors: int = 2,
    max_single_author_commit_share_pct: float = 80.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §9.3 — Wiki Onboarding Bus-Factor Single-Point-of-Knowledge (SPOK), SME Concentration & Cross-Training Shadowing Auditor."""
    valid_domains: list[dict[str, Any]] = []
    if isinstance(domains, (list, tuple)):
        for item in domains:
            if not isinstance(item, dict):
                continue
            did = str(item.get("domain_id") or "").strip()
            if not did:
                continue
            valid_domains.append({**item, "_did": did})

    if not valid_domains:
        return {
            "total_domains_evaluated": 0,
            "bus_factor_one_domain_ids": [],
            "monopolized_knowledge_domain_ids": [],
            "untrained_handover_domain_ids": [],
            "bus_factor_governance_status": "KNOWLEDGE_RESILIENT",
            "is_bus_factor_compliant": True,
            "recommendations": [],
        }

    bus_factor_one_domain_ids: list[str] = []
    monopolized_knowledge_domain_ids: list[str] = []
    untrained_handover_domain_ids: list[str] = []

    for dom in valid_domains:
        did = dom["_did"]
        contributors = max(
            0, int(dom.get("active_distinct_contributors", 0) or 0)
        )
        top_share = float(
            dom.get("top_author_contribution_share_pct", 100.0)
            if dom.get("top_author_contribution_share_pct") is not None
            else 100.0
        )
        has_walkthrough = bool(
            dom.get("has_verified_onboarding_walkthrough", False)
        )
        has_shadowing = bool(dom.get("has_completed_shadowing_rotation", False))

        if contributors < min_bus_factor_contributors:
            bus_factor_one_domain_ids.append(did)
        if top_share > max_single_author_commit_share_pct:
            monopolized_knowledge_domain_ids.append(did)
        if not has_walkthrough or not has_shadowing:
            untrained_handover_domain_ids.append(did)

    recommendations: list[str] = []
    if bus_factor_one_domain_ids:
        recommendations.append(
            f"Eliminate Single-Point-of-Knowledge (SPOK) by onboarding >= {min_bus_factor_contributors} active contributors in domain(s): {', '.join(bus_factor_one_domain_ids)}."
        )
    if monopolized_knowledge_domain_ids:
        recommendations.append(
            f"Reduce SME concentration below {max_single_author_commit_share_pct}% single-author contribution share in domain(s): {', '.join(monopolized_knowledge_domain_ids)}."
        )
    if untrained_handover_domain_ids:
        recommendations.append(
            f"Complete verified onboarding walkthroughs and shadowing rotations in domain(s): {', '.join(untrained_handover_domain_ids)}."
        )

    if bus_factor_one_domain_ids or monopolized_knowledge_domain_ids:
        bus_factor_governance_status = "CRITICAL_SPOK_EXPOSURE"
    elif untrained_handover_domain_ids:
        bus_factor_governance_status = "CROSS_TRAINING_GAP_WARNING"
    else:
        bus_factor_governance_status = "KNOWLEDGE_RESILIENT"

    return {
        "total_domains_evaluated": len(valid_domains),
        "bus_factor_one_domain_ids": bus_factor_one_domain_ids,
        "monopolized_knowledge_domain_ids": monopolized_knowledge_domain_ids,
        "untrained_handover_domain_ids": untrained_handover_domain_ids,
        "bus_factor_governance_status": bus_factor_governance_status,
        "is_bus_factor_compliant": bus_factor_governance_status
        == "KNOWLEDGE_RESILIENT",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_bus_factor_spok_and_cross_training_coverage = staticmethod(
    audit_wiki_bus_factor_spok_and_cross_training_coverage
)


def audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene(
    credentials: Any,
    *,
    max_rotation_age_days: int = 90,
    max_lease_ttl_hours: float = 24.0,
) -> Dict[str, object]:
    """Auditoría PMBOK 11.6 y 10.2: higiene de secretos y credenciales.

    Evalúa por credencial la cadencia de rotación, el uso de claves
    estáticas vs leases dinámicos de vault, el TTL del lease y la
    existencia de runbook de rotación automatizado.
    """
    entries = credentials if isinstance(credentials, list) else []
    rows = [item for item in entries if isinstance(item, dict)]

    stale_rotation_credential_ids: List[str] = []
    static_key_violation_ids: List[str] = []
    excessive_lease_ttl_ids: List[str] = []
    missing_rotation_runbook_ids: List[str] = []

    for item in rows:
        credential_id = item.get("credential_id")

        days_since = item.get("days_since_last_rotation", 0)
        days_since_val = days_since if isinstance(days_since, (int, float)) and days_since >= 0 else 0

        if days_since_val > max_rotation_age_days:
            stale_rotation_credential_ids.append(credential_id)

        if (
            item.get("is_static_long_lived_key", False) is True
            or item.get("uses_dynamic_vault_lease", True) is not True
        ):
            static_key_violation_ids.append(credential_id)

        lease_ttl = item.get("lease_ttl_hours", 8.0)
        lease_ttl_val = lease_ttl if isinstance(lease_ttl, (int, float)) else 0.0

        if lease_ttl_val > max_lease_ttl_hours or lease_ttl_val <= 0.0:
            excessive_lease_ttl_ids.append(credential_id)

        if item.get("has_automated_rotation_runbook", True) is not True:
            missing_rotation_runbook_ids.append(credential_id)

    if stale_rotation_credential_ids or static_key_violation_ids:
        secret_hygiene_status = "CREDENTIAL_EXPOSURE_BREACH"
    elif excessive_lease_ttl_ids or missing_rotation_runbook_ids:
        secret_hygiene_status = "LEASE_OR_RUNBOOK_WARNING"
    else:
        secret_hygiene_status = "ZERO_STATIC_SECRETS_VERIFIED"

    return {
        "total_credentials_evaluated": len(rows),
        "stale_rotation_credential_ids": stale_rotation_credential_ids,
        "static_key_violation_ids": static_key_violation_ids,
        "excessive_lease_ttl_ids": excessive_lease_ttl_ids,
        "missing_rotation_runbook_ids": missing_rotation_runbook_ids,
        "secret_hygiene_status": secret_hygiene_status,
        "is_secret_hygiene_compliant": secret_hygiene_status == "ZERO_STATIC_SECRETS_VERIFIED",
    }


WikiPMIService.audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene = staticmethod(
    audit_wiki_secret_rotation_cadence_and_vault_lease_hygiene
)


def audit_wiki_quarterly_attestation_and_orphan_page_archival(
    pages: list[dict[str, Any]],
    *,
    max_days_since_attestation: int = 90,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §10.2 — Wiki Knowledge Base Quarterly Attestation SLA, Orphan Unindexed Page & Deprecated Procedure Archival Auditor."""
    valid_pages: list[dict[str, Any]] = []
    if isinstance(pages, (list, tuple)):
        for item in pages:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("page_id") or "").strip()
            if not pid:
                continue
            valid_pages.append({**item, "_pid": pid})

    if not valid_pages:
        return {
            "total_pages_evaluated": 0,
            "active_pages_count": 0,
            "unattested_stale_page_ids": [],
            "orphan_unindexed_page_ids": [],
            "active_deprecated_procedure_page_ids": [],
            "knowledge_curation_status": "CURATED_KNOWLEDGE_BASE",
            "is_curation_compliant": True,
            "recommendations": [],
        }

    unattested_stale_page_ids: list[str] = []
    orphan_unindexed_page_ids: list[str] = []
    active_deprecated_procedure_page_ids: list[str] = []
    active_pages_count = 0

    for pg in valid_pages:
        pid = pg["_pid"]
        is_archived = bool(pg.get("is_marked_archived", False))
        if is_archived:
            continue
        active_pages_count += 1
        raw_days = pg.get("days_since_owner_attestation")
        days_since = max(0, int(raw_days if raw_days is not None else 0))
        raw_links = pg.get("incoming_navigation_links_count")
        in_links = int(raw_links if raw_links is not None else 1)
        is_root = bool(pg.get("is_root_index_page", False))
        refs_deprecated = bool(pg.get("references_deprecated_system", False))

        if days_since > max_days_since_attestation:
            unattested_stale_page_ids.append(pid)
        if not is_root and in_links <= 0:
            orphan_unindexed_page_ids.append(pid)
        if refs_deprecated:
            active_deprecated_procedure_page_ids.append(pid)

    recommendations: list[str] = []
    if active_deprecated_procedure_page_ids:
        recommendations.append(
            f"Archive or update active pages referencing deprecated systems/procedures: {', '.join(active_deprecated_procedure_page_ids)}."
        )
    if unattested_stale_page_ids:
        recommendations.append(
            f"Complete quarterly owner attestation (<= {max_days_since_attestation} days) for stale page(s): {', '.join(unattested_stale_page_ids)}."
        )
    if orphan_unindexed_page_ids:
        recommendations.append(
            f"Link orphan page(s) into the root navigation index or archive if obsolete: {', '.join(orphan_unindexed_page_ids)}."
        )

    if active_deprecated_procedure_page_ids or unattested_stale_page_ids:
        knowledge_curation_status = "DEPRECATED_OR_STALE_HAZARD"
    elif orphan_unindexed_page_ids:
        knowledge_curation_status = "ORPHAN_DISCOVERABILITY_WARNING"
    else:
        knowledge_curation_status = "CURATED_KNOWLEDGE_BASE"

    return {
        "total_pages_evaluated": len(valid_pages),
        "active_pages_count": active_pages_count,
        "unattested_stale_page_ids": unattested_stale_page_ids,
        "orphan_unindexed_page_ids": orphan_unindexed_page_ids,
        "active_deprecated_procedure_page_ids": active_deprecated_procedure_page_ids,
        "knowledge_curation_status": knowledge_curation_status,
        "is_curation_compliant": knowledge_curation_status
        == "CURATED_KNOWLEDGE_BASE",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_quarterly_attestation_and_orphan_page_archival = staticmethod(
    audit_wiki_quarterly_attestation_and_orphan_page_archival
)


def audit_wiki_dr_tabletop_exercise_and_communication_tree(
    exercises: list[dict[str, Any]],
    *,
    max_days_since_tabletop: int = 180,
    min_participant_attendance_pct: float = 85.0,
) -> dict[str, Any]:
    """PMI PMBOK §11.2 & §10.2 — Wiki Disaster Recovery Tabletop Exercise Cadence, Communication Tree Verification & Recovery Runbook Drill Auditor."""
    valid_exercises: list[dict[str, Any]] = []
    if isinstance(exercises, (list, tuple)):
        for item in exercises:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("exercise_id") or "").strip()
            if not eid:
                continue
            valid_exercises.append({**item, "_eid": eid})

    if not valid_exercises:
        return {
            "total_exercises_evaluated": 0,
            "overdue_tabletop_exercise_ids": [],
            "unverified_comm_tree_exercise_ids": [],
            "low_attendance_or_unassigned_gap_ids": [],
            "tabletop_readiness_status": "TABLETOP_DRILL_VERIFIED",
            "is_tabletop_compliant": True,
            "recommendations": [],
        }

    overdue_tabletop_exercise_ids: list[str] = []
    unverified_comm_tree_exercise_ids: list[str] = []
    low_attendance_or_unassigned_gap_ids: list[str] = []

    for exc in valid_exercises:
        eid = exc["_eid"]
        days_since = int(
            exc.get("days_since_last_tabletop", 30)
            if exc.get("days_since_last_tabletop") is not None
            else 30
        )
        attendance_pct = float(
            exc.get("participant_attendance_pct", 100.0)
            if exc.get("participant_attendance_pct") is not None
            else 100.0
        )
        comm_verified = bool(exc.get("out_of_band_comm_tree_verified", True))
        unassigned_gaps = max(
            0, int(exc.get("unassigned_gaps_discovered_count", 0) or 0)
        )

        if days_since < 0 or days_since > max_days_since_tabletop:
            overdue_tabletop_exercise_ids.append(eid)
        if not comm_verified:
            unverified_comm_tree_exercise_ids.append(eid)
        if (
            attendance_pct < min_participant_attendance_pct
            or unassigned_gaps > 0
        ):
            low_attendance_or_unassigned_gap_ids.append(eid)

    recommendations: list[str] = []
    if overdue_tabletop_exercise_ids:
        recommendations.append(
            f"Conduct Disaster Recovery tabletop exercises within <= {max_days_since_tabletop} days for exercise(s): {', '.join(overdue_tabletop_exercise_ids)}."
        )
    if unverified_comm_tree_exercise_ids:
        recommendations.append(
            f"Verify out-of-band emergency communication tree contacts and fallback channels for exercise(s): {', '.join(unverified_comm_tree_exercise_ids)}."
        )
    if low_attendance_or_unassigned_gap_ids:
        recommendations.append(
            f"Enforce >= {min_participant_attendance_pct}% responder attendance and assign owners to all discovered gaps in exercise(s): {', '.join(low_attendance_or_unassigned_gap_ids)}."
        )

    if overdue_tabletop_exercise_ids or unverified_comm_tree_exercise_ids:
        tabletop_readiness_status = "DR_PREPAREDNESS_BREACH"
    elif low_attendance_or_unassigned_gap_ids:
        tabletop_readiness_status = "ATTENDANCE_OR_GAP_FOLLOWUP_WARNING"
    else:
        tabletop_readiness_status = "TABLETOP_DRILL_VERIFIED"

    return {
        "total_exercises_evaluated": len(valid_exercises),
        "overdue_tabletop_exercise_ids": overdue_tabletop_exercise_ids,
        "unverified_comm_tree_exercise_ids": unverified_comm_tree_exercise_ids,
        "low_attendance_or_unassigned_gap_ids": low_attendance_or_unassigned_gap_ids,
        "tabletop_readiness_status": tabletop_readiness_status,
        "is_tabletop_compliant": tabletop_readiness_status
        == "TABLETOP_DRILL_VERIFIED",
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_dr_tabletop_exercise_and_communication_tree = staticmethod(
    audit_wiki_dr_tabletop_exercise_and_communication_tree
)


def audit_wiki_api_deprecation_sunset_and_consumer_migration(
    deprecated_endpoints: Sequence[Mapping[str, Any]] | None,
    *,
    min_sunset_notice_days: int | float = 90,
    max_remaining_active_consumers_at_sunset: int = 0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §10.2 — Wiki API Deprecation Sunset Notice Window, Consumer Migration Tracking & Breaking-Change Runbook Auditor."""
    valid_endpoints = [
        ep
        for ep in (deprecated_endpoints or [])
        if isinstance(ep, Mapping) and str(ep.get("endpoint_id") or "").strip()
    ]

    unsafe_sunset_or_undocumented_endpoint_ids: list[str] = []
    short_notice_or_missing_header_endpoint_ids: list[str] = []

    for ep in valid_endpoints:
        eid = str(ep.get("endpoint_id")).strip()
        notice_days = float(
            ep.get("notice_period_days_granted", 90)
            if ep.get("notice_period_days_granted") is not None
            else 90
        )
        days_until_sunset = float(
            ep.get("days_until_sunset", 30)
            if ep.get("days_until_sunset") is not None
            else 30
        )
        active_consumers = int(
            ep.get("active_consumers_count", 0)
            if ep.get("active_consumers_count") is not None
            else 0
        )
        has_migration_guide = bool(
            ep.get("has_published_migration_guide_in_wiki", True)
            if ep.get("has_published_migration_guide_in_wiki") is not None
            else True
        )
        emits_headers = bool(
            ep.get("emits_rfc8594_sunset_headers", True)
            if ep.get("emits_rfc8594_sunset_headers") is not None
            else True
        )

        if not has_migration_guide or (
            days_until_sunset <= 0
            and active_consumers > max_remaining_active_consumers_at_sunset
        ):
            unsafe_sunset_or_undocumented_endpoint_ids.append(eid)

        if (
            notice_days < min_sunset_notice_days
            or not emits_headers
            or (days_until_sunset <= 14 and active_consumers > 0)
        ):
            short_notice_or_missing_header_endpoint_ids.append(eid)

    if unsafe_sunset_or_undocumented_endpoint_ids:
        api_sunset_governance_status = (
            "API_SUNSET_BREAKING_OR_UNDOCUMENTED_BREACH"
        )
    elif short_notice_or_missing_header_endpoint_ids:
        api_sunset_governance_status = "API_SUNSET_NOTICE_OR_MIGRATION_WARNING"
    else:
        api_sunset_governance_status = "API_SUNSET_GOVERNANCE_OPTIMAL"

    return {
        "evaluated_endpoints_count": len(valid_endpoints),
        "unsafe_sunset_or_undocumented_endpoint_ids": unsafe_sunset_or_undocumented_endpoint_ids,
        "short_notice_or_missing_header_endpoint_ids": short_notice_or_missing_header_endpoint_ids,
        "api_sunset_governance_status": api_sunset_governance_status,
        "is_api_sunset_compliant": api_sunset_governance_status
        == "API_SUNSET_GOVERNANCE_OPTIMAL",
    }


WikiPMIService.audit_wiki_api_deprecation_sunset_and_consumer_migration = staticmethod(
    audit_wiki_api_deprecation_sunset_and_consumer_migration
)


def audit_wiki_runbook_automation_toil_and_idempotency(
    runbooks: Sequence[Mapping[str, Any]] | None,
    *,
    max_manual_steps_allowed: int = 3,
    max_toil_hours_per_month: float = 10.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §10.2 — Wiki SRE Runbook Automation Coverage, Operational Toil Cap & Script Idempotency Auditor."""
    valid_runbooks = [
        rb
        for rb in (runbooks or [])
        if isinstance(rb, Mapping) and str(rb.get("runbook_id") or "").strip()
    ]

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    unsafe_or_non_idempotent_runbook_ids: list[str] = []
    high_toil_or_missing_dry_run_runbook_ids: list[str] = []

    for rb in valid_runbooks:
        rid = str(rb.get("runbook_id")).strip()
        manual_steps = _num(
            rb.get("manual_cli_steps_count"), 1.0
        )
        toil_hours = _num(
            rb.get("monthly_toil_hours_consumed"), 2.0
        )
        scripts_idempotent = _bool(
            rb.get("automation_scripts_idempotent"), True
        )
        dry_run_supported = _bool(
            rb.get("dry_run_mode_supported"), True
        )
        peer_reviewed_staging = _bool(
            rb.get("peer_reviewed_and_tested_in_staging"), True
        )

        if not scripts_idempotent or not peer_reviewed_staging:
            unsafe_or_non_idempotent_runbook_ids.append(rid)

        if (
            manual_steps > max_manual_steps_allowed
            or toil_hours > max_toil_hours_per_month
            or not dry_run_supported
        ):
            high_toil_or_missing_dry_run_runbook_ids.append(rid)

    if unsafe_or_non_idempotent_runbook_ids:
        runbook_automation_status = "RUNBOOK_IDEMPOTENCY_OR_STAGING_BREACH"
    elif high_toil_or_missing_dry_run_runbook_ids:
        runbook_automation_status = "RUNBOOK_TOIL_OR_DRY_RUN_WARNING"
    else:
        runbook_automation_status = "RUNBOOK_AUTOMATION_OPTIMAL"

    return {
        "evaluated_runbooks_count": len(valid_runbooks),
        "unsafe_or_non_idempotent_runbook_ids": unsafe_or_non_idempotent_runbook_ids,
        "high_toil_or_missing_dry_run_runbook_ids": high_toil_or_missing_dry_run_runbook_ids,
        "runbook_automation_status": runbook_automation_status,
        "is_runbook_automation_compliant": runbook_automation_status
        == "RUNBOOK_AUTOMATION_OPTIMAL",
    }


WikiPMIService.audit_wiki_runbook_automation_toil_and_idempotency = staticmethod(
    audit_wiki_runbook_automation_toil_and_idempotency
)


def audit_wiki_chaos_gameday_hypothesis_and_blast_radius(
    chaos_experiments: Sequence[Mapping[str, Any]] | None,
    *,
    max_blast_radius_tenants_pct: float = 5.0,
    max_unremediated_findings_days: int | float = 14,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §8.2 — Wiki Chaos Engineering GameDay Hypothesis Verification, Blast-Radius Containment & Abort-Switch Auditor."""
    valid_experiments = [
        exp
        for exp in (chaos_experiments or [])
        if isinstance(exp, Mapping) and str(exp.get("experiment_id") or "").strip()
    ]

    unsafe_or_uncontained_experiment_ids: list[str] = []
    overdue_remediation_experiment_ids: list[str] = []

    for exp in valid_experiments:
        eid = str(exp.get("experiment_id")).strip()
        hypothesis_defined = bool(
            exp.get("steady_state_hypothesis_defined", True)
            if exp.get("steady_state_hypothesis_defined") is not None
            else True
        )
        abort_switch_verified = bool(
            exp.get("automated_abort_switch_verified", True)
            if exp.get("automated_abort_switch_verified") is not None
            else True
        )
        blast_radius_pct = float(
            exp.get("blast_radius_tenants_pct", 1.0)
            if exp.get("blast_radius_tenants_pct") is not None
            else 1.0
        )
        unremediated_gaps = int(
            exp.get("unremediated_resilience_gaps_count", 0)
            if exp.get("unremediated_resilience_gaps_count") is not None
            else 0
        )
        days_since_gameday = float(
            exp.get("days_since_gameday_execution", 7)
            if exp.get("days_since_gameday_execution") is not None
            else 7
        )

        if (
            not hypothesis_defined
            or not abort_switch_verified
            or blast_radius_pct > max_blast_radius_tenants_pct
        ):
            unsafe_or_uncontained_experiment_ids.append(eid)

        if (
            unremediated_gaps > 0
            and days_since_gameday > max_unremediated_findings_days
        ):
            overdue_remediation_experiment_ids.append(eid)

    if unsafe_or_uncontained_experiment_ids:
        chaos_gameday_status = "CHAOS_ABORT_SWITCH_OR_BLAST_RADIUS_BREACH"
    elif overdue_remediation_experiment_ids:
        chaos_gameday_status = "CHAOS_RESILIENCE_GAP_REMEDIATION_WARNING"
    else:
        chaos_gameday_status = "CHAOS_GAMEDAY_GOVERNANCE_OPTIMAL"

    return {
        "evaluated_experiments_count": len(valid_experiments),
        "unsafe_or_uncontained_experiment_ids": unsafe_or_uncontained_experiment_ids,
        "overdue_remediation_experiment_ids": overdue_remediation_experiment_ids,
        "chaos_gameday_status": chaos_gameday_status,
        "is_chaos_gameday_compliant": chaos_gameday_status
        == "CHAOS_GAMEDAY_GOVERNANCE_OPTIMAL",
    }


WikiPMIService.audit_wiki_chaos_gameday_hypothesis_and_blast_radius = staticmethod(
    audit_wiki_chaos_gameday_hypothesis_and_blast_radius
)


def audit_wiki_observability_cardinality_and_trace_sampling(
    telemetry_pipelines: Sequence[Mapping[str, Any]] | None,
    *,
    max_metric_label_cardinality: int = 10000,
    min_error_trace_tail_sampling_pct: float = 100.0,
) -> dict[str, Any]:
    """PMI PMBOK §8.2 & §10.2 — Wiki Observability Telemetry Cardinality Explosion, OpenTelemetry Trace Sampling & Log Retention Tiering Auditor."""
    valid_pipelines = [
        pl
        for pl in (telemetry_pipelines or [])
        if isinstance(pl, Mapping) and str(pl.get("pipeline_id") or "").strip()
    ]

    cardinality_explosion_or_blind_trace_pipeline_ids: list[str] = []
    high_cardinality_or_untiered_log_pipeline_ids: list[str] = []

    for pl in valid_pipelines:
        pid = str(pl.get("pipeline_id")).strip()
        cardinality = int(
            pl.get("observed_metric_series_cardinality", 1500)
            if pl.get("observed_metric_series_cardinality") is not None
            else 1500
        )
        unbounded_labels = bool(
            pl.get("unbounded_user_id_or_uuid_labels_detected", False)
            if pl.get("unbounded_user_id_or_uuid_labels_detected") is not None
            else False
        )
        error_sampling_pct = float(
            pl.get("error_trace_tail_sampling_pct", 100.0)
            if pl.get("error_trace_tail_sampling_pct") is not None
            else 100.0
        )
        w3c_propagated = bool(
            pl.get("w3c_trace_context_propagated", True)
            if pl.get("w3c_trace_context_propagated") is not None
            else True
        )
        cold_tiering = bool(
            pl.get("cold_storage_log_tiering_configured", True)
            if pl.get("cold_storage_log_tiering_configured") is not None
            else True
        )

        if (
            unbounded_labels
            or not w3c_propagated
            or error_sampling_pct < min_error_trace_tail_sampling_pct
        ):
            cardinality_explosion_or_blind_trace_pipeline_ids.append(pid)

        if (
            cardinality > max_metric_label_cardinality
            or not cold_tiering
        ):
            high_cardinality_or_untiered_log_pipeline_ids.append(pid)

    if cardinality_explosion_or_blind_trace_pipeline_ids:
        observability_hygiene_status = (
            "OBSERVABILITY_CARDINALITY_OR_BLIND_TRACE_BREACH"
        )
    elif high_cardinality_or_untiered_log_pipeline_ids:
        observability_hygiene_status = (
            "OBSERVABILITY_SERIES_PRESSURE_OR_TIERING_WARNING"
        )
    else:
        observability_hygiene_status = "OBSERVABILITY_TELEMETRY_OPTIMAL"

    return {
        "evaluated_pipelines_count": len(valid_pipelines),
        "cardinality_explosion_or_blind_trace_pipeline_ids": cardinality_explosion_or_blind_trace_pipeline_ids,
        "high_cardinality_or_untiered_log_pipeline_ids": high_cardinality_or_untiered_log_pipeline_ids,
        "observability_hygiene_status": observability_hygiene_status,
        "is_observability_hygiene_compliant": observability_hygiene_status
        == "OBSERVABILITY_TELEMETRY_OPTIMAL",
    }


WikiPMIService.audit_wiki_observability_cardinality_and_trace_sampling = staticmethod(
    audit_wiki_observability_cardinality_and_trace_sampling
)


def audit_wiki_service_catalog_ownership_and_dependency_graph(
    catalog_services: Sequence[Mapping[str, Any]] | None,
    *,
    max_dependency_fan_out: int = 15,
) -> dict[str, Any]:
    """PMI PMBOK §9.1 & §10.2 — Wiki Service Catalog Tier-1 Ownership, PagerDuty Escalation Policy & Circular Dependency Graph Auditor."""
    valid_services = [
        svc
        for svc in (catalog_services or [])
        if isinstance(svc, Mapping) and str(svc.get("service_id") or "").strip()
    ]

    unowned_or_circular_dependency_service_ids: list[str] = []
    high_fan_out_or_unlinked_slo_service_ids: list[str] = []

    for svc in valid_services:
        sid = str(svc.get("service_id")).strip()
        raw_tier = svc.get("criticality_tier")
        tier = int(raw_tier if raw_tier is not None else 2)
        has_owner = bool(
            svc.get("has_accountable_team_owner", True)
            if svc.get("has_accountable_team_owner") is not None
            else True
        )
        has_pagerduty = bool(
            svc.get("has_pagerduty_escalation_policy", True)
            if svc.get("has_pagerduty_escalation_policy") is not None
            else True
        )
        circular_dep = bool(
            svc.get("circular_runtime_dependency_detected", False)
            if svc.get("circular_runtime_dependency_detected") is not None
            else False
        )
        raw_fan_out = svc.get("synchronous_downstream_fan_out_count")
        fan_out = int(raw_fan_out if raw_fan_out is not None else 4)
        slo_linked = bool(
            svc.get("slo_dashboard_linked_in_wiki", True)
            if svc.get("slo_dashboard_linked_in_wiki") is not None
            else True
        )

        if (
            not has_owner
            or circular_dep
            or (tier == 1 and not has_pagerduty)
        ):
            unowned_or_circular_dependency_service_ids.append(sid)

        if fan_out > max_dependency_fan_out or not slo_linked:
            high_fan_out_or_unlinked_slo_service_ids.append(sid)

    if unowned_or_circular_dependency_service_ids:
        service_catalog_status = "SERVICE_CATALOG_OWNERSHIP_OR_CYCLE_BREACH"
    elif high_fan_out_or_unlinked_slo_service_ids:
        service_catalog_status = "SERVICE_CATALOG_FAN_OUT_OR_SLO_WARNING"
    else:
        service_catalog_status = "SERVICE_CATALOG_GOVERNANCE_OPTIMAL"

    return {
        "evaluated_services_count": len(valid_services),
        "unowned_or_circular_dependency_service_ids": unowned_or_circular_dependency_service_ids,
        "high_fan_out_or_unlinked_slo_service_ids": high_fan_out_or_unlinked_slo_service_ids,
        "service_catalog_status": service_catalog_status,
        "is_service_catalog_compliant": service_catalog_status
        == "SERVICE_CATALOG_GOVERNANCE_OPTIMAL",
    }


WikiPMIService.audit_wiki_service_catalog_ownership_and_dependency_graph = staticmethod(
    audit_wiki_service_catalog_ownership_and_dependency_graph
)


def audit_wiki_tls_certificate_expiration_and_acme_renewal(
    certificates: Sequence[Mapping[str, Any]] | None,
    *,
    min_days_before_expiry_warning: int | float = 21,
    critical_expiry_days_threshold: int | float = 7,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §10.2 — Wiki Certificate Authority (mTLS/TLS) Expiration Horizon, ACME Auto-Renewal & Cipher Suite Hygiene Auditor."""
    valid_certs = [
        crt
        for crt in (certificates or [])
        if isinstance(crt, Mapping) and str(crt.get("cert_id") or "").strip()
    ]

    expired_imminent_or_weak_cipher_cert_ids: list[str] = []
    renewal_window_or_manual_cert_ids: list[str] = []

    for crt in valid_certs:
        cid = str(crt.get("cert_id")).strip()
        days_until_expiration = float(
            crt.get("days_until_expiration", 60)
            if crt.get("days_until_expiration") is not None
            else 60
        )
        acme_auto_renewal_enabled = bool(
            crt.get("acme_auto_renewal_enabled", True)
            if crt.get("acme_auto_renewal_enabled") is not None
            else True
        )
        uses_deprecated_tls10_or_tls11_or_weak_cipher = bool(
            crt.get("uses_deprecated_tls10_or_tls11_or_weak_cipher", False)
            if crt.get("uses_deprecated_tls10_or_tls11_or_weak_cipher") is not None
            else False
        )
        ocsp_stapling_and_ct_logged = bool(
            crt.get("ocsp_stapling_and_ct_logged", True)
            if crt.get("ocsp_stapling_and_ct_logged") is not None
            else True
        )

        if (
            days_until_expiration <= critical_expiry_days_threshold
            or uses_deprecated_tls10_or_tls11_or_weak_cipher
        ):
            expired_imminent_or_weak_cipher_cert_ids.append(cid)

        if (
            (
                days_until_expiration <= min_days_before_expiry_warning
                and days_until_expiration > critical_expiry_days_threshold
            )
            or not acme_auto_renewal_enabled
            or not ocsp_stapling_and_ct_logged
        ):
            renewal_window_or_manual_cert_ids.append(cid)

    if expired_imminent_or_weak_cipher_cert_ids:
        tls_certificate_status = "TLS_CERTIFICATE_EXPIRY_OR_CIPHER_BREACH"
    elif renewal_window_or_manual_cert_ids:
        tls_certificate_status = "TLS_RENEWAL_WINDOW_OR_ACME_WARNING"
    else:
        tls_certificate_status = "TLS_CRYPTO_LIFECYCLE_OPTIMAL"

    return {
        "evaluated_certificates_count": len(valid_certs),
        "expired_imminent_or_weak_cipher_cert_ids": expired_imminent_or_weak_cipher_cert_ids,
        "renewal_window_or_manual_cert_ids": renewal_window_or_manual_cert_ids,
        "tls_certificate_status": tls_certificate_status,
        "is_tls_certificate_compliant": tls_certificate_status
        == "TLS_CRYPTO_LIFECYCLE_OPTIMAL",
    }


WikiPMIService.audit_wiki_tls_certificate_expiration_and_acme_renewal = staticmethod(
    audit_wiki_tls_certificate_expiration_and_acme_renewal
)


def audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction(
    workloads: Sequence[Mapping[str, Any]] | None,
    *,
    min_hpa_replica_headroom_pct: float = 20.0,
    max_oomkill_restarts_last_7d: int = 0,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §9.2 — Wiki Kubernetes PodDisruptionBudget (PDB), HPA Autoscaling Headroom & OOMKill Eviction Hygiene Auditor."""
    valid_workloads = [
        workload
        for workload in (workloads or [])
        if isinstance(workload, Mapping)
        and str(workload.get("workload_id") or "").strip()
    ]

    def _bool(value: Any, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    def _num(value: Any, default: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    oomkill_or_missing_pdb_workload_ids: list[str] = []
    low_headroom_or_coupled_probes_workload_ids: list[str] = []

    for workload in valid_workloads:
        workload_id = str(workload.get("workload_id")).strip()
        oomkill_restarts = _num(
            workload.get("oomkill_restarts_last_7d"), 0.0
        )
        pdb_ok = _bool(
            workload.get("pdb_configured_and_non_blocking"), True
        )
        headroom_pct = _num(
            workload.get("hpa_replica_headroom_pct"), 35.0
        )
        topology_spread = _bool(
            workload.get("multi_az_topology_spread_enforced"), True
        )
        probes_distinct = _bool(
            workload.get("liveness_and_readiness_probes_distinct"), True
        )

        if (
            oomkill_restarts > max_oomkill_restarts_last_7d
            or not pdb_ok
            or not topology_spread
        ):
            oomkill_or_missing_pdb_workload_ids.append(workload_id)

        if (
            headroom_pct < min_hpa_replica_headroom_pct
            or not probes_distinct
        ):
            low_headroom_or_coupled_probes_workload_ids.append(workload_id)

    if oomkill_or_missing_pdb_workload_ids:
        k8s_resilience_status = "K8S_OOMKILL_OR_PDB_TOPOLOGY_BREACH"
    elif low_headroom_or_coupled_probes_workload_ids:
        k8s_resilience_status = "K8S_HPA_HEADROOM_OR_PROBE_WARNING"
    else:
        k8s_resilience_status = "K8S_WORKLOAD_RESILIENCE_OPTIMAL"

    return {
        "evaluated_workloads_count": len(valid_workloads),
        "oomkill_or_missing_pdb_workload_ids": oomkill_or_missing_pdb_workload_ids,
        "low_headroom_or_coupled_probes_workload_ids": low_headroom_or_coupled_probes_workload_ids,
        "k8s_resilience_status": k8s_resilience_status,
        "is_k8s_resilience_compliant": k8s_resilience_status
        == "K8S_WORKLOAD_RESILIENCE_OPTIMAL",
    }


WikiPMIService.audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction = staticmethod(
    audit_wiki_k8s_pdb_hpa_headroom_and_oomkill_eviction
)


def audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience(
    zones: list[dict[str, Any]] | None,
    *,
    max_failover_ttl_seconds: int = 60,
    require_dnssec_and_caa_records: bool = True,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §8.2 — Wiki DNS Failover TTL Hygiene, BGP Anycast Multi-Provider Resilience & DNSSEC/CAA Record Auditor."""
    raw_zones = zones if isinstance(zones, list) else []
    valid_zones = [
        z
        for z in raw_zones
        if isinstance(z, dict)
        and isinstance(z.get("zone_id"), str)
        and z["zone_id"].strip()
    ]

    unverified_failover_or_missing_dnssec_zone_ids: list[str] = []
    high_ttl_or_single_provider_zone_ids: list[str] = []

    for z in valid_zones:
        zid = str(z["zone_id"]).strip()
        failover_ttl_seconds = int(
            z.get("failover_ttl_seconds", 30)
            if z.get("failover_ttl_seconds") is not None
            else 30
        )
        dnssec_and_caa_enabled = bool(
            z.get("dnssec_and_caa_enabled", True)
            if z.get("dnssec_and_caa_enabled") is not None
            else True
        )
        multi_provider_anycast_active = bool(
            z.get("multi_provider_anycast_active", True)
            if z.get("multi_provider_anycast_active") is not None
            else True
        )
        health_check_auto_failover_verified = bool(
            z.get("health_check_auto_failover_verified", True)
            if z.get("health_check_auto_failover_verified") is not None
            else True
        )

        if (
            require_dnssec_and_caa_records and not dnssec_and_caa_enabled
        ) or not health_check_auto_failover_verified:
            unverified_failover_or_missing_dnssec_zone_ids.append(zid)

        if (
            failover_ttl_seconds > max_failover_ttl_seconds
            or not multi_provider_anycast_active
        ):
            high_ttl_or_single_provider_zone_ids.append(zid)

    if unverified_failover_or_missing_dnssec_zone_ids:
        dns_resilience_status = "DNS_FAILOVER_OR_SECURITY_RECORD_BREACH"
    elif high_ttl_or_single_provider_zone_ids:
        dns_resilience_status = "DNS_TTL_OR_SINGLE_PROVIDER_WARNING"
    else:
        dns_resilience_status = "DNS_ANYCAST_RESILIENCE_OPTIMAL"

    return {
        "evaluated_zones_count": len(valid_zones),
        "unverified_failover_or_missing_dnssec_zone_ids": unverified_failover_or_missing_dnssec_zone_ids,
        "high_ttl_or_single_provider_zone_ids": high_ttl_or_single_provider_zone_ids,
        "dns_resilience_status": dns_resilience_status,
        "is_dns_resilience_compliant": dns_resilience_status
        == "DNS_ANYCAST_RESILIENCE_OPTIMAL",
    }


WikiPMIService.audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience = staticmethod(
    audit_wiki_dns_failover_ttl_and_bgp_anycast_resilience
)


def audit_wiki_db_read_replica_lag_and_split_brain_fencing(
    clusters: Sequence[Mapping[str, Any]] | None,
    *,
    max_replication_lag_ms: float = 250.0,
    max_failover_rto_seconds: int = 30,
) -> dict[str, Any]:
    """PMI PMBOK §11.6 & §8.2 — Wiki Database Read-Replica Replication Lag, Automated Failover Promotion & Split-Brain STONITH Fencing Auditor."""
    raw_clusters = clusters if isinstance(clusters, (list, tuple)) else []
    valid_clusters = [
        c
        for c in raw_clusters
        if isinstance(c, Mapping)
        and isinstance(c.get("cluster_id"), str)
        and c["cluster_id"].strip()
    ]

    split_brain_or_unarchived_wal_cluster_ids: list[str] = []
    high_lag_or_slow_promotion_cluster_ids: list[str] = []

    for c in valid_clusters:
        cid = str(c["cluster_id"]).strip()
        replication_lag_ms = float(
            c.get("replication_lag_ms", 45.0)
            if c.get("replication_lag_ms") is not None
            else 45.0
        )
        split_brain_stonith_fencing_enabled = bool(
            c.get("split_brain_stonith_fencing_enabled", True)
            if c.get("split_brain_stonith_fencing_enabled") is not None
            else True
        )
        quorum_synchronous_commit_verified = bool(
            c.get("quorum_synchronous_commit_verified", True)
            if c.get("quorum_synchronous_commit_verified") is not None
            else True
        )
        failover_promotion_rto_seconds = int(
            c.get("failover_promotion_rto_seconds", 12)
            if c.get("failover_promotion_rto_seconds") is not None
            else 12
        )
        wal_archiving_continuous = bool(
            c.get("wal_archiving_continuous", True)
            if c.get("wal_archiving_continuous") is not None
            else True
        )

        if (
            not split_brain_stonith_fencing_enabled
            or not quorum_synchronous_commit_verified
            or not wal_archiving_continuous
        ):
            split_brain_or_unarchived_wal_cluster_ids.append(cid)

        if (
            replication_lag_ms > max_replication_lag_ms
            or failover_promotion_rto_seconds > max_failover_rto_seconds
        ):
            high_lag_or_slow_promotion_cluster_ids.append(cid)

    if split_brain_or_unarchived_wal_cluster_ids:
        db_ha_fencing_status = "DB_SPLIT_BRAIN_OR_WAL_DURABILITY_BREACH"
    elif high_lag_or_slow_promotion_cluster_ids:
        db_ha_fencing_status = "DB_REPLICA_LAG_OR_FAILOVER_RTO_WARNING"
    else:
        db_ha_fencing_status = "DB_HA_REPLICATION_FENCING_OPTIMAL"

    return {
        "evaluated_clusters_count": len(valid_clusters),
        "split_brain_or_unarchived_wal_cluster_ids": split_brain_or_unarchived_wal_cluster_ids,
        "high_lag_or_slow_promotion_cluster_ids": high_lag_or_slow_promotion_cluster_ids,
        "db_ha_fencing_status": db_ha_fencing_status,
        "is_db_ha_fencing_compliant": db_ha_fencing_status
        == "DB_HA_REPLICATION_FENCING_OPTIMAL",
    }


WikiPMIService.audit_wiki_db_read_replica_lag_and_split_brain_fencing = staticmethod(
    audit_wiki_db_read_replica_lag_and_split_brain_fencing
)


def audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection(
    edges: list[dict] | None,
    *,
    max_purge_propagation_seconds: int = 30,
    min_origin_shield_offload_pct: float = 90.0,
) -> dict:
    """PMBOK §8.2 & §11.6 — Audita SLA de propagación de purga de caché CDN edge, protección de Origin Shield y mitigación WAF bot-challenge."""
    raw_items = edges if isinstance(edges, list) else []
    valid_edges: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("edge_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_edges.append(item)

    unshielded_or_waf_disabled_edge_ids: list[str] = []
    slow_purge_or_low_offload_edge_ids: list[str] = []

    for e in valid_edges:
        eid = e["edge_id"].strip()
        raw_shield = e.get("origin_shield_enabled", True)
        origin_shield_enabled = bool(
            True if raw_shield is None else raw_shield
        )

        raw_waf = e.get("waf_ddos_challenge_active", True)
        waf_ddos_challenge_active = bool(True if raw_waf is None else raw_waf)

        raw_purge = e.get("purge_propagation_seconds", 8)
        purge_propagation_seconds = int(8 if raw_purge is None else raw_purge)

        raw_offload = e.get("origin_shield_offload_pct", 96.0)
        origin_shield_offload_pct = float(
            96.0 if raw_offload is None else raw_offload
        )

        if not origin_shield_enabled or not waf_ddos_challenge_active:
            unshielded_or_waf_disabled_edge_ids.append(eid)

        if (
            purge_propagation_seconds > max_purge_propagation_seconds
            or origin_shield_offload_pct < min_origin_shield_offload_pct
        ):
            slow_purge_or_low_offload_edge_ids.append(eid)

    if unshielded_or_waf_disabled_edge_ids:
        cdn_edge_status = "CDN_ORIGIN_SHIELD_OR_WAF_BREACH"
    elif slow_purge_or_low_offload_edge_ids:
        cdn_edge_status = "CDN_PURGE_SLA_OR_OFFLOAD_WARNING"
    else:
        cdn_edge_status = "CDN_EDGE_DELIVERY_OPTIMAL"

    return {
        "evaluated_edges_count": len(valid_edges),
        "unshielded_or_waf_disabled_edge_ids": unshielded_or_waf_disabled_edge_ids,
        "slow_purge_or_low_offload_edge_ids": slow_purge_or_low_offload_edge_ids,
        "cdn_edge_status": cdn_edge_status,
        "is_cdn_edge_compliant": cdn_edge_status
        == "CDN_EDGE_DELIVERY_OPTIMAL",
    }


WikiPMIService.audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection = staticmethod(
    audit_wiki_cdn_edge_cache_purge_sla_and_origin_shield_protection
)

def audit_wiki_object_storage_worm_lock_and_ransomware_airgap(
    buckets: list[dict] | None,
    *,
    min_retention_lock_days: int = 90,
    max_cross_account_replication_lag_minutes: int = 15,
) -> dict:
    """PMBOK §11.6 & §10.2 — Audita object-lock WORM inmutable, MFA-Delete/block público y air-gap cross-account anti-ransomware."""
    raw_items = buckets if isinstance(buckets, list) else []
    valid_buckets: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("bucket_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_buckets.append(item)

    def _num(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    mutable_or_public_exposed_bucket_ids: list[str] = []
    short_retention_or_slow_airgap_bucket_ids: list[str] = []

    for bucket in valid_buckets:
        bucket_id = str(bucket.get("bucket_id")).strip()
        worm_lock = _bool(
            bucket.get("worm_compliance_lock_enabled"), True
        )
        mfa_delete_block = _bool(
            bucket.get("mfa_delete_and_public_block_enforced"), True
        )
        retention_days = _num(
            bucket.get("retention_lock_days"), 365.0
        )
        airgap_lag_minutes = _num(
            bucket.get("cross_account_airgap_lag_minutes"), 5.0
        )

        if not worm_lock or not mfa_delete_block:
            mutable_or_public_exposed_bucket_ids.append(bucket_id)

        if (
            retention_days < min_retention_lock_days
            or airgap_lag_minutes > max_cross_account_replication_lag_minutes
        ):
            short_retention_or_slow_airgap_bucket_ids.append(bucket_id)

    if mutable_or_public_exposed_bucket_ids:
        worm_airgap_status = "WORM_OBJECT_LOCK_OR_EXPOSURE_BREACH"
    elif short_retention_or_slow_airgap_bucket_ids:
        worm_airgap_status = "WORM_RETENTION_OR_AIRGAP_LAG_WARNING"
    else:
        worm_airgap_status = "WORM_RANSOMWARE_AIRGAP_OPTIMAL"

    return {
        "evaluated_buckets_count": len(valid_buckets),
        "mutable_or_public_exposed_bucket_ids": mutable_or_public_exposed_bucket_ids,
        "short_retention_or_slow_airgap_bucket_ids": short_retention_or_slow_airgap_bucket_ids,
        "worm_airgap_status": worm_airgap_status,
        "is_worm_airgap_compliant": worm_airgap_status
        == "WORM_RANSOMWARE_AIRGAP_OPTIMAL",
    }


WikiPMIService.audit_wiki_object_storage_worm_lock_and_ransomware_airgap = staticmethod(
    audit_wiki_object_storage_worm_lock_and_ransomware_airgap
)


def audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover(
    prefixes: list[dict] | None,
    *,
    max_scrubbing_diversion_seconds: int = 45,
    require_rpki_roa_and_bfd: bool = True,
) -> dict:
    """PMBOK §11.6 & §8.2 — Audita validación criptográfica RPKI ROA contra secuestro de rutas BGP, liveness BFD subsegundo en sesiones de peering y failover de centro de scrubbing DDoS."""
    raw_items = prefixes if isinstance(prefixes, list) else []
    valid_prefixes: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("prefix_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_prefixes.append(item)

    unsigned_rpki_or_missing_bfd_prefix_ids: list[str] = []
    slow_scrubbing_or_single_homed_prefix_ids: list[str] = []

    for p in valid_prefixes:
        pid = p["prefix_id"].strip()
        raw_rpki = p.get("rpki_roa_cryptographically_valid", True)
        rpki_roa_cryptographically_valid = bool(
            True if raw_rpki is None else raw_rpki
        )

        raw_bfd = p.get("bfd_subsecond_peering_enabled", True)
        bfd_subsecond_peering_enabled = bool(
            True if raw_bfd is None else raw_bfd
        )

        raw_scrub = p.get("scrubbing_diversion_seconds", 15)
        scrubbing_diversion_seconds = int(
            15 if raw_scrub is None else raw_scrub
        )

        raw_asns = p.get("redundant_transit_asns_count", 2)
        redundant_transit_asns_count = int(
            2 if raw_asns is None else raw_asns
        )

        if require_rpki_roa_and_bfd and (
            not rpki_roa_cryptographically_valid
            or not bfd_subsecond_peering_enabled
        ):
            unsigned_rpki_or_missing_bfd_prefix_ids.append(pid)

        if (
            scrubbing_diversion_seconds > max_scrubbing_diversion_seconds
            or redundant_transit_asns_count < 2
        ):
            slow_scrubbing_or_single_homed_prefix_ids.append(pid)

    if unsigned_rpki_or_missing_bfd_prefix_ids:
        bgp_routing_status = "BGP_RPKI_ROA_OR_BFD_LIVENESS_BREACH"
    elif slow_scrubbing_or_single_homed_prefix_ids:
        bgp_routing_status = "BGP_SCRUBBING_DIVERSION_OR_SINGLE_ASN_WARNING"
    else:
        bgp_routing_status = "BGP_ROUTING_AND_SCRUBBING_OPTIMAL"

    return {
        "evaluated_prefixes_count": len(valid_prefixes),
        "unsigned_rpki_or_missing_bfd_prefix_ids": unsigned_rpki_or_missing_bfd_prefix_ids,
        "slow_scrubbing_or_single_homed_prefix_ids": slow_scrubbing_or_single_homed_prefix_ids,
        "bgp_routing_status": bgp_routing_status,
        "is_bgp_routing_compliant": bgp_routing_status
        == "BGP_ROUTING_AND_SCRUBBING_OPTIMAL",
    }


WikiPMIService.audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover = staticmethod(
    audit_wiki_bgp_rpki_roa_and_ddos_scrubbing_failover
)


def audit_wiki_secrets_vault_lease_rotation_and_root_token_seal(
    vaults: list[dict] | None,
    *,
    max_dynamic_lease_ttl_hours: int = 24,
    require_root_token_revoked: bool = True,
) -> dict:
    """PMBOK §11.6 & §10.2 — Audita rotación de concesiones dinámicas (leases) en bóvedas de secretos de la Wiki, revocación/sellado de root tokens y quórum de auto-unseal Shamir/KMS."""
    raw_items = vaults if isinstance(vaults, list) else []
    valid_vaults: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("vault_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_vaults.append(item)

    active_root_token_or_unverified_unseal_vault_ids: list[str] = []
    long_lease_or_static_secret_vault_ids: list[str] = []

    for v in valid_vaults:
        vid = str(v["vault_id"]).strip()
        raw_root = v.get("root_tokens_revoked_and_audited", True)
        root_tokens_revoked_and_audited = bool(
            True if raw_root is None else raw_root
        )

        raw_unseal = v.get("hsm_kms_auto_unseal_quorum_verified", True)
        hsm_kms_auto_unseal_quorum_verified = bool(
            True if raw_unseal is None else raw_unseal
        )

        raw_ttl = v.get("dynamic_lease_ttl_hours", 8)
        dynamic_lease_ttl_hours = int(8 if raw_ttl is None else raw_ttl)

        raw_static = v.get("static_long_lived_secrets_count", 0)
        static_long_lived_secrets_count = int(
            0 if raw_static is None else raw_static
        )

        if (
            require_root_token_revoked and not root_tokens_revoked_and_audited
        ) or not hsm_kms_auto_unseal_quorum_verified:
            active_root_token_or_unverified_unseal_vault_ids.append(vid)

        if (
            dynamic_lease_ttl_hours > max_dynamic_lease_ttl_hours
            or static_long_lived_secrets_count > 0
        ):
            long_lease_or_static_secret_vault_ids.append(vid)

    if active_root_token_or_unverified_unseal_vault_ids:
        secrets_vault_status = "VAULT_ROOT_TOKEN_OR_UNSEAL_QUORUM_BREACH"
    elif long_lease_or_static_secret_vault_ids:
        secrets_vault_status = "VAULT_LEASE_TTL_OR_STATIC_SECRET_WARNING"
    else:
        secrets_vault_status = "VAULT_DYNAMIC_SECRETS_OPTIMAL"

    return {
        "evaluated_vaults_count": len(valid_vaults),
        "active_root_token_or_unverified_unseal_vault_ids": active_root_token_or_unverified_unseal_vault_ids,
        "long_lease_or_static_secret_vault_ids": long_lease_or_static_secret_vault_ids,
        "secrets_vault_status": secrets_vault_status,
        "is_secrets_vault_compliant": secrets_vault_status
        == "VAULT_DYNAMIC_SECRETS_OPTIMAL",
    }


WikiPMIService.audit_wiki_secrets_vault_lease_rotation_and_root_token_seal = staticmethod(
    audit_wiki_secrets_vault_lease_rotation_and_root_token_seal
)


def audit_wiki_ntp_clock_drift_and_leap_second_smearing(
    nodes: list[dict] | None,
    *,
    max_clock_offset_ms: float = 10.0,
    max_stratum_level: int = 3,
) -> dict:
    """PMBOK §11.6 & §8.2 — Audita drift de sincronización NTP/PTP por stratum, fuentes de tiempo autenticadas NTS y smearing consistente de leap second."""
    raw_items = nodes if isinstance(nodes, list) else []
    valid_nodes: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("node_id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            continue
        valid_nodes.append(item)

    def _num(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    unauthenticated_or_unsmeared_leap_node_ids: list[str] = []
    high_drift_or_degraded_stratum_node_ids: list[str] = []

    for node in valid_nodes:
        node_id = str(node.get("node_id")).strip()
        nts_authenticated = _bool(
            node.get("nts_authenticated_time_sources"), True
        )
        smearing_consistent = _bool(
            node.get("leap_second_smearing_consistent"), True
        )
        clock_offset_ms = _num(
            node.get("observed_clock_offset_ms"), 1.5
        )
        stratum_level = _num(
            node.get("stratum_level"), 2.0
        )

        if not nts_authenticated or not smearing_consistent:
            unauthenticated_or_unsmeared_leap_node_ids.append(node_id)

        if (
            abs(clock_offset_ms) > max_clock_offset_ms
            or stratum_level > max_stratum_level
        ):
            high_drift_or_degraded_stratum_node_ids.append(node_id)

    if unauthenticated_or_unsmeared_leap_node_ids:
        clock_sync_status = "CLOCK_NTS_AUTH_OR_LEAP_SMEAR_BREACH"
    elif high_drift_or_degraded_stratum_node_ids:
        clock_sync_status = "CLOCK_OFFSET_DRIFT_OR_STRATUM_WARNING"
    else:
        clock_sync_status = "CLOCK_SYNCHRONIZATION_OPTIMAL"

    return {
        "evaluated_nodes_count": len(valid_nodes),
        "unauthenticated_or_unsmeared_leap_node_ids": unauthenticated_or_unsmeared_leap_node_ids,
        "high_drift_or_degraded_stratum_node_ids": high_drift_or_degraded_stratum_node_ids,
        "clock_sync_status": clock_sync_status,
        "is_clock_sync_compliant": clock_sync_status
        == "CLOCK_SYNCHRONIZATION_OPTIMAL",
    }


WikiPMIService.audit_wiki_ntp_clock_drift_and_leap_second_smearing = staticmethod(
    audit_wiki_ntp_clock_drift_and_leap_second_smearing
)


def audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety(
    probe_samples: list[dict[str, Any]],
    *,
    max_ringbuffer_drop_rate_pct: float = 0.5,
    max_cpu_overhead_pct: float = 2.0,
    require_btf_core_portability: bool = True,
) -> dict[str, Any]:
    """PMBOK §11.6 & §8.2 — Audita seguridad del verificador eBPF, tasa de descarte en ring-buffer, sobrecarga de CPU y portabilidad BTF CO-RE."""
    raw_items = probe_samples if isinstance(probe_samples, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    unsafe_probe_ids: list[str] = []
    dropping_or_high_cpu_probe_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        probe_id = (
            str(
                item.get("probe_id") or item.get("id") or f"probe-{idx + 1}"
            ).strip()
            or f"probe-{idx + 1}"
        )

        raw_verifier = item.get("verifier_passed", True)
        verifier_passed = bool(True if raw_verifier is None else raw_verifier)

        raw_btf = item.get("btf_core_enabled", True)
        btf_core_enabled = bool(True if raw_btf is None else raw_btf)

        events_emitted = max(0, int(item.get("events_emitted") or 0))
        events_dropped = max(0, int(item.get("events_dropped") or 0))
        cpu_overhead_pct = max(0.0, float(item.get("cpu_overhead_pct") or 0.0))

        raw_loop = item.get("unbounded_loop_detected", False)
        unbounded_loop_detected = bool(False if raw_loop is None else raw_loop)

        total_events = events_emitted + events_dropped
        if total_events > 0:
            ringbuffer_drop_rate_pct = round(
                (events_dropped / total_events) * 100.0, 4
            )
        else:
            ringbuffer_drop_rate_pct = 0.0

        verifier_or_loop_safety_breach = (
            not verifier_passed or unbounded_loop_detected
        )
        ringbuffer_drop_rate_exceeded = (
            ringbuffer_drop_rate_pct > max_ringbuffer_drop_rate_pct
        )
        cpu_overhead_budget_exceeded = cpu_overhead_pct > max_cpu_overhead_pct
        btf_core_missing = bool(
            require_btf_core_portability and not btf_core_enabled
        )

        if verifier_or_loop_safety_breach:
            unsafe_probe_ids.append(probe_id)
            has_critical = True
            violations.append(
                f"Probe '{probe_id}' failed eBPF verifier or has unbounded loop."
            )

        if ringbuffer_drop_rate_exceeded or cpu_overhead_budget_exceeded:
            dropping_or_high_cpu_probe_ids.append(probe_id)
            has_warning = True
            if ringbuffer_drop_rate_exceeded:
                violations.append(
                    f"Probe '{probe_id}' ringbuffer drop rate {ringbuffer_drop_rate_pct}% exceeds {max_ringbuffer_drop_rate_pct}%."
                )
            if cpu_overhead_budget_exceeded:
                violations.append(
                    f"Probe '{probe_id}' CPU overhead {cpu_overhead_pct}% exceeds {max_cpu_overhead_pct}%."
                )

        if btf_core_missing:
            has_warning = True
            violations.append(
                f"Probe '{probe_id}' is missing BTF CO-RE portability."
            )

        records.append(
            {
                "probe_id": probe_id,
                "verifier_passed": verifier_passed,
                "btf_core_enabled": btf_core_enabled,
                "events_emitted": events_emitted,
                "events_dropped": events_dropped,
                "ringbuffer_drop_rate_pct": ringbuffer_drop_rate_pct,
                "cpu_overhead_pct": cpu_overhead_pct,
                "unbounded_loop_detected": unbounded_loop_detected,
                "verifier_or_loop_safety_breach": verifier_or_loop_safety_breach,
                "ringbuffer_drop_rate_exceeded": ringbuffer_drop_rate_exceeded,
                "cpu_overhead_budget_exceeded": cpu_overhead_budget_exceeded,
                "btf_core_missing": btf_core_missing,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "healthy"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "probes_evaluated": len(records),
        "unsafe_probe_ids": unsafe_probe_ids,
        "dropping_or_high_cpu_probe_ids": dropping_or_high_cpu_probe_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


WikiPMIService.audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety = staticmethod(
    audit_wiki_ebpf_kernel_probe_ringbuffer_drop_and_verifier_safety
)


def audit_wiki_otel_tail_sampling_baggage_and_span_drop(
    collector_pipelines: list[dict[str, Any]],
    *,
    max_span_drop_rate_pct: float = 1.0,
    min_error_trace_retention_pct: float = 100.0,
    max_baggage_header_bytes: int = 8192,
    require_w3c_tracecontext: bool = True,
) -> dict[str, Any]:
    """PMBOK §11.6 & §8.2 — Audita muestreo tail-based OpenTelemetry, propagación W3C TraceContext, desbordamiento de baggage y descarte de spans en colectores."""
    raw_items = (
        collector_pipelines if isinstance(collector_pipelines, list) else []
    )
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    trace_loss_pipeline_ids: list[str] = []
    degraded_pipeline_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        pipeline_id = (
            str(
                item.get("pipeline_id")
                or item.get("id")
                or f"pipeline-{idx + 1}"
            ).strip()
            or f"pipeline-{idx + 1}"
        )

        raw_w3c = item.get("w3c_tracecontext_enforced", True)
        w3c_tracecontext_enforced = bool(True if raw_w3c is None else raw_w3c)

        raw_err_ret = item.get("error_trace_retention_pct", 100.0)
        error_trace_retention_pct = float(
            100.0 if raw_err_ret is None else raw_err_ret
        )

        spans_received = max(0, int(item.get("spans_received") or 0))
        spans_dropped_queue_full = max(
            0, int(item.get("spans_dropped_queue_full") or 0)
        )
        max_observed_baggage_bytes = max(
            0, int(item.get("max_observed_baggage_bytes") or 0)
        )

        span_drop_rate_pct = (
            round((spans_dropped_queue_full / spans_received) * 100.0, 4)
            if spans_received > 0
            else 0.0
        )

        missing_w3c_tracecontext = bool(
            require_w3c_tracecontext and not w3c_tracecontext_enforced
        )
        error_trace_sampling_loss = (
            error_trace_retention_pct < min_error_trace_retention_pct
        )
        span_drop_budget_exceeded = (
            span_drop_rate_pct > max_span_drop_rate_pct
        )
        baggage_size_overflow = (
            max_observed_baggage_bytes > max_baggage_header_bytes
        )

        if missing_w3c_tracecontext or error_trace_sampling_loss:
            trace_loss_pipeline_ids.append(pipeline_id)
            has_critical = True
            if missing_w3c_tracecontext:
                violations.append(
                    f"Pipeline '{pipeline_id}' does not enforce W3C TraceContext propagation."
                )
            if error_trace_sampling_loss:
                violations.append(
                    f"Pipeline '{pipeline_id}' error trace retention {error_trace_retention_pct}% is below {min_error_trace_retention_pct}%."
                )

        if span_drop_budget_exceeded or baggage_size_overflow:
            degraded_pipeline_ids.append(pipeline_id)
            has_warning = True
            if span_drop_budget_exceeded:
                violations.append(
                    f"Pipeline '{pipeline_id}' span drop rate {span_drop_rate_pct}% exceeds {max_span_drop_rate_pct}%."
                )
            if baggage_size_overflow:
                violations.append(
                    f"Pipeline '{pipeline_id}' baggage header size {max_observed_baggage_bytes}B exceeds {max_baggage_header_bytes}B."
                )

        records.append(
            {
                "pipeline_id": pipeline_id,
                "w3c_tracecontext_enforced": w3c_tracecontext_enforced,
                "error_trace_retention_pct": error_trace_retention_pct,
                "spans_received": spans_received,
                "spans_dropped_queue_full": spans_dropped_queue_full,
                "span_drop_rate_pct": span_drop_rate_pct,
                "max_observed_baggage_bytes": max_observed_baggage_bytes,
                "missing_w3c_tracecontext": missing_w3c_tracecontext,
                "error_trace_sampling_loss": error_trace_sampling_loss,
                "span_drop_budget_exceeded": span_drop_budget_exceeded,
                "baggage_size_overflow": baggage_size_overflow,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "healthy"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "pipelines_evaluated": len(records),
        "trace_loss_pipeline_ids": trace_loss_pipeline_ids,
        "degraded_pipeline_ids": degraded_pipeline_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


WikiPMIService.audit_wiki_otel_tail_sampling_baggage_and_span_drop = staticmethod(
    audit_wiki_otel_tail_sampling_baggage_and_span_drop
)


def audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing(
    vector_shards: list[dict[str, Any]],
    *,
    min_recall_at_10_pct: float = 95.0,
    max_tombstone_fragmentation_pct: float = 20.0,
    canonical_embedding_model_version: str = "text-embedding-3-large-v1",
) -> dict[str, Any]:
    """PMBOK §4.4 & §8.2 — Audita degradación de Recall@10 en índices vectoriales HNSW, desfase de versión del modelo de embeddings y fragmentación por tombstones."""
    raw_items = vector_shards if isinstance(vector_shards, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]
    canonical_version = str(canonical_embedding_model_version).strip()

    version_skew_or_low_recall_shard_ids: list[str] = []
    fragmented_shard_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        shard_id = (
            str(
                item.get("shard_id") or item.get("id") or f"shard-{idx + 1}"
            ).strip()
            or f"shard-{idx + 1}"
        )

        raw_recall = item.get("observed_recall_at_10_pct", 100.0)
        observed_recall_at_10_pct = min(
            100.0, max(0.0, float(100.0 if raw_recall is None else raw_recall))
        )

        tombstone_fragmentation_pct = max(
            0.0, float(item.get("tombstone_fragmentation_pct") or 0.0)
        )

        raw_model = item.get(
            "embedding_model_version", "text-embedding-3-large-v1"
        )
        embedding_model_version = (
            str(
                "text-embedding-3-large-v1" if raw_model is None else raw_model
            ).strip()
            or "text-embedding-3-large-v1"
        )

        p99_ann_query_latency_ms = max(
            0.0, float(item.get("p99_ann_query_latency_ms") or 0.0)
        )

        embedding_model_version_skew = (
            embedding_model_version != canonical_version
        )
        recall_at_10_degraded = (
            observed_recall_at_10_pct < min_recall_at_10_pct
        )
        tombstone_fragmentation_exceeded = (
            tombstone_fragmentation_pct > max_tombstone_fragmentation_pct
        )

        if embedding_model_version_skew or recall_at_10_degraded:
            version_skew_or_low_recall_shard_ids.append(shard_id)
            has_critical = True
            if embedding_model_version_skew:
                violations.append(
                    f"Shard '{shard_id}' embedding model version '{embedding_model_version}' skews from canonical '{canonical_version}'."
                )
            if recall_at_10_degraded:
                violations.append(
                    f"Shard '{shard_id}' Recall@10 ({observed_recall_at_10_pct}%) below minimum ({min_recall_at_10_pct}%)."
                )

        if tombstone_fragmentation_exceeded:
            fragmented_shard_ids.append(shard_id)
            has_warning = True
            violations.append(
                f"Shard '{shard_id}' tombstone fragmentation ({tombstone_fragmentation_pct}%) exceeds {max_tombstone_fragmentation_pct}%."
            )

        records.append(
            {
                "shard_id": shard_id,
                "observed_recall_at_10_pct": observed_recall_at_10_pct,
                "tombstone_fragmentation_pct": tombstone_fragmentation_pct,
                "embedding_model_version": embedding_model_version,
                "p99_ann_query_latency_ms": p99_ann_query_latency_ms,
                "embedding_model_version_skew": embedding_model_version_skew,
                "recall_at_10_degraded": recall_at_10_degraded,
                "tombstone_fragmentation_exceeded": tombstone_fragmentation_exceeded,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "healthy"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "shards_evaluated": len(records),
        "version_skew_or_low_recall_shard_ids": version_skew_or_low_recall_shard_ids,
        "fragmented_shard_ids": fragmented_shard_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


WikiPMIService.audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing = staticmethod(
    audit_wiki_vector_embedding_hnsw_index_recall_and_drift_reindexing
)


def audit_wiki_graph_backlink_reciprocity_and_orphan_clusters(
    graph_nodes: list[dict] | None,
    *,
    max_orphan_cluster_ratio_pct: float = 5.0,
) -> dict:
    """PMBOK §4.4 & §10.2 — Audita reciprocidad de backlinks bidireccionales, clústeres de nodos huérfanos aislados y transclusiones rotas del grafo de conocimiento de la Wiki."""
    raw_items = graph_nodes if isinstance(graph_nodes, list) else []
    valid_nodes: list[dict] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        raw_page_id = item.get("page_id")
        if not isinstance(raw_page_id, str) or not raw_page_id.strip():
            continue
        valid_nodes.append(item)

    def _bool(value, default):
        return value if isinstance(value, bool) else default

    def _int(value, default):
        if isinstance(value, bool) or not isinstance(value, int):
            return default
        return value

    def _float(value, default):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return default
        return float(value)

    desynced_backlink_or_broken_transclusion_page_ids: list[str] = []
    isolated_orphan_cluster_page_ids: list[str] = []

    for node in valid_nodes:
        page_id = str(node.get("page_id")).strip()
        backlinks_synced = _bool(
            node.get("bidirectional_backlinks_synced"), True
        )
        broken_transclusions = _int(
            node.get("broken_transclusion_embeds_count"), 0
        )
        is_orphan = _bool(node.get("is_isolated_orphan_node"), False)
        orphan_cluster_ratio_pct = _float(
            node.get("orphan_cluster_ratio_pct"), 2.0
        )

        if not bool(backlinks_synced) or int(broken_transclusions) > 0:
            desynced_backlink_or_broken_transclusion_page_ids.append(page_id)

        if (
            bool(is_orphan) is True
            or float(orphan_cluster_ratio_pct)
            > float(max_orphan_cluster_ratio_pct)
        ):
            isolated_orphan_cluster_page_ids.append(page_id)

    if desynced_backlink_or_broken_transclusion_page_ids:
        knowledge_graph_status = "BACKLINK_DESYNC_OR_BROKEN_TRANSCLUSION_BREACH"
    elif isolated_orphan_cluster_page_ids:
        knowledge_graph_status = "ORPHAN_CLUSTER_FRAGMENTATION_WARNING"
    else:
        knowledge_graph_status = "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL"

    return {
        "evaluated_pages_count": len(valid_nodes),
        "desynced_backlink_or_broken_transclusion_page_ids": desynced_backlink_or_broken_transclusion_page_ids,
        "isolated_orphan_cluster_page_ids": isolated_orphan_cluster_page_ids,
        "knowledge_graph_status": knowledge_graph_status,
        "is_knowledge_graph_compliant": knowledge_graph_status
        == "KNOWLEDGE_GRAPH_TOPOLOGY_OPTIMAL",
    }


WikiPMIService.audit_wiki_graph_backlink_reciprocity_and_orphan_clusters = staticmethod(
    audit_wiki_graph_backlink_reciprocity_and_orphan_clusters
)


def audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock(
    crdt_documents: list[dict[str, Any]],
    *,
    max_tombstone_overhead_pct: float = 25.0,
    max_offline_divergence_ops: int = 500,
    require_causal_vector_convergence: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Audita edición colaborativa en tiempo real CRDT de la Wiki: convergencia causal del vector de estado, sobrecarga de tombstones sin recolectar (GC) y cola de operaciones offline sin fusionar."""
    raw_items = crdt_documents if isinstance(crdt_documents, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    diverged_or_conflicted_doc_ids: list[str] = []
    tombstone_or_offline_lag_doc_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        doc_id = (
            str(
                item.get("doc_id") or item.get("id") or f"crdt-{idx + 1}"
            ).strip()
            or f"crdt-{idx + 1}"
        )

        raw_conv = item.get("causal_vector_converged", True)
        causal_vector_converged = bool(True if raw_conv is None else raw_conv)

        raw_tomb = item.get("tombstone_overhead_pct", 0.0)
        tombstone_overhead_pct = max(
            0.0, float(0.0 if raw_tomb is None else raw_tomb)
        )

        raw_ops = item.get("unmerged_offline_ops_count", 0)
        unmerged_offline_ops_count = max(
            0, int(0 if raw_ops is None else raw_ops)
        )

        raw_dup = item.get("duplicate_client_id_detected")
        if raw_dup is None:
            raw_dup = item.get("concurrent_Awareness_peers_lost", False)
        duplicate_client_id_detected = bool(
            False if raw_dup is None else raw_dup
        )

        causal_divergence_or_duplicate_client_breach = bool(
            (require_causal_vector_convergence and not causal_vector_converged)
            or duplicate_client_id_detected
        )
        tombstone_bloat_or_offline_ops_warning = bool(
            tombstone_overhead_pct > max_tombstone_overhead_pct
            or unmerged_offline_ops_count > max_offline_divergence_ops
        )

        if causal_divergence_or_duplicate_client_breach:
            diverged_or_conflicted_doc_ids.append(doc_id)
            has_critical = True
            violations.append(
                f"CRDT document '{doc_id}' has causal state-vector divergence or duplicate client ID collision."
            )

        if tombstone_bloat_or_offline_ops_warning:
            tombstone_or_offline_lag_doc_ids.append(doc_id)
            has_warning = True
            violations.append(
                f"CRDT document '{doc_id}' exceeds tombstone overhead ({tombstone_overhead_pct}%) or offline unmerged ops ({unmerged_offline_ops_count})."
            )

        records.append(
            {
                "doc_id": doc_id,
                "causal_vector_converged": causal_vector_converged,
                "tombstone_overhead_pct": tombstone_overhead_pct,
                "unmerged_offline_ops_count": unmerged_offline_ops_count,
                "duplicate_client_id_detected": duplicate_client_id_detected,
                "causal_divergence_or_duplicate_client_breach": causal_divergence_or_duplicate_client_breach,
                "tombstone_bloat_or_offline_ops_warning": tombstone_bloat_or_offline_ops_warning,
            }
        )

    if has_critical:
        status = "critical"
        is_compliant = False
    elif has_warning:
        status = "warning"
        is_compliant = False
    else:
        status = "healthy"
        is_compliant = True

    return {
        "status": status,
        "is_compliant": is_compliant,
        "documents_evaluated": len(records),
        "diverged_or_conflicted_doc_ids": diverged_or_conflicted_doc_ids,
        "tombstone_or_offline_lag_doc_ids": tombstone_or_offline_lag_doc_ids,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


WikiPMIService.audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock = staticmethod(
    audit_wiki_crdt_collaborative_editing_tombstone_gc_and_causal_vector_clock
)


def audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle(
    workloads: list[dict[str, Any]],
    *,
    min_rotation_headroom_pct: float = 20.0,
    max_federation_bundle_staleness_sec: int = 300,
    require_node_and_unix_attestation: bool = True,
) -> dict[str, Any]:
    """PMBOK §10.2 & §11.6 — Audita identidad Zero-Trust SPIFFE/SPIRE X.509-SVID mTLS de la Wiki: margen de rotación de certificados efímeros, frescura del bundle de federación entre trust domains y atestación de nodo/proceso Unix."""
    raw_items = workloads if isinstance(workloads, list) else []
    valid_items = [item for item in raw_items if isinstance(item, dict)]

    unattested_or_invalid_spiffe_workload_ids: list[str] = []
    expiring_or_expired_svid_workload_ids: list[str] = []
    stale_federation_bundle_workload_ids: list[str] = []
    records: list[dict[str, Any]] = []
    violations: list[str] = []
    has_critical = False
    has_warning = False

    for idx, item in enumerate(valid_items):
        workload_id = (
            str(
                item.get("workload_id")
                or item.get("id")
                or f"workload-{idx + 1}"
            ).strip()
            or f"workload-{idx + 1}"
        )

        raw_spiffe = item.get("spiffe_id", "spiffe://ccf.local/wiki/service")
        spiffe_id = str(
            "spiffe://ccf.local/wiki/service"
            if raw_spiffe is None
            else raw_spiffe
        ).strip()

        raw_total = item.get("svid_ttl_total_sec", 3600)
        svid_ttl_total_sec = max(
            0, int(3600 if raw_total is None else raw_total)
        )

        raw_rem = item.get("svid_ttl_remaining_sec", 1800)
        svid_ttl_remaining_sec = int(1800 if raw_rem is None else raw_rem)

        raw_node = item.get("node_attested", True)
        node_attested = bool(True if raw_node is None else raw_node)

        raw_unix = item.get("unix_workload_attested", True)
        unix_workload_attested = bool(True if raw_unix is None else raw_unix)

        raw_age = item.get("federation_bundle_age_sec", 0)
        federation_bundle_age_sec = max(
            0, int(0 if raw_age is None else raw_age)
        )

        valid_spiffe_prefix = (
            spiffe_id.startswith("spiffe://") and len(spiffe_id) > len("spiffe://")
        )
        incomplete_attestation = bool(
            require_node_and_unix_attestation
            and (not node_attested or not unix_workload_attested)
        )
        unattested_or_invalid_spiffe = (
            not valid_spiffe_prefix or incomplete_attestation
        )

        svid_rotation_headroom_pct = (
            round((svid_ttl_remaining_sec / svid_ttl_total_sec) * 100.0, 2)
            if svid_ttl_total_sec > 0
            else 0.0
        )
        svid_expired = svid_ttl_total_sec <= 0 or svid_ttl_remaining_sec <= 0
        svid_expiring_or_expired = bool(
            svid_expired
            or (svid_ttl_remaining_sec / svid_ttl_total_sec) * 100.0
            < min_rotation_headroom_pct
        )
        stale_federation_bundle = (
            federation_bundle_age_sec > max_federation_bundle_staleness_sec
        )

        if unattested_or_invalid_spiffe:
            unattested_or_invalid_spiffe_workload_ids.append(workload_id)
            has_critical = True
            violations.append(
                f"Workload '{workload_id}' has invalid SPIFFE ID ('{spiffe_id}') or incomplete node/unix attestation."
            )

        if svid_expiring_or_expired:
            expiring_or_expired_svid_workload_ids.append(workload_id)
            if svid_expired:
                has_critical = True
                violations.append(
                    f"Workload '{workload_id}' X.509-SVID certificate is expired (remaining={svid_ttl_remaining_sec}s)."
                )
            else:
                has_warning = True
                violations.append(
                    f"Workload '{workload_id}' SVID rotation headroom ({svid_rotation_headroom_pct}%) is below minimum ({min_rotation_headroom_pct}%)."
                )

        if stale_federation_bundle:
            stale_federation_bundle_workload_ids.append(workload_id)
            has_warning = True
            violations.append(
                f"Workload '{workload_id}' trust domain federation bundle age ({federation_bundle_age_sec}s) exceeds maximum ({max_federation_bundle_staleness_sec}s)."
            )

        records.append(
            {
                "workload_id": workload_id,
                "spiffe_id": spiffe_id,
                "svid_ttl_total_sec": svid_ttl_total_sec,
                "svid_ttl_remaining_sec": svid_ttl_remaining_sec,
                "svid_rotation_headroom_pct": svid_rotation_headroom_pct,
                "node_attested": node_attested,
                "unix_workload_attested": unix_workload_attested,
                "federation_bundle_age_sec": federation_bundle_age_sec,
                "unattested_or_invalid_spiffe": unattested_or_invalid_spiffe,
                "svid_expiring_or_expired": svid_expiring_or_expired,
                "stale_federation_bundle": stale_federation_bundle,
            }
        )

    if has_critical:
        spiffe_svid_federation_status = (
            "CRITICAL_ATTESTATION_OR_SVID_EXPIRY_BREACH"
        )
        status = "critical"
        is_spiffe_zero_trust_healthy = False
    elif has_warning:
        spiffe_svid_federation_status = (
            "SVID_ROTATION_OR_FEDERATION_BUNDLE_WARNING"
        )
        status = "warning"
        is_spiffe_zero_trust_healthy = False
    else:
        spiffe_svid_federation_status = "SPIFFE_ZERO_TRUST_HEALTHY"
        status = "healthy"
        is_spiffe_zero_trust_healthy = True

    return {
        "status": status,
        "is_compliant": is_spiffe_zero_trust_healthy,
        "is_spiffe_zero_trust_healthy": is_spiffe_zero_trust_healthy,
        "workloads_evaluated": len(records),
        "unattested_or_invalid_spiffe_workload_ids": unattested_or_invalid_spiffe_workload_ids,
        "expiring_or_expired_svid_workload_ids": expiring_or_expired_svid_workload_ids,
        "stale_federation_bundle_workload_ids": stale_federation_bundle_workload_ids,
        "spiffe_svid_federation_status": spiffe_svid_federation_status,
        "records": records,
        "violations": violations,
        "Violations": violations,
    }


WikiPMIService.audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle = staticmethod(
    audit_wiki_spiffe_spire_svid_mtls_rotation_and_federation_bundle
)


def audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker(
    indices: list[dict[str, Any]],
    max_node_jvm_heap_used_pct: float = 70.0,
    jvm_parent_circuit_breaker_limit_pct: float = 85.0,
    quorum_master_nodes_present: bool = True,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki Distributed Search Elasticsearch/OpenSearch Shard Split-Brain, Unassigned Primary/Replica Shards & JVM Heap Circuit-Breaker Auditor."""
    valid_indices = [
        idx for idx in (indices if isinstance(indices, list) else []) if isinstance(idx, dict)
    ]

    red_unassigned_primary_indices: list[str] = []
    degraded_replica_or_rejected_indices: list[str] = []

    for i, item in enumerate(valid_indices):
        idx_name = str(item.get("index_name") or f"index-{i + 1}").strip()
        unassigned_prim = int(item.get("unassigned_primary_shards", 0) or 0)
        unassigned_rep = int(item.get("unassigned_replica_shards", 0) or 0)
        rejections = int(item.get("search_thread_pool_rejections", 0) or 0)

        if unassigned_prim > 0:
            red_unassigned_primary_indices.append(idx_name)
        if unassigned_rep > 0 or rejections > 0:
            degraded_replica_or_rejected_indices.append(idx_name)

    heap_pct = float(max_node_jvm_heap_used_pct)
    breaker_limit_pct = float(jvm_parent_circuit_breaker_limit_pct)
    jvm_circuit_breaker_tripped = (
        heap_pct >= breaker_limit_pct or heap_pct > 100.0 or heap_pct < 0.0
    )
    split_brain_risk = not bool(quorum_master_nodes_present)

    recommendations: list[str] = []
    if len(valid_indices) == 0:
        recommendations.append(
            "Provide at least one search index configuration for cluster health auditing."
        )
    if red_unassigned_primary_indices:
        recommendations.append(
            f"Restore primary shard allocation immediately for RED indices: {', '.join(red_unassigned_primary_indices)}."
        )
    if degraded_replica_or_rejected_indices:
        recommendations.append(
            f"Rebalance unassigned replica shards and scale search thread pools for: {', '.join(degraded_replica_or_rejected_indices)}."
        )
    if jvm_circuit_breaker_tripped:
        recommendations.append(
            f"Reduce JVM heap pressure ({heap_pct:.2f}% >= {breaker_limit_pct:.2f}%) or scale data nodes to clear parent circuit-breaker."
        )
    if split_brain_risk:
        recommendations.append(
            "Restore master-eligible node quorum (discovery.zen.minimum_master_nodes / cluster.initial_master_nodes) to prevent split-brain."
        )

    if (
        len(red_unassigned_primary_indices) > 0
        or jvm_circuit_breaker_tripped
        or split_brain_risk
        or len(valid_indices) == 0
    ):
        cluster_health_status = "RED_CRITICAL_OUTAGE"
    elif len(degraded_replica_or_rejected_indices) > 0:
        cluster_health_status = "YELLOW_REPLICA_OR_QUEUE_PRESSURE"
    else:
        cluster_health_status = "GREEN_OPTIMAL"

    return {
        "is_valid": cluster_health_status == "GREEN_OPTIMAL",
        "total_indices": len(valid_indices),
        "red_unassigned_primary_indices": red_unassigned_primary_indices,
        "degraded_replica_or_rejected_indices": degraded_replica_or_rejected_indices,
        "jvm_circuit_breaker_tripped": jvm_circuit_breaker_tripped,
        "split_brain_risk": split_brain_risk,
        "cluster_health_status": cluster_health_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker = staticmethod(
    audit_wiki_search_cluster_shard_allocation_and_jvm_heap_breaker
)


def audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio(
    pop_regions: list[dict[str, Any]],
    max_purge_propagation_sec: float = 5.0,
    min_cache_hit_ratio_pct: float = 85.0,
    max_5xx_error_rate_pct: float = 0.5,
) -> dict[str, Any]:
    """PMBOK §4.4 & §10.2 — Wiki Content Delivery Network (CDN) Edge Cache Surrogate-Key Purge Latency, Stale-While-Revalidate Window & Origin Shield Hit-Ratio Auditor."""
    valid_regions = [
        r for r in (pop_regions if isinstance(pop_regions, list) else []) if isinstance(r, dict)
    ]

    slow_purge_propagation_regions: list[str] = []
    cache_thrashing_or_unshielded_regions: list[str] = []
    elevated_5xx_edge_regions: list[str] = []
    any_unshielded = False

    for idx, r in enumerate(valid_regions):
        rid = str(r.get("region_id") or f"region-{idx + 1}").strip()
        purge_sec = float(r.get("surrogate_purge_latency_sec", 0.0) or 0.0)
        hit_pct = float(r.get("edge_cache_hit_ratio_pct", 0.0) or 0.0)
        shield_on = bool(r.get("origin_shield_enabled", True))
        err_5xx = float(r.get("five_xx_edge_error_rate_pct", 0.0) or 0.0)

        if not shield_on:
            any_unshielded = True
        if purge_sec > float(max_purge_propagation_sec) or purge_sec < 0.0:
            slow_purge_propagation_regions.append(rid)
        if hit_pct < float(min_cache_hit_ratio_pct) or not shield_on:
            cache_thrashing_or_unshielded_regions.append(rid)
        if err_5xx > float(max_5xx_error_rate_pct):
            elevated_5xx_edge_regions.append(rid)

    recommendations: list[str] = []
    if len(valid_regions) == 0:
        recommendations.append(
            "Provide at least one CDN PoP region telemetry record for edge cache auditing."
        )
    if elevated_5xx_edge_regions or any_unshielded:
        recommendations.append(
            "Enable origin shielding across all PoP regions and mitigate elevated 5xx edge error rates."
        )
    if slow_purge_propagation_regions:
        recommendations.append(
            f"Optimize surrogate-key fast-purge invalidation pipeline within <= {max_purge_propagation_sec}s on: {', '.join(slow_purge_propagation_regions)}."
        )
    if cache_thrashing_or_unshielded_regions:
        recommendations.append(
            f"Tune stale-while-revalidate headers and cache key normalization to reach >= {min_cache_hit_ratio_pct}% hit ratio on: {', '.join(cache_thrashing_or_unshielded_regions)}."
        )

    if (
        len(elevated_5xx_edge_regions) > 0
        or any_unshielded
        or len(valid_regions) == 0
    ):
        cdn_edge_status = "CRITICAL_EDGE_5XX_OR_UNSHIELDED_ORIGIN_BREACH"
    elif (
        len(slow_purge_propagation_regions) > 0
        or len(cache_thrashing_or_unshielded_regions) > 0
    ):
        cdn_edge_status = "PURGE_LATENCY_OR_CACHE_HIT_WARNING"
    else:
        cdn_edge_status = "CDN_EDGE_OPTIMAL"

    return {
        "is_valid": cdn_edge_status == "CDN_EDGE_OPTIMAL",
        "total_pop_regions": len(valid_regions),
        "slow_purge_propagation_regions": slow_purge_propagation_regions,
        "cache_thrashing_or_unshielded_regions": cache_thrashing_or_unshielded_regions,
        "elevated_5xx_edge_regions": elevated_5xx_edge_regions,
        "cdn_edge_status": cdn_edge_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio = staticmethod(
    audit_wiki_cdn_surrogate_key_purge_and_origin_shield_hit_ratio
)


def audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound(
    replication_slots: list[dict[str, Any]],
    max_retained_wal_gb: float = 20.0,
    max_replica_lag_seconds: float = 30.0,
    txid_autovacuum_freeze_max_age_millions: float = 200.0,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki Postgres Logical Replication Slot WAL Bloat, Replication Lag LSN Byte Delta & Dead-Tuple Autovacuum Freeze-Age Auditor."""
    valid_slots = [
        s for s in (replication_slots if isinstance(replication_slots, list) else []) if isinstance(s, dict)
    ]

    inactive_or_wal_bloated_slots: list[str] = []
    lagging_replication_slots: list[str] = []
    txid_wraparound_risk_slots: list[str] = []

    for idx, s in enumerate(valid_slots):
        sname = str(s.get("slot_name") or f"slot-{idx + 1}").strip()
        active = bool(s.get("active", False))
        retained_gb = float(s.get("retained_wal_gb", 0.0) or 0.0)
        lag_sec = float(s.get("replica_lag_seconds", 0.0) or 0.0)
        txid_age_m = float(s.get("max_table_txid_age_millions", 50.0) or 0.0)

        if not active or retained_gb > float(max_retained_wal_gb):
            inactive_or_wal_bloated_slots.append(sname)
        if lag_sec > float(max_replica_lag_seconds):
            lagging_replication_slots.append(sname)
        if txid_age_m >= float(txid_autovacuum_freeze_max_age_millions):
            txid_wraparound_risk_slots.append(sname)

    recommendations: list[str] = []
    if len(valid_slots) == 0:
        recommendations.append(
            "Provide at least one PostgreSQL logical replication slot record for WAL and vacuum health auditing."
        )
    if inactive_or_wal_bloated_slots:
        recommendations.append(
            f"Drop or resume inactive logical replication slots and cap max_slot_wal_keep_size on: {', '.join(inactive_or_wal_bloated_slots)}."
        )
    if txid_wraparound_risk_slots:
        recommendations.append(
            f"Execute emergency VACUUM FREEZE to prevent XID wraparound shutdown on: {', '.join(txid_wraparound_risk_slots)}."
        )
    if lagging_replication_slots:
        recommendations.append(
            f"Investigate WAL sender/receiver I/O bottleneck for lagging replication slots (> {max_replica_lag_seconds}s): {', '.join(lagging_replication_slots)}."
        )

    if (
        len(inactive_or_wal_bloated_slots) > 0
        or len(txid_wraparound_risk_slots) > 0
        or len(valid_slots) == 0
    ):
        replication_health_status = "CRITICAL_WAL_EXHAUSTION_OR_TXID_WRAPAROUND"
    elif len(lagging_replication_slots) > 0:
        replication_health_status = "REPLICA_LAG_WARNING"
    else:
        replication_health_status = "REPLICATION_AND_VACUUM_HEALTHY"

    return {
        "is_valid": replication_health_status == "REPLICATION_AND_VACUUM_HEALTHY",
        "total_slots": len(valid_slots),
        "inactive_or_wal_bloated_slots": inactive_or_wal_bloated_slots,
        "lagging_replication_slots": lagging_replication_slots,
        "txid_wraparound_risk_slots": txid_wraparound_risk_slots,
        "replication_health_status": replication_health_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound = staticmethod(
    audit_wiki_postgres_logical_replication_wal_bloat_and_txid_wraparound
)


def audit_wiki_s3_erasure_coding_quorum_and_object_lock_worm(
    buckets: list[dict[str, Any]],
    allowed_max_presigned_url_ttl_sec: int = 3600,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Object Storage S3/MinIO erasure coding parity drive rebuild, versioning Object-Lock WORM compliance & presigned URL expiry cap auditor."""
    quorum_lost_or_unlocked_buckets: list[str] = []
    degraded_parity_or_long_presigned_ttl_buckets: list[str] = []
    recommendations: list[str] = []

    valid_buckets = [b for b in (buckets or []) if isinstance(b, Mapping)]

    for bucket in valid_buckets:
        name = str(bucket.get("bucket_name") or "").strip()
        if not name:
            continue

        online_drives = int(bucket.get("online_drives_count", 0) or 0)
        total_drives = int(bucket.get("total_drives_count", 0) or 0)
        parity_shards = int(bucket.get("parity_shards_ec_m", 0) or 0)
        worm_enabled = bool(bucket.get("versioning_and_object_lock_enabled", True))
        max_ttl = int(bucket.get("max_presigned_url_ttl_sec", 3600) or 0)

        failed_drives = max(0, total_drives - online_drives)
        write_quorum = total_drives - parity_shards

        if (
            total_drives <= 0
            or failed_drives > parity_shards
            or online_drives < write_quorum
            or not worm_enabled
        ):
            quorum_lost_or_unlocked_buckets.append(name)
            recommendations.append(
                f"Restore erasure-coding quorum ({online_drives}/{total_drives} drives, EC:{parity_shards}) and enforce Object-Lock WORM on bucket '{name}'."
            )
        if 0 < failed_drives <= parity_shards or max_ttl > int(
            allowed_max_presigned_url_ttl_sec
        ):
            degraded_parity_or_long_presigned_ttl_buckets.append(name)
            recommendations.append(
                f"Heal degraded parity drives ({failed_drives} offline) and cap presigned URL TTL ({max_ttl}s <= {allowed_max_presigned_url_ttl_sec}s) on bucket '{name}'."
            )

    if len(valid_buckets) == 0 or len(quorum_lost_or_unlocked_buckets) > 0:
        storage_status = "CRITICAL_ERASURE_QUORUM_OR_WORM_LOCK_BREACH"
    elif len(degraded_parity_or_long_presigned_ttl_buckets) > 0:
        storage_status = "DEGRADED_PARITY_HEALING_OR_TTL_WARNING"
    else:
        storage_status = "OBJECT_STORAGE_WORM_OPTIMAL"

    return {
        "is_valid": storage_status == "OBJECT_STORAGE_WORM_OPTIMAL",
        "total_buckets": len(valid_buckets),
        "quorum_lost_or_unlocked_buckets": quorum_lost_or_unlocked_buckets,
        "degraded_parity_or_long_presigned_ttl_buckets": degraded_parity_or_long_presigned_ttl_buckets,
        "storage_status": storage_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_s3_erasure_coding_quorum_and_object_lock_worm = staticmethod(
    audit_wiki_s3_erasure_coding_quorum_and_object_lock_worm
)


def audit_wiki_redis_cluster_hash_slot_coverage_and_aof_eviction(
    shards: list[dict[str, Any]],
    total_required_hash_slots: int = 16384,
    min_replicas_per_master: int = 1,
    max_memory_used_pct: float = 85.0,
    max_evicted_keys_per_sec: float = 10.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Redis Cluster hash-slot coverage (16384 slots), master-replica failover quorum, eviction OOM & AOF fsync lag auditor."""
    valid_shards = [s for s in (shards or []) if isinstance(s, Mapping)]

    total_assigned_slots = sum(
        max(0, int(s.get("assigned_slots_count", 0) or 0)) for s in valid_shards
    )
    unassigned_hash_slots_gap = max(
        0, int(total_required_hash_slots) - total_assigned_slots
    )

    unreplicated_single_point_shards: list[str] = []
    memory_pressure_or_aof_stalled_shards: list[str] = []
    recommendations: list[str] = []

    for idx, shard in enumerate(valid_shards):
        shard_id = str(shard.get("shard_id") or f"shard-{idx + 1}").strip()
        replicas = int(shard.get("connected_healthy_replicas", 0) or 0)
        mem_pct = float(shard.get("memory_used_pct", 0.0) or 0.0)
        evicted_sec = float(shard.get("evicted_keys_per_sec", 0.0) or 0.0)
        raw_aof_delayed = shard.get(
            "aof_delayed_fsync_count", shard.get("aof_Delayed_fsync_count", 0)
        )
        aof_delayed = int(raw_aof_delayed or 0)

        if replicas < int(min_replicas_per_master):
            unreplicated_single_point_shards.append(shard_id)

        if (
            mem_pct > float(max_memory_used_pct)
            or evicted_sec > float(max_evicted_keys_per_sec)
            or aof_delayed > 0
        ):
            memory_pressure_or_aof_stalled_shards.append(shard_id)

    if len(valid_shards) == 0:
        recommendations.append(
            "Provide Redis Cluster master shard telemetry for 16384 hash-slot coverage verification."
        )
    if (
        unassigned_hash_slots_gap > 0
        or total_assigned_slots != int(total_required_hash_slots)
    ):
        recommendations.append(
            f"Rebalance and assign all {total_required_hash_slots} Redis Cluster hash slots (current assigned: {total_assigned_slots}, gap: {unassigned_hash_slots_gap}) to prevent CLUSTERDOWN."
        )
    if unreplicated_single_point_shards:
        recommendations.append(
            f"Attach at least {min_replicas_per_master} healthy replica(s) per master shard on: {', '.join(unreplicated_single_point_shards)}."
        )
    if memory_pressure_or_aof_stalled_shards:
        recommendations.append(
            f"Scale shard memory (<={max_memory_used_pct}%), reduce eviction thrashing, and resolve AOF delayed fsync stalls on: {', '.join(memory_pressure_or_aof_stalled_shards)}."
        )

    if (
        len(valid_shards) == 0
        or unassigned_hash_slots_gap > 0
        or total_assigned_slots != int(total_required_hash_slots)
        or len(unreplicated_single_point_shards) > 0
    ):
        redis_cluster_status = "CRITICAL_CLUSTERDOWN_SLOT_GAP_OR_UNREPLICATED"
    elif len(memory_pressure_or_aof_stalled_shards) > 0:
        redis_cluster_status = "MEMORY_EVICTION_OR_AOF_FSYNC_WARNING"
    else:
        redis_cluster_status = "REDIS_CLUSTER_OPTIMAL"

    return {
        "is_valid": redis_cluster_status == "REDIS_CLUSTER_OPTIMAL",
        "total_shards": len(valid_shards),
        "total_assigned_slots": total_assigned_slots,
        "unassigned_hash_slots_gap": unassigned_hash_slots_gap,
        "unreplicated_single_point_shards": unreplicated_single_point_shards,
        "memory_pressure_or_aof_stalled_shards": memory_pressure_or_aof_stalled_shards,
        "redis_cluster_status": redis_cluster_status,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_redis_cluster_hash_slot_coverage_and_aof_eviction = staticmethod(
    audit_wiki_redis_cluster_hash_slot_coverage_and_aof_eviction
)


def audit_wiki_kms_envelope_key_rotation_and_hsm_tamper_seal(
    key_rings: list[dict[str, Any]],
    *,
    max_kek_age_days: int = 365,
    max_stale_dek_rewrap_pct: float = 5.0,
    min_hsm_quorum_nodes: int = 2,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki KMS Envelope Encryption Key Rotation, DEK Re-Wrapping Backlog & HSM Tamper Seal Auditor."""
    valid_keyrings = [
        kr for kr in (key_rings if isinstance(key_rings, list) else []) if isinstance(kr, Mapping)
    ]

    critical_keyrings: list[str] = []
    warning_keyrings: list[str] = []
    keyring_evaluations: list[dict[str, Any]] = []
    max_observed_stale_dek_pct = 0.0

    for idx, kr in enumerate(valid_keyrings):
        keyring_id = str(kr.get("keyring_id") or f"keyring-{idx + 1}").strip()
        kek_age_days = int(kr.get("kek_age_days", 0) or 0)
        total_encrypted_pages = int(kr.get("total_encrypted_pages", 0) or 0)
        stale_dek_pages = int(kr.get("stale_dek_version_pages", 0) or 0)
        hsm_nodes = int(kr.get("active_hsm_partition_nodes", 0) or 0)
        tamper_detected = bool(kr.get("hsm_tamper_event_detected", False))
        plaintext_leak = bool(kr.get("plaintext_dek_cache_leak_detected", False))
        auto_rotation = bool(kr.get("auto_rotation_schedule_enabled", True))

        stale_dek_rewrap_pct = (
            round((stale_dek_pages / total_encrypted_pages) * 100.0, 2)
            if total_encrypted_pages > 0
            else 0.0
        )
        if stale_dek_rewrap_pct > max_observed_stale_dek_pct:
            max_observed_stale_dek_pct = stale_dek_rewrap_pct

        critical_kms_breach = bool(
            tamper_detected is True
            or plaintext_leak is True
            or hsm_nodes < int(min_hsm_quorum_nodes)
            or kek_age_days > float(max_kek_age_days) * 1.25
        )
        rotation_or_rewrap_warning = bool(
            not critical_kms_breach
            and (
                kek_age_days > int(max_kek_age_days)
                or stale_dek_rewrap_pct > float(max_stale_dek_rewrap_pct)
                or not auto_rotation
            )
        )

        if critical_kms_breach:
            critical_keyrings.append(keyring_id)
        elif rotation_or_rewrap_warning:
            warning_keyrings.append(keyring_id)

        keyring_evaluations.append(
            {
                "keyring_id": keyring_id,
                "kek_age_days": kek_age_days,
                "stale_dek_rewrap_pct": stale_dek_rewrap_pct,
                "active_hsm_partition_nodes": hsm_nodes,
                "critical_kms_breach": critical_kms_breach,
                "rotation_or_rewrap_warning": rotation_or_rewrap_warning,
            }
        )

    if len(critical_keyrings) > 0:
        status = "CRITICAL"
    elif len(warning_keyrings) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_keyrings_count": len(keyring_evaluations),
        "critical_keyrings": critical_keyrings,
        "warning_keyrings": warning_keyrings,
        "max_observed_stale_dek_pct": max_observed_stale_dek_pct,
        "keyring_evaluations": keyring_evaluations,
    }


WikiPMIService.audit_wiki_kms_envelope_key_rotation_and_hsm_tamper_seal = staticmethod(
    audit_wiki_kms_envelope_key_rotation_and_hsm_tamper_seal
)


def audit_wiki_webhook_ssrf_cidr_blocklist_and_dns_rebinding_guard(
    webhooks: list[dict[str, Any]],
    *,
    max_redirect_hops: int = 0,
    max_delivery_timeout_ms: int = 5000,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki GraphQL / Webhook Outbound SSRF Private CIDR Blocklist, DNS Rebinding Pinning & Egress Proxy mTLS Auditor."""
    webhook_evaluations: list[dict[str, Any]] = []
    critical_webhooks: list[str] = []
    warning_webhooks: list[str] = []

    for item in webhooks or []:
        if not isinstance(item, Mapping):
            continue
        webhook_id = str(item.get("webhook_id") or "").strip() or "UNKNOWN_WEBHOOK"
        resolved_ip_in_rfc1918_or_link_local = bool(
            item.get("resolved_ip_in_rfc1918_or_link_local", False)
        )
        cloud_metadata_ip_169_254_targeted = bool(
            item.get("cloud_metadata_ip_169_254_targeted", False)
        )
        dns_pinning_enforced = bool(item.get("dns_pinning_enforced", True))
        egress_proxy_mtls_verified = bool(
            item.get("egress_proxy_mtls_verified", True)
        )
        hmac_sha256_signature_enabled = bool(
            item.get("hmac_sha256_signature_enabled", True)
        )
        redirect_hops_followed = int(item.get("redirect_hops_followed", 0) or 0)
        delivery_timeout_ms = int(item.get("delivery_timeout_ms", 3000) or 0)

        critical_ssrf_breach = (
            resolved_ip_in_rfc1918_or_link_local is True
            or cloud_metadata_ip_169_254_targeted is True
            or not dns_pinning_enforced
            or not egress_proxy_mtls_verified
            or redirect_hops_followed > max_redirect_hops
        )
        webhook_security_warning = (not critical_ssrf_breach) and (
            not hmac_sha256_signature_enabled
            or delivery_timeout_ms > max_delivery_timeout_ms
        )

        if critical_ssrf_breach:
            critical_webhooks.append(webhook_id)
        elif webhook_security_warning:
            warning_webhooks.append(webhook_id)

        webhook_evaluations.append(
            {
                "webhook_id": webhook_id,
                "resolved_ip_in_rfc1918_or_link_local": resolved_ip_in_rfc1918_or_link_local,
                "cloud_metadata_ip_169_254_targeted": cloud_metadata_ip_169_254_targeted,
                "dns_pinning_enforced": dns_pinning_enforced,
                "egress_proxy_mtls_verified": egress_proxy_mtls_verified,
                "hmac_sha256_signature_enabled": hmac_sha256_signature_enabled,
                "redirect_hops_followed": redirect_hops_followed,
                "delivery_timeout_ms": delivery_timeout_ms,
                "critical_ssrf_breach": critical_ssrf_breach,
                "webhook_security_warning": webhook_security_warning,
            }
        )

    if len(critical_webhooks) > 0:
        status = "CRITICAL"
    elif len(warning_webhooks) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_webhooks_count": len(webhook_evaluations),
        "critical_webhooks": critical_webhooks,
        "warning_webhooks": warning_webhooks,
        "ssrf_blocked_count": len(critical_webhooks),
        "webhook_evaluations": webhook_evaluations,
    }


WikiPMIService.audit_wiki_webhook_ssrf_cidr_blocklist_and_dns_rebinding_guard = staticmethod(
    audit_wiki_webhook_ssrf_cidr_blocklist_and_dns_rebinding_guard
)


def audit_wiki_outbox_cdc_debezium_connector_lag_and_tombstone_hygiene(
    connectors: list[dict[str, Any]],
    *,
    max_replication_slot_lag_mb: float = 512.0,
    max_outbox_pending_events: int = 10000,
    max_dlq_poison_events: int = 0,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki Kafka / Event-Sourcing Outbox Debezium CDC Connector Offset Lag, Poison Tombstone & Schema Evolution Auditor."""
    connector_evaluations: list[dict[str, Any]] = []
    critical_connectors: list[str] = []
    warning_connectors: list[str] = []
    max_observed_slot_lag_mb = 0.0

    for item in connectors or []:
        if not isinstance(item, Mapping):
            continue
        connector_id = (
            str(item.get("connector_id") or "").strip() or "UNKNOWN_CONNECTOR"
        )
        connector_state = (
            str(item.get("connector_state") or "RUNNING").strip().upper()
        )
        replication_slot_lag_mb = round(
            float(item.get("replication_slot_lag_mb", 10.0) or 0.0), 2
        )
        outbox_pending_events_count = int(
            item.get("outbox_pending_events_count", 50) or 0
        )
        dlq_poison_events_count = int(
            item.get("dlq_poison_events_count", 0) or 0
        )
        backward_compatible_avro_schema = bool(
            item.get("backward_compatible_avro_schema", True)
        )
        heartbeat_interval_configured = bool(
            item.get("heartbeat_interval_configured", True)
        )

        max_observed_slot_lag_mb = max(
            max_observed_slot_lag_mb, replication_slot_lag_mb
        )

        critical_cdc_breach = (
            connector_state == "FAILED"
            or not backward_compatible_avro_schema
            or dlq_poison_events_count > max_dlq_poison_events
            or replication_slot_lag_mb > max_replication_slot_lag_mb
        )
        cdc_backlog_warning = (not critical_cdc_breach) and (
            connector_state == "PAUSED"
            or outbox_pending_events_count > max_outbox_pending_events
            or not heartbeat_interval_configured
            or replication_slot_lag_mb >= max_replication_slot_lag_mb * 0.75
        )

        if critical_cdc_breach:
            critical_connectors.append(connector_id)
        elif cdc_backlog_warning:
            warning_connectors.append(connector_id)

        connector_evaluations.append(
            {
                "connector_id": connector_id,
                "connector_state": connector_state,
                "replication_slot_lag_mb": replication_slot_lag_mb,
                "outbox_pending_events_count": outbox_pending_events_count,
                "dlq_poison_events_count": dlq_poison_events_count,
                "backward_compatible_avro_schema": backward_compatible_avro_schema,
                "heartbeat_interval_configured": heartbeat_interval_configured,
                "critical_cdc_breach": critical_cdc_breach,
                "cdc_backlog_warning": cdc_backlog_warning,
            }
        )

    if len(critical_connectors) > 0:
        status = "CRITICAL"
    elif len(warning_connectors) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_connectors_count": len(connector_evaluations),
        "critical_connectors": critical_connectors,
        "warning_connectors": warning_connectors,
        "max_observed_slot_lag_mb": max_observed_slot_lag_mb,
        "connector_evaluations": connector_evaluations,
    }


WikiPMIService.audit_wiki_outbox_cdc_debezium_connector_lag_and_tombstone_hygiene = staticmethod(
    audit_wiki_outbox_cdc_debezium_connector_lag_and_tombstone_hygiene
)


def audit_wiki_sso_saml_oidc_assertion_signature_and_replay_guard(
    providers: list[dict[str, Any]],
    *,
    max_clock_skew_seconds: int = 120,
    max_idp_cert_days_before_expiry: int = 30,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki OIDC / SAML 2.0 Federated Single Sign-On (SSO) Assertion Signature XML-DSig Wrapping, Clock Skew Replay & JIT Group Sync Auditor."""
    provider_evaluations: list[dict[str, Any]] = []
    critical_providers: list[str] = []
    warning_providers: list[str] = []
    observed_cert_days: list[int] = []

    for item in providers or []:
        if not isinstance(item, Mapping):
            continue
        idp_id = str(item.get("idp_id") or "").strip() or "UNKNOWN_IDP"
        protocol = str(item.get("protocol") or "oidc").strip().lower()
        xml_dsig_wrapping_protection_enabled = bool(
            item.get("xml_dsig_wrapping_protection_enabled", True)
        )
        assertion_replay_jti_cache_enforced = bool(
            item.get("assertion_replay_jti_cache_enforced", True)
        )
        pkce_s256_required = bool(item.get("pkce_s256_required", True))
        raw_skew = item.get("allowed_clock_skew_seconds", 60)
        allowed_clock_skew_seconds = int(60 if raw_skew is None else raw_skew)
        raw_cert_days = item.get("idp_signing_cert_days_remaining", 180)
        idp_signing_cert_days_remaining = int(
            180 if raw_cert_days is None else raw_cert_days
        )
        jit_deprovisioning_scim_synced = bool(
            item.get("jit_deprovisioning_scim_synced", True)
        )

        observed_cert_days.append(idp_signing_cert_days_remaining)

        critical_sso_breach = (
            (protocol == "saml2" and not xml_dsig_wrapping_protection_enabled)
            or (protocol == "oidc" and not pkce_s256_required)
            or not assertion_replay_jti_cache_enforced
            or idp_signing_cert_days_remaining <= 0
            or allowed_clock_skew_seconds > max_clock_skew_seconds * 2
        )
        sso_hygiene_warning = (not critical_sso_breach) and (
            idp_signing_cert_days_remaining <= max_idp_cert_days_before_expiry
            or allowed_clock_skew_seconds > max_clock_skew_seconds
            or not jit_deprovisioning_scim_synced
        )

        if critical_sso_breach:
            critical_providers.append(idp_id)
        elif sso_hygiene_warning:
            warning_providers.append(idp_id)

        provider_evaluations.append(
            {
                "idp_id": idp_id,
                "protocol": protocol,
                "xml_dsig_wrapping_protection_enabled": xml_dsig_wrapping_protection_enabled,
                "assertion_replay_jti_cache_enforced": assertion_replay_jti_cache_enforced,
                "pkce_s256_required": pkce_s256_required,
                "allowed_clock_skew_seconds": allowed_clock_skew_seconds,
                "idp_signing_cert_days_remaining": idp_signing_cert_days_remaining,
                "jit_deprovisioning_scim_synced": jit_deprovisioning_scim_synced,
                "critical_sso_breach": critical_sso_breach,
                "sso_hygiene_warning": sso_hygiene_warning,
            }
        )

    if len(critical_providers) > 0:
        status = "CRITICAL"
    elif len(warning_providers) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    min_cert_days_remaining = (
        min(observed_cert_days) if observed_cert_days else 0
    )

    return {
        "status": status,
        "evaluated_providers_count": len(provider_evaluations),
        "critical_providers": critical_providers,
        "warning_providers": warning_providers,
        "min_cert_days_remaining": min_cert_days_remaining,
        "provider_evaluations": provider_evaluations,
    }


WikiPMIService.audit_wiki_sso_saml_oidc_assertion_signature_and_replay_guard = staticmethod(
    audit_wiki_sso_saml_oidc_assertion_signature_and_replay_guard
)


def audit_wiki_vector_rag_index_drift_and_acl_prefilter_guard(
    indexes: list[dict[str, Any]],
    *,
    max_embedding_drift_pct: float = 5.0,
    min_chunk_overlap_ratio: float = 0.10,
    max_chunk_overlap_ratio: float = 0.40,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki Full-Text Vector Embedding RAG Index Drift, Chunk Overlap Hallucination Guard & ACL Permission Filter Pre-Filtering Auditor."""
    index_evaluations: list[dict[str, Any]] = []
    critical_indexes: list[str] = []
    warning_indexes: list[str] = []
    max_observed_drift_pct = 0.0

    for item in indexes or []:
        if not isinstance(item, Mapping):
            continue
        index_id = str(item.get("index_id") or "").strip() or "UNKNOWN_INDEX"
        acl_pre_filtering_enforced_before_ann = bool(
            item.get("acl_pre_filtering_enforced_before_ann", True)
        )
        cross_tenant_namespace_isolated = bool(
            item.get("cross_tenant_namespace_isolated", True)
        )
        embedding_model_dimension_mismatch = bool(
            item.get("embedding_model_dimension_mismatch", False)
        )
        total_wiki_chunks = int(item.get("total_wiki_chunks", 0) or 0)
        stale_unindexed_chunks = int(item.get("stale_unindexed_chunks", 0) or 0)
        raw_overlap = item.get("chunk_overlap_ratio", 0.15)
        chunk_overlap_ratio = float(
            0.15 if raw_overlap is None else raw_overlap
        )
        prompt_injection_sanitizer_active = bool(
            item.get("prompt_injection_sanitizer_active", True)
        )

        embedding_drift_pct = (
            round((stale_unindexed_chunks / total_wiki_chunks) * 100.0, 2)
            if total_wiki_chunks > 0
            else 0.0
        )
        max_observed_drift_pct = max(
            max_observed_drift_pct, embedding_drift_pct
        )

        critical_rag_breach = (
            not acl_pre_filtering_enforced_before_ann
            or not cross_tenant_namespace_isolated
            or embedding_model_dimension_mismatch is True
            or not prompt_injection_sanitizer_active
            or embedding_drift_pct > max_embedding_drift_pct * 3.0
        )
        rag_quality_warning = (not critical_rag_breach) and (
            embedding_drift_pct > max_embedding_drift_pct
            or chunk_overlap_ratio < min_chunk_overlap_ratio
            or chunk_overlap_ratio > max_chunk_overlap_ratio
        )

        if critical_rag_breach:
            critical_indexes.append(index_id)
        elif rag_quality_warning:
            warning_indexes.append(index_id)

        index_evaluations.append(
            {
                "index_id": index_id,
                "acl_pre_filtering_enforced_before_ann": acl_pre_filtering_enforced_before_ann,
                "cross_tenant_namespace_isolated": cross_tenant_namespace_isolated,
                "embedding_model_dimension_mismatch": embedding_model_dimension_mismatch,
                "total_wiki_chunks": total_wiki_chunks,
                "stale_unindexed_chunks": stale_unindexed_chunks,
                "embedding_drift_pct": embedding_drift_pct,
                "chunk_overlap_ratio": chunk_overlap_ratio,
                "prompt_injection_sanitizer_active": prompt_injection_sanitizer_active,
                "critical_rag_breach": critical_rag_breach,
                "rag_quality_warning": rag_quality_warning,
            }
        )

    if len(critical_indexes) > 0:
        status = "CRITICAL"
    elif len(warning_indexes) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_indexes_count": len(index_evaluations),
        "critical_indexes": critical_indexes,
        "warning_indexes": warning_indexes,
        "max_observed_drift_pct": max_observed_drift_pct,
        "index_evaluations": index_evaluations,
    }


WikiPMIService.audit_wiki_vector_rag_index_drift_and_acl_prefilter_guard = staticmethod(
    audit_wiki_vector_rag_index_drift_and_acl_prefilter_guard
)


def audit_wiki_websocket_presence_backpressure_and_zombie_socket_hygiene(
    gateways: list[dict[str, Any]],
    *,
    max_zombie_socket_ratio_pct: float = 2.0,
    max_send_buffer_utilization_pct: float = 80.0,
    max_fanout_latency_p99_ms: float = 250.0,
) -> dict[str, Any]:
    """PMBOK §4.4 & §11.6 — Wiki WebSocket / SSE Real-Time Presence Fan-Out Backpressure, Slow-Consumer RingBuffer Drop & Heartbeat Ping/Pong Zombie Connection Auditor."""
    gateway_evaluations: list[dict[str, Any]] = []
    critical_gateways: list[str] = []
    warning_gateways: list[str] = []
    peak_send_buffer_utilization_pct = 0.0

    for item in gateways or []:
        if not isinstance(item, Mapping):
            continue
        gateway_id = str(item.get("gateway_id") or "").strip() or "UNKNOWN_GATEWAY"
        active_connections = int(item.get("active_connections", 0) or 0)
        zombie_unacked_ping_connections = int(
            item.get("zombie_unacked_ping_connections", 0) or 0
        )
        raw_buf = item.get("send_buffer_utilization_pct", 30.0)
        send_buffer_utilization_pct = round(
            float(30.0 if raw_buf is None else raw_buf), 2
        )
        slow_consumer_disconnect_policy_enabled = bool(
            item.get("slow_consumer_disconnect_policy_enabled", True)
        )
        raw_lat = item.get("fanout_latency_p99_ms", 45.0)
        fanout_latency_p99_ms = round(
            float(45.0 if raw_lat is None else raw_lat), 2
        )
        per_ip_connection_rate_limit_enforced = bool(
            item.get("per_ip_connection_rate_limit_enforced", True)
        )
        ephemeral_port_exhaustion_risk = bool(
            item.get("ephemeral_port_exhaustion_risk", False)
        )

        zombie_socket_ratio_pct = (
            round(
                (zombie_unacked_ping_connections / active_connections) * 100.0, 2
            )
            if active_connections > 0
            else 0.0
        )
        peak_send_buffer_utilization_pct = max(
            peak_send_buffer_utilization_pct, send_buffer_utilization_pct
        )

        critical_ws_breach = (
            ephemeral_port_exhaustion_risk is True
            or not slow_consumer_disconnect_policy_enabled
            or not per_ip_connection_rate_limit_enforced
            or send_buffer_utilization_pct > 95.0
            or fanout_latency_p99_ms > max_fanout_latency_p99_ms * 2.0
        )
        ws_backpressure_warning = (not critical_ws_breach) and (
            zombie_socket_ratio_pct > max_zombie_socket_ratio_pct
            or send_buffer_utilization_pct > max_send_buffer_utilization_pct
            or fanout_latency_p99_ms > max_fanout_latency_p99_ms
        )

        if critical_ws_breach:
            critical_gateways.append(gateway_id)
        elif ws_backpressure_warning:
            warning_gateways.append(gateway_id)

        gateway_evaluations.append(
            {
                "gateway_id": gateway_id,
                "active_connections": active_connections,
                "zombie_unacked_ping_connections": zombie_unacked_ping_connections,
                "zombie_socket_ratio_pct": zombie_socket_ratio_pct,
                "send_buffer_utilization_pct": send_buffer_utilization_pct,
                "slow_consumer_disconnect_policy_enabled": slow_consumer_disconnect_policy_enabled,
                "fanout_latency_p99_ms": fanout_latency_p99_ms,
                "per_ip_connection_rate_limit_enforced": per_ip_connection_rate_limit_enforced,
                "ephemeral_port_exhaustion_risk": ephemeral_port_exhaustion_risk,
                "critical_ws_breach": critical_ws_breach,
                "ws_backpressure_warning": ws_backpressure_warning,
            }
        )

    if len(critical_gateways) > 0:
        status = "CRITICAL"
    elif len(warning_gateways) > 0:
        status = "WARNING"
    else:
        status = "HEALTHY"

    return {
        "status": status,
        "evaluated_gateways_count": len(gateway_evaluations),
        "critical_gateways": critical_gateways,
        "warning_gateways": warning_gateways,
        "peak_send_buffer_utilization_pct": peak_send_buffer_utilization_pct,
        "gateway_evaluations": gateway_evaluations,
    }


WikiPMIService.audit_wiki_websocket_presence_backpressure_and_zombie_socket_hygiene = staticmethod(
    audit_wiki_websocket_presence_backpressure_and_zombie_socket_hygiene
)


def audit_wiki_distributed_lock_fencing_token_and_split_brain_guard(
    lock_events: list[dict[str, Any]],
    *,
    max_heartbeat_skew_ms: float = 1500.0,
    min_quorum_nodes: int = 3,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Distributed Lock Fencing Token Monotonicity, Lease Heartbeat & Split-Brain Guard Auditor."""
    normalized_max_skew = max(float(max_heartbeat_skew_ms), 50.0)
    normalized_min_quorum = max(int(min_quorum_nodes), 1)

    raw_events = lock_events if isinstance(lock_events, list) else []
    events: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    unblocked_split_brain_count = 0
    stale_fencing_token_count = 0
    quorum_shortfall_count = 0
    heartbeat_skew_breach_count = 0

    for idx, item in enumerate(raw_events, start=1):
        if not isinstance(item, dict):
            continue
        event_id = str(item.get("event_id") or f"lock-evt-{idx}").strip()
        page_id = str(item.get("page_id") or f"page-{idx}").strip()
        try:
            fencing_token = int(item.get("fencing_token", 0) or 0)
        except (TypeError, ValueError):
            fencing_token = 0
        try:
            storage_highest_token = int(item.get("storage_highest_token", 0) or 0)
        except (TypeError, ValueError):
            storage_highest_token = 0
        try:
            quorum_acks = int(item.get("quorum_acks", 0) or 0)
        except (TypeError, ValueError):
            quorum_acks = 0
        lease_expired_before_commit = bool(
            item.get("lease_expired_before_commit", False)
        )
        try:
            heartbeat_skew_ms = float(item.get("heartbeat_skew_ms", 0.0) or 0.0)
        except (TypeError, ValueError):
            heartbeat_skew_ms = 0.0
        storage_rejected_stale_token = bool(
            item.get("storage_rejected_stale_token", True)
        )

        stale_fencing_token_detected = (
            fencing_token < storage_highest_token or fencing_token <= 0
        )
        unblocked_split_brain_write = (
            stale_fencing_token_detected or lease_expired_before_commit
        ) and not storage_rejected_stale_token
        quorum_shortfall = quorum_acks < normalized_min_quorum
        heartbeat_skew_breach = heartbeat_skew_ms > normalized_max_skew

        if unblocked_split_brain_write:
            unblocked_split_brain_count += 1
        if stale_fencing_token_detected:
            stale_fencing_token_count += 1
        if quorum_shortfall:
            quorum_shortfall_count += 1
        if heartbeat_skew_breach:
            heartbeat_skew_breach_count += 1

        if unblocked_split_brain_write or quorum_shortfall:
            event_status = "critical"
            critical_count += 1
        elif (
            stale_fencing_token_detected
            or lease_expired_before_commit
            or heartbeat_skew_breach
        ):
            event_status = "warning"
            warning_count += 1
        else:
            event_status = "healthy"
            healthy_count += 1

        events.append(
            {
                "event_id": event_id,
                "page_id": page_id,
                "fencing_token": fencing_token,
                "storage_highest_token": storage_highest_token,
                "quorum_acks": quorum_acks,
                "lease_expired_before_commit": lease_expired_before_commit,
                "heartbeat_skew_ms": heartbeat_skew_ms,
                "storage_rejected_stale_token": storage_rejected_stale_token,
                "stale_fencing_token_detected": stale_fencing_token_detected,
                "unblocked_split_brain_write": unblocked_split_brain_write,
                "quorum_shortfall": quorum_shortfall,
                "heartbeat_skew_breach": heartbeat_skew_breach,
                "event_status": event_status,
            }
        )

    total_events = len(events)
    fencing_integrity_rate_pct = (
        round((healthy_count / total_events) * 100.0, 2)
        if total_events > 0
        else 100.0
    )

    recommendations: list[str] = []
    if unblocked_split_brain_count > 0:
        recommendations.append(
            f"Bloquear inmediatamente escrituras con fencing_token obsoleto o lease expirado en la capa de almacenamiento ({unblocked_split_brain_count} evento(s) split-brain)."
        )
    if quorum_shortfall_count > 0:
        recommendations.append(
            f"Exigir quórum mínimo de {normalized_min_quorum} nodos antes de conceder el lock distribuido ({quorum_shortfall_count} evento(s))."
        )
    if stale_fencing_token_count > 0:
        recommendations.append(
            f"Auditar emisores con fencing_token <= storage_highest_token por pausas GC o particiones de red ({stale_fencing_token_count} evento(s))."
        )
    if heartbeat_skew_breach_count > 0:
        recommendations.append(
            f"Reducir heartbeat_skew_ms por debajo de {normalized_max_skew}ms para evitar expiraciones prematuras de lease ({heartbeat_skew_breach_count} evento(s))."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_events": total_events,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "unblocked_split_brain_count": unblocked_split_brain_count,
        "stale_fencing_token_count": stale_fencing_token_count,
        "quorum_shortfall_count": quorum_shortfall_count,
        "heartbeat_skew_breach_count": heartbeat_skew_breach_count,
        "fencing_integrity_rate_pct": fencing_integrity_rate_pct,
        "status": status,
        "events": events,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_distributed_lock_fencing_token_and_split_brain_guard = staticmethod(
    audit_wiki_distributed_lock_fencing_token_and_split_brain_guard
)


def audit_wiki_graphql_query_depth_alias_budget_and_introspection_guard(
    queries: list[dict[str, Any]],
    *,
    max_query_depth: int = 8,
    max_complexity_cost: int = 1000,
    max_aliases_per_query: int = 15,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki GraphQL AST Query Depth, Alias Amplification Budget & Schema Introspection Leak Guard Auditor."""
    normalized_max_depth = max(int(max_query_depth), 1)
    normalized_max_cost = max(int(max_complexity_cost), 10)
    normalized_max_aliases = max(int(max_aliases_per_query), 1)

    raw_queries = queries if isinstance(queries, list) else []
    evaluated_queries: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    unauthenticated_introspection_count = 0
    unblocked_dos_count = 0
    depth_exceeded_count = 0
    alias_amplification_count = 0

    for idx, item in enumerate(raw_queries, start=1):
        if not isinstance(item, dict):
            continue
        query_id = str(item.get("query_id") or f"gql-query-{idx}").strip()
        raw_depth = item.get("ast_depth", 1)
        try:
            ast_depth = int(1 if raw_depth is None else raw_depth)
        except (TypeError, ValueError):
            ast_depth = 1

        raw_cost = item.get("estimated_complexity_cost", 10)
        try:
            estimated_complexity_cost = int(10 if raw_cost is None else raw_cost)
        except (TypeError, ValueError):
            estimated_complexity_cost = 10

        raw_aliases = item.get("alias_count", 0)
        try:
            alias_count = int(0 if raw_aliases is None else raw_aliases)
        except (TypeError, ValueError):
            alias_count = 0

        contains_schema_introspection = bool(
            item.get("contains_schema_introspection", False)
        )
        is_production_unauthenticated = bool(
            item.get("is_production_unauthenticated", False)
        )
        cost_limiter_enforced_rejection = bool(
            item.get("cost_limiter_enforced_rejection", True)
        )

        depth_limit_exceeded = ast_depth > normalized_max_depth
        complexity_budget_exceeded = (
            estimated_complexity_cost > normalized_max_cost
        )
        alias_amplification_detected = alias_count > normalized_max_aliases
        unauthenticated_introspection_leak = (
            contains_schema_introspection and is_production_unauthenticated
        )
        unblocked_dos_amplification = (
            depth_limit_exceeded
            or complexity_budget_exceeded
            or alias_amplification_detected
        ) and not cost_limiter_enforced_rejection

        if unauthenticated_introspection_leak:
            unauthenticated_introspection_count += 1
        if unblocked_dos_amplification:
            unblocked_dos_count += 1
        if depth_limit_exceeded:
            depth_exceeded_count += 1
        if alias_amplification_detected:
            alias_amplification_count += 1

        if unauthenticated_introspection_leak or unblocked_dos_amplification:
            query_status = "critical"
            critical_count += 1
        elif (
            depth_limit_exceeded
            or complexity_budget_exceeded
            or alias_amplification_detected
            or contains_schema_introspection
        ):
            query_status = "warning"
            warning_count += 1
        else:
            query_status = "healthy"
            healthy_count += 1

        evaluated_queries.append(
            {
                "query_id": query_id,
                "ast_depth": ast_depth,
                "estimated_complexity_cost": estimated_complexity_cost,
                "alias_count": alias_count,
                "contains_schema_introspection": contains_schema_introspection,
                "is_production_unauthenticated": is_production_unauthenticated,
                "cost_limiter_enforced_rejection": cost_limiter_enforced_rejection,
                "depth_limit_exceeded": depth_limit_exceeded,
                "complexity_budget_exceeded": complexity_budget_exceeded,
                "alias_amplification_detected": alias_amplification_detected,
                "unauthenticated_introspection_leak": unauthenticated_introspection_leak,
                "unblocked_dos_amplification": unblocked_dos_amplification,
                "query_status": query_status,
            }
        )

    total_queries = len(evaluated_queries)
    graphql_shield_rate_pct = (
        round((healthy_count / total_queries) * 100.0, 2)
        if total_queries > 0
        else 100.0
    )

    recommendations: list[str] = []
    if unauthenticated_introspection_count > 0:
        recommendations.append(
            f"Deshabilitar introspección de esquema GraphQL (__schema/__type) para tráfico no autenticado en producción ({unauthenticated_introspection_count} consulta(s))."
        )
    if unblocked_dos_count > 0:
        recommendations.append(
            f"Activar rechazo estricto en el cost/depth limiter antes de ejecutar resolvers para {unblocked_dos_count} consulta(s) con amplificación DoS."
        )
    if depth_exceeded_count > 0:
        recommendations.append(
            f"Restringir profundidad AST GraphQL <= {normalized_max_depth} niveles en {depth_exceeded_count} consulta(s)."
        )
    if alias_amplification_count > 0:
        recommendations.append(
            f"Limitar número de alias por operación GraphQL <= {normalized_max_aliases} para prevenir ataques de batching/alias amplification ({alias_amplification_count} consulta(s))."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_queries": total_queries,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "unauthenticated_introspection_count": unauthenticated_introspection_count,
        "unblocked_dos_count": unblocked_dos_count,
        "depth_exceeded_count": depth_exceeded_count,
        "alias_amplification_count": alias_amplification_count,
        "graphql_shield_rate_pct": graphql_shield_rate_pct,
        "status": status,
        "queries": evaluated_queries,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_graphql_query_depth_alias_budget_and_introspection_guard = staticmethod(
    audit_wiki_graphql_query_depth_alias_budget_and_introspection_guard
)


def audit_wiki_presigned_url_ttl_and_bucket_public_acl_guard(
    attachments: list[dict[str, Any]],
    *,
    max_presigned_ttl_seconds: int = 900,
    max_upload_size_mb: float = 50.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Object Storage Presigned URL TTL, Content-Disposition Anti-XSS & Bucket Public ACL Block Guard Auditor."""
    normalized_max_ttl = max(int(max_presigned_ttl_seconds), 60)
    normalized_max_size_mb = max(float(max_upload_size_mb), 1.0)

    raw_attachments = attachments if isinstance(attachments, list) else []
    evaluated_attachments: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    public_or_infected_count = 0
    inline_xss_risk_count = 0
    excessive_ttl_count = 0
    oversized_upload_count = 0

    for idx, item in enumerate(raw_attachments, start=1):
        if not isinstance(item, dict):
            continue
        attachment_id = str(
            item.get("attachment_id") or f"wiki-att-{idx}"
        ).strip()

        raw_ttl = item.get("presigned_ttl_seconds", 300)
        try:
            presigned_ttl_seconds = int(300 if raw_ttl is None else raw_ttl)
        except (TypeError, ValueError):
            presigned_ttl_seconds = 300

        raw_size = item.get("size_mb", 1.0)
        try:
            size_mb = float(1.0 if raw_size is None else raw_size)
        except (TypeError, ValueError):
            size_mb = 1.0

        bucket_public_access_blocked = bool(
            item.get("bucket_public_access_blocked", True)
        )
        av_malware_scan_clean = bool(item.get("av_malware_scan_clean", True))
        content_disposition_attachment_enforced = bool(
            item.get("content_disposition_attachment_enforced", True)
        )
        executable_mime_sniffer_blocked = bool(
            item.get("executable_mime_sniffer_blocked", True)
        )

        public_bucket_exposure_or_infected = (
            not bucket_public_access_blocked or not av_malware_scan_clean
        )
        stored_xss_inline_execution_risk = (
            not content_disposition_attachment_enforced
            or not executable_mime_sniffer_blocked
        )
        excessive_presigned_ttl = (
            presigned_ttl_seconds > normalized_max_ttl
            or presigned_ttl_seconds <= 0
        )
        oversized_upload = size_mb > normalized_max_size_mb

        if public_bucket_exposure_or_infected:
            public_or_infected_count += 1
        if stored_xss_inline_execution_risk:
            inline_xss_risk_count += 1
        if excessive_presigned_ttl:
            excessive_ttl_count += 1
        if oversized_upload:
            oversized_upload_count += 1

        if (
            public_bucket_exposure_or_infected
            or stored_xss_inline_execution_risk
        ):
            attachment_status = "critical"
            critical_count += 1
        elif excessive_presigned_ttl or oversized_upload:
            attachment_status = "warning"
            warning_count += 1
        else:
            attachment_status = "healthy"
            healthy_count += 1

        evaluated_attachments.append(
            {
                "attachment_id": attachment_id,
                "presigned_ttl_seconds": presigned_ttl_seconds,
                "size_mb": size_mb,
                "bucket_public_access_blocked": bucket_public_access_blocked,
                "av_malware_scan_clean": av_malware_scan_clean,
                "content_disposition_attachment_enforced": content_disposition_attachment_enforced,
                "executable_mime_sniffer_blocked": executable_mime_sniffer_blocked,
                "public_bucket_exposure_or_infected": public_bucket_exposure_or_infected,
                "stored_xss_inline_execution_risk": stored_xss_inline_execution_risk,
                "excessive_presigned_ttl": excessive_presigned_ttl,
                "oversized_upload": oversized_upload,
                "attachment_status": attachment_status,
            }
        )

    total_attachments = len(evaluated_attachments)
    storage_security_rate_pct = (
        round((healthy_count / total_attachments) * 100.0, 2)
        if total_attachments > 0
        else 100.0
    )

    recommendations: list[str] = []
    if public_or_infected_count > 0:
        recommendations.append(
            f"Bloquear inmediatamente acceso público al bucket S3/Object Storage y poner en cuarentena adjuntos con detección antimalware positiva ({public_or_infected_count} adjunto(s))."
        )
    if inline_xss_risk_count > 0:
        recommendations.append(
            f"Forzar cabeceras Content-Disposition: attachment y X-Content-Type-Options: nosniff para prevenir XSS almacenado en {inline_xss_risk_count} adjunto(s)."
        )
    if excessive_ttl_count > 0:
        recommendations.append(
            f"Restringir el tiempo de expiración de Presigned URLs dentro del rango (0, {normalized_max_ttl}] segundos en {excessive_ttl_count} adjunto(s)."
        )
    if oversized_upload_count > 0:
        recommendations.append(
            f"Aplicar límite de tamaño máximo de carga <= {normalized_max_size_mb} MB en {oversized_upload_count} adjunto(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_attachments": total_attachments,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "public_or_infected_count": public_or_infected_count,
        "inline_xss_risk_count": inline_xss_risk_count,
        "excessive_ttl_count": excessive_ttl_count,
        "oversized_upload_count": oversized_upload_count,
        "storage_security_rate_pct": storage_security_rate_pct,
        "status": status,
        "attachments": evaluated_attachments,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_presigned_url_ttl_and_bucket_public_acl_guard = staticmethod(
    audit_wiki_presigned_url_ttl_and_bucket_public_acl_guard
)


def audit_wiki_fts_bm25_index_bloat_and_reindex_lock_guard(
    indices: list[dict[str, Any]],
    *,
    max_bloat_ratio_pct: float = 30.0,
    max_p99_search_latency_ms: float = 120.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Full-Text Search (BM25 / GIN Trigram) Index Bloat, Reindex Concurrently Guard & P99 Latency Auditor."""
    normalized_max_bloat = min(max(float(max_bloat_ratio_pct), 1.0), 95.0)
    normalized_max_latency = max(float(max_p99_search_latency_ms), 5.0)

    raw_indices = indices if isinstance(indices, list) else []
    evaluated_indices: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    blocking_reindex_count = 0
    bloat_exceeded_count = 0
    latency_breach_count = 0
    gin_or_locale_drift_count = 0

    for idx, item in enumerate(raw_indices, start=1):
        if not isinstance(item, dict):
            continue
        index_id = str(item.get("index_id") or f"wiki-fts-idx-{idx}").strip()

        raw_bloat = item.get("dead_tuple_bloat_pct", 5.0)
        try:
            dead_tuple_bloat_pct = float(5.0 if raw_bloat is None else raw_bloat)
        except (TypeError, ValueError):
            dead_tuple_bloat_pct = 5.0

        raw_latency = item.get("p99_search_latency_ms", 25.0)
        try:
            p99_search_latency_ms = float(
                25.0 if raw_latency is None else raw_latency
            )
        except (TypeError, ValueError):
            p99_search_latency_ms = 25.0

        reindex_uses_concurrently = bool(
            item.get("reindex_uses_concurrently", True)
        )

        raw_gin_overflow = item.get("gin_pending_list_overflow_kb", 0.0)
        try:
            gin_pending_list_overflow_kb = float(
                0.0 if raw_gin_overflow is None else raw_gin_overflow
            )
        except (TypeError, ValueError):
            gin_pending_list_overflow_kb = 0.0

        dictionary_stemmer_locale_mismatch = bool(
            item.get("dictionary_stemmer_locale_mismatch", False)
        )

        blocking_reindex_table_lock = not reindex_uses_concurrently
        bloat_threshold_exceeded = dead_tuple_bloat_pct > normalized_max_bloat
        search_latency_slo_breach = (
            p99_search_latency_ms > normalized_max_latency
        )
        gin_fastupdate_or_locale_drift = (
            gin_pending_list_overflow_kb > 4096.0
            or dictionary_stemmer_locale_mismatch
        )

        if blocking_reindex_table_lock:
            blocking_reindex_count += 1
        if bloat_threshold_exceeded:
            bloat_exceeded_count += 1
        if search_latency_slo_breach:
            latency_breach_count += 1
        if gin_fastupdate_or_locale_drift:
            gin_or_locale_drift_count += 1

        if blocking_reindex_table_lock or (
            bloat_threshold_exceeded and search_latency_slo_breach
        ):
            index_status = "critical"
            critical_count += 1
        elif (
            bloat_threshold_exceeded
            or search_latency_slo_breach
            or gin_fastupdate_or_locale_drift
        ):
            index_status = "warning"
            warning_count += 1
        else:
            index_status = "healthy"
            healthy_count += 1

        evaluated_indices.append(
            {
                "index_id": index_id,
                "dead_tuple_bloat_pct": dead_tuple_bloat_pct,
                "p99_search_latency_ms": p99_search_latency_ms,
                "reindex_uses_concurrently": reindex_uses_concurrently,
                "gin_pending_list_overflow_kb": gin_pending_list_overflow_kb,
                "dictionary_stemmer_locale_mismatch": dictionary_stemmer_locale_mismatch,
                "blocking_reindex_table_lock": blocking_reindex_table_lock,
                "bloat_threshold_exceeded": bloat_threshold_exceeded,
                "search_latency_slo_breach": search_latency_slo_breach,
                "gin_fastupdate_or_locale_drift": gin_fastupdate_or_locale_drift,
                "index_status": index_status,
            }
        )

    total_indices = len(evaluated_indices)
    fts_health_rate_pct = (
        round((healthy_count / total_indices) * 100.0, 2)
        if total_indices > 0
        else 100.0
    )

    recommendations: list[str] = []
    if blocking_reindex_count > 0:
        recommendations.append(
            f"Exigir REINDEX INDEX CONCURRENTLY para evitar bloqueos exclusivos de tabla (AccessExclusiveLock) en {blocking_reindex_count} índice(s) FTS."
        )
    if bloat_exceeded_count > 0:
        recommendations.append(
            f"Compactar índices con dead_tuple_bloat_pct > {normalized_max_bloat}% mediante autovacuum agresivo o reindexación concurrente en {bloat_exceeded_count} índice(s)."
        )
    if latency_breach_count > 0:
        recommendations.append(
            f"Optimizar consultas BM25/GIN para reducir latencia p99 <= {normalized_max_latency} ms en {latency_breach_count} índice(s)."
        )
    if gin_or_locale_drift_count > 0:
        recommendations.append(
            f"Purgar GIN pending list (gin_clean_pending_list) <= 4096 KB y alinear configuración de stemmer/diccionario en {gin_or_locale_drift_count} índice(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_indices": total_indices,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "blocking_reindex_count": blocking_reindex_count,
        "bloat_exceeded_count": bloat_exceeded_count,
        "latency_breach_count": latency_breach_count,
        "gin_or_locale_drift_count": gin_or_locale_drift_count,
        "fts_health_rate_pct": fts_health_rate_pct,
        "status": status,
        "indices": evaluated_indices,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_fts_bm25_index_bloat_and_reindex_lock_guard = staticmethod(
    audit_wiki_fts_bm25_index_bloat_and_reindex_lock_guard
)


def audit_wiki_crdt_vector_clock_divergence_and_tombstone_gc_guard(
    replicas: list[dict[str, Any]],
    *,
    max_causal_lag_ops: int = 500,
    max_tombstone_ratio_pct: float = 25.0,
) -> dict[str, Any]:
    """PMI PMBOK §4.4 & §11.6 — Wiki Multi-Region CRDT Vector-Clock Causal Divergence & Tombstone GC Compaction Guard Auditor."""
    normalized_max_lag = max(int(max_causal_lag_ops), 1)
    normalized_max_tombstone = min(max(float(max_tombstone_ratio_pct), 1.0), 95.0)

    raw_replicas = replicas if isinstance(replicas, list) else []
    evaluated_replicas: list[dict[str, Any]] = []
    healthy_count = 0
    warning_count = 0
    critical_count = 0
    corruption_or_resurrection_count = 0
    move_cycle_count = 0
    causal_lag_exceeded_count = 0
    tombstone_bloat_count = 0

    for idx, item in enumerate(raw_replicas, start=1):
        if not isinstance(item, dict):
            continue
        replica_id = str(
            item.get("replica_id") or f"wiki-crdt-replica-{idx}"
        ).strip()

        raw_lag = item.get("unmerged_causal_lag_ops", 0)
        try:
            unmerged_causal_lag_ops = int(0 if raw_lag is None else raw_lag)
        except (TypeError, ValueError):
            unmerged_causal_lag_ops = 0

        raw_tombstone = item.get("tombstone_overhead_pct", 5.0)
        try:
            tombstone_overhead_pct = float(
                5.0 if raw_tombstone is None else raw_tombstone
            )
        except (TypeError, ValueError):
            tombstone_overhead_pct = 5.0

        gc_grace_period_expired_before_anti_entropy = bool(
            item.get("gc_grace_period_expired_before_anti_entropy", False)
        )
        state_vector_checksum_matched = bool(
            item.get("state_vector_checksum_matched", True)
        )
        concurrent_move_cycle_detected = bool(
            item.get("concurrent_move_cycle_detected", False)
        )

        zombie_resurrection_or_checksum_corruption = (
            gc_grace_period_expired_before_anti_entropy
            or not state_vector_checksum_matched
        )
        causal_divergence_lag_exceeded = (
            unmerged_causal_lag_ops > normalized_max_lag
        )
        tombstone_bloat_exceeded = (
            tombstone_overhead_pct > normalized_max_tombstone
        )
        tree_move_cycle_anomaly = concurrent_move_cycle_detected

        if zombie_resurrection_or_checksum_corruption:
            corruption_or_resurrection_count += 1
        if tree_move_cycle_anomaly:
            move_cycle_count += 1
        if causal_divergence_lag_exceeded:
            causal_lag_exceeded_count += 1
        if tombstone_bloat_exceeded:
            tombstone_bloat_count += 1

        if (
            zombie_resurrection_or_checksum_corruption
            or tree_move_cycle_anomaly
        ):
            replica_status = "critical"
            critical_count += 1
        elif causal_divergence_lag_exceeded or tombstone_bloat_exceeded:
            replica_status = "warning"
            warning_count += 1
        else:
            replica_status = "healthy"
            healthy_count += 1

        evaluated_replicas.append(
            {
                "replica_id": replica_id,
                "unmerged_causal_lag_ops": unmerged_causal_lag_ops,
                "tombstone_overhead_pct": tombstone_overhead_pct,
                "gc_grace_period_expired_before_anti_entropy": gc_grace_period_expired_before_anti_entropy,
                "state_vector_checksum_matched": state_vector_checksum_matched,
                "concurrent_move_cycle_detected": concurrent_move_cycle_detected,
                "zombie_resurrection_or_checksum_corruption": zombie_resurrection_or_checksum_corruption,
                "causal_divergence_lag_exceeded": causal_divergence_lag_exceeded,
                "tombstone_bloat_exceeded": tombstone_bloat_exceeded,
                "tree_move_cycle_anomaly": tree_move_cycle_anomaly,
                "replica_status": replica_status,
            }
        )

    total_replicas = len(evaluated_replicas)
    crdt_convergence_rate_pct = (
        round((healthy_count / total_replicas) * 100.0, 2)
        if total_replicas > 0
        else 100.0
    )

    recommendations: list[str] = []
    if corruption_or_resurrection_count > 0:
        recommendations.append(
            f"Suspender purgado de tombstones antes del ciclo anti-entropía y reconciliar checksum del vector de estado en {corruption_or_resurrection_count} réplica(s) CRDT."
        )
    if move_cycle_count > 0:
        recommendations.append(
            f"Ejecutar algoritmo Kleppmann tree-move undo/redo para deshacer ciclos concurrentes en {move_cycle_count} réplica(s) CRDT."
        )
    if causal_lag_exceeded_count > 0:
        recommendations.append(
            f"Acelerar difusión gossip de deltas de reloj vectorial para mantener operaciones sin fusionar <= {normalized_max_lag} en {causal_lag_exceeded_count} réplica(s)."
        )
    if tombstone_bloat_count > 0:
        recommendations.append(
            f"Ejecutar compactación GC de tombstones tras quórum causal para reducir sobrecarga <= {normalized_max_tombstone}% en {tombstone_bloat_count} réplica(s)."
        )

    if critical_count > 0:
        status = "critical"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "healthy"

    return {
        "total_replicas": total_replicas,
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "corruption_or_resurrection_count": corruption_or_resurrection_count,
        "move_cycle_count": move_cycle_count,
        "causal_lag_exceeded_count": causal_lag_exceeded_count,
        "tombstone_bloat_count": tombstone_bloat_count,
        "crdt_convergence_rate_pct": crdt_convergence_rate_pct,
        "status": status,
        "replicas": evaluated_replicas,
        "recommendations": recommendations,
    }


WikiPMIService.audit_wiki_crdt_vector_clock_divergence_and_tombstone_gc_guard = staticmethod(
    audit_wiki_crdt_vector_clock_divergence_and_tombstone_gc_guard
)


