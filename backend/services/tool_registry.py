"""Tool Registry — Sistema de herramientas para agentes multiagente.

Cada módulo registra sus capacidades como herramientas invocables.
El orquestador puede descubrir y ejecutar herramientas dinámicamente.
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)


class ToolParameter(BaseModel):
    """Definición de un parámetro de herramienta."""
    name: str
    type: str  # "string", "integer", "boolean", "array"
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Definición de una herramienta del sistema."""
    name: str
    description: str
    module: str
    parameters: List[ToolParameter] = []
    returns: str = "dict"


class AgentTool(ABC):
    """Clase base para herramientas de agentes."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def module(self) -> str:
        ...

    @property
    def parameters(self) -> List[ToolParameter]:
        return []

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        ...

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            module=self.module,
            parameters=self.parameters,
        )

    def to_openai_function(self) -> Dict[str, Any]:
        """Convierte a formato OpenAI function calling."""
        props = {}
        required = []
        for p in self.parameters:
            schema: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                schema["enum"] = p.enum
            props[p.name] = schema
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        }


class ToolRegistry:
    """Registro central de herramientas disponibles."""

    def __init__(self):
        self._tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool):
        """Registra una herramienta."""
        self._tools[tool.name] = tool
        log.info("Tool registered: %s (%s)", tool.name, tool.module)

    def unregister(self, name: str):
        """Elimina una herramienta del registro."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[AgentTool]:
        """Obtiene una herramienta por nombre."""
        return self._tools.get(name)

    def list_all(self) -> List[ToolDefinition]:
        """Lista todas las herramientas registradas."""
        return [t.to_definition() for t in self._tools.values()]

    def list_by_module(self, module: str) -> List[ToolDefinition]:
        """Lista herramientas de un módulo específico."""
        return [
            t.to_definition()
            for t in self._tools.values()
            if t.module == module
        ]

    def get_openai_tools(self) -> List[Dict[str, Any]]:
        """Todas las herramientas en formato OpenAI function calling."""
        return [t.to_openai_function() for t in self._tools.values()]

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una herramienta por nombre."""
        tool = self._tools.get(name)
        if not tool:
            return {
                "error": f"Tool '{name}' not found",
                "available_tools": list(self._tools.keys()),
            }
        try:
            result = tool.execute(**kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            log.exception("Tool execution error: %s", name)
            return {"success": False, "error": str(e)}

    @property
    def count(self) -> int:
        return len(self._tools)


# Singleton global
tool_registry = ToolRegistry()


# ──────────────────────────────────────────────
# HERRAMIENTAS CRM
# ──────────────────────────────────────────────

class CRMSearchMember(AgentTool):
    """Busca miembros por nombre, email o teléfono."""

    @property
    def name(self): return "crm_search_member"

    @property
    def description(self):
        return "Search church members by name, email, or phone"

    @property
    def module(self): return "crm"

    @property
    def parameters(self):
        return [
            ToolParameter(
                name="query", type="string",
                description="Search term (name, email, or phone)",
            ),
        ]

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            term = f"%{query}%"
            members = db.query(models.Persona).filter(
                models.Persona.first_name.ilike(term)
                | models.Persona.last_name.ilike(term)
                | models.Persona.email.ilike(term)
                | (models.Persona.phone == query),
            ).limit(10).all()
            return {
                "count": len(members),
                "members": [
                    {
                        "id": m.id,
                        "name": f"{m.first_name} {m.last_name}",
                        "email": m.email,
                        "phone": m.phone,
                        "church_role": m.church_role,
                    }
                    for m in members
                ],
            }
        finally:
            db.close()


class CRMGetMemberProfile(AgentTool):
    """Obtiene el perfil completo de un miembro."""

    @property
    def name(self): return "crm_get_member_profile"

    @property
    def description(self):
        return "Get full profile of a church member by ID"

    @property
    def module(self): return "crm"

    @property
    def parameters(self):
        return [
            ToolParameter(
                name="persona_id", type="string",
                description="Persona ID (UUID)",
            ),
        ]

    def execute(self, persona_id: str, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            persona = db.query(models.Persona).filter(
                models.Persona.id == uuid.UUID(persona_id),
            ).first()
            if not persona:
                return {"error": f"Persona {persona_id} not found"}
            return {
                "id": persona.id,
                "name": f"{persona.first_name} {persona.last_name}",
                "email": persona.email,
                "phone": persona.phone,
                "church_role": persona.church_role,
                "baptized": persona.baptized,
                "ministry": persona.ministry,
                "status": persona.status,
            }
        finally:
            db.close()


# ──────────────────────────────────────────────
# HERRAMIENTAS ACADEMY
# ──────────────────────────────────────────────

class AcademySearchCourse(AgentTool):
    """Busca cursos por nombre o descripción."""

    @property
    def name(self): return "academy_search_course"

    @property
    def description(self):
        return "Search courses by name or description"

    @property
    def module(self): return "academy"

    @property
    def parameters(self):
        return [
            ToolParameter(
                name="query", type="string",
                description="Search term",
            ),
        ]

    def execute(self, query: str, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            term = f"%{query}%"
            courses = db.query(models.Course).filter(
                models.Course.is_published,
            ).filter(
                models.Course.title.ilike(term)
                | (models.Course.description or "").ilike(term),
            ).limit(10).all()
            return {
                "count": len(courses),
                "courses": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "description": (c.description or "")[:200],
                        "modality": c.modality,
                        "duration_hours": c.duration_hours,
                    }
                    for c in courses
                ],
            }
        finally:
            db.close()


class AcademyGetStats(AgentTool):
    """Obtiene estadísticas de la academia."""

    @property
    def name(self): return "academy_get_stats"

    @property
    def description(self):
        return "Get academy statistics (courses, enrollments, certificates)"

    @property
    def module(self): return "academy"

    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            courses = db.query(models.Course).filter(
                models.Course.is_published,
            ).count()
            enrollments = db.query(models.Enrollment).count()
            certificates = db.query(models.Certificate).count()
            return {
                "active_courses": courses,
                "total_enrollments": enrollments,
                "total_certificates": certificates,
            }
        finally:
            db.close()


# ──────────────────────────────────────────────
# HERRAMIENTAS PROJECTS
# ──────────────────────────────────────────────

class ProjectsSearchTask(AgentTool):
    """Busca tareas de proyectos."""

    @property
    def name(self): return "projects_search_task"

    @property
    def description(self):
        return "Search project tasks by title or description"

    @property
    def module(self): return "projects"

    @property
    def parameters(self):
        return [
            ToolParameter(
                name="query", type="string",
                description="Search term",
            ),
            ToolParameter(
                name="status", type="string",
                description="Filter by status (todo, in_progress, review, done)",
                required=False,
            ),
        ]

    def execute(self, query: str, status: str = None, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            term = f"%{query}%"
            q = db.query(models.ProjectTask).filter(
                models.ProjectTask.title.ilike(term)
                | (models.ProjectTask.description or "").ilike(term),
            )
            if status:
                q = q.filter(models.ProjectTask.status == status)
            tasks = q.limit(10).all()
            return {
                "count": len(tasks),
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "status": t.status,
                        "priority": t.priority,
                        "project_id": t.project_id,
                    }
                    for t in tasks
                ],
            }
        finally:
            db.close()


class ProjectsGetStats(AgentTool):
    """Obtiene estadísticas de proyectos."""

    @property
    def name(self): return "projects_get_stats"

    @property
    def description(self):
        return "Get project statistics"

    @property
    def module(self): return "projects"

    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            projects = db.query(models.Project).count()
            active = db.query(models.Project).filter(
                models.Project.status == "active",
            ).count()
            tasks = db.query(models.ProjectTask).count()
            overdue = db.query(models.ProjectTask).filter(
                models.ProjectTask.status.in_(["todo", "in_progress"]),
            ).count()
            return {
                "total_projects": projects,
                "active_projects": active,
                "total_tasks": tasks,
                "potentially_overdue": overdue,
            }
        finally:
            db.close()


# ──────────────────────────────────────────────
# HERRAMIENTAS ANALYTICS
# ──────────────────────────────────────────────

class AnalyticsGetRadar(AgentTool):
    """Obtiene KPIs del Pastor's Radar."""

    @property
    def name(self): return "analytics_get_radar"

    @property
    def description(self):
        return "Get Pastor's Radar KPIs (members, baptisms, students, revenue)"

    @property
    def module(self): return "analytics"

    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend import models
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            return {
                "members": db.query(models.Persona).count(),
                "active_projects": db.query(models.Project).filter(
                    models.Project.status == "active",
                ).count(),
                "courses": db.query(models.Course).filter(
                    models.Course.is_published,
                ).count(),
            }
        finally:
            db.close()


class AnalyticsProactive(AgentTool):
    """Ejecuta análisis proactivo de IA."""

    @property
    def name(self): return "analytics_proactive_analysis"

    @property
    def description(self):
        return "Run proactive AI analysis (attrition risk, bottlenecks, recognition)"

    @property
    def module(self): return "analytics"

    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.analytics.proactive_ia import run_proactive_analysis
        from backend.core.database import SessionLocal

        db = SessionLocal()
        try:
            findings = run_proactive_analysis(db)
            return {"findings": findings, "count": len(findings)}
        finally:
            db.close()


# ──────────────────────────────────────────────
# REGISTRO AUTOMÁTICO
# ──────────────────────────────────────────────

def register_all_tools():
    """Registra todas las herramientas en el registry global."""
    tools = [
        CRMSearchMember(),
        CRMGetMemberProfile(),
        AcademySearchCourse(),
        AcademyGetStats(),
        ProjectsSearchTask(),
        ProjectsGetStats(),
        AnalyticsGetRadar(),
        AnalyticsProactive(),
    ]
    for tool in tools:
        tool_registry.register(tool)
    return tool_registry
