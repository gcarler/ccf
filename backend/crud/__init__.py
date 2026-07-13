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

    kernel,  # noqa: F401
)
from backend.crud.crm_ import extended as crm_extended  # noqa: F401
from backend.crud.crm_ import resources as crm_resources  # noqa: F401

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
    capture_daily_seo_snapshots,
    create_announcement,
    create_cms_category,
    create_cms_media_item,
    create_cms_menu,
    create_cms_menu_item,
    create_cms_page,
    create_cms_page_version,
    create_cms_post,
    create_cms_section,
    create_cms_site,
    create_cms_tag,
    create_cms_theme,
    create_testimonial,
    delete_announcement,
    delete_cms_category,
    delete_cms_media_item,
    delete_cms_menu,
    delete_cms_menu_item,
    delete_cms_page,
    delete_cms_post,
    delete_cms_section,
    delete_cms_tag,
    delete_testimonial,
    update_cms_post,
    find_pages_due_for_archive,
    find_pages_due_for_publish,
    find_posts_due_for_archive,
    get_active_cms_theme,
    get_announcement,
    get_cms_category,
    get_cms_menu,
    get_cms_menu_item,
    get_cms_media_item,
    get_cms_page,
    get_cms_page_version,
    get_cms_post,
    get_cms_post_by_id,
    get_cms_section,
    get_cms_site_by_key,
    get_cms_tag,
    get_cms_theme,
    get_post_categories,
    get_post_tags,
    get_posts_categories_batch,
    get_posts_tags_batch,
    get_public_cms_page,
    get_seo_trend,
    get_public_cms_posts,
    get_public_cms_post,
    get_testimonial,
    list_announcements,
    list_cms_categories,
    list_cms_menu_items,
    list_cms_media_items,
    list_cms_menus,
    list_cms_page_versions,
    list_cms_pages,
    list_cms_posts,
    list_cms_publish_logs,
    list_cms_sections,
    list_cms_sites,
    list_cms_tags,
    list_cms_themes,
    list_pastoral_team,
    list_testimonials,
    process_due_content,
    reorder_cms_menu_items,
    reorder_cms_sections,
    resolve_persona_id_for_user,
    restore_cms_page_version,
    transition_cms_page_status,
    update_announcement,
    update_cms_category,
    update_cms_media_item,
    update_cms_menu,
    update_cms_menu_item,
    update_cms_page,
    update_cms_section,
    update_cms_site,
    update_cms_tag,
    update_cms_theme,
    update_pastoral_profile,
    update_testimonial,
)

# ── CRM (consumed by pastoral, personas, donations, support, messaging …) ─
# Note: calculate_health_score, calculate_pastoral_health, calculate_pastoral_health_score
# live in crm_/health.py which imports from backend.api.crm._shared — importing them
# eagerly here creates a circular import. Access via:
#   from backend.crud.crm_.health import calculate_health_score
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
    create_volunteer_shift,
    delete_communication_log,
    delete_community_card,
    delete_counseling_ticket,
    delete_crm_event,
    delete_crm_task,
    delete_donation,
    delete_event_attendance,
    delete_family,
    delete_grupo,
    delete_milestone,
    delete_persona,
    delete_prayer_request,
    delete_support_ticket,
    delete_volunteer_shift,
    get_communication_log,
    get_communication_logs,
    get_community_card,
    get_community_cards,
    get_counseling_ticket,
    get_counseling_tickets,
    get_crm_event,
    get_crm_events,
    get_crm_tasks,
    get_donation,
    get_donations,
    get_event_attendance,
    get_families,
    get_family,
    get_family_personas,
    get_grupo,
    get_grupos,
    get_milestones,
    get_persona,
    get_persona_donations,
    get_persona_timeline,
    get_personas,
    get_prayer_request,
    get_prayer_requests,
    get_support_ticket,
    get_support_tickets,
    get_talents,
    get_total_donations_amount,
    get_user_notifications,
    get_user_sede_id,
    get_volunteer_shift,
    get_volunteer_shifts,
    mark_all_notifications_read,
    mark_notification_as_read,
    resolve_persona_id_from_identity,
    search_personas,
    search_personas_paginated,
    update_communication_log,
    update_community_card,
    update_counseling_ticket,
    update_crm_event,
    update_crm_task,
    update_donation,
    update_family,
    update_grupo,
    update_milestone,
    update_prayer_request,
    update_persona,
    update_support_ticket,
    update_volunteer_shift,
)

# ── CRM Extended — chat / conversations ────────────────────────────────────
from backend.crud.crm_.extended import (
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
    delete_attachment,
    delete_supply,
    get_project,  # Axiom 3 defense-in-depth: single-record scope filter
    get_project_milestones,
    get_project_phases,
    get_project_whiteboard,
    get_project_wiki,
    get_projects,
    get_task_supplies,
    set_project_phases,
)
