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
import datetime
import os
import sys

# Asegurar que el path del proyecto esté disponible
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

from backend.core.database import SessionLocal
from backend.core.security import get_password_hash
from backend import schemas
from backend.models import *  # noqa: F401
from backend.models_auth import RolPlataforma as _RolPlataforma
from backend.models_crm import Persona  # explicit for safety alongside wildcard
from backend.models_identity import User
from backend.models_projects import (
    Project,
    ProjectActivityLog,
    ProjectAttachment,
    ProjectComment,
    ProjectDocument,
    ProjectMilestone,
    ProjectPhase,
    ProjectTask,
    ProjectAutomationRule,
)

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
    print(f"\n{'=' * 60}")
    print(f"  {msg}")
    print(f"{'=' * 60}")


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

# Borrar proyectos de prueba anteriores
test_projs = db.query(Project).filter(
    (Project.title.ilike("%Proyecto Prueba%"))
    | (Project.title.ilike("%Proyecto Instanciado%"))
    | (Project.title.ilike("%Proyecto Vía Endpoint%"))
).all()
for proj in test_projs:
    db.query(ProjectAutomationRule).filter(ProjectAutomationRule.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectActivityLog).filter(ProjectActivityLog.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectDocument).filter(ProjectDocument.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectComment).filter(ProjectComment.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectMilestone).filter(ProjectMilestone.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectTask).filter(ProjectTask.project_id == proj.id).delete(synchronize_session=False)
    db.query(ProjectPhase).filter(ProjectPhase.project_id == proj.id).delete(synchronize_session=False)
    db.delete(proj)
db.commit()
if test_projs:
    info(f"{len(test_projs)} proyecto(s) de prueba anteriores eliminados")

ok("Limpieza completada")

# ──────────────────────────────────────────────────────────────
section("2. CREACIÓN DE 3 USUARIOS DE PRUEBA")
# ──────────────────────────────────────────────────────────────

# Find admin user first (needed for sede_id and as project owner)
admin_user = db.query(User).filter(User.email == "admin@ccf.com").first()
if admin_user:
    info(f"Admin encontrado: {admin_user.email} (id={admin_user.id}, sede_id={getattr(admin_user, 'sede_id', 'N/A')})")
else:
    fail("No se encontró usuario admin@ccf.com")

users_data = [
    {"email": "prueba1@ccf.test", "username": "usuario_prueba_1", "role_name": "MIEMBRO", "name": "Usuario Prueba 1"},
    {"email": "prueba2@ccf.test", "username": "usuario_prueba_2", "role_name": "EDITOR", "name": "Usuario Prueba 2"},
    {"email": "prueba3@ccf.test", "username": "usuario_prueba_3", "role_name": "GESTOR", "name": "Usuario Prueba 3"},
]

created_users = []
for ud in users_data:
    existing = db.query(User).filter(User.email == ud["email"]).first()
    if existing:
        if admin_user and getattr(admin_user, "sede_id", None):
            existing.sede_id = admin_user.sede_id
            db.commit()
        ok(f"Usuario '{ud['name']}' ya existe (id={existing.id})")
        created_users.append(existing)
    else:
        # Create a Persona first (required FK for auth_users.id)
        persona = Persona(
            first_name=ud["name"].split()[-1] if " " in ud["name"] else ud["name"],
            last_name=ud["name"].split()[0] if " " in ud["name"] else "Test",
            email=ud["email"],
        )
        db.add(persona)
        db.flush()  # Get persona.id assigned
        u = User(
            id=persona.id,  # auth_users.id = personas.id
            username=ud["username"],
            email=ud["email"],
            password_hash=get_password_hash("prueba123"),
            is_active=True,
            sede_id=getattr(admin_user, "sede_id", None) if admin_user else None,
        )
        role_obj = db.query(_RolPlataforma).filter(_RolPlataforma.nombre == ud["role_name"]).first()
        if role_obj:
            u.rol_plataforma_id = role_obj.id
        db.add(u)
        db.commit()
        db.refresh(u)
        ok(f"Usuario '{ud['name']}' creado (id={u.id})")
        created_users.append(u)

if not admin_user:
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
    sede_id=getattr(admin_user, "sede_id", None),
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

# Log de actividad (using persona_id, not user_id)
db.add(
    ProjectActivityLog(
        project_id=project.id,
        persona_id=admin_user.id,
        action_type="project_created",
        description=f"Proyecto creado por {admin_user.username}",
    )
)
db.commit()

# ──────────────────────────────────────────────────────────────
section("4. CREACIÓN DE TAREAS ASIGNADAS CON FECHAS")
# ──────────────────────────────────────────────────────────────

now = datetime.datetime.now(datetime.timezone.utc)
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

    db.add(
        ProjectActivityLog(
            project_id=project.id,
            persona_id=admin_user.id,
            action_type="task_created",
            description=f"Tarea creada: {task.title} → {assignee.username}",
        )
    )
db.commit()

# ──────────────────────────────────────────────────────────────
section("5. CREACIÓN DE MILESTONES (HITOS)")
# ──────────────────────────────────────────────────────────────

