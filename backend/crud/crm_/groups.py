"""Grupos evangelismo CRUD."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from backend import models, schemas
from backend.crud._utils import _utcnow


def _group_participant_role_values(item):
    role = str(getattr(item, "role", "") or "participante").strip()
    custom_role_id = getattr(item, "rol_personalizado_id", None)
    if role.startswith("custom:"):
        try:
            custom_role_id = int(role.split(":", 1)[1])
        except (TypeError, ValueError):
            custom_role_id = None
        role = "personalizado"
    return role or "participante", custom_role_id


def get_grupos(db: Session, skip: int = 0, limit: int = 100, sede_id: str | None = None):
    query = db.query(models.GrupoEvangelismo)
    if sede_id:
        query = query.filter(models.GrupoEvangelismo.sede_id == sede_id)
    return query.offset(skip).limit(limit).all()


def create_grupo(db: Session, payload: schemas.GrupoEvangelismoCreate, sede_id: str | None = None):
    data = payload.model_dump(exclude={"base_attendee_ids", "base_attendees_with_roles"})
    # Map evangelism_strategy_id -> estrategia_id.
    if data.get("evangelism_strategy_id") and not data.get("estrategia_id"):
        data["estrategia_id"] = data.pop("evangelism_strategy_id")
    # Infer sede_id from user if not provided in payload
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id
    if not str(data.get("code") or "").strip():
        base = (str(data.get("name") or data.get("address") or "FARO").strip().upper().replace(" ", "-"))[
            :12
        ]  # truncate to leave room for suffix
        suffix = _utcnow().strftime("%m%d%H%M")  # 8 chars
        data["code"] = f"{base}-{suffix}"[:30]
    if not str(data.get("name") or "").strip():
        fallback_name = str(data.get("address") or data["code"]).strip()
        data["name"] = f"Grupo pendiente - {fallback_name}"
    db_obj = models.GrupoEvangelismo(**data)
    db.add(db_obj)

    base_attendees_with_roles = getattr(payload, "base_attendees_with_roles", None)
    if base_attendees_with_roles is not None:
        db.flush()  # Get the ID without committing
        for item in base_attendees_with_roles:
            role, custom_role_id = _group_participant_role_values(item)
            attendee = models.ParticipanteGrupo(
                grupo_id=db_obj.id,
                persona_id=uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id,
                role=role,
                rol_personalizado_id=custom_role_id,
            )
            db.add(attendee)
    elif payload.base_attendee_ids:
        db.flush()  # Get the ID without committing
        for persona_id in payload.base_attendee_ids:
            attendee = models.ParticipanteGrupo(grupo_id=db_obj.id, persona_id=persona_id, role="asistente")
            db.add(attendee)

    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_grupo(db: Session, house_id: uuid.UUID) -> Optional[models.GrupoEvangelismo]:
    return db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()


def update_grupo(db: Session, house_id: uuid.UUID, payload: schemas.GrupoEvangelismoUpdate):
    house = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()
    if not house:
        return None

    update_data = payload.model_dump(
        exclude_unset=True,
        exclude={"base_attendee_ids", "base_attendees_with_roles"},
    )
    if "code" in update_data and not str(update_data["code"] or "").strip():
        update_data["code"] = house.code or f"FARO-{house.id}"
    for key, value in update_data.items():
        setattr(house, key, value)

    if payload.base_attendees_with_roles is not None:
        db.query(models.ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == house_id).update(
            {models.ParticipanteGrupo.deleted_at: _utcnow(), models.ParticipanteGrupo.activo: False},
            synchronize_session=False,
        )
        for item in payload.base_attendees_with_roles:
            role, custom_role_id = _group_participant_role_values(item)
            p_id = uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id
            existing = db.query(models.ParticipanteGrupo).filter(
                models.ParticipanteGrupo.grupo_id == house_id,
                models.ParticipanteGrupo.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = role
                existing.rol_personalizado_id = custom_role_id
            else:
                db.add(
                    models.ParticipanteGrupo(
                        grupo_id=house_id,
                        persona_id=p_id,
                        role=role,
                        rol_personalizado_id=custom_role_id,
                    )
                )
        # Sincronizar lider_persona_id, asistente_persona_id y anfitrion_persona_id desde los participantes.
        _SUBORDINATE_TOKENS = {"co", "colider", "colíder", "asistente", "del"}
        db.flush()

        new_leader_id = None
        new_assistant_id = None
        new_host_id = None

        for item in payload.base_attendees_with_roles:
            role_str = str(getattr(item, "role", "") or "").lower().strip()
            custom_id = getattr(item, "rol_personalizado_id", None)
            if role_str.startswith("custom:") and not custom_id:
                try:
                    custom_id = int(role_str.split(":", 1)[1])
                except (ValueError, TypeError):
                    pass
            if custom_id:
                custom_rol = db.query(models.RolPersonalizadoEstrategia).filter(
                    models.RolPersonalizadoEstrategia.id == custom_id
                ).first()
                role_str = (custom_rol.nombre_rol if custom_rol else role_str).lower().strip()

            # Normalizar para comparación
            role_norm = role_str.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            tokens = set(role_norm.replace("-", " ").replace("_", " ").split())

            is_leader = ("lider" in tokens or "leader" in tokens) and not (tokens & _SUBORDINATE_TOKENS)
            is_assistant = ("asistente" in tokens or "colider" in tokens or ("co" in tokens and ("lider" in tokens or "leader" in tokens)))
            is_host = "anfitrion" in tokens or "host" in tokens

            p_uuid = uuid.UUID(str(item.persona_id)) if isinstance(item.persona_id, str) else item.persona_id

            if is_leader and not new_leader_id:
                new_leader_id = p_uuid
            if is_assistant and not new_assistant_id:
                new_assistant_id = p_uuid
            if is_host and not new_host_id:
                new_host_id = p_uuid

        house.lider_persona_id = new_leader_id
        house.asistente_persona_id = new_assistant_id
        house.anfitrion_persona_id = new_host_id
    elif payload.base_attendee_ids is not None:
        db.query(models.ParticipanteGrupo).filter(models.ParticipanteGrupo.grupo_id == house_id).update(
            {models.ParticipanteGrupo.deleted_at: _utcnow(), models.ParticipanteGrupo.activo: False},
            synchronize_session=False,
        )
        for persona_id in payload.base_attendee_ids:
            p_id = uuid.UUID(str(persona_id)) if isinstance(persona_id, str) else persona_id
            existing = db.query(models.ParticipanteGrupo).filter(
                models.ParticipanteGrupo.grupo_id == house_id,
                models.ParticipanteGrupo.persona_id == p_id
            ).first()
            if existing:
                existing.deleted_at = None
                existing.activo = True
                existing.role = "miembro"
            else:
                db.add(
                    models.ParticipanteGrupo(
                        grupo_id=house_id,
                        persona_id=p_id,
                        role="miembro",
                    )
                )

    db.flush()
    house.personas_count = (
        db.query(models.ParticipanteGrupo)
        .filter(
            models.ParticipanteGrupo.grupo_id == house_id,
            models.ParticipanteGrupo.deleted_at.is_(None),
        )
        .count()
    )

    db.commit()
    db.refresh(house)
    return house


def delete_grupo(db: Session, house_id: uuid.UUID) -> bool:
    row = db.query(models.GrupoEvangelismo).filter(models.GrupoEvangelismo.id == house_id).first()
    if not row:
        return False
    row.deleted_at = _utcnow()
    db.commit()
    return True
