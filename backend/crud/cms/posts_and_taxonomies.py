"""CMS Posts & Taxonomías — CRUD de ``CmsPost``, ``CmsCategory``, ``CmsTag``.

Extraído de ``crud/cms/__init__.py`` (split del monolito, deuda estructural
🔴#1, 2026-08-05). 30 funciones: categorías CRUD, tags CRUD, posts CRUD
+ batch helpers + canonical categories + public posts.
"""

import datetime as dt
import uuid

from sqlalchemy.orm import Session

from backend import models, schemas


# ── Helpers — importados del __init__.py del paquete ──────────────────────

def _actor_sede_or_none_cms(db, actor_user_id):
    """Re-import por extracción — ver doc original en __init__.py."""
    from backend.crud.cms import _actor_sede_or_none_cms as _f

    return _f(db, actor_user_id)


def _crud_scope_re_check_cms_site_content(db, actor_user_id, *, actor_sede, site_id=None):
    """Re-import por extracción — ver doc original en __init__.py."""
    from backend.crud.cms import _crud_scope_re_check_cms_site_content as _f

    return _f(db, actor_user_id, actor_sede=actor_sede, site_id=site_id)


def _resolve_persona_id(*args, **kwargs):
    """Re-import por extracción."""
    from backend.crud.cms import resolve_persona_uuid_for_user as _f

    return _f(*args, **kwargs)


def _now_utc():
    from backend.crud.cms import _now_utc as _f

    return _f()


# ── CMS Posts & Taxonomías ─────────────────────────────────────────────────


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


def _set_post_categories(db: Session, post_id: uuid.UUID, category_ids: list[uuid.UUID]):
    db.query(models.CmsPostCategory).filter(models.CmsPostCategory.post_id == post_id).delete(synchronize_session=False)
    for cid in category_ids:
        db.add(models.CmsPostCategory(post_id=post_id, category_id=cid))


def _set_post_tags(db: Session, post_id: uuid.UUID, tag_ids: list[uuid.UUID]):
    db.query(models.CmsPostTag).filter(models.CmsPostTag.post_id == post_id).delete(synchronize_session=False)
    for tid in tag_ids:
        db.add(models.CmsPostTag(post_id=post_id, tag_id=tid))