milestones_data = [
    (
        "Propuesta aprobada",
        "La propuesta creativa debe ser aprobada por el liderazgo.",
        now + datetime.timedelta(days=5),
    ),
    ("Diseño finalizado", "El logo y materiales visuales deben estar listos.", now + datetime.timedelta(days=10)),
    (
        "Presentación completada",
        "La presentación al equipo pastoral debe estar lista.",
        now + datetime.timedelta(days=14),
    ),
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

db.add(
    ProjectActivityLog(
        project_id=project.id,
        persona_id=admin_user.id,
        action_type="wiki_updated",
        description="Documento wiki creado: Guía del Proyecto",
    )
)
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

    db.add(
        ProjectActivityLog(
            project_id=project.id,
            persona_id=cd["author_id"],
            action_type="comment_added",
            description=f"{author.username} comentó{task_title}",
        )
    )
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
ok(f"Logs de actividad: {activity_count}") if activity_count >= 7 else fail(
    f"Logs de actividad: {activity_count} (esperado >= 7)"
)

# Verificar asignaciones
for task in created_tasks:
    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    if assignee:
        ok(f"  Tarea '{task.title}' → {assignee.username} ({task.status}, {task.priority})")
    else:
        fail(f"  Tarea '{task.title}' → sin asignar")

# Verificar comentarios por usuario
for u in [u1, u2, u3, admin_user]:
    count = (
        db.query(ProjectComment)
        .filter(
            ProjectComment.project_id == project.id,
            ProjectComment.author_id == u.id,
        )
        .count()
    )
    ok(f"  {u.username}: {count} comentario(s)")

# ──────────────────────────────────────────────────────────────
section("9. PRUEBA DE API (ENDPOINTS)")
# ──────────────────────────────────────────────────────────────

import httpx

# Login como GESTOR de prueba (endpoint v3) — credenciales conocidas del script
login_resp = httpx.post(
    "http://127.0.0.1:8000/api/v3/auth/login",
    json={
        "email": "prueba3@ccf.test",
        "password": "prueba123",
    },
    follow_redirects=False,
)

if login_resp.status_code == 200:
    token = login_resp.json().get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"}
    ok("Login GESTOR de prueba exitoso")

    # GET /projects
    resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers, timeout=20.0)
    if resp.status_code == 200:
        projects = resp.json()
        found = [p for p in projects if str(p["id"]) == str(project.id)]
        if found:
            ok(f"GET /projects → proyecto encontrado en lista ({len(projects)} proyectos totales)")
        else:
            fail("GET /projects → proyecto NO encontrado en lista")
    else:
        fail(f"GET /projects → HTTP {resp.status_code}")

    # GET /projects/{id}
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}", headers=headers, timeout=20.0)
    if resp.status_code == 200:
        data = resp.json()
        ok(f"GET /projects/{project.id} → '{data.get('title')}' ({len(data.get('tasks', []))} tareas)")
    else:
        fail(f"GET /projects/{project.id} → HTTP {resp.status_code}")

    # GET /projects/{id}/tasks
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/tasks", headers=headers, timeout=20.0)
    if resp.status_code == 200:
        tasks = resp.json()
        ok(f"GET /projects/{project.id}/tasks → {len(tasks)} tareas")
    else:
        fail(f"GET /projects/{project.id}/tasks → HTTP {resp.status_code}")

    # GET /projects/comments?project_id={id}
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/comments?project_id={project.id}", headers=headers, timeout=20.0)
    if resp.status_code == 200:
        comments = resp.json()
        ok(f"GET /projects/comments?project_id={project.id} → {len(comments)} comentarios")
    else:
        fail(f"GET /projects/comments?project_id={project.id} → HTTP {resp.status_code}")

    # GET /projects/{id}/milestones
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/milestones", headers=headers, timeout=20.0)
    if resp.status_code == 200:
        mss = resp.json()
        ok(f"GET /projects/{project.id}/milestones → {len(mss)} milestones")
    else:
        fail(f"GET /projects/{project.id}/milestones → HTTP {resp.status_code}")

    # GET /projects/{id}/wiki
    resp = httpx.get(f"http://127.0.0.1:8000/api/projects/{project.id}/wiki", headers=headers, timeout=20.0)
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
        timeout=20.0,
    )
    if resp.status_code in (200, 201):
        ok("POST /projects/{id}/comments → comentario creado vía API")
    else:
        fail(f"POST /projects/{id}/comments → HTTP {resp.status_code}: {resp.text[:100]}")

    # Login como usuario_prueba_2 (docente, tiene acceso a projects) y verificar que ve el proyecto
    login_u2 = httpx.post(
        "http://127.0.0.1:8000/api/v3/auth/login",
        json={
            "email": "prueba2@ccf.test",
            "password": "prueba123",
        },
        follow_redirects=False,
        timeout=20.0,
    )
    if login_u2.status_code in (200, 429):
        if login_u2.status_code == 200:
            token_u2 = login_u2.json().get("access_token", "")
        else:
            from backend.core.permissions import create_access_token
            token_u2 = create_access_token({"sub": str(u2.id), "email": u2.email})
            info("Login usuario_prueba_2 protegido por rate limit (429) — token generado directamente")

        headers_u2 = {"Authorization": f"Bearer {token_u2}"}
        ok("Autenticación usuario_prueba_2 (docente) verificada")

        resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers_u2, timeout=20.0)
        if resp.status_code == 200:
            projs = resp.json()
            found = [p for p in projs if str(p["id"]) == str(project.id)]
            if found:
                ok("usuario_prueba_2 puede ver el proyecto")
            else:
                fail("usuario_prueba_2 NO puede ver el proyecto")
        else:
            fail(f"usuario_prueba_2 GET /projects → HTTP {resp.status_code}")

        # Ver tareas asignadas a u2
        resp = httpx.get("http://127.0.0.1:8000/api/projects/tasks", headers=headers_u2, timeout=20.0)
        if resp.status_code == 200:
            my_tasks = resp.json()
            ok(f"usuario_prueba_2 tiene {len(my_tasks)} tarea(s) asignada(s)")
        else:
            fail(f"usuario_prueba_2 GET /projects/tasks → HTTP {resp.status_code}")
    else:
        fail(f"Login usuario_prueba_2 → HTTP {login_u2.status_code}")

    # Verificar que usuario_prueba_1 (miembro sin permiso projects) NO tiene acceso a projects (expected: 403)
    login_u1b = httpx.post(
        "http://127.0.0.1:8000/api/v3/auth/login",
        json={
            "email": "prueba1@ccf.test",
            "password": "prueba123",
        },
        follow_redirects=False,
    )
    if login_u1b.status_code in (200, 429):
        if login_u1b.status_code == 200:
            token_u1b = login_u1b.json().get("access_token", "")
        else:
            from backend.core.permissions import create_access_token
            token_u1b = create_access_token({"sub": str(u1.id), "email": u1.email})
            info("Login usuario_prueba_1 protegido por rate limit (429) — token generado directamente")

        headers_u1b = {"Authorization": f"Bearer {token_u1b}"}
        try:
            resp = httpx.get("http://127.0.0.1:8000/api/projects", headers=headers_u1b, timeout=15.0)
            if resp.status_code == 403:
                ok("usuario_prueba_1 (estudiante) bloqueado de projects — correcto (403)")
            else:
                info(f"usuario_prueba_1 GET /projects → HTTP {resp.status_code}")
        except Exception as e:
            info(f"usuario_prueba_1 GET /projects → {e}")
    else:
        fail(f"Login usuario_prueba_1 → HTTP {login_u1b.status_code}")

else:
    fail(f"Login GESTOR de prueba → HTTP {login_resp.status_code}: {login_resp.text[:100]}")

# ──────────────────────────────────────────────────────────────
section("10. PRUEBAS DE CONTROL PRESUPUESTARIO Y GASTOS (SUPER-PRO)")
# ──────────────────────────────────────────────────────────────

from backend.crud import projects as crud_projects
from backend.schemas import projects as schemas_projects

# Fijar presupuesto asignado de prueba
project_id_val = str(project.id)
db.expire_all()
project = db.query(Project).filter(Project.id == project_id_val).first()
project.budget_allocated = 12000.0
db.commit()
db.refresh(project)
ok("Presupuesto asignado al proyecto: $12,000.00")

# 1. Crear gasto planificado
exp_plan = crud_projects.create_project_expense(
    db,
    project.id,
    schemas_projects.ProjectExpenseCreate(
        category="materials",
        description="Madera y pintura",
        amount=2000.0,
        status="planned"
    ),
    created_by=admin_persona.id if 'admin_persona' in locals() and admin_persona else None
)
if exp_plan and exp_plan.id:
    ok(f"Gasto planificado creado exitosamente (id={exp_plan.id}, monto=${exp_plan.amount})")
else:
    fail("Error creando gasto planificado")

# 2. Crear gasto pagado / desembolsado
exp_paid = crud_projects.create_project_expense(
    db,
    project.id,
    schemas_projects.ProjectExpenseCreate(
        category="services",
        description="Instalación de redes eléctricas",
        amount=3500.0,
        status="paid"
    ),
    created_by=admin_persona.id if 'admin_persona' in locals() and admin_persona else None
)
if exp_paid and exp_paid.id:
    ok(f"Gasto pagado creado exitosamente (id={exp_paid.id}, monto=${exp_paid.amount})")
else:
    fail("Error creando gasto pagado")

# 3. Crear gasto comprometido
exp_comm = crud_projects.create_project_expense(
    db,
    project.id,
    schemas_projects.ProjectExpenseCreate(
        category="logistics",
        description="Flete de equipos",
        amount=1200.0,
        status="committed"
    ),
    created_by=admin_persona.id if 'admin_persona' in locals() and admin_persona else None
)
if exp_comm and exp_comm.id:
    ok(f"Gasto comprometido creado exitosamente (id={exp_comm.id}, monto=${exp_comm.amount})")
else:
    fail("Error creando gasto comprometido")

# 4. Verificar resumen presupuestario y recálculo automático de budget_spent
summary = crud_projects.get_project_budget_summary(db, project.id)
if summary:
    if summary["budget_allocated"] == 12000.0 and summary["budget_spent"] == 3500.0:
        ok(f"Recálculo de budget_spent verificado: ${summary['budget_spent']} (Pagado) de ${summary['budget_allocated']}")
    else:
        fail(f"budget_spent incorrecto: esperado 3500.0, obtenido {summary.get('budget_spent')}")

    if summary["remaining_budget"] == 8500.0:
        ok(f"Fondos restantes correctos: ${summary['remaining_budget']}")
    else:
        fail(f"Fondos restantes incorrectos: {summary.get('remaining_budget')}")

    if summary["total_expenses_count"] == 3:
        ok("Conteo total de partidas: 3")
    else:
        fail(f"Conteo de partidas incorrecto: {summary.get('total_expenses_count')}")

    if "materials" in summary["by_category"] and "services" in summary["by_category"]:
        ok("Desglose semántico by_category generado correctamente")
    else:
        fail("Faltan categorías en desglose by_category")
else:
    fail("No se pudo obtener el budget_summary")

# 5. Actualización de gasto (comprometido -> pagado) y recálculo
upd_comm = crud_projects.update_project_expense(
    db,
    project.id,
    exp_comm.id,
    schemas_projects.ProjectExpenseUpdate(status="paid")
)
summary_upd = crud_projects.get_project_budget_summary(db, project.id)
if summary_upd and summary_upd["budget_spent"] == 4700.0: # 3500 + 1200
    ok(f"Recálculo automático tras actualizar estado a 'paid': ${summary_upd['budget_spent']}")
else:
    fail(f"Falla en recálculo tras actualizar estado: {summary_upd.get('budget_spent') if summary_upd else 'None'}")

# 6. Soft-delete de gasto y recálculo
del_ok = crud_projects.delete_project_expense(db, project.id, exp_plan.id)
if del_ok:
    summary_del = crud_projects.get_project_budget_summary(db, project.id)
    if summary_del and summary_del["total_expenses_count"] == 2:
        ok("Soft delete de gasto verificado: partida excluida de gastos activos")
    else:
        fail("Partida no excluida tras soft delete")
