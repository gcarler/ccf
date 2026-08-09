"""CMS: Page content, media, CMS v2 (sites, themes, menus, pages, sections, versions).

Axioma 3 — Multi-Tenant (Fase 5 — CRUD Layer defense-in-depth): las
funciones mutantes de User-Generated Content (Testimonial, Announcement,
CmsMediaItem) y PastoralProfile re-validan scope Multi-Tenant antes de
persistir cambios, propagando actor_user_id desde el caller API. Esto
cierra el TOCTOU gap donde un caller no-API (worker async, script de
seeding, llamada directa al CRUD) podría crear/mutar registros sin
pasar por el helper API `_get_scoped_*` correspondiente.
"""

import logging
import math
import uuid

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



def list_cms_ab_tests(
    db: Session,
    site_id: uuid.UUID,
    page_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[models.CmsAbTest]:
    query = db.query(models.CmsAbTest).filter(
        models.CmsAbTest.site_id == site_id,
        models.CmsAbTest.deleted_at.is_(None),
    )
    if page_id:
        query = query.filter(models.CmsAbTest.page_id == page_id)
    if status:
        query = query.filter(models.CmsAbTest.status == status)
    return query.order_by(models.CmsAbTest.created_at.desc()).all()



def get_cms_ab_test(db: Session, site_id: uuid.UUID, test_id: uuid.UUID) -> models.CmsAbTest | None:
    return (
        db.query(models.CmsAbTest)
        .filter(
            models.CmsAbTest.site_id == site_id,
            models.CmsAbTest.id == test_id,
            models.CmsAbTest.deleted_at.is_(None),
        )
        .first()
    )



def get_cms_ab_test_by_id(db: Session, test_id: uuid.UUID) -> models.CmsAbTest | None:
    return (
        db.query(models.CmsAbTest)
        .filter(
            models.CmsAbTest.id == test_id,
            models.CmsAbTest.deleted_at.is_(None),
        )
        .first()
    )



def create_cms_ab_test(db: Session, site_id: uuid.UUID, payload: schemas.CmsAbTestCreate) -> models.CmsAbTest:
    row = models.CmsAbTest(
        site_id=site_id,
        page_id=payload.page_id,
        name=payload.name,
        section_a_id=payload.section_a_id,
        section_b_id=payload.section_b_id,
        traffic_split=payload.traffic_split,
        status="active",
        started_at=_utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def update_cms_ab_test(db: Session, row: models.CmsAbTest, payload: schemas.CmsAbTestUpdate) -> models.CmsAbTest:
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] == "completed" and row.status != "completed":
        row.ended_at = _utcnow()
    for field, val in data.items():
        setattr(row, field, val)
    db.commit()
    db.refresh(row)
    return row



def delete_cms_ab_test(db: Session, row: models.CmsAbTest) -> bool:
    row.deleted_at = _utcnow()
    row.status = "deleted"
    db.commit()
    return True



def record_cms_ab_test_event(
    db: Session, test_id: uuid.UUID, payload: schemas.CmsAbTestEventCreate
) -> models.CmsAbTestEvent:
    event = models.CmsAbTestEvent(
        test_id=test_id,
        variant=payload.variant,
        event_type=payload.event_type,
        visitor_id=payload.visitor_id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event



def get_cms_ab_test_results(db: Session, test_id: uuid.UUID) -> schemas.CmsAbTestResults:
    events = db.query(models.CmsAbTestEvent).filter(models.CmsAbTestEvent.test_id == test_id).all()
    views_a = sum(1 for e in events if e.variant == "a" and e.event_type == "view")
    views_b = sum(1 for e in events if e.variant == "b" and e.event_type == "view")
    clicks_a = sum(1 for e in events if e.variant == "a" and e.event_type == "click")
    clicks_b = sum(1 for e in events if e.variant == "b" and e.event_type == "click")
    conversions_a = sum(1 for e in events if e.variant == "a" and e.event_type == "conversion")
    conversions_b = sum(1 for e in events if e.variant == "b" and e.event_type == "conversion")

    # Primary conversion count: use conversions if present, else clicks
    conv_a = conversions_a if conversions_a > 0 else clicks_a
    conv_b = conversions_b if conversions_b > 0 else clicks_b

    cr_a = conv_a / views_a if views_a > 0 else 0.0
    cr_b = conv_b / views_b if views_b > 0 else 0.0

    # Calculate 2-proportion Z-test statistical significance
    confidence = 0.0
    if views_a > 0 and views_b > 0:
        p_pool = (conv_a + conv_b) / (views_a + views_b)
        if 0 < p_pool < 1:
            se = math.sqrt(p_pool * (1 - p_pool) * (1 / views_a + 1 / views_b))
            if se > 0:
                z = abs(cr_a - cr_b) / se
                confidence = math.erf(z / math.sqrt(2))

    confidence = round(max(0.0, min(1.0, confidence)), 4)
    is_significant = confidence >= 0.95

    recommended_winner = None
    if is_significant:
        if cr_a > cr_b:
            recommended_winner = "a"
        elif cr_b > cr_a:
            recommended_winner = "b"

    return schemas.CmsAbTestResults(
        test_id=test_id,
        views_a=views_a,
        views_b=views_b,
        clicks_a=clicks_a,
        clicks_b=clicks_b,
        conversions_a=conversions_a,
        conversions_b=conversions_b,
        conversion_rate_a=round(cr_a, 4),
        conversion_rate_b=round(cr_b, 4),
        statistical_significance=confidence,
        is_significant=is_significant,
        recommended_winner=recommended_winner,
    )



def apply_cms_ab_test_winner(
    db: Session,
    site_id: uuid.UUID,
    test_id: uuid.UUID,
    payload: schemas.CmsAbTestApplyWinner | None = None,
) -> models.CmsAbTest:
    test = get_cms_ab_test(db, site_id, test_id)
    if not test:
        raise ValueError("A/B test not found")

    winner_variant = payload.winner_variant if payload else None
    winner_section_id = payload.winner_section_id if payload else None

    if not winner_section_id:
        if winner_variant == "a":
            winner_section_id = test.section_a_id
        elif winner_variant == "b":
            winner_section_id = test.section_b_id
        else:
            # Determine based on current results
            results = get_cms_ab_test_results(db, test_id)
            if results.recommended_winner == "b":
                winner_section_id = test.section_b_id
            else:
                winner_section_id = test.section_a_id

    winning_section = db.query(models.CmsSection).filter(models.CmsSection.id == winner_section_id).first()
    if winning_section:
        winning_section.is_visible = True
        # If variant B won and is different from section A, make section A hidden
        if winner_section_id == test.section_b_id and test.section_a_id != test.section_b_id:
            sec_a = db.query(models.CmsSection).filter(models.CmsSection.id == test.section_a_id).first()
            if sec_a:
                winning_section.sort_order = sec_a.sort_order
                sec_a.is_visible = False
        elif winner_section_id == test.section_a_id and test.section_a_id != test.section_b_id:
            sec_b = db.query(models.CmsSection).filter(models.CmsSection.id == test.section_b_id).first()
            if sec_b:
                sec_b.is_visible = False

    test.status = "completed"
    test.winner_section_id = winner_section_id
    test.ended_at = _utcnow()

    db.commit()
    db.refresh(test)
    return test

