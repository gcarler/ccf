#!/usr/bin/env python3
"""
scripts/migrate_compat_to_v2.py
Migración de datos Compat → v2 para la plataforma CCF.

Tablas soportadas:
  projects          → proyectos
  courses           → academy_courses
  enrollments       → academy_enrollments
  users             → auth_users
  roles             → auth_roles
  consolidation_cases → crm_casos
  cell_groups       → grupos_evangelismo  (nota: user pidió crm_celulas, no existe)
  cell_group_sessions → sesiones_grupo    (nota: user pidió crm_sesiones, no existe)
  agenda_events     → eventos_agenda

Uso:
    export DATABASE_URL="postgresql://user:pass@host:5432/db"
    export DEFAULT_SEDE_ID="<uuid-sede>"
    ./scripts/migrate_compat_to_v2.py [--dry-run] [--batch-size 1000]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL")
DEFAULT_SEDE_ID = os.getenv("DEFAULT_SEDE_ID", "00000000-0000-0000-0000-000000000001")
DEFAULT_PERSONA_ID = os.getenv("DEFAULT_PERSONA_ID", "00000000-0000-0000-0000-000000000001")
DEFAULT_PIPELINE_NAME = os.getenv("DEFAULT_PIPELINE_NAME", "NUEVOS_VISITANTES")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("migrate_compat_to_v2")


# ═══════════════════════════════════════════════════════════════════
# REPORTE
# ═══════════════════════════════════════════════════════════════════

class MigrationReport:
    def __init__(self) -> None:
        self.tables: Dict[str, Dict[str, int]] = {}

    def record(self, table: str, total: int, migrated: int, failed: int) -> None:
        self.tables[table] = {"total": total, "migrated": migrated, "failed": failed}

    def print_summary(self) -> None:
        print("\n" + "=" * 60)
        print("RESUMEN DE MIGRACIÓN COMPAT → V2")
        print("=" * 60)
        total_all = migrated_all = failed_all = 0
        for table, stats in self.tables.items():
            total_all += stats["total"]
            migrated_all += stats["migrated"]
            failed_all += stats["failed"]
            ok = stats["failed"] == 0 and stats["migrated"] == stats["total"]
            icon = "✅" if ok else "⚠️"
            print(
                f"{icon} {table:30s}  "
                f"migrados={stats['migrated']}/{stats['total']}  "
                f"fallidos={stats['failed']}"
            )
        print("-" * 60)
        print(f"TOTAL: {migrated_all}/{total_all} migrados, {failed_all} fallidos")
        print("=" * 60)


# ═══════════════════════════════════════════════════════════════════
# MAPEO DE IDs
# ═══════════════════════════════════════════════════════════════════

class CompatIdMapping:
    """Administra la tabla compat_id_mapping en memoria + DB."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._cache: Dict[str, Dict[int, str]] = {}
        self._ensure_table()
        self._preload()

    def _ensure_table(self) -> None:
        # NOTA: v2_id se define como TEXT para soportar UUID e Integer PKs.
        self.session.execute(text("""
            CREATE TABLE IF NOT EXISTS compat_id_mapping (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tabla VARCHAR(64) NOT NULL,
                compat_id INTEGER NOT NULL,
                v2_id TEXT NOT NULL,
                migrated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                UNIQUE(tabla, compat_id)
            )
        """))
        self.session.commit()

    def _preload(self) -> None:
        rows = self.session.execute(
            text("SELECT tabla, compat_id, v2_id FROM compat_id_mapping")
        ).fetchall()
        for row in rows:
            self._cache.setdefault(row.tabla, {})[row.compat_id] = row.v2_id

    def get(self, tabla: str, compat_id: int) -> Optional[str]:
        return self._cache.get(tabla, {}).get(compat_id)

    def set(self, tabla: str, compat_id: int, v2_id: Any) -> None:
        v2_str = str(v2_id)
        self._cache.setdefault(tabla, {})[compat_id] = v2_str
        self.session.execute(
            text("""
                INSERT INTO compat_id_mapping (tabla, compat_id, v2_id)
                VALUES (:tabla, :compat_id, :v2_id)
                ON CONFLICT (tabla, compat_id) DO UPDATE SET
                    v2_id = EXCLUDED.v2_id,
                    migrated_at = now()
            """),
            {"tabla": tabla, "compat_id": compat_id, "v2_id": v2_str},
        )