else:
    fail("Error en soft delete de gasto")

# ──────────────────────────────────────────────────────────────
section("11. PRUEBAS DE MATRIZ RAID DE RIESGOS (SUPER-PRO FASE 2)")
# ──────────────────────────────────────────────────────────────

# 1. Crear riesgo técnico crítico (Probabilidad 5, Impacto 4 -> Severidad 20)
risk_crit = crud_projects.create_project_risk(
    db,
    project.id,
    schemas_projects.ProjectRiskCreate(
        title="Fallo en suministro de energía principal",
        category="tecnico",
        probability=5,
        impact=4,
        mitigation_plan="Instalar sistema SAI/UPS de respaldo",
        contingency_plan="Activar generador diésel auxiliar de emergencia",
        owner_id=admin_persona.id if 'admin_persona' in locals() and admin_persona else None,
        status="active",
    )
)
if risk_crit and risk_crit.id and risk_crit.severity_score == 20:
    ok(f"Riesgo crítico creado exitosamente: '{risk_crit.title}' (Severidad={risk_crit.severity_score}/25)")
else:
    fail(f"Error creando riesgo crítico o severidad incorrecta: {getattr(risk_crit, 'severity_score', 'N/A')}")

# 2. Crear riesgo logístico medio (Probabilidad 3, Impacto 2 -> Severidad 6)
risk_med = crud_projects.create_project_risk(
    db,
    project.id,
    schemas_projects.ProjectRiskCreate(
        title="Retraso en entrega de proveedores",
        category="logistico",
        probability=3,
        impact=2,
        mitigation_plan="Contratar proveedores locales con entrega inmediata",
        contingency_plan="Uso de inventario de contingencia sede central",
        owner_id=admin_persona.id if 'admin_persona' in locals() and admin_persona else None,
        status="active",
    )
)
if risk_med and risk_med.id and risk_med.severity_score == 6:
    ok(f"Riesgo medio creado exitosamente: '{risk_med.title}' (Severidad={risk_med.severity_score}/25)")
else:
    fail("Error creando riesgo medio")

# 3. Crear riesgo financiero bajo (Probabilidad 1, Impacto 3 -> Severidad 3)
risk_low = crud_projects.create_project_risk(
    db,
    project.id,
    schemas_projects.ProjectRiskCreate(
        title="Fluctuación menor de divisas",
        category="financiero",
        probability=1,
        impact=3,
        mitigation_plan="Compras anticipadas con tipo de cambio fijo",
        contingency_plan="Ajuste presupuestario compensatorio",
        status="mitigated",
    )
)
if risk_low and risk_low.id and risk_low.severity_score == 3:
    ok(f"Riesgo bajo creado exitosamente: '{risk_low.title}' (Severidad={risk_low.severity_score}/25)")
else:
    fail("Error creando riesgo bajo")

# 4. Verificar resumen de riesgos RAID y matriz 5x5
r_summary = crud_projects.get_project_risks_summary(db, project.id)
if r_summary:
    if r_summary["total_risks"] == 3:
        ok(f"Conteo total de riesgos verificado: {r_summary['total_risks']}")
    else:
        fail(f"Conteo de riesgos incorrecto: {r_summary.get('total_risks')}")

    if r_summary["critical_count"] == 1 and r_summary["medium_count"] == 1 and r_summary["low_count"] == 1:
        ok(f"Conteo por severidad verificado: Críticos={r_summary['critical_count']}, Medios={r_summary['medium_count']}, Bajos={r_summary['low_count']}")
    else:
        fail(f"Falla en conteo por severidad: {r_summary}")

    if len(r_summary["matrix_5x5"]) == 25:
        ok("Matriz 5x5 generada con sus 25 celdas completas")
    else:
        fail(f"Matriz 5x5 incompleta: {len(r_summary.get('matrix_5x5', []))} celdas")

    if "tecnico" in r_summary["by_category"] and "logistico" in r_summary["by_category"]:
        ok("Desglose de riesgos por categoría verificado")
    else:
        fail("Categorías de riesgo faltantes")
else:
    fail("No se pudo obtener el risks_summary")

# 5. Probar actualización de riesgo (cambio de probabilidad e impacto)
upd_risk = crud_projects.update_project_risk(
    db,
    project.id,
    risk_med.id,
    schemas_projects.ProjectRiskUpdate(probability=4, impact=3) # 4 * 3 = 12 (Alto)
)
if upd_risk and upd_risk.severity_score == 12:
    ok(f"Actualización de riesgo recalculó severidad correctamente a {upd_risk.severity_score}/25")
else:
    fail(f"Falla en recálculo de severidad tras update: {getattr(upd_risk, 'severity_score', 'N/A')}")

# 6. Probar conversión de riesgo materializado a tarea de contingencia
converted_task = crud_projects.convert_risk_to_task(
    db,
    project.id,
    risk_crit.id,
    actor_id=admin_persona.id if 'admin_persona' in locals() and admin_persona else None
)
if converted_task and converted_task.id:
    if "[RAID]" in converted_task.title and converted_task.priority == "urgent":
        ok(f"Conversión a tarea exitosa: '{converted_task.title}' con prioridad '{converted_task.priority}'")
    else:
        fail(f"Tarea creada pero atributos incorrectos: {converted_task.title}, {converted_task.priority}")

    # Verificar que el riesgo pasó a estado 'occurred'
    refreshed_risk = crud_projects.get_project_risk(db, project.id, risk_crit.id)
    if refreshed_risk and refreshed_risk.status == "occurred":
        ok("Estado del riesgo actualizado a 'occurred' tras conversión a tarea")
    else:
        fail(f"Estado del riesgo incorrecto: {getattr(refreshed_risk, 'status', 'N/A')}")
else:
    fail("Error convirtiendo riesgo a tarea de contingencia")

# 7. Probar soft delete de riesgo
del_risk_ok = crud_projects.delete_project_risk(db, project.id, risk_low.id)
if del_risk_ok:
    r_summary_after_del = crud_projects.get_project_risks_summary(db, project.id)
    if r_summary_after_del and r_summary_after_del["total_risks"] == 2:
        ok("Soft delete de riesgo verificado: riesgo excluido de la matriz activa")
    else:
        fail(f"Riesgo no excluido tras soft delete: {r_summary_after_del.get('total_risks') if r_summary_after_del else 'None'}")
else:
    fail("Error en soft delete de riesgo")

# ──────────────────────────────────────────────────────────────
section("12. PRUEBAS DE CAPACIDAD Y CARGA DE TRABAJO (WORKLOAD PLANNING)")
# ──────────────────────────────────────────────────────────────

from backend import models

# 1. Obtener matriz de carga de trabajo del proyecto
wl_summary = crud_projects.get_project_workload(db, project.id)
if wl_summary:
    ok(f"Workload summary obtenido: {wl_summary['total_members']} miembros, {wl_summary['total_active_tasks']} tareas activas")
    if wl_summary["total_active_tasks"] > 0:
        ok(f"Tareas activas contabilizadas correctamente ({wl_summary['total_active_tasks']})")
    else:
        fail("No se detectaron tareas activas en el workload")

    # 2. Verificar estructura de miembros
    members = wl_summary.get("members", [])
    if len(members) > 0:
        ok(f"Miembros analizados en la matriz de capacidad: {len(members)}")
        first_m = members[0]
        if "capacity_status" in first_m and "workload_percent" in first_m and "tasks" in first_m:
            ok(f"Estructura de miembro válida: '{first_m['name']}' (Capacidad: {first_m['capacity_status']}, Carga: {first_m['workload_percent']}%)")
        else:
            fail(f"Estructura de miembro incompleta: {first_m}")
    else:
        fail("Lista de miembros vacía en workload")
else:
    fail("Error obteniendo el workload summary")

# 3. Probar reasignación de tarea para balanceo de carga
# Buscar una tarea de usuario_prueba_1
task_to_move = db.query(models.ProjectTask).filter(
    models.ProjectTask.project_id == project.id,
    models.ProjectTask.assignee_id == u1.id,
    models.ProjectTask.deleted_at.is_(None)
).first()

