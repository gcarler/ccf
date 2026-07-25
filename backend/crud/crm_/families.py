"""Family CRUD and family personas."""
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow


def get_families(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    sede_id: Optional[UUID] = None,
):
    """Lista familias con scope-via-personas (Family sin sede_id propio — Axioma 3).

    Cuando se pasa ``sede_id``, sólo se retornan las familias que tienen al
    menos una persona assignada con esa sede. Aplica ``.offset()``/``.limit()``
    DESPUÉS del scope, así la paginación funciona correctamente incluso para
    sedes minoritarias (no se saltan offsets globales de otra sede).

    Elimina el N+1 query del loop anterior: las ``personas_count`` se
    resuelven en una sola sub-agregación por ``family_id``.

    NOTA: ``Family`` no tiene ``deleted_at`` (doctrina: Family es derivado via
    Persona en lugar de soft-deletable standalone — getPuntos(id)/delete_family
    marca deleted_at en runtime via ORM attribute, pero la columna NO existe
    en la tabla/modelo). No aplicar filter ``deleted_at.is_(None)`` aquí.
    """
    base_q = db.query(models.Family)

    if sede_id is not None:
        # Family no tiene sede_id propio -> membership-scoped: la familia
        # aparece sólo si existe al menos una Persona con sede_id + family_id.
        base_q = base_q.join(
            models.Persona,
            models.Persona.family_id == models.Family.id,
        ).filter(
            models.Persona.sede_id == sede_id,
        ).distinct()

    families = base_q.order_by(models.Family.name.asc()).offset(skip).limit(limit).all()

    # Batch count: una sola query GROUP BY en vez de N round-trip por family.
    if families:
        family_ids = [f.id for f in families]
        count_rows = (
            db.query(
                models.Persona.family_id,
                func.count(models.Persona.id).label("c"),
            )
            .filter(
                models.Persona.family_id.in_(family_ids),
            )
            .group_by(models.Persona.family_id)
            .all()
        )
        counts = {row[0]: row[1] for row in count_rows}
    else:
        counts = {}

    for f in families:
        f.personas_count = counts.get(f.id, 0)

    return families


def create_family(db: Session, name: str):
    fam = models.Family(name=name)
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


def get_family(db: Session, family_id: UUID) -> Optional[models.Family]:
    return db.query(models.Family).filter(models.Family.id == family_id).first()


def update_family(db: Session, family_id: UUID, name: str) -> Optional[models.Family]:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return None
    row.name = name
    db.commit()
    db.refresh(row)
    return row


def delete_family(db: Session, family_id: UUID) -> bool:
    row = db.query(models.Family).filter(models.Family.id == family_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True


def get_family_personas(db: Session, family_id: UUID):
    return (
        db.query(models.Persona)
        .filter(models.Persona.family_id == family_id)
        .order_by(models.Persona.nombre_completo.asc())
        .all()
    )
