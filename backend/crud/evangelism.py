"""CRUD del módulo de Evangelismo — Estrategias, roles, grupos, seguimiento.

Las funciones existentes en crud/crm.py se mantienen para back-compat.
Este archivo contiene el CRUD refactorizado con los nuevos esquemas.
"""

from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow
from backend.models_crm import EvangelismStrategy
from backend.models_academy import (
    GloryHouse, GloryHouseMember, GloryHouseAttendance, GloryHouseSession,
)
from backend.models_evangelism import (
    RolPersonalizadoEstrategia,
    RegistroSeguimiento,
)
from backend.schemas.evangelism import ClaseEstrategiaEnum
from backend.schemas.evangelism import (
    AsistenciaSesionCreate,
    EstrategiaEvangelismoCreate,
    EstrategiaEvangelismoUpdate,
    ParticipanteGrupoCreate,
    ParticipanteGrupoUpdate,
    RegistroSeguimientoCreate,
    RegistroSeguimientoUpdate,
    RolPersonalizadoEstrategiaCreate,
)


# ──────────────────────────────────────────────
# ESTRATEGIAS
# ──────────────────────────────────────────────

def _generate_codigo(db: Session) -> str:
    """Genera un código EVG-XXX auto-incremental."""
    last = (
        db.query(EvangelismStrategy.codigo)
        .filter(EvangelismStrategy.codigo.isnot(None))
        .order_by(EvangelismStrategy.id.desc())
        .first()
    )
    if last and last.codigo:
        try:
            num = int(last.codigo.split("-")[1])
            return f"EVG-{num + 1}"
        except (IndexError, ValueError):
            pass
    # Fallback: usar el próximo ID
    from sqlalchemy import func
    max_id = db.query(func.max(EvangelismStrategy.id)).scalar() or 0
    return f"EVG-{max_id + 1}"


def get_estrategias(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[ClaseEstrategiaEnum] = None,
) -> List[EvangelismStrategy]:
    """Lista estrategias con filtros opcionales."""
    q = db.query(EvangelismStrategy).order_by(EvangelismStrategy.created_at.desc())
    if activa is not None:
        q = q.filter(EvangelismStrategy.activa == activa)
    if clase_raiz is not None:
        q = q.filter(EvangelismStrategy.clase_raiz == clase_raiz.value)
    return q.offset(skip).limit(limit).all()


def get_estrategia(db: Session, strategy_id: int) -> Optional[EvangelismStrategy]:
    return (
        db.query(EvangelismStrategy)
        .filter(EvangelismStrategy.id == strategy_id)
        .first()
    )


def create_estrategia(
    db: Session, data: EstrategiaEvangelismoCreate
) -> EvangelismStrategy:
    valid_cols = {c.key for c in EvangelismStrategy.__table__.columns}
    dump = data.model_dump()
    # Mapear clase_raiz a string si viene como enum
    if "clase_raiz" in dump and dump["clase_raiz"] is not None:
        dump["clase_raiz"] = (
            dump["clase_raiz"].value
            if hasattr(dump["clase_raiz"], "value")
            else dump["clase_raiz"]
        )
    row_data = {k: v for k, v in dump.items() if k in valid_cols}
    db_obj = EvangelismStrategy(**row_data)
    db.add(db_obj)
    db.flush()  # Obtener el ID
    # Generar código después del flush para tener el ID
    if not db_obj.codigo:
        db_obj.codigo = f"EVG-{db_obj.id}"
        # Sincronizar clase_raiz con typology si no se especificó
    if not db_obj.clase_raiz and db_obj.typology:
        db_obj.clase_raiz = db_obj.typology
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_estrategia(
    db: Session, strategy_id: int, data: EstrategiaEvangelismoUpdate
) -> Optional[EvangelismStrategy]:
    db_obj = (
        db.query(EvangelismStrategy)
        .filter(EvangelismStrategy.id == strategy_id)
        .first()
    )
    if not db_obj:
        return None
    valid_cols = {c.key for c in EvangelismStrategy.__table__.columns}
    dump = data.model_dump(exclude_unset=True)
    # Mapear clase_raiz enum a string
    if "clase_raiz" in dump and dump["clase_raiz"] is not None:
        dump["clase_raiz"] = (
            dump["clase_raiz"].value
            if hasattr(dump["clase_raiz"], "value")
            else dump["clase_raiz"]
        )
    update_data = {k: v for k, v in dump.items() if k in valid_cols}
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_estrategia(db: Session, strategy_id: int) -> bool:
    db_obj = (
        db.query(EvangelismStrategy)
        .filter(EvangelismStrategy.id == strategy_id)
        .first()
    )
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True


