import os

crm_path = 'backend/api/crm.py'
evang_path = 'backend/api/evangelism.py'

f = open(crm_path, encoding='utf-8').read()

# Define the start and end of the events section in crm.py
start_marker = "# --- EVENTS & ATTENDANCE ---"
# Find where the events section starts
idx_start = f.find(start_marker)

if idx_start == -1:
    print("Could not find start marker")
    exit(1)

# Let's find the end of the events section. The next major section is "# --- METRICS & DASHBOARD ---" or EOF.
# Actually, the CRM has "# --- METRICS & DASHBOARD ---" near the bottom?
idx_end = f.find("# --- METRICS & DASHBOARD ---", idx_start)
if idx_end == -1:
    idx_end = len(f)

# Extract the block
events_code = f[idx_start:idx_end]

# Now, we create evangelism.py with the necessary imports
imports = """from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import datetime
from datetime import timedelta

from backend import schemas, models, crud
from backend.core.database import get_db
from backend.core.security import get_current_user
from backend.api.auth import require_admin, require_pastor_or_admin

router = APIRouter()

def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

def record_admin_action(db: Session, current_user: models.User, action: str, resource_type: str, resource_id: str):
    log = models.AdminAuditLog(
        actor_user_id=current_user.id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id
    )
    db.add(log)
    db.commit()

# Constants used in events
ABSENTEES_PREVIEW_LIMIT = 50

"""

with open(evang_path, 'w', encoding='utf-8') as out:
    out.write(imports + events_code)

# Remove the events code from crm.py
new_crm_code = f[:idx_start] + f[idx_end:]

# Wait, there might be other things depending on utc_now or record_admin_action in crm.py, 
# so we don't delete them from crm.py, we just duplicated them for evangelism.py which is fine.

with open(crm_path, 'w', encoding='utf-8') as out:
    out.write(new_crm_code)

print("Split completed")
