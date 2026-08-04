"""Evangelism Events package — split from evangelism_events.py.

Sub-modules:
- events_main.py: CRUD, analytics, roles, audience, export, attendance history
- events_participantes.py: attendance registration, assignments, session detail
- events_checkin.py: fast check-in / visitor registration
- events_registrations.py: pre-registration admin (plan_de_preregistro)
- _shared.py: permission helpers
"""

from fastapi import APIRouter

router = APIRouter(tags=["Evangelismo - Eventos"])

from backend.api.evangelism_events import (
    events_checkin,
    events_main,
    events_participantes,
    events_registrations,
)

router.include_router(events_main.router)
router.include_router(events_participantes.router)
router.include_router(events_checkin.router)
router.include_router(events_registrations.router)
