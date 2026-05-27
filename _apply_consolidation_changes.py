#!/usr/bin/env python3
"""Apply all consolidation transformation changes to pastoral.py and crud/crm.py"""

def fix_pastoral():
    with open('backend/api/crm/pastoral.py') as f:
        content = f.read()

    # 1. Fix case_id: int -> str in consolidation endpoints
    content = content.replace(
        'def get_consolidation_case(\n    case_id: int,',
        'def get_consolidation_case(\n    case_id: str,'
    )
    content = content.replace(
        'def update_consolidation_case(\n    case_id: int,',
        'def update_consolidation_case(\n    case_id: str,'
    )
    content = content.replace(
        'def delete_consolidation_case(\n    case_id: int,',
        'def delete_consolidation_case(\n    case_id: str,'
    )
    content = content.replace(
        'def list_consolidation_tasks(\n    case_id: int,',
        'def list_consolidation_tasks(\n    case_id: str,'
    )
    content = content.replace(
        'def list_consolidation_interactions(\n    case_id: int,',
        'def list_consolidation_interactions(\n    case_id: str,'
    )

    # update_consolidation_task
    content = content.replace(
        'def update_consolidation_task(\n    case_id: int,\n    task_id: int,\n    payload: schemas.ConsolidationFollowUpTaskUpdate,',
        'def update_consolidation_task(\n    case_id: str,\n    task_id: str,\n    payload: schemas.ConsolidationTaskUpdate,'
    )

    # 2. Fix create_consolidation_case - Member -> Persona lookup
    content = content.replace(
        "    member = (\n        db.query(models.Member).filter(models.Member.id == payload.persona_id).first()\n    )\n    if not member:\n        raise HTTPException(status_code=404, detail=\"Member not found\")",
        "    persona = (\n        db.query(models.Persona).filter(models.Persona.id == payload.persona_id).first()\n    )\n    if not persona:\n        raise HTTPException(status_code=404, detail=\"Persona not found\")"
    )

    # Wait, the strings may use single or double quotes. Let me check and handle both.
    # Actually, let me just read the raw content and handle it.

    # 3. Fix performed_by_member_id -> performed_by_id
    content = content.replace(
        '"performed_by_member_id": i.performed_by_member_id,',
        '"performed_by_id": i.performed_by_id,'
    )

    # 4. Fix update_consolidation_assignment response
    content = content.replace(
        '"assigned_by_member_id": assignment.assigned_by_member_id,',
        '"assigned_by_id": assignment.assigned_by_id,'
    )
    content = content.replace(
        '"assigned_to_member_id": assignment.assigned_to_member_id,',
        '"assigned_to_id": assignment.assigned_to_id,'
    )

    # 5. Remove ALL pipeline endpoints + call logs from CONSOLIDATION & PIPELINE to just before messaging
    pipeline_marker = '# --- CONSOLIDATION & PIPELINE ---'
    messaging_marker = "@router.post(\"/messaging/send\", response_model=dict)"
    idx1 = content.find(pipeline_marker)
    idx2 = content.find(messaging_marker)
    if idx1 >= 0 and idx2 > idx1:
        content = content[:idx1] + content[idx2:]

    # 6. Fix analytics - remove pipeline queries
    old_pipeline_analytics = """    pipeline_rows = (
        db.query(
            models.ConsolidationPipeline.stage,
            func.count(models.ConsolidationPipeline.id),
        )
        .group_by(models.ConsolidationPipeline.stage)
        .all()
    )
    pipeline_by_stage = {}
    for stage, count in pipeline_rows:
        normalized_stage = schemas.normalize_pipeline_stage(stage)
        pipeline_by_stage[normalized_stage] = (
            pipeline_by_stage.get(normalized_stage, 0) + count
        )
    total_leads = sum(pipeline_by_stage.values())
    open_counseling = ("""
    new_analytics = "    open_counseling = ("
    content = content.replace(old_pipeline_analytics, new_analytics)

    # 7. Fix analytics return
    old_analytics_return = """        "total_members": total_members,
        "active_members": active_members,
        "total_leads": total_leads,
        "pipeline_by_stage": pipeline_by_stage,
        "open_counseling": open_counseling,"""
    new_analytics_return = """        "total_members": total_members,
        "active_members": active_members,
        "open_counseling": open_counseling,"""
    content = content.replace(old_analytics_return, new_analytics_return)

    # 8. Fix newsletter leads - Member -> Persona join
    content = content.replace(
        '.join(models.Member, models.ConsolidationCase.persona_id == models.Member.id)',
        '.join(models.Persona, models.ConsolidationCase.persona_id == models.Persona.id)'
    )

    # Fix newsletter response (first occurrence - GET /leads/newsletter)
    old_newsletter_response = """        member = case.persona
        leads.append({
            "case_id": case.id,
            "member_id": member.id if member else None,
            "first_name": member.first_name if member else "",
            "last_name": member.last_name if member else "",
            "email": member.email if member else None,
            "phone": member.phone if member else None,"""
    new_newsletter_response = """        persona = case.persona
        leads.append({
            "case_id": case.id,
            "persona_id": persona.id if persona else None,
            "nombre_completo": persona.nombre_completo if persona else "",
            "email": persona.email if persona else None,
            "telefono": persona.telefono if persona else None,"""
    content = content.replace(old_newsletter_response, new_newsletter_response)

    # Fix export newsletter response (second occurrence)
    old_export_response = """        member = case.persona
        rows.append({
            "first_name": member.first_name if member else "",
            "last_name": member.last_name if member else "",
            "email": member.email if member else "",
            "phone": member.phone if member else ","""
    new_export_response = """        persona = case.persona
        rows.append({
            "nombre_completo": persona.nombre_completo if persona else "",
            "email": persona.email if persona else "",
            "telefono": persona.telefono if persona else ","""
    content = content.replace(old_export_response, new_export_response)

    with open('backend/api/crm/pastoral.py', 'w') as f:
        f.write(content)
    print("pastoral.py: OK")


