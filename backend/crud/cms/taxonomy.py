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
import uuid

from sqlalchemy.orm import Session

from backend import models, schemas

_logger = logging.getLogger(__name__)


# ``resolve_persona_id_for_user`` (imported as ``resolve_persona_uuid_for_user``
# above) comes from ``backend.crud.crm`` which re-exports the canonical
# implementation in ``backend.crud.crm_.shared``. We call that directly
# throughout this module — the previous local wrapper added only
# indirection (M-10 in ``errorescms.md``).



from backend.crud.cms._shared import _actor_sede_or_none_cms, _crud_scope_re_check_cms_site_content


def _assert_parent_category_same_site(db: Session, site_id: uuid.UUID, parent_id: uuid.UUID | None) -> None:
    """Defensa Axioma 3 (multi-tenant) para ``CmsCategory.parent_id``.

    Si ``parent_id`` no es ``None`` valida que el parent exista Y pertenezca
    al mismo ``site_id`` que la categoría bajo mutación.  Un parent
    cross-site sería una fuga de tenant (categorias del site A colgando de
    categorías del site B).  Se ejecuta en la capa CRUD para cubrir también
    callers no-API (workers async, seeding, tests directos).

    Lanza ``ValueError`` cuando el parent no existe o es de otro site; el
    caller API traduce esto a ``HTTP 422``.
    """
    if parent_id is None:
        return
    parent = db.query(models.CmsCategory).filter(models.CmsCategory.id == parent_id).first()
    if parent is None or parent.site_id != site_id:
        raise ValueError("parent_id must belong to the same site")



def list_cms_categories(db: Session, site_id: uuid.UUID):
    return (
        db.query(models.CmsCategory)
        .filter(models.CmsCategory.site_id == site_id)
        .order_by(models.CmsCategory.name.asc())
        .all()
    )



def get_cms_category(db: Session, site_id: uuid.UUID, slug: str):
    return (
        db.query(models.CmsCategory)
        .filter(models.CmsCategory.site_id == site_id, models.CmsCategory.slug == slug)
        .first()
    )



def create_cms_category(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsCategoryCreate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=site_id,
        )
    _assert_parent_category_same_site(db, site_id, payload.parent_id)
    row = models.CmsCategory(
        site_id=site_id,
        slug=payload.slug.strip().lower(),
        name=payload.name.strip(),
        description=payload.description,
        parent_id=payload.parent_id,
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def update_cms_category(
    db: Session,
    row: models.CmsCategory,
    payload: schemas.CmsCategoryUpdate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=row.site_id,
        )
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        row.slug = str(data["slug"]).strip().lower()
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "description" in data:
        row.description = data["description"]
    if "parent_id" in data:
        _assert_parent_category_same_site(db, row.site_id, data["parent_id"])
        row.parent_id = data["parent_id"]
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(row)
    return row



def delete_cms_category(
    db: Session,
    row: models.CmsCategory,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> bool:
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=row.site_id,
        )
    row.is_active = False
    db.commit()
    return True



def list_cms_tags(db: Session, site_id: uuid.UUID):
    return db.query(models.CmsTag).filter(models.CmsTag.site_id == site_id).order_by(models.CmsTag.name.asc()).all()



def get_cms_tag(db: Session, site_id: uuid.UUID, slug: str):
    return db.query(models.CmsTag).filter(models.CmsTag.site_id == site_id, models.CmsTag.slug == slug).first()



def create_cms_tag(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsTagCreate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=site_id,
        )
    row = models.CmsTag(
        site_id=site_id,
        slug=payload.slug.strip().lower(),
        name=payload.name.strip(),
        is_active=payload.is_active,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row



def update_cms_tag(
    db: Session,
    row: models.CmsTag,
    payload: schemas.CmsTagUpdate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
):
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=row.site_id,
        )
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        row.slug = str(data["slug"]).strip().lower()
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "is_active" in data and data["is_active"] is not None:
        row.is_active = bool(data["is_active"])
    db.commit()
    db.refresh(row)
    return row



def delete_cms_tag(
    db: Session,
    row: models.CmsTag,
    *,
    actor_user_id: str | uuid.UUID | None = None,
) -> bool:
    if actor_user_id is not None:
        actor_sede = _actor_sede_or_none_cms(db, actor_user_id)
        _crud_scope_re_check_cms_site_content(
            db,
            actor_user_id,
            actor_sede=actor_sede,
            site_id=row.site_id,
        )
    row.is_active = False
    db.commit()
    return True



def get_or_create_canonical_category(
    db: Session, site_id: uuid.UUID, slug: str, name: str, description: str | None = None
) -> models.CmsCategory:
    """Obtiene o crea una categoría canónica (testimonials/announcements) para un site."""
    cat = (
        db.query(models.CmsCategory)
        .filter(models.CmsCategory.site_id == site_id, models.CmsCategory.slug == slug)
        .first()
    )
    if cat:
        return cat
    cat = models.CmsCategory(
        site_id=site_id,
        slug=slug,
        name=name,
        description=description or f"Categoría canónica para {name}",
        is_active=True,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat



def _assert_canonical_category_unchanged(
    existing_category_ids: list[uuid.UUID],
    new_category_ids: list[uuid.UUID] | None,
    canonical_category_id: uuid.UUID,
) -> None:
    """Valida que la categoría canónica no se cambie en updates."""
    if new_category_ids is None:
        return
    existing_set = set(existing_category_ids)
    new_set = set(new_category_ids)
    if canonical_category_id not in new_set:
        raise ValueError("Cannot remove canonical category from post")
    if existing_set != new_set:
        raise ValueError("Cannot change canonical category assignment")



