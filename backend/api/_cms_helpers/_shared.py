"""Axioma 3 — Multi-Tenant scope helpers + SEO audit helpers (CMS routes).

This module is the SINGLE canonical helper module for ``_cms_helpers/`` per
Gate 6 of ``docs/ESTADO_ARQUITECTURA_CCF.md``. Any ad-hoc helper file in
this directory is considered drift and must be merged here.

Two responsibilities coexist:

  1. **Multi-tenant scope helpers** (Axioma 3) for User-Generated Content
     CMS routes: ``Testimonial``, ``Announcement``, ``CmsMediaItem`` y
     ``Persona`` (perfil pastoral). Patrón consistente con ``backend/api/crm/_shared.py``.

     Reglas:
       - El helper SIEMPRE devuelve 404 (no 403) ante cross-sede o target
         inexistente. Existence-leak safe.
       - Si el staff actual no tiene sede (``_actor_sede_or_none`` retorna
         ``None`` → superadmin / anterior path), se omite el scope filter.
       - Cierre del IDOR crítico en ``cms_pastoral_profile_update``
         vía ``_get_scoped_persona`` importada desde ``backend.api.crm._shared``.

  2. **SEO audit helpers** para el faro global (``CmsSite``/``CmsPage``).
     Las funciones son puras — reciben modelos ORM ya materializados y
     retornan ``schemas.SeoFinding`` / ``schemas.PageSeoAudit``. Operan
     sin scope de sede por diseño editorial (Axioma 3: contenido del
     site público es cross-sede).
"""

from __future__ import annotations

import re
import uuid as _uuid
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api.crm._shared import _get_scoped_persona  # noqa: F401
from backend.crud.crm import get_user_sede_id

# ─────────────────────────────────────────────────────────────────
# 1) MULTI-TENANT SCOPE HELPERS (Axioma 3)
# ─────────────────────────────────────────────────────────────────


def _actor_sede_or_none(db: Session, current_user: models.User) -> Optional[str]:
    """Retorna la sede del actor o ``None`` para superadministración."""
    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, user_id)


def _scope_cms_testimonials_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.Testimonial`` por ``sede_id == user_sede``.

    Si el actor canónico no tiene sede (superadmin), retorna el query sin
    modificar y conserva el alcance administrativo global.

    Testimonial exige ``sede_id`` propio desde la migración 2026-07-01. El
    scope se aplica de forma directa sin necesidad de JOIN.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.Testimonial.sede_id == user_sede)
    return query


def _scope_cms_announcements_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.Announcement`` por ``sede_id == user_sede``.

    Announcement exige ``sede_id`` + ``created_by_persona_id`` no nulos.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.Announcement.sede_id == user_sede)
    return query


def _scope_cms_media_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de ``models.CmsMediaItem`` por ``sede_id == user_sede``.

    CmsMediaItem exige ``sede_id`` propio desde la migración 2026-07-01 y
    permite filtrado directo, eficiente y consistente.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(models.CmsMediaItem.sede_id == user_sede)
    return query


def _scope_cms_pastoral_team_by_user_sede(
    db: Session, current_user: models.User, query
):
    """Filtra un query de pastoral-leaders por ``Persona.sede_id ==
    user_sede``. Si el actor canónico no tiene sede (superadmin), retorna el
    query sin modificar y conserva el alcance administrativo global.

    Incluye personas con sede_id NULL (sin sede asignada) para que aparezcan
    en todas las sedes. Esto permite que pastores sin sede específica sean
    visibles globalmente.
    """
    user_sede = _actor_sede_or_none(db, current_user)
    if user_sede:
        query = query.filter(
            (models.Persona.sede_id == user_sede) | (models.Persona.sede_id.is_(None))
        )
    return query


