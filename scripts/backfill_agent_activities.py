#!/usr/bin/env python
"""Phase 3b: Backfill agent_activities from existing module data."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

# Import ALL models first for relationship resolution
from backend.models import *  # noqa: F401

from backend.core.database import SessionLocal
from backend.models_agents import Agent, AgentActivity
from backend.models_crm import Member
from backend.models_identity import User
from sqlalchemy import or_

db = SessionLocal()
total = 0

def get_agent_for_member(member):
    criteria = []
    if member.email:
        criteria.append(Agent.email == member.email)
    if member.phone:
        criteria.append(Agent.phone == member.phone)
    if not criteria:
        return None
    return db.query(Agent).filter(or_(*criteria)).first()

def get_agent_by_email(email):
    if not email:
        return None
    return db.query(Agent).filter(Agent.email == email).first()

# 1. Event attendances
ea_count = db.query(EventAttendance).count()
print(f"Migrating {ea_count} event attendances...")
migrated_ea = 0
for ea in db.query(EventAttendance).all():
    member = db.query(Member).filter(Member.id == ea.member_id).first()
    if not member:
        continue
    agent = get_agent_for_member(member)
    if not agent:
        continue
    db.add(AgentActivity(
        agent_id=agent.id,
        activity_type="attendance",
        source_type="crm_event",
        source_id=ea.event_id,
        status="present" if ea.attended else "absent",
        notes=ea.notes if hasattr(ea, 'notes') else None,
        occurred_at=ea.session_date if hasattr(ea, 'session_date') else ea.created_at,
    ))
    migrated_ea += 1
    if migrated_ea % 200 == 0:
        db.commit()
        print(f"  {migrated_ea} migrated...")
db.commit()
print(f"  Event attendances: {migrated_ea} migrated")
total += migrated_ea

# 2. Glory House attendances
gha_count = db.query(GloryHouseAttendance).count()
print(f"Migrating {gha_count} glory house attendances...")
migrated_gha = 0
for gha in db.query(GloryHouseAttendance).all():
    member = db.query(Member).filter(Member.id == gha.member_id).first()
    if not member:
        continue
    agent = get_agent_for_member(member)
    if not agent:
        continue
    session = db.query(GloryHouseSession).filter(GloryHouseSession.id == gha.session_id).first()
    db.add(AgentActivity(
        agent_id=agent.id,
        activity_type="attendance",
        source_type="glory_house",
        source_id=gha.session_id,
        status="present" if gha.attended else "absent",
        notes=gha.absence_reason_detail if hasattr(gha, 'absence_reason_detail') else gha.absence_reason,
        occurred_at=session.session_date if session else gha.scanned_at,
    ))
    migrated_gha += 1
    if migrated_gha % 200 == 0:
        db.commit()
        print(f"  {migrated_gha} migrated...")
db.commit()
print(f"  Glory house attendances: {migrated_gha} migrated")
total += migrated_gha

# 3. Course enrollments
enr_count = db.query(Enrollment).count()
print(f"Migrating {enr_count} course enrollments...")
migrated_enr = 0
for enr in db.query(Enrollment).all():
    user = db.query(User).filter(User.id == enr.user_id).first()
    if not user:
        continue
    agent = get_agent_by_email(user.email)
    if not agent:
        continue
    db.add(AgentActivity(
        agent_id=agent.id,
        activity_type="enrollment",
        source_type="course",
        source_id=enr.course_id,
        status=enr.status,
        occurred_at=enr.created_at,
    ))
    migrated_enr += 1
    if migrated_enr % 200 == 0:
        db.commit()
        print(f"  {migrated_enr} migrated...")
db.commit()
print(f"  Course enrollments: {migrated_enr} migrated")
total += migrated_enr

# 4. Donations
don_count = db.query(Donation).count()
print(f"Migrating {don_count} donations...")
migrated_don = 0
for don in db.query(Donation).all():
    if don.member_id:
        member = db.query(Member).filter(Member.id == don.member_id).first()
        agent = get_agent_for_member(member) if member else None
    elif don.donor_email:
        agent = get_agent_by_email(don.donor_email)
    else:
        agent = None
    if not agent:
        continue
    db.add(AgentActivity(
        agent_id=agent.id,
        activity_type="donation",
        source_type="donation_form",
        source_id=don.id,
        status=don.status if hasattr(don, 'status') else None,
        notes=f"Amount: {don.amount}" if hasattr(don, 'amount') else None,
        occurred_at=don.donation_date if hasattr(don, 'donation_date') else don.created_at,
    ))
    migrated_don += 1
    if migrated_don % 200 == 0:
        db.commit()
        print(f"  {migrated_don} migrated...")
db.commit()
print(f"  Donations: {migrated_don} migrated")
total += migrated_don

print(f"\n{'=' * 60}")
print(f"TOTAL: {total} activities migrated to agent_activities")
print(f"{'=' * 60}")

db.close()
