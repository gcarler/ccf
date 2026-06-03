"""CRUD del módulo de Evangelismo — Estrategias, roles, grupos, seguimiento.

Las funciones existentes en crud/crm.py se mantienen para back-compat.
Este archivo contiene el CRUD refactorizado con los nuevos esquemas.
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _utcnow
from backend.models_evangelism import EstrategiaEvangelismo
from backend.models_evangelism import (
    ParticipanteGrupo, Asistencia,
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
        db.query(EstrategiaEvangelismo.codigo)
        .filter(EstrategiaEvangelismo.codigo.isnot(None))
        .order_by(EstrategiaEvangelismo.codigo.desc())
        .first()
    )
    if last and last.codigo:
        try:
            num = int(last.codigo.split("-")[1])
            return f"EVG-{num + 1}"
        except (IndexError, ValueError):
            pass
    # Fallback: timestamp-based
    import time
    return f"EVG-{int(time.time()) % 100000}"


def get_estrategias(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    activa: Optional[bool] = None,
    clase_raiz: Optional[str] = None,
    sede_id: Optional[str] = None,
) -> List[EstrategiaEvangelismo]:
    """Lista estrategias con filtros opcionales."""
    q = db.query(EstrategiaEvangelismo).order_by(EstrategiaEvangelismo.created_at.desc())
    if activa is not None:
        q = q.filter(EstrategiaEvangelismo.activa == activa)
    if clase_raiz is not None:
        q = q.filter(EstrategiaEvangelismo.clase_raiz == clase_raiz)
    if sede_id is not None:
        q = q.filter(EstrategiaEvangelismo.sede_id == sede_id)
    return q.offset(skip).limit(limit).all()


def get_estrategia(db: Session, strategy_id: str) -> Optional[EstrategiaEvangelismo]:
    return (
        db.query(EstrategiaEvangelismo)
        .filter(EstrategiaEvangelismo.id == strategy_id)
        .first()
    )


def create_estrategia(
    db: Session, data: EstrategiaEvangelismoCreate, sede_id: str | None = None, categoria_id: int | None = None
) -> EstrategiaEvangelismo:
    valid_cols = {c.key for c in EstrategiaEvangelismo.__table__.columns}
    dump = data.model_dump()
    # Mapear clase_raiz a string si viene como enum
    if "clase_raiz" in dump and dump["clase_raiz"] is not None:
        dump["clase_raiz"] = (
            dump["clase_raiz"].value
            if hasattr(dump["clase_raiz"], "value")
            else dump["clase_raiz"]
        )
    # Map English schema fields to Spanish model columns (via synonym — no field_map needed)
    FIELD_MAP = {"name": "nombre", "description": "descripcion", "start_date": "fecha_inicio", "end_date": "fecha_fin", "day_of_week": "dia_reunion", "start_time": "hora_reunion", "recurrence": "frecuencia"}
    for eng, spa in FIELD_MAP.items():
        if eng in dump and dump[eng] is not None:
            dump[spa] = dump[eng]
    # Campos que no existen como columnas directas: descartar
    row_data = {k: v for k, v in dump.items() if k in valid_cols}
    # Asignar sede_id y categoria_id al objeto
    if sede_id is not None:
        row_data["sede_id"] = sede_id
    if categoria_id is not None:
        row_data["categoria_id"] = categoria_id
    db_obj = EstrategiaEvangelismo(**row_data)
    db.add(db_obj)
    db.flush()  # Obtener el ID
    # Generar código después del flush
    if not db_obj.codigo:
        db_obj.codigo = f"EVG-{str(db_obj.id)[:8]}"
    # Sincronizar clase_raiz con typology si no se especificó
    if not db_obj.clase_raiz and db_obj.typology:
        db_obj.clase_raiz = db_obj.typology
    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_estrategia(
    db: Session, strategy_id: str, data: EstrategiaEvangelismoUpdate
) -> Optional[EstrategiaEvangelismo]:
    db_obj = (
        db.query(EstrategiaEvangelismo)
        .filter(EstrategiaEvangelismo.id == strategy_id)
        .first()
    )
    if not db_obj:
        return None
    valid_cols = {c.key for c in EstrategiaEvangelismo.__table__.columns}
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


def delete_estrategia(db: Session, strategy_id: str) -> bool:
    db_obj = (
        db.query(EstrategiaEvangelismo)
        .filter(EstrategiaEvangelismo.id == strategy_id)
        .first()
    )
    if not db_obj:
        return False
    db_obj.deleted_at = _utcnow()
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
        .order_by(RolPersonalizadoEstrategia.id)
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
    db_obj.deleted_at = _utcnow()
    db.commit()
    return True


# ──────────────────────────────────────────────
# PARTICIPANTES DE GRUPO
# ──────────────────────────────────────────────

def get_participantes(
    db: Session,
    grupo_id: int,
    solo_activos: bool = True,
) -> List[ParticipanteGrupo]:
    q = db.query(ParticipanteGrupo).filter(
        ParticipanteGrupo.grupo_id == grupo_id
    )
    if solo_activos:
        q = q.filter(ParticipanteGrupo.activo == True)  # noqa: E712
    return q.all()


def agregar_participante(
    db: Session, data: ParticipanteGrupoCreate
) -> ParticipanteGrupo:
    db_obj = ParticipanteGrupo(
        grupo_id=data.grupo_id,
        persona_id=data.persona_id,
        rol_base=data.role or "miembro",
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
) -> Optional[ParticipanteGrupo]:
    db_obj = (
        db.query(ParticipanteGrupo)
        .filter(ParticipanteGrupo.id == participante_id)
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
        db.query(ParticipanteGrupo)
        .filter(ParticipanteGrupo.id == participante_id)
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
) -> Asistencia:
    """Crea o actualiza un registro de asistencia.

    Auto-detecta es_primera_vez: si la persona no tiene asistencias previas
    en el mismo grupo, marca como primera_vez.
    """
    # Verificar si ya existe
    existing = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == data.sesion_id,
            Asistencia.persona_id == data.persona_id,
        )
        .first()
    )
    if existing:
        # Actualizar registro existente
        update_data = data.model_dump(exclude={"sesion_id", "persona_id"}, exclude_unset=True)
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
    valid_cols = {c.key for c in Asistencia.__table__.columns}
    row_data = {k: v for k, v in dump.items() if k in valid_cols}
    db_obj = Asistencia(**row_data)
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
        db.query(Asistencia)
        .filter(Asistencia.id == data.asistencia_id)
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
        .filter(RegistroSeguimiento.estado_completado == False)  # noqa: E712
        .order_by(RegistroSeguimiento.fecha_seguimiento.asc().nullsfirst())
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
    db_obj.deleted_at = _utcnow()
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
