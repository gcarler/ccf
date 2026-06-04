"""Academy 2.0 — CRUD functions."""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4

from sqlalchemy.orm import Session
from backend.models_shared import _utcnow

from backend.models_academy_core import (
    Curso, Leccion, Matricula, Evaluacion, ActaFormal,
    HiloForo, ComentarioForo, Certificado,
    PrerrequisitoCurso,
)
from backend.schemas.academy_core import (
    CursoCreate, LeccionCreate, MatriculaCreate, EvaluacionCreate,
    ActaFormalCreate, HiloForoCreate, ComentarioForoCreate,
    CertificadoCreate, PrerrequisitoCursoCreate,
)


# ── Curso ────────────────────────────────────────────────

def create_curso(db: Session, payload: CursoCreate) -> Curso:
    obj = Curso(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_curso(db: Session, curso_id: int) -> Optional[Curso]:
    return db.query(Curso).filter(Curso.id == curso_id).first()


def list_cursos(db: Session, sede_id: Optional[int] = None, published_only: bool = False) -> List[Curso]:
    q = db.query(Curso)
    if sede_id: q = q.filter(Curso.sede_id == sede_id)
    if published_only: q = q.filter(Curso.is_published.is_(True))
    return q.all()


def update_curso(db: Session, curso_id: int, payload: CursoCreate) -> Optional[Curso]:
    obj = get_curso(db, curso_id)
    if not obj: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    obj.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(obj)
    return obj


def delete_curso(db: Session, curso_id: int) -> bool:
    obj = get_curso(db, curso_id)
    if not obj: return False
    obj.deleted_at = _utcnow(); db.commit()
    return True


# ── Leccion ──────────────────────────────────────────────

def create_leccion(db: Session, payload: LeccionCreate) -> Leccion:
    obj = Leccion(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_leccion(db: Session, leccion_id: int) -> Optional[Leccion]:
    return db.query(Leccion).filter(Leccion.id == leccion_id).first()


def list_lecciones(db: Session, course_id: int) -> List[Leccion]:
    return db.query(Leccion).filter(Leccion.course_id == course_id).order_by(Leccion.order_index).all()


def update_leccion(db: Session, leccion_id: int, payload: LeccionCreate) -> Optional[Leccion]:
    obj = get_leccion(db, leccion_id)
    if not obj: return None
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


def delete_leccion(db: Session, leccion_id: int) -> bool:
    obj = get_leccion(db, leccion_id)
    if not obj: return False
    obj.deleted_at = _utcnow(); db.commit()
    return True


# ── Matricula ────────────────────────────────────────────

def create_matricula(db: Session, payload: MatriculaCreate) -> Matricula:
    obj = Matricula(id=uuid4(), **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_matricula(db: Session, matricula_id: str) -> Optional[Matricula]:
    return db.query(Matricula).filter(Matricula.id == matricula_id).first()


def list_matriculas(db: Session, persona_id: Optional[str] = None, course_id: Optional[int] = None) -> List[Matricula]:
    q = db.query(Matricula)
    if persona_id: q = q.filter(Matricula.persona_id == persona_id)
    if course_id: q = q.filter(Matricula.course_id == course_id)
    return q.all()


# ── Evaluacion ───────────────────────────────────────────

def create_evaluacion(db: Session, payload: EvaluacionCreate) -> Evaluacion:
    obj = Evaluacion(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_evaluacion(db: Session, eval_id: int) -> Optional[Evaluacion]:
    return db.query(Evaluacion).filter(Evaluacion.id == eval_id).first()


def list_evaluaciones(db: Session, course_id: int) -> List[Evaluacion]:
    return db.query(Evaluacion).filter(Evaluacion.course_id == course_id).all()


# ── Acta Formal ──────────────────────────────────────────

def create_acta(db: Session, payload: ActaFormalCreate) -> ActaFormal:
    obj = ActaFormal(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_acta(db: Session, acta_id: int) -> Optional[ActaFormal]:
    return db.query(ActaFormal).filter(ActaFormal.id == acta_id).first()


# ── Hilo Foro ────────────────────────────────────────────

def create_hilo(db: Session, payload: HiloForoCreate) -> HiloForo:
    obj = HiloForo(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_hilo(db: Session, hilo_id: int) -> Optional[HiloForo]:
    return db.query(HiloForo).filter(HiloForo.id == hilo_id).first()


def list_hilos(db: Session, course_id: int) -> List[HiloForo]:
    return db.query(HiloForo).filter(HiloForo.course_id == course_id).order_by(HiloForo.created_at.desc()).all()


# ── Comentario Foro ──────────────────────────────────────

def create_comentario(db: Session, payload: ComentarioForoCreate) -> ComentarioForo:
    obj = ComentarioForo(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def list_comentarios(db: Session, thread_id: int) -> List[ComentarioForo]:
    return db.query(ComentarioForo).filter(ComentarioForo.thread_id == thread_id).order_by(ComentarioForo.created_at).all()


# ── Certificado ──────────────────────────────────────────

def create_certificado(db: Session, payload: CertificadoCreate) -> Certificado:
    code = f"CERT-{uuid4().hex[:8].upper()}"
    obj = Certificado(certificate_code=code, **payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


def get_certificado(db: Session, cert_id: int) -> Optional[Certificado]:
    return db.query(Certificado).filter(Certificado.id == cert_id).first()


def list_certificados(db: Session, persona_id: Optional[str] = None) -> List[Certificado]:
    q = db.query(Certificado)
    if persona_id: q = q.filter(Certificado.persona_id == persona_id)
    return q.all()


# ── Prerrequisito ────────────────────────────────────────

def create_prerrequisito(db: Session, payload: PrerrequisitoCursoCreate) -> PrerrequisitoCurso:
    obj = PrerrequisitoCurso(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj
