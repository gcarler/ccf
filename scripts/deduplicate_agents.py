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
Phase 4: Agent deduplication and merge tool.

Finds duplicate agents by email/phone and offers merge operations.

Usage:
    cd /root/ccf && ./venv/bin/python scripts/deduplicate_agents.py [--auto-merge]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")

from collections import defaultdict

from sqlalchemy import or_

from backend.core.database import SessionLocal
from backend.models import *  # noqa: F401
from backend.models_agents import (
    Agent,
    AgentActivity,
    AgentAuth,
    AgentContact,
    AgentFamily,
    AgentJourney,
    AgentPermission,
    AgentRole,
)

db = SessionLocal()

print("=" * 60)
print("AGENT DEDUPLICATION TOOL")
print("=" * 60)

# Find duplicates by email
email_groups = defaultdict(list)
for agent in db.query(Agent).filter(Agent.email != None).all():
    email_groups[agent.email.lower()].append(agent)

# Find duplicates by phone
phone_groups = defaultdict(list)
for agent in db.query(Agent).filter(Agent.phone != None).all():
    phone_groups[agent.phone].append(agent)

duplicates = []
for email, agents in email_groups.items():
    if len(agents) > 1:
        duplicates.append(("email", email, agents))

for phone, agents in phone_groups.items():
    if len(agents) > 1:
        duplicates.append(("phone", phone, agents))

if not duplicates:
    print("\n✓ No duplicates found. All agents are unique.")
    db.close()
    sys.exit(0)

print(f"\nFound {len(duplicates)} duplicate group(s):\n")

for i, (field, value, agents) in enumerate(duplicates):
    print(f"  Group {i+1} (by {field}: '{value}'):")
    for a in agents:
        roles = db.query(AgentRole).filter(AgentRole.agent_id == a.id).count()
        activities = db.query(AgentActivity).filter(AgentActivity.agent_id == a.id).count()
        print(f"    Agent #{a.id} ({a.code}): {a.full_name} - {roles} roles, {activities} activities")
    print()

auto_merge = "--auto-merge" in sys.argv

if auto_merge:
    print("AUTO-MERGE MODE: Merging duplicates...\n")
    merged = 0
    for field, value, agents in duplicates:
        # Keep the first agent (oldest), merge others into it
        primary = agents[0]
        for duplicate in agents[1:]:
            print(f"  Merging Agent #{duplicate.id} → Agent #{primary.id}")
            
            # Move activities
            db.query(AgentActivity).filter(AgentActivity.agent_id == duplicate.id).update({AgentActivity.agent_id: primary.id})
            
            # Move roles (avoid duplicates)
            for role in db.query(AgentRole).filter(AgentRole.agent_id == duplicate.id).all():
                existing = db.query(AgentRole).filter(
                    AgentRole.agent_id == primary.id,
                    AgentRole.role_type == role.role_type,
                    AgentRole.role_value == role.role_value,
                ).first()
                if not existing:
                    role.agent_id = primary.id
            
            # Move auth (avoid duplicates)
            for auth in db.query(AgentAuth).filter(AgentAuth.agent_id == duplicate.id).all():
                existing = db.query(AgentAuth).filter(
                    AgentAuth.agent_id == primary.id,
                    AgentAuth.username == auth.username,
                ).first()
                if not existing:
                    auth.agent_id = primary.id
            
            # Move contacts
            db.query(AgentContact).filter(AgentContact.agent_id == duplicate.id).update({AgentContact.agent_id: primary.id})
            
            # Move journey
            db.query(AgentJourney).filter(AgentJourney.agent_id == duplicate.id).update({AgentJourney.agent_id: primary.id})
            
            # Move permissions
            db.query(AgentPermission).filter(AgentPermission.agent_id == duplicate.id).update({AgentPermission.agent_id: primary.id})
            
            # Delete duplicate
            db.delete(duplicate)
            merged += 1
        
        db.commit()
    
    print(f"\n✓ Merged {merged} duplicate agents.")
else:
    print("Run with --auto-merge to automatically merge duplicates.")
    print("Primary agent (kept) = oldest. Others merged into primary.")

db.close()
