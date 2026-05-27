"""⚠️ DEPRECADO — Este archivo está obsoleto y NO se importa en ningún módulo.

Los modelos canónicos están en models_evangelism.py y models_crm.py.
Este archivo se conserva solo como referencia histórica.
No agregar nuevos modelos aquí — usar models_evangelism.py.

Modelos originales (todos reemplazados):
- Sedes (multi-tenant)
- Categorías de estrategia
- Log de auditoría con JSONB
- Historial de embudo (velocidad ministerial)
- Vistas materializadas OLAP
"""

from __future__ import annotations

import enum

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, JSON)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.core.database import Base
from backend.models_shared import _utcnow


# ──────────────────────────────────────────────
# ENUMS SUPER PRO
# ──────────────────────────────────────────────

class RolEnGrupoSuperEnum(str, enum.Enum):
    """Roles dentro de un grupo (propuesta del usuario)."""
    LIDER = "LIDER"
    COLIDER = "COLIDER"
    ANFITRION = "ANFITRION"
    ASISTENTE = "ASISTENTE"
    INVITADO = "INVITADO"
    PERSONALIZADO = "PERSONALIZADO"


class EstadoAsistenciaSuperEnum(str, enum.Enum):
    """Estado de asistencia (propuesta del usuario)."""
    ASISTIO = "ASISTIO"
    FALTO = "FALTO"
    EXCUSA = "EXCUSA"


class TipoSeguimientoSuperEnum(str, enum.Enum):
    """Tipo de seguimiento (propuesta del usuario)."""
    LLAMADA = "LLAMADA"
    MENSAJE_WHATSAPP = "MENSAJE_WHATSAPP"
    VISITA_PRESENCIAL = "VISITA_PRESENCIAL"
    ORACION = "ORACION"


class FrecuenciaEnum(str, enum.Enum):
    """Frecuencia de reunión."""
    SEMANAL = "SEMANAL"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"
    EVENTO_UNICO = "EVENTO_UNICO"


class EstadoSesionEnum(str, enum.Enum):
    """Estado de una sesión."""
    PENDIENTE = "PENDIENTE"
    REALIZADA = "REALIZADA"
    CANCELADA = "CANCELADA"


# ──────────────────────────────────────────────
# 1. MULTI-TENANT
# ──────────────────────────────────────────────

class Sede(Base):
    """Campus/sedes de la CCF para soporte multi-tenant."""

    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)  # Ej: "Sede Principal"
    ciudad = Column(String(100), nullable=False)
    es_activa = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow)

    estrategias = relationship("EstrategiaEvangelismo", back_populates="sede")
    grupos = relationship("GrupoEvangelismoSuper", back_populates="sede")


# ──────────────────────────────────────────────
# 2. AUDITORÍA CON JSONB
# ──────────────────────────────────────────────

class LogAuditoria(Base):
    """Trazabilidad absoluta — registra cada mutación crítica.
    
    Usa JSONB de PostgreSQL para guardar el "antes" y "después" 
    permitiendo deshacer cambios.
    """

    __tablename__ = "logs_auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tabla_afectada = Column(String(50), nullable=False, index=True)  # Ej: "asistencias"
    registro_id = Column(String(50), nullable=False)  # El ID alterado
    accion = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE

    # JSONB permite guardar el "antes" y "después" para deshacer cambios
    detalles_cambio = Column(JSON, nullable=True)

    usuario_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Quien ejecutó
    fecha_accion = Column(DateTime, default=_utcnow, index=True)


# ──────────────────────────────────────────────
# 3. CONFIGURACIÓN DINÁMICA
# ──────────────────────────────────────────────

class CategoriaEstrategia(Base):
    """Categorías configurables para estrategias de evangelismo."""

    __tablename__ = "categorias_estrategia"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(String(255), nullable=True)
    es_del_sistema = Column(Boolean, default=False)
    activa = Column(Boolean, default=True, index=True)

    estrategias = relationship("EstrategiaEvangelismo", back_populates="categoria")


# ──────────────────────────────────────────────
# 4. CORE EVANGELISMO (propuesta del usuario)
# ──────────────────────────────────────────────