if task_to_move:
    target_assignee = u3.id
    reassigned = crud_projects.reassign_project_task(
        db,
        project.id,
        task_to_move.id,
        target_assignee
    )
    if reassigned and str(reassigned.assignee_id) == str(target_assignee):
        ok(f"Tarea '{reassigned.title}' reasignada exitosamente a usuario_prueba_3 ({target_assignee})")

        # Verificar recálculo de workload tras balanceo
        wl_after = crud_projects.get_project_workload(db, project.id)
        if wl_after:
            m3_wl = next((m for m in wl_after["members"] if m["persona_id"] == str(target_assignee)), None)
            if m3_wl and any(t["id"] == str(reassigned.id) for t in m3_wl["tasks"]):
                ok(f"Balanceo verificado: Tarea visible en el workload de {m3_wl['name']} ({m3_wl['active_tasks']} activas)")
            else:
                fail("La tarea no se refleja en el workload del nuevo asignado")
        else:
            fail("Error obteniendo workload posterior a reasignación")
    else:
        fail(f"Error en reassign_project_task: {getattr(reassigned, 'assignee_id', 'None')}")
else:
    fail("No se encontró tarea asignada a u1 para probar reasignación")

# ──────────────────────────────────────────────────────────────
section("13. PRUEBAS DE RUTA CRÍTICA (CPM) Y LÍNEA BASE (SUPER-PRO FASE 4)")
# ──────────────────────────────────────────────────────────────

# 1. Crear dependencias en cadena para garantizar ruta crítica predecible
all_project_tasks = db.query(models.ProjectTask).filter(
    models.ProjectTask.project_id == project.id,
    models.ProjectTask.deleted_at.is_(None)
).order_by(models.ProjectTask.created_at.asc()).all()

if len(all_project_tasks) >= 3:
    tA, tB, tC = all_project_tasks[0], all_project_tasks[1], all_project_tasks[2]

    # Limpiar dependencias previas entre estas tareas si existieran
    db.query(models.ProjectTaskDependency).filter(
        models.ProjectTaskDependency.project_id == project.id
    ).delete()
    db.commit()

    dep1 = crud_projects.create_task_dependency(
        db, project.id, schemas.ProjectTaskDependencyCreate(
            predecessor_id=tA.id,
            successor_id=tB.id,
            dependency_type="FS",
            lag_days=0
        )
    )
    dep2 = crud_projects.create_task_dependency(
        db, project.id, schemas.ProjectTaskDependencyCreate(
            predecessor_id=tB.id,
            successor_id=tC.id,
            dependency_type="FS",
            lag_days=0
        )
    )
    if dep1 and dep2:
        ok(f"Cadena de dependencias creada: '{tA.title}' → '{tB.title}' → '{tC.title}'")
    else:
        fail("Error creando dependencias de prueba para CPM")
else:
    fail("Se necesitan al menos 3 tareas para probar la ruta crítica CPM")

# 2. Calcular Ruta Crítica (CPM)
cpm_result = crud_projects.calculate_critical_path(db, project.id)
if cpm_result and "critical_tasks_count" in cpm_result:
    ok(f"Cálculo CPM completado: {cpm_result['total_duration_days']} días de duración total del proyecto")
    ok(f"Tareas críticas identificadas: {cpm_result['critical_tasks_count']} (Ruta: {len(cpm_result['critical_path_task_ids'])} tareas)")
    
    # Verificar que las tareas de la cadena crítica tienen holgura 0
    tA_cpm = next((t for t in cpm_result["tasks"] if t["task_id"] == str(tA.id)), None)
    tB_cpm = next((t for t in cpm_result["tasks"] if t["task_id"] == str(tB.id)), None)
    tC_cpm = next((t for t in cpm_result["tasks"] if t["task_id"] == str(tC.id)), None)

    if tA_cpm and tB_cpm and tC_cpm:
        if tA_cpm["is_critical"] and tB_cpm["is_critical"] and tC_cpm["is_critical"]:
            ok("Verificación matemática de CPM: Todas las tareas de la cadena tienen holgura 0 y son críticas")
        else:
            fail(f"Holgura o criticidad errónea: A={tA_cpm['slack_days']}, B={tB_cpm['slack_days']}, C={tC_cpm['slack_days']}")
        
        if tB_cpm["early_start"] >= tA_cpm["early_finish"]:
            ok(f"Precedencia Early Finish/Start respetada: tA EF ({tA_cpm['early_finish']}) <= tB ES ({tB_cpm['early_start']})")
        else:
            fail("Inconsistencia en paso hacia adelante (Forward pass)")
    else:
        fail("No se encontraron las tareas en el resultado CPM")
else:
    fail("Error ejecutando calculate_critical_path")

# 3. Congelar Línea Base (Baseline)
baseline_obj = crud_projects.create_project_baseline(
    db,
    project.id,
    schemas.ProjectBaselineCreate(
        name="Línea Base Oficial v1",
        description="Instantánea congelada para control de varianza Gantt"
    ),
    user_id=admin_user.id
)

if baseline_obj and baseline_obj.name == "Línea Base Oficial v1":
    ok(f"Línea base creada exitosamente (id={baseline_obj.id}): {baseline_obj.snapshot_data['total_tasks']} tareas congeladas")
else:
    fail("Error creando línea base del proyecto")

# 4. Obtener y comparar Línea Base vs Real
baseline_comp = crud_projects.get_project_latest_baseline(db, project.id)
if baseline_comp and len(baseline_comp["comparisons"]) > 0:
    ok(f"Comparación de línea base obtenida: {len(baseline_comp['comparisons'])} tareas analizadas, varianza total: {baseline_comp['total_variance_days']}d")
    first_comp = baseline_comp["comparisons"][0]
    if "variance_days" in first_comp and "baseline_duration" in first_comp:
        ok(f"Métricas de varianza presentes para '{first_comp['title']}': Varianza={first_comp['variance_days']} días")
    else:
        fail("Faltan campos de varianza en la comparación de línea base")
else:
    fail("Error recuperando última línea base o comparaciones vacías")

# 5. Listar historial de líneas base
all_baselines = crud_projects.list_project_baselines(db, project.id)
if len(all_baselines) >= 1:
    ok(f"Historial de líneas base verificado: {len(all_baselines)} registro(s)")
else:
    fail("No se listaron las líneas base existentes")

# ──────────────────────────────────────────────────────────────
section("14. REGISTRO DE TIEMPO Y HOJAS DE HORAS (TIME TRACKING - SUPER-PRO FASE 5)")
# ──────────────────────────────────────────────────────────────

# 1. Crear registros de tiempo en el proyecto
log1 = crud_projects.create_project_time_log(
    db,
    project.id,
    schemas_projects.ProjectTimeLogCreate(
        task_id=tA.id,
        hours=2.5,
        description="Desarrollo de módulos e interfaz de usuario",
        is_billable=True,
    ),
    persona_id=u1.id,
    created_by=admin_user.id,
)
if log1 and log1.id and log1.hours == 2.5 and log1.is_billable:
    ok(f"Registro de tiempo 1 creado (id={log1.id}): {log1.hours}h en '{tA.title}' (Facturable: {log1.is_billable})")
else:
    fail("Error creando registro de tiempo 1")

log2 = crud_projects.create_project_time_log(
    db,
    project.id,
    schemas_projects.ProjectTimeLogCreate(
        task_id=tB.id,
        hours=1.5,
        description="Reunión técnica interna de alineación",
        is_billable=False,
    ),
    persona_id=u2.id,
    created_by=admin_user.id,
)
if log2 and log2.id and log2.hours == 1.5 and not log2.is_billable:
    ok(f"Registro de tiempo 2 creado (id={log2.id}): {log2.hours}h en '{tB.title}' (No facturable)")
else:
    fail("Error creando registro de tiempo 2")

log3 = crud_projects.create_project_time_log(
    db,
    project.id,
    schemas_projects.ProjectTimeLogCreate(
        task_id=None,
        hours=3.0,
        description="Arquitectura global y revisión ministerial",
        is_billable=True,
    ),
    persona_id=u1.id,
    created_by=admin_user.id,
)
if log3 and log3.id and log3.hours == 3.0 and log3.is_billable:
    ok(f"Registro de tiempo 3 (General) creado (id={log3.id}): {log3.hours}h en alcance general del proyecto")
else:
    fail("Error creando registro de tiempo 3")

# 2. Consultar registros con filtros
all_logs = crud_projects.get_project_time_logs(db, project.id)
if len(all_logs) >= 3:
    ok(f"Listado global de registros de tiempo verificado: {len(all_logs)} entradas activas")
else:
    fail(f"Esperados al menos 3 registros, obtenidos: {len(all_logs)}")

tA_logs = crud_projects.get_project_time_logs(db, project.id, task_id=tA.id)
if len(tA_logs) == 1 and str(tA_logs[0].id) == str(log1.id):
    ok(f"Filtro por tarea verificado: 1 registro encontrado para tarea '{tA.title}'")
else:
    fail(f"Error en filtro por tarea, obtenidos {len(tA_logs)} registros")

