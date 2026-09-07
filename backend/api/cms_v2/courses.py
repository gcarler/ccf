"""CMS courses admin endpoints.

Allows CMS editors and administrators to manage public courses displayed on /cursos,
including updating titles, descriptions, cover photos, instructors, modalities,
publication status, and display order.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.api._cms_helpers import _actor_sede_or_none, _is_global_media_admin
from backend.api.cms_v2._shared import CMS_EDITOR_ROLES, _assert_role, _slugify
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_module_access
from backend.models_academy_core import Course, Lesson

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_courses"])


def _generate_course_code(title: str) -> str:
    """Generate a clean, unique course code from title."""
    clean = re.sub(r"[^A-Za-z0-9]", "", title).upper()[:6]
    random_suffix = uuid.uuid4().hex[:4].upper()
    return f"CCF-{clean or 'CUR'}-{random_suffix}"


def _get_scoped_cms_course(db: Session, current_user: models.User, course_id_str: str) -> Course:
    """Resolve a course by UUID with multi-tenant scoping and Axioma 3 validation."""
    try:
        cid = UUID(course_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    query = db.query(Course).filter(Course.id == cid, Course.deleted_at.is_(None))
    if not _is_global_media_admin(current_user):
        user_sede = _actor_sede_or_none(db, current_user)
        if user_sede:
            query = query.filter(or_(Course.sede_id == user_sede, Course.sede_id.is_(None)))

    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


@router.get("/cms/courses", response_model=List[schemas.CmsCourseRead])
def cms_courses_list(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "read")),
):
    """List all courses for CMS builder and public courses management."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    query = db.query(Course).filter(Course.deleted_at.is_(None))

    if not _is_global_media_admin(current_user):
        user_sede = _actor_sede_or_none(db, current_user)
        if user_sede:
            query = query.filter(or_(Course.sede_id == user_sede, Course.sede_id.is_(None)))

    courses = query.order_by(Course.sort_order.asc(), Course.created_at.desc(), Course.id).all()

    lesson_counts = dict(
        db.query(Lesson.course_id, func.count(Lesson.id))
        .filter(Lesson.course_id.in_([c.id for c in courses]), Lesson.deleted_at.is_(None))
        .group_by(Lesson.course_id)
        .all()
    ) if courses else {}

    result = []
    for c in courses:
        result.append(
            schemas.CmsCourseRead(
                id=str(c.id),
                code=c.code,
                slug=c.slug or str(c.id),
                title=c.title,
                description=c.description,
                excerpt=c.excerpt,
                instructor_name=c.instructor_name,
                modality=c.modality or "online",
                image_url=c.image_url,
                cta_text=c.cta_text or "Inscribirme",
                is_published=c.is_published,
                access_level=c.access_level or "persona",
                duration_hours=c.duration_hours or 0,
                sort_order=getattr(c, "sort_order", 0) or 0,
                lessons_count=lesson_counts.get(c.id, 0),
                created_at=c.created_at,
            )
        )
    return result


@router.post("/cms/courses", response_model=schemas.CmsCourseRead, status_code=201)
def cms_course_create(
    payload: schemas.CmsCourseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Create a new course from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)

    code = payload.code.strip() if payload.code and payload.code.strip() else _generate_course_code(payload.title)
    slug = payload.slug.strip() if payload.slug and payload.slug.strip() else _slugify(payload.title)

    # Ensure unique slug
    base_slug = slug
    counter = 1
    while db.query(Course).filter(Course.slug == slug, Course.deleted_at.is_(None)).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    sede_id = None
    if not _is_global_media_admin(current_user):
        user_sede = _actor_sede_or_none(db, current_user)
        if user_sede:
            try:
                sede_id = UUID(str(user_sede))
            except (ValueError, TypeError):
                sede_id = None

    course = Course(
        code=code,
        slug=slug,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        excerpt=payload.excerpt.strip() if payload.excerpt else None,
        instructor_name=payload.instructor_name.strip() if payload.instructor_name else None,
        modality=payload.modality or "online",
        image_url=payload.image_url.strip() if payload.image_url else None,
        cta_text=payload.cta_text.strip() if payload.cta_text else "Inscribirme",
        is_published=payload.is_published if payload.is_published is not None else True,
        access_level=payload.access_level or "persona",
        duration_hours=payload.duration_hours or 0,
        sort_order=payload.sort_order or 0,
        sede_id=sede_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    record_admin_action(
        db,
        current_user,
        action="cms.courses.create",
        resource_type="academy_course",
        resource_id=str(course.id),
        metadata={"title": course.title, "code": course.code},
    )

    return schemas.CmsCourseRead(
        id=str(course.id),
        code=course.code,
        slug=course.slug or str(course.id),
        title=course.title,
        description=course.description,
        excerpt=course.excerpt,
        instructor_name=course.instructor_name,
        modality=course.modality or "online",
        image_url=course.image_url,
        cta_text=course.cta_text or "Inscribirme",
        is_published=course.is_published,
        access_level=course.access_level or "persona",
        duration_hours=course.duration_hours or 0,
        sort_order=getattr(course, "sort_order", 0) or 0,
        lessons_count=0,
        created_at=course.created_at,
    )


@router.patch("/cms/courses/{course_id}", response_model=schemas.CmsCourseRead)
def cms_course_update(
    course_id: str,
    payload: schemas.CmsCourseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Update a course from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    course = _get_scoped_cms_course(db, current_user, course_id)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(course, key):
            setattr(course, key, value)

    course.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(course)

    record_admin_action(
        db,
        current_user,
        action="cms.courses.update",
        resource_type="academy_course",
        resource_id=str(course.id),
        metadata={"title": course.title, "updated_fields": list(update_data.keys())},
    )

    lessons_count = db.query(Lesson).filter(Lesson.course_id == course.id, Lesson.deleted_at.is_(None)).count()

    return schemas.CmsCourseRead(
        id=str(course.id),
        code=course.code,
        slug=course.slug or str(course.id),
        title=course.title,
        description=course.description,
        excerpt=course.excerpt,
        instructor_name=course.instructor_name,
        modality=course.modality or "online",
        image_url=course.image_url,
        cta_text=course.cta_text or "Inscribirme",
        is_published=course.is_published,
        access_level=course.access_level or "persona",
        duration_hours=course.duration_hours or 0,
        sort_order=getattr(course, "sort_order", 0) or 0,
        lessons_count=lessons_count,
        created_at=course.created_at,
    )


@router.delete("/cms/courses/{course_id}", status_code=204)
def cms_course_delete(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("cms", "edit")),
):
    """Archive / soft delete a course from CMS Builder."""
    _assert_role(current_user, CMS_EDITOR_ROLES)
    course = _get_scoped_cms_course(db, current_user, course_id)

    course.deleted_at = datetime.now(timezone.utc)
    course.is_published = False
    db.commit()

    record_admin_action(
        db,
        current_user,
        action="cms.courses.delete",
        resource_type="academy_course",
        resource_id=str(course.id),
        metadata={"title": course.title},
    )
    return None
