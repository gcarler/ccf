#!/usr/bin/env python3.12
"""Seed data para módulos v2: CRM, Academy, Agenda, Proyectos.

Ejecutar: cd /root/ccf && ENV_FILE=backend/.env python3.12 scripts/seed_v2.py
"""
import sys, os, uuid as _uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ENV_FILE", "backend/.env")

from backend.core.database import SessionLocal
from backend.models_crm_core import (
    PipelineCRM, EtapaPipeline, CasoCRM, InteraccionCRM, TareaCRM, PlantillaMensaje,
    TipoPipelineEnum, EstadoCasoEnum, PrioridadCasoEnum,
    CanalOrigenEnum, TipoInteraccionEnum,
)
from backend.models_academy_core import (
    Curso, Leccion, PrerrequisitoCurso, Evaluacion, Pregunta, Opcion,
    Matricula, ProgresoLeccion, AsistenciaClase, IntentoEvaluacion,
    Certificado, ActaFormal, ActaEntrada, HiloForo, ComentarioForo,
)
from backend.models_agenda import (
    RecursoFisico, EventoAgenda, ParticipanteEvento, ReservaRecurso,
)
from backend.models_proyectos import Proyecto, EquipoProyecto, TareaProyecto


def seed():
    db = SessionLocal()
    try:
        # ── CRM Core ──────────────────────────────────────────────
        if db.query(PipelineCRM).count() == 0:
            p1 = PipelineCRM(
                sede_id=1, nombre="Pipeline de Nuevos Visitantes",
                tipo=TipoPipelineEnum.NUEVOS_VISITANTES,
                descripcion="Proceso estándar de seguimiento post-visita"
            )
            p2 = PipelineCRM(
                sede_id=1, nombre="Pipeline de Consejería Pastoral",
                tipo=TipoPipelineEnum.CONSEJERIA,
                descripcion="Casos derivados del equipo pastoral"
            )
            db.add_all([p1, p2])
            db.flush()

            etapas = [
                EtapaPipeline(pipeline_id=p1.id, nombre="Primer Contacto", orden=1),
                EtapaPipeline(pipeline_id=p1.id, nombre="Invitación a Célula", orden=2),
                EtapaPipeline(pipeline_id=p1.id, nombre="Seguimiento", orden=3),
                EtapaPipeline(pipeline_id=p2.id, nombre="Agendar Cita", orden=1),
                EtapaPipeline(pipeline_id=p2.id, nombre="Sesión de Consejería", orden=2),
                EtapaPipeline(pipeline_id=p2.id, nombre="Cierre", orden=3),
            ]
            db.add_all(etapas)
            db.flush()

            plantillas = [
                PlantillaMensaje(titulo="Bienvenida Visitante", canal="WHATSAPP",
                                 contenido_texto="¡Hola {nombre}! Gracias por visitarnos..."),
                PlantillaMensaje(titulo="Seguimiento 7 días", canal="WHATSAPP",
                                 contenido_texto="Hola {nombre}, ¿cómo has estado esta semana?"),
            ]
            db.add_all(plantillas)
            print("  ✓ CRM Core seeded: 2 pipelines, 6 etapas, 2 plantillas")

        # ── Academy Core ─────────────────────────────────────────
        if db.query(Curso).count() == 0:
            curso1 = Curso(
                sede_id=1, code="DISC-101", title="Discipulado Básico",
                modality="PRESENCIAL", is_published=True,
                otorga_rol_iglesia="DISCIPULO",
                duration_hours=20, xp_per_lesson=10,
            )
            curso2 = Curso(
                sede_id=1, code="LID-201", title="Liderazgo Nivel 1",
                modality="HIBRIDO", is_published=True,
                otorga_rol_iglesia="LIDER",
                duration_hours=40, xp_per_lesson=15,
            )
            db.add_all([curso1, curso2])
            db.flush()

            lecciones = [
                Leccion(course_id=curso1.id, title="¿Qué es el discipulado?",
                        content="Contenido de la lección 1...", content_type="video",
                        order_index=1, duration_minutes=30, is_published=True),
                Leccion(course_id=curso1.id, title="La oración",
                        content="Contenido de la lección 2...", content_type="video",
                        order_index=2, duration_minutes=25, is_published=True),
                Leccion(course_id=curso2.id, title="El carácter del líder",
                        content="Contenido lección 1...", content_type="video",
                        order_index=1, duration_minutes=45, is_published=True),
            ]
            db.add_all(lecciones)
            db.flush()

            # Evaluación para DISC-101
            eval1 = Evaluacion(
                course_id=curso1.id, title="Examen Final Discipulado",
                max_score=100, passing_score=70, is_published=True, weight=1.0,
            )
            db.add(eval1)
            db.flush()

            preg = Pregunta(assessment_id=eval1.id, question_text="¿Qué es el discipulado bíblico?",
                            question_type="MULTIPLE_CHOICE", points=10)
            db.add(preg)
            db.flush()

            opciones = [
                Opcion(question_id=preg.id, option_text="Un programa de la iglesia", is_correct=False),
                Opcion(question_id=preg.id, option_text="El proceso de seguir a Cristo y ayudar a otros", is_correct=True),
                Opcion(question_id=preg.id, option_text="Un título académico", is_correct=False),
            ]
            db.add_all(opciones)
            print("  ✓ Academy Core seeded: 2 cursos, 3 lecciones, 1 evaluación")

        # ── Agenda Core ──────────────────────────────────────────
        if db.query(RecursoFisico).count() == 0:
            recursos = [
                RecursoFisico(sede_id=1, nombre="Auditorio Principal", tipo="ESPACIO",
                              capacidad_maxima=500),
                RecursoFisico(sede_id=1, nombre="Salón de Jóvenes", tipo="ESPACIO",
                              capacidad_maxima=80),
                RecursoFisico(sede_id=1, nombre="Camioneta", tipo="VEHICULO"),
            ]
            db.add_all(recursos)
            print("  ✓ Agenda Core seeded: 3 recursos")

        # ── Proyectos v2 ─────────────────────────────────────────
        if db.query(Proyecto).count() == 0:
            proy = Proyecto(
                sede_id=1, codigo_wbs="PROY-001",
                nombre="Conferencia Misionera 2026",
                descripcion="Organización de la conferencia misionera anual",
                fecha_inicio=datetime(2026, 8, 1).date(),
                fecha_fin_est=datetime(2026, 10, 15).date(),
            )
            db.add(proy)
            print("  ✓ Proyectos v2 seeded: 1 proyecto")

        db.commit()
        print("\n✅ Seed v2 completado exitosamente.")
    except Exception as exc:
        db.rollback()
        print(f"\n❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
