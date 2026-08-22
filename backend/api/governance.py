from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.audit import record_admin_action
from backend.core.database import get_db
from backend.core.permissions import require_active_user, require_admin
from backend.crud import governance as gov_crud
from backend.schemas import governance as gov_schemas

router = APIRouter(prefix="/governance", tags=["governance"])


# ══════════════════════════════════════════════════════════════════════════════
# STATS & DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/stats", response_model=gov_schemas.GovernanceStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = getattr(current_user, "sede_id", None)
    return gov_crud.get_governance_stats(db, sede_id=sede_id)


# ══════════════════════════════════════════════════════════════════════════════
# POLICIES (POLÍTICAS Y NORMATIVAS)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/policies", response_model=List[gov_schemas.PolicyRead])
def list_policies(
    category: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = getattr(current_user, "sede_id", None)
    items, _total = gov_crud.list_policies(
        db, sede_id=sede_id, category=category, status=status, skip=skip, limit=limit
    )
    return items


@router.post("/policies", response_model=gov_schemas.PolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: gov_schemas.PolicyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)
    sede_id = getattr(current_user, "sede_id", None)
    policy = gov_crud.create_policy(
        db, payload, creator_persona_id=persona_id, sede_id=sede_id
    )
    record_admin_action(db, current_user, "governance.policy.create", "policy", str(policy.id))
    return policy


@router.get("/policies/{policy_id}", response_model=gov_schemas.PolicyRead)
def get_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_active_user),
):
    policy = gov_crud.get_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    return policy