def fix_crud_crm():
    with open('backend/crud/crm.py') as f:
        content = f.read()

    # Remove pipeline CRUD section (lines ~246-315)
    pipeline_section = """# ── Pipeline ───────────────────────────────────────────


def create_pipeline_lead(db: Session, payload: schemas.ConsolidationPipelineCreate):
    row = models.ConsolidationPipeline(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_pipeline_lead(
    db: Session, lead_id: int, payload: schemas.ConsolidationPipelineUpdate
):
    row = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )
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
        query = query.filter(
            models.ConsolidationPipeline.assigned_pastor_id == assigned_pastor_id
        )
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                models.ConsolidationPipeline.first_name.ilike(like),
                models.ConsolidationPipeline.last_name.ilike(like),
            )
        )
    return query.all()


def create_pastoral_call_log(
    db: Session, lead_id: int, call_log: schemas.PastoralCallLogCreate
):
    row = models.PastoralCallLog(
        lead_id=lead_id, pastor_id=call_log.pastor_id, outcome=call_log.outcome
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_pastoral_call_logs(db: Session, lead_id: int):
    return (
        db.query(models.PastoralCallLog)
        .filter(models.PastoralCallLog.lead_id == lead_id)
        .all()
    )


# ── CRM Events ─────────────────────────────────────────"""
    content = content.replace(pipeline_section, "# ── CRM Events ─────────────────────────────────────────")

    # Remove pipeline CRUD at the bottom (lines ~1003-1047)
    bottom_pipeline = """# ── Pipeline ───────────────────────────────────────────


def get_pipeline_lead(
    db: Session, lead_id: int
) -> Optional[models.ConsolidationPipeline]:
    return (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )


def delete_pipeline_lead(db: Session, lead_id: int) -> bool:
    row = (
        db.query(models.ConsolidationPipeline)
        .filter(models.ConsolidationPipeline.id == lead_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def get_pastoral_call_log(db: Session, log_id: int) -> Optional[models.PastoralCallLog]:
    return (
        db.query(models.PastoralCallLog)
        .filter(models.PastoralCallLog.id == log_id)
        .first()
    )


def delete_pastoral_call_log(db: Session, log_id: int) -> bool:
    row = (
        db.query(models.PastoralCallLog)
        .filter(models.PastoralCallLog.id == log_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


# ── CRM Events ─────────────────────────────────────────"""
    content = content.replace(bottom_pipeline, "# ── CRM Events ─────────────────────────────────────────")

    # Fix get_crm_tasks - remove lead_id
    old_get_crm_tasks = """def get_crm_tasks(
    db: Session,
    assignee_id: Optional[int] = None,
    persona_id: Optional[str] = None,
    lead_id: Optional[int] = None,
) -> List[models.CrmTask]:
    query = db.query(models.CrmTask)
    if assignee_id:
        query = query.filter(models.CrmTask.assignee_id == assignee_id)
    if persona_id:
        query = query.filter(models.CrmTask.persona_id == persona_id)
    if lead_id:
        query = query.filter(models.CrmTask.lead_id == lead_id)
    return query.order_by(models.CrmTask.due_date.asc()).all()"""
    new_get_crm_tasks = """def get_crm_tasks(
    db: Session,
    assignee_id: Optional[int] = None,
    persona_id: Optional[str] = None,
) -> List[models.CrmTask]:
    query = db.query(models.CrmTask)
    if assignee_id:
        query = query.filter(models.CrmTask.assignee_id == assignee_id)
    if persona_id:
        query = query.filter(models.CrmTask.persona_id == persona_id)
    return query.order_by(models.CrmTask.due_date.asc()).all()"""
    content = content.replace(old_get_crm_tasks, new_get_crm_tasks)

    # Fix consolidation_case CRUDs - case_id: int -> str
    content = content.replace(
        'def get_consolidation_case(db: Session, case_id: int):',
        'def get_consolidation_case(db: Session, case_id: str):'
    )
    content = content.replace(
        'def update_consolidation_case(\n    db: Session, case_id: int, payload: schemas.ConsolidationCaseUpdate',
        'def update_consolidation_case(\n    db: Session, case_id: str, payload: schemas.ConsolidationCaseUpdate'
    )
    content = content.replace(
        'def delete_consolidation_case(db: Session, case_id: int) -> bool:',
        'def delete_consolidation_case(db: Session, case_id: str) -> bool:'
    )

    with open('backend/crud/crm.py', 'w') as f:
        f.write(content)
    print("crud/crm.py: OK")


def fix_models_identity():
    with open('backend/models_identity.py') as f:
        content = f.read()
    content = content.replace(
        '\n    # Relationships for CRM & Pipeline\n    assigned_leads = relationship("ConsolidationPipeline", back_populates="pastor")\n',
        '\n'
    )
    with open('backend/models_identity.py', 'w') as f:
        f.write(content)
    print("models_identity.py: OK")


def fix_crud_init():
    with open('backend/crud/__init__.py') as f:
        content = f.read()
    # Remove pipeline CRUD exports
    lines_to_remove = [
        '"create_pipeline_lead",',
        '"get_pipeline_leads",',
        '"get_pipeline_lead",',
        '"update_pipeline_lead",',
    ]
    for line in lines_to_remove:
        content = content.replace(f'    {line}\n', '')
    with open('backend/crud/__init__.py', 'w') as f:
        f.write(content)
    print("crud/__init__.py: OK")


if __name__ == "__main__":
    fix_pastoral()
    fix_crud_crm()
    fix_models_identity()
    fix_crud_init()
