"""Servicio de doctrina PMI y gestión de páginas canónicas en la Wiki Ministerial.

Carga e indexa los 7 volúmenes canónicos de la biblioteca metodológica PMI
en la tabla `wiki_pages` para consulta universal por los equipos de proyectos.
"""

from __future__ import annotations

import logging
import os
import re
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

