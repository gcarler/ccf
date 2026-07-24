"""CRUD del modulo de Evangelismo: estrategias, roles, grupos y seguimiento."""

from __future__ import annotations

import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend import models
from backend.crud._utils import _coerce_uuid_or_404, _utcnow
from backend.crud.crm import (
    get_user_sede_id,
    resolve_persona_id_for_user,
)
from backend.models_evangelism import (
    Asistencia,
    EstrategiaEvangelismo,
    GrupoEvangelismo,
    ParticipanteGrupo,
    RegistroSeguimiento,
    RolPersonalizadoEstrategia,
    SesionGrupo,
)
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

# ============================================================
# Axioma 3 — Multi-Tenant defense-in-depth helpers (evangelismo)
# ============================================================
# Patrón idéntico al canon backend/crud/cms.py. Red de seguridad
# contra callers no-API (workers, scripts/seed_*, pytest) y TOCTOU
# entre fetch y commit. La API-layer hace el primer filtro vía
# require_user_sede_id + crud_*_with_sede helpers propios de
# cada router; el CRUD re-valida pre-commit aquí.


def _actor_sede_or_none_evangelismo(
    db: Session, actor_user_id: str | uuid.UUID | None
) -> str | None:
    """Resuelve la sede del actor.

    ``None`` solo representa un superadministrador canonico sin sede.
    Actor ausente, malformado o sin persona asociada -> 401.
    """
    if actor_user_id is None:
        return None
    try:
        actor_uuid = uuid.UUID(str(actor_user_id))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Authenticated actor required")
    if resolve_persona_id_for_user(db, actor_uuid) is None:
        raise HTTPException(status_code=401, detail="Authenticated actor required")
    return get_user_sede_id(db, str(actor_uuid))


def _resolve_persona_sede(db: Session, persona_id) -> str | None:
    """Sede de una persona target, o None si no existe o sin sede."""
    if persona_id is None:
        return None
    try:
        persona_uuid = uuid.UUID(str(persona_id))
    except (TypeError, ValueError, AttributeError):
        return None
    row = (
        db.query(models.Persona.sede_id)
        .filter(models.Persona.id == persona_uuid)
        .first()
    )
    if not row or row[0] is None:
        return None
    return str(row[0])


def _crud_scope_re_check_evangelism_create(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    target_sede: str | None,
    target_persona_id=None,
) -> str:
    """Defense-in-depth para creates.

    Politica:
      - Actor sin sede o target sin sede -> REJECT 409.
      - target_sede != actor_sede -> REJECT 404 (existence-leak safe).
      - target_persona_id resuelve a sede distinta -> REJECT 404.
    """
    if not actor_sede or not target_sede:
        if actor_user_id is None and target_sede:
            return str(target_sede)
        raise HTTPException(
            status_code=409,
            detail="Evangelism content requires an attributed persona and sede",
        )
    if str(target_sede) != str(actor_sede):
        raise HTTPException(
            status_code=404, detail="Evangelism create cross-sede blocked"
        )
    if target_persona_id is not None:
        target_persona_sede = _resolve_persona_sede(db, target_persona_id)
        if target_persona_sede is None or str(target_persona_sede) != str(actor_sede):
            raise HTTPException(
                status_code=404, detail="Evangelism create FK cross-sede blocked"
            )
    return target_sede


def _crud_scope_re_check_evangelism_update(
    db: Session,
    actor_user_id,
    *,
    actor_sede: str | None,
    current_row_sede: str | None,
    incoming_fk_sede: str | None = None,
) -> None:
    """Defense-in-depth para updates/deletes."""
    if not actor_sede:
        return  # superadmin bypass (consistente con API-layer + crud/cms)
    if current_row_sede is None or str(current_row_sede) != str(actor_sede):
        raise HTTPException(
            status_code=404, detail="Evangelism update row cross-sede blocked"
        )
    if incoming_fk_sede is not None and str(incoming_fk_sede) != str(actor_sede):
        raise HTTPException(
            status_code=404, detail="Evangelism update FK cross-sede blocked"
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
    q = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).order_by(EstrategiaEvangelismo.created_at.desc())
    if activa is not None:
        q = q.filter(EstrategiaEvangelismo.activa == activa)
    if clase_raiz is not None:
        q = q.filter(EstrategiaEvangelismo.clase_raiz == clase_raiz)
    if sede_id is not None:
        q = q.filter(EstrategiaEvangelismo.sede_id == sede_id)
    return q.offset(skip).limit(limit).all()


