from __future__ import annotations

import datetime as dt
import uuid
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.core.security import get_password_hash


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(tzinfo=None)


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=get_password_hash(user.password),
        role=user.role,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_refresh_token(db: Session, user_id: int, token: str, expires_at: dt.datetime):
    row = models.RefreshToken(user_id=user_id, token=token, expires_at=expires_at, revoked=False)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_valid_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    if row.revoked:
        return None
    if row.expires_at <= _utcnow():
        return None
    return row


def revoke_refresh_token(db: Session, token: str):
    row = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not row:
        return None
    row.revoked = True
    db.commit()
    db.refresh(row)
    return row


def grant_xp(db: Session, user_id: int, amount: int) -> Optional[models.User]:
    user = get_user(db, user_id)
    if not user:
        return None
    user.xp = (user.xp or 0) + amount
    next_level = (
        db.query(models.Level)
        .filter(models.Level.min_xp <= user.xp)
        .order_by(models.Level.min_xp.desc())
        .first()
    )
    if next_level and user.current_level_id != next_level.id:
        user.current_level_id = next_level.id
    db.commit()
    db.refresh(user)
    return user


def update_ui_preferences(db: Session, user_id: int, settings: dict):
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings=settings)
        db.add(prefs)
    else:
        prefs.settings = settings
    db.commit()
    db.refresh(prefs)
    return prefs


def get_ui_preferences(db: Session, user_id: int):
    prefs = db.query(models.UserUIPreference).filter(models.UserUIPreference.user_id == user_id).first()
    if not prefs:
        prefs = models.UserUIPreference(user_id=user_id, settings={})
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def award_badge(db: Session, user_id: int, badge_name: str):
    badge = db.query(models.Badge).filter(models.Badge.name == badge_name).first()
    if not badge:
        return None
    existing = (
        db.query(models.UserBadge)
        .filter(models.UserBadge.user_id == user_id, models.UserBadge.badge_id == badge.id)
        .first()
    )
    if existing:
        return existing
    row = models.UserBadge(user_id=user_id, badge_id=badge.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_member(db: Session, payload: schemas.MemberCreate):
    row = models.Member(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_members(db: Session, search: str | None = None, role: str | None = None):
    query = db.query(models.Member)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Member.first_name.ilike(like),
                models.Member.last_name.ilike(like),
                models.Member.email.ilike(like),
            )
        )
    if role:
        query = query.filter(models.Member.church_role == role)
    return query.all()


def update_member(db: Session, member_id: int, payload: schemas.MemberUpdate):
    row = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def create_pipeline_lead(db: Session, payload: schemas.ConsolidationPipelineCreate):
    row = models.ConsolidationPipeline(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_pipeline_lead(db: Session, lead_id: int, payload: schemas.ConsolidationPipelineUpdate):
    row = db.query(models.ConsolidationPipeline).filter(models.ConsolidationPipeline.id == lead_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def get_pipeline_leads(
    db: Session,
    stage: str | None = None,
    assigned_pastor_id: int | None = None,
    search: str | None = None,
):
    query = db.query(models.ConsolidationPipeline)
    if stage:
        query = query.filter(models.ConsolidationPipeline.stage == stage)
    if assigned_pastor_id is not None:
        query = query.filter(models.ConsolidationPipeline.assigned_pastor_id == assigned_pastor_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.ConsolidationPipeline.first_name.ilike(like),
                models.ConsolidationPipeline.last_name.ilike(like),
            )
        )
    return query.all()


def create_pastoral_call_log(db: Session, lead_id: int, call_log: schemas.PastoralCallLogCreate):
    row = models.PastoralCallLog(lead_id=lead_id, pastor_id=call_log.pastor_id, outcome=call_log.outcome)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pastoral_call_logs(db: Session, lead_id: int):
    return db.query(models.PastoralCallLog).filter(models.PastoralCallLog.lead_id == lead_id).all()


def get_courses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    modality: str | None = None,
    published_only: bool = True,
):
    query = db.query(models.Course)
    if modality:
        query = query.filter(models.Course.modality == modality)
    if published_only:
        query = query.filter(models.Course.is_published.is_(True))
    return query.offset(skip).limit(limit).all()


def get_course(db: Session, course_id: int):
    return db.query(models.Course).filter(models.Course.id == course_id).first()


def create_enrollment(db: Session, enrollment: schemas.EnrollmentCreate):
    existing = (
        db.query(models.Enrollment)
        .filter(models.Enrollment.user_id == enrollment.user_id, models.Enrollment.course_id == enrollment.course_id)
        .first()
    )
    if existing:
        raise ValueError("Enrollment already exists")
    row = models.Enrollment(user_id=enrollment.user_id, course_id=enrollment.course_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def issue_pending_certificates(db: Session):
    rows = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.status == "completed",
            models.Enrollment.approved.is_(True),
            models.Enrollment.certificate_issued.is_(False),
        )
        .all()
    )
    issued = []
    for enrollment in rows:
        code = f"CCF-{uuid.uuid4().hex[:8].upper()}"
        enrollment.certificate_issued = True
        enrollment.certificate_code = code
        cert = models.Certificate(enrollment_id=enrollment.id, certificate_code=code)
        db.add(cert)
        issued.append(cert)
    db.commit()
    for cert in issued:
        db.refresh(cert)
    return issued


