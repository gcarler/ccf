"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import datetime as dt
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend import models
from backend.crud.cms._shared import _now_utc
from backend.crud.cms.pages import transition_cms_page_status


def find_pages_due_for_publish(
    db: Session,
    *,
    now: dt.datetime | None = None,
    with_for_update: bool = True,
) -> list[models.CmsPage]:
    """Páginas con ``status='scheduled'`` cuyo ``publish_at`` ya pasó.

    Idempotente: una vez que el scheduler aplica ``transition(...,
    action='publish')``, el ``status`` cambia a ``published`` y el row
    ya no aparece aquí. Garantiza que un cron overlap no publique dos
    veces.

    Hardening (2026-07-06): ``with_for_update=True`` (default) emite
    ``SELECT ... FOR UPDATE SKIP LOCKED`` en Postgres para que múltiples
    crons corriendo en paralelo no se pisen filas. En SQLite (tests)
    se ignora silenciosamente — el status-guard sigue protegiendo.
    """
    cutoff = now or _now_utc()
    q = db.query(models.CmsPage).filter(
        models.CmsPage.status == "scheduled",
        models.CmsPage.publish_at.isnot(None),
        models.CmsPage.publish_at <= cutoff,
    )
    bind = db.get_bind()
    if with_for_update and bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q.all()



def find_pages_due_for_archive(
    db: Session,
    *,
    now: dt.datetime | None = None,
    with_for_update: bool = True,
) -> list[models.CmsPage]:
    """Páginas con ``status='published'`` cuyo ``expires_at`` ya pasó.

    Sólo se auto-archiván páginas ``published``. Borradores no se ven
    afectados aunque tengan ``expires_at`` heredado. Mismo hardening
    ``FOR UPDATE SKIP LOCKED`` que ``find_pages_due_for_publish``.
    """
    cutoff = now or _now_utc()
    q = db.query(models.CmsPage).filter(
        models.CmsPage.status == "published",
        models.CmsPage.expires_at.isnot(None),
        models.CmsPage.expires_at <= cutoff,
    )
    bind = db.get_bind()
    if with_for_update and bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q.all()



def find_posts_due_for_archive(
    db: Session,
    *,
    now: dt.datetime | None = None,
    with_for_update: bool = True,
) -> list[models.CmsPost]:
    """Posts ``published`` cuyo ``expires_at`` ya pasó."""
    cutoff = now or _now_utc()
    q = db.query(models.CmsPost).filter(
        models.CmsPost.status == "published",
        models.CmsPost.expires_at.isnot(None),
        models.CmsPost.expires_at <= cutoff,
    )
    bind = db.get_bind()
    if with_for_update and bind.dialect.name == "postgresql":
        q = q.with_for_update(skip_locked=True)
    return q.all()



