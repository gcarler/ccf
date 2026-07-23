"""Synchronize the public pastors page with pastoral Persona profiles.

This bridges the CMS v2 page section ``pastors`` and the CRM ``Persona``
records marked as pastoral leaders. The goal is a single source of truth:
edit a pastor's profile (photo, bio, role) in the pastoral team admin, and
re-publish the ``pastors`` page to reflect the changes on the public site.
"""

from __future__ import annotations

import re
import unicodedata
import uuid as _uuid

from sqlalchemy.orm import Session

from backend import models

SITE_KEY = "ccf"
PAGE_SLUG = "pastors"
SECTION_KEY = "pastors"


def _slugify(value: str) -> str:
    """Normalize a full name into a URL-safe slug (NFKD handles diacritics).

    Mirrors the canonical rule used by ``scripts/fix_pastor_photos.py`` and
    ``tests/test_pastor_photo_regression.py``: NFKD decomposition drops
    the combining mark for accented characters (``í`` → ``i`` + U+0301 → ``i``),
    keeping the alphabetic base character so ``Nehemías`` slugifies to
    ``nehemias`` (not ``nehemas`` like a naive ``[^a-z0-9]`` strip would do).
    """
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _split_name(full_name: str) -> tuple[str, str]:
    """Best-effort split of a full name into first/last names for Persona."""
    parts = full_name.strip().split()
    if not parts:
        return ("Sin", "nombre")
    if len(parts) == 1:
        return (parts[0], "")
    # Keep first name as-is, join the rest as last name.
    return (parts[0], " ".join(parts[1:]))


def _find_persona_by_name(db: Session, full_name: str) -> models.Persona | None:
    """Look for an existing persona whose full name closely matches the query.

    Three-tier matching (hardened against first-name token collisions that
    bit the original substring-lookup implementation, e.g. ``"Maria Martinez"``
    incorrectly matching a persona named ``"Ana Maria Martinez"``):

    1. **Exact slug match** — ``_slugify(query) == _slugify(persona)``.
       Strongest signal, used for the canonical case (incl. accent
       normalization via NFKD so ``"Camilo Pájaro"`` query matches
       ``"Camilo Pajaro"`` stored in DB after a lossy import).
    2. **First-name anchor + token overlap** — the first slug-token of the
       query must EQUAL the first slug-token of the persona. Prevents the
       ``"Maria Martinez"`` ↔ ``"Ana Maria Martinez"`` collision. Score
       must be ≥ 2 (or full coverage for single-token queries).
    3. **Pure token overlap fallback** — for cultures where the public
       display name omits the first given name (e.g. CMS says
       ``"Camilo Pájaro"`` but CRM has ``"José Camilo Pájaro"``). Tier 2
       would reject this because the first tokens differ; Tier 3 catches
       it via high token overlap. Same ≥ 2 / full-coverage threshold as
       Tier 2 to avoid single-token false positives.
    """
    query_slug = _slugify(full_name)
    if not query_slug:
        return None
    query_tokens = query_slug.split("-")

    candidates = (
        db.query(models.Persona)
        .filter(models.Persona.estado_vital != "FALLECIDO")
        .all()
    )

    # Tier 1: Exact slug match.
    for p in candidates:
        if _slugify(p.nombre_completo or "") == query_slug:
            return p

    # Tier 2: First-name anchor + high token overlap.
    tier2: models.Persona | None = None
    tier2_score = 0
    for p in candidates:
        p_slug = _slugify(p.nombre_completo or "")
        if not p_slug:
            continue
        p_tokens = p_slug.split("-")
        # First-name anchor: the first token of the query must match the
        # first token of the persona. This blocks "Maria Martinez" from
        # matching a persona named "Ana Maria Martinez" (ana != maria).
        if query_tokens[0] != p_tokens[0]:
            continue
        p_tokens_set = set(p_tokens)
        score = sum(1 for t in query_tokens if t in p_tokens_set)
        # Accept if ≥ 2 tokens match OR query is fully covered (single-token
        # case). Threshold mirrors the original implementation's contract.
        if score >= 2 or score == len(query_tokens):
            if score > tier2_score:
                tier2_score = score
                tier2 = p
    if tier2 is not None:
        return tier2

    # Tier 3 (fallback): pure token overlap, same threshold as Tier 2.
    # Catches cultures where the CMS display name uses a middle name and
    # so the first-token anchor does not align with the CRM first_name.
    best: models.Persona | None = None
    best_score = 0
    for p in candidates:
        p_slug = _slugify(p.nombre_completo or "")
        if not p_slug:
            continue
        p_tokens_set = set(p_slug.split("-"))
        score = sum(1 for t in query_tokens if t in p_tokens_set)
        if score > best_score and (score >= 2 or score == len(query_tokens)):
            best_score = score
            best = p
    return best


def get_cms_pastors_section(db: Session) -> models.CmsSection | None:
    """Return the pastors section for the canonical public pastors page."""
    site = db.query(models.CmsSite).filter(models.CmsSite.site_key == SITE_KEY).first()
    if not site:
        return None
    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == PAGE_SLUG)
        .first()
    )
    if not page:
        return None
    return (
        db.query(models.CmsSection)
        .filter(
            models.CmsSection.page_id == page.id,
            models.CmsSection.section_key == SECTION_KEY,
        )
        .first()
    )


