"""
CCF Backend — CRUD operations split by domain.

Each sub-module contains the data-access functions for one business area.
This package re-exports only symbols consumed via ``from backend import crud``
/ ``crud.function_name(...)``.  Direct sub-module imports
(``from backend.crud import cms``) are preferred for new code.
"""
# ruff: noqa: F401, I001

# ── Sub-modules accessed directly (kernel, agenda, pipeline, test aliases) ──
from backend.crud import (
    agenda,  # noqa: F401
    crm_pipeline,  # noqa: F401
    kernel,  # noqa: F401
)

# ── Agents ─────────────────────────────────────────────────────────────────
from backend.crud.agents import (
    acknowledge_insight,
    create_agent_insight,
    create_agent_task,
    list_agent_insights,
    list_agent_tasks,
    update_agent_task,
)

# ── Audit ──────────────────────────────────────────────────────────────────
from backend.crud.audit import create_admin_audit_log, get_admin_audit_logs

# ── CMS (consumed by cms_v2, cms) ────────────────────────────
from backend.crud.cms import (
    activate_cms_theme,
    archive_cms_section,
    archive_cms_site,
    archive_cms_theme,
    create_announcement,
    create_cms_media_item,
    create_cms_menu,
    create_cms_menu_item,
    create_cms_page,
    create_cms_section,
    create_cms_site,
    create_cms_theme,
    create_testimonial,
    delete_announcement,
    delete_cms_media_item,
    delete_cms_menu,
    delete_cms_menu_item,
    delete_cms_page,
    delete_cms_section,
    delete_testimonial,
    get_active_cms_theme,
    get_announcement,
    get_cms_menu,
    get_cms_menu_item,
    get_cms_page,
    get_cms_page_version,
    get_cms_section,
    get_cms_site_by_key,
    get_cms_theme,
    get_public_cms_page,
    get_testimonial,
    list_announcements,
    list_cms_menu_items,
    list_cms_menus,
    list_cms_page_versions,
    list_cms_pages,
    list_cms_publish_logs,
    list_cms_sections,
    list_cms_sites,
    list_cms_themes,
    list_testimonials,
    reorder_cms_menu_items,
    reorder_cms_sections,
    resolve_persona_id_for_user,
    restore_cms_page_version,
    transition_cms_page_status,
    update_announcement,
    update_cms_media_item,
    update_cms_menu,
    update_cms_menu_item,
    update_cms_page,
    update_cms_section,
    update_cms_site,
    update_cms_theme,
    update_pastoral_profile,
    update_testimonial,
)

# ── CRM (consumed by pastoral, personas, donations, support, messaging …) ─
from backend.crud.crm import (
    create_communication_log,
    create_community_card,
    create_counseling_ticket,
    create_crm_event,
    create_crm_task,
    create_donation,
    create_event_attendance,
    create_family,
    create_grupo,
    create_milestone,
    create_persona,
    create_prayer_request,
    create_support_ticket,
    get_communication_logs,
    get_community_cards,
    get_counseling_tickets,
    get_donations,
    get_families,
    get_family_personas,
    get_grupos,
    get_milestones,
    get_persona_donations,
    get_persona_timeline,
    get_personas,
    get_prayer_requests,
    get_support_tickets,
    get_total_donations_amount,
    get_user_notifications,
    get_user_sede_id,
    update_support_ticket,
    get_volunteer_shifts,
    mark_all_notifications_read,
    mark_notification_as_read,
    search_personas,
    update_crm_task,
    update_grupo,
    update_persona,
)

# ── CRM Extended — chat / conversations ────────────────────────────────────
from backend.crud.crm_extended import (
    create_conversation,
    create_direct_message,
    get_conversation_messages,
    get_unread_count_for_conversation,
    get_user_conversations,
    mark_conversation_read,
)

# ── Dashboard ──────────────────────────────────────────────────────────────
from backend.crud.dashboard import (
    get_dashboard_metrics,
    get_pastor_radar,
    search_knowledge_base,
)

# ── Evangelism ─────────────────────────────────────────────────────────────
from backend.crud.evangelism import get_estrategias

# ── Governance ─────────────────────────────────────────────────────────────
from backend.crud.governance import get_automation_rules

# ── Identity & auth ────────────────────────────────────────────────────────
from backend.crud.identity import (
    award_badge,
    get_ui_preferences,
    get_user_by_email,
    grant_xp,
    update_ui_preferences,
)

# ── Projects ───────────────────────────────────────────────────────────────
from backend.crud.projects import (
    create_activity_log,
    create_default_phases,
    create_project,
    get_project_phases,
    get_projects,
    set_project_phases,
)
