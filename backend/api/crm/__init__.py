"""
CRM API package.

Aggregates endpoints from members and pastoral sub-modules.
Exposes ``router`` for mounting in app.py, plus serialization helpers
for use by other modules.
"""

from fastapi import APIRouter

# ── shared utilities ───────────────────────────────────────────────────
from backend.api.crm._shared import (_persona_full_name, _serialize_case,
                                     _serialize_member_position,
                                     _serialize_message_group, _serialize_task,
                                     utc_now)

# ── main router (used by app.py: ``crm.router``) ──────────────────────
router = APIRouter(tags=["CRM"])

# ── include sub-routers ────────────────────────────────────────────────
from backend.api.crm import members, pastoral, personas, resources  # noqa: E402

router.include_router(members.router)
router.include_router(pastoral.router)
router.include_router(personas.router)
router.include_router(resources.router)

__all__ = [
    "router",
    "utc_now",
    "_serialize_member_position",
    "_serialize_case",
    "_persona_full_name",
    "_serialize_task",
    "_serialize_message_group",
]