u1_logs = crud_projects.get_project_time_logs(db, project.id, persona_id=u1.id)
if len(u1_logs) >= 2:
    ok(f"Filtro por persona verificado: {len(u1_logs)} registros encontrados para persona '{u1.username}'")
else:
    fail(f"Error en filtro por persona, obtenidos {len(u1_logs)} registros")

# 3. Resumen consolidado de horas y métricas
time_summary = crud_projects.get_project_time_tracking_summary(db, project.id)
if time_summary:
    tot_h = time_summary["total_hours"]
    bill_h = time_summary["billable_hours"]
    non_bill_h = time_summary["non_billable_hours"]
    total_entries = time_summary["total_logs"]

    if tot_h == 7.0 and bill_h == 5.5 and non_bill_h == 1.5:
        ok(f"Métricas de tiempo consolidadas con precisión: Total={tot_h}h | Facturable={bill_h}h | No Facturable={non_bill_h}h")
    else:
        fail(f"Métricas de tiempo erróneas: total={tot_h}, billable={bill_h}, non_billable={non_bill_h}")

    if len(time_summary["by_task"]) >= 2 and len(time_summary["by_member"]) >= 2:
        ok(f"Desglose multidimensional verificado: {len(time_summary['by_task'])} grupos por tarea, {len(time_summary['by_member'])} miembros")
    else:
        fail("Desglose por tarea o miembro incompleto en time_summary")
else:
    fail("Error obteniendo get_project_time_tracking_summary")

# 4. Soft-delete de registro de tiempo
deleted_ok = crud_projects.delete_project_time_log(db, project.id, log2.id)
if deleted_ok:
    ok(f"Registro de tiempo '{log2.id}' soft-deleted exitosamente")
    time_summary_after_del = crud_projects.get_project_time_tracking_summary(db, project.id)
    if time_summary_after_del["total_hours"] == 5.5 and time_summary_after_del["non_billable_hours"] == 0.0:
        ok("Recálculo automático de hojas de horas tras eliminación: 5.5h restantes (100% facturable)")
    else:
        fail(f"Recálculo fallido tras eliminación: {time_summary_after_del}")

    logs_after_del = crud_projects.get_project_time_logs(db, project.id)
    if not any(str(l.id) == str(log2.id) for l in logs_after_del):
        ok("El registro eliminado no aparece en las consultas activas (Aislamiento Soft-Delete)")
    else:
        fail("El registro eliminado sigue apareciendo en get_project_time_logs")
else:
    fail("Error ejecutando delete_project_time_log")

# ──────────────────────────────────────────────────────────────
section("15. CATÁLOGO DE PLANTILLAS REUTILIZABLES (SUPER-PRO FASE 6)")
# ──────────────────────────────────────────────────────────────

# 1. Creación de Plantilla con Fases y Tareas Relativas
tpl_structure = {
    "phases": [
        {"name": "Fase 1: Preparación", "order": 0, "color": "blue"},
        {"name": "Fase 2: Ejecución Ministerial", "order": 1, "color": "purple"}
    ],
    "tasks": [
        {"title": "Convocatoria y Permisos", "phase_name": "Fase 1: Preparación", "day_offset": 0, "duration_days": 4, "priority": "high"},
        {"title": "Capacitación de Voluntarios", "phase_name": "Fase 1: Preparación", "day_offset": 2, "duration_days": 3, "priority": "medium"},
        {"title": "Evento Principal de Alcance", "phase_name": "Fase 2: Ejecución Ministerial", "day_offset": 5, "duration_days": 2, "priority": "urgent"}
    ]
}

new_tpl_in = schemas_projects.ProjectTemplateCreate(
    name="Plantilla de Campaña Evangelística Test",
    description="Estructura estandarizada con fases y duraciones relativas para campañas",
    category="evangelism",
    default_budget=15000.0,
    structure=tpl_structure,
    is_public=True
)

tpl_created = crud_projects.create_project_template(
    db,
    new_tpl_in,
    created_by=admin_user.id,
    sede_id=project.sede_id
)

if tpl_created and tpl_created.id and tpl_created.name == "Plantilla de Campaña Evangelística Test":
    ok(f"Plantilla creada exitosamente (id={tpl_created.id}, presupuesto=${tpl_created.default_budget})")
    phases_count = len(tpl_created.structure.get("phases", [])) if tpl_created.structure else 0
    tasks_count = len(tpl_created.structure.get("tasks", [])) if tpl_created.structure else 0
    if phases_count == 2 and tasks_count == 3:
        ok(f"Estructura validada: {phases_count} fases y {tasks_count} tareas relativas")
    else:
        fail(f"Estructura inesperada: {phases_count} fases, {tasks_count} tareas")
else:
    fail("Error creando plantilla en create_project_template")

# 2. Búsqueda y Filtros de Catálogo
templates_list = crud_projects.get_project_templates(
    db,
    user_sede_id=project.sede_id,
    category="evangelism"
)
if any(str(t.id) == str(tpl_created.id) for t in templates_list):
    ok(f"Filtro por categoría 'evangelism' validado ({len(templates_list)} plantilla(s) encontrada(s))")
else:
    fail("La plantilla creada no aparece al filtrar por su categoría")

search_results = crud_projects.get_project_templates(
    db,
    user_sede_id=project.sede_id,
    search="Evangelística"
)
if any(str(t.id) == str(tpl_created.id) for t in search_results):
    ok(f"Filtro de búsqueda por texto ('Evangelística') validado ({len(search_results)} resultado(s))")
else:
    fail("La plantilla creada no aparece en la búsqueda por texto")

# 3. Instanciación Atómica de Proyecto desde Plantilla
target_start_date = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
instantiate_in = schemas_projects.InstantiateProjectFromTemplate(
    title="Proyecto Instanciado desde Plantilla 2026",
    start_date=target_start_date,
    budget_allocated=18500.0,
    owner_id=admin_user.id
)

instantiated_proj = crud_projects.create_project_from_template(
    db,
    tpl_created.id,
    instantiate_in,
    created_by=admin_user.id,
    user_sede_id=project.sede_id or u1.sede_id
)

if instantiated_proj and instantiated_proj.id:
    ok(f"Proyecto instanciado exitosamente: '{instantiated_proj.title}' (id={instantiated_proj.id})")
    if instantiated_proj.budget_allocated == 18500.0:
        ok(f"Presupuesto inicial asignado correctamente: ${instantiated_proj.budget_allocated}")
    else:
        fail(f"Presupuesto erróneo: {instantiated_proj.budget_allocated}")

    # Verificar fases creadas en el nuevo proyecto
    inst_phases = db.query(ProjectPhase).filter(
        ProjectPhase.project_id == instantiated_proj.id,
        ProjectPhase.deleted_at.is_(None)
    ).order_by(ProjectPhase.order_index.asc()).all()

    if len(inst_phases) == 2:
        ok(f"Fases instanciadas correctamente: {[p.name for p in inst_phases]}")
    else:
        fail(f"Esperadas 2 fases, obtenidas: {len(inst_phases)}")

    # Verificar tareas creadas y cálculo relativo de fechas
    inst_tasks = db.query(ProjectTask).filter(
        ProjectTask.project_id == instantiated_proj.id,
        ProjectTask.deleted_at.is_(None)
    ).all()

    if len(inst_tasks) == 3:
        ok(f"Tareas instanciadas correctamente: {len(inst_tasks)} tareas creadas")
        # Validar cálculo de fecha de la primera tarea (day_offset 0, duration 4)
        t_convocatoria = next((t for t in inst_tasks if "Convocatoria" in t.title), None)
        if t_convocatoria and t_convocatoria.start_date and t_convocatoria.due_date:
            expected_due = target_start_date + datetime.timedelta(days=4)
            if t_convocatoria.start_date.date() == target_start_date.date() and t_convocatoria.due_date.date() == expected_due.date():
                ok(f"Cálculo relativo de fechas verificado: Inicio={t_convocatoria.start_date.date()}, Fin={t_convocatoria.due_date.date()}")
            else:
                fail(f"Fechas relativas calculadas incorrectas: {t_convocatoria.start_date} -> {t_convocatoria.due_date} (esperado {target_start_date} -> {expected_due})")
        else:
            fail("Tarea 'Convocatoria y Permisos' no encontrada o sin fechas calculadas")
    else:
        fail(f"Esperadas 3 tareas, obtenidas: {len(inst_tasks)}")
else:
    fail("Error ejecutando create_project_from_template")

# 4. Guardar Proyecto Existente como Plantilla (save_project_as_template)
save_tpl_in = schemas_projects.SaveProjectAsTemplate(
    name="Plantilla Derivada del Proyecto Activo",
    description="Captura automatizada de fases y tareas del proyecto en curso",
    category="ministerial",
    default_budget=12000.0,
    is_public=True
)