def get_estrategia(db: Session, strategy_id: UUID) -> Optional[EstrategiaEvangelismo]:
    return (
        db.query(EstrategiaEvangelismo)
        .filter(
            EstrategiaEvangelismo.id == strategy_id,
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )


def create_estrategia(
    db: Session,
    data: EstrategiaEvangelismoCreate,
    *,
    actor_user_id: str | uuid.UUID | None = None,
    sede_id: str | None = None,
    categoria_id: UUID | None = None,
) -> EstrategiaEvangelismo:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    valid_cols = {c.key for c in EstrategiaEvangelismo.__table__.columns}
    dump = data.model_dump()
    # Mapear clase_raiz a string si viene como enum; normalizar a mayúsculas
    if "clase_raiz" in dump and dump["clase_raiz"] is not None:
        dump["clase_raiz"] = (
            dump["clase_raiz"].value
            if hasattr(dump["clase_raiz"], "value")
            else dump["clase_raiz"].upper()
        )
    # Map English schema fields to Spanish model columns (via synonym — no field_map needed)
    FIELD_MAP = {"name": "nombre", "description": "descripcion", "start_date": "fecha_inicio", "end_date": "fecha_fin", "day_of_week": "dia_reunion", "start_time": "hora_reunion", "recurrence": "frecuencia"}
    for eng, spa in FIELD_MAP.items():
        if eng in dump and dump[eng] is not None:
            dump[spa] = dump[eng]
    # Campos que no existen como columnas directas: descartar
    row_data = {k: v for k, v in dump.items() if k in valid_cols}
    # Asignar sede_id y categoria_id al objeto
    if sede_id is None and actor_sede is not None:
        sede_id = actor_sede
    if sede_id is not None:
        row_data["sede_id"] = sede_id
    if categoria_id is not None:
        row_data["categoria_id"] = categoria_id
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-construction ──
    _crud_scope_re_check_evangelism_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_sede=row_data.get("sede_id"),
    )
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
    db: Session,
    strategy_id: UUID,
    data: EstrategiaEvangelismoUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> Optional[EstrategiaEvangelismo]:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(EstrategiaEvangelismo)
        .filter(
            EstrategiaEvangelismo.id == strategy_id,
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not db_obj:
        return None
    valid_cols = {c.key for c in EstrategiaEvangelismo.__table__.columns}
    # Los synonyms (recurrence→frecuencia, start_date→fecha_inicio, etc.)
    # no aparecen en __table__.columns, así que los agregamos manualmente
    synonym_map = {
        "recurrence": "frecuencia",
        "start_date": "fecha_inicio",
        "end_date": "fecha_fin",
        "day_of_week": "dia_reunion",
        "start_time": "hora_reunion",
        "created_at": "fecha_creacion",
        "name": "nombre",
        "description": "descripcion",
    }
    dump = data.model_dump(exclude_unset=True)
    # Mapear clase_raiz: normalizar a mayúsculas si viene en minúsculas
    if "clase_raiz" in dump and dump["clase_raiz"] is not None:
        dump["clase_raiz"] = (
            dump["clase_raiz"].value
            if hasattr(dump["clase_raiz"], "value")
            else dump["clase_raiz"].upper()
        )
    update_data = {k: v for k, v in dump.items() if k in valid_cols}
    # Agregar synonyms mapeados a sus columnas reales
    for syn_key, col_name in synonym_map.items():
        if syn_key in dump and col_name not in update_data:
            update_data[col_name] = dump[syn_key]
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-commit ──
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(db_obj.sede_id) if db_obj.sede_id else None,
    )
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_estrategia(
    db: Session,
    strategy_id: UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(EstrategiaEvangelismo)
        .filter(
            EstrategiaEvangelismo.id == strategy_id,
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not db_obj:
        return False
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-soft-delete ──
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=str(db_obj.sede_id) if db_obj.sede_id else None,
    )
    db_obj.deleted_at = _utcnow()
    db.commit()
    return True


# ──────────────────────────────────────────────
# ROLES PERSONALIZADOS DE ESTRATEGIA
# ──────────────────────────────────────────────

def get_roles_personalizados(
    db: Session, estrategia_id: UUID
) -> List[RolPersonalizadoEstrategia]:
    return (
        db.query(RolPersonalizadoEstrategia)
        .filter(
            RolPersonalizadoEstrategia.estrategia_id == estrategia_id,
            RolPersonalizadoEstrategia.deleted_at.is_(None),
        )
        .order_by(RolPersonalizadoEstrategia.id)
        .all()
    )


def create_rol_personalizado(
    db: Session,
    data: RolPersonalizadoEstrategiaCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> RolPersonalizadoEstrategia:
    """Crea un rol personalizado asociado a una estrategia.

    Axioma 3: defense-in-depth — valida que ``data.estrategia_id``
    pertenece a la sede del actor. Si el rol se crea sin estrategia
    (estrategia_id=None) se rechaza con 409: un rol sin estrategia
    es un huérfano no apto para multi-tenant.
    """
    # ── Axioma 3 — Multi-Tenant: resolve actor + estrategia → sede ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    target_sede: str | None = None
    if data.estrategia_id is not None:
        strategy_uuid = _coerce_uuid_or_404(
            data.estrategia_id, "Estrategia no encontrada"
        )
        strategy_row = (
            db.query(EstrategiaEvangelismo.sede_id)
            .filter(
                EstrategiaEvangelismo.id == strategy_uuid,
                EstrategiaEvangelismo.deleted_at.is_(None),
            )
            .first()
        )
        target_sede = (
            str(strategy_row[0]) if strategy_row and strategy_row[0] else None
        )
    _crud_scope_re_check_evangelism_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_sede=target_sede,
    )
    db_obj = RolPersonalizadoEstrategia(**data.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_rol_personalizado(
    db: Session,
    role_id: UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(RolPersonalizadoEstrategia)
        .filter(
            RolPersonalizadoEstrategia.id == role_id,
            RolPersonalizadoEstrategia.deleted_at.is_(None),
        )
        .first()
    )
    if not db_obj:
        return False
    strategy = None
    if db_obj.estrategia_id:
        strategy = (
            db.query(EstrategiaEvangelismo)
            .filter(EstrategiaEvangelismo.id == db_obj.estrategia_id)
            .first()
        )
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-soft-delete ──
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=(
            str(strategy.sede_id) if strategy and strategy.sede_id else None
        ),
    )
    if strategy and strategy.default_role_id == db_obj.id:
        strategy.default_role_id = None
    db_obj.deleted_at = _utcnow()
    db.commit()
    return True


# ──────────────────────────────────────────────
# PARTICIPANTES DE GRUPO
# ──────────────────────────────────────────────

def get_participantes(
    db: Session,
    grupo_id: uuid.UUID,
    solo_activos: bool = True,
) -> List[ParticipanteGrupo]:
    q = db.query(ParticipanteGrupo).filter(
        ParticipanteGrupo.grupo_id == grupo_id,
        ParticipanteGrupo.deleted_at.is_(None),
    )
    if solo_activos:
        q = q.filter(ParticipanteGrupo.activo == True)  # noqa: E712
    return q.all()


def agregar_participante(
    db: Session,
    data: ParticipanteGrupoCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> ParticipanteGrupo:
    # ── Axioma 3 — Multi-Tenant: validate grupo + persona FK against actor's sede ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    grupo_row = (
        db.query(GrupoEvangelismo.sede_id)
        .filter(GrupoEvangelismo.id == data.grupo_id)
        .first()
    )
    grupo_sede = str(grupo_row[0]) if grupo_row and grupo_row[0] else None
    _crud_scope_re_check_evangelism_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_sede=grupo_sede,
        target_persona_id=data.persona_id,
    )
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
    db: Session,
    participante_id: UUID,
    data: ParticipanteGrupoUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> Optional[ParticipanteGrupo]:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(ParticipanteGrupo)
        .filter(ParticipanteGrupo.id == participante_id)
        .first()
    )
    if not db_obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-commit ──
    grupo_row = (
        db.query(GrupoEvangelismo.sede_id)
        .filter(GrupoEvangelismo.id == db_obj.grupo_id)
        .first()
    )
    current_grupo_sede = str(grupo_row[0]) if grupo_row and grupo_row[0] else None
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=current_grupo_sede,
        incoming_fk_sede=(
            _resolve_persona_sede(db, update_data.get("persona_id"))
            if update_data.get("persona_id") else None
        ),
    )
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def remover_participante(
    db: Session,
    participante_id: UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    """Soft-delete: marca como inactivo en lugar de borrar."""
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(ParticipanteGrupo)
        .filter(ParticipanteGrupo.id == participante_id)
        .first()
    )
    if not db_obj:
        return False
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-soft-delete ──
    grupo_row = (
        db.query(GrupoEvangelismo.sede_id)
        .filter(GrupoEvangelismo.id == db_obj.grupo_id)
        .first()
    )
    grupo_sede = str(grupo_row[0]) if grupo_row and grupo_row[0] else None
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=grupo_sede,
    )
    db_obj.activo = False
    db.commit()
    return True


