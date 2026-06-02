from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.models_shared import _utcnow
from backend import crud, models, schemas
from backend.agents.orchestrator import AgentOrchestrator
from backend.auth import require_active_user, require_admin
from backend.core.audit import record_admin_action
from backend.core.database import get_db

router = APIRouter(prefix="/agents", tags=["agents"])
analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


@analytics_router.get("/summary")
def analytics_summary(
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Resumen global para el Dashboard de Administración."""
    total_members = db.query(models.Persona).count()
    total_projects = db.query(models.Project).count()
    total_enrollments = db.query(models.Enrollment).count()
    total_certificates = db.query(models.Certificate).count()
    pending_tasks = (
        db.query(models.AgentTask).filter(models.AgentTask.status == "pending").count()
    )
    unread_insights = (
        db.query(models.AgentInsight)
        .filter(~models.AgentInsight.acknowledged)
        .count()
    )

    pending_testimonials = sum(
        1 for row in crud.list_testimonials(db) if not row.is_approved
    )

    return {
        "total_members": total_members,
        "total_projects": total_projects,
        "total_enrollments": total_enrollments,
        "total_certificates": total_certificates,
        "pending_agent_tasks": pending_tasks,
        "unread_insights": unread_insights,
        "pending_testimonials": pending_testimonials,
    }


@router.post("/tasks", response_model=schemas.AgentTask)
def create_task(
    task: schemas.AgentTaskCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_agent_task(db, task)
    record_admin_action(
        db,
        current_user,
        action="create_agent_task",
        resource_type="agent_task",
        resource_id=str(created.id),
        metadata={"title": created.title, "priority": created.priority},
    )
    return created


@router.get("/tasks", response_model=List[schemas.AgentTask])
def list_tasks(
    status: Optional[str] = None,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return crud.list_agent_tasks(db, status)


@router.patch("/tasks/{task_id}", response_model=schemas.AgentTask)
def update_task(
    task_id: int,
    payload: schemas.AgentTaskUpdate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    updated = crud.update_agent_task(db, task_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    record_admin_action(
        db,
        current_user,
        action="update_agent_task",
        resource_type="agent_task",
        resource_id=str(task_id),
        metadata=payload.model_dump(exclude_unset=True),
    )
    return updated


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina una tarea de agente."""
    task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.deleted_at = _utcnow()
    db.commit()
    return None


@router.post("/insights", response_model=schemas.AgentInsight)
def create_insight(
    insight: schemas.AgentInsightCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    created = crud.create_agent_insight(db, insight)
    record_admin_action(
        db,
        current_user,
        action="create_agent_insight",
        resource_type="agent_insight",
        resource_id=str(created.id),
        metadata={"title": created.title, "type": created.insight_type},
    )
    return created


@router.get("/insights", response_model=List[schemas.AgentInsight])
def list_insights(
    acknowledged: Optional[bool] = None,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    return crud.list_agent_insights(db, acknowledged)


@router.post("/insights/{insight_id}/ack")
def acknowledge_insight(
    insight_id: int,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    insight = crud.acknowledge_insight(db, insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    record_admin_action(
        db,
        current_user,
        action="ack_agent_insight",
        resource_type="agent_insight",
        resource_id=str(insight_id),
    )
    return {"status": "ok"}


@router.delete("/insights/{insight_id}", status_code=204)
def delete_insight(
    insight_id: int,
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Elimina un insight de agente."""
    insight = (
        db.query(models.AgentInsight)
        .filter(models.AgentInsight.id == insight_id)
        .first()
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    insight.deleted_at = _utcnow()
    db.commit()
    return None


class AskRequest(BaseModel):
    query: str


@router.post("/ask")
def ask_optimus(
    payload: AskRequest,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """
    Query the Neural MESH engine. It searches the Knowledge Base and
    then uses AgentOrchestrator to generate a high-quality response.
    """
    # 1. Search in KB for context
    kb_results = crud.search_knowledge_base(db, payload.query)
    context = ""
    sources = []

    if kb_results:
        context = "\n".join([f"Source [{r.title}]: {r.content}" for r in kb_results])
        sources = [r.title for r in kb_results]

    # 2. Use Orchestrator for real AI generation if configured
    try:
        orchestrator = AgentOrchestrator()
        # Create a custom prompt combining KB context and query
        full_query = (
            f"Context from Knowledge Base:\n{context}\n\nUser Question: {payload.query}"
        )

        insight = orchestrator.run_diagnosis(
            summary=f"Consulta de usuario: {payload.query}",
            metrics={
                "context_length": len(context),
                "user": current_user.username,
                "full_query": full_query,
            },
        )

        return {"answer": insight.payload, "sources": sources}
    except MemoryError:
        raise
    except Exception:
        # Fallback to basic KB retrieval if AI fails or is not configured
        if kb_results:
            return {
                "answer": f"He encontrado informaci??n relevante en nuestra base de conocimientos: {kb_results[0].content[:500]}...",
                "sources": sources,
            }

        return {
            "answer": "Lo siento, el motor neuronal MESH no est?? disponible en este momento y no encontr?? informaci??n en la base de datos local. ??Te gustar??a que notifique a un administrador?",
            "sources": [],
        }


# ── Agent Identity API (Canonical Person Model) ──
from typing import List as TypingList
from sqlalchemy.orm import Session
from backend.models import User
from sqlalchemy import or_
from backend.models_agents import (Agent as AgentModel, AgentActivity,
                                    AgentJourney, AgentRole)
from backend.schemas.agents import (AgentCreate, AgentProfileResponse,
                                     AgentResponse, AgentRoleCreate,
                                     AgentRoleResponse, AgentSearchResult,
                                     AgentTimelineItem, AgentUpdate,
                                     StageTransition)


def _generate_agent_code(db) -> str:
    count = db.query(AgentModel).count()
    return f"CCF-AGENT-{count + 1:05d}"


@router.get("/search", response_model=TypingList[AgentSearchResult])
def search_agents(
    q: str,
    limit: int = 20,
    db=Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    term = f"%{q}%"
    agents = db.query(AgentModel).filter(
        or_(AgentModel.first_name.ilike(term), AgentModel.last_name.ilike(term),
            AgentModel.email.ilike(term), AgentModel.phone.ilike(term)),
        AgentModel.is_active,
    ).order_by(AgentModel.first_name).limit(limit).all()
    return agents


@router.get("/profile/{agent_id}", response_model=AgentProfileResponse)
def get_agent_profile(
    agent_id: int,
    limit: int = 50,
    db=Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    roles = db.query(AgentRole).filter(AgentRole.agent_id == agent_id, AgentRole.ended_at.is_(None)).all()
    activities = db.query(AgentActivity).filter(AgentActivity.agent_id == agent_id).order_by(AgentActivity.occurred_at.desc()).limit(limit).all()
    total = db.query(AgentActivity).filter(AgentActivity.agent_id == agent_id).count()
    return AgentProfileResponse(
        agent=agent, roles=roles,
        activities=[AgentTimelineItem(activity_type=a.activity_type, source_type=a.source_type, source_id=a.source_id, status=a.status, notes=a.notes, occurred_at=a.occurred_at) for a in activities],
        total_activities=total,
    )


@router.get("/timeline/{agent_id}", response_model=TypingList[AgentTimelineItem])
def get_agent_timeline(agent_id: int, limit: int = 100, db=Depends(get_db), _user: models.User = Depends(require_active_user)):
    activities = db.query(AgentActivity).filter(AgentActivity.agent_id == agent_id).order_by(AgentActivity.occurred_at.desc()).limit(limit).all()
    return [AgentTimelineItem(activity_type=a.activity_type, source_type=a.source_type, source_id=a.source_id, status=a.status, notes=a.notes, occurred_at=a.occurred_at) for a in activities]


@router.get("/roles/{agent_id}", response_model=TypingList[AgentRoleResponse])
def get_agent_roles(agent_id: int, active_only: bool = True, db=Depends(get_db), _user: models.User = Depends(require_active_user)):
    query = db.query(AgentRole).filter(AgentRole.agent_id == agent_id)
    if active_only:
        query = query.filter(AgentRole.ended_at.is_(None))
    return query.order_by(AgentRole.started_at.desc()).all()


@router.post("/roles/{agent_id}", response_model=AgentRoleResponse)
def add_agent_role(agent_id: int, role: AgentRoleCreate, db=Depends(get_db), current_user: models.User = Depends(require_active_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    new_role = AgentRole(agent_id=agent_id, role_type=role.role_type, role_value=role.role_value, context_id=role.context_id, context_type=role.context_type, is_primary=role.is_primary, created_by=current_user.id)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


@router.post("", response_model=AgentResponse)
def create_agent(data: AgentCreate, db=Depends(get_db), current_user: models.User = Depends(require_admin)):
    code = _generate_agent_code(db)
    agent = AgentModel(code=code, first_name=data.first_name, last_name=data.last_name, email=data.email, phone=data.phone, avatar_url=data.avatar_url, spiritual_stage=data.spiritual_stage, created_by=current_user.id)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: int, data: AgentUpdate, db=Depends(get_db), current_user: models.User = Depends(require_active_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    agent.updated_by = current_user.id
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/{agent_id}/stage", response_model=dict)
def transition_stage(agent_id: int, data: StageTransition, db=Depends(get_db), current_user: models.User = Depends(require_active_user)):
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(404, "Agent not found")
    from_stage = agent.spiritual_stage
    agent.spiritual_stage = data.to_stage
    agent.updated_by = current_user.id
    journey = AgentJourney(agent_id=agent_id, from_stage=from_stage, to_stage=data.to_stage, reason=data.reason, triggered_by="manual", triggered_by_id=current_user.id)
    db.add(journey)
    db.commit()
    return {"from": from_stage, "to": data.to_stage, "agent_id": agent_id}


# ── Dual Write Hooks (Phase 2) ──
# These are called from existing registration/member creation endpoints
# to ensure a canonical Agent is created alongside User/Persona records.

from backend.models_agents import AgentAuth as AgentModelAuth


def sync_persona_to_agent(db: Session, persona) -> int:
    """Create an Agent from a Persona if one doesn't exist yet."""
    if persona.user_id:
        existing = db.query(AgentModel).filter(
            or_(
                AgentModel.email == persona.email,
                AgentModel.phone == persona.phone,
            )
        ).first()
    else:
        existing = db.query(AgentModel).filter(
            or_(
                AgentModel.email == persona.email,
                AgentModel.phone == persona.phone,
            )
        ).first()

    if existing:
        return existing.id

    agent = AgentModel(
        code=_generate_agent_code(db),
        first_name=persona.first_name,
        last_name=persona.last_name,
        email=persona.email,
        phone=persona.phone,
        spiritual_stage="visitor" if (persona.church_role or "").lower().startswith("visitante") else "believer",
    )
    db.add(agent)
    db.flush()

    if persona.user_id:
        user = db.query(User).filter(User.id == persona.user_id).first()
        if user:
            auth = AgentModelAuth(
                agent_id=agent.id,
                username=user.username,
                provider="local",
            )
            db.add(auth)

    if persona.church_role:
        db.add(AgentRole(
            agent_id=agent.id,
            role_type="church",
            role_value=persona.church_role,
        ))

    return agent.id


def sync_user_to_agent(db: Session, user) -> int:
    """Create an Agent from a User if one doesn't exist yet."""
    existing = db.query(AgentModel).filter(
        or_(AgentModel.email == user.email)
    ).first()
    
    if existing:
        return existing.id
    
    agent = AgentModel(
        code=_generate_agent_code(db),
        first_name=user.username.split("@")[0] if "@" in user.email else user.username,
        last_name="",
        email=user.email,
        spiritual_stage="visitor",
    )
    db.add(agent)
    db.flush()
    
    db.add(AgentModelAuth(
        agent_id=agent.id,
        username=user.username,
        password_hash=user.password_hash if hasattr(user, 'password_hash') else None,
        provider="local",
    ))
    
    # Platform role
    if user.role:
        db.add(AgentRole(
            agent_id=agent.id,
            role_type="platform",
            role_value=user.role,
        ))

    return agent.id


# ── Knowledge Base Endpoints ──
from backend.services.knowledge_base import (
    KnowledgeIndexer, AgentKnowledgeBase,
)
from sqlalchemy import func


class KBRebuildResponse(BaseModel):
    status: str
    stats: dict


@router.post("/kb/rebuild", response_model=KBRebuildResponse)
def rebuild_knowledge_base(
    db=Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    """Reconstruye la Knowledge Base desde cero."""
    indexer = KnowledgeIndexer(db)
    stats = indexer.rebuild_all()
    return KBRebuildResponse(status="ok", stats=stats)


@router.get("/kb/search")
def search_kb(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
    db=Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    """Busca en la Knowledge Base."""
    from backend.services.knowledge_base import search_knowledge_base_real

    results = search_knowledge_base_real(
        db, q, top_k=limit, category=category,
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content[:500],
            "summary": r.summary,
            "category": r.category,
            "source_module": r.source_module,
            "source_id": r.source_id,
            "relevance": r.relevance_score,
        }
        for r in results
    ]


@router.get("/kb/stats")
def kb_stats(
    db=Depends(get_db),
    _user: models.User = Depends(require_active_user),
):
    """Estadísticas de la Knowledge Base."""
    total = db.query(AgentKnowledgeBase).count()
    active = db.query(AgentKnowledgeBase).filter(
        AgentKnowledgeBase.is_active,
    ).count()
    by_category = {}
    for cat, cnt in db.query(
        AgentKnowledgeBase.category,
        func.count(AgentKnowledgeBase.id),
    ).filter(
        AgentKnowledgeBase.is_active,
    ).group_by(AgentKnowledgeBase.category).all():
        by_category[cat] = cnt
    return {"total": total, "active": active, "by_category": by_category}


# ── Conversation Endpoints ──
from backend.services.conversation_memory import (
    create_conversation, get_user_conversations,
    get_conversation_messages, delete_conversation,
)


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    agent_name: str = "Optimus"


@router.post("/conversations")
def create_conv(
    data: ConversationCreate,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Crea una nueva conversación."""
    conv_id = create_conversation(
        current_user.id, title=data.title, agent_name=data.agent_name,
    )
    return {"id": conv_id, "title": data.title or data.agent_name}


@router.get("/conversations")
def list_convs(
    limit: int = 20,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Lista conversaciones del usuario."""
    return get_user_conversations(current_user.id, limit=limit)


@router.get("/conversations/{conv_id}/messages")
def get_conv_messages(
    conv_id: int,
    limit: int = 50,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Obtiene mensajes de una conversación."""
    return get_conversation_messages(conv_id, limit=limit)


@router.delete("/conversations/{conv_id}")
def delete_conv(
    conv_id: int,
    db=Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    """Elimina una conversación."""
    success = delete_conversation(conv_id, current_user.id)
    if not success:
        raise HTTPException(404, "Conversation not found")
    return {"status": "ok"}


# ── SSE Event Stream ──
from fastapi.responses import StreamingResponse
import asyncio


async def _event_generator(user_id: int):
    """Genera eventos SSE para el usuario."""
    while True:
        await asyncio.sleep(2)
        yield ": heartbeat\n\n"


@router.get("/events/stream")
async def event_stream(
    current_user: models.User = Depends(require_active_user),
):
    """Server-Sent Events para notificaciones en tiempo real."""
    return StreamingResponse(
        _event_generator(current_user.id),
        media_type="text/event-stream",
    )
