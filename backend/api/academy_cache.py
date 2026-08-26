"""TKT-203 — Caching + N+1 query optimization para Academy.

Provee funciones puras con cache LRU (TTL 5min) alimentadas por el decorador
``backend.core.cache.cached`` y consolida queries que en el cuerpo original de
los endpoints eran N+1 (varias llamadas COUNT sobre el mismo set filtrado).

Scope de cache key:
  * ``dashboard_metrics`` — key por ``sede_id`` (``_global_`` para superadmin).
  * ``list_lessons`` — key por ``(course_id, viewer_role, skip, limit)``.

Estos helpers son invocados desde ``backend.api.academy`` y NO se montan como
routers. La firma acepta ``db: Session`` como argumento posicional, pero la
función ``key_fn`` explícita del decorador ``cached`` evita que la ``Session``
contamine el hash de la cache key (los ``__str__`` de SQLAlchemy son
inestables entre sesiones).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import DeclarativeBase, Session, selectinload

from backend import models
from backend.core.cache import cached

logger = logging.getLogger(__name__)

# ----------------- dashboard_metrics -----------------


def _dashboard_metrics_key(args, kwargs):
    """Cache key de dashboard_metrics: sólo depende de ``sede_id_str``.

    ``args = (sede_id_str, db: Session)``. La ``Session`` es excluida porque
    SQLAlchemy la serializa con ``__str__`` y contaminaría el hash.
    """
    return f"academy:dashboard:metrics:v1:sede={args[0]}"


def invalidate_dashboard_metrics(sede_id_str: str) -> None:
    """M-04 — invalidación activa del cache de ``dashboard_metrics``.

    Borrar la key cacheada de la sede afectada tras una mutación que cambia
    las métricas (Course archive/publish, Enrollment create, Certificate
    emit, etc.). Antes, el cache era puramente pasivo con TTL 5min → un
    Manager podía tomar decisiones con datos stale hasta 5 minutos.

    Llamar solo tras un ``db.commit()`` exitoso, y pasando el mismo
    ``sede_id_str`` que el lector usaría (``_global_`` para superadmin).
    Es no-op si la key no existe. Safe en tests (MemoryRedis.delete mira
    el store y no raises).
    """
    from backend.core.cache import get_redis

    key = f"academy:dashboard:metrics:v1:sede={sede_id_str}"
    try:
        get_redis().delete(key)
    except Exception as exc:  # pragma: no cover - redis best-effort
        # Best-effort: si Redis está caído no rompemos el flujo de mutación.
        logger.debug("academy_cache: redis delete failed for %s: %s", key, exc)


@cached(ttl=300, key_fn=_dashboard_metrics_key)
def _fetch_dashboard_metrics_cached(
    sede_id_str: str,
    db: Session,
) -> dict[str, Any]:
    """Implementación cacheada de ``dashboard_metrics`` (TKT-203).

    N+1 reducido: las contabilizaciones de ``total`` y ``completed`` se
    consolidan en UN sólo query con ``COUNT`` y ``COALESCE(SUM(CASE...))``.
    Antes: 2 queries; ahora: 1 query.

    Sede_id ``_global_`` → superadmin (cursos sin sede). Cualquier otra sede
    filtra cursos por sede + cursos globales (``sede_id IS NULL``) — semántica
    idéntica a ``_course_scope`` en backend.api.academy.

    Staleness: TTL 5min pasivo, ALTA invalidación activa vía
    ``invalidate_dashboard_metrics(sede_id_str)`` tras mutaciones
    (Course archive/publish, Enrollment create, Certificate emit). El TTL
    sigue siendo 5min como backstop para cualquier cambio que no invoque
    el helper, pero el path normal ahora garantiza lectura fresh.

    Si se necesita lectura guaranteed-fresh tras un cambio, bump
    ``academy:dashboard:metrics:v1`` → ``v2`` en ``_dashboard_metrics_key``
    para forzar MISS global sin esperar al TTL.
    """
    courses_query = db.query(models.Course).filter(models.Course.deleted_at.is_(None))
    if sede_id_str != "_global_":
        try:
            sede_id = uuid.UUID(sede_id_str)
        except (TypeError, ValueError):
            logger.warning("academy_cache: ignoring invalid sede_id cache key %r", sede_id_str)
            sede_id = None
        courses_query = courses_query.filter(or_(models.Course.sede_id == sede_id, models.Course.sede_id.is_(None)))
    # Preserve UUID objects at the ORM boundary. Converting them to strings
    # breaks SQLite's UUID bind processor and is unnecessary for PostgreSQL.
    course_ids = [row.id for row in courses_query.with_entities(models.Course.id).all()]
    total_courses = len(course_ids)

    # ----- N+1 consolidado: total + completed en un único query -----
    total_enrollments = 0
    completed_enrollments = 0
    if course_ids:
        agg_row = (
            db.query(
                func.count(models.Enrollment.id),
                func.coalesce(
                    func.sum(case((models.Enrollment.status == "completed", 1), else_=0)),
                    0,
                ),
            )
            .filter(
                models.Enrollment.course_id.in_(course_ids),
                models.Enrollment.deleted_at.is_(None),
            )
            .first()
        )
        if agg_row:
            total_enrollments = int(agg_row[0] or 0)
            completed_enrollments = int(agg_row[1] or 0)

    # ----- Certificados (1 query) -----
    certificates_issued = (
        db.query(models.Certificate)
        .join(models.Enrollment)
        .filter(
            models.Enrollment.course_id.in_(course_ids),
            models.Enrollment.deleted_at.is_(None),
        )
        .count()
        if course_ids
        else 0
    )

    completion_rate = round((completed_enrollments / total_enrollments) * 100, 2) if total_enrollments else 0

    # ----- Trends mensuales (últimos 12 meses) -----
    enrollment_trends: list[dict[str, Any]] = []
    if course_ids:
        cutoff = datetime.now(timezone.utc) - timedelta(days=365)
        # F-07 (cierre 2026-08-02): ``func.date_trunc`` es PostgreSQL-only y
        # producía 500 en SQLite (test con skip silencioso). Expression
        # dialect-aware: SQLite → strftime("%Y-%m") (string), Postgres →
        # date_trunc("month") (datetime). Ambos se normalizan a "YYYY-MM".
        is_sqlite = db.get_bind().dialect.name == "sqlite"
        month_expr = (
            func.strftime("%Y-%m", models.Enrollment.created_at).label("month")
            if is_sqlite
            else func.date_trunc("month", models.Enrollment.created_at).label("month")
        )
        monthly_rows = (
            db.query(
                month_expr,
                func.count(models.Enrollment.id).label("count"),
            )
            .filter(
                models.Enrollment.course_id.in_(course_ids),
                models.Enrollment.deleted_at.is_(None),
                models.Enrollment.created_at >= cutoff,
            )
            .group_by("month")
            .order_by("month")
            .all()
        )
        for month_value, count_value in monthly_rows:
            if isinstance(month_value, str):
                label = month_value
            else:
                label = month_value.strftime("%Y-%m")
            enrollment_trends.append({"label": label, "value": int(count_value or 0)})

    # ----- Top 5 cursos con más matrículas -----
    top_courses: list[dict[str, Any]] = []
    if course_ids:
        top_rows = (
            db.query(
                models.Course.title,
                func.count(models.Enrollment.id).label("count"),
            )
            .join(models.Enrollment, models.Enrollment.course_id == models.Course.id)
            .filter(
                models.Course.id.in_(course_ids),
                models.Enrollment.deleted_at.is_(None),
            )
            .group_by(models.Course.title)
            .order_by(func.count(models.Enrollment.id).desc())
            .limit(5)
            .all()
        )
        for title, count_value in top_rows:
            top_courses.append({"title": title, "count": int(count_value or 0)})

    return {
        "active_students": total_enrollments,
        "completion_rate": completion_rate,
        "certificates_issued": certificates_issued,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "completed_enrollments": completed_enrollments,
        "cards": [
            {"title": "Cursos", "value": str(total_courses), "trend": "", "color": "blue"},
            {"title": "Estudiantes", "value": str(total_enrollments), "trend": "", "color": "green"},
            {"title": "Finalización", "value": f"{completion_rate}%", "trend": "", "color": "amber"},
        ],
        "enrollment_trends": enrollment_trends,
        "top_courses": top_courses,
    }


# ----------------- list_lessons -----------------


def _list_lessons_key(args, kwargs):
    """Cache key de list_lessons: (course_id, viewer_persona_id, is_editor, skip, limit).

    M-05 — antes la key usaba ``viewer_role`` ("editor"/"student"), derivado
    1:1 de ``is_editor``: dos estudiantes con permisos efectivos distintos
    compartían "student" y la misma key pese a potencial divergencia futura.
    Ahora la key incluye ``viewer_persona_id`` (estable por request y único por
    usuario autenticado) + ``is_editor`` explícito, de modo que cualquier
    personalización por usuario (roles granulares, ACLs) invalidar_a la key
    correctamente sin compartir snapshot entre usuarios distintos.

    Nota: ``args`` incluye también ``db: Session`` como último parámetro
    (no serializable); se excluye de la key deliberadamente.
    """
    course_id_str, viewer_persona_id, is_editor, skip, limit, _db = args
    return (
        f"academy:courses:{course_id_str}:lessons:v1:"
        f"user={viewer_persona_id}:editor={bool(is_editor)}:skip={skip}:limit={limit}"
    )


def _to_dict(orm_obj: DeclarativeBase) -> dict[str, Any]:
    """Serializa cualquier ORM SQLAlchemy a dict JSON-seguro (TKT-203).

    Equivalente al ``jsonable_encoder`` por defecto de FastAPI sobre ORM:
    mismas columnas que ``orm_obj.__table__.columns`` con ``datetime``
    → ``isoformat()`` y ``UUID`` → ``str()``. Mantiene el orden natural
    de columnas para que snapshots tests no se rompan al añadir/quitar
    campos en migraciones.
    """

    data: dict[str, Any] = {}
    for column in orm_obj.__table__.columns:
        value = getattr(orm_obj, column.name)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        elif hasattr(value, "hex") and not isinstance(value, str):
            value = str(value)
        data[column.name] = value
    return data


def _lesson_to_dict(lesson: models.Lesson) -> dict[str, Any]:
    """Specialization Lesson → dict: agrega ``resources`` pre-materializados.

    Los ``resources`` pre-materializados por ``.options(selectinload(...))``
    se serializan con el serializer genérico ``_to_dict`` y se filtran los
    soft-deleted (``deleted_at is not None``).
    """

    data = _to_dict(lesson)
    data["resources"] = [_to_dict(r) for r in (lesson.resources or []) if getattr(r, "deleted_at", None) is None]
    return data


@cached(ttl=300, key_fn=_list_lessons_key)
def _fetch_list_lessons_cached(
    course_id_str: str,
    viewer_persona_id: str,
    is_editor: bool,
    skip: int,
    limit: int,
    db: Session,
) -> list[dict[str, Any]]:
    """Implementación cacheada de list_lessons (TKT-203).

    Nota arquitectónica: NO aplica consolidación SQL aquí. La razón:
    ``.options(selectinload(Lesson.resources))`` ya materializa recursos en
    un único JOIN previo (cierre del N+1 latente en Fase 2). La consolidación
    SQL N+1 sólo aplica a ``dashboard_metrics`` donde existían 2 ``count()``
    separados sobre Enrollment. Sin esta nota, un reviewer futuro podría
    pensar que falta N+1 fix en este endpoint.

    Staleness: TTL 5min pasivo (no hay invalidación activa). Mutaciones sobre
    Lesson (publish_toggle, archive, content update) o Course (archive) se
    reflejan hasta 5min después, vía expiración natural. Aceptable para
    catálogo donde staleness de minutos no rompe contrato académico.

    Si se necesita lectura guaranteed-fresh tras un cambio, bump
    ``academy:courses:{course_id}:lessons:v1`` → ``v2`` en ``_list_lessons_key``
    para forzar MISS general sin esperar al TTL.

    M-05 — el parámetro ``viewer_persona_id`` reemplaza al anterior
    ``viewer_role`` ("editor"/"student") en la cache key, para que dos
    usuarios con rol "student" divergent-restrictibles reciban snapshots
    separados por user-id.
    """
    query = (
        db.query(models.Lesson)
        .options(selectinload(models.Lesson.resources))
        .filter(
            models.Lesson.course_id == course_id_str,
            models.Lesson.deleted_at.is_(None),
        )
    )
    if not is_editor:
        query = query.filter(models.Lesson.is_published.is_(True))
    rows = query.order_by(models.Lesson.order_index).offset(skip).limit(limit).all()
    return [_lesson_to_dict(row) for row in rows]