@router.patch("/policies/{policy_id}", response_model=gov_schemas.PolicyRead)
def update_policy(
    policy_id: UUID,
    payload: gov_schemas.PolicyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)
    policy = gov_crud.update_policy(db, policy_id, payload, approver_persona_id=persona_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    record_admin_action(db, current_user, "governance.policy.update", "policy", str(policy.id))
    return policy


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    success = gov_crud.delete_policy(db, policy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Política no encontrada")
    record_admin_action(db, current_user, "governance.policy.delete", "policy", str(policy_id))


# ══════════════════════════════════════════════════════════════════════════════
# RESOLUTIONS (RESOLUCIONES Y ACTAS)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/resolutions", response_model=List[gov_schemas.ResolutionRead])
def list_resolutions(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = getattr(current_user, "sede_id", None)
    items, _total = gov_crud.list_resolutions(db, sede_id=sede_id, status=status, skip=skip, limit=limit)
    return items


@router.post("/resolutions", response_model=gov_schemas.ResolutionRead, status_code=status.HTTP_201_CREATED)
def create_resolution(
    payload: gov_schemas.ResolutionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)
    sede_id = getattr(current_user, "sede_id", None)
    res = gov_crud.create_resolution(db, payload, creator_persona_id=persona_id, sede_id=sede_id)
    record_admin_action(db, current_user, "governance.resolution.create", "resolution", str(res.id))
    return res


@router.get("/resolutions/{resolution_id}", response_model=gov_schemas.ResolutionRead)
def get_resolution(
    resolution_id: UUID,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_active_user),
):
    res = gov_crud.get_resolution(db, resolution_id)
    if not res:
        raise HTTPException(status_code=404, detail="Resolución no encontrada")
    return res


@router.patch("/resolutions/{resolution_id}", response_model=gov_schemas.ResolutionRead)
def update_resolution(
    resolution_id: UUID,
    payload: gov_schemas.ResolutionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    res = gov_crud.update_resolution(db, resolution_id, payload)
    if not res:
        raise HTTPException(status_code=404, detail="Resolución no encontrada")
    record_admin_action(db, current_user, "governance.resolution.update", "resolution", str(res.id))
    return res


@router.delete("/resolutions/{resolution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resolution(
    resolution_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    success = gov_crud.delete_resolution(db, resolution_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resolución no encontrada")
    record_admin_action(db, current_user, "governance.resolution.delete", "resolution", str(resolution_id))


@router.post("/resolutions/{resolution_id}/signatures", response_model=gov_schemas.SignatureRead)
def request_signature(
    resolution_id: UUID,
    payload: gov_schemas.SignatureCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sig = gov_crud.add_resolution_signature(db, resolution_id, payload)
    record_admin_action(db, current_user, "governance.signature.request", "signature", str(sig.id))
    return sig


@router.post("/signatures/{signature_id}/sign", response_model=gov_schemas.SignatureRead)
def sign_resolution_action(
    signature_id: UUID,
    payload: gov_schemas.SignatureSign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)
    sig = gov_crud.sign_resolution(db, signature_id, persona_id, payload)
    if not sig:
        raise HTTPException(status_code=404, detail="Solicitud de firma no encontrada o no autorizada")
    record_admin_action(db, current_user, "governance.signature.signed", "signature", str(sig.id))
    return sig


# ══════════════════════════════════════════════════════════════════════════════
# COMMITTEES (COMITÉS PASTORALES)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/committees", response_model=List[gov_schemas.CommitteeRead])
def list_committees(
    committee_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_active_user),
):
    sede_id = getattr(current_user, "sede_id", None)
    items, _total = gov_crud.list_committees(db, sede_id=sede_id, committee_type=committee_type, skip=skip, limit=limit)
    return items


@router.post("/committees", response_model=gov_schemas.CommitteeRead, status_code=status.HTTP_201_CREATED)
def create_committee(
    payload: gov_schemas.CommitteeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = getattr(current_user, "sede_id", None)
    comm = gov_crud.create_committee(db, payload, sede_id=sede_id)
    record_admin_action(db, current_user, "governance.committee.create", "committee", str(comm.id))
    return comm


@router.get("/committees/{committee_id}", response_model=gov_schemas.CommitteeRead)
def get_committee(
    committee_id: UUID,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_active_user),
):
    comm = gov_crud.get_committee(db, committee_id)
    if not comm:
        raise HTTPException(status_code=404, detail="Comité no encontrado")
    return comm


@router.patch("/committees/{committee_id}", response_model=gov_schemas.CommitteeRead)
def update_committee(
    committee_id: UUID,
    payload: gov_schemas.CommitteeUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    comm = gov_crud.update_committee(db, committee_id, payload)
    if not comm:
        raise HTTPException(status_code=404, detail="Comité no encontrado")
    record_admin_action(db, current_user, "governance.committee.update", "committee", str(comm.id))
    return comm


@router.delete("/committees/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_committee(
    committee_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    success = gov_crud.delete_committee(db, committee_id)
    if not success:
        raise HTTPException(status_code=404, detail="Comité no encontrado")
    record_admin_action(db, current_user, "governance.committee.delete", "committee", str(committee_id))


@router.post("/committees/{committee_id}/members", response_model=gov_schemas.CommitteeMemberRead)
def add_committee_member(
    committee_id: UUID,
    payload: gov_schemas.CommitteeMemberCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    member = gov_crud.add_committee_member(db, committee_id, payload)
    record_admin_action(db, current_user, "governance.committee.member_add", "committee_member", str(member.id))
    return member


@router.delete("/committees/{committee_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_committee_member(
    committee_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    success = gov_crud.remove_committee_member(db, committee_id, member_id)
    if not success:
        raise HTTPException(status_code=404, detail="Miembro de comité no encontrado")
    record_admin_action(db, current_user, "governance.committee.member_remove", "committee_member", str(member_id))


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS & AUTOMATION RULES (PRESERVED)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/audit-logs", response_model=List[schemas.AdminAuditLog])
def list_audit_logs(
    limit: int = 100,
    actor_persona_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    return crud.get_admin_audit_logs(
        db,
        limit=limit,
        actor_persona_id=actor_persona_id,
        resource_type=resource_type,
    )


@router.get("/automations", response_model=List[gov_schemas.AutomationRuleRead])
def list_automations(
    only_active: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = getattr(current_user, "sede_id", None)
    return gov_crud.get_automation_rules(db, only_active=only_active, sede_id=sede_id)


@router.post("/automations", response_model=gov_schemas.AutomationRuleRead, status_code=status.HTTP_201_CREATED)
def create_automation(
    payload: gov_schemas.AutomationRuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    sede_id = getattr(current_user, "sede_id", None)
    rule = gov_crud.create_automation_rule(db, payload, sede_id=sede_id)
    record_admin_action(db, current_user, "governance.automation.create", "automation_rule", str(rule.id))
    return rule


@router.patch("/automations/{rule_id}", response_model=gov_schemas.AutomationRuleRead)
def update_automation(
    rule_id: UUID,
    payload: gov_schemas.AutomationRuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    rule = gov_crud.update_automation_rule(db, rule_id, payload)
    if not rule:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    record_admin_action(db, current_user, "governance.automation.update", "automation_rule", str(rule.id))
    return rule


@router.delete("/automations/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_automation(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    success = gov_crud.delete_automation_rule(db, rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    record_admin_action(db, current_user, "governance.automation.delete", "automation_rule", str(rule_id))
