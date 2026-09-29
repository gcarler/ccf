"""Endpoints públicos de Evangelismo para el portal CCF.

Ticket TKT-CMS-BACKEND-EVENTS-02:
  - GET  /api/evangelism/public/upcoming-events
        Feed unificado de reuniones públicas (estrategias activas marcadas
        ``is_public``) enriquecido para el frontend público:
        ``sede_nombre``, ``direccion``, ``imagen_url``, ``next_datetime``
        (UTC aware), ``hora_formateada`` y ``permite_registro``.
  - POST /api/evangelism/public/strategies/{estrategia_id}/register
        Pre-registro de visitantes desde el portal público. Resuelve la
        Persona canónica (Axioma 1: ``personas.id`` es la única identidad
        de seres humanos — nunca se crean tablas paralelas de personas) y
        registra la confirmación de asistencia en ``asistencias`` sobre la
        próxima sesión calculada (idempotente: una confirmación por
        persona y sesión).

Los endpoints públicos NO exponen datos de otras sedes: el feed muestra
estrategias marcadas explícitamente como públicas y el pre-registro fija
``Persona.sede_id`` desde la ``EstrategiaEvangelismo`` del servidor (Axioma
3: el scope de tenant nunca proviene del cliente).
"""

from __future__ import annotations

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import require_evangelism_manage
from backend.core.tenant import require_user_sede_id
from backend.models_evangelism import EstadoAsistenciaEnum, EstrategiaEvangelismo

router = APIRouter(prefix="", tags=["Evangelism Public"])

DIAS_SEMANA = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
}

def get_next_occurrence(dia_str, hora_str):
    """Próxima ocurrencia (UTC aware) del par día/hora semanal.

    Devuelve ``None`` ante entradas inválidas (día desconocido, hora mal
    formada) para no romper el feed público.
    """
    if not dia_str or not hora_str:
        return None
    try:
        dia_idx = DIAS_SEMANA.get(str(dia_str).lower().strip())
        if dia_idx is None:
            return None

        hh_str, mm_str = str(hora_str).split(":")
        hh = int(hh_str)
        mm = int(mm_str)
        now = datetime.datetime.now(datetime.timezone.utc)

        days_ahead = dia_idx - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and (now.hour > hh or (now.hour == hh and now.minute >= mm))):
            days_ahead += 7

        next_date = now + datetime.timedelta(days=days_ahead)
        next_dt = next_date.replace(hour=hh, minute=mm, second=0, microsecond=0)
        return next_dt
    except Exception:
        return None


