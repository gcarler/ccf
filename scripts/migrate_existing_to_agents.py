#!/usr/bin/env python
"""
Phase 2b: Data migration — populate agents table from existing users and members.

Usage:
    cd /root/ccf && ./venv/bin/python scripts/migrate_existing_to_agents.py

This creates canonical Agent records for:
1. All Members (with or without linked Users)
2. All Users that don't have a corresponding Member
3. Deduplicates by email/phone
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

from backend.core.database import SessionLocal
from backend.models import Member, User
from backend.models_agents import (Agent, AgentAuth, AgentContact,
                                    AgentRole)

db = SessionLocal()
created = 0
skipped = 0
linked = 0

def get_agent_code(db):
    count = db.query(Agent).count()
    return f"CCF-AGENT-{count + 1:05d}"

def find_existing_by_email_or_phone(email, phone):
    """Find existing agent by email or phone."""
    criteria = []
    if email:
        criteria.append(Agent.email == email)
    if phone:
        criteria.append(Agent.phone == phone)
    if criteria:
        from sqlalchemy import or_
        return db.query(Agent).filter(or_(*criteria)).first()
    return None

print("=" * 60)
print("MIGRATING MEMBERS → AGENTS")
print("=" * 60)

members = db.query(Member).all()
print(f"Found {len(members)} members to migrate...")

for m in members:
    existing = find_existing_by_email_or_phone(m.email, m.phone)
    if existing:
        skipped += 1
        continue

    agent = Agent(
        code=get_agent_code(db),
        first_name=m.first_name,
        last_name=m.last_name,
        email=m.email,
        phone=m.phone,
        spiritual_stage="visitor" if (m.church_role or "").lower().startswith("visitante") else "believer",
        is_active=m.is_active if hasattr(m, 'is_active') else True,
    )
    db.add(agent)
    db.flush()

    # Create auth if member has a linked user
    if m.user_id:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            db.add(AgentAuth(
                agent_id=agent.id,
                username=user.username,
                provider="local",
                is_email_verified=user.is_email_verified if hasattr(user, 'is_email_verified') else False,
            ))
            linked += 1

    # Create church role
    if m.church_role:
        db.add(AgentRole(
            agent_id=agent.id,
            role_type="church",
            role_value=m.church_role,
        ))

    created += 1
    if created % 100 == 0:
        db.commit()
        print(f"  Created {created} agents so far...")

db.commit()
print(f"Members → Agents: {created} created, {skipped} skipped, {linked} linked to auth")

print("\n" + "=" * 60)
print("MIGRATING USERS WITHOUT MEMBERS → AGENTS")
print("=" * 60)

# Find users without agents
users_without_agent = []
for u in db.query(User).all():
    existing = find_existing_by_email_or_phone(u.email, None)
    if not existing:
        users_without_agent.append(u)

print(f"Found {len(users_without_agent)} users without agents...")

user_created = 0
for u in users_without_agent:
    agent = Agent(
        code=get_agent_code(db),
        first_name=u.username.split("@")[0] if "@" in (u.email or "") else u.username,
        last_name="",
        email=u.email,
        spiritual_stage="visitor",
        is_active=u.is_active if hasattr(u, 'is_active') else True,
    )
    db.add(agent)
    db.flush()

    db.add(AgentAuth(
        agent_id=agent.id,
        username=u.username,
        provider="local",
        is_email_verified=u.is_email_verified if hasattr(u, 'is_email_verified') else False,
    ))

    # Platform role
    if u.role:
        db.add(AgentRole(
            agent_id=agent.id,
            role_type="platform",
            role_value=u.role,
        ))

    user_created += 1

db.commit()
print(f"Users → Agents: {user_created} created")

# Summary
total_agents = db.query(Agent).count()
print(f"\n{'=' * 60}")
print(f"SUMMARY: {total_agents} total agents in database")
print(f"{'=' * 60}")

db.close()
