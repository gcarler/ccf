"""
CCF Backend — CRUD operations split by domain.

Each sub-module contains the data-access functions for one business area.
This package re-exports everything so that existing callers using
``from backend import crud`` / ``crud.function_name(...)`` continue to work.
"""

# Utils
from backend.crud._utils import _utcnow  # noqa: F401
from backend.crud._utils import (analyze_pastoral_priority,
                                 analyze_pastoral_sentiment)
# Academy
from backend.crud.academy import check_user_meets_prerequisites  # noqa: F401
from backend.crud.academy import (close_formal_acta, create_assessment,
                                  create_assessment_option,
                                  create_assessment_question,
                                  create_assignment_submission, create_course,
                                  create_course_attendance, create_enrollment,
                                  create_forum_thread, create_lesson,
                                  create_or_update_assessment_attempt,
                                  create_resource, delete_assessment,
                                  delete_assessment_option,
                                  delete_assessment_question,
                                  delete_certificate, delete_course,
                                  delete_course_attendance, delete_enrollment,
                                  delete_forum_thread, delete_lesson,
                                  delete_resource, get_academy_candidates,
                                  get_assessment, get_assessment_by_id,
                                  get_assessment_options,
                                  get_assessment_question,
                                  get_assessment_questions,
                                  get_assessment_with_questions,
                                  get_assessments_by_course,
                                  get_assignment_submission_with_meta,
                                  get_certificate, get_certificate_by_code,
                                  get_certificates_by_user, get_course,
                                  get_course_attendance, get_course_students,
                                  get_courses, get_enrollment,
                                  get_enrollment_by_user_course,
                                  get_enrollments_by_user, get_forum_thread,
                                  get_forum_threads, get_latest_acta_by_course,
                                  get_lesson, get_lesson_progress,
                                  get_lesson_resources, get_lessons_by_course,
                                  grade_assignment_submission,
                                  issue_certificate,
                                  issue_certificate_for_enrollment,
                                  issue_pending_certificates,
                                  list_assignment_submissions_with_meta,
                                  record_activity_attendance,
                                  submit_assessment_attempt, update_assessment,
                                  update_assessment_option,
                                  update_assessment_question, update_course,
                                  update_enrollment, update_lesson,
                                  update_lesson_progress)
# Agents
from backend.crud.agents import acknowledge_insight  # noqa: F401
from backend.crud.agents import (create_agent_insight, create_agent_task,
                                 delete_agent_insight, delete_agent_task,
                                 list_agent_insights, list_agent_tasks,
                                 update_agent_task)
# Assets
from backend.crud.assets import create_asset  # noqa: F401
from backend.crud.assets import (create_maintenance_log, delete_asset,
                                 get_asset, get_assets, get_maintenance_logs,
                                 update_asset)
# Audit
from backend.crud.audit import create_admin_audit_log  # noqa: F401
from backend.crud.audit import get_admin_audit_logs
# CMS
from backend.crud.cms import activate_cms_theme  # noqa: F401
from backend.crud.cms import (archive_cms_section, archive_cms_site,
                              archive_cms_theme, create_announcement,
                              create_cms_media_item, create_cms_menu,
                              create_cms_menu_item, create_cms_page,
                              create_cms_page_version, create_cms_section,
                              create_cms_site, create_cms_theme,
                              create_media_asset, create_testimonial,
                              delete_announcement, delete_cms_media_item,
                              delete_cms_menu, delete_cms_menu_item,
                              delete_cms_page, delete_cms_section,
                              delete_media_asset, delete_testimonial,
                              get_active_cms_theme, get_announcement,
                              get_cms_media_item, get_cms_menu,
                              get_cms_menu_item, get_cms_page,
                              get_cms_page_version, get_cms_section,
                              get_cms_site_by_key, get_cms_theme,
                              get_or_create_content_publication,
                              get_or_create_page_content, get_page_content,
                              get_page_content_versions, get_public_cms_page,
                              get_testimonial, increment_content_metric,
                              list_announcements, list_cms_media_items,
                              list_cms_menu_items, list_cms_menus,
                              list_cms_page_versions, list_cms_pages,
                              list_cms_publish_logs, list_cms_sections,
                              list_cms_sites, list_cms_themes,
                              list_content_publications, list_page_contents,
                              list_testimonials, reorder_cms_menu_items,
                              reorder_cms_sections, restore_cms_page_version,
                              restore_page_content_version,
                              transition_cms_page_status, update_announcement,
                              update_cms_media_item, update_cms_menu,
                              update_cms_menu_item, update_cms_page,
                              update_cms_section, update_cms_site,
                              update_cms_theme, update_content_publication,
                              update_page_content, update_testimonial)