# ──────────────────────────────────────────────
# ASISTENCIA
# ──────────────────────────────────────────────

def submit_asistencia(
    db: Session,
    data: AsistenciaSesionCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> Asistencia:
    """Crea o actualiza un registro de asistencia.

    El valor es_primera_vez se toma del payload.
    Axioma 3: defense-in-depth — valida que sesion y persona estan en sede del actor.
    """
    # ── Axioma 3 ─ Multi-Tenant: resolve actor + sesion ─ grupo ─ sede ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    # Existence-leak safe 404 antes del query para cerrar vector 500.
    sesion_uuid = _coerce_uuid_or_404(data.sesion_id, "Sesión no encontrada")
    sesion_row = (
        db.query(SesionGrupo.id, GrupoEvangelismo.sede_id)
        .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(SesionGrupo.id == sesion_uuid)
        .first()
    )
    sesion_sede = str(sesion_row[1]) if sesion_row and sesion_row[1] else None
    _crud_scope_re_check_evangelism_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_sede=sesion_sede,
        target_persona_id=data.persona_id,
    )
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
    db: Session, asistencia_id: UUID, *, sede_id: str | None = None
) -> List[RegistroSeguimiento]:
    """Lista seguimientos de una asistencia.

    ``sede_id`` opcional aplica Axioma 3 (multi-tenant) por join
    ``seguimiento -> asistencia -> sesion -> grupo -> sede``. Sin ``sede_id``
    (= superadmin sin sede) se devuelven todas — consistente con el canon
    del módulo.
    """
    q = db.query(RegistroSeguimiento).filter(
        RegistroSeguimiento.asistencia_id == asistencia_id,
        RegistroSeguimiento.deleted_at.is_(None),
    )
    if sede_id is not None:
        q = (
            q.join(Asistencia, Asistencia.id == RegistroSeguimiento.asistencia_id)
            .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
            .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
            .filter(GrupoEvangelismo.sede_id == sede_id)
        )
    return q.order_by(RegistroSeguimiento.created_at.desc()).all()


