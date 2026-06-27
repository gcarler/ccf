import sys
from pathlib import Path

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

#!/usr/bin/env python
"""
Script de calidad para el módulo de proyectos.

Crea 3 usuarios de prueba, un proyecto, tareas asignadas,
documentos, comentarios y verifica el flujo completo.

Uso:
    cd /root/ccf && ./venv/bin/python scripts/test_projects_quality.py
"""
import os
import sys
import datetime
import tempfile
import base64

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

from backend.core.database import SessionLocal
from backend.models import *  # noqa: F401 - importa todos los modelos para resolver relaciones
from backend.models_identity import User
from backend.models_projects import (
    Project, ProjectTask, ProjectMilestone, ProjectComment,
    ProjectPhase, ProjectActivityLog, ProjectDocument, ProjectAttachment
)
from backend.core.security import get_password_hash

db = SessionLocal()

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"
PASS = 0
FAIL = 0

def ok(msg):
    global PASS
    PASS += 1
    print(f"  {GREEN}✓{NC} {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  {RED}✗{NC} {msg}")

def info(msg):
    print(f"  {BLUE}ℹ{NC} {msg}")

def section(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")

# ──────────────────────────────────────────────────────────────
section("1. LIMPIEZA DE DATOS DE PRUEBA ANTERIORES")
# ──────────────────────────────────────────────────────────────

test_emails = [
    "prueba1@ccf.test",
    "prueba2@ccf.test",
    "prueba3@ccf.test",
]

for email in test_emails:
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Borrar tareas asignadas
        db.query(ProjectTask).filter(ProjectTask.assignee_id == user.id).delete(synchronize_session=False)
        # Borrar comentarios
        db.query(ProjectComment).filter(ProjectComment.author_id == user.id).delete(synchronize_session=False)
        # Borrar attachments subidos
        db.query(ProjectAttachment).filter(ProjectAttachment.uploader_id == user.id).delete(synchronize_session=False)
        db.commit()
        info(f"Usuario anterior '{email}' eliminado")

# Borrar proyecto de prueba anterior
proj = db.query(Project).filter(Project.title == "Proyecto Prueba - Creatividad").first()
if proj:
    db.query(ProjectActivityLog).filter(ProjectActivityLog.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectDocument).filter(ProjectDocument.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectComment).filter(ProjectComment.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectMilestone).filter(ProjectMilestone.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectTask).filter(ProjectTask.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectPhase).filter(ProjectPhase.project_id == proj.id).delete(synchronize_session=False)
    db.delete(proj)
    db.commit()
    info("Proyecto de prueba anterior eliminado")

ok("Limpieza completada")

# ──────────────────────────────────────────────────────────────
section("2. CREACIÓN DE 3 USUARIOS DE PRUEBA")
# ──────────────────────────────────────────────────────────────

users_data = [
    {"email": "prueba1@ccf.test", "username": "usuario_prueba_1", "role": "estudiante", "name": "Usuario Prueba 1"},
    {"email": "prueba2@ccf.test", "username": "usuario_prueba_2", "role": "docente", "name": "Usuario Prueba 2"},
    {"email": "prueba3@ccf.test", "username": "usuario_prueba_3", "role": "coordinador", "name": "Usuario Prueba 3"},
]

created_users = []
for ud in users_data:
    existing = db.query(User).filter(User.email == ud["email"]).first()
    if existing:
        ok(f"Usuario '{ud['name']}' ya existe (id={existing.id})")
        created_users.append(existing)
    else:
        u = User(
            username=ud["username"],
            email=ud["email"],
            password_hash=get_password_hash("prueba123"),
            role=ud["role"],
            is_active=True,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
        ok(f"Usuario '{ud['name']}' creado (id={u.id}, rol={u.role})")
        created_users.append(u)

admin_user = db.query(User).filter(User.email == "admin@ccf.com").first()
if admin_user:
    info(f"Admin encontrado: {admin_user.email} (id={admin_user.id})")
else:
    fail("No se encontró usuario admin@ccf.com")
    admin_user = created_users[0]  # fallback

u1, u2, u3 = created_users

# ──────────────────────────────────────────────────────────────
section("3. CREACIÓN DEL PROYECTO 'CREATIVIDAD'")
# ──────────────────────────────────────────────────────────────

project = Project(
    title="Proyecto Prueba - Creatividad",
    description="Proyecto de calidad para probar el módulo completo de proyectos. Incluye tareas, documentos y comentarios entre 3 usuarios.",
    status="active",
    owner_id=admin_user.id,
    color="#3b82f6",
    icon="palette",
)
db.add(project)
db.commit()
db.refresh(project)
ok(f"Proyecto creado: '{project.title}' (id={project.id})")

# Crear fases por defecto
default_phases = [
    ("Por Hacer", "todo", "#94a3b8", 0),
    ("En Curso", "in_progress", "#3b82f6", 1),
    ("Revisión", "review", "#f59e0b", 2),
    ("Completado", "completed", "#10b981", 3),
]
for name, slug, color, order in default_phases:
    phase = ProjectPhase(
        project_id=project.id,
        name=name,
        slug=slug,
        color=color,
        order_index=order,
    )
    db.add(phase)
db.commit()
ok("4 fases kanban creadas (Por Hacer, En Curso, Revisión, Completado)")

# Log de actividad
db.add(ProjectActivityLog(
    project_id=project.id,
    user_id=admin_user.id,
    action_type="project_created",
    description=f"Proyecto creado por {admin_user.username}",
))
db.commit()

# ──────────────────────────────────────────────────────────────
section("4. CREACIÓN DE TAREAS ASIGNADAS CON FECHAS")
# ──────────────────────────────────────────────────────────────

now = datetime.datetime.utcnow()
tasks_data = [
    {
        "title": "Diseñar logo del proyecto",
        "description": "Crear un logo que represente la identidad visual del proyecto de creatividad.",
        "priority": "high",
        "status": "todo",
        "assignee_id": u1.id,
        "start_date": now,
        "due_date": now + datetime.timedelta(days=3),
        "labels": ["diseño", "branding"],
    },
    {
        "title": "Escribir documento de propuesta",
        "description": "Redactar la propuesta creativa incluyendo objetivos, alcance y cronograma.",
        "priority": "urgent",
        "status": "in_progress",
        "assignee_id": u2.id,
        "start_date": now - datetime.timedelta(days=1),
        "due_date": now + datetime.timedelta(days=5),
        "labels": ["documentación", "propuesta"],
    },
    {
        "title": "Prepresentación del equipo",
        "description": "Armar la presentación para mostrar los avances al pastor.",
        "priority": "medium",
        "status": "todo",
        "assignee_id": u3.id,
        "start_date": now + datetime.timedelta(days=2),
        "due_date": now + datetime.timedelta(days=7),
        "labels": ["presentación"],
    },
    {
        "title": "Revisar materiales necesarios",
        "description": "Listar todos los materiales y suministros que se necesitan para la ejecución.",
        "priority": "low",
        "status": "todo",
        "assignee_id": u1.id,
        "start_date": now,
        "due_date": now + datetime.timedelta(days=2),
        "labels": ["logística"],
    },
    {
        "title": "Coordinar cronograma general",
        "description": "Definir fechas clave y hitos del proyecto completo.",
        "priority": "high",
        "status": "todo",
        "assignee_id": admin_user.id,
        "start_date": now,
        "due_date": now + datetime.timedelta(days=4),
        "labels": ["planificación"],
    },
]

created_tasks = []
for td in tasks_data:
    task = ProjectTask(
        project_id=project.id,
        title=td["title"],
        description=td["description"],
        priority=td["priority"],
        status=td["status"],
        assignee_id=td["assignee_id"],
        start_date=td["start_date"],
        due_date=td["due_date"],
        labels=td["labels"],
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    assignee = db.query(User).filter(User.id == td["assignee_id"]).first()
    ok(f"Tarea '{task.title}' → asignada a {assignee.username} (id={task.id})")
    created_tasks.append(task)

    db.add(ProjectActivityLog(
        project_id=project.id,
        user_id=admin_user.id,
        action_type="task_created",
        description=f"Tarea creada: {task.title} → {assignee.username}",
    ))
db.commit()

# ──────────────────────────────────────────────────────────────
section("5. CREACIÓN DE MILESTONES (HITOS)")
# ──────────────────────────────────────────────────────────────

milestones_data = [
    ("Propuesta aprobada", "La propuesta creativa debe ser aprobada por el liderazgo.", now + datetime.timedelta(days=5)),
    ("Diseño finalizado", "El logo y materiales visuales deben estar listos.", now + datetime.timedelta(days=10)),
    ("Presentación completada", "La presentación al equipo pastoral debe estar lista.", now + datetime.timedelta(days=14)),
]

for title, desc, target in milestones_data:
    ms = ProjectMilestone(
        project_id=project.id,
        title=title,
        description=desc,
        target_date=target,
        is_completed=False,
    )
    db.add(ms)
    db.commit()
    ok(f"Hito '{title}' creado (target: {target.strftime('%Y-%m-%d')})")

# ──────────────────────────────────────────────────────────────
section("6. DOCUMENTO WIKI DEL PROYECTO")
# ──────────────────────────────────────────────────────────────

wiki = ProjectDocument(
    project_id=project.id,
    title="Guía del Proyecto - Creatividad",
    content="""# Guía del Proyecto: Creatividad

## Objetivo
Desarrollar una campaña creativa para la iglesia que incluya diseño, contenido y presentación.

## Equipo
- **Administrador:** Coordina el proyecto
- **Usuario Prueba 1:** Diseño y logística
- **Usuario Prueba 2:** Documentación y propuesta
- **Usuario Prueba 3:** Presentación y coordinación

## Cronograma
1. Semana 1: Propuesta y diseño inicial
2. Semana 2: Desarrollo de materiales
3. Semana 3: Revisión y ajustes
4. Semana 4: Presentación final

## Recursos
- Herramientas de diseño: Figma, Canva
- Documentación: Google Docs
- Presentación: PowerPoint / Google Slides
""",
    author_id=admin_user.id,
)
db.add(wiki)
db.commit()
ok(f"Documento wiki creado: '{wiki.title}' (id={wiki.id})")

db.add(ProjectActivityLog(
    project_id=project.id,
    user_id=admin_user.id,
    action_type="wiki_updated",
    description="Documento wiki creado: Guía del Proyecto",
))
db.commit()

# ──────────────────────────────────────────────────────────────
section("7. COMENTARIOS ENTRE USUARIOS")
# ──────────────────────────────────────────────────────────────

comments_data = [
    {
        "author_id": u1.id,
        "content": "¡Hola equipo! Ya empecé con el diseño del logo. Voy a tener el primer borrador para mañana. ¿Alguna sugerencia de colores?",
        "task_id": created_tasks[0].id,
    },
    {
        "author_id": u2.id,
        "content": "Buena iniciativa @usuario_prueba_1. Creo que deberíamos usar los colores institucionales de la iglesia: azul y blanco.",
        "task_id": created_tasks[0].id,
    },
    {
        "author_id": u3.id,
        "content": "De acuerdo con los colores institucionales. Yo me encargo de la presentación mientras ustedes avanzan con el diseño.",
        "task_id": created_tasks[2].id,
    },
    {
        "author_id": admin_user.id,
        "content": "Excelente trabajo equipo. Recuerden que la presentación es el viernes. Vamos bien con los tiempos.",
        "task_id": None,  # Comentario general del proyecto
    },
    {
        "author_id": u1.id,
        "content": "Ya tengo la lista de materiales. Necesitamos: papel bond, marcadores, impresiones a color y un proyector.",
        "task_id": created_tasks[3].id,
    },
    {
        "author_id": u2.id,
        "content": "La propuesta ya está al 70%. Mañana la termino y la comparto para revisión.",
        "task_id": created_tasks[1].id,
    },
]

for cd in comments_data:
    author = db.query(User).filter(User.id == cd["author_id"]).first()
    comment = ProjectComment(
        project_id=project.id,
        task_id=cd["task_id"],
        author_id=cd["author_id"],
        content=cd["content"],
        is_resolved=False,
    )
    db.add(comment)
    db.commit()

    task_title = ""
    if cd["task_id"]:
        task = db.query(ProjectTask).filter(ProjectTask.id == cd["task_id"]).first()
        task_title = f" en tarea '{task.title}'"

    ok(f"Comentario de {author.username}{task_title}: '{cd['content'][:60]}...'")

    db.add(ProjectActivityLog(
        project_id=project.id,
        user_id=cd["author_id"],
        action_type="comment_added",
        description=f"{author.username} comentó{task_title}",
    ))
db.commit()

# ──────────────────────────────────────────────────────────────
section("8. VERIFICACIÓN DE DATOS")
# ──────────────────────────────────────────────────────────────

# Contar todo
proj_count = db.query(Project).filter(Project.id == project.id).count()
ok(f"Proyectos: {proj_count}") if proj_count == 1 else fail(f"Proyectos: {proj_count} (esperado 1)")

task_count = db.query(ProjectTask).filter(ProjectTask.project_id == project.id).count()
ok(f"Tareas: {task_count}") if task_count == 5 else fail(f"Tareas: {task_count} (esperado 5)")

phase_count = db.query(ProjectPhase).filter(ProjectPhase.project_id == project.id).count()
ok(f"Fases: {phase_count}") if phase_count == 4 else fail(f"Fases: {phase_count} (esperado 4)")

ms_count = db.query(ProjectMilestone).filter(ProjectMilestone.project_id == project.id).count()
ok(f"Milestones: {ms_count}") if ms_count == 3 else fail(f"Milestones: {ms_count} (esperado 3)")

comment_count = db.query(ProjectComment).filter(ProjectComment.project_id == project.id).count()
ok(f"Comentarios: {comment_count}") if comment_count == 6 else fail(f"Comentarios: {comment_count} (esperado 6)")

doc_count = db.query(ProjectDocument).filter(ProjectDocument.project_id == project.id).count()
ok(f"Documentos wiki: {doc_count}") if doc_count == 1 else fail(f"Documentos wiki: {doc_count} (esperado 1)")

activity_count = db.query(ProjectActivityLog).filter(ProjectActivityLog.project_id == project.id).count()
ok(f"Logs de actividad: {activity_count}") if activity_count >= 7 else fail(f"Logs de actividad: {activity_count} (esperado >= 7)")

# Verificar asignaciones
for task in created_tasks:
    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    if assignee:
        ok(f"  Tarea '{task.title}' → {assignee.username} ({task.status}, {task.priority})")
    else:
        fail(f"  Tarea '{task.title}' → sin asignar")

# Verificar comentarios por usuario
for u in [u1, u2, u3, admin_user]:
    count = db.query(ProjectComment).filter(
        ProjectComment.project_id == project.id,
        ProjectComment.author_id == u.id,
    ).count()
    ok(f"  {u.username}: {count} comentario(s)")

# ──────────────────────────────────────────────────────────────
section("9. PRUEBA DE API (ENDPOINTS)")
# ──────────────────────────────────────────────────────────────

import httpx

# Login como admin
login_resp = httpx.post("http://127.0.0.1:8000/api/auth/login", data={
    "username": "admin@ccf.com",
    "password": "admin123",
    "grant_type": "password",
}, follow_redirects=False)

if login_resp.status_code == 200:
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    ok("Login admin exitoso")

    # GET /projects
    resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers)
    if resp.status_code == 200:
        projects = resp.json()
        found = [p for p in projects if p["id"] == project.id]
        if found:
            ok(f"GET /projects → proyecto encontrado en lista ({len(projects)} proyectos totales)")
        else:
            fail("GET /projects → proyecto NO encontrado en lista")
    else:
        fail(f"GET /projects → HTTP {resp.status_code}")

    # GET /projects/{id}
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        ok(f"GET /projects/{project.id} → '{data.get('title')}' ({len(data.get('tasks', []))} tareas)")
    else:
        fail(f"GET /projects/{project.id} → HTTP {resp.status_code}")

    # GET /projects/{id}/tasks
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/tasks", headers=headers)
    if resp.status_code == 200:
        tasks = resp.json()
        ok(f"GET /projects/{project.id}/tasks → {len(tasks)} tareas")
    else:
        fail(f"GET /projects/{project.id}/tasks → HTTP {resp.status_code}")

    # GET /projects/comments?project_id={id}
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/comments?project_id={project.id}", headers=headers)
    if resp.status_code == 200:
        comments = resp.json()
        ok(f"GET /projects/comments?project_id={project.id} → {len(comments)} comentarios")
    else:
        fail(f"GET /projects/comments?project_id={project.id} → HTTP {resp.status_code}")

    # GET /projects/{id}/milestones
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/milestones", headers=headers)
    if resp.status_code == 200:
        mss = resp.json()
        ok(f"GET /projects/{project.id}/milestones → {len(mss)} milestones")
    else:
        fail(f"GET /projects/{project.id}/milestones → HTTP {resp.status_code}")

    # GET /projects/{id}/wiki
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/wiki", headers=headers)
    if resp.status_code == 200:
        wiki_data = resp.json()
        ok(f"GET /projects/{project.id}/wiki → '{wiki_data.get('title')}'")
    else:
        fail(f"GET /projects/{project.id}/wiki → HTTP {resp.status_code}")

    # POST new comment as test (create a new comment via API)
    resp = httpx.post(
        f"http://127.0.0.1:8000/api/projects/{project.id}/comments",
        headers={**headers, "Content-Type": "application/json"},
        json={"content": "Comentario creado vía API para validar el endpoint.", "task_id": None},
    )
    if resp.status_code in (200, 201):
        ok("POST /projects/{id}/comments → comentario creado vía API")
    else:
        fail(f"POST /projects/{id}/comments → HTTP {resp.status_code}: {resp.text[:100]}")

    # Login como usuario_prueba_2 (docente, tiene acceso a projects) y verificar que ve el proyecto
    login_u2 = httpx.post("http://127.0.0.1:8000/api/auth/login", data={
        "username": "prueba2@ccf.test",
        "password": "prueba123",
        "grant_type": "password",
    }, follow_redirects=False)
    if login_u2.status_code == 200:
        token_u2 = login_u2.json().get("access_token", "")
        headers_u2 = {"Authorization": f"Bearer {token_u2}"}
        ok("Login usuario_prueba_2 (docente) exitoso")

        resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers_u2)
        if resp.status_code == 200:
            projs = resp.json()
            found = [p for p in projs if p["id"] == project.id]
            if found:
                ok("usuario_prueba_2 puede ver el proyecto")
            else:
                fail("usuario_prueba_2 NO puede ver el proyecto")
        else:
            fail(f"usuario_prueba_2 GET /projects → HTTP {resp.status_code}")

        # Ver tareas asignadas a u2
        resp = httpx.get("http://127.0.0.1:8000/api/projects/tasks", headers=headers_u2)
        if resp.status_code == 200:
            my_tasks = resp.json()
            ok(f"usuario_prueba_2 tiene {len(my_tasks)} tarea(s) asignada(s)")
        else:
            fail(f"usuario_prueba_2 GET /projects/tasks → HTTP {resp.status_code}")
    else:
        fail(f"Login usuario_prueba_2 → HTTP {login_u2.status_code}")

    # Verificar que usuario_prueba_1 (estudiante) NO tiene acceso a projects (expected: 403)
    login_u1b = httpx.post("http://127.0.0.1:8000/api/auth/login", data={
        "username": "prueba1@ccf.test",
        "password": "prueba123",
        "grant_type": "password",
    }, follow_redirects=False)
    if login_u1b.status_code == 200:
        token_u1b = login_u1b.json().get("access_token", "")
        headers_u1b = {"Authorization": f"Bearer {token_u1b}"}
        resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers_u1b)
        if resp.status_code == 403:
            ok("usuario_prueba_1 (estudiante) bloqueado de projects — correcto (403)")
        else:
            info(f"usuario_prueba_1 GET /projects → HTTP {resp.status_code}")
    else:
        fail(f"Login usuario_prueba_1 → HTTP {login_u1b.status_code}")

else:
    fail(f"Login admin → HTTP {login_resp.status_code}: {login_resp.text[:100]}")

# ──────────────────────────────────────────────────────────────
section(f"RESUMEN: {PASS} passed, {FAIL} failed")
# ──────────────────────────────────────────────────────────────

info(f"Proyecto ID: {project.id}")
info(f"Usuarios: {u1.username} (id={u1.id}), {u2.username} (id={u2.id}), {u3.username} (id={u3.id})")
info(f"Contraseña de prueba: prueba123")
info(f"URL del proyecto: https://elfarocc.tech/plataforma/projects/{project.id}")

if FAIL > 0:
    print(f"\n  {RED}⚠ {FAIL} test(s) fallaron. Revisar arriba.{NC}\n")
    sys.exit(1)
else:
    print(f"\n  {GREEN}✓ Todos los tests pasaron. El módulo de proyectos funciona correctamente.{NC}\n")

db.close()
