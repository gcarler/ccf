"""Academy 2.0 — Catálogo, Evaluaciones, Matrícula, Progreso, Certificaciones, Foros CRUD."""

import uuid as _uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models_academy_core import (
    ActaFormal,
    AsistenciaClase,
    Certificado,
    ComentarioForo,
    Curso,
    EntregaTarea,
    Evaluacion,
    HiloForo,
    IntentoEvaluacion,
    Leccion,
    Matricula,
    Opcion,
    Pregunta,
    PrerrequisitoCurso,
    ProgresoLeccion,
)


# ═══════════════════════════════════════════════════════════════════
# Curso
# ═══════════════════════════════════════════════════════════════════

def create_curso(db: Session, payload: dict) -> Curso:
    row = Curso(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_curso(db: Session, curso_id: int) -> Optional[Curso]:
    return db.query(Curso).filter(Curso.id == curso_id).first()


def list_cursos(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    modality: Optional[str] = None,
    published_only: bool = False,
    sede_id: Optional[int] = None,
) -> List[Curso]:
    q = db.query(Curso)
    if modality:
        q = q.filter(Curso.modality == modality)
    if published_only:
        q = q.filter(Curso.is_published.is_(True))
    if sede_id is not None:
        q = q.filter(Curso.sede_id == sede_id)
    return q.offset(skip).limit(limit).all()


def update_curso(db: Session, curso_id: int, payload: dict) -> Optional[Curso]:
    row = db.query(Curso).filter(Curso.id == curso_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_curso(db: Session, curso_id: int) -> bool:
    row = db.query(Curso).filter(Curso.id == curso_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def list_lecciones(db: Session, curso_id: int) -> List[Leccion]:
    return (
        db.query(Leccion)
        .filter(Leccion.course_id == curso_id)
        .order_by(Leccion.order_index)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════
# Leccion
# ═══════════════════════════════════════════════════════════════════

def create_leccion(db: Session, payload: dict) -> Leccion:
    row = Leccion(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_leccion(db: Session, leccion_id: int) -> Optional[Leccion]:
    return db.query(Leccion).filter(Leccion.id == leccion_id).first()


def list_lecciones_by_curso(db: Session, curso_id: int) -> List[Leccion]:
    return (
        db.query(Leccion)
        .filter(Leccion.course_id == curso_id)
        .order_by(Leccion.order_index)
        .all()
    )


def update_leccion(db: Session, leccion_id: int, payload: dict) -> Optional[Leccion]:
    row = db.query(Leccion).filter(Leccion.id == leccion_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_leccion(db: Session, leccion_id: int) -> bool:
    row = db.query(Leccion).filter(Leccion.id == leccion_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# PrerrequisitoCurso
# ═══════════════════════════════════════════════════════════════════

def create_prerrequisito(db: Session, payload: dict) -> PrerrequisitoCurso:
    row = PrerrequisitoCurso(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_prerrequisitos(db: Session, curso_id: int) -> List[PrerrequisitoCurso]:
    return (
        db.query(PrerrequisitoCurso)
        .filter(PrerrequisitoCurso.course_id == curso_id)
        .all()
    )


def delete_prerrequisito(db: Session, prereq_id: int) -> bool:
    row = db.query(PrerrequisitoCurso).filter(PrerrequisitoCurso.id == prereq_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# Evaluacion
# ═══════════════════════════════════════════════════════════════════

def create_evaluacion(db: Session, payload: dict) -> Evaluacion:
    row = Evaluacion(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_evaluacion(db: Session, eval_id: int) -> Optional[Evaluacion]:
    return db.query(Evaluacion).filter(Evaluacion.id == eval_id).first()


def list_evaluaciones(db: Session, course_id: Optional[int] = None) -> List[Evaluacion]:
    q = db.query(Evaluacion)
    if course_id is not None:
        q = q.filter(Evaluacion.course_id == course_id)
    return q.all()


def update_evaluacion(db: Session, eval_id: int, payload: dict) -> Optional[Evaluacion]:
    row = db.query(Evaluacion).filter(Evaluacion.id == eval_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_evaluacion(db: Session, eval_id: int) -> bool:
    row = db.query(Evaluacion).filter(Evaluacion.id == eval_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def list_preguntas(db: Session, evaluacion_id: int) -> List[Pregunta]:
    return (
        db.query(Pregunta)
        .filter(Pregunta.assessment_id == evaluacion_id)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════
# Pregunta
# ═══════════════════════════════════════════════════════════════════

def create_pregunta(db: Session, payload: dict) -> Pregunta:
    row = Pregunta(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pregunta(db: Session, pregunta_id: int) -> Optional[Pregunta]:
    return db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()


def update_pregunta(db: Session, pregunta_id: int, payload: dict) -> Optional[Pregunta]:
    row = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_pregunta(db: Session, pregunta_id: int) -> bool:
    row = db.query(Pregunta).filter(Pregunta.id == pregunta_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# Opcion
# ═══════════════════════════════════════════════════════════════════

def create_opcion(db: Session, payload: dict) -> Opcion:
    row = Opcion(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_opcion(db: Session, opcion_id: int) -> Optional[Opcion]:
    return db.query(Opcion).filter(Opcion.id == opcion_id).first()


def list_opciones(db: Session, pregunta_id: int) -> List[Opcion]:
    return (
        db.query(Opcion)
        .filter(Opcion.question_id == pregunta_id)
        .all()
    )


def update_opcion(db: Session, opcion_id: int, payload: dict) -> Optional[Opcion]:
    row = db.query(Opcion).filter(Opcion.id == opcion_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_opcion(db: Session, opcion_id: int) -> bool:
    row = db.query(Opcion).filter(Opcion.id == opcion_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# Matricula
# ═══════════════════════════════════════════════════════════════════

def enroll(db: Session, payload: dict) -> Matricula:
    existing = (
        db.query(Matricula)
        .filter(
            Matricula.persona_id == payload["persona_id"],
            Matricula.course_id == payload["course_id"],
        )
        .first()
    )
    if existing:
        raise ValueError("El estudiante ya se encuentra inscrito en este curso")

    matricula_data = {
        "persona_id": payload["persona_id"],
        "course_id": payload["course_id"],
        "cohort_name": payload.get("cohort_name"),
        "status": payload.get("status", "ACTIVO"),
    }
    row = Matricula(id=_uuid.uuid4(), **matricula_data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_matricula(db: Session, matricula_id: str) -> Optional[Matricula]:
    return db.query(Matricula).filter(Matricula.id == matricula_id).first()


def list_matriculas(db: Session, course_id: Optional[int] = None) -> List[Matricula]:
    q = db.query(Matricula)
    if course_id is not None:
        q = q.filter(Matricula.course_id == course_id)
    return q.all()


def list_by_persona(db: Session, persona_id: str) -> List[Matricula]:
    return (
        db.query(Matricula)
        .filter(Matricula.persona_id == persona_id)
        .all()
    )


def update_progress(db: Session, matricula_id: str, payload: dict) -> Optional[Matricula]:
    row = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


def delete_matricula(db: Session, matricula_id: str) -> bool:
    row = db.query(Matricula).filter(Matricula.id == matricula_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ═══════════════════════════════════════════════════════════════════
# ProgresoLeccion
# ═══════════════════════════════════════════════════════════════════

def create_progreso_leccion(db: Session, payload: dict) -> ProgresoLeccion:
    row = ProgresoLeccion(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_progreso_leccion(db: Session, prog_id: int) -> Optional[ProgresoLeccion]:
    return db.query(ProgresoLeccion).filter(ProgresoLeccion.id == prog_id).first()


def list_progreso_by_persona(db: Session, persona_id: str) -> List[ProgresoLeccion]:
    return (
        db.query(ProgresoLeccion)
        .filter(ProgresoLeccion.persona_id == persona_id)
        .all()
    )


def update_progreso_leccion(db: Session, prog_id: int, payload: dict) -> Optional[ProgresoLeccion]:
    row = db.query(ProgresoLeccion).filter(ProgresoLeccion.id == prog_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════
# AsistenciaClase
# ═══════════════════════════════════════════════════════════════════

def create_asistencia(db: Session, payload: dict) -> AsistenciaClase:
    row = AsistenciaClase(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_asistencias(db: Session, enrollment_id: str) -> List[AsistenciaClase]:
    return (
        db.query(AsistenciaClase)
        .filter(AsistenciaClase.enrollment_id == enrollment_id)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════
# IntentoEvaluacion
# ═══════════════════════════════════════════════════════════════════

def create_intento(db: Session, payload: dict) -> IntentoEvaluacion:
    row = IntentoEvaluacion(id=_uuid.uuid4(), **payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_intento(db: Session, intento_id: str) -> Optional[IntentoEvaluacion]:
    return db.query(IntentoEvaluacion).filter(IntentoEvaluacion.id == intento_id).first()


def list_intentos(db: Session, enrollment_id: str) -> List[IntentoEvaluacion]:
    return (
        db.query(IntentoEvaluacion)
        .filter(IntentoEvaluacion.enrollment_id == enrollment_id)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════
# EntregaTarea
# ═══════════════════════════════════════════════════════════════════

def create_entrega(db: Session, payload: dict) -> EntregaTarea:
    row = EntregaTarea(id=_uuid.uuid4(), **payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_entrega(db: Session, entrega_id: str) -> Optional[EntregaTarea]:
    return db.query(EntregaTarea).filter(EntregaTarea.id == entrega_id).first()


def list_entregas(db: Session, enrollment_id: str) -> List[EntregaTarea]:
    return (
        db.query(EntregaTarea)
        .filter(EntregaTarea.enrollment_id == enrollment_id)
        .all()
    )


def update_entrega(db: Session, entrega_id: str, payload: dict) -> Optional[EntregaTarea]:
    row = db.query(EntregaTarea).filter(EntregaTarea.id == entrega_id).first()
    if not row:
        return None
    for k, v in payload.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════
# Certificado
# ═══════════════════════════════════════════════════════════════════

def create_certificado(db: Session, payload: dict) -> Certificado:
    row = Certificado(id=_uuid.uuid4(), **payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_certificado(db: Session, cert_id: str) -> Optional[Certificado]:
    return db.query(Certificado).filter(Certificado.id == cert_id).first()


def list_certificados(db: Session, enrollment_id: Optional[str] = None) -> List[Certificado]:
    q = db.query(Certificado)
    if enrollment_id is not None:
        q = q.filter(Certificado.enrollment_id == enrollment_id)
    return q.all()


# ═══════════════════════════════════════════════════════════════════
# ActaFormal
# ═══════════════════════════════════════════════════════════════════

def create_acta(db: Session, payload: dict) -> ActaFormal:
    row = ActaFormal(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_acta(db: Session, acta_id: int) -> Optional[ActaFormal]:
    return db.query(ActaFormal).filter(ActaFormal.id == acta_id).first()


def list_actas(db: Session, course_id: Optional[int] = None) -> List[ActaFormal]:
    q = db.query(ActaFormal)
    if course_id is not None:
        q = q.filter(ActaFormal.course_id == course_id)
    return q.all()


# ═══════════════════════════════════════════════════════════════════
# HiloForo
# ═══════════════════════════════════════════════════════════════════

def create_hilo(db: Session, payload: dict) -> HiloForo:
    row = HiloForo(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_hilo(db: Session, hilo_id: int) -> Optional[HiloForo]:
    return db.query(HiloForo).filter(HiloForo.id == hilo_id).first()


def list_by_course(db: Session, course_id: int) -> List[HiloForo]:
    return (
        db.query(HiloForo)
        .filter(HiloForo.course_id == course_id)
        .order_by(HiloForo.created_at.desc())
        .all()
    )


def delete_hilo(db: Session, hilo_id: int) -> bool:
    row = db.query(HiloForo).filter(HiloForo.id == hilo_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def create_comentario(db: Session, payload: dict) -> ComentarioForo:
    row = ComentarioForo(**payload)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ═══════════════════════════════════════════════════════════════════
# ComentarioForo
# ═══════════════════════════════════════════════════════════════════

def get_comentario(db: Session, comentario_id: int) -> Optional[ComentarioForo]:
    return db.query(ComentarioForo).filter(ComentarioForo.id == comentario_id).first()


def list_comentarios(db: Session, thread_id: int) -> List[ComentarioForo]:
    return (
        db.query(ComentarioForo)
        .filter(ComentarioForo.thread_id == thread_id)
        .order_by(ComentarioForo.created_at)
        .all()
    )


def delete_comentario(db: Session, comentario_id: int) -> bool:
    row = db.query(ComentarioForo).filter(ComentarioForo.id == comentario_id).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True