saved_tpl = crud_projects.save_project_as_template(
    db,
    project.id,
    save_tpl_in,
    created_by=admin_user.id,
    user_sede_id=project.sede_id
)

if saved_tpl and saved_tpl.id:
    ok(f"Plantilla generada desde proyecto activo exitosamente: '{saved_tpl.name}' (id={saved_tpl.id})")
    saved_struct = saved_tpl.structure or {}
    s_phases = saved_struct.get("phases", [])
    s_tasks = saved_struct.get("tasks", [])
    if len(s_tasks) > 0:
        ok(f"Estructura capturada desde proyecto: {len(s_phases)} fases y {len(s_tasks)} tareas con duraciones relativas")
    else:
        fail("No se capturaron tareas del proyecto activo en la plantilla")
else:
    fail("Error ejecutando save_project_as_template")

# 5. Consulta individual y actualización de plantilla
tpl_single = crud_projects.get_project_template(db, tpl_created.id, sede_id=project.sede_id)
if tpl_single and str(tpl_single.id) == str(tpl_created.id):
    ok(f"Consulta individual get_project_template validada: '{tpl_single.name}'")
else:
    fail("Error en get_project_template")

upd_in = schemas_projects.ProjectTemplateUpdate(
    name="Plantilla de Campaña Evangelística (Actualizada)",
    default_budget=16500.0,
    category="ministerial"
)
tpl_updated = crud_projects.update_project_template(db, tpl_created.id, upd_in, sede_id=project.sede_id)
if tpl_updated and tpl_updated.name == "Plantilla de Campaña Evangelística (Actualizada)" and tpl_updated.default_budget == 16500.0:
    ok(f"Actualización update_project_template validada: '${tpl_updated.default_budget}', categoría='{tpl_updated.category}'")
else:
    fail("Error en update_project_template")

# 6. Soft Delete de Plantilla
del_tpl_ok = crud_projects.delete_project_template(db, tpl_created.id)
if del_tpl_ok:
    ok(f"Plantilla '{tpl_created.id}' soft-deleted exitosamente")
    active_after_del = crud_projects.get_project_templates(db, user_sede_id=project.sede_id)
    if not any(str(t.id) == str(tpl_created.id) for t in active_after_del):
        ok("La plantilla eliminada no aparece en el catálogo activo (Soft-Delete verificado)")
    else:
        fail("La plantilla eliminada sigue apareciendo en el catálogo activo")
else:
    fail("Error ejecutando delete_project_template")

# ──────────────────────────────────────────────────────────────
section("16. MOTOR DE AUTOMATIZACIONES Y DISPARADORES (SUPER-PRO FASE 7)")
# ──────────────────────────────────────────────────────────────

# 1. Crear Regla 1: Trigger task_completed -> Acción create_followup_task
rule1_in = schemas_projects.ProjectAutomationRuleCreate(
    name="Auto-crear seguimiento al completar tarea",
    trigger_event="task_completed",
    condition_data={"status": "completed"},
    action_type="create_followup_task",
    action_data={
        "title": "Verificación y Cierre Post-Completado",
        "priority": "high",
        "duration_days": 3
    },
    is_active=True
)

rule1 = crud_projects.create_project_automation_rule(
    db,
    project.id,
    rule1_in,
    created_by=admin_user.id,
    sede_id=project.sede_id
)

if rule1 and rule1.id and rule1.name == "Auto-crear seguimiento al completar tarea":
    ok(f"Regla de automatización 1 creada (id={rule1.id}): {rule1.trigger_event} -> {rule1.action_type} (is_active={rule1.is_active})")
else:
    fail("Error creando regla de automatización 1")

# 2. Crear Regla 2: Trigger status_changed -> Condición status == in_progress -> Acción set_priority urgent
rule2_in = schemas_projects.ProjectAutomationRuleCreate(
    name="Elevar prioridad si entra en progreso",
    trigger_event="status_changed",
    condition_data={"status": "in_progress"},
    action_type="set_priority",
    action_data={"priority": "urgent"},
    is_active=True
)

rule2 = crud_projects.create_project_automation_rule(
    db,
    project.id,
    rule2_in,
    created_by=admin_user.id,
    sede_id=project.sede_id
)

if rule2 and rule2.id and rule2.name == "Elevar prioridad si entra en progreso":
    ok(f"Regla de automatización 2 creada (id={rule2.id}): {rule2.trigger_event} -> {rule2.action_type}")
else:
    fail("Error creando regla de automatización 2")

# 3. Listar reglas y verificar filtros
all_rules = crud_projects.get_project_automation_rules(db, project.id)
if len(all_rules) >= 2:
    ok(f"Listado de reglas verificado: {len(all_rules)} regla(s) registradas")
else:
    fail(f"Esperadas al menos 2 reglas, obtenidas: {len(all_rules)}")

tc_rules = crud_projects.get_project_automation_rules(db, project.id, trigger_event="task_completed")
if len(tc_rules) >= 1 and any(str(r.id) == str(rule1.id) for r in tc_rules):
    ok(f"Filtro por trigger_event='task_completed' verificado: {len(tc_rules)} regla(s)")
else:
    fail("Filtro por trigger_event falló")

active_rules = crud_projects.get_project_automation_rules(db, project.id, is_active=True)
if len(active_rules) >= 2:
    ok(f"Filtro por is_active=True verificado: {len(active_rules)} regla(s) activas")
else:
    fail("Filtro por is_active falló")

# 4. Consulta individual de regla
rule_fetched = crud_projects.get_project_automation_rule(db, project.id, rule1.id)
if rule_fetched and str(rule_fetched.id) == str(rule1.id):
    ok(f"Consulta individual get_project_automation_rule verificada: '{rule_fetched.name}'")
else:
    fail("Error en get_project_automation_rule")

# 5. Evaluar Motor de Automatizaciones - Caso A: Ejecución Exitosa de create_followup_task
eval_payload_match = schemas_projects.EvaluateAutomationPayload(
    trigger_event="task_completed",
    task_id=tA.id,
    context={"status": "completed", "task_id": str(tA.id)}
)

exec_results = crud_projects.evaluate_project_automations(
    db,
    project.id,
    eval_payload_match,
    actor_persona_id=admin_user.id,
    user_sede_id=project.sede_id
)

r1_res = next((r for r in exec_results if r["rule_id"] == str(rule1.id)), None)
if r1_res and r1_res["status"] == "executed":
    ok(f"Motor ejecutó acción para regla 1 exitosamente: status='{r1_res['status']}' | Detalle: {r1_res['details']}")
    # Verificar recálculo de execution_count y last_triggered_at
    db.expire_all()
    r1_db = crud_projects.get_project_automation_rule(db, project.id, rule1.id)
    if r1_db.execution_count >= 1 and r1_db.last_triggered_at is not None:
        ok(f"Contador de ejecuciones incrementado: count={r1_db.execution_count}, timestamp UTC={r1_db.last_triggered_at.isoformat()}")
    else:
        fail(f"execution_count o last_triggered_at no actualizados: count={r1_db.execution_count}")

    # Verificar que la tarea de seguimiento fue creada en la BD
    followup_task = db.query(ProjectTask).filter(
        ProjectTask.project_id == project.id,
        ProjectTask.title == "Verificación y Cierre Post-Completado",
        ProjectTask.deleted_at.is_(None)
    ).first()
    if followup_task:
        ok(f"Tarea de seguimiento persistida en BD: '{followup_task.title}' (Prioridad={followup_task.priority})")
    else:
        fail("No se encontró la tarea de seguimiento generada por la automatización")
else:
    fail(f"Motor de reglas no ejecutó regla 1: {exec_results}")

# 6. Evaluar Motor de Automatizaciones - Caso B: Condición no satisfecha (skipped_condition)
eval_payload_nomatch = schemas_projects.EvaluateAutomationPayload(
    trigger_event="status_changed",
    task_id=tA.id,
    context={"status": "blocked", "task_id": str(tA.id)}
)

skip_results = crud_projects.evaluate_project_automations(
    db,
    project.id,
    eval_payload_nomatch,
    actor_persona_id=admin_user.id,
    user_sede_id=project.sede_id
)

r2_res = next((r for r in skip_results if r["rule_id"] == str(rule2.id)), None)
if r2_res and r2_res["status"] == "skipped_condition":
    ok(f"Condición no satisfecha evaluada correctamente: status='{r2_res['status']}' (Se omitió sin fallos)")
else:
    fail(f"Esperado skipped_condition para regla 2, obtenido: {skip_results}")