def _hora_formateada(hora_str: Optional[str]) -> Optional[str]:
    """Normaliza ``HH:MM(:SS)`` a ``HH:MM`` para el portal público."""
    if not hora_str:
        return None
    try:
        hh_str, mm_str = str(hora_str).split(":")[:2]
        return f"{int(hh_str):02d}:{int(mm_str):02d}"
    except (ValueError, AttributeError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# GET /public/upcoming-events — feed unificado para el portal
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/public/upcoming-events")
def get_upcoming_public_events(db: Session = Depends(get_db)):
    """Feed público de reuniones/enventos próximos (estrategias publicadas).

    Campos por ítem:
      - ``id``, ``nombre``, ``slug``, ``typology``, ``categoria_pastoral``,
        ``descripcion``, ``dia_reunion``, ``hora_reunion``,
        ``hora_formateada``.
      - ``next_datetime`` (ISO-8601 UTC aware) y ``next_date`` (YYYY-MM-DD).
      - ``sede`` (``{id, nombre, ciudad}``) y ``sede_nombre`` (shorthand).
      - ``direccion`` (dirección del grupo base de la estrategia; fallback
        ``ubicacion``) y ``lugar`` (compuesto para el portal).
      - ``imagen_url`` (definida a nivel de estrategia) y ``permite_registro``
        (True si la estrategia acepta pre-registro público).
    """
    estrategias = (
        db.query(EstrategiaEvangelismo)
        .filter(
            EstrategiaEvangelismo.is_public.is_(True),
            EstrategiaEvangelismo.activa.is_(True),
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .all()
    )

    events = []
    for est in estrategias:
        next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)
        if not next_dt:
            # Sin día/hora válidos no hay próxima reunión computable.
            continue

        sede = est.sede
        grupo_base = est.grupos[0] if est.grupos else None
        direccion = getattr(grupo_base, "direccion", None) or getattr(grupo_base, "ubicacion", None)
        sede_nombre = getattr(sede, "nombre", None)

        events.append(
            {
                "id": str(est.id),
                "nombre": est.nombre,
                "slug": getattr(est, "codigo", None) or str(est.id),
                "typology": est.typology,
                "categoria_pastoral": est.strategy_type,
                "descripcion": est.descripcion,
                "dia_reunion": est.dia_reunion,
                "hora_reunion": est.hora_reunion,
                "hora_formateada": _hora_formateada(est.hora_reunion),
                "next_datetime": next_dt.isoformat(),
                "next_date": next_dt.strftime("%Y-%m-%d"),
                "sede": (
                    {"id": str(sede.id), "nombre": sede.nombre, "ciudad": sede.ciudad}
                    if sede is not None
                    else None
                ),
                "sede_nombre": sede_nombre,
                "direccion": direccion,
                "lugar": ", ".join(part for part in [direccion, sede_nombre] if part) or None,
                "imagen_url": getattr(est, "imagen_url", None),
                "permite_registro": True,
            }
        )

    events.sort(key=lambda item: item["next_datetime"])
    return events


# ─────────────────────────────────────────────────────────────────────────────
# POST /public/strategies/{id}/register — pre-registro de visitantes (Axioma 1)
# ─────────────────────────────────────────────────────────────────────────────


class PublicStrategyRegisterPayload(BaseModel):
    """Payload nominal del drawer de pre-registro del portal público."""

    nombre: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    asistentes_count: int = 1
    peticion_oracion: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def _nombre_no_vacio(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El nombre es obligatorio")
        return value.strip()


def _split_nombre(nombre_completo: str) -> tuple[str, str]:
    """Divide el nombre completo del portal en (first_name, last_name).

    Axioma 1: ``personas`` exige ``first_name``/``last_name`` NOT NULL; el
    portal solo captura un campo ``nombre``, por lo que la última palabra
    pasa a apellido y el resto a nombres.
    """
    parts = nombre_completo.strip().split()
    if len(parts) == 1:
        return parts[0], "-"
    return " ".join(parts[:-1]), parts[-1]


def _next_session_or_404(db: Session, est: EstrategiaEvangelismo) -> datetime.datetime:
    next_dt = get_next_occurrence(est.dia_reunion, est.hora_reunion)
    if not next_dt:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La estrategia no tiene una próxima reunión computable",
        )
    return next_dt


@router.post("/public/strategies/{estrategia_id}/register")
def public_register_for_strategy(
    estrategia_id: str,
    payload: PublicStrategyRegisterPayload,
    db: Session = Depends(get_db),
):
    """Pre-registro público de un visitante a una estrategia publicada.

    Axioma 1 (Kernel de Personas): busca la Persona canónica por email
    (prioritario) o teléfono; si no existe la crea con rol ``Visitante`` y
    estado espiritual ``Nuevo``. Nunca se escriben tablas paralelas de
    personas.

    Axioma 3: la sede del visitante se hereda de la estrategia del
    servidor (``estrategia.sede_id``); el cliente no envía sede.

    Confirma asistencia (``asistencias``) sobre la próxima sesión calculada
    de forma idempotente: un registro por (sesión, persona).
    """
    est = (
        db.query(EstrategiaEvangelismo)
        .filter(
            EstrategiaEvangelismo.id == estrategia_id,
            EstrategiaEvangelismo.is_public.is_(True),
            EstrategiaEvangelismo.activa.is_(True),
            EstrategiaEvangelismo.deleted_at.is_(None),
        )
        .first()
    )
    if not est:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estrategia no encontrada o no disponible para registro público",
        )

    next_dt = _next_session_or_404(db, est)

    email = (payload.email or "").strip() or None
    telefono = (payload.telefono or "").strip() or None
    if not email and not telefono:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe proporcionar email o teléfono de contacto",
        )

    first_name, last_name = _split_nombre(payload.nombre)

    # ── Axioma 1: resolver la Persona canónica ────────────────────────────
    persona = None
    if email:
        persona = db.query(models.Persona).filter(models.Persona.email == email).first()
    if persona is None and telefono:
        persona = db.query(models.Persona).filter(models.Persona.phone == telefono).first()

    created_persona = False
    if persona is None:
        persona = models.Persona(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=telefono,
            sede_id=est.sede_id,
            church_role="Visitante",
            spiritual_status="Nuevo",
        )
        db.add(persona)
        db.flush()
        created_persona = True

    # ── Confirmación de asistencia idempotente ────────────────────────────
    # Aislamiento multi-tenant: solo sesiones de la sede de la estrategia.
    sesion = (
        db.query(models.SesionGrupo)
        .join(models.GrupoEvangelismo, models.SesionGrupo.grupo_id == models.GrupoEvangelismo.id)
        .filter(
            models.GrupoEvangelismo.estrategia_id == est.id,
            models.GrupoEvangelismo.sede_id == est.sede_id,
            models.SesionGrupo.fecha_sesion == next_dt,
            models.SesionGrupo.deleted_at.is_(None),
        )
        .first()
    )
    if sesion is not None:
        asistio = (
            db.query(models.Asistencia)
            .filter(
                models.Asistencia.sesion_id == sesion.id,
                models.Asistencia.persona_id == persona.id,
                models.Asistencia.deleted_at.is_(None),
            )
            .first()
        )
        if asistio is None:
            db.add(
                models.Asistencia(
                    sesion_id=sesion.id,
                    persona_id=persona.id,
                    estado=EstadoAsistenciaEnum.ASISTIO.value,
                    es_primera_vez=True,
                )
            )

    db.commit()

    return {
        "ok": True,
        "message": "Asistencia confirmada con éxito",
        "estrategia_id": str(est.id),
        "persona_id": str(persona.id),
        "persona_created": created_persona,
        "sede_id": str(est.sede_id),
        "next_datetime": next_dt.isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints autenticados (config pública de estrategias) — sin cambios
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/strategies/public-config")
def get_public_strategies_config(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    user_sede_id = require_user_sede_id(db, current_user)
    estrategias = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.sede_id == user_sede_id,
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).order_by(EstrategiaEvangelismo.nombre).all()

    return [
        {
            "id": str(est.id),
            "nombre": est.nombre,
            "typology": est.typology,
            "dia_reunion": est.dia_reunion,
            "hora_reunion": est.hora_reunion,
            "is_public": est.is_public
        }
        for est in estrategias
    ]


class TogglePublicPayload(BaseModel):
    is_public: bool


@router.patch("/strategies/{estrategia_id}/toggle-public")
def toggle_public_strategy(
    estrategia_id: str,
    payload: TogglePublicPayload,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_evangelism_manage),
):
    user_sede_id = require_user_sede_id(db, current_user)
    est = db.query(EstrategiaEvangelismo).filter(
        EstrategiaEvangelismo.id == estrategia_id,
        EstrategiaEvangelismo.sede_id == user_sede_id,
        EstrategiaEvangelismo.deleted_at.is_(None)
    ).first()
    if not est:
        raise HTTPException(status_code=404, detail="Estrategia no encontrada")

    est.is_public = payload.is_public
    db.commit()

    return {"id": str(est.id), "is_public": est.is_public}