def create_seguimiento(
    db: Session,
    data: RegistroSeguimientoCreate,
    *,
    actor_user_id: str | uuid.UUID,
) -> RegistroSeguimiento:
    # ── Axioma 3 — Multi-Tenant: validate seguimiento -> asistencia -> sesion -> grupo ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    target_sede: str | None = None
    if data.asistencia_id:
        # Existence-leak safe 404 antes del query para cerrar vector 500.
        asist_uuid = _coerce_uuid_or_404(data.asistencia_id, "Asistencia no encontrada")
        asist_row = (
            db.query(Asistencia.id, GrupoEvangelismo.sede_id)
            .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
            .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
            .filter(Asistencia.id == asist_uuid, Asistencia.deleted_at.is_(None))
            .first()
        )
        if not asist_row:
            raise HTTPException(status_code=404, detail="Asistencia no encontrada")
        target_sede = str(asist_row[1]) if asist_row and asist_row[1] else None
    _crud_scope_re_check_evangelism_create(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        target_sede=target_sede,
    )
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
        .filter(
            Asistencia.id == data.asistencia_id,
            Asistencia.deleted_at.is_(None),
        )
        .first()
    )
    if asistencia:
        asistencia.requiere_seguimiento = True

    db.commit()
    db.refresh(db_obj)
    return db_obj