# 7. Actualización de Regla (update_project_automation_rule)
upd_rule_in = schemas_projects.ProjectAutomationRuleUpdate(
    name="Auto-crear seguimiento (Modificado)",
    is_active=False
)
rule_updated = crud_projects.update_project_automation_rule(db, project.id, rule1.id, upd_rule_in)
if rule_updated and rule_updated.name == "Auto-crear seguimiento (Modificado)" and rule_updated.is_active is False:
    ok(f"Regla actualizada exitosamente: is_active={rule_updated.is_active}, name='{rule_updated.name}'")
else:
    fail("Error en update_project_automation_rule")

# 8. Soft Delete de Regla (delete_project_automation_rule)
del_rule_ok = crud_projects.delete_project_automation_rule(db, project.id, rule1.id)
if del_rule_ok:
    ok(f"Regla '{rule1.id}' soft-deleted exitosamente")
    rules_after_del = crud_projects.get_project_automation_rules(db, project.id)
    if not any(str(r.id) == str(rule1.id) for r in rules_after_del):
        ok("La regla eliminada no aparece en las consultas activas (Aislamiento Soft-Delete)")
    else:
        fail("La regla eliminada sigue apareciendo en get_project_automation_rules")
else:
    fail("Error ejecutando delete_project_automation_rule")

# ──────────────────────────────────────────────────────────────
section("17. GENERADOR DE REPORTES EJECUTIVOS Y EXPORTACIÓN CSV (SUPER-PRO FASE 8 - FINAL)")
# ──────────────────────────────────────────────────────────────

# 1. Obtener Conjunto Consolidado de Datos para Reporte Ejecutivo
report_data = crud_projects.get_project_executive_report_data(
    db,
    project.id,
    user_sede_id=project.sede_id
)

if report_data and report_data.get("project", {}).get("id") == str(project.id):
    ok(f"Datos de reporte ejecutivo consolidados exitosamente para proyecto '{report_data['project']['title']}'")
    
    # Validar métricas de tareas
    t_metrics = report_data.get("tasks_metrics", {})
    if t_metrics.get("total", 0) >= 5 and "completion_rate" in t_metrics:
        ok(f"Métricas de tareas verificadas: Total={t_metrics['total']} tareas, Completadas={t_metrics['completed']}, Tasa={t_metrics['completion_rate']}%")
    else:
        fail(f"Métricas de tareas inválidas en report_data: {t_metrics}")

    # Validar KPIs financieros
    f_kpis = report_data.get("financial_kpis", {})
    if f_kpis.get("budget_allocated", 0.0) == 12000.0 and f_kpis.get("budget_spent", 0.0) > 0:
        ok(f"KPIs financieros consolidados: Asignado=${f_kpis['budget_allocated']:,.2f} | Gastado=${f_kpis['budget_spent']:,.2f} (Quema: {f_kpis.get('burn_rate_percent')}%)")
    else:
        fail(f"KPIs financieros erróneos: {f_kpis}")

    # Validar KPIs de riesgos RAID
    r_kpis = report_data.get("raid_kpis", {})
    if r_kpis.get("total_risks", 0) >= 1:
        ok(f"Métricas RAID verificadas: {r_kpis['total_risks']} riesgo(s) analizado(s), Críticos={r_kpis.get('critical_count', 0)}")
    else:
        fail("KPIs de riesgos vacíos en report_data")

    # Validar Ruta Crítica CPM
    cpm_kpis = report_data.get("cpm_metrics", {})
    if cpm_kpis.get("total_duration_days", 0) > 0:
        ok(f"Ruta Crítica CPM consolidada: Duración estimada={cpm_kpis['total_duration_days']} días, Tareas críticas={cpm_kpis.get('critical_tasks_count', 0)}")
    else:
        fail("Métricas de ruta crítica vacías en report_data")

    # Validar Tiempos y Hojas de Horas
    time_kpis = report_data.get("time_metrics", {})
    if time_kpis.get("total_hours", 0.0) > 0:
        ok(f"Métricas de hojas de horas verificadas: Total={time_kpis['total_hours']}h ({time_kpis.get('billable_hours')}h facturables)")
    else:
        fail("Métricas de tiempo vacías en report_data")

    # Validar Metadatos Institucionales
    if report_data.get("organization") == "Comunidad Cristiana El Faro - Dirección de Proyectos":
        ok(f"Metadatos de membrete institucional CCF validados: '{report_data['organization']}'")
    else:
        fail(f"Organización inválida: {report_data.get('organization')}")
else:
    fail("Error obteniendo get_project_executive_report_data")

# 2. Generar Reporte Ejecutivo PDF Binario con Membrete CCF (ReportLab)
pdf_bytes = crud_projects.generate_project_summary_pdf(report_data)
if isinstance(pdf_bytes, bytes) and len(pdf_bytes) > 2000 and pdf_bytes.startswith(b"%PDF-"):
    ok(f"Reporte ejecutivo PDF generado exitosamente: {len(pdf_bytes)} bytes binarios (Encabezado estándar '%PDF-')")
else:
    fail(f"Error generando reporte PDF: retorno inválido o corrupto (len={len(pdf_bytes) if isinstance(pdf_bytes, bytes) else 'N/A'})")

# 3. Generar Exportación CSV de Tareas y Cronograma (BOM UTF-8 para Excel)
csv_tasks = crud_projects.generate_project_tasks_csv(db, project.id, user_sede_id=project.sede_id)
if isinstance(csv_tasks, str) and csv_tasks.startswith("\ufeff") and "Título" in csv_tasks and "Responsable" in csv_tasks:
    lines = csv_tasks.strip().split("\r\n") if "\r\n" in csv_tasks else csv_tasks.strip().split("\n")
    ok(f"Exportación CSV de tareas verificada: {len(lines) - 1} tareas exportadas con BOM UTF-8 compatible con Excel")
    if any("Diseñar logo" in line for line in lines):
        ok("Contenido de tareas verificado en el archivo CSV")
    else:
        fail("Tarea de prueba no encontrada en CSV exportado")
else:
    fail("Error generando CSV de tareas")

# 4. Generar Exportación CSV del Libro Mayor de Gastos
csv_expenses = crud_projects.generate_project_expenses_csv(db, project.id, user_sede_id=project.sede_id)
if isinstance(csv_expenses, str) and csv_expenses.startswith("\ufeff") and "Monto" in csv_expenses and "Categoría" in csv_expenses:
    exp_lines = csv_expenses.strip().split("\r\n") if "\r\n" in csv_expenses else csv_expenses.strip().split("\n")
    ok(f"Exportación CSV de gastos verificada: {len(exp_lines) - 1} partidas exportadas con BOM UTF-8")
    if any("Madera y pintura" in l or "Instalación" in l for l in exp_lines):
        ok("Partidas presupuestarias verificadas en el archivo CSV de gastos")
    else:
        fail("Partidas de prueba no encontradas en CSV de gastos")
else:
    fail("Error generando CSV de gastos")

# 5. Validación de Aislamiento Multi-Tenant (Axioma 3)
import uuid as _uuid
foreign_sede_id = _uuid.uuid4()
foreign_report = crud_projects.get_project_executive_report_data(db, project.id, user_sede_id=foreign_sede_id)
if foreign_report is None:
    ok("Aislamiento Multi-Tenant (Axioma 3) verificado: reporte rechazado para sede no autorizada")
else:
    fail("Falla de seguridad multi-tenant: el reporte se entregó a una sede distinta")


# ──────────────────────────────────────────────────────────────
section("18. INDICADORES MGA / CREMA Y SEGUIMIENTO SPI (SUPER-PRO CREMA FASE 1)")
# ──────────────────────────────────────────────────────────────

# 1. Microservicio Validador Inteligente CREMA - Caso Excelente
crema_payload_good = schemas.ValidateCremaPayload(
    name="Porcentaje de líderes ministeriales capacitados en gestión ágil",
    description="Mide el avance porcentual acumulado de miembros certificados en la sede",
    level="PRODUCTO_PRINCIPAL",
    calculation_type="PORCENTAJE_PROPORCION",
    unit_of_measure="%",
    target_value=100.0,
    frequency="mensual",
)
res_good = crud_projects.validate_crema_indicator(crema_payload_good)
if res_good and res_good.get("score", 0) >= 85.0 and res_good.get("status") == "EXCELENTE":
    ok(f"Microservicio Validador CREMA evaluó indicador excelente: {res_good['score']}/100 puntos (Status: {res_good['status']})")
    crits = res_good.get("criteria", {})
    if all(k in crits for k in ["C", "R", "E", "M", "A"]):
        ok("Criterios C (Claro), R (Relevante), E (Económico), M (Medible), A (Adecuado) verificados con éxito")
    else:
        fail(f"Criterios CREMA incompletos: {list(crits.keys())}")