def list_cms_posts(
    db: Session,
    site_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    category_id: uuid.UUID | None = None,
    tag_id: uuid.UUID | None = None,
):
    query = db.query(models.CmsPost).filter(models.CmsPost.site_id == site_id)
    if status:
        query = query.filter(models.CmsPost.status == status)
    if category_id:
        query = query.join(models.CmsPostCategory).filter(models.CmsPostCategory.category_id == category_id)
    if tag_id:
        query = query.join(models.CmsPostTag).filter(models.CmsPostTag.tag_id == tag_id)
    total = query.count()
    items = query.order_by(models.CmsPost.updated_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_cms_post(db: Session, site_id: uuid.UUID, slug: str):
    return db.query(models.CmsPost).filter(models.CmsPost.site_id == site_id, models.CmsPost.slug == slug).first()


def get_cms_post_by_id(db: Session, post_id: uuid.UUID):
    return db.query(models.CmsPost).filter(models.CmsPost.id == post_id).first()


def _assert_post_published_before_expires(published_at: dt.datetime | None, expires_at: dt.datetime | None) -> None:
    """F-09: valida coherencia temporal de ``CmsPost``.

    Un post con auto-archivo (``expires_at``) debe publicarse antes de
    expirar; si ``published_at >= expires_at`` el scheduler de
    auto-archivo entraría en un estado contradictorio (expira antes o en
    el mismo instante de publicar).  Solo valida cuando AMBOS son
    no-None — cualquiera de los dos en None desactiva la restricción
    (``published_at=None`` significa no publicado; ``expires_at=None``
    significa sin auto-archivo).

    Compara normalizando a UTC aware para evitar el bug de tz-info loss
    que ya documentamos para SQLite (ver MEMORY §SQLite tz-info loss
    invariant).
    """
    if published_at is None or expires_at is None:
        return
    pub = published_at if published_at.tzinfo is not None else published_at.replace(tzinfo=dt.timezone.utc)
    exp = expires_at if expires_at.tzinfo is not None else expires_at.replace(tzinfo=dt.timezone.utc)
    if pub >= exp:
        raise ValueError("published_at must be earlier than expires_at")


def create_cms_post(
    db: Session,
    site_id: uuid.UUID,
    payload: schemas.CmsPostCreate,
    user_id: uuid.UUID | None,
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
    _assert_post_published_before_expires(payload.published_at, payload.expires_at)
    row = models.CmsPost(
        site_id=site_id,
        slug=payload.slug.strip().lower(),
        title=payload.title.strip(),
        excerpt=payload.excerpt,
        content=payload.content,
        featured_image_url=payload.featured_image_url,
        status=payload.status,
        locale=payload.locale,
        seo_json=payload.seo_json or {},
        published_at=payload.published_at,
        created_by_persona_id=_resolve_persona_id(db, user_id),
        updated_by_persona_id=_resolve_persona_id(db, user_id),
    )
    db.add(row)
    db.flush()
    if payload.category_ids:
        _set_post_categories(db, row.id, payload.category_ids)
    if payload.tag_ids:
        _set_post_tags(db, row.id, payload.tag_ids)
    db.commit()
    db.refresh(row)
    return row


def update_cms_post(
    db: Session,
    row: models.CmsPost,
    payload: schemas.CmsPostUpdate,
    user_id: uuid.UUID | None,
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
    if "title" in data and data["title"] is not None:
        row.title = str(data["title"]).strip()
    if "excerpt" in data:
        row.excerpt = data["excerpt"]
    if "content" in data:
        row.content = data["content"]
    if "featured_image_url" in data:
        row.featured_image_url = data["featured_image_url"]
    if "status" in data and data["status"] is not None:
        row.status = str(data["status"]).strip()
    if "locale" in data and data["locale"] is not None:
        row.locale = str(data["locale"]).strip()
    if "seo_json" in data and data["seo_json"] is not None:
        row.seo_json = data["seo_json"]
    if "published_at" in data:
        row.published_at = data["published_at"]
    if "expires_at" in data:
        row.expires_at = data["expires_at"]
    _assert_post_published_before_expires(row.published_at, row.expires_at)
    if user_id is not None:
        row.updated_by_persona_id = _resolve_persona_id(db, user_id)
    db.flush()
    if "category_ids" in data and data["category_ids"] is not None:
        _set_post_categories(db, row.id, data["category_ids"])
    if "tag_ids" in data and data["tag_ids"] is not None:
        _set_post_tags(db, row.id, data["tag_ids"])
    db.commit()
    db.refresh(row)
    return row


def delete_cms_post(
    db: Session,
    row: models.CmsPost,
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
    row.status = "archived"
    db.commit()
    return True


def get_post_categories(db: Session, post_id: uuid.UUID):
    return (
        db.query(models.CmsCategory)
        .join(models.CmsPostCategory)
        .filter(models.CmsPostCategory.post_id == post_id)
        .all()
    )


def get_post_tags(db: Session, post_id: uuid.UUID):
    return db.query(models.CmsTag).join(models.CmsPostTag).filter(models.CmsPostTag.post_id == post_id).all()


def get_posts_categories_batch(db: Session, post_ids: list[uuid.UUID]) -> dict[str, list]:
    """Batch-fetch categories for multiple posts in one query (N+1 fix).

    Keys are normalized to strings because some DB drivers (notably SQLite)
    return UUIDs as strings, which would cause KeyError when the caller
    looks up by the original uuid.UUID object.
    """
    if not post_ids:
        return {}
    rows = (
        db.query(models.CmsPostCategory.post_id, models.CmsCategory)
        .join(models.CmsCategory, models.CmsCategory.id == models.CmsPostCategory.category_id)
        .filter(models.CmsPostCategory.post_id.in_(post_ids))
        .all()
    )
    result: dict[str, list] = {str(pid): [] for pid in post_ids}
    for post_id, category in rows:
        result.setdefault(str(post_id), []).append(category)
    return result


def get_posts_tags_batch(db: Session, post_ids: list[uuid.UUID]) -> dict[str, list]:
    """Batch-fetch tags for multiple posts in one query (N+1 fix).

    Keys are normalized to strings because some DB drivers (notably SQLite)
    return UUIDs as strings, which would cause KeyError when the caller
    looks up by the original uuid.UUID object.
    """
    if not post_ids:
        return {}
    rows = (
        db.query(models.CmsPostTag.post_id, models.CmsTag)
        .join(models.CmsTag, models.CmsTag.id == models.CmsPostTag.tag_id)
        .filter(models.CmsPostTag.post_id.in_(post_ids))
        .all()
    )
    result: dict[str, list] = {str(pid): [] for pid in post_ids}
    for post_id, tag in rows:
        result.setdefault(str(post_id), []).append(tag)
    return result


def get_public_cms_posts(
    db: Session,
    site_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    category_slug: str | None = None,
    tag_slug: str | None = None,
):
    query = db.query(models.CmsPost).filter(models.CmsPost.site_id == site_id, models.CmsPost.status == "published")
    if category_slug:
        query = (
            query.join(models.CmsPostCategory).join(models.CmsCategory).filter(models.CmsCategory.slug == category_slug)
        )
    if tag_slug:
        query = query.join(models.CmsPostTag).join(models.CmsTag).filter(models.CmsTag.slug == tag_slug)
    total = query.count()
    items = query.order_by(models.CmsPost.published_at.desc().nullslast()).offset(skip).limit(limit).all()
    return items, total


def get_public_cms_post(db: Session, site_id: uuid.UUID, slug: str):
    return (
        db.query(models.CmsPost)
        .filter(
            models.CmsPost.site_id == site_id,
            models.CmsPost.slug == slug,
            models.CmsPost.status == "published",
        )
        .first()
    )


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


def list_cms_posts_by_category(
    db: Session,
    site_id: uuid.UUID,
    category_slug: str,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    include_archived: bool = False,
):
    """Lista posts filtrados por slug de categoría (para categorías canónicas)."""
    query = (
        db.query(models.CmsPost)
        .join(models.CmsPostCategory)
        .join(models.CmsCategory)
        .filter(
            models.CmsPost.site_id == site_id,
            models.CmsCategory.slug == category_slug,
        )
    )
    if status:
        query = query.filter(models.CmsPost.status == status)
    if not include_archived:
        query = query.filter(models.CmsPost.status != "archived")
    total = query.count()
    items = query.order_by(models.CmsPost.updated_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_cms_post_by_slug_and_category(
    db: Session, site_id: uuid.UUID, slug: str, category_slug: str
) -> models.CmsPost | None:
    """Obtiene un post por slug validando que pertenezca a la categoría canónica."""
    return (
        db.query(models.CmsPost)
        .join(models.CmsPostCategory)
        .join(models.CmsCategory)
        .filter(
            models.CmsPost.site_id == site_id,
            models.CmsPost.slug == slug,
            models.CmsCategory.slug == category_slug,
        )
        .first()
    )


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