def update_seguimiento(
    db: Session,
    seguimiento_id: UUID,
    data: RegistroSeguimientoUpdate,
    *,
    actor_user_id: str | uuid.UUID,
) -> Optional[RegistroSeguimiento]:
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(RegistroSeguimiento)
        .filter(
            RegistroSeguimiento.id == seguimiento_id,
            RegistroSeguimiento.deleted_at.is_(None),
        )
        .first()
    )
    if not db_obj:
        return None
    update_data = data.model_dump(exclude_unset=True)
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-commit ──
    asist_row = (
        db.query(Asistencia.id, GrupoEvangelismo.sede_id)
        .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
        .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(Asistencia.id == db_obj.asistencia_id)
        .first()
    )
    current_sede = str(asist_row[1]) if asist_row and asist_row[1] else None
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=current_sede,
        incoming_fk_sede=(
            _resolve_persona_sede(db, update_data.get("responsable_id"))
            if update_data.get("responsable_id") else None
        ),
    )
    for key, value in update_data.items():
        setattr(db_obj, key, value)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_pendientes_seguimiento(
    db: Session,
    limit: int = 50,
    *,
    sede_id: str | None = None,
    strategy_id: str | UUID | None = None,
) -> List[RegistroSeguimiento]:
    """Retorna los seguimientos pendientes (no completados).

    ``sede_id`` opcional aplica Axioma 3 (multi-tenant) por join
    ``seguimiento -> asistencia -> sesion -> grupo -> sede``. Sin ``sede_id``
    (= superadmin sin sede) se devuelven todas.

    ``strategy_id`` opcional acota el resultado a seguimientos cuya
    asistencia está dentro de un grupo de la estrategia dada (join extra
    ``grupo.estrategia_id``). Útil para scoping del panel de la page
    ``/strategies/[id]`` que sin esto mostraría seguimientos globales de
    la sede dando una impresión falsa de "estos son de esta estrategia".
    """
    q = db.query(RegistroSeguimiento).filter(
        RegistroSeguimiento.estado_completado == False,  # noqa: E712
        RegistroSeguimiento.deleted_at.is_(None),
    )
    if sede_id is not None or strategy_id is not None:
        q = (
            q.join(Asistencia, Asistencia.id == RegistroSeguimiento.asistencia_id)
            .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
            .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        )
        if sede_id is not None:
            q = q.filter(GrupoEvangelismo.sede_id == sede_id)
        if strategy_id is not None:
            try:
                strategy_uuid = uuid.UUID(str(strategy_id))
            except (TypeError, ValueError, AttributeError):
                strategy_uuid = None
            if strategy_uuid is not None:
                q = q.filter(GrupoEvangelismo.estrategia_id == strategy_uuid)
    return (
        q.order_by(RegistroSeguimiento.fecha_seguimiento.asc().nullsfirst())
        .limit(limit)
        .all()
    )


