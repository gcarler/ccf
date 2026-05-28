"""Academy 2.0 — API REST para Cursos, Lecciones, Matrícula, Foros y Certificados."""

import uuid as _uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend import models
from backend.auth import require_pastor_or_admin
from backend.core.database import get_db
from backend.crud import academy_core as crud
from backend.crud.crm import get_user_sede_id
from backend.schemas.academy_core import (
    CertificadoResponse,
    ComentarioForoCreate,
    ComentarioForoResponse,
    CursoCreate,
    CursoResponse,
    CursoUpdate,
    HiloForoCreate,
    HiloForoResponse,
    LeccionCreate,
    LeccionResponse,
    LeccionUpdate,
    MatriculaCreate,
    MatriculaResponse,
    ProgresoUpdate,
)

router = APIRouter(prefix="/v2/academy", tags=["Academy v2"])


# ═══════════════════════════════════════════════════════
# CURSOS
# ═══════════════════════════════════════════════════════

@router.get("/courses", response_model=List[CursoResponse])
def list_courses(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    published_only: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    sede_id = get_user_sede_id(db, current_user.id)
    return crud.list_cursos(db, skip=skip, limit=limit, published_only=published_only, sede_id=sede_id)


@router.post("/courses", response_model=CursoResponse, status_code=201)
def create_course(
    payload: CursoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.create_curso(db, payload.model_dump())


@router.get("/courses/{course_id}", response_model=CursoResponse)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_pastor_or_admin),
):
    obj = crud.get_curso(db, course_id)
    user_sede = get_user_sede_id(db, current_user.id)
    if not obj or (user_sede and obj.sede_id and obj.sede_id != user_sede):
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return obj


@router.put("/courses/{course_id}", response_model=CursoResponse)
def update_course(
    course_id: int,
    payload: CursoUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_curso(db, course_id, payload.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return obj


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_curso(db, course_id):
        raise HTTPException(status_code=404, detail="Curso no encontrado")


# ── Lessons ──

@router.get("/courses/{course_id}/lessons", response_model=List[LeccionResponse])
def list_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_lecciones_by_curso(db, course_id)


@router.post("/courses/{course_id}/lessons", response_model=LeccionResponse, status_code=201)
def create_lesson(
    course_id: int,
    payload: LeccionCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    data = payload.model_dump()
    data["course_id"] = course_id
    return crud.create_leccion(db, data)


@router.put("/lessons/{lesson_id}", response_model=LeccionResponse)
def update_lesson(
    lesson_id: int,
    payload: LeccionUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_leccion(db, lesson_id, payload.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Lección no encontrada")
    return obj


@router.delete("/lessons/{lesson_id}", status_code=204)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if not crud.delete_leccion(db, lesson_id):
        raise HTTPException(status_code=404, detail="Lección no encontrada")


# ═══════════════════════════════════════════════════════
# ENROLLMENTS (MATRÍCULA)
# ═══════════════════════════════════════════════════════

@router.post("/enrollments", response_model=MatriculaResponse, status_code=201)
def enroll_persona(
    payload: MatriculaCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.enroll(db, payload.model_dump())


@router.get("/enrollments", response_model=List[MatriculaResponse])
def list_enrollments(
    persona_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if persona_id:
        return crud.list_by_persona(db, persona_id)
    raise HTTPException(status_code=400, detail="Debe proporcionar persona_id")


@router.get("/enrollments/{enrollment_id}", response_model=MatriculaResponse)
def get_enrollment(
    enrollment_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.get_matricula(db, enrollment_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    return obj


@router.patch("/enrollments/{enrollment_id}/progress", response_model=MatriculaResponse)
def update_progress(
    enrollment_id: str,
    payload: ProgresoUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    obj = crud.update_progress(db, enrollment_id, payload.model_dump(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    return obj


# ═══════════════════════════════════════════════════════
# FOROS
# ═══════════════════════════════════════════════════════

@router.get("/courses/{course_id}/threads", response_model=List[HiloForoResponse])
def list_threads(
    course_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_by_course(db, course_id)


@router.post("/courses/{course_id}/threads", response_model=HiloForoResponse, status_code=201)
def create_thread(
    course_id: int,
    payload: HiloForoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    data = payload.model_dump()
    data["course_id"] = course_id
    return crud.create_hilo(db, data)


@router.get("/threads/{thread_id}/comments", response_model=List[ComentarioForoResponse])
def list_comments(
    thread_id: int,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    return crud.list_comentarios(db, thread_id)


@router.post("/threads/{thread_id}/comments", response_model=ComentarioForoResponse, status_code=201)
def create_comment(
    thread_id: int,
    payload: ComentarioForoCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    data = payload.model_dump()
    data["thread_id"] = thread_id
    return crud.create_comentario(db, data)


# ═══════════════════════════════════════════════════════
# CERTIFICADOS
# ═══════════════════════════════════════════════════════

@router.post("/enrollments/{enrollment_id}/certificate", response_model=CertificadoResponse, status_code=201)
def issue_certificate(
    enrollment_id: str,
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    matricula = crud.get_matricula(db, enrollment_id)
    if not matricula:
        raise HTTPException(status_code=404, detail="Matrícula no encontrada")
    if not matricula.approved:
        raise HTTPException(status_code=400, detail="El estudiante no ha sido aprobado")
    return crud.create_certificado(db, {
        "enrollment_id": enrollment_id,
        "certificate_code": str(_uuid.uuid4()),
        "certificate_type": "COMPLETION",
    })


@router.get("/certificates", response_model=List[CertificadoResponse])
def list_certificates(
    persona_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_pastor_or_admin),
):
    if persona_id:
        return crud.get_certificados_by_persona(db, persona_id)  # noqa: defined below
    raise HTTPException(status_code=400, detail="Debe proporcionar persona_id")