class EstrategiaEvangelismo(Base):
    """Estrategia de evangelismo con soporte multi-tenant.
    
    NOTA: Coexiste con EvangelismStrategy existente.
    Esta es la versión nueva con FK a sedes y categorias.
    """

    __tablename__ = "estrategias_evangelismo_super"

    id = Column(String(20), primary_key=True)  # Ej: "FARO-001"
    nombre = Column(String(200), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_estrategia.id"), nullable=False, index=True)

    # MULTI-TENANT
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False, index=True)

    fecha_creacion = Column(DateTime, default=_utcnow)
    frecuencia = Column(String(20), nullable=True)  # FrecuenciaEnum
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    activa = Column(Boolean, default=True, index=True)

    categoria = relationship("CategoriaEstrategia", back_populates="estrategias")
    sede = relationship("Sede", back_populates="estrategias")
    grupos = relationship("GrupoEvangelismoSuper", back_populates="estrategia")


class GrupoEvangelismoSuper(Base):
    """Grupo de evangelismo con geolocalización y multi-tenant."""

    __tablename__ = "grupos_evangelismo_super"

    id = Column(Integer, primary_key=True, autoincrement=True)
    estrategia_id = Column(String(20), ForeignKey("estrategias_evangelismo_super.id"), nullable=False, index=True)

    # MULTI-TENANT
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False, index=True)

    nombre = Column(String(200), nullable=False)
    ubicacion = Column(String(255), nullable=True)

    # GEOLOCALIZACIÓN
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)

    dia_reunion = Column(String(20), nullable=True)
    hora_reunion = Column(String(10), nullable=True)
    activo = Column(Boolean, default=True, index=True)

    estrategia = relationship("EstrategiaEvangelismo", back_populates="grupos")
    sede = relationship("Sede", back_populates="grupos")


# ──────────────────────────────────────────────
# 5. VELOCIDAD DEL EMBUDO
# ──────────────────────────────────────────────

class HistorialEmbudo(Base):
    """Motor de Velocidad Ministerial.
    
    Mide cuánto tarda una persona en avanzar en el embudo.
    Ej: ¿Cuántos días pasaron desde VISITANTE hasta BAUTIZADO?
    """

    __tablename__ = "historial_embudo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id"),
        nullable=False,
        index=True,
    )

    rol_anterior = Column(String(50), nullable=True)
    rol_nuevo = Column(String(50), nullable=False)

    fecha_cambio = Column(DateTime, default=_utcnow, index=True)
    dias_en_estado_anterior = Column(Integer, nullable=True)  # La métrica dorada


# ──────────────────────────────────────────────
# 6. VISTAS MATERIALIZADAS (DDL)
# ──────────────────────────────────────────────

MV_RESUMEN_ASISTENCIA_DDL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_resumen_asistencia AS
SELECT 
    g.evangelism_strategy_id as estrategia_id,
    DATE_TRUNC('month', ghss.session_date) as mes,
    COUNT(gha.id) FILTER (WHERE gha.attended = TRUE) as total_asistencias,
    COUNT(gha.id) FILTER (WHERE gha.attended = FALSE) as total_faltas,
    COUNT(gha.id) FILTER (WHERE gha.status = 'first_time' OR gha.es_primera_vez = TRUE) as total_nuevos
FROM cell_group_sessions ghss
JOIN cell_group_attendance gha ON ghss.id = gha.session_id
JOIN cell_groups g ON ghss.cell_group_id = g.id
GROUP BY g.evangelism_strategy_id, DATE_TRUNC('month', ghss.session_date);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_resumen_asistencia 
ON mv_resumen_asistencia(estrategia_id, mes);
"""

MV_VELOCIDAD_EMBUDO_DDL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_velocidad_embudo AS
SELECT 
    he.persona_id,
    he.rol_anterior,
    he.rol_nuevo,
    he.dias_en_estado_anterior,
    he.fecha_cambio
FROM historial_embudo he
WHERE he.dias_en_estado_anterior IS NOT NULL
ORDER BY he.fecha_cambio DESC;

CREATE INDEX IF NOT EXISTS idx_mv_velocidad_persona 
ON mv_velocidad_embudo(persona_id);
"""


def register_materialized_views():
    """Registra las vistas materializadas en el sistema de eventos."""
    pass  # Se ejecutan vía Alembic, no al startup
