"""
CRM API package.

Aggregates endpoints from members and pastoral sub-modules.
Exposes ``router`` for mounting in app.py, plus serialization helpers
for use by other modules.
"""

from fastapi import APIRouter

# ── shared utilities (re-exported for backward compatibility) ──────────
from backend.api.crm._shared import (
    utc_now,
    _serialize_member_position,
    _serialize_case,
    _member_full_name,
    _serialize_task,
    _serialize_message_group,
)

# ── main router (used by app.py: ``crm.router``) ──────────────────────
router = APIRouter(tags=["CRM"])

# ── include sub-routers ────────────────────────────────────────────────
from backend.api.crm import members
from backend.api.crm import pastoral

router.include_router(members.router)
router.include_router(pastoral.router)

__all__ = [
    "router",
    "utc_now",
    "_serialize_member_position",
    "_serialize_case",
    "_member_full_name",
    "_serialize_task",
    "_serialize_message_group",
]