# Consolidation Extended — assignments, interactions, follow-up tasks
from backend.crud.consolidation import (  # noqa: F401
    create_consolidation_assignment, create_consolidation_follow_up_task,
    create_consolidation_interaction, delete_consolidation_assignment,
    delete_consolidation_follow_up_task, delete_consolidation_interaction,
    get_consolidation_assignment, get_consolidation_assignments,
    get_consolidation_follow_up_task, get_consolidation_follow_up_tasks,
    get_consolidation_interaction, get_consolidation_interactions,
    update_consolidation_assignment, update_consolidation_follow_up_task,
    update_consolidation_interaction)
# CRM
from backend.crud.crm import create_communication_log  # noqa: F401
from backend.crud.crm import (create_community_card, create_consolidation_case,
                              create_counseling_ticket, create_crm_event,
                              create_crm_task, create_donation,
                              create_evangelism_strategy,
                              create_event_attendance, create_family,
                              create_glory_house, create_member,
                              create_milestone, create_pastoral_call_log,
                              create_pipeline_lead, create_prayer_request,
                              create_support_ticket, create_volunteer_shift,
                              delete_communication_log, delete_community_card,
                              delete_consolidation_case,
                              delete_counseling_ticket, delete_crm_event,
                              delete_crm_task, delete_donation,
                              delete_evangelism_strategy,
                              delete_event_attendance, delete_family,
                              delete_glory_house, delete_member,
                              delete_milestone, delete_pastoral_call_log,
                              delete_pipeline_lead, delete_prayer_request,
                              delete_support_ticket, delete_volunteer_shift,
                              get_communication_log, get_communication_logs,
                              get_community_card, get_community_cards,
                              get_consolidation_case, get_counseling_ticket,
                              get_counseling_tickets, get_crm_event,
                              get_crm_events, get_crm_tasks, get_donation,
                              get_donations, get_evangelism_strategies,
                              get_event_attendance, get_families, get_family,
                              get_family_members, get_glory_house,
                              get_glory_houses, get_member,
                              get_member_donations, get_member_timeline,
                              get_members, get_milestones,
                              get_pastoral_call_log, get_pastoral_call_logs,
                              get_pipeline_lead, get_pipeline_leads,
                              get_prayer_request, get_prayer_requests,
                              get_support_ticket, get_support_tickets,
                              get_talents, get_total_donations_amount,
                              get_user_notifications, get_volunteer_shift,
                              get_volunteer_shifts,
                              mark_all_notifications_read,
                              mark_notification_as_read, search_members,
                              update_communication_log, update_community_card,
                              update_consolidation_case,
                              update_counseling_ticket, update_crm_event,
                              update_crm_task, update_donation,
                              update_evangelism_strategy, update_family,
                              update_glory_house, update_member,
                              update_milestone, update_pipeline_lead,
                              update_prayer_request, update_support_ticket,
                              update_volunteer_shift)