def sync_pastoral_profiles_from_cms_section(db: Session) -> dict[str, int]:
    """Create/update Persona records from the CMS pastors section.

    Existing personas are matched by name; if no match is found a new Persona
    is created. All matched/created records are marked as pastoral leaders.

    Returns a summary dict with ``matched``, ``created``, ``total``.
    """
    section = get_cms_pastors_section(db)
    if section is None:
        raise RuntimeError(f"CMS section {SECTION_KEY!r} for page {PAGE_SLUG!r} not found")

    pastors = (section.props_json or {}).get("pastors") or []
    if not isinstance(pastors, list):
        raise RuntimeError("Invalid pastors section: expected a list")

    matched = 0
    created = 0

    for pastor in pastors:
        name = str(pastor.get("name") or "").strip()
        if not name:
            continue

        persona = _find_persona_by_name(db, name)
        if persona is None:
            first, last = _split_name(name)
            persona = models.Persona(
                first_name=first,
                last_name=last,
                church_role=pastor.get("role") or "Pastor",
                estado_vital="ACTIVO",
            )
            db.add(persona)
            created += 1
        else:
            matched += 1

        persona.is_pastoral_leader = True
        persona.is_main_pastor = bool(pastor.get("isMain"))
        # Normalize the name so the live profile matches the CMS display name.
        first, last = _split_name(name)
        persona.first_name = first
        persona.last_name = last
        persona.photo_url = pastor.get("image") or pastor.get("photo_url") or persona.photo_url
        persona.bio_short = pastor.get("story") or pastor.get("bio_short") or persona.bio_short
        persona.bio_full = pastor.get("bio_full") or persona.bio_full
        role = pastor.get("role")
        if role:
            persona.church_role = role

    db.commit()
    return {"matched": matched, "created": created, "total": len(pastors)}


def build_pastors_section_props(db: Session, *, sede_id: _uuid.UUID | None = None) -> dict[str, list[dict[str, object]]]:
    """Build the ``pastors`` section payload from live pastoral Persona records.

    Only personas with ``is_pastoral_leader == True`` are included, ordered by
    main pastor first and then alphabetically by full name.

    Axioma 3 (C-04): when ``sede_id`` is provided, only pastoral leaders
    belonging to that sede are included. When ``sede_id`` is ``None``
    (orphan site operated by an admin), an empty list is returned — an
    admin reassigning an orphan site should publish an empty team, not a
    cross-sede dump of every pastor in the platform.
    """
    if sede_id is None:
        return {"pastors": []}
    leaders = (
        db.query(models.Persona)
        .filter(
            models.Persona.is_pastoral_leader.is_(True),
            models.Persona.estado_vital != "FALLECIDO",
            models.Persona.sede_id == sede_id,
        )
        .order_by(
            models.Persona.is_main_pastor.desc(),
            models.Persona.nombre_completo.asc(),
        )
        .all()
    )

    pastors: list[dict[str, object]] = []
    for p in leaders:
        name = p.nombre_completo
        slug = _slugify(name)
        pastors.append(
            {
                "slug": slug,
                "name": name,
                "role": p.church_role or ("Pastor Principal" if p.is_main_pastor else "Pastor"),
                "image": p.photo_url or "",
                "isMain": bool(p.is_main_pastor),
                "story": p.bio_short or "",
                "bio_short": p.bio_short or "",
                "bio_full": p.bio_full or "",
                "social_instagram": p.social_instagram or "",
                "social_facebook": p.social_facebook or "",
                "social_twitter": p.social_twitter or "",
            }
        )

    return {"pastors": pastors}


def update_pastors_section_from_profiles(db: Session) -> bool:
    """Overwrite the CMS ``pastors`` section with data from pastoral profiles.

    Axioma 3 — Multi-Tenant (C-04 fix): the pastor list is scoped to the
    sede that owns the site the ``pastors`` section belongs to. Before
    this fix the query pulled ``is_pastoral_leader`` personas across ALL
    sedes, so publishing the ``pastors`` page of site A leaked pastors of
    sede B into site A's public page. Now the site's ``sede_id`` drives
    the filter; sites without sede_id (orphans, admin-only) fall back to
    an empty list rather than a cross-sede dump.

    Returns ``True`` if the section was updated.
    """
    section = get_cms_pastors_section(db)
    if section is None:
        return False
    sede_id = _resolve_section_sede_id(db, section)
    section.props_json = build_pastors_section_props(db, sede_id=sede_id)
    db.commit()
    db.refresh(section)
    return True


def _resolve_section_sede_id(db: Session, section: models.CmsSection) -> _uuid.UUID | None:
    """Resolve the sede_id of the site owning ``section`` (Axioma 3 scope).

    Walks section.page.site.sede_id. Returns ``None`` for orphan sites
    (no sede); callers must treat ``None`` as "no pastors to publish"
    rather than "all pastors" to avoid a cross-sede leak.
    """
    page = (
        db.query(models.CmsPage)
        .filter(models.CmsPage.id == section.page_id)
        .first()
    )
    if page is None:
        return None
    site = (
        db.query(models.CmsSite)
        .filter(models.CmsSite.id == page.site_id)
        .first()
    )
    if site is None:
        return None
    return site.sede_id