# ═══════════════════════════════════════════════════════════════════
# MOTOR DE MIGRACIÓN
# ═══════════════════════════════════════════════════════════════════

class Migrator:
    def __init__(self, session: Session, dry_run: bool, batch_size: int) -> None:
        self.session = session
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.mapping = CompatIdMapping(session)
        self.report = MigrationReport()
        self._inspector = inspect(session.bind)
        self._default_pipeline: Optional[Tuple[int, int]] = None

    # ── utilidades de DB ──────────────────────────────────────────

    def _table_exists(self, name: str) -> bool:
        return self._inspector.has_table(name)

    def _count_rows(self, name: str) -> int:
        row = self.session.execute(text(f"SELECT COUNT(*) FROM {name}")).fetchone()
        return row[0] if row else 0

    def _pk_name(self, name: str) -> str:
        pks = self._inspector.get_pk_constraint(name)["constrained_columns"]
        return pks[0] if pks else "id"

    def _pk_type(self, name: str) -> str:
        cols = self._inspector.get_columns(name)
        pk = self._pk_name(name)
        for c in cols:
            if c["name"] == pk:
                return str(c["type"])
        return "UNKNOWN"

    def _get_default_pipeline(self) -> Tuple[Optional[int], Optional[int]]:
        if self._default_pipeline is not None:
            return self._default_pipeline
        row = self.session.execute(
            text("""
                SELECT p.id, e.id
                FROM crm_pipelines p
                JOIN crm_etapas_pipeline e ON e.pipeline_id = p.id
                WHERE p.tipo = :tipo
                ORDER BY e.orden
                LIMIT 1
            """),
            {"tipo": DEFAULT_PIPELINE_NAME},
        ).fetchone()
        if row:
            self._default_pipeline = (row[0], row[1])
        else:
            self._default_pipeline = (None, None)
        return self._default_pipeline

    def _resolve_fk(self, tabla_compat: str, compat_id: Any) -> Optional[Any]:
        if compat_id is None:
            return None
        return self.mapping.get(tabla_compat, int(compat_id))

    # ── migración genérica ────────────────────────────────────────

    def migrate_pair(
        self,
        compat_name: str,
        v2_name: str,
        mapper: Callable[[Any, "Migrator"], Optional[Dict[str, Any]]],
    ) -> None:
        logger.info("Iniciando %s → %s", compat_name, v2_name)

        if not self._table_exists(compat_name):
            logger.error("Tabla compat no existe: %s", compat_name)
            self.report.record(compat_name, 0, 0, 0)
            return
        if not self._table_exists(v2_name):
            logger.error("Tabla v2 no existe: %s", v2_name)
            self.report.record(compat_name, 0, 0, 0)
            return

        compat_pk = self._pk_name(compat_name)
        v2_pk = self._pk_name(v2_name)
        v2_pk_type = self._pk_type(v2_name)
        is_v2_uuid = "uuid" in v2_pk_type.lower()

        total = self._count_rows(compat_name)
        migrated = failed = skipped = 0
        logger.info("Registros compat: %d", total)

        if total == 0:
            self.report.record(compat_name, 0, 0, 0)
            return

        offset = 0
        while offset < total:
            rows = self.session.execute(
                text(f"""
                    SELECT * FROM {compat_name}
                    ORDER BY {compat_pk}
                    LIMIT :limit OFFSET :offset
                """),
                {"limit": self.batch_size, "offset": offset},
            ).fetchall()
            if not rows:
                break

            for row in rows:
                lid = getattr(row, compat_pk)
                if self.mapping.get(compat_name, int(lid)):
                    skipped += 1
                    continue

                try:
                    values = mapper(row, self)
                    if values is None:
                        skipped += 1
                        continue

                    if is_v2_uuid:
                        v2_id = values.get(v2_pk)
                        if not v2_id:
                            v2_id = uuid.uuid4()
                            values[v2_pk] = v2_id
                    else:
                        # PK integer (auto-increment): omitir del INSERT
                        v2_id = values.pop(v2_pk, None)

                    if not self.dry_run:
                        if is_v2_uuid:
                            cols = ",".join(values.keys())
                            placeholders = ",".join(f":{k}" for k in values.keys())
                            self.session.execute(
                                text(f"INSERT INTO {v2_name} ({cols}) VALUES ({placeholders})"),
                                {k: (v if not isinstance(v, uuid.UUID) else str(v)) for k, v in values.items()},
                            )
                        else:
                            cols = ",".join(values.keys())
                            placeholders = ",".join(f":{k}" for k in values.keys())
                            result = self.session.execute(
                                text(f"INSERT INTO {v2_name} ({cols}) VALUES ({placeholders}) RETURNING {v2_pk}"),
                                {k: (v if not isinstance(v, uuid.UUID) else str(v)) for k, v in values.items()},
                            )
                            v2_id = result.scalar()

                        self.mapping.set(compat_name, int(lid), v2_id)

                    migrated += 1
                except Exception as exc:
                    logger.error(
                        "Error migrando %s.%s=%s: %s",
                        compat_name, compat_pk, lid, exc,
                    )
                    failed += 1

            if not self.dry_run:
                self.session.commit()

            offset += self.batch_size
            logger.info(
                "%s lote offset=%d  migrados=%d  fallidos=%d  saltados=%d",
                compat_name, offset, migrated, failed, skipped,
            )

        self.report.record(compat_name, total, migrated, failed)

    # ── mappers por tabla ─────────────────────────────────────────

    def _map_projects(self, row: Any, _: "Migrator") -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        created = row.created_at or now
        return {
            "id": uuid.uuid4(),
            "codigo_wbs": f"PROJ-{int(row.id):04d}",
            "sede_id": row.sede_id or DEFAULT_SEDE_ID,
            "nombre": (row.title or f"Proyecto {row.id}")[:150],
            "descripcion": row.description,
            "estado": {
                "planning": "PLANIFICACION",
                "active": "EN_PROGRESO",
                "in_progress": "EN_PROGRESO",
                "completed": "COMPLETADO",
                "cancelled": "CANCELADO",
                "paused": "PAUSADO",
            }.get(str(row.status).lower(), "PLANIFICACION"),
            "fecha_inicio": created.date(),
            "fecha_fin_est": created.date(),
            "fecha_fin_real": None,
            "presupuesto_est": 0,
            "creado_por_id": row.owner_id or DEFAULT_PERSONA_ID,
            "fecha_creacion": created,
            "deleted_at": row.deleted_at,
        }

    def _map_courses(self, row: Any, _: "Migrator") -> Optional[Dict[str, Any]]:
        return {
            "id": uuid.uuid4(),
            "sede_id": row.sede_id,
            "code": row.code,
            "title": row.title,
            "description": row.description,
            "modality": str(row.modality).upper() if row.modality else "PRESENCIAL",
            "otorga_rol_iglesia": None,
            "is_published": bool(row.is_published) if row.is_published is not None else False,
            "is_self_paced": bool(row.is_self_paced) if row.is_self_paced is not None else False,
            "duration_hours": row.duration_hours or 0,
            "xp_per_lesson": row.xp_per_lesson or 10,
            "image_url": row.image_url,
            "created_at": row.created_at,
            "updated_at": row.created_at,
        }

    def _map_enrollments(self, row: Any, m: "Migrator") -> Optional[Dict[str, Any]]:
        course_v2 = m._resolve_fk("courses", row.course_id)
        if not course_v2:
            logger.warning("Enrollment %s: sin mapeo para course_id=%s", row.id, row.course_id)
            return None
        return {
            "id": uuid.uuid4(),
            "persona_id": row.persona_id,
            "course_id": course_v2,
            "cohort_name": None,
            "status": str(row.status).upper() if row.status else "ACTIVO",
            "progress_percent": float(row.progress_percent or 0),
            "final_grade": float(row.final_grade) if row.final_grade is not None else None,
            "attendance_percent": float(row.attendance_percent or 0),
            "approved": bool(row.approved) if row.approved is not None else False,
            "acta_closed": bool(row.acta_closed) if row.acta_closed is not None else False,
            "completed_at": row.completed_at,
            "deleted_at": None,
        }

    def _map_users(self, row: Any, m: "Migrator") -> Optional[Dict[str, Any]]:
        # auth_users.id DEBE ser el UUID de la persona asociada
        persona = m.session.execute(
            text("SELECT id FROM personas WHERE user_id = :uid"),
            {"uid": row.id},
        ).fetchone()
        if not persona:
            logger.warning("User %s: no existe persona vinculada (user_id), omitiendo", row.id)
            return None

        rol_v2 = m._resolve_fk("roles", row.role_id)

        # Buscar nivel gamificado aproximado por XP
        level_uuid: Optional[str] = None
        if row.current_level_id:
            level_row = m.session.execute(
                text("""
                    SELECT id FROM auth_levels
                    WHERE min_xp <= :xp
                    ORDER BY min_xp DESC
                    LIMIT 1
                """),
                {"xp": row.xp or 0},
            ).fetchone()
            if level_row:
                level_uuid = str(level_row.id)

        return {
            "id": persona.id,
            "sede_id": DEFAULT_SEDE_ID,
            "username": row.username,
            "email": row.email,
            "password_hash": row.password_hash,
            "rol_plataforma_id": rol_v2,
            "platform_role_id": None,
            "is_active": bool(row.is_active) if row.is_active is not None else True,
            "is_email_verified": bool(row.is_email_verified) if row.is_email_verified is not None else False,
            "failed_login_attempts": 0,
            "xp": row.xp or 0,
            "current_level_id": level_uuid,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _map_roles(self, row: Any, _: "Migrator") -> Optional[Dict[str, Any]]:
        return {
            "id": uuid.uuid4(),
            "nombre": row.name,
            "permisos": row.permissions or {},
        }

    def _map_consolidation_cases(self, row: Any, m: "Migrator") -> Optional[Dict[str, Any]]:
        pipe_id, etapa_id = m._get_default_pipeline()
        if not pipe_id:
            logger.warning("consolidation_cases %s: no hay pipeline por defecto, omitiendo", row.id)
            return None

        return {
            "id": uuid.uuid4(),
            "persona_id": row.persona_id,
            "sede_id": row.sede_id or DEFAULT_SEDE_ID,
            "pipeline_id": pipe_id,
            "etapa_actual_id": etapa_id,
            "titulo_caso": (row.notes or f"Caso migrado #{row.id}")[:200],
            "prioridad": "MEDIA",
            "estado": {
                "active": "ABIERTO",
                "closed": "CERRADO_PERDIDO",
                "resolved": "RESUELTO_EXITO",
                "new": "ABIERTO",
                "open": "ABIERTO",
                "in_progress": "EN_PROGRESO",
            }.get(str(row.status).lower(), "ABIERTO"),
            "origen_canal": "DERIVACION_INTERNA",
            "origen_detalle_id": str(row.id),
            "payload_web": None,
            "asignado_a_id": row.assigned_pastor_id or row.assigned_leader_id,
            "fecha_creacion": row.created_at or datetime.now(timezone.utc),
            "fecha_cierre": None,
            "sla_vencimiento_contacto": row.next_contact_at,
            "deleted_at": row.deleted_at,
        }

    def _map_cell_groups(self, row: Any, _: "Migrator") -> Optional[Dict[str, Any]]:
        return {
            "id": uuid.uuid4(),
            "estrategia_id": None,
            "evangelism_strategy_id": row.evangelism_strategy_id,
            "sede_id": row.sede_id or DEFAULT_SEDE_ID,
            "codigo": row.code,
            "nombre": row.name,
            "ubicacion": row.zone,
            "direccion": row.address,
            "capacidad": row.capacity or 15,
            "latitud": row.latitude,
            "longitud": row.longitude,
            "dia_reunion": row.day_of_week,
            "hora_reunion": row.start_time,
            "activo": str(row.status).lower() in ("activo", "active", "true", "1") if row.status else True,
            "lider_persona_id": row.leader_persona_id,
            "asistente_persona_id": row.assistant_persona_id,
            "anfitrion_persona_id": row.host_persona_id,
            "parent_group_id": None,
            "notes_historial": None,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _map_cell_group_sessions(self, row: Any, m: "Migrator") -> Optional[Dict[str, Any]]:
        grupo_v2 = m._resolve_fk("cell_groups", row.cell_group_id)
        if not grupo_v2:
            logger.warning(
                "cell_group_session %s: sin mapeo para cell_group_id=%s",
                row.id, row.cell_group_id,
            )
            return None
        return {
            "id": uuid.uuid4(),
            "grupo_id": grupo_v2,
            "fecha_sesion": row.session_date,
            "estado": str(row.status).upper() if row.status else "PENDIENTE",
            "motivo_cancelacion": None,
            "tema_estudio": row.topic,
            "notas_lider": row.report_notes,
            "offering_amount": row.offering_amount,
            "created_at": row.created_at,
            "deleted_at": None,
        }

    def _map_agenda_events(self, row: Any, _: "Migrator") -> Optional[Dict[str, Any]]:
        return {
            "id": uuid.uuid4(),
            "sede_id": DEFAULT_SEDE_ID,
            "modulo_origen": "MANUAL",
            "entidad_origen_id": str(row.id),
            "titulo": row.title,
            "descripcion": row.description,
            "fecha_inicio": row.start_at,
            "fecha_fin": row.end_at or row.start_at,
            "todo_el_dia": bool(row.is_all_day) if row.is_all_day is not None else False,
            "regla_recurrencia": None,
            "fecha_limite_recurrencia": None,
            "excepciones_recurrencia": [],
            "recordatorios_config": [],
            "color_hex": None,
            "ubicacion_texto": row.location,
            "url_conferencia": None,
            "organizador_persona_id": row.created_by_persona_id or DEFAULT_PERSONA_ID,
            "visibilidad": "PRIVADO",
            "estado": "ACTIVO",
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "deleted_at": None,
        }

    # ── orquestación ──────────────────────────────────────────────

    def run(self) -> None:
        logger.info("Iniciando migración compat→v2 (dry_run=%s)", self.dry_run)

        # Orden importa: roles antes que users; courses antes que enrollments
        self.migrate_pair("roles", "auth_roles", self._map_roles)
        self.migrate_pair("users", "auth_users", self._map_users)
        self.migrate_pair("courses", "academy_courses", self._map_courses)
        self.migrate_pair("enrollments", "academy_enrollments", self._map_enrollments)
        self.migrate_pair("projects", "proyectos", self._map_projects)
        self.migrate_pair("consolidation_cases", "crm_casos", self._map_consolidation_cases)
        self.migrate_pair("cell_groups", "grupos_evangelismo", self._map_cell_groups)
        self.migrate_pair("cell_group_sessions", "sesiones_grupo", self._map_cell_group_sessions)
        self.migrate_pair("agenda_events", "eventos_agenda", self._map_agenda_events)

        self.report.print_summary()

        if self.dry_run:
            logger.info("Modo DRY-RUN: no se escribieron cambios en la base de datos.")
            # Hacer rollback por si acaso
            self.session.rollback()


# ═══════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Migración Compat → v2 CCF")
    parser.add_argument("--dry-run", action="store_true", help="Previsualizar sin escribir")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Registros por lote (default: 1000)",
    )
    args = parser.parse_args()

    if not DATABASE_URL:
        logger.error("Falta variable de entorno DATABASE_URL")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        migrator = Migrator(session, dry_run=args.dry_run, batch_size=args.batch_size)
        migrator.run()
    except Exception:
        logger.exception("Error fatal durante la migración")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
