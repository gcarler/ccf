import json
import logging
import uuid
import uuid as _uuid
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import backref, relationship

from backend.models_shared import Base, _utcnow

logger = logging.getLogger(__name__)


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="planning", index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    target_date = Column(DateTime(timezone=True), nullable=True)
    progress_mode = Column(String(20), default="auto_tasks", nullable=False)
    manual_progress = Column(Float, default=0.0, nullable=False)
    budget_allocated = Column(Float, nullable=True)
    budget_spent = Column(Float, nullable=True)
    health_override = Column(String(20), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    owner = relationship("Persona", foreign_keys=[owner_id])
    tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")
    milestones = relationship("ProjectMilestone", back_populates="project", cascade="all, delete-orphan")
    activity_logs = relationship("ProjectActivityLog", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    whiteboard = relationship(
        "ProjectWhiteboard", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    kpis = relationship("ProjectKPI", back_populates="project", cascade="all, delete-orphan")
    dependencies = relationship("ProjectTaskDependency", back_populates="project", cascade="all, delete-orphan")
    expenses = relationship("ProjectExpense", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("ProjectRisk", back_populates="project", cascade="all, delete-orphan")
    baselines = relationship("ProjectBaseline", back_populates="project", cascade="all, delete-orphan")
    time_logs = relationship("ProjectTimeLog", back_populates="project", cascade="all, delete-orphan")
    automations = relationship("ProjectAutomationRule", back_populates="project", cascade="all, delete-orphan")
    indicators = relationship("ProjectIndicator", back_populates="project", cascade="all, delete-orphan")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    components = relationship(
        "ProjectComponent", back_populates="project", cascade="all, delete-orphan", order_by="ProjectComponent.order_index"
    )
    lifecycle = relationship("ProjectLifecycle", back_populates="project", uselist=False, cascade="all, delete-orphan")
    stakeholders = relationship("ProjectStakeholder", back_populates="project", cascade="all, delete-orphan")

    # ``name`` is a thin alias over ``title`` so callers that pass or read
    # ``name`` (e.g. ``tests/test_crud_integration.py::TestProjectsCrud``)
    # work without renaming the canonical column. The setter keeps store/update
    # paths single-source-of-truth on ``title``.
    def __init__(self, **kwargs: Any) -> None:
        contingency_res = kwargs.pop("contingency_reserve", None)
        management_res = kwargs.pop("management_reserve", None)
        management_res_pct = kwargs.pop("management_reserve_pct", None)
        super().__init__(**kwargs)
        if contingency_res is not None:
            self.__dict__["_contingency_reserve"] = round(max(0.0, float(contingency_res)), 2)
        if management_res is not None:
            self.__dict__["_management_reserve"] = round(max(0.0, float(management_res)), 2)
        if management_res_pct is not None:
            self.__dict__["_management_reserve_pct"] = round(max(0.0, float(management_res_pct)), 2)

    @property
    def name(self) -> str | None:
        return self.title

    @name.setter
    def name(self, value: str | None) -> None:
        self.title = value

    @property
    def contingency_reserve(self) -> float | None:
        val = self.__dict__.get("_contingency_reserve")
        return round(max(0.0, float(val)), 2) if val is not None else None

    @contingency_reserve.setter
    def contingency_reserve(self, value: float | None) -> None:
        self.__dict__["_contingency_reserve"] = round(max(0.0, float(value)), 2) if value is not None else None

    @property
    def management_reserve(self) -> float | None:
        val = self.__dict__.get("_management_reserve")
        return round(max(0.0, float(val)), 2) if val is not None else None

    @management_reserve.setter
    def management_reserve(self, value: float | None) -> None:
        self.__dict__["_management_reserve"] = round(max(0.0, float(value)), 2) if value is not None else None

    @property
    def management_reserve_pct(self) -> float:
        val = self.__dict__.get("_management_reserve_pct")
        return round(max(0.0, float(val)), 2) if val is not None else 10.0

    @management_reserve_pct.setter
    def management_reserve_pct(self, value: float | None) -> None:
        self.__dict__["_management_reserve_pct"] = round(max(0.0, float(value)), 2) if value is not None else None


class ProjectLifecycle(Base):
    """Project charter and formal closure record, one lifecycle per project."""

    __tablename__ = "project_lifecycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    sponsor_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    business_case = Column(Text, nullable=True)
    strategic_justification = Column(Text, nullable=True)
    measurable_objectives = Column(JSON, nullable=False, default=list)
    key_assumptions = Column(JSON, nullable=False, default=list)
    key_constraints = Column(JSON, nullable=False, default=list)
    high_level_risks = Column(JSON, nullable=False, default=list)
    preliminary_budget = Column(Float, nullable=True)
    development_approach = Column(String(20), nullable=False, default="hybrid", server_default="hybrid")
    pmo_type = Column(String(20), nullable=False, default="controlling", server_default="controlling")
    charter_status = Column(String(20), nullable=False, default="draft")
    authorized_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    authorized_at = Column(DateTime(timezone=True), nullable=True)
    closure_status = Column(String(20), nullable=False, default="open")
    deliverables_accepted_verified = Column(Boolean, nullable=False, default=False)
    financial_reconciliation_completed = Column(Boolean, nullable=False, default=False)
    final_bac = Column(Float, nullable=True)
    final_ac = Column(Float, nullable=True)
    final_variance = Column(Float, nullable=True)
    operational_handover_to = Column(String(255), nullable=True)
    lessons_learned = Column(JSON, nullable=False, default=list)
    closed_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    wiki_synced = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="lifecycle")
    sponsor = relationship("Persona", foreign_keys=[sponsor_id])
    authorizer = relationship("Persona", foreign_keys=[authorized_by])
    closer = relationship("Persona", foreign_keys=[closed_by])


class ProjectStakeholder(Base):
    """Stakeholder register entry with calculated power/interest quadrant."""

    __tablename__ = "project_stakeholders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    display_name = Column(String(200), nullable=True)
    role_title = Column(String(200), nullable=True)
    organization_or_ministry = Column(String(200), nullable=True)
    power_level = Column(Integer, nullable=False)
    interest_level = Column(Integer, nullable=False)
    quadrant = Column(String(30), nullable=False)
    engagement_level = Column(String(20), nullable=False, default="neutral")
    management_strategy = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="stakeholders")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    project = relationship("Project", back_populates="milestones")


class ProjectActivityLog(Base):
    __tablename__ = "project_activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    project = relationship("Project", back_populates="activity_logs")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectWhiteboard(Base):
    __tablename__ = "project_whiteboards"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    title = Column(String(200), nullable=False, default="Pizarra")
    elements_json = Column(Text, nullable=False, default="[]")
    thumbnail_url = Column(String(500), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="whiteboard")


class ProjectComponent(Base):
    """Componente de la Estructura de Desglose del Trabajo (EDT Nivel 2 / WBS).

    Representa un paquete de trabajo o entregable principal del proyecto según estándares PMI.
    Permite agrupar tareas y gastos para cálculo de EVM (PV, EV, AC, CPI, SPI) sectorizado
    y control de la regla del 100% presupuestal.
    """

    __tablename__ = "project_components"
    __table_args__ = (
        UniqueConstraint("project_id", "code", name="uq_project_components_project_code"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    budget_allocated = Column(Float, default=0.0, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    color = Column(String(20), default="#3b82f6", nullable=True)
    status = Column(String(20), default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="components")
    tasks = relationship("ProjectTask", back_populates="component")
    expenses = relationship("ProjectExpense", back_populates="component")


class ProjectTask(Base):
    __tablename__ = "project_tasks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(
        UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    component_id = Column(
        UUID(as_uuid=True), ForeignKey("project_components.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_index = Column(Integer, default=0)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="todo", index=True)
    priority = Column(String(20), default="medium", nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    node = Column(String(50), nullable=True, index=True)
    physical_progress_pct = Column(Float, default=0.0, nullable=False)
    estimated_hours = Column(Float, default=0.0, nullable=False)
    labels = Column(JSON, default=list, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    project = relationship("Project", back_populates="tasks")
    component = relationship("ProjectComponent", back_populates="tasks")
    assignee = relationship("Persona", foreign_keys=[assignee_id])
    supplies = relationship("TaskSupply", back_populates="task", cascade="all, delete-orphan")
    attachments = relationship("ProjectAttachment", back_populates="task", cascade="all, delete-orphan")
    time_logs = relationship("ProjectTimeLog", back_populates="task", cascade="all, delete-orphan")
    expenses = relationship("ProjectExpense", back_populates="task")
    subtasks = relationship(
        "ProjectTask",
        backref=backref("parent", remote_side="ProjectTask.id"),
        cascade="all, delete-orphan",
    )

    @property
    def actual_hours(self) -> float:
        if "_actual_hours" in self.__dict__ and self.__dict__["_actual_hours"] is not None:
            return float(self.__dict__["_actual_hours"])
        total = 0.0
        try:
            from sqlalchemy.orm import object_session
            sess = object_session(self)
            if sess is not None and self.id is not None:
                logs = (
                    sess.query(ProjectTimeLog)
                    .filter(
                        ProjectTimeLog.task_id == self.id,
                        ProjectTimeLog.deleted_at.is_(None),
                    )
                    .all()
                )
                total += sum(float(getattr(tl, "hours", 0.0) or 0.0) for tl in logs)
                children = (
                    sess.query(ProjectTask)
                    .filter(
                        ProjectTask.parent_id == self.id,
                        ProjectTask.deleted_at.is_(None),
                    )
                    .all()
                )
                for ch in children:
                    total += float(ch.actual_hours or 0.0)
                return round(total, 2)
        except Exception:
            logger.debug("Best-effort actual_hours failed; retaining fallback")
        own_logs = [
            tl for tl in (self.__dict__.get("time_logs") or [])
            if getattr(tl, "deleted_at", None) is None
        ]
        total += sum(float(getattr(tl, "hours", 0.0) or 0.0) for tl in own_logs)
        for sub in (self.__dict__.get("subtasks") or []):
            if getattr(sub, "deleted_at", None) is None:
                total += float(getattr(sub, "actual_hours", 0.0) or 0.0)
        return round(total, 2)

    @actual_hours.setter
    def actual_hours(self, value: float | None) -> None:
        self.__dict__["_actual_hours"] = round(float(value or 0.0), 2) if value is not None else None

    @property
    def actual_cost(self) -> float:
        if "_actual_cost" in self.__dict__ and self.__dict__["_actual_cost"] is not None:
            return float(self.__dict__["_actual_cost"])
        total = 0.0
        try:
            from sqlalchemy.orm import object_session
            sess = object_session(self)
            if sess is not None and self.id is not None:
                exps = (
                    sess.query(ProjectExpense)
                    .filter(
                        ProjectExpense.task_id == self.id,
                        ProjectExpense.deleted_at.is_(None),
                        ProjectExpense.status.in_(["approved", "paid"]),
                    )
                    .all()
                )
                total += sum(float(getattr(e, "amount", 0.0) or 0.0) for e in exps)
                children = (
                    sess.query(ProjectTask)
                    .filter(
                        ProjectTask.parent_id == self.id,
                        ProjectTask.deleted_at.is_(None),
                    )
                    .all()
                )
                for ch in children:
                    total += float(ch.actual_cost or 0.0)
                return round(total, 2)
        except Exception:
            logger.debug("Best-effort actual_cost failed; retaining fallback")
        own_exps = [
            e for e in (self.__dict__.get("expenses") or [])
            if getattr(e, "deleted_at", None) is None and getattr(e, "status", None) in ("approved", "paid")
        ]
        total += sum(float(getattr(e, "amount", 0.0) or 0.0) for e in own_exps)
        return round(total, 2)

    @actual_cost.setter
    def actual_cost(self, value: float | None) -> None:
        self.__dict__["_actual_cost"] = round(float(value or 0.0), 2) if value is not None else None


class ProjectAttachment(Base):
    __tablename__ = "project_attachments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    task = relationship("ProjectTask", back_populates="attachments")
    uploader = relationship("Persona", foreign_keys=[uploader_id])


class TaskSupply(Base):
    __tablename__ = "task_supplies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    item_name = Column(String(200), nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("ProjectTask", back_populates="supplies")

    def __init__(self, **kwargs: Any) -> None:
        u_cost = kwargs.pop("unit_cost", None)
        t_cost = kwargs.pop("total_cost", None)
        exp_id = kwargs.pop("expense_id", None)
        super().__init__(**kwargs)
        qty = max(1, int(self.quantity or 1))
        if u_cost is not None or t_cost is not None:
            uc = float(u_cost or 0.0)
            tc = float(t_cost) if (t_cost is not None and float(t_cost) > 0) else round(uc * qty, 2)
            if uc == 0.0 and tc > 0:
                uc = round(tc / qty, 2)
            self.__dict__["_unit_cost"] = round(uc, 2)
            self.__dict__["_total_cost"] = round(tc, 2)
        if exp_id is not None:
            self.__dict__["_expense_id"] = str(exp_id)

    def _resolve_linked_expense(self) -> Optional["ProjectExpense"]:
        try:
            from sqlalchemy.orm import object_session
            sess = object_session(self)
            if sess is not None and self.id is not None and self.task_id is not None:
                tag = f"[supply_id:{self.id}]"
                return (
                    sess.query(ProjectExpense)
                    .filter(
                        ProjectExpense.task_id == self.task_id,
                        ProjectExpense.category == "supplies",
                        ProjectExpense.deleted_at.is_(None),
                        ProjectExpense.description.contains(tag),
                    )
                    .first()
                )
        except Exception:
            logger.debug("Best-effort _resolve_linked_expense failed; retaining fallback")
        return None

    @property
    def unit_cost(self) -> float:
        if "_unit_cost" in self.__dict__ and self.__dict__["_unit_cost"] is not None:
            return float(self.__dict__["_unit_cost"])
        exp = self._resolve_linked_expense()
        if exp is not None:
            qty = max(1, int(self.quantity or 1))
            tc = float(exp.amount or 0.0)
            uc = round(tc / qty, 2)
            self.__dict__["_unit_cost"] = uc
            self.__dict__["_total_cost"] = round(tc, 2)
            self.__dict__["_expense_id"] = str(exp.id)
            return uc
        return 0.0

    @unit_cost.setter
    def unit_cost(self, value: float | None) -> None:
        self.__dict__["_unit_cost"] = round(float(value or 0.0), 2) if value is not None else 0.0

    @property
    def total_cost(self) -> float:
        if "_total_cost" in self.__dict__ and self.__dict__["_total_cost"] is not None:
            return float(self.__dict__["_total_cost"])
        if "_unit_cost" in self.__dict__ and self.__dict__["_unit_cost"]:
            qty = max(1, int(self.quantity or 1))
            return round(float(self.__dict__["_unit_cost"]) * qty, 2)
        exp = self._resolve_linked_expense()
        if exp is not None:
            qty = max(1, int(self.quantity or 1))
            tc = round(float(exp.amount or 0.0), 2)
            self.__dict__["_total_cost"] = tc
            self.__dict__["_unit_cost"] = round(tc / qty, 2)
            self.__dict__["_expense_id"] = str(exp.id)
            return tc
        return 0.0

    @total_cost.setter
    def total_cost(self, value: float | None) -> None:
        self.__dict__["_total_cost"] = round(float(value or 0.0), 2) if value is not None else 0.0

    @property
    def expense_id(self) -> Optional[str]:
        if "_expense_id" in self.__dict__ and self.__dict__["_expense_id"] is not None:
            return str(self.__dict__["_expense_id"])
        exp = self._resolve_linked_expense()
        if exp is not None:
            self.__dict__["_expense_id"] = str(exp.id)
            return str(exp.id)
        return None

    @expense_id.setter
    def expense_id(self, value: object) -> None:
        self.__dict__["_expense_id"] = str(value) if value else None


class ProjectComment(Base):
    __tablename__ = "project_comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    attachments = Column(JSON, default=list, nullable=False)
    mentions = Column(JSON, default=list, nullable=False)
    is_resolved = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False, nullable=False, index=True)
    pinned_at = Column(DateTime(timezone=True), nullable=True)
    pinned_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    author = relationship("Persona", foreign_keys=[author_id])
    pinner = relationship("Persona", foreign_keys=[pinned_by])


class ProjectPhase(Base):
    __tablename__ = "project_phases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False)
    slug = Column(String(20), nullable=False)
    color = Column(String(20), default="#94a3b8")
    order_index = Column(Integer, default=0)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship(
        "Project",
        backref=backref("phases", order_by="ProjectPhase.order_index", cascade="all, delete-orphan"),
    )


class ProjectInboxState(Base):
    __tablename__ = "project_inbox_state"
    __table_args__ = (UniqueConstraint("persona_id", "item_id", name="uq_persona_project_item"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(String(80), nullable=False)
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class ProjectMember(Base):
    """Membresía del equipo de un proyecto (F4).

    Persona invitada a colaborar en un proyecto, distinta de ``Project.owner_id``
    (responsable). Persiste la pertenencia al equipo para alimentar la vista
    ``/plataforma/projects/team`` y el flujo de invitación del botón "Invitar".
    """

    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "persona_id", name="uq_project_member_persona"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="member")
    invited_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="members")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectDocument(Base):
    __tablename__ = "project_documents"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="Wiki")
    content = Column(Text, nullable=False, default="")
    author_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    last_edited_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project")
    author = relationship("Persona", foreign_keys=[author_id])


class ProjectKPI(Base):
    __tablename__ = "project_kpis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0.0, nullable=False)
    unit = Column(String(30), default="unidades", nullable=False)
    category = Column(String(50), default="impact", nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="kpis")

    @property
    def source_type(self) -> str:
        val = self.__dict__.get("_source_type")
        if val:
            return str(val)
        _, meta = decode_kpi_meta(self.__dict__.get("description"))
        return str(meta.get("source_type") or "manual")

    @source_type.setter
    def source_type(self, value: str | None) -> None:
        self.__dict__["_source_type"] = str(value).strip() if value else "manual"

    @property
    def component_id(self) -> str | None:
        val = self.__dict__.get("_component_id")
        if val:
            return str(val)
        _, meta = decode_kpi_meta(self.__dict__.get("description"))
        comp = meta.get("component_id")
        return str(comp) if comp else None

    @component_id.setter
    def component_id(self, value: object) -> None:
        self.__dict__["_component_id"] = str(value) if value else None


_KPI_META_PREFIX = "<!--ccf_kpi_meta:"
_KPI_META_SUFFIX = "-->"


def decode_kpi_meta(raw_description: str | None) -> tuple[str | None, dict[str, Any]]:
    if not raw_description or not isinstance(raw_description, str):
        return raw_description, {}
    idx = raw_description.rfind(_KPI_META_PREFIX)
    if idx == -1 or not raw_description.endswith(_KPI_META_SUFFIX):
        return raw_description, {}
    json_part = raw_description[idx + len(_KPI_META_PREFIX) : -len(_KPI_META_SUFFIX)]
    clean_desc = raw_description[:idx].rstrip()
    try:
        parsed = json.loads(json_part)
        if isinstance(parsed, dict):
            return (clean_desc if clean_desc else None), parsed
    except Exception:
        logger.debug("Best-effort decode_kpi_meta failed; retaining fallback")
    return raw_description, {}


def encode_kpi_meta(
    description: str | None,
    source_type: str | None = None,
    component_id: object = None,
) -> str | None:
    clean_desc, existing_meta = decode_kpi_meta(description)
    src = str(source_type or existing_meta.get("source_type") or "manual").strip()
    comp = str(component_id) if component_id else existing_meta.get("component_id")
    if src == "manual" and not comp:
        return clean_desc
    meta = {"source_type": src, "component_id": str(comp) if comp else None}
    tag = f"{_KPI_META_PREFIX}{json.dumps(meta, separators=(',', ':'))}{_KPI_META_SUFFIX}"
    if clean_desc:
        return f"{clean_desc}\n{tag}"
    return tag



class ProjectTaskDependency(Base):
    __tablename__ = "project_task_dependencies"
    __table_args__ = (UniqueConstraint("predecessor_id", "successor_id", name="uq_project_task_dependency_pair"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    predecessor_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    successor_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    dependency_type = Column(String(10), default="FS", nullable=False)
    lag_days = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="dependencies")
    predecessor = relationship("ProjectTask", foreign_keys=[predecessor_id])
    successor = relationship("ProjectTask", foreign_keys=[successor_id])


class ProjectExpense(Base):
    __tablename__ = "project_expenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    component_id = Column(
        UUID(as_uuid=True), ForeignKey("project_components.id", ondelete="SET NULL"), nullable=True, index=True
    )
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category = Column(String(50), default="general", nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Float, default=0.0, nullable=False)
    date = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    receipt_url = Column(String(500), nullable=True)
    status = Column(String(20), default="planned", nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="expenses")
    component = relationship("ProjectComponent", back_populates="expenses")
    task = relationship("ProjectTask", back_populates="expenses")
    creator = relationship("Persona", foreign_keys=[created_by])

    def __init__(self, **kwargs: Any) -> None:
        auto_gen = kwargs.pop("is_auto_generated", None)
        super().__init__(**kwargs)
        if auto_gen is not None:
            self.__dict__["_is_auto_generated"] = bool(auto_gen)

    @property
    def is_auto_generated(self) -> bool:
        if "_is_auto_generated" in self.__dict__ and self.__dict__["_is_auto_generated"] is not None:
            return bool(self.__dict__["_is_auto_generated"])
        return bool(self.description and "[supply_id:" in str(self.description))

    @is_auto_generated.setter
    def is_auto_generated(self, value: bool) -> None:
        self.__dict__["_is_auto_generated"] = bool(value)


_RISK_META_PREFIX = "<!--ccf_risk_meta:"
_RISK_META_SUFFIX = "-->"


def decode_risk_meta(raw_text: str | None) -> tuple[str | None, dict[str, Any]]:
    if not raw_text or not isinstance(raw_text, str):
        return raw_text, {}
    idx = raw_text.rfind(_RISK_META_PREFIX)
    if idx == -1 or not raw_text.endswith(_RISK_META_SUFFIX):
        return raw_text, {}
    json_part = raw_text[idx + len(_RISK_META_PREFIX) : -len(_RISK_META_SUFFIX)]
    clean_text = raw_text[:idx].rstrip()
    try:
        parsed = json.loads(json_part)
        if isinstance(parsed, dict):
            return (clean_text if clean_text else None), parsed
    except Exception:
        logger.debug("Best-effort decode_risk_meta failed; retaining fallback")
    return raw_text, {}


def encode_risk_meta(
    contingency_plan: str | None,
    risk_type: str | None = None,
    probability_pct: float | None = None,
    financial_impact: float | None = None,
) -> str | None:
    clean_text, existing_meta = decode_risk_meta(contingency_plan)
    r_type = str(risk_type or existing_meta.get("risk_type") or "threat").strip().lower()
    if r_type not in ("threat", "opportunity"):
        r_type = "threat"
    p_pct = (
        round(max(0.0, min(100.0, float(probability_pct))), 2)
        if probability_pct is not None
        else existing_meta.get("probability_pct")
    )
    f_imp = (
        round(max(0.0, float(financial_impact)), 2)
        if financial_impact is not None
        else float(existing_meta.get("financial_impact") or 0.0)
    )
    if r_type == "threat" and p_pct is None and f_imp == 0.0:
        return clean_text
    meta: dict[str, Any] = {
        "risk_type": r_type,
        "probability_pct": p_pct,
        "financial_impact": f_imp,
    }
    tag = f"{_RISK_META_PREFIX}{json.dumps(meta, separators=(',', ':'))}{_KPI_META_SUFFIX}"
    if clean_text:
        return f"{clean_text}\n{tag}"
    return tag


class ProjectRisk(Base):
    __tablename__ = "project_risks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(50), default="tecnico", nullable=False)
    probability = Column(Integer, default=3, nullable=False)
    impact = Column(Integer, default=3, nullable=False)
    severity_score = Column(Integer, default=9, nullable=False)
    mitigation_plan = Column(Text, nullable=True)
    contingency_plan = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), default="active", nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="risks")
    owner = relationship("Persona", foreign_keys=[owner_id])

    def __init__(self, **kwargs: Any) -> None:
        r_type = kwargs.pop("risk_type", None)
        p_pct = kwargs.pop("probability_pct", None)
        f_imp = kwargs.pop("financial_impact", None)
        kwargs.pop("emv", None)
        super().__init__(**kwargs)
        if r_type is not None:
            self.risk_type = r_type
        if p_pct is not None:
            self.probability_pct = p_pct
        if f_imp is not None:
            self.financial_impact = f_imp

    def _sync_risk_meta(self) -> None:
        raw_plan = self.__dict__.get("contingency_plan")
        _, meta = decode_risk_meta(raw_plan)
        r_type = self.__dict__.get("_risk_type") or meta.get("risk_type") or "threat"
        p_pct = self.__dict__.get("_probability_pct")
        if p_pct is None and "probability_pct" in meta:
            p_pct = meta.get("probability_pct")
        f_imp = self.__dict__.get("_financial_impact")
        if f_imp is None and "financial_impact" in meta:
            f_imp = meta.get("financial_impact")
        self.contingency_plan = encode_risk_meta(
            raw_plan,
            risk_type=str(r_type),
            probability_pct=float(p_pct) if p_pct is not None else None,
            financial_impact=float(f_imp) if f_imp is not None else 0.0,
        )

    @property
    def risk_type(self) -> str:
        val = self.__dict__.get("_risk_type")
        if val in ("threat", "opportunity"):
            return str(val)
        _, meta = decode_risk_meta(self.__dict__.get("contingency_plan"))
        m_val = str(meta.get("risk_type") or "threat").strip().lower()
        return "opportunity" if m_val == "opportunity" else "threat"

    @risk_type.setter
    def risk_type(self, value: str | None) -> None:
        norm = "opportunity" if str(value or "").strip().lower() == "opportunity" else "threat"
        self.__dict__["_risk_type"] = norm
        self._sync_risk_meta()

    @property
    def probability_pct(self) -> float:
        val = self.__dict__.get("_probability_pct")
        if val is not None:
            return round(max(0.0, min(100.0, float(val))), 2)
        _, meta = decode_risk_meta(self.__dict__.get("contingency_plan"))
        m_val = meta.get("probability_pct")
        if m_val is not None:
            return round(max(0.0, min(100.0, float(m_val))), 2)
        prob_scale = int(self.probability if self.probability is not None else 3)
        prob_scale = max(1, min(5, prob_scale))
        return round(prob_scale * 20.0, 2)

    @probability_pct.setter
    def probability_pct(self, value: float | None) -> None:
        if value is None:
            self.__dict__["_probability_pct"] = None
        else:
            self.__dict__["_probability_pct"] = round(max(0.0, min(100.0, float(value))), 2)
        self._sync_risk_meta()

    @property
    def financial_impact(self) -> float:
        val = self.__dict__.get("_financial_impact")
        if val is not None:
            return round(max(0.0, float(val)), 2)
        _, meta = decode_risk_meta(self.__dict__.get("contingency_plan"))
        m_val = meta.get("financial_impact")
        if m_val is not None:
            return round(max(0.0, float(m_val)), 2)
        return 0.0

    @financial_impact.setter
    def financial_impact(self, value: float | None) -> None:
        self.__dict__["_financial_impact"] = round(max(0.0, float(value or 0.0)), 2)
        self._sync_risk_meta()

    @property
    def emv(self) -> float:
        raw_emv = (float(self.probability_pct) / 100.0) * float(self.financial_impact)
        if abs(raw_emv) < 1e-9:
            return 0.0
        signed = -abs(raw_emv) if self.risk_type == "opportunity" else abs(raw_emv)
        return round(signed, 2)

    @emv.setter
    def emv(self, value: float | None) -> None:
        self.__dict__["_emv"] = round(float(value), 2) if value is not None else 0.0


class ProjectBaseline(Base):
    __tablename__ = "project_baselines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), default="Línea Base Inicial", nullable=False)
    description = Column(Text, nullable=True)
    snapshot_data = Column(JSON, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="baselines")
    creator = relationship("Persona", foreign_keys=[created_by])


class ProjectTimeLog(Base):
    __tablename__ = "project_time_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=True, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False, index=True)
    hours = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    description = Column(Text, nullable=True)
    is_billable = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="time_logs")
    task = relationship("ProjectTask", back_populates="time_logs")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectTemplate(Base):
    __tablename__ = "project_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="general", nullable=False, index=True)
    default_budget = Column(Float, default=0.0, nullable=False)
    structure = Column(JSON, nullable=False, default=dict)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    is_public = Column(Boolean, default=True, nullable=False, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    creator = relationship("Persona", foreign_keys=[created_by])


class ProjectAutomationRule(Base):
    __tablename__ = "project_automation_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_event = Column(String(50), nullable=False, index=True)
    condition_data = Column(JSON, nullable=False, default=dict)
    action_type = Column(String(50), nullable=False)
    action_data = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    execution_count = Column(Integer, default=0, nullable=False)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="automations")
    creator = relationship("Persona", foreign_keys=[created_by])


class ProjectIndicator(Base):
    __tablename__ = "project_indicators"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    level = Column(String(50), default="PRODUCTO_PRINCIPAL", nullable=False, index=True)
    calculation_type = Column(String(50), default="ABSOLUTO_ACUMULADO", nullable=False, index=True)
    unit_of_measure = Column(String(50), nullable=True)
    baseline_value = Column(Float, default=0.0, nullable=False)
    target_value = Column(Float, default=0.0, nullable=False)
    current_value = Column(Float, default=0.0, nullable=False)
    frequency = Column(String(50), default="mensual", nullable=False)
    period_targets = Column(JSON, default=dict, nullable=False)
    crema_score = Column(Float, nullable=True)
    crema_evaluation = Column(JSON, default=dict, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="indicators")
    creator = relationship("Persona", foreign_keys=[created_by])
    records = relationship("ProjectIndicatorRecord", back_populates="indicator", cascade="all, delete-orphan")

    @property
    def source_type(self) -> str:
        val = self.__dict__.get("_source_type")
        if val:
            return str(val)
        eval_dict = self.crema_evaluation if isinstance(self.crema_evaluation, dict) else {}
        link = eval_dict.get("execution_link") if isinstance(eval_dict.get("execution_link"), dict) else {}
        src = link.get("source_type")
        return str(src) if src else "manual"

    @source_type.setter
    def source_type(self, value: str | None) -> None:
        clean = str(value).strip() if value else "manual"
        self.__dict__["_source_type"] = clean
        eval_dict = dict(self.crema_evaluation) if isinstance(self.crema_evaluation, dict) else {}
        link = dict(eval_dict.get("execution_link")) if isinstance(eval_dict.get("execution_link"), dict) else {}
        link["source_type"] = clean
        eval_dict["execution_link"] = link
        self.crema_evaluation = eval_dict

    @property
    def component_id(self) -> str | None:
        val = self.__dict__.get("_component_id")
        if val:
            return str(val)
        eval_dict = self.crema_evaluation if isinstance(self.crema_evaluation, dict) else {}
        link = eval_dict.get("execution_link") if isinstance(eval_dict.get("execution_link"), dict) else {}
        comp = link.get("component_id")
        return str(comp) if comp else None

    @component_id.setter
    def component_id(self, value: object) -> None:
        clean = str(value) if value else None
        self.__dict__["_component_id"] = clean
        eval_dict = dict(self.crema_evaluation) if isinstance(self.crema_evaluation, dict) else {}
        link = dict(eval_dict.get("execution_link")) if isinstance(eval_dict.get("execution_link"), dict) else {}
        link["component_id"] = clean
        eval_dict["execution_link"] = link
        self.crema_evaluation = eval_dict


class ProjectIndicatorRecord(Base):
    __tablename__ = "project_indicator_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_id = Column(UUID(as_uuid=True), ForeignKey("project_indicators.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(String(50), nullable=False, index=True)
    target_value = Column(Float, default=0.0, nullable=False)
    actual_value = Column(Float, default=0.0, nullable=False)
    spi = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    evidence_url = Column(String(500), nullable=True)
    reported_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    reported_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    indicator = relationship("ProjectIndicator", back_populates="records")
    reporter = relationship("Persona", foreign_keys=[reported_by])


class ProjectUserFavorite(Base):
    __tablename__ = "project_user_favorites"
    __table_args__ = (
        UniqueConstraint("persona_id", "entity_type", "entity_id", name="uq_project_user_favorites_entity"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(50), default="task", nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    project = relationship("Project")
    persona = relationship("Persona", foreign_keys=[persona_id])


class ProjectFile(Base):
    """Bóveda documental y visor universal embebido (Google Drive, PDFs, imágenes)."""
    __tablename__ = "project_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="general", nullable=False, index=True)
    file_source = Column(String(50), default="local", nullable=False, index=True)  # 'local', 'drive', 'dropbox', 'onedrive'
    file_url = Column(Text, nullable=False)
    file_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    drive_file_id = Column(String(255), nullable=True, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    phase_id = Column(UUID(as_uuid=True), ForeignKey("project_phases.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="RESTRICT"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    project = relationship("Project", back_populates="files")
    task = relationship("ProjectTask", backref="project_files")
    phase = relationship("ProjectPhase", backref="project_files")
    uploader = relationship("Persona", foreign_keys=[uploaded_by])
    sede = relationship("Sede", foreign_keys=[sede_id])

    @property
    def embed_url(self) -> Optional[str]:
        """Calcula dinámicamente la URL embebible para iframes."""
        if self.file_source == "drive" or (self.file_url and ("drive.google.com" in self.file_url or "docs.google.com" in self.file_url)):
            if self.drive_file_id:
                url_str = (self.file_url or "").lower()
                if "document/d/" in url_str:
                    return f"https://docs.google.com/document/d/{self.drive_file_id}/preview"
                elif "spreadsheets/d/" in url_str:
                    return f"https://docs.google.com/spreadsheets/d/{self.drive_file_id}/preview"
                elif "presentation/d/" in url_str:
                    return f"https://docs.google.com/presentation/d/{self.drive_file_id}/preview"
                elif "forms/d/" in url_str:
                    return f"https://docs.google.com/forms/d/{self.drive_file_id}/viewform?embedded=true"
                return f"https://drive.google.com/file/d/{self.drive_file_id}/preview"
        return self.file_url

class ProjectChangeRequest(Base):
    """Solicitud de Cambio Formal (Change Request) del proceso CCB de PMI Vol 6 sec 5.

    Trazabilidad inmutable: los campos de impacto no se mutan tras la creacion;
    el dictamen del Comite se registra en status/review_notes/reviewed_by/reviewed_at
    y el Re-baseline automatico queda vinculado en resulting_baseline_id.
    """

    __tablename__ = "project_change_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    justification = Column(Text, nullable=False)
    change_type = Column(
        String(20), default="integrated", nullable=False, index=True
    )  # scope | schedule | budget | integrated
    cost_impact_delta = Column(Float, default=0.0, nullable=False)
    schedule_impact_days = Column(Integer, default=0, nullable=False)
    scope_impact_summary = Column(Text, nullable=True)
    status = Column(String(20), default="pending_ccb", nullable=False, index=True)
    # pending_ccb | approved | rejected
    requested_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="RESTRICT"), nullable=False, index=True)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resulting_baseline_id = Column(
        UUID(as_uuid=True), ForeignKey("project_baselines.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)

    project = relationship("Project", backref="change_requests")
    requester = relationship("Persona", foreign_keys=[requested_by])
    reviewer = relationship("Persona", foreign_keys=[reviewed_by])
    resulting_baseline = relationship("ProjectBaseline", foreign_keys=[resulting_baseline_id])


class ProjectDodAcceptance(Base):
    """Criterios de aceptacion (Definition of Done / Validate Scope) de PMI Vol 6 sec 4.

    Registra la verificacion de los 4 criterios canonicos de un paquete de trabajo
    y clasificacion opcional del Costo de Calidad (CoQ).
    """

    __tablename__ = "project_dod_acceptances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("project_tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    specification_met = Column(Boolean, default=False, nullable=False)
    tests_no_critical_failures = Column(Boolean, default=False, nullable=False)
    evidence_archived = Column(Boolean, default=False, nullable=False)
    supervisor_sign_off = Column(Boolean, default=False, nullable=False)
    status = Column(String(20), default="pending", nullable=False, index=True)  # pending | accepted
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    coq_classification = Column(
        String(30), nullable=True
    )  # prevention | appraisal | internal_failure | external_failure
    coq_amount = Column(Float, nullable=True)  # Monto $ del Costo de Calidad (CoQ)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="RESTRICT"), nullable=True, index=True)

    project = relationship("Project", backref="dod_acceptances")
    task = relationship("ProjectTask", backref="dod_acceptance", uselist=False)
    acceptor = relationship("Persona", foreign_keys=[accepted_by])