def _get_scoped_cms_testimonial(
    db: Session, current_user: models.User, testimonial_id
) -> models.Testimonial:
    """Devuelve el Testimonial o raise ``HTTPException(404)``.

    Existence-leak safe: devuelve 404 tanto si el testimonial no existe
    como si pertenece a otra sede. Mismo patrón que
    ``_get_scoped_persona``.

    Si el actor es superadmin sin sede, retorna cualquier Testimonial no
    archivado (consistente con el resto de Axioma 3).
    """
    try:
        tid = _uuid.UUID(str(testimonial_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Testimonial no encontrado")

    query = db.query(models.Testimonial).filter(models.Testimonial.id == tid)
    query = _scope_cms_testimonials_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Testimonial no encontrado")
    return row


def _get_scoped_cms_announcement(
    db: Session, current_user: models.User, announcement_id
) -> models.Announcement:
    """Devuelve el Announcement o raise ``HTTPException(404)``.

    Existence-leak safe (mismo patrón que Testimonial).
    """
    try:
        aid = _uuid.UUID(str(announcement_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Announcement no encontrado")

    query = db.query(models.Announcement).filter(models.Announcement.id == aid)
    query = _scope_cms_announcements_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Announcement no encontrado")
    return row


def _get_scoped_cms_media(
    db: Session, current_user: models.User, media_id
) -> models.CmsMediaItem:
    """Devuelve el CmsMediaItem o raise ``HTTPException(404)``.

    Existence-leak safe (mismo patrón que Testimonial / Announcement).
    """
    try:
        mid = _uuid.UUID(str(media_id))
    except (TypeError, ValueError):
        raise HTTPException(status_code=404, detail="Media item no encontrado")

    query = db.query(models.CmsMediaItem).filter(models.CmsMediaItem.id == mid)
    query = _scope_cms_media_by_user_sede(db, current_user, query)
    row = query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Media item no encontrado")
    return row


# ─────────────────────────────────────────────────────────────────
# 2) SEO AUDIT HELPERS (Faro Global)
# ─────────────────────────────────────────────────────────────────
#
# Pesos totales por página = 100 puntos. La puntuación final por página
# es ``max(0, 100 - sum(finding.impact_points))``. Severidades:
#
#   - error:    hallazgo crítico (ej. noindex en página publicada).
#   - warning:  hallazgo importante pero no bloqueante.
#   - info:     nota informativa, sin impacto en puntos.
#
# Migrado desde ``_cms_helpers/seo_audit.py`` (Gate 6 anti-drift):
# cualquier ad-hoc helper en este directorio se considera drift.

# ── Weights (sum to 100 per page) ──

META_DESC_WEIGHT = 25
TITLE_LEN_WEIGHT = 15
INDEXABILITY_WEIGHT = 15
ALT_TEXT_WEIGHT = 20
CONTENT_HEALTH_WEIGHT = 15
OG_IMAGE_WEIGHT = 10

# Reasonable ranges from Google SERP previews & common DRY-RUN heuristics.
META_DESC_MIN = 50
META_DESC_MAX = 160
TITLE_MIN = 15
TITLE_MAX = 65
RICH_TEXT_MIN_WORDS = 100

# Patterns we accept when scanning section ``props_json`` for media
# references and optional alt overrides dentro del mismo section.
MEDIA_REFERENCE_KEYS = ("media_id", "media_ids", "image_id", "image_ids")
ALT_KEYS = ("alt", "alt_text", "image_alt")
RICH_TEXT_BODY_KEYS = ("body", "content", "html", "text")

_WORD_RE = re.compile(r"\b\w+\b", flags=re.UNICODE)


def _uuid_or_none(value) -> Optional[str]:
    """Convierte un valor posiblemente-UUID a string canónico, o None."""
    if value is None:
        return None
    try:
        return str(_uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _section_text(section: models.CmsSection) -> str:
    """Extrae el texto concatenado de los campos de body de la sección.

    Cada section-type guarda el contenido en forma distinta
    (``props_json.content`` como string, ``props_json.body`` como lista
    de bloques, etc.). Esta función intenta cubrirlos todos para no
    subdetectar contenido delgado.
    """
    props = section.props_json if isinstance(section.props_json, dict) else {}
    parts: List[str] = []
    for key in RICH_TEXT_BODY_KEYS:
        value = props.get(key)
        if isinstance(value, str):
            parts.append(value)
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    for nested_key in ("text", "body", "content", "html"):
                        inner = item.get(nested_key)
                        if isinstance(inner, str):
                            parts.append(inner)
            continue
        if isinstance(value, dict):
            for nested_key in ("text", "body", "content", "html"):
                inner = value.get(nested_key)
                if isinstance(inner, str):
                    parts.append(inner)
    return " ".join(parts)


def _word_count(text: str) -> int:
    if not text:
        return 0
    return len(_WORD_RE.findall(text))


def _scan_section_media_refs(section: models.CmsSection) -> Tuple[List[str], bool]:
    """Devuelve ``(media_ids, has_inline_alt)``.

    Revisa los ``MEDIA_REFERENCE_KEYS`` dentro de ``props_json`` para
    extraer UUIDs válidos y verifica si la sección incluye un alt en
    línea (independiente del CmsMediaItem referenciado).
    """
    props = section.props_json if isinstance(section.props_json, dict) else {}
    media_ids: List[str] = []
    for key in MEDIA_REFERENCE_KEYS:
        value = props.get(key)
        if isinstance(value, str):
            parsed = _uuid_or_none(value)
            if parsed:
                media_ids.append(parsed)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    parsed = _uuid_or_none(item)
                    if parsed:
                        media_ids.append(parsed)
    has_inline_alt = any(
        isinstance(props.get(key), str) and (props.get(key) or "").strip()
        for key in ALT_KEYS
    )
    return media_ids, has_inline_alt


def _is_visible(section: models.CmsSection) -> bool:
    return bool(section.is_visible) and (getattr(section, "status", "active") or "active") != "archived"


# ── Per-check evaluators ──


def _check_meta_description(page: models.CmsPage) -> Optional[schemas.SeoFinding]:
    seo = page.seo_json if isinstance(page.seo_json, dict) else {}
    desc = seo.get("meta_description")
    if not desc or not str(desc).strip():
        return schemas.SeoFinding(
            code="meta_description_missing",
            severity="error",
            message="La página no tiene meta descripción configurada.",
            impact_points=META_DESC_WEIGHT,
            hint="Añadir meta descripción en la configuración de la página",
            field_ref="seo_json.meta_description",
        )
    length = len(str(desc).strip())
    if length < META_DESC_MIN:
        return schemas.SeoFinding(
            code="meta_description_too_short",
            severity="warning",
            message=(
                f"Meta descripción muy corta ({length} caracteres). "
                f"Recomendado entre {META_DESC_MIN} y {META_DESC_MAX}."
            ),
            impact_points=10,
            hint="Ampliar la meta descripción para mejorar CTR en Google",
            field_ref="seo_json.meta_description",
        )
    if length > META_DESC_MAX:
        return schemas.SeoFinding(
            code="meta_description_too_long",
            severity="warning",
            message=(
                f"Meta descripción demasiado larga ({length} caracteres). "
                f"Google la truncará después de {META_DESC_MAX}."
            ),
            impact_points=10,
            hint="Recortar la meta descripción para evitar truncamiento",
            field_ref="seo_json.meta_description",
        )
    return None


def _check_title_length(page: models.CmsPage) -> Optional[schemas.SeoFinding]:
    title = (page.title or "").strip()
    length = len(title)
    if length < TITLE_MIN or length > TITLE_MAX:
        return schemas.SeoFinding(
            code="title_length_out_of_range",
            severity="warning",
            message=(
                f"Título con longitud fuera de rango "
                f"({length} caracteres; recomendado {TITLE_MIN}–{TITLE_MAX})."
            ),
            impact_points=TITLE_LEN_WEIGHT,
            hint="Ajustar el título de la página",
            field_ref="title",
        )
    return None


def _check_indexability(page: models.CmsPage) -> Optional[schemas.SeoFinding]:
    seo = page.seo_json if isinstance(page.seo_json, dict) else {}
    robots = (seo.get("robots_meta") or "").strip().lower()
    if page.status != "published":
        return None
    if "noindex" in robots:
        return schemas.SeoFinding(
            code="noindex_on_published",
            severity="error",
            message=(
                "La página está publicada pero marcada con noindex — "
                "no aparecerá en Google."
            ),
            impact_points=INDEXABILITY_WEIGHT,
            hint="Revisar robots_meta en la configuración de la página",
            field_ref="seo_json.robots_meta",
        )
    if "nofollow" in robots:
        return schemas.SeoFinding(
            code="nofollow_on_published",
            severity="warning",
            message=(
                "La página publicada usa 'nofollow' — Google no seguirá "
                "los enlaces salientes."
            ),
            impact_points=5,
            hint="Considerar quitar 'nofollow' si quiere enlazar externamente",
            field_ref="seo_json.robots_meta",
        )
    return None


def _check_content_health(
    page: models.CmsPage,
    sections: List[models.CmsSection],
) -> List[schemas.SeoFinding]:
    findings: List[schemas.SeoFinding] = []
    visible = [s for s in sections if _is_visible(s)]

    if not visible:
        findings.append(
            schemas.SeoFinding(
                code="no_visible_sections",
                severity="error",
                message="La página publicada no tiene secciones visibles.",
                impact_points=CONTENT_HEALTH_WEIGHT,
                hint="Añadir y publicar al menos una sección en el builder",
            )
        )
        return findings

    if len(visible) < 2 and page.status == "published":
        findings.append(
            schemas.SeoFinding(
                code="thin_content_sections",
                severity="info",
                message=(
                    "La página publicada tiene una sola sección visible. "
                    "Sólo se recomienda considerar más estructura editorial si "
                    "el contenido crece."
                ),
                impact_points=0,
                hint="Considerar agregar estructura si el contenido lo amerita",
            )
        )

    rich_sections = [s for s in visible if s.type in ("rich_text", "rich_text_columns")]
    if rich_sections:
        words = sum(_word_count(_section_text(s)) for s in rich_sections)
        if words < RICH_TEXT_MIN_WORDS:
            findings.append(
                schemas.SeoFinding(
                    code="thin_content_text",
                    severity="warning",
                    message=(
                        f"El contenido de texto tiene solo {words} palabras "
                        f"(recomendado ≥ {RICH_TEXT_MIN_WORDS})."
                    ),
                    impact_points=5,
                    hint="Expandir el contenido textual para mejorar ranking",
                )
            )
    return findings


def _check_alt_text(
    sections: List[models.CmsSection],
    media_alt_lookup: Dict[str, Optional[str]],
) -> List[schemas.SeoFinding]:
    findings: List[schemas.SeoFinding] = []
    flagged_sections: set = set()

    for section in sections:
        if not _is_visible(section):
            continue
        props = section.props_json if isinstance(section.props_json, dict) else {}

        media_ids, has_inline_alt = _scan_section_media_refs(section)
        for mid in media_ids:
            alt = media_alt_lookup.get(mid)
            if alt and alt.strip():
                continue
            if str(section.id) in flagged_sections:
                continue
            flagged_sections.add(str(section.id))
            findings.append(
                schemas.SeoFinding(
                    code="image_missing_alt",
                    severity="error",
                    message="Una imagen referenciada no tiene texto alternativo.",
                    impact_points=ALT_TEXT_WEIGHT,
                    hint="Añadir descripción de imagen accesible en el editor",
                    field_ref=f"section.{section.id}.image.alt",
                    section_id=section.id,
                )
            )

        # imágenes con URL directa sin alt en línea → mismo tratamiento
        image_url = props.get("image_url")
        if (
            isinstance(image_url, str)
            and image_url.strip()
            and not has_inline_alt
            and str(section.id) not in flagged_sections
        ):
            flagged_sections.add(str(section.id))
            findings.append(
                schemas.SeoFinding(
                    code="image_url_missing_alt",
                    severity="error",
                    message="Una sección con image_url no tiene alt configurado.",
                    impact_points=ALT_TEXT_WEIGHT,
                    hint="Añadir descripción alternativa en la sección afectada",
                    field_ref=f"section.{section.id}.image_url",
                    section_id=section.id,
                )
            )
    return findings


def _check_og_image(page: models.CmsPage) -> Optional[schemas.SeoFinding]:
    seo = page.seo_json if isinstance(page.seo_json, dict) else {}
    og = seo.get("meta_image")
    if not og or not str(og).strip():
        if page.status == "published":
            return schemas.SeoFinding(
                code="og_image_missing",
                severity="warning",
                message="La página publicada no tiene imagen Open Graph.",
                impact_points=OG_IMAGE_WEIGHT,
                hint="Añadir una URL de imagen para Open Graph en la configuración",
                field_ref="seo_json.meta_image",
            )
    return None


def _evaluate_page(
    page: models.CmsPage,
    sections: List[models.CmsSection],
    media_alt_lookup: Dict[str, Optional[str]],
) -> schemas.PageSeoAudit:
    findings: List[schemas.SeoFinding] = []
    findings.extend(_check_content_health(page, sections))
    findings.extend(_check_alt_text(sections, media_alt_lookup))
    for single in (
        _check_meta_description(page),
        _check_title_length(page),
        _check_indexability(page),
        _check_og_image(page),
    ):
        if single is not None:
            findings.append(single)
    score = max(0, 100 - sum(f.impact_points for f in findings))
    return schemas.PageSeoAudit(
        page_id=page.id,
        slug=page.slug,
        title=page.title,
        status=page.status or "draft",
        score=score,
        findings=findings,
    )


def _aggregate(audits: List[schemas.PageSeoAudit]) -> schemas.SiteSeoStats:
    if not audits:
        return schemas.SiteSeoStats(
            average_score=0,
            total_pages=0,
            pages_with_errors=0,
            critical_issues=0,
            by_severity={"error": 0, "warning": 0, "info": 0},
        )
    average = round(sum(a.score for a in audits) / len(audits))
    by_sev: Dict[str, int] = defaultdict(int)
    pages_with_errors = 0
    critical = 0
    for audit in audits:
        page_has_error = False
        for finding in audit.findings:
            severity = finding.severity or "info"
            by_sev[severity] += 1
            if severity == "error":
                page_has_error = True
                critical += 1
        if page_has_error:
            pages_with_errors += 1
    return schemas.SiteSeoStats(
        average_score=average,
        total_pages=len(audits),
        pages_with_errors=pages_with_errors,
        critical_issues=critical,
        by_severity=dict(by_sev),
    )


def group_sections_by_page(
    sections: Iterable[models.CmsSection],
) -> Dict[_uuid.UUID, List[models.CmsSection]]:
    """Agrupa secciones por page_id preservando sort_order del ORM."""
    grouped: Dict[_uuid.UUID, List[models.CmsSection]] = defaultdict(list)
    for section in sections:
        grouped[section.page_id].append(section)
    return grouped


def build_media_alt_lookup(
    db: Session, media_ids: Iterable[str]
) -> Dict[str, Optional[str]]:
    """Devuelve un dict {media_id: alt_text_or_None} para los IDs provistos."""
    valid_ids = {str(mid) for mid in media_ids if _uuid_or_none(mid)}
    if not valid_ids:
        return {}
    rows = (
        db.query(models.CmsMediaItem.id, models.CmsMediaItem.alt_text)
        .filter(models.CmsMediaItem.id.in_(valid_ids))
        .all()
    )
    return {str(rid): alt for rid, alt in rows}


def collect_section_media_ids(sections: Iterable[models.CmsSection]) -> set:
    """Extrae todos los media UUIDs referenciados por las secciones."""
    bucket: set = set()
    for section in sections:
        for mid in _scan_section_media_refs(section)[0]:
            bucket.add(mid)
    return bucket


def audit_pages(
    pages: Iterable[models.CmsPage],
    sections_by_page: Dict[_uuid.UUID, List[models.CmsSection]],
    media_alt_lookup: Dict[str, Optional[str]],
) -> Tuple[List[schemas.PageSeoAudit], schemas.SiteSeoStats]:
    """Evalúa cada página con sus secciones y devuelve los hallazgos agregados.

    Función pura — no consulta la DB. Los datos deben venir ya materializados
    de antemano por el caller (para ``N+1`` se cargan en batch con
    ``group_sections_by_page`` + ``build_media_alt_lookup``).

    Retorna una tupla ``(audits, aggregate)``. El orden de ``audits``
    refleja el orden de ``pages`` recibido.
    """
    audited: List[schemas.PageSeoAudit] = []
    for page in pages:
        sections = sections_by_page.get(page.id, [])
        audited.append(_evaluate_page(page, sections, media_alt_lookup))
    return audited, _aggregate(audited)


# Module-level ``__all__`` declares the public exports of this merged
# helper module only — scope helpers (underscore-prefixed) are
# intentional internal APIs and live in the implicit private namespace;
# callers (dashboard.py, cms.py, cms_v2.py, ``__init__.py``) reach them
# via explicit imports. SEO audit functions are the public surface for
# faro CMS integration; they are also re-exported from
# ``backend.api._cms_helpers`` (the ``__init__.py`` of the package) so
# internal callers can import them from the public path.
__all__ = (
    "audit_pages",
    "build_media_alt_lookup",
    "collect_section_media_ids",
    "group_sections_by_page",
)