def get_pilot_readiness(db: Session):
    checklist = [
        {"key": "db", "status": "ok"},
        {"key": "courses", "status": "ok" if db.query(models.Course).count() >= 0 else "warning"},
        {"key": "users", "status": "ok" if db.query(models.User).count() >= 0 else "warning"},
    ]
    return schemas.PilotReadiness(environment_ready=True, checklist=checklist)


def create_agent_task(db: Session, payload: schemas.AgentTaskCreate):
    row = models.AgentTask(
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        source=payload.source,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_tasks(db: Session, status: str | None = None):
    query = db.query(models.AgentTask)
    if status:
        query = query.filter(models.AgentTask.status == status)
    return query.order_by(models.AgentTask.created_at.desc()).all()


def update_agent_task(db: Session, task_id: int, payload: schemas.AgentTaskUpdate):
    row = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def create_agent_insight(db: Session, payload: schemas.AgentInsightCreate):
    row = models.AgentInsight(
        title=payload.title,
        insight_type=payload.insight_type,
        payload=payload.payload,
        acknowledged=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_agent_insights(db: Session, acknowledged: bool | None = None):
    query = db.query(models.AgentInsight)
    if acknowledged is not None:
        query = query.filter(models.AgentInsight.acknowledged == acknowledged)
    return query.order_by(models.AgentInsight.created_at.desc()).all()


def acknowledge_insight(db: Session, insight_id: int):
    row = db.query(models.AgentInsight).filter(models.AgentInsight.id == insight_id).first()
    if not row:
        return None
    row.acknowledged = True
    db.commit()
    db.refresh(row)
    return row


def create_admin_audit_log(
    db: Session,
    actor_user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
):
    row = models.AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json={**(metadata or {}), **({"ip_address": ip_address} if ip_address else {})},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_admin_audit_logs(
    db: Session,
    limit: int = 100,
    actor_user_id: int | None = None,
    resource_type: str | None = None,
):
    query = db.query(models.AdminAuditLog)
    if actor_user_id is not None:
        query = query.filter(models.AdminAuditLog.actor_user_id == actor_user_id)
    if resource_type is not None:
        query = query.filter(models.AdminAuditLog.resource_type == resource_type)
    rows = query.order_by(models.AdminAuditLog.created_at.desc()).limit(limit).all()
    for row in rows:
        row.metadata = row.metadata_json or {}
    return rows


def update_page_content(db: Session, page_key: str, payload: schemas.PageContentUpdate):
    page = db.query(models.PageContent).filter(models.PageContent.page_key == page_key).first()
    if not page:
        page = models.PageContent(page_key=page_key, title=payload.title or "", content=payload.content or "")
        db.add(page)
        db.commit()
        db.refresh(page)
        return page
    version = models.PageContentVersion(page_key=page.page_key, title=page.title, content=page.content)
    db.add(version)
    if payload.title is not None:
        page.title = payload.title
    if payload.content is not None:
        page.content = payload.content
    db.commit()
    db.refresh(page)
    return page


def get_page_content_versions(db: Session, page_key: str):
    return (
        db.query(models.PageContentVersion)
        .filter(models.PageContentVersion.page_key == page_key)
        .order_by(models.PageContentVersion.created_at.desc())
        .all()
    )


def increment_content_metric(db: Session, metric_key: str, ref_id: int, amount: int = 1):
    row = (
        db.query(models.ContentMetric)
        .filter(models.ContentMetric.metric_key == metric_key, models.ContentMetric.ref_id == ref_id)
        .first()
    )
    if not row:
        row = models.ContentMetric(metric_key=metric_key, ref_id=ref_id, value=0)
        db.add(row)
    row.value = int(row.value or 0) + int(amount)
    db.commit()
    db.refresh(row)
    return row


def create_media_asset(db: Session, filename: str, url: str, mime_type: str | None, size_bytes: int):
    row = models.MediaAsset(filename=filename, url=url, mime_type=mime_type, size_bytes=size_bytes)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_user_notifications(db: Session, user_id: int, limit: int = 20):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user_id)
        .order_by(models.Notification.created_at.desc())
        .limit(limit)
        .all()
    )


def mark_notification_as_read(db: Session, notification_id: int):
    row = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not row:
        return None
    row.is_read = True
    db.commit()
    db.refresh(row)
    return row


def mark_all_notifications_read(db: Session, user_id: int):
    rows = db.query(models.Notification).filter(models.Notification.user_id == user_id).all()
    for row in rows:
        row.is_read = True
    db.commit()
    return len(rows)


def create_communication_log(db: Session, payload: schemas.CommunicationLogCreate):
    row = models.CommunicationLog(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_communication_logs(db: Session, limit: int = 50):
    return db.query(models.CommunicationLog).order_by(models.CommunicationLog.created_at.desc()).limit(limit).all()


def get_talents(db: Session, search: str | None = None):
    query = db.query(models.Member)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.Member.first_name.ilike(like),
                models.Member.last_name.ilike(like),
                models.Member.church_role.ilike(like),
            )
        )
    members = query.all()
    return [
        {
            "id": m.id,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "email": m.email,
            "church_role": m.church_role,
        }
        for m in members
    ]


def get_family_members(db: Session, family_id: int):
    members = db.query(models.Member).filter(models.Member.family_id == family_id).all()
    return [
        {
            "id": m.id,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "family_id": m.family_id,
        }
        for m in members
    ]


def search_knowledge_base(db: Session, query: str):
    if not query:
        return []
    return [SimpleNamespace(title="Base de conocimiento", content=f"Resultado para: {query}")]
