"""MCP privado para operaciones seguras de evangelismo.

La primera superficie operativa cubre eventos masivos, que se relacionan con
`CrmEvent` y `EventAttendance` directamente y no requieren grupos ni sesiones
de grupo. Todas las herramientas resuelven usuario, permiso y sede antes de
leer o mutar datos.
"""

from __future__ import annotations

import datetime
from typing import Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_

from backend import models, schemas
from backend.api.evangelism_shared import get_expected_personas_for_event, utc_now
from backend.core.cache_v2 import _to_jsonable
from backend.core.database import SessionLocal
from backend.core.tenant import require_user_sede_id
from backend.mcp_auth import authenticated_mcp_app, get_mcp_current_user, require_mcp_permission

mass_event_mcp = FastMCP(
    name="CCF Evangelismo",
    instructions=(
        "Opera únicamente datos de evangelismo de la sede del usuario autenticado. "
        "Los eventos masivos no usan grupos: su asistencia se registra directamente "
        "por evento y fecha. Nunca inventes personas, eventos o IDs."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


def _is_mass_event(event: models.CrmEvent) -> bool:
    settings = event.settings_json if isinstance(event.settings_json, dict) else {}
    return settings.get("strategy_typology") == "evento_masivo"


def _resolve_mass_event(db, user: models.Usuario, event_id: UUID) -> models.CrmEvent:
    sede_id = require_user_sede_id(db, user)
    event = (
        db.query(models.CrmEvent)
        .filter(
            models.CrmEvent.id == event_id,
            models.CrmEvent.sede_id == sede_id,
            models.CrmEvent.deleted_at.is_(None),
        )
        .first()
    )
    if not event:
        raise ValueError("Evento masivo no encontrado")
    if not _is_mass_event(event):
        raise ValueError("El evento no está asociado a una estrategia evento_masivo")
    return event


def _event_summary(event: models.CrmEvent) -> dict[str, Any]:
    settings = event.settings_json if isinstance(event.settings_json, dict) else {}
    return {
        "id": str(event.id),
        "name": event.name,
        "description": event.description,
        "event_date": event.event_date.isoformat() if event.event_date else None,
        "location": event.location,
        "status": event.status,
        "strategy_id": settings.get("evangelism_strategy_id"),
        "typology": settings.get("strategy_typology"),
        "uses_groups": False,
    }


@mass_event_mcp.tool()
def list_mass_events(limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Lista eventos masivos activos visibles en la sede del usuario."""
    safe_limit = max(1, min(int(limit), 100))
    safe_offset = max(0, int(offset))
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        sede_id = require_user_sede_id(db, user)
        # La tipología evento_masivo vive en settings_json (JSON, sin filtro SQL
        # portable), así que se escanean solo las columnas del summary con
        # yield_per: no se materializan todos los eventos de la sede en memoria.
        columns = (
            models.CrmEvent.id,
            models.CrmEvent.name,
            models.CrmEvent.description,
            models.CrmEvent.event_date,
            models.CrmEvent.location,
            models.CrmEvent.status,
            models.CrmEvent.settings_json,
        )
        rows = (
            db.query(*columns)
            .filter(
                models.CrmEvent.sede_id == sede_id,
                models.CrmEvent.deleted_at.is_(None),
            )
            .order_by(models.CrmEvent.event_date.desc().nullslast())
            .yield_per(500)
        )
        mass_events = [row for row in rows if _is_mass_event(row)]
        page = mass_events[safe_offset : safe_offset + safe_limit]
        return {"items": [_event_summary(event) for event in page], "total": len(mass_events)}
    finally:
        db.close()


@mass_event_mcp.tool()
def ensure_mass_event(strategy_id: UUID) -> dict[str, Any]:
    """Obtiene o crea de forma perezosa el evento de una estrategia masiva."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        sede_id = require_user_sede_id(db, user)
        strategy = (
            db.query(models.EstrategiaEvangelismo)
            .filter(
                models.EstrategiaEvangelismo.id == strategy_id,
                models.EstrategiaEvangelismo.sede_id == sede_id,
                models.EstrategiaEvangelismo.deleted_at.is_(None),
            )
            .first()
        )
        if not strategy:
            raise ValueError("Estrategia no encontrada")
        if strategy.typology != "evento_masivo":
            raise ValueError("La estrategia no es de tipología evento_masivo")

        # Mismo escaneo liviano que list_mass_events: solo las columnas del
        # summary (la tipología vive en settings_json, JSON sin filtro SQL
        # portable), en lugar de materializar todos los eventos de la sede.
        columns = (
            models.CrmEvent.id,
            models.CrmEvent.name,
            models.CrmEvent.description,
            models.CrmEvent.event_date,
            models.CrmEvent.location,
            models.CrmEvent.status,
            models.CrmEvent.settings_json,
        )
        event = next(
            (
                item
                for item in db.query(*columns)
                .filter(
                    models.CrmEvent.sede_id == sede_id,
                    models.CrmEvent.deleted_at.is_(None),
                )
                .order_by(models.CrmEvent.event_date.desc())
                .all()
                if (
                    isinstance(item.settings_json, dict)
                    and str(item.settings_json.get("evangelism_strategy_id") or "") == str(strategy_id)
                )
            ),
            None,
        )
        if event is None:
            event_date = strategy.fecha_inicio or utc_now()
            event = models.CrmEvent(
                sede_id=sede_id,
                name=strategy.nombre,
                description=strategy.descripcion,
                event_date=event_date,
                fixed_date=event_date,
                event_type="ONCE",
                status="SCHEDULED",
                target_audience="ALL",
                settings_json={
                    "evangelism_strategy_id": str(strategy.id),
                    "strategy_typology": "evento_masivo",
                },
            )
            db.add(event)
            db.commit()
            db.refresh(event)
        return _event_summary(event)
    finally:
        db.close()


@mass_event_mcp.tool()
def search_mass_event_people(event_id: UUID, query: str, limit: int = 50) -> dict[str, Any]:
    """Busca personas de la sede para seleccionar asistencia, sin exponer otras sedes."""
    term = query.strip()
    if len(term) < 2:
        return {"items": [], "total": 0, "message": "La búsqueda requiere al menos 2 caracteres."}
    safe_limit = max(1, min(int(limit), 100))
    pattern = f"%{term}%"
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        event = _resolve_mass_event(db, user, event_id)
        people = (
            db.query(models.Persona)
            .filter(
                models.Persona.sede_id == event.sede_id,
                or_(
                    models.Persona.first_name.ilike(pattern),
                    models.Persona.last_name.ilike(pattern),
                    models.Persona.nombre_completo.ilike(pattern),
                ),
            )
            .order_by(models.Persona.nombre_completo.asc())
            .limit(safe_limit)
            .all()
        )
        return {
            "items": [
                {
                    "persona_id": str(person.id),
                    "name": person.nombre_completo,
                    "church_role": person.church_role,
                    "email": person.email,
                    "phone": person.phone,
                }
                for person in people
            ],
            "total": len(people),
        }
    finally:
        db.close()


@mass_event_mcp.tool()
def get_mass_event_attendance(event_id: UUID, session_date: datetime.date) -> dict[str, Any]:
    """Consulta presentes y ausentes registrados para un evento masivo y fecha."""
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        event = _resolve_mass_event(db, user, event_id)
        rows = (
            db.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event.id,
                models.EventAttendance.session_date == session_date,
                models.EventAttendance.deleted_at.is_(None),
            )
            .join(models.Persona)
            .order_by(models.Persona.nombre_completo.asc())
            .all()
        )
        expected_personas = get_expected_personas_for_event(db, event)
        present = []
        absent_by_persona_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = {
                "persona_id": str(row.persona_id),
                "name": row.persona.nombre_completo if row.persona else "Sin nombre",
                "status": "present" if row.attended else "absent",
                "source": row.source,
                "check_in_at": row.check_in_at.isoformat() if row.check_in_at else None,
            }
            if row.attended:
                present.append(item)
            else:
                absent_by_persona_id[str(row.persona_id)] = item

        # En una lista masiva no es necesario crear una fila de ausencia para
        # cada persona. Completa el reporte desde la audiencia esperada para
        # que "ausente" también incluya a quien aún no tiene fila persistida.
        present_ids = {item["persona_id"] for item in present}
        for person in expected_personas:
            person_id = str(person.id)
            if person_id not in present_ids and person_id not in absent_by_persona_id:
                absent_by_persona_id[person_id] = {
                    "persona_id": person_id,
                    "name": person.nombre_completo,
                    "status": "absent",
                    "source": "not_recorded",
                    "check_in_at": None,
                }
        absent = sorted(absent_by_persona_id.values(), key=lambda item: item["name"])
        return {
            "event": _event_summary(event),
            "session_date": session_date.isoformat(),
            "counts": {"present": len(present), "absent": len(absent)},
            "expected_count": len(expected_personas),
            "present": present,
            "absent": absent,
        }
    finally:
        db.close()


@mass_event_mcp.tool()
def register_mass_event_attendance(
    event_id: UUID,
    session_date: datetime.date,
    persona_ids: list[UUID],
    allow_empty: bool = False,
) -> dict[str, Any]:
    """Registra asistencia masiva reemplazando el estado de esa fecha.

    `persona_ids` contiene los presentes; las filas existentes no incluidas se
    marcan ausentes. Una lista vacía requiere `allow_empty=true` para evitar
    que un agente marque accidentalmente a todo el evento como ausente.
    """
    if not persona_ids and not allow_empty:
        raise ValueError("persona_ids está vacío; confirme allow_empty=true para marcar todos ausentes")
    if len(persona_ids) > 2000:
        raise ValueError("El máximo permitido por operación MCP es 2000 personas")

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:edit")
        event = _resolve_mass_event(db, user, event_id)
        if str(event.status or "").upper() in {"CANCELLED", "CANCELED"}:
            raise ValueError("No se puede registrar asistencia en un evento cancelado")
        if event.attendance_closed_at is not None:
            raise ValueError("La asistencia de este evento ya fue cerrada")

        selected_ids = list(dict.fromkeys(persona_ids))
        valid_ids = {
            row[0]
            for row in db.query(models.Persona.id)
            .filter(
                models.Persona.id.in_(selected_ids),
                models.Persona.sede_id == event.sede_id,
            )
            .all()
        }
        invalid_ids = sorted(str(persona_id) for persona_id in set(selected_ids) - valid_ids)
        if invalid_ids:
            return {
                "status": "rejected",
                "reason": "Hay personas inexistentes o fuera de la sede del evento",
                "invalid_persona_ids": invalid_ids,
                "recorded": 0,
            }

        # Se consultan TODAS las filas de la fecha (incluidas las soft-deleted):
        # la UniqueConstraint(event_id, session_date, persona_id) no considera
        # deleted_at, así que una fila soft-deleted debe reutilizarse/reactivarse
        # en lugar de insertar un duplicado (mismo patrón que el REST
        # register_bulk_attendance).
        existing_rows = (
            db.query(models.EventAttendance)
            .filter(
                models.EventAttendance.event_id == event.id,
                models.EventAttendance.session_date == session_date,
            )
            .all()
        )
        existing_by_persona_id = {row.persona_id: row for row in existing_rows}
        now = utc_now()
        created = 0
        marked_present = 0
        marked_absent = 0

        for persona_id in selected_ids:
            row = existing_by_persona_id.get(persona_id)
            if row is None:
                db.add(
                    models.EventAttendance(
                        event_id=event.id,
                        session_date=session_date,
                        persona_id=persona_id,
                        attended=True,
                        status="present",
                        source="mcp",
                        scanned_at=now,
                        check_in_at=now,
                    )
                )
                created += 1
            else:
                was_present = bool(row.attended)
                row.attended = True
                row.status = "present"
                row.source = "mcp"
                row.scanned_at = now
                row.check_in_at = now
                row.check_out_at = None
                if row.deleted_at is not None:
                    # Reactivar fila soft-deleted en vez de insertar un
                    # duplicado (UniqueConstraint sin deleted_at).
                    row.deleted_at = None
                if not was_present:
                    marked_present += 1

        selected_set = set(selected_ids)
        for row in existing_rows:
            if row.persona_id in selected_set:
                continue
            if row.deleted_at is not None:
                # Fila soft-deleted no seleccionada: no revivirla como ausente.
                continue
            if row.attended or row.status != "absent":
                row.attended = False
                row.status = "absent"
                row.check_out_at = now
                marked_absent += 1

        db.commit()
        return {
            "status": "success",
            "event_id": str(event.id),
            "session_date": session_date.isoformat(),
            "recorded": len(selected_ids),
            "created": created,
            "marked_present": marked_present,
            "marked_absent": marked_absent,
            "invalid_persona_ids": [],
        }
    finally:
        db.close()


def _parse_datetime(value: str | None) -> datetime.datetime | None:
    if value is None or not str(value).strip():
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Fecha inválida; use ISO-8601") from exc


def _call_with_db(operation, db, user, *args, user_parameter="current_user", **kwargs):
    """Invoca un handler REST con sus dependencias ya resueltas."""
    kwargs[user_parameter] = user
    return operation(*args, db=db, **kwargs)


@mass_event_mcp.tool()
def list_evangelism_strategies(limit: int = 100, offset: int = 0, typology: str | None = None) -> dict[str, Any]:
    """Lista estrategias de evangelismo activas de la sede del usuario."""
    from backend.api.evangelism_main import main_estrategias

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        rows = _call_with_db(
            main_estrategias.read_evangelism_strategies,
            db,
            user,
            skip=max(0, int(offset)),
            limit=max(1, min(int(limit), 200)),
            activa=True,
            clase_raiz=typology,
            sede_id=None,
            user_parameter="_user",
        )
        return {"items": _to_jsonable(rows), "count": len(rows)}
    finally:
        db.close()


@mass_event_mcp.tool()
def get_evangelism_strategy(strategy_id: UUID) -> dict[str, Any]:
    """Obtiene el detalle de una estrategia de evangelismo dentro de la sede."""
    from backend.api.evangelism_main import main_estrategias

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        return _to_jsonable(
            _call_with_db(main_estrategias.read_strategy, db, user, strategy_id, user_parameter="_user")
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def create_evangelism_strategy(
    name: str,
    typology: str = "relacional",
    description: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    recurrence: str | None = None,
    day_of_week: str | None = None,
    start_time: str | None = None,
    event_format: str | None = None,
    phases: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Crea una estrategia de evangelismo con sede y auditoría del backend."""
    from backend.api.evangelism_main import main_estrategias

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.EstrategiaEvangelismoCreate(
            name=name,
            description=description,
            typology=typology,
            clase_raiz=typology,
            start_date=_parse_datetime(start_date),
            end_date=_parse_datetime(end_date),
            recurrence=recurrence,
            day_of_week=day_of_week,
            start_time=start_time,
            event_format=event_format,
            phases=phases,
        )
        return _to_jsonable(_call_with_db(main_estrategias.create_strategy, db, user, strategy=payload))
    finally:
        db.close()


@mass_event_mcp.tool()
def update_evangelism_strategy(strategy_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza campos permitidos de una estrategia dentro de la sede."""
    from backend.api.evangelism_main import main_estrategias

    allowed = {
        "name",
        "description",
        "clase_raiz",
        "activa",
        "typology",
        "recurrence",
        "day_of_week",
        "start_time",
        "event_format",
        "phases",
        "niche_objective",
        "strategy_type",
        "status",
        "default_role_id",
        "start_date",
        "end_date",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    for field in ("start_date", "end_date"):
        if field in clean:
            clean[field] = _parse_datetime(clean[field])
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.EstrategiaEvangelismoUpdate(**clean)
        return _to_jsonable(
            _call_with_db(
                main_estrategias.update_strategy,
                db,
                user,
                strategy_id,
                strategy=payload,
                user_parameter="_user",
            )
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def archive_evangelism_strategy(strategy_id: UUID) -> dict[str, Any]:
    """Archiva lógicamente una estrategia de evangelismo."""
    from backend.api.evangelism_main import main_estrategias

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        _call_with_db(main_estrategias.delete_strategy, db, user, strategy_id, user_parameter="_user")
        return {"status": "archived", "strategy_id": str(strategy_id)}
    finally:
        db.close()


@mass_event_mcp.tool()
def list_evangelism_strategy_roles(strategy_id: UUID) -> dict[str, Any]:
    """Lista roles personalizados de una estrategia de evangelismo."""
    from backend.api.evangelism_main import main_roles

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        rows = _call_with_db(
            main_roles.list_strategy_roles,
            db,
            user,
            strategy_id,
            user_parameter="_user",
        )
        return {"items": _to_jsonable(rows), "count": len(rows)}
    finally:
        db.close()


@mass_event_mcp.tool()
def create_evangelism_strategy_role(
    strategy_id: UUID,
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Crea un rol personalizado dentro de una estrategia."""
    from backend.api.evangelism_main import main_roles

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.RolPersonalizadoEstrategiaCreate(nombre_rol=name, descripcion=description)
        return _to_jsonable(
            _call_with_db(
                main_roles.create_strategy_role,
                db,
                user,
                strategy_id,
                payload=payload,
                user_parameter="_user",
            )
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def update_evangelism_strategy_role(
    strategy_id: UUID,
    role_id: UUID,
    changes: dict[str, Any],
) -> dict[str, Any]:
    """Actualiza el nombre o descripción de un rol de estrategia."""
    from backend.api.evangelism_main import main_roles

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.RolPersonalizadoEstrategiaUpdate(
            **{key: value for key, value in changes.items() if key in {"nombre_rol", "descripcion"}}
        )
        return _to_jsonable(
            _call_with_db(
                main_roles.update_strategy_role,
                db,
                user,
                strategy_id,
                role_id,
                payload=payload,
                user_parameter="_user",
            )
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def archive_evangelism_strategy_role(strategy_id: UUID, role_id: UUID) -> dict[str, Any]:
    """Archiva un rol personalizado de una estrategia."""
    from backend.api.evangelism_main import main_roles

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        result = _call_with_db(
            main_roles.delete_strategy_role,
            db,
            user,
            strategy_id,
            role_id,
            user_parameter="_user",
        )
        return _to_jsonable(result)
    finally:
        db.close()


@mass_event_mcp.tool()
def list_evangelism_groups(strategy_id: UUID | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    """Lista grupos de evangelismo visibles en la sede."""
    from backend.api.evangelism_grupos import grupos_main

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        rows = _call_with_db(
            grupos_main.list_grupos,
            db,
            user,
            evangelism_strategy_id=strategy_id,
            skip=max(0, int(offset)),
            limit=max(1, min(int(limit), 500)),
        )
        return {"items": _to_jsonable(rows), "count": len(rows)}
    finally:
        db.close()


@mass_event_mcp.tool()
def get_evangelism_group(group_id: UUID) -> dict[str, Any]:
    """Obtiene un grupo, participantes, sesiones y alertas de asistencia."""
    from backend.api.evangelism_grupos import grupos_main

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        return _to_jsonable(_call_with_db(grupos_main.get_grupo, db, user, group_id))
    finally:
        db.close()


@mass_event_mcp.tool()
async def create_evangelism_group(
    name: str,
    strategy_id: UUID | None = None,
    leader_id: UUID | None = None,
    assistant_id: UUID | None = None,
    host_id: UUID | None = None,
    capacity: int = 15,
    zone: str | None = None,
    address: str | None = None,
    day_of_week: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    attendee_ids: list[UUID] | None = None,
) -> dict[str, Any]:
    """Crea un grupo y valida que sus personas pertenezcan a la sede."""
    from backend.api.evangelism_grupos import grupos_main

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.GrupoEvangelismoCreate(
            name=name,
            evangelism_strategy_id=strategy_id,
            leader_id=leader_id,
            assistant_id=assistant_id,
            host_id=host_id,
            capacity=max(1, min(int(capacity), 1000)),
            zone=zone,
            address=address,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            base_attendee_ids=attendee_ids or [],
        )
        result = await _call_with_db(grupos_main.create_grupo, db, user, payload=payload)
        return _to_jsonable(result)
    finally:
        db.close()


@mass_event_mcp.tool()
def update_evangelism_group(group_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza un grupo y sus participantes dentro de la sede."""
    from backend.api.evangelism_grupos import grupos_main

    allowed = {
        "code",
        "name",
        "zone",
        "address",
        "leader_id",
        "assistant_id",
        "host_id",
        "capacity",
        "status",
        "day_of_week",
        "start_time",
        "end_time",
        "base_attendee_ids",
        "base_attendees_with_roles",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.GrupoEvangelismoUpdate(**clean)
        return _to_jsonable(_call_with_db(grupos_main.update_grupo, db, user, group_id, payload=payload))
    finally:
        db.close()


@mass_event_mcp.tool()
def archive_evangelism_group(group_id: UUID) -> dict[str, Any]:
    """Archiva un grupo de evangelismo sin eliminar su historial."""
    from backend.api.evangelism_grupos import grupos_main

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        _call_with_db(grupos_main.delete_grupo, db, user, group_id)
        return {"status": "archived", "group_id": str(group_id)}
    finally:
        db.close()


@mass_event_mcp.tool()
def list_evangelism_sessions(strategy_id: UUID | None = None, group_id: UUID | None = None) -> dict[str, Any]:
    """Lista sesiones de grupos dentro de la sede del usuario."""
    from backend.api.evangelism_grupos import grupos_sesiones

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        rows = _call_with_db(
            grupos_sesiones.list_sessions,
            db,
            user,
            strategy_id=strategy_id,
            house_id=group_id,
        )
        return {"items": _to_jsonable(rows), "count": len(rows)}
    finally:
        db.close()


@mass_event_mcp.tool()
def create_evangelism_session(
    group_id: UUID,
    session_date: str,
    topic: str | None = None,
    status: str = "Realizada",
    report_notes: str | None = None,
) -> dict[str, Any]:
    """Crea una sesión de grupo dentro de la sede."""
    from backend.api.evangelism_grupos import grupos_sesiones

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.SesionGrupoCreate(
            grupo_id=group_id,
            session_date=datetime.datetime.fromisoformat(session_date.replace("Z", "+00:00")),
            topic=topic,
            status=status,
            report_notes=report_notes,
        )
        return _to_jsonable(_call_with_db(grupos_sesiones.create_session, db, user, data=payload))
    finally:
        db.close()


@mass_event_mcp.tool()
def update_evangelism_session(session_id: UUID, changes: dict[str, Any]) -> dict[str, Any]:
    """Actualiza una sesión de grupo."""
    from backend.api.evangelism_grupos import grupos_sesiones

    allowed = {
        "session_date",
        "topic",
        "offering_amount",
        "report_notes",
        "novelty_type",
        "novelty_detail",
        "cancellation_reason",
        "reported_by_persona_id",
        "report_deadline",
        "status",
    }
    clean = {key: value for key, value in changes.items() if key in allowed}
    for field in ("session_date", "report_deadline"):
        if isinstance(clean.get(field), str):
            clean[field] = datetime.datetime.fromisoformat(clean[field].replace("Z", "+00:00"))
    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        payload = schemas.SesionGrupoUpdate(**clean)
        return _to_jsonable(
            _call_with_db(grupos_sesiones.update_session, db, user, session_id, update=payload)
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def archive_evangelism_session(session_id: UUID) -> dict[str, Any]:
    """Archiva una sesión de grupo manteniendo su historial."""
    from backend.api.evangelism_grupos import grupos_sesiones

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        _call_with_db(grupos_sesiones.delete_session, db, user, session_id)
        return {"status": "archived", "session_id": str(session_id)}
    finally:
        db.close()


@mass_event_mcp.tool()
def toggle_evangelism_session(
    session_id: UUID,
    action: str,
) -> dict[str, Any]:
    """Habilita, deshabilita o cierra una sesión para reportar asistencia."""
    from backend.api.evangelism_grupos import grupos_sesiones

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:manage")
        return _to_jsonable(
            _call_with_db(
                grupos_sesiones.toggle_session_habilitacion,
                db,
                user,
                session_id,
                payload={"accion": action},
            )
        )
    finally:
        db.close()


@mass_event_mcp.tool()
def get_evangelism_session(session_id: UUID) -> dict[str, Any]:
    """Obtiene una sesión de grupo y sus registros de asistencia."""
    from backend.api.evangelism_grupos import grupos_sesiones

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:read")
        return _to_jsonable(_call_with_db(grupos_sesiones.get_session_detail, db, user, session_id))
    finally:
        db.close()


@mass_event_mcp.tool()
def register_evangelism_group_attendance(
    session_id: UUID,
    attendance: list[dict[str, Any]],
) -> dict[str, Any]:
    """Registra asistencia de una sesión relacional habilitada."""
    from backend.api.evangelism_grupos import grupos_asistencias

    db = SessionLocal()
    try:
        user = get_mcp_current_user(db)
        require_mcp_permission(db, user, "evangelism:edit")
        payload = [schemas.AsistenciaGrupoCreate(**item) for item in attendance]
        result = _call_with_db(grupos_asistencias.submit_attendance, db, user, session_id, payload)
        return _to_jsonable(result)
    finally:
        db.close()


mass_event_mcp_app = authenticated_mcp_app(mass_event_mcp)
