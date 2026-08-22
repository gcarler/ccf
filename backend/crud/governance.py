"""Governance CRUD: Policies, Resolutions, Committees, Signatures, and Automation Rules."""

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend import models
from backend.models_governance import (
    CommitteeMember,
    GovernanceCommittee,
    GovernancePolicy,
    GovernanceResolution,
    GovernanceSignature,
)
from backend.models_shared import _utcnow
from backend.schemas.governance import (
    AutomationRuleCreate,
    AutomationRuleUpdate,
    CommitteeCreate,
    CommitteeMemberCreate,
    CommitteeUpdate,
    GovernanceStats,
    PolicyCreate,
    PolicyUpdate,
    ResolutionCreate,
    ResolutionUpdate,
    SignatureCreate,
    SignatureSign,
)


# ══════════════════════════════════════════════════════════════════════════════
# AUTOMATION RULES (LEGACY UTILITIES)
# ══════════════════════════════════════════════════════════════════════════════

def get_automation_rules(db: Session, only_active: bool = False, sede_id: Optional[UUID] = None):
    query = db.query(models.AutomationRule)
    if sede_id:
        query = query.filter((models.AutomationRule.sede_id == sede_id) | (models.AutomationRule.sede_id.is_(None)))
    if only_active:
        query = query.filter(models.AutomationRule.is_active)
    return query.order_by(models.AutomationRule.name).all()


def get_automation_rule(db: Session, rule_id: UUID) -> Optional[models.AutomationRule]:
    return db.query(models.AutomationRule).filter(models.AutomationRule.id == rule_id).first()