def capture_daily_seo_snapshots(db: Session, *, today: dt.date | None = None, dry_run: bool = False) -> dict:
    """Capture one SEO score snapshot per active faro site for ``today``.

    Idempotente: usa ``UNIQUE(site_id, captured_date)`` para garantizar
    que dos pasadas del mismo día no produzcan duplicados (un retry del
    cron = mismo row, no dos rows). Funciona sin scope de sede porque
    las CmsSite son globales del faro (Axioma 3: contenido editorial
    compartido cross-sede por diseño para preservar coherencia visual).

    Retorna un dict ``{snapshots_count, skipped_count, sites_captured}``
    con conteos para heartbeat.
    """  # Gate 6 anti-drift: SEO audit helpers viven ahora en
    # ``backend.api._cms_helpers._shared`` (post-merge de ``seo_audit.py``)
    # y se re-exportan vía el __init__ del paquete para que callers
    # consuman la API pública (alineado con cms_v2.py).
    from backend.api._cms_helpers import (
        audit_pages,
        build_media_alt_lookup,
        collect_section_media_ids,
        group_sections_by_page,
    )

    sites = db.query(models.CmsSite).filter(models.CmsSite.is_active.is_(True)).all()
    counts = {"snapshots_count": 0, "skipped_count": 0, "sites_captured": 0}
    target_date = today or dt.date.today()

    # Idempotency via UNIQUE(site_id, captured_date). Si dos crons
    # corren en paralelo, ambos pasan el SELECT, ambos intentan
    # INSERT, uno gana y el otro recibe IntegrityError. La
    # idempotencia del cron es best-effort a nivel worker — un
    # retry explícito vía ``with_for_update(skip_locked=True)``
    # sería más estricto, pero el cron corre serial en una sola
    # máquina así que la condición de carrera es exceedingly rare.
    for site in sites:
        existing = (
            db.query(models.CmsSeoSnapshot)
            .filter(
                models.CmsSeoSnapshot.site_id == site.id,
                models.CmsSeoSnapshot.captured_date == target_date,
            )
            .first()
        )
        if existing is not None:
            counts["skipped_count"] += 1
            continue

        # Carga eager de páginas + secciones (no N+1).
        pages = db.query(models.CmsPage).filter(models.CmsPage.site_id == site.id).all()
        sections = (
            db.query(models.CmsSection)
            .join(models.CmsPage, models.CmsSection.page_id == models.CmsPage.id)
            .filter(models.CmsPage.site_id == site.id)
            .filter(models.CmsSection.deleted_at.is_(None))
            .all()
        )
        sections_by_page = group_sections_by_page(sections)
        media_ids = collect_section_media_ids(sections)
        media_alt_lookup = build_media_alt_lookup(db, media_ids)

        _audits, aggregate = audit_pages(pages, sections_by_page, media_alt_lookup)

        if dry_run:
            counts["sites_captured"] += 1
            continue

        snapshot = models.CmsSeoSnapshot(
            site_id=site.id,
            sede_id=site.sede_id,
            captured_date=target_date,
            captured_at=dt.datetime.now(dt.timezone.utc),
            average_score=int(aggregate.average_score or 0),
            total_pages=int(aggregate.total_pages or 0),
            pages_with_errors=int(aggregate.pages_with_errors or 0),
            critical_issues=int(aggregate.critical_issues or 0),
            by_severity_json=dict(aggregate.by_severity or {}),
        )
        db.add(snapshot)
        try:
            # El flush temprano fuerza el INSERT y el UNIQUE constraint;
            # sin él, el error sale en el commit y la transacción queda
            # envenenada (cualquier query subsiguiente fallaría). Si
            # dos crons corren en paralelo y los dos pasan el SELECT,
            # uno gana y el otro entra al except.
            #
            # Usamos un SAVEPOINT (begin_nested) para que el rollback
            # sólo afecte a este INSERT y no a iteraciones previas
            # del mismo loop (cuyo db.add ya está pendiente en la tx).
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            # Carrera con otro cron: el UNIQUE(site_id, captured_date)
            # ya está satisfecho. Contamos como "skipped" y seguimos
            # con el siguiente site.
            counts["skipped_count"] += 1
            counts["sites_visited"] += 1
            continue
        counts["snapshots_count"] += 1
        counts["sites_captured"] += 1

    return counts



def list_seo_snapshots(
    db: Session,
    *,
    site_id: uuid.UUID,
    limit: int = 90,
    offset: int = 0,
):
    """F-07 (errorescms.md): lista los snapshots SEO historicos de un site,
    ordenados por ``captured_date DESC`` (más reciente primero).

    Scope Axioma 3: el caller (endpoint API) debe pasar el ``site_id``
    previamente scopped via ``_get_scoped_site_or_404`` para garantizar
    que el usuario solo acceda a snapshots de sites de su sede (cuando
    aplique). Este helper no re-valida sede — lo hace el endpoint-API.

    Retorna una tupla ``(rows, total)`` para que el endpoint pueda
    construir una respuesta paginada.
    """
    q = db.query(models.CmsSeoSnapshot).filter(models.CmsSeoSnapshot.site_id == site_id)
    total = q.count()
    rows = q.order_by(models.CmsSeoSnapshot.captured_date.desc()).offset(offset).limit(limit).all()
    return rows, total