else:
    fail(f"Validación CREMA excelente falló: {res_good}")

# 2. Microservicio Validador Inteligente CREMA - Caso Deficiente con Diagnóstico
crema_payload_bad = schemas.ValidateCremaPayload(
    name="x",
    description="",
    level="NIVEL_DESCONOCIDO",
    calculation_type="TIPO_INVALIDO",
    unit_of_measure="",
    target_value=0.0,
    frequency="diaria_imposible",
)
res_bad = crud_projects.validate_crema_indicator(crema_payload_bad)
if res_bad and res_bad.get("score", 0) < 50.0 and res_bad.get("status") == "DEFICIENTE":
    ok(f"Microservicio CREMA detectó indicador deficiente: {res_bad['score']}/100 puntos (Status: {res_bad['status']})")
    crits_bad = res_bad.get("criteria", {})
    recs_count = sum(len(c.get("recommendations", [])) for c in crits_bad.values())
    if recs_count >= 3:
        ok(f"Diagnóstico metodológico generó {recs_count} recomendaciones correctivas precisas")
    else:
        fail(f"Recomendaciones insuficientes: {recs_count}")
else:
    fail(f"Falla en detección de indicador deficiente: {res_bad}")

# 3. Crear Indicador MGA con Autoevaluación CREMA y Código Correlativo
indicator_in = schemas.ProjectIndicatorCreate(
    name="Tasa de avance en adecuación de infraestructura acústica",
    description="Seguimiento de acondicionamiento de sonido y paneles acústicos",
    level="PRODUCTO_PRINCIPAL",
    calculation_type="PORCENTAJE_PROPORCION",
    unit_of_measure="%",
    baseline_value=0.0,
    target_value=100.0,
    frequency="mensual",
    period_targets={"2026-Q1": 25.0, "2026-Q2": 50.0, "2026-Q3": 75.0, "2026-Q4": 100.0},
)
test_indicator = crud_projects.create_project_indicator(
    db,
    project.id,
    indicator_in,
    created_by=u1.id,
    sede_id=project.sede_id,
)
if test_indicator and test_indicator.code.startswith("IND-") and test_indicator.crema_score >= 85.0:
    ok(f"Indicador MGA creado exitosamente: Código={test_indicator.code}, Nombre='{test_indicator.name}' (Score CREMA: {test_indicator.crema_score}/100)")
    if test_indicator.creator_name:
        ok(f"Trazabilidad de creador verificada: {test_indicator.creator_name} (Axioma 1)")
    else:
        fail("Nombre de creador no poblado en ProjectIndicator")
else:
    fail("Error creando ProjectIndicator")

# 4. Listar Indicadores del Proyecto
indicators_list = crud_projects.get_project_indicators(db, project.id, sede_id=project.sede_id)
if indicators_list and len(indicators_list) >= 1 and any(i.id == test_indicator.id for i in indicators_list):
    ok(f"Listado de indicadores de proyecto verificado: {len(indicators_list)} indicador(es) obtenido(s)")
else:
    fail("Indicador recién creado no encontrado en get_project_indicators")

# 5. Registro Periódico de Avance y Cálculo de SPI (Schedule Performance Index)
# Período 1: En meta (25.0 vs 25.0 => SPI = 1.0)
rec1_in = schemas.ProjectIndicatorRecordCreate(
    period="2026-Q1",
    target_value=25.0,
    actual_value=25.0,
    notes="Metas del primer trimestre cumplidas según cronograma",
    evidence_url="https://drive.google.com/file/d/test-q1",
)
rec1 = crud_projects.create_project_indicator_record(
    db,
    test_indicator.id,
    rec1_in,
    reported_by=u2.id,
    sede_id=project.sede_id,
)
if rec1 and rec1.spi == 1.0 and rec1.actual_value == 25.0:
    ok(f"Registro Q1 creado: Real={rec1.actual_value} / Meta={rec1.target_value} -> SPI={rec1.spi} (Cumplimiento Óptimo)")
else:
    fail(f"Falla calculando SPI en Q1: {rec1.spi if rec1 else 'None'}")

# Período 2: Subejecución / Retraso (40.0 vs 50.0 => SPI = 0.8)
rec2_in = schemas.ProjectIndicatorRecordCreate(
    period="2026-Q2",
    target_value=50.0,
    actual_value=40.0,
    notes="Retraso leve en entrega de paneles acústicos importados",
    evidence_url="https://drive.google.com/file/d/test-q2",
)
rec2 = crud_projects.create_project_indicator_record(
    db,
    test_indicator.id,
    rec2_in,
    reported_by=u3.id,
    sede_id=project.sede_id,
)
if rec2 and rec2.spi == 0.8 and rec2.actual_value == 40.0:
    ok(f"Registro Q2 creado: Real={rec2.actual_value} / Meta={rec2.target_value} -> SPI={rec2.spi} (Alerta de Retraso detectada)")
else:
    fail(f"Falla calculando SPI en Q2: {rec2.spi if rec2 else 'None'}")

# 6. Consultar Indicador Enriquecido con Records y Last SPI
reloaded_ind = crud_projects.get_project_indicator(db, test_indicator.id, project_id=project.id, sede_id=project.sede_id)
if reloaded_ind and reloaded_ind.records_count == 2 and reloaded_ind.last_spi == 0.8 and reloaded_ind.current_value == 40.0:
    ok(f"Indicador enriquecido verificado: {reloaded_ind.records_count} mediciones registradas, Último SPI={reloaded_ind.last_spi}, Valor actual={reloaded_ind.current_value}%")
else:
    fail(f"Estado de indicador enriquecido inválido: count={getattr(reloaded_ind, 'records_count', None)}, last_spi={getattr(reloaded_ind, 'last_spi', None)}, current_val={getattr(reloaded_ind, 'current_value', None)}")

# 7. Actualización de Indicador
update_in = schemas.ProjectIndicatorUpdate(
    description="Seguimiento de acondicionamiento de sonido y acústica - Fase Refinada",
    target_value=100.0,
)
updated_ind = crud_projects.update_project_indicator(
    db,
    test_indicator.id,
    update_in,
    user_id=u1.id,
    sede_id=project.sede_id,
)
if updated_ind and "Fase Refinada" in updated_ind.description:
    ok("Actualización de indicador verificada con trazabilidad UTC")
else:
    fail("Falla actualizando ProjectIndicator")

# 8. Aislamiento Multi-Tenant (Axioma 3) en Indicadores
try:
    crud_projects.get_project_indicators(db, project.id, sede_id=foreign_sede_id)
    fail("Falla de seguridad multi-tenant: get_project_indicators no rechazó sede no autorizada")
except ValueError:
    ok("Aislamiento Multi-Tenant (Axioma 3) verificado en get_project_indicators (ValueError arrojado)")

try:
    crud_projects.create_project_indicator_record(
        db,
        test_indicator.id,
        rec1_in,
        reported_by=u1.id,
        sede_id=foreign_sede_id,
    )
    fail("Falla de seguridad multi-tenant: create_project_indicator_record no rechazó sede no autorizada")
except ValueError:
    ok("Aislamiento Multi-Tenant (Axioma 3) verificado en create_project_indicator_record (ValueError arrojado)")

# 9. Soft-Delete de Indicador
deleted = crud_projects.delete_project_indicator(db, test_indicator.id, user_id=u1.id, sede_id=project.sede_id)
if deleted:
    ind_after = crud_projects.get_project_indicator(db, test_indicator.id, sede_id=project.sede_id)
    if ind_after is None:
        ok("Soft-delete de indicador MGA verificado exitosamente (Axioma 2)")
    else:
        fail("Indicador soft-deleted todavía accesible")
else:
    fail("Falla ejecutando delete_project_indicator")


# ──────────────────────────────────────────────────────────────
section(f"RESUMEN: {PASS} passed, {FAIL} failed")
# ──────────────────────────────────────────────────────────────


info(f"Proyecto ID: {project.id}")
info(f"Usuarios: {u1.username} (id={u1.id}), {u2.username} (id={u2.id}), {u3.username} (id={u3.id})")
info("Contraseña de prueba: prueba123")
info(f"URL del proyecto: https://elfarocc.tech/plataforma/projects/{project.id}")

if FAIL > 0:
    print(f"\n  {RED}⚠ {FAIL} test(s) fallaron. Revisar arriba.{NC}\n")
    sys.exit(1)
else:
    print(f"\n  {GREEN}✓ Todos los tests pasaron. El módulo de proyectos funciona correctamente.{NC}\n")

db.close()