def delete_seguimiento(
    db: Session,
    seguimiento_id: UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    """Realiza soft-delete de un ``RegistroSeguimiento``.

    Axioma 3: valida que el seguimiento → asistencia → sesion → grupo
    pertenezca a la sede del actor; ``deleted_at`` ya previene re-mutacion
    (query inicial reusa el mismo filtro).
    Retorna ``True`` si se elimino, ``False`` si no se encontro.
    """
    # ── Axioma 3 — Multi-Tenant: resolve actor ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = (
        db.query(RegistroSeguimiento)
        .filter(
            RegistroSeguimiento.id == seguimiento_id,
            RegistroSeguimiento.deleted_at.is_(None),
        )
        .first()
    )
    if not db_obj:
        return False
    # ── Axioma 3 — Multi-Tenant: defense-in-depth pre-commit ──
    asist_row = (
        db.query(Asistencia.id, GrupoEvangelismo.sede_id)
        .join(SesionGrupo, SesionGrupo.id == Asistencia.sesion_id)
        .join(GrupoEvangelismo, GrupoEvangelismo.id == SesionGrupo.grupo_id)
        .filter(Asistencia.id == db_obj.asistencia_id)
        .first()
    )
    current_sede = str(asist_row[1]) if asist_row and asist_row[1] else None
    _crud_scope_re_check_evangelism_update(
        db,
        actor_user_id,
        actor_sede=actor_sede,
        current_row_sede=current_sede,
    )
    db_obj.deleted_at = _utcnow()
    db.commit()
    return True


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
    db: Session,
    descripcion: str,
    es_del_sistema: bool = False,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.MotivoExcusa:
    # ── Axioma 3 — Multi-Tenant: motivos del sistema solo superadmin ──
    actor_sede = _actor_sede_or_none_evangelismo(db, actor_user_id)
    if es_del_sistema and actor_sede is not None:
        raise HTTPException(
            status_code=409,
            detail="Solo superadmin sin sede puede crear motivo del sistema",
        )
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
    db: Session,
    excusa_id: UUID,
    descripcion: str | None = None,
    activo: bool | None = None,
    *,
    actor_user_id: str | uuid.UUID,
) -> models.MotivoExcusa | None:
    # ── Axioma 3 — Multi-Tenant: requiere autenticacion. Mutaciones a
    # MotivoExcusa son cross-sede por naturaleza (lookup table global);
    # el actor debe estar autenticado (401 si no). Las reglas de
    # sistema (es_del_sistema=True) se refuerzan abajo. ──
    _ = _actor_sede_or_none_evangelismo(db, actor_user_id)
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


def delete_motivo_excusa(
    db: Session,
    excusa_id: UUID,
    *,
    actor_user_id: str | uuid.UUID,
) -> bool:
    # ── Axioma 3 — Multi-Tenant: requiere autenticacion. ──
    _ = _actor_sede_or_none_evangelismo(db, actor_user_id)
    db_obj = db.query(models.MotivoExcusa).filter(models.MotivoExcusa.id == excusa_id).first()
    if not db_obj or db_obj.es_del_sistema:
        return False
    db_obj.deleted_at = _utcnow()
    db.commit()
    return True


def seed_motivos_excusa(
    db: Session, *, actor_user_id: str | uuid.UUID | None = None
) -> list[models.MotivoExcusa]:
    """Inserta las excusas base del sistema si no existen.

    ``MotivoExcusa`` es lookup-table global (cross-sede por naturaleza),
    por lo que cualquier actor autorizado del módulo puede ejecutar el
    seed. La operación es idempotente y solo crea filas faltantes.
    """
    base = ["SALUD", "TRABAJO", "FAMILIA", "OTRA (VER DETALLE)"]
    created = []
    for desc in base:
        existing = db.query(models.MotivoExcusa).filter(
            models.MotivoExcusa.descripcion == desc
        ).first()
        if not existing:
            row = models.MotivoExcusa(
                descripcion=desc.upper(),
                es_del_sistema=True,
                activo=True,
            )
            db.add(row)
            created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created