def create_automation_rule(db: Session, payload: AutomationRuleCreate, sede_id: Optional[UUID] = None) -> models.AutomationRule:
    data = payload.model_dump()
    if sede_id:
        data["sede_id"] = sede_id
    row = models.AutomationRule(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_automation_rule(
    db: Session, rule_id: UUID, payload: AutomationRuleUpdate
) -> Optional[models.AutomationRule]:
    row = db.query(models.AutomationRule).filter(models.AutomationRule.id == rule_id).first()
    if not row:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def delete_automation_rule(db: Session, rule_id: UUID) -> bool:
    row = db.query(models.AutomationRule).filter(models.AutomationRule.id == rule_id).first()
    if not row:
        return False
    row.is_active = False
    db.commit()
    return True


def record_automation_run(db: Session, rule_id: UUID):
    row = db.query(models.AutomationRule).filter(models.AutomationRule.id == rule_id).first()
    if not row:
        return None
    row.last_run = _utcnow()
    db.commit()
    db.refresh(row)
    return row


# ══════════════════════════════════════════════════════════════════════════════
# POLICIES (POLÍTICAS ECLESIALES)
# ══════════════════════════════════════════════════════════════════════════════

def list_policies(
    db: Session,
    sede_id: Optional[UUID] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[GovernancePolicy], int]:
    q = db.query(GovernancePolicy).filter(GovernancePolicy.deleted_at.is_(None))
    if sede_id:
        q = q.filter((GovernancePolicy.sede_id == sede_id) | (GovernancePolicy.sede_id.is_(None)))
    if category:
        q = q.filter(GovernancePolicy.category == category)
    if status:
        q = q.filter(GovernancePolicy.status == status)

    total = q.count()
    items = q.order_by(GovernancePolicy.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def get_policy(db: Session, policy_id: UUID) -> Optional[GovernancePolicy]:
    return (
        db.query(GovernancePolicy)
        .filter(GovernancePolicy.id == policy_id, GovernancePolicy.deleted_at.is_(None))
        .first()
    )


def create_policy(
    db: Session, payload: PolicyCreate, creator_persona_id: Optional[UUID] = None, sede_id: Optional[UUID] = None
) -> GovernancePolicy:
    data = payload.model_dump()
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id
    if creator_persona_id:
        data["created_by_id"] = creator_persona_id

    policy = GovernancePolicy(**data)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(db: Session, policy_id: UUID, payload: PolicyUpdate, approver_persona_id: Optional[UUID] = None) -> Optional[GovernancePolicy]:
    policy = get_policy(db, policy_id)
    if not policy:
        return None

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "APROBADA" and approver_persona_id:
        policy.approved_by_id = approver_persona_id

    for k, v in data.items():
        setattr(policy, k, v)

    policy.updated_at = _utcnow()
    db.commit()
    db.refresh(policy)
    return policy


def delete_policy(db: Session, policy_id: UUID) -> bool:
    policy = get_policy(db, policy_id)
    if not policy:
        return False
    policy.deleted_at = _utcnow()
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# RESOLUTIONS (RESOLUCIONES Y ACTAS)
# ══════════════════════════════════════════════════════════════════════════════

def list_resolutions(
    db: Session,
    sede_id: Optional[UUID] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[GovernanceResolution], int]:
    q = (
        db.query(GovernanceResolution)
        .options(joinedload(GovernanceResolution.signatures).joinedload(GovernanceSignature.persona))
        .filter(GovernanceResolution.deleted_at.is_(None))
    )
    if sede_id:
        q = q.filter((GovernanceResolution.sede_id == sede_id) | (GovernanceResolution.sede_id.is_(None)))
    if status:
        q = q.filter(GovernanceResolution.status == status)

    total = q.count()
    items = q.order_by(GovernanceResolution.session_date.desc()).offset(skip).limit(limit).all()
    return items, total


def get_resolution(db: Session, resolution_id: UUID) -> Optional[GovernanceResolution]:
    return (
        db.query(GovernanceResolution)
        .options(joinedload(GovernanceResolution.signatures).joinedload(GovernanceSignature.persona))
        .filter(GovernanceResolution.id == resolution_id, GovernanceResolution.deleted_at.is_(None))
        .first()
    )


def create_resolution(
    db: Session, payload: ResolutionCreate, creator_persona_id: Optional[UUID] = None, sede_id: Optional[UUID] = None
) -> GovernanceResolution:
    data = payload.model_dump()
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id
    if creator_persona_id:
        data["created_by_id"] = creator_persona_id

    resolution = GovernanceResolution(**data)
    db.add(resolution)
    db.commit()
    db.refresh(resolution)
    return resolution


def update_resolution(db: Session, resolution_id: UUID, payload: ResolutionUpdate) -> Optional[GovernanceResolution]:
    res = get_resolution(db, resolution_id)
    if not res:
        return None

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(res, k, v)

    res.updated_at = _utcnow()
    db.commit()
    db.refresh(res)
    return res


def delete_resolution(db: Session, resolution_id: UUID) -> bool:
    res = get_resolution(db, resolution_id)
    if not res:
        return False
    res.deleted_at = _utcnow()
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# SIGNATURES (FIRMAS DIGITALES)
# ══════════════════════════════════════════════════════════════════════════════

def add_resolution_signature(db: Session, resolution_id: UUID, payload: SignatureCreate) -> GovernanceSignature:
    sig = GovernanceSignature(
        resolution_id=resolution_id,
        persona_id=payload.persona_id,
        observations=payload.observations,
        status="PENDIENTE",
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


def sign_resolution(
    db: Session, signature_id: UUID, persona_id: UUID, payload: SignatureSign
) -> Optional[GovernanceSignature]:
    sig = db.query(GovernanceSignature).filter(
        GovernanceSignature.id == signature_id,
        GovernanceSignature.persona_id == persona_id,
    ).first()
    if not sig:
        return None

    sig.signature_hash = payload.signature_hash
    sig.observations = payload.observations or sig.observations
    sig.status = "FIRMADO"
    sig.signed_at = _utcnow()

    db.commit()
    db.refresh(sig)

    # If all signatures are completed, mark resolution as FIRMADA
    res = db.query(GovernanceResolution).filter(GovernanceResolution.id == sig.resolution_id).first()
    if res:
        pending_count = (
            db.query(GovernanceSignature)
            .filter(GovernanceSignature.resolution_id == res.id, GovernanceSignature.status != "FIRMADO")
            .count()
        )
        if pending_count == 0:
            res.status = "FIRMADA"
            db.commit()

    return sig


# ══════════════════════════════════════════════════════════════════════════════
# COMMITTEES (COMITÉS PASTORALES)
# ══════════════════════════════════════════════════════════════════════════════

def list_committees(
    db: Session,
    sede_id: Optional[UUID] = None,
    committee_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[GovernanceCommittee], int]:
    q = (
        db.query(GovernanceCommittee)
        .options(joinedload(GovernanceCommittee.members).joinedload(CommitteeMember.persona))
        .filter(GovernanceCommittee.deleted_at.is_(None))
    )
    if sede_id:
        q = q.filter((GovernanceCommittee.sede_id == sede_id) | (GovernanceCommittee.sede_id.is_(None)))
    if committee_type:
        q = q.filter(GovernanceCommittee.committee_type == committee_type)

    total = q.count()
    items = q.order_by(GovernanceCommittee.name.asc()).offset(skip).limit(limit).all()
    return items, total


def get_committee(db: Session, committee_id: UUID) -> Optional[GovernanceCommittee]:
    return (
        db.query(GovernanceCommittee)
        .options(joinedload(GovernanceCommittee.members).joinedload(CommitteeMember.persona))
        .filter(GovernanceCommittee.id == committee_id, GovernanceCommittee.deleted_at.is_(None))
        .first()
    )


def create_committee(
    db: Session, payload: CommitteeCreate, sede_id: Optional[UUID] = None
) -> GovernanceCommittee:
    data = payload.model_dump()
    if sede_id and not data.get("sede_id"):
        data["sede_id"] = sede_id

    committee = GovernanceCommittee(**data)
    db.add(committee)
    db.commit()
    db.refresh(committee)
    return committee


def update_committee(db: Session, committee_id: UUID, payload: CommitteeUpdate) -> Optional[GovernanceCommittee]:
    comm = get_committee(db, committee_id)
    if not comm:
        return None

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(comm, k, v)

    comm.updated_at = _utcnow()
    db.commit()
    db.refresh(comm)
    return comm


def delete_committee(db: Session, committee_id: UUID) -> bool:
    comm = get_committee(db, committee_id)
    if not comm:
        return False
    comm.deleted_at = _utcnow()
    db.commit()
    return True


def add_committee_member(
    db: Session, committee_id: UUID, payload: CommitteeMemberCreate
) -> CommitteeMember:
    member = CommitteeMember(
        committee_id=committee_id,
        persona_id=payload.persona_id,
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_committee_member(db: Session, committee_id: UUID, member_id: UUID) -> bool:
    member = (
        db.query(CommitteeMember)
        .filter(CommitteeMember.id == member_id, CommitteeMember.committee_id == committee_id)
        .first()
    )
    if not member:
        return False
    member.deleted_at = _utcnow()
    member.is_active = False
    db.commit()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# STATS & DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

def get_governance_stats(db: Session, sede_id: Optional[UUID] = None) -> GovernanceStats:
    pq = db.query(GovernancePolicy).filter(GovernancePolicy.deleted_at.is_(None))
    rq = db.query(GovernanceResolution).filter(GovernanceResolution.deleted_at.is_(None))
    cq = db.query(GovernanceCommittee).filter(GovernanceCommittee.deleted_at.is_(None))
    mq = db.query(CommitteeMember).filter(CommitteeMember.deleted_at.is_(None), CommitteeMember.is_active.is_(True))

    if sede_id:
        pq = pq.filter((GovernancePolicy.sede_id == sede_id) | (GovernancePolicy.sede_id.is_(None)))
        rq = rq.filter((GovernanceResolution.sede_id == sede_id) | (GovernanceResolution.sede_id.is_(None)))
        cq = cq.filter((GovernanceCommittee.sede_id == sede_id) | (GovernanceCommittee.sede_id.is_(None)))

    return GovernanceStats(
        total_policies=pq.count(),
        published_policies=pq.filter(GovernancePolicy.status == "PUBLICADA").count(),
        total_resolutions=rq.count(),
        signed_resolutions=rq.filter(GovernanceResolution.status == "FIRMADA").count(),
        total_committees=cq.count(),
        active_committee_members=mq.count(),
    )