def get_seo_trend(
    db: Session,
    *,
    site_id: uuid.UUID | None = None,
    sede_id: uuid.UUID | str | None = None,
    days: int = 30,
) -> dict:
    """Devuelve la serie de SEO scores de los últimos ``days`` días.

    Scope Axioma 3: si ``sede_id`` está presente, solo se agregan
    snapshots cuyo ``sede_id`` coincida (los snapshots copian el
    ``sede_id`` del site al momento de captura, así que esto es
    eficiente). Promedio simple por día across sites.
    """
    cutoff = dt.date.today() - dt.timedelta(days=max(1, days) - 1)
    query = db.query(models.CmsSeoSnapshot).filter(models.CmsSeoSnapshot.captured_date >= cutoff)
    if site_id is not None:
        query = query.filter(models.CmsSeoSnapshot.site_id == site_id)
    if sede_id is not None:
        query = query.filter(models.CmsSeoSnapshot.sede_id == sede_id)

    rows = query.order_by(models.CmsSeoSnapshot.captured_date.asc()).all()
    by_date: dict[str, list[int]] = {}
    for row in rows:
        by_date.setdefault(row.captured_date.isoformat(), []).append(int(row.average_score or 0))

    series: list[dict] = []
    for key in sorted(by_date.keys()):
        scores = by_date[key]
        avg = round(sum(scores) / len(scores)) if scores else 0
        sample = next((r for r in rows if r.captured_date.isoformat() == key), None)
        series.append(
            {
                "captured_date": key,
                "average_score": avg,
                "total_pages": int(sample.total_pages or 0) if sample else 0,
                "pages_with_errors": int(sample.pages_with_errors or 0) if sample else 0,
                "critical_issues": int(sample.critical_issues or 0) if sample else 0,
            }
        )

    return {"series": series, "days": days}



def _archive_post_with_audit(db: Session, post: models.CmsPost, *, dry_run: bool) -> bool:
    """Archiva un post y deja huella en ``CmsPublishLog``.

    ``entity_type='post'`` distingue de páginas en el log unificado.
    ``actor_persona_id=None`` es la convención para automatizaciones
    del sistema (vs editor humano).
    """
    if dry_run:
        return True
    previous_status = post.status
    post.status = "archived"
    db.add(
        models.CmsPublishLog(
            site_id=post.site_id,
            page_id=None,
            entity_type="post",
            entity_id=str(post.id),
            action="archive",
            from_status=previous_status,
            to_status="archived",
            actor_persona_id=None,
            metadata_json={"source": "scheduler", "reason": "expires_at"},
        )
    )
    db.commit()
    db.refresh(post)
    return True



def process_due_content(db: Session, *, dry_run: bool = False) -> dict[str, int]:
    """Materializa transiciones programadas.

    Idempotente bajo el contrato:
      - ``publish_due_pages`` se procesa 1 vez; al transicionar, el row
        ya no calza para el siguiente ``find_*`` (status cambió a
        ``published``).
      - ``archive_due_pages`` idem.
      - Una corrida manual doble o un cron overlap no aplica el mismo
        cambio dos veces.

    Returns counts (debug + heartbeat metrics):
      - ``pages_published``
      - ``pages_archived``
      - ``posts_archived``
    """
    now = _now_utc()
    pages_published = 0
    pages_archived = 0
    posts_archived = 0

    # ── 1. Pages → publish ────────────────────────────────────────────
    for page in find_pages_due_for_publish(db, now=now):
        if dry_run:
            pages_published += 1
            continue
        result = transition_cms_page_status(
            db,
            page,
            action="publish",
            user_id=None,
            notes="Auto-published by scheduler",
        )
        if result is not None:
            pages_published += 1

    # ── 2. Pages → archive ────────────────────────────────────────────
    for page in find_pages_due_for_archive(db, now=now):
        if dry_run:
            pages_archived += 1
            continue
        result = transition_cms_page_status(
            db,
            page,
            action="archive",
            user_id=None,
            notes="Auto-archived by scheduler (expires_at reached)",
        )
        if result is not None:
            pages_archived += 1

    # ── 3. Posts → archive ────────────────────────────────────────────
    for post in find_posts_due_for_archive(db, now=now):
        if dry_run:
            posts_archived += 1
            continue
        if _archive_post_with_audit(db, post, dry_run=False):
            posts_archived += 1

    return {
        "pages_published": pages_published,
        "pages_archived": pages_archived,
        "posts_archived": posts_archived,
    }