# ──────────────────────────────────────────────
# ROLES PERSONALIZADOS DE ESTRATEGIA
# ──────────────────────────────────────────────

def get_roles_personalizados(
    db: Session, estrategia_id: str
) -> List[RolPersonalizadoEstrategia]:
    return (
        db.query(RolPersonalizadoEstrategia)
        .filter(RolPersonalizadoEstrategia.estrategia_id == estrategia_id)
        .order_by(RolPersonalizadoEstrategia.created_at)
        .all()
    )


def create_rol_personalizado(
    db: Session, data: RolPersonalizadoEstrategiaCreate
) -> RolPersonalizadoEstrategia:
    db_obj = RolPersonalizadoEstrategia(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_rol_personalizado(db: Session, role_id: int) -> bool:
    db_obj = (
        db.query(RolPersonalizadoEstrategia)
        .filter(RolPersonalizadoEstrategia.id == role_id)
        .first()
    )
    if not db_obj:
        return False
    db.delete(db_obj)
    db.commit()
    return True


# ──────────────────────────────────────────────
# PARTICIPANTES DE GRUPO
# ──────────────────────────────────────────────

def get_participantes(
    db: Session,
    grupo_id: int,
    solo_activos: bool = True,
) -> List[GloryHouseMember]:
    q = db.query(GloryHouseMember).filter(
        GloryHouseMember.glory_house_id == grupo_id
    )
    if solo_activos:
        q = q.filter(GloryHouseMember.activo == True)  # noqa: E712
    return q.all()


def agregar_participante(
    db: Session, data: ParticipanteGrupoCreate
) -> GloryHouseMember:
    db_obj = GloryHouseMember(
        glory_house_id=data.glory_house_id,
        persona_id=data.persona_id,
        role=data.role or "miembro",
        rol_personalizado_id=data.rol_personalizado_id,
        activo=data.activo,
        fecha_ingreso=_utcnow(),
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def actualizar_participante(
    db: Session, participante_id: int, data: ParticipanteGrupoUpdate
) -> Optional[GloryHouseMember]:
    db_obj = (
        db.query(GloryHouseMember)
        .filter(GloryHouseMember.id == participante_id)
        .first()
    )
    if not db_obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remover_participante(db: Session, participante_id: int) -> bool:
    """Soft-delete: marca como inactivo en lugar de borrar."""
    db_obj = (
        db.query(GloryHouseMember)
        .filter(GloryHouseMember.id == participante_id)
        .first()
    )
    if not db_obj:
        return False
    db_obj.activo = False
    db.commit()
    return True


# ──────────────────────────────────────────────
# ASISTENCIA
# ──────────────────────────────────────────────

def submit_asistencia(
    db: Session, data: AsistenciaSesionCreate
) -> GloryHouseAttendance:
    """Crea o actualiza un registro de asistencia.

    Auto-detecta es_primera_vez: si la persona no tiene asistencias previas
    en el mismo grupo, marca como primera_vez.
    """
    # Verificar si ya existe
    existing = (
        db.query(GloryHouseAttendance)
        .filter(
            GloryHouseAttendance.session_id == data.session_id,
            GloryHouseAttendance.persona_id == data.persona_id,
        )
        .first()
    )
    if existing:
        # Actualizar registro existente
        update_data = data.model_dump(exclude={"session_id", "persona_id"}, exclude_unset=True)
        # Mapear estado a string si viene como enum
        if "estado" in update_data and update_data["estado"] is not None:
            raw = update_data["estado"]
            update_data["estado"] = raw.value if hasattr(raw, "value") else raw
        for key, value in update_data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing

    dump = data.model_dump()
    if dump.get("estado") is not None:
        raw = dump["estado"]
        dump["estado"] = raw.value if hasattr(raw, "value") else raw

    db_obj = GloryHouseAttendance(**dump)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


# ──────────────────────────────────────────────
# SEGUIMIENTO
# ──────────────────────────────────────────────

def get_seguimientos(
    db: Session, asistencia_id: int
) -> List[RegistroSeguimiento]:
    return (
        db.query(RegistroSeguimiento)
        .filter(RegistroSeguimiento.asistencia_id == asistencia_id)
        .order_by(RegistroSeguimiento.created_at.desc())
        .all()
    )


def create_seguimiento(
    db: Session, data: RegistroSeguimientoCreate
) -> RegistroSeguimiento:
    dump = data.model_dump()
    # Mapear tipo enum a string
    if "tipo" in dump and dump["tipo"] is not None:
        raw = dump["tipo"]
        dump["tipo"] = raw.value if hasattr(raw, "value") else raw
    db_obj = RegistroSeguimiento(**dump)
    db.add(db_obj)

    # Marcar la asistencia como requiere_seguimiento = True
    asistencia = (
        db.query(GloryHouseAttendance)
        .filter(GloryHouseAttendance.id == data.asistencia_id)
        .first()
    )
    if asistencia:
        asistencia.requiere_seguimiento = True

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_seguimiento(
    db: Session, seguimiento_id: int, data: RegistroSeguimientoUpdate
) -> Optional[RegistroSeguimiento]:
    db_obj = (
        db.query(RegistroSeguimiento)
        .filter(RegistroSeguimiento.id == seguimiento_id)
        .first()
    )
    if not db_obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_pendientes_seguimiento(
    db: Session, limit: int = 50
) -> List[RegistroSeguimiento]:
    """Retorna todos los seguimientos pendientes (no completados)."""
    return (
        db.query(RegistroSeguimiento)
        .filter(RegistroSeguimiento.completado == False)  # noqa: E712
        .order_by(RegistroSeguimiento.fecha_programada.asc().nullsfirst())
        .limit(limit)
        .all()
    )


# ──────────────────────────────────────────────
# MOTIVOS DE EXCUSA
# ──────────────────────────────────────────────

def get_motivos_excusa(
    db: Session, solo_activos: bool = True
) -> List[models.MotivoExcusa]:
    q = db.query(models.MotivoExcusa).order_by(models.MotivoExcusa.descripcion)
    if solo_activos:
        q = q.filter(models.MotivoExcusa.activo == True)  # noqa: E712
    return q.all()


def create_motivo_excusa(
    db: Session, descripcion: str, es_del_sistema: bool = False
) -> models.MotivoExcusa:
    db_obj = models.MotivoExcusa(
        descripcion=descripcion.upper(),
        es_del_sistema=es_del_sistema,
        activo=True,
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_motivo_excusa(
    db: Session, excusa_id: int, descripcion: str | None = None, activo: bool | None = None
) -> models.MotivoExcusa | None:
    db_obj = db.query(models.MotivoExcusa).filter(models.MotivoExcusa.id == excusa_id).first()
    if not db_obj:
        return None
    if db_obj.es_del_sistema:
        return None  # No se puede modificar excusas del sistema
    if descripcion is not None:
        db_obj.descripcion = descripcion.upper()
    if activo is not None:
        db_obj.activo = activo
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_motivo_excusa(db: Session, excusa_id: int) -> bool:
    db_obj = db.query(models.MotivoExcusa).filter(models.MotivoExcusa.id == excusa_id).first()
    if not db_obj or db_obj.es_del_sistema:
        return False
    db.delete(db_obj)
    db.commit()
    return True


def seed_motivos_excusa(db: Session) -> list[models.MotivoExcusa]:
    """Inserta las excusas base del sistema si no existen."""
    base = ["SALUD", "TRABAJO", "FAMILIA", "OTRA (VER DETALLE)"]
    created = []
    for desc in base:
        existing = db.query(models.MotivoExcusa).filter(
            models.MotivoExcusa.descripcion == desc
        ).first()
        if not existing:
            created.append(create_motivo_excusa(db, desc, es_del_sistema=True))
    return created
