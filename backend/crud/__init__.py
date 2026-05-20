"""
CCF Backend — CRUD operations split by domain.

Each sub-module contains the data-access functions for one business area.
This package re-exports everything so that existing callers using
``from backend import crud`` / ``crud.function_name(...)`` continue to work.
"""

# Utils
from backend.crud._utils import (  # noqa: F401
    _utcnow,
    analyze_pastoral_priority,
    analyze_pastoral_sentiment,
)

# Identity & auth
from backend.crud.identity import (  # noqa: F401
    get_user,
    get_user_by_email,
    get_user_by_username,
    get_users,
    create_user,
    update_user,
    delete_user,
    create_refresh_token,
    get_valid_refresh_token,
    revoke_refresh_token,
    grant_xp,
    award_badge,
    update_ui_preferences,
    get_ui_preferences,
)

# Academy
from backend.crud.academy import (  # noqa: F401
    get_courses,
    get_course,
    check_user_meets_prerequisites,
    get_enrollment,
    get_enrollments_by_user,
    create_enrollment,
    get_assessment,
    get_assessment_with_questions,
    create_or_update_assessment_attempt,
    submit_assessment_attempt,
    get_lesson_progress,
    update_lesson_progress,
    get_certificates_by_user,
    get_certificate_by_code,
    issue_certificate_for_enrollment,
    issue_certificate,
    issue_pending_certificates,
    close_formal_acta,
    get_latest_acta_by_course,
    record_activity_attendance,
    create_assignment_submission,
    list_assignment_submissions_with_meta,
    get_assignment_submission_with_meta,
    grade_assignment_submission,
    get_academy_candidates,
    get_forum_threads,
    create_forum_thread,
)

# CRM
from backend.crud.crm import (  # noqa: F401
    get_member_donations,
    create_member,
    search_members,
    get_members,
    update_member,
    create_pipeline_lead,
    update_pipeline_lead,
    get_pipeline_leads,
    create_pastoral_call_log,
    get_pastoral_call_logs,
    get_crm_events,
    create_crm_event,
    get_crm_tasks,
    create_crm_task,
    update_crm_task,
    get_volunteer_shifts,
    create_volunteer_shift,
    create_event_attendance,
    get_counseling_tickets,
    create_counseling_ticket,
    get_prayer_requests,
    create_prayer_request,
    get_glory_houses,
    create_glory_house,
    update_glory_house,
    get_talents,
    get_families,
    create_family,
    get_member_timeline,
    create_communication_log,
    get_communication_logs,
    get_user_notifications,
    mark_notification_as_read,
    mark_all_notifications_read,
    create_donation,
    get_donations,
    get_total_donations_amount,
    get_milestones,
    create_milestone,
    get_family_members,
    create_support_ticket,
    get_support_tickets,
    update_support_ticket,
    get_community_cards,
    create_community_card,
)

# CMS
from backend.crud.cms import (  # noqa: F401
    update_page_content,
    get_page_content,
    list_page_contents,
    get_or_create_page_content,
    get_page_content_versions,
    restore_page_content_version,
    get_or_create_content_publication,
    update_content_publication,
    list_content_publications,
    create_cms_media_item,
    list_cms_media_items,
    get_cms_media_item,
    update_cms_media_item,
    delete_cms_media_item,
    create_media_asset,
    increment_content_metric,
    list_cms_sites,
    get_cms_site_by_key,
    create_cms_site,
    update_cms_site,
    archive_cms_site,
    list_cms_themes,
    create_cms_theme,
    get_cms_theme,
    update_cms_theme,
    activate_cms_theme,
    archive_cms_theme,
    get_active_cms_theme,
    list_cms_menus,
    get_cms_menu,
    create_cms_menu,
    update_cms_menu,
    delete_cms_menu,
    list_cms_menu_items,
    create_cms_menu_item,
    get_cms_menu_item,
    update_cms_menu_item,
    delete_cms_menu_item,
    reorder_cms_menu_items,
    list_cms_pages,
    get_cms_page,
    create_cms_page,
    update_cms_page,
    delete_cms_page,
    list_cms_sections,
    create_cms_section,
    get_cms_section,
    update_cms_section,
    delete_cms_section,
    archive_cms_section,
    reorder_cms_sections,
    create_cms_page_version,
    list_cms_page_versions,
    get_cms_page_version,
    list_cms_publish_logs,
    restore_cms_page_version,
    transition_cms_page_status,
    get_public_cms_page,
    create_announcement,
    list_announcements,
    get_announcement,
    update_announcement,
    delete_announcement,
    create_testimonial,
    list_testimonials,
    get_testimonial,
    update_testimonial,
    delete_testimonial,
)

# Agents
from backend.crud.agents import (  # noqa: F401
    create_agent_task,
    list_agent_tasks,
    update_agent_task,
    create_agent_insight,
    list_agent_insights,
    acknowledge_insight,
)

# Audit
from backend.crud.audit import (  # noqa: F401
    create_admin_audit_log,
    get_admin_audit_logs,
)

# Dashboard
from backend.crud.dashboard import (  # noqa: F401
    get_dashboard_metrics,
    get_pastor_radar,
    get_pilot_readiness,
    search_knowledge_base,
)

# Projects
from backend.crud.projects import (  # noqa: F401
    create_project,
    create_project_task,
)

# Assets
from backend.crud.assets import (  # noqa: F401
    get_assets,
    create_maintenance_log,
)
