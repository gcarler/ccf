# ANÁLISIS DE MÓDULOS PENDIENTES DE ACTUALIZACIÓN
# ==============================================
# Fecha: 2026-05-28
# BD PostgreSQL tiene 177 tablas. 43 FKs ya migradas a UUID (personas.id).
# Las tablas marcadas abajo aún usan Integer FK a users.id en el modelo Python.

## MÓDULOS YA ACTUALIZADOS (UUID nativo) ✅
- Kernel (personas, persona_ministries, persona_church_roles, etc.)
- CRM Core 2.0 (crm_pipelines, crm_casos, crm_interacciones, crm_tareas)
- Academy 2.0 (academy_courses, academy_lessons, academy_enrollments, etc.)
- Agenda 2.0 (agenda_eventos, agenda_recursos, agenda_participantes, agenda_reserva_recursos)
- Proyectos (proyectos, equipo_proyecto, tareas_proyecto, documentos_proyecto)
- Evangelism (grupos_evangelismo, asistencias, sesiones_grupo, etc.)
- Cell Groups (cell_groups, cell_group_members, cell_group_sessions)

## MÓDULOS PENDIENTES (requieren nueva propuesta de BD)

### 1. IDENTITY / AUTH (models_identity.py) — CRÍTICO
Tablas: users, roles, badges, notifications, user_badges, user_permissions,
        user_reminders, user_ui_preferences, refresh_tokens, reset_tokens,
        verification_tokens, levels

### 2. ACADEMY COMPAT (models_academy.py) — CRÍTICO
Tablas: courses, lessons, enrollments, lesson_progress, course_attendance,
        course_prerequisites, formal_actas, forum_threads, forum_comments,
        resources, assessment_*, assignment_submissions, academy_activity_logs
Nota: Ya existe Academy 2.0 (models_academy_core.py) — este es el compat.

### 3. CRM COMPAT (models_crm.py) — ALTO
Tablas: conversations, chat_messages, agenda_events, event_assignments,
        event_attendances, crm_automations, prayer_requests, support_tickets,
        volunteer_skills, role_definitions, donation_categories, funds
Nota: Ya existe CRM Core 2.0 (models_crm_core.py) — este es el compat.

### 4. PROJECTS COMPAT (models_projects.py) — ALTO
Tablas: projects, project_tasks, project_activity_logs, project_inbox_state,
        project_attachments, project_comments, project_documents,
        project_milestones, project_phases, project_whiteboards, task_supplies
Nota: Ya existe Proyectos V2 (models_proyectos.py) — este es el compat.

### 5. CMS (models_cms.py) — MEDIO
Tablas: cms_pages, cms_menus, cms_publish_logs, cms_media_items, cms_sites,
        cms_themes, announcements, content_metrics, content_publications,
        media_assets, newsletter_subscriptions, testimonials, etc.

### 6. AGENTS (models_agents.py) — MEDIO
Tablas: agent_tasks, agent_insights, agent_journey, agent_permissions

### 7. GOVERNANCE (models_governance.py) — BAJO
Tablas: admin_audit_logs

### 8. KERNEL PLATFORM ROLES (models_kernel.py) — BAJO
Tablas: kernel_role_history, platform_role_definitions