# CRM Extended — roles, positions, ministries, funds, skills, automations, chat
from backend.crud.crm_extended import (  # noqa: F401; Positions; Member Positions; Event Assignments; Ministries; Member Ministries; CRM Automations; Role Definitions; Member Roles; Funds; Volunteer Skills; Chat Messages
    ChatMessageCreate, CrmAutomationCreate, CrmAutomationUpdate,
    EventAssignmentCreate, EventAssignmentUpdate, FundCreate, FundUpdate,
    MemberMinistryCreate, MemberMinistryUpdate, MemberPositionCreate,
    MemberPositionUpdate, MemberRoleCreate, MinistryCreate, MinistryUpdate,
    PositionCreate, PositionUpdate, RoleDefinitionCreate, RoleDefinitionUpdate,
    VolunteerSkillCreate, VolunteerSkillUpdate, create_chat_message,
    create_crm_automation, create_event_assignment, create_fund,
    create_member_ministry, create_member_position, create_member_role,
    create_ministry, create_position, create_role_definition,
    create_volunteer_skill, delete_chat_message, delete_crm_automation,
    delete_event_assignment, delete_fund, delete_member_ministry,
    delete_member_position, delete_member_role, delete_ministry,
    delete_position, delete_role_definition, delete_volunteer_skill,
    get_chat_message, get_chat_messages, get_crm_automation,
    get_crm_automations, get_event_assignment, get_event_assignments, get_fund,
    get_funds, get_member_ministries, get_member_ministry, get_member_position,
    get_member_positions, get_member_roles, get_ministries, get_ministry,
    get_position, get_positions, get_role_definition, get_role_definitions,
    get_volunteer_skill, get_volunteer_skills, update_crm_automation,
    update_event_assignment, update_fund, update_member_ministry,
    update_member_position, update_ministry, update_position,
    update_role_definition, update_volunteer_skill)
# Dashboard
from backend.crud.dashboard import get_dashboard_metrics  # noqa: F401
from backend.crud.dashboard import (get_pastor_radar, get_pilot_readiness,
                                    search_knowledge_base)
# Governance
from backend.crud.governance import create_automation_rule  # noqa: F401
from backend.crud.governance import (delete_automation_rule,
                                     get_automation_rule, get_automation_rules,
                                     record_automation_run,
                                     update_automation_rule)
# Identity & auth
from backend.crud.identity import award_badge  # noqa: F401
from backend.crud.identity import (create_refresh_token, create_reset_token,
                                   create_user, create_verification_token,
                                   delete_user, ensure_ui_preferences,
                                   get_ui_preferences, get_user,
                                   get_user_by_email, get_user_by_username,
                                   get_users, get_valid_refresh_token,
                                   grant_xp, revoke_refresh_token,
                                   update_ui_preferences, update_user,
                                   use_reset_token, use_verification_token)
# Ops — church locations, social channels, system variables
from backend.crud.ops import ChurchLocationCreate  # noqa: F401
from backend.crud.ops import (ChurchLocationUpdate, SocialChannelCreate,
                              SocialChannelUpdate, SystemVariableCreate,
                              SystemVariableUpdate, create_church_location,
                              create_social_channel, create_system_variable,
                              delete_church_location, delete_social_channel,
                              delete_system_variable, get_church_location,
                              get_church_locations, get_social_channel,
                              get_social_channels, get_system_variable,
                              get_system_variable_value, get_system_variables,
                              update_church_location, update_social_channel,
                              update_system_variable, upsert_system_variable)
# Projects
from backend.crud.projects import create_activity_log  # noqa: F401
from backend.crud.projects import (create_attachment, create_comment,
                                   create_default_phases, create_milestone,
                                   create_project, create_project_task,
                                   create_supply, delete_attachment,
                                   delete_comment, delete_milestone,
                                   delete_project, delete_project_task,
                                   delete_supply, get_attachment, get_comment,
                                   get_inbox_state, get_milestone,
                                   get_portfolio_summary, get_project,
                                   get_project_activities,
                                   get_project_comments,
                                   get_project_milestones, get_project_phases,
                                   get_project_task, get_project_tasks,
                                   get_project_whiteboard, get_project_wiki,
                                   get_projects, get_supply,
                                   get_task_attachments, get_task_supplies,
                                   get_workload_summary, set_project_phases,
                                   update_comment, update_inbox_state,
                                   update_milestone, update_project,
                                   update_project_task,
                                   update_project_whiteboard,
                                   update_project_wiki, update_supply)
