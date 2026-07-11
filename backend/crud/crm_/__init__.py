"""CRM subdomain CRUD package.

This package splits the monolithic ``backend.crud.crm`` module into
focused, business-domain modules.  It re-exports every public symbol so
existing callers can continue using ``from backend.crud import crm`` or
``from backend.crud.crm_ import ...``.
"""
# ruff: noqa: F401

from backend.crud.crm_.communication import (
    create_communication_log,
    delete_communication_log,
    get_communication_log,
    get_communication_logs,
    update_communication_log,
)
from backend.crud.crm_.community import (
    create_community_card,
    delete_community_card,
    get_community_card,
    get_community_cards,
    update_community_card,
)
from backend.crud.crm_.counseling import (
    create_counseling_ticket,
    delete_counseling_ticket,
    get_counseling_ticket,
    get_counseling_tickets,
    update_counseling_ticket,
)
from backend.crud.crm_.donations import (
    create_donation,
    delete_donation,
    get_donation,
    get_donations,
    get_total_donations_amount,
    update_donation,
)
from backend.crud.crm_.events import (
    create_crm_event,
    create_event_attendance,
    delete_crm_event,
    delete_event_attendance,
    get_crm_event,
    get_crm_events,
    get_event_attendance,
    update_crm_event,
)
from backend.crud.crm_.families import (
    create_family,
    delete_family,
    get_families,
    get_family,
    get_family_personas,
    update_family,
)
from backend.crud.crm_.groups import (
    create_grupo,
    delete_grupo,
    get_grupo,
    get_grupos,
    update_grupo,
)
# health.py imports from backend.api.crm._shared — not imported here
# to avoid circular dependency. Access directly:
#   from backend.crud.crm_.health import calculate_health_score
from backend.crud.crm_.milestones import (
    create_milestone,
    delete_milestone,
    get_milestones,
    update_milestone,
)
from backend.crud.crm_.notifications import (
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_as_read,
)
from backend.crud.crm_.personas import (
    create_persona,
    delete_persona,
    get_persona,
    get_persona_donations,
    get_personas,
    get_talents,
    search_personas,
    search_personas_paginated,
    update_persona,
)
from backend.crud.crm_.prayer import (
    create_prayer_request,
    delete_prayer_request,
    get_prayer_request,
    get_prayer_requests,
    update_prayer_request,
)
from backend.crud.crm_.shared import (
    get_user_sede_id,
    resolve_persona_id_for_user,
    resolve_persona_id_from_identity,
)
from backend.crud.crm_.support import (
    create_support_ticket,
    delete_support_ticket,
    get_support_ticket,
    get_support_tickets,
    update_support_ticket,
)
from backend.crud.crm_.tasks import (
    create_crm_task,
    delete_crm_task,
    get_crm_tasks,
    update_crm_task,
)
from backend.crud.crm_.timeline import get_persona_timeline
from backend.crud.crm_.volunteers import (
    create_volunteer_shift,
    delete_volunteer_shift,
    get_volunteer_shift,
    get_volunteer_shifts,
    update_volunteer_shift,
)
