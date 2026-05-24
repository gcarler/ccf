-- ============================================================================
-- master_schema.sql
-- DDL completo para SQLite generado a partir de los modelos Python (models_*.py)
-- Proyecto: CCF (Church Management System)
-- Fecha: 2026-05-21
-- ============================================================================
-- NOTA: SQLite no soporta FOREIGN KEY por defecto. Se recomienda habilitar
--       PRAGMA foreign_keys = ON; al abrir la conexión.
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- 1. IDENTITY, GAMIFICATION & UI  (models_identity.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS roles (
    role_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name           VARCHAR(50) NOT NULL UNIQUE,
    permissions    TEXT
);

CREATE TABLE IF NOT EXISTS levels (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  VARCHAR(50) NOT NULL UNIQUE,
    min_xp INTEGER DEFAULT 0,
    icon_key VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    username          VARCHAR(50) NOT NULL UNIQUE,
    email             VARCHAR(100) NOT NULL UNIQUE,
    password_hash     TEXT NOT NULL,
    role_id           INTEGER REFERENCES roles(role_id),
    role              VARCHAR(20) DEFAULT 'estudiante',
    xp                INTEGER DEFAULT 0,
    current_level_id  INTEGER REFERENCES levels(id),
    is_active         INTEGER DEFAULT 1,
    is_email_verified INTEGER DEFAULT 0,
    created_at        DATETIME DEFAULT (datetime('now')),
    updated_at        DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_users_username ON users(username);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);
CREATE INDEX IF NOT EXISTS ix_users_xp ON users(xp);
CREATE INDEX IF NOT EXISTS ix_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_is_email_verified ON users(is_email_verified);
CREATE INDEX IF NOT EXISTS ix_users_created_at ON users(created_at);

CREATE TABLE IF NOT EXISTS badges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon_key    VARCHAR(50) NOT NULL,
    xp_reward   INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS user_badges (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER NOT NULL REFERENCES users(id),
    badge_id INTEGER NOT NULL REFERENCES badges(id),
    earned_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_user_badges_user_id ON user_badges(user_id);

CREATE TABLE IF NOT EXISTS user_ui_preferences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id),
    settings   TEXT DEFAULT '{}',
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    token      VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    revoked    INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token ON refresh_tokens(token);

CREATE TABLE IF NOT EXISTS notifications (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(200) NOT NULL,
    content    TEXT,
    is_read    INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications(created_at);

CREATE TABLE IF NOT EXISTS user_reminders (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    remind_at     DATETIME NOT NULL,
    priority      VARCHAR(20) DEFAULT 'normal',
    related_type  VARCHAR(50),
    related_id    INTEGER,
    is_dismissed  INTEGER DEFAULT 0,
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_user_reminders_user_id ON user_reminders(user_id);
CREATE INDEX IF NOT EXISTS ix_user_reminders_remind_at ON user_reminders(remind_at);
CREATE INDEX IF NOT EXISTS ix_user_reminders_related_type ON user_reminders(related_type);
CREATE INDEX IF NOT EXISTS ix_user_reminders_is_dismissed ON user_reminders(is_dismissed);
CREATE INDEX IF NOT EXISTS ix_user_reminders_created_at ON user_reminders(created_at);

-- ============================================================================
-- 2. GOVERNANCE & AUTOMATION  (models_governance.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_user_id INTEGER REFERENCES users(id),
    action        VARCHAR(120) NOT NULL,
    resource_type VARCHAR(120),
    resource_id   VARCHAR(120),
    ip_address    VARCHAR(45),
    severity      VARCHAR(20) DEFAULT 'info',
    metadata      TEXT DEFAULT '{}',
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action ON admin_audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_resource_type ON admin_audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at ON admin_audit_logs(created_at);

CREATE TABLE IF NOT EXISTS automation_rules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR(200) NOT NULL,
    trigger_type  VARCHAR(100) NOT NULL,
    action_type   VARCHAR(100),
    action_payload TEXT DEFAULT '{}',
    config_json   TEXT DEFAULT '{}',
    is_active     INTEGER DEFAULT 1,
    last_run      DATETIME,
    created_at    DATETIME DEFAULT (datetime('now')),
    updated_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_automation_rules_name ON automation_rules(name);
CREATE INDEX IF NOT EXISTS ix_automation_rules_trigger_type ON automation_rules(trigger_type);
CREATE INDEX IF NOT EXISTS ix_automation_rules_action_type ON automation_rules(action_type);
CREATE INDEX IF NOT EXISTS ix_automation_rules_is_active ON automation_rules(is_active);
CREATE INDEX IF NOT EXISTS ix_automation_rules_last_run ON automation_rules(last_run);
CREATE INDEX IF NOT EXISTS ix_automation_rules_created_at ON automation_rules(created_at);
CREATE INDEX IF NOT EXISTS ix_automation_rules_updated_at ON automation_rules(updated_at);

-- ============================================================================
-- 3. ASSETS & INVENTORY  (models_assets.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS inventory_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR(200) NOT NULL,
    category   VARCHAR(100) NOT NULL,
    stock      INTEGER DEFAULT 0,
    status     VARCHAR(20) DEFAULT 'ok',
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets_items (
    id             TEXT PRIMARY KEY,
    name           VARCHAR(200) NOT NULL,
    brand          VARCHAR(100),
    serial_number  VARCHAR(100) UNIQUE,
    purchase_price REAL,
    current_status VARCHAR(50) DEFAULT 'Disponible',
    category       VARCHAR(100) DEFAULT 'Mobiliario',
    created_at     DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id      TEXT REFERENCES assets_items(id),
    service_date DATETIME DEFAULT (datetime('now')),
    description  TEXT,
    cost         REAL DEFAULT 0.0
);

-- ============================================================================
-- 4. AGENTS  (models_agents.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_insights (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         VARCHAR(200) NOT NULL,
    insight_type  VARCHAR(50) NOT NULL,
    payload       TEXT NOT NULL,
    acknowledged  INTEGER DEFAULT 0,
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_agent_insights_insight_type ON agent_insights(insight_type);
CREATE INDEX IF NOT EXISTS ix_agent_insights_acknowledged ON agent_insights(acknowledged);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    status      VARCHAR(20) DEFAULT 'pending',
    priority    VARCHAR(20) DEFAULT 'medium',
    source      VARCHAR(100),
    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_agent_tasks_status ON agent_tasks(status);

-- ============================================================================
-- 5. ACADEMY & FORUM  (models_academy.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS courses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    code             VARCHAR(20) NOT NULL UNIQUE,
    title            VARCHAR(200) NOT NULL,
    description      TEXT,
    modality         VARCHAR(20) NOT NULL,
    is_published     INTEGER DEFAULT 1,
    is_self_paced    INTEGER DEFAULT 1,
    duration_hours   INTEGER DEFAULT 0,
    cohort_name      VARCHAR(100),
    certificate_type VARCHAR(50) DEFAULT 'Participación',
    xp_per_lesson    INTEGER DEFAULT 10,
    image_url        VARCHAR(500),
    instructor_name  VARCHAR(200),
    created_at       DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_courses_code ON courses(code);
CREATE INDEX IF NOT EXISTS ix_courses_title ON courses(title);
CREATE INDEX IF NOT EXISTS ix_courses_modality ON courses(modality);

CREATE TABLE IF NOT EXISTS course_prerequisites (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id              INTEGER NOT NULL REFERENCES courses(id),
    prerequisite_course_id INTEGER NOT NULL REFERENCES courses(id),
    UNIQUE(course_id, prerequisite_course_id)
);
CREATE INDEX IF NOT EXISTS ix_course_prerequisites_course_id ON course_prerequisites(course_id);
CREATE INDEX IF NOT EXISTS ix_course_prerequisites_prerequisite_course_id ON course_prerequisites(prerequisite_course_id);

CREATE TABLE IF NOT EXISTS lessons (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       INTEGER NOT NULL REFERENCES courses(id),
    title           VARCHAR(200) NOT NULL,
    content         TEXT NOT NULL,
    content_type    VARCHAR(50) DEFAULT 'video',
    media_url       VARCHAR(255),
    order_index     INTEGER DEFAULT 0,
    duration_minutes INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_lessons_course_id ON lessons(course_id);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id               INTEGER NOT NULL REFERENCES users(id),
    lesson_id             INTEGER NOT NULL REFERENCES lessons(id),
    progress_percent      NUMERIC(5,2) DEFAULT 0,
    last_position_seconds INTEGER DEFAULT 0,
    is_completed          INTEGER DEFAULT 0,
    updated_at            DATETIME DEFAULT (datetime('now')),
    UNIQUE(user_id, lesson_id)
);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_user_id ON lesson_progress(user_id);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_is_completed ON lesson_progress(is_completed);

CREATE TABLE IF NOT EXISTS assessments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id   INTEGER NOT NULL REFERENCES lessons(id),
    course_id   INTEGER REFERENCES courses(id),
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    min_score   NUMERIC(5,2) DEFAULT 70,
    weight      NUMERIC(5,2) DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS ix_assessments_lesson_id ON assessments(lesson_id);
CREATE INDEX IF NOT EXISTS ix_assessments_course_id ON assessments(course_id);

CREATE TABLE IF NOT EXISTS assessment_questions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    assessment_id  INTEGER NOT NULL REFERENCES assessments(id),
    question_text  TEXT NOT NULL,
    question_type  VARCHAR(20) DEFAULT 'multiple_choice',
    points         INTEGER DEFAULT 10
);
CREATE INDEX IF NOT EXISTS ix_assessment_questions_assessment_id ON assessment_questions(assessment_id);

CREATE TABLE IF NOT EXISTS assessment_options (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES assessment_questions(id),
    option_text TEXT NOT NULL,
    is_correct  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_assessment_options_question_id ON assessment_options(question_id);

CREATE TABLE IF NOT EXISTS assessment_attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
    assessment_id INTEGER NOT NULL REFERENCES assessments(id),
    score         NUMERIC(5,2) DEFAULT 0,
    passed        INTEGER DEFAULT 0,
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_assessment_attempts_enrollment_id ON assessment_attempts(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_assessment_attempts_passed ON assessment_attempts(passed);
CREATE INDEX IF NOT EXISTS ix_assessment_attempts_created_at ON assessment_attempts(created_at);

CREATE TABLE IF NOT EXISTS resources (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id),
    title         VARCHAR(200) NOT NULL,
    file_url      VARCHAR(500) NOT NULL,
    resource_type VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS assignment_submissions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id),
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id),
    file_url      VARCHAR(500) NOT NULL,
    comment       TEXT,
    grade         NUMERIC(5,2),
    teacher_feedback TEXT,
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_assignment_submissions_enrollment_id ON assignment_submissions(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_assignment_submissions_lesson_id ON assignment_submissions(lesson_id);

CREATE TABLE IF NOT EXISTS formal_actas (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id              INTEGER NOT NULL REFERENCES courses(id),
    closed_by_user_id      INTEGER NOT NULL REFERENCES users(id),
    status                 VARCHAR(20) DEFAULT 'closed',
    min_grade_required     NUMERIC(5,2) DEFAULT 70,
    min_attendance_required NUMERIC(5,2) DEFAULT 75,
    created_at             DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forum_threads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       VARCHAR(200) NOT NULL,
    category    VARCHAR(50) NOT NULL,
    author_id   INTEGER NOT NULL REFERENCES users(id),
    is_resolved INTEGER DEFAULT 0,
    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_forum_threads_title ON forum_threads(title);
CREATE INDEX IF NOT EXISTS ix_forum_threads_category ON forum_threads(category);

CREATE TABLE IF NOT EXISTS forum_comments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id  INTEGER NOT NULL REFERENCES forum_threads(id),
    author_id  INTEGER NOT NULL REFERENCES users(id),
    content    TEXT NOT NULL,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS families (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       VARCHAR(100) NOT NULL,
    address    TEXT,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS glory_houses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    code          VARCHAR(30) UNIQUE,
    name          VARCHAR(100) NOT NULL,
    zone          VARCHAR(100),
    address       VARCHAR(255),
    latitude      NUMERIC(10,8),
    longitude     NUMERIC(11,8),
    leader_name   VARCHAR(100),
    members_count INTEGER DEFAULT 0,
    capacity      INTEGER DEFAULT 15,
    day_of_week   VARCHAR(20),
    start_time    VARCHAR(50),
    end_time      VARCHAR(50),
    status        VARCHAR(20) DEFAULT 'Activo',
    leader_id     INTEGER REFERENCES members(id) ON DELETE SET NULL,
    assistant_id  INTEGER REFERENCES members(id) ON DELETE SET NULL,
    host_id       INTEGER REFERENCES members(id) ON DELETE SET NULL,
    created_at    DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_glory_houses_code ON glory_houses(code);
CREATE INDEX IF NOT EXISTS ix_glory_houses_status ON glory_houses(status);

CREATE TABLE IF NOT EXISTS glory_house_members (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    glory_house_id INTEGER NOT NULL REFERENCES glory_houses(id) ON DELETE CASCADE,
    member_id      INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    role           VARCHAR(50) DEFAULT 'asistente'
);
CREATE INDEX IF NOT EXISTS ix_glory_house_members_glory_house_id ON glory_house_members(glory_house_id);
CREATE INDEX IF NOT EXISTS ix_glory_house_members_member_id ON glory_house_members(member_id);

CREATE TABLE IF NOT EXISTS faro_seasons (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         VARCHAR(100) NOT NULL,
    start_date   DATE NOT NULL,
    end_date     DATE NOT NULL,
    periodicity  VARCHAR(20) NOT NULL DEFAULT 'SEMANAL',
    status       VARCHAR(20) DEFAULT 'Activa',
    created_at   DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_faro_seasons_status ON faro_seasons(status);

CREATE TABLE IF NOT EXISTS glory_house_sessions (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    glory_house_id        INTEGER NOT NULL REFERENCES glory_houses(id) ON DELETE CASCADE,
    season_id             INTEGER NOT NULL REFERENCES faro_seasons(id) ON DELETE CASCADE,
    session_date          DATE NOT NULL,
    report_deadline       DATETIME,
    status                VARCHAR(20) DEFAULT 'Realizada',
    topic                 VARCHAR(255),
    offering_amount       NUMERIC(12,2),
    report_notes          TEXT,
    novelty_type          VARCHAR(50),
    novelty_detail        TEXT,
    cancellation_reason   TEXT,
    reported_by_member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    reported_at           DATETIME,
    created_at            DATETIME DEFAULT (datetime('now')),
    UNIQUE(glory_house_id, season_id, session_date)
);
CREATE INDEX IF NOT EXISTS ix_glory_house_sessions_glory_house_id ON glory_house_sessions(glory_house_id);
CREATE INDEX IF NOT EXISTS ix_glory_house_sessions_season_id ON glory_house_sessions(season_id);
CREATE INDEX IF NOT EXISTS ix_glory_house_sessions_session_date ON glory_house_sessions(session_date);
CREATE INDEX IF NOT EXISTS ix_glory_house_sessions_reported_by_member_id ON glory_house_sessions(reported_by_member_id);

CREATE TABLE IF NOT EXISTS glory_house_attendance (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id            INTEGER NOT NULL REFERENCES glory_house_sessions(id) ON DELETE CASCADE,
    member_id             INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    attended              INTEGER DEFAULT 1,
    absence_reason        VARCHAR(50),
    absence_reason_detail TEXT,
    scanned_at            DATETIME DEFAULT (datetime('now')),
    UNIQUE(session_id, member_id)
);
CREATE INDEX IF NOT EXISTS ix_glory_house_attendance_session_id ON glory_house_attendance(session_id);
CREATE INDEX IF NOT EXISTS ix_glory_house_attendance_member_id ON glory_house_attendance(member_id);
CREATE INDEX IF NOT EXISTS ix_glory_house_attendance_absence_reason ON glory_house_attendance(absence_reason);
CREATE INDEX IF NOT EXISTS ix_glory_house_attendance_scanned_at ON glory_house_attendance(scanned_at);

CREATE TABLE IF NOT EXISTS enrollments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    course_id           INTEGER NOT NULL REFERENCES courses(id),
    status              VARCHAR(20) DEFAULT 'active',
    progress_percent    NUMERIC(5,2) DEFAULT 0,
    lessons_completed   TEXT DEFAULT '[]',
    approved            INTEGER DEFAULT 0,
    certificate_issued  INTEGER DEFAULT 0,
    certificate_code    VARCHAR(64),
    access_window_end   DATETIME,
    created_at          DATETIME DEFAULT (datetime('now')),
    UNIQUE(user_id, course_id)
);
CREATE INDEX IF NOT EXISTS ix_enrollments_user_id ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS ix_enrollments_course_id ON enrollments(course_id);

CREATE TABLE IF NOT EXISTS academy_activity_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type VARCHAR(50) NOT NULL,
    course_id  INTEGER REFERENCES courses(id),
    user_id    INTEGER REFERENCES users(id),
    modality   VARCHAR(20),
    value      NUMERIC(10,2) DEFAULT 1.0,
    created_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_academy_activity_logs_event_type ON academy_activity_logs(event_type);
CREATE INDEX IF NOT EXISTS ix_academy_activity_logs_created_at ON academy_activity_logs(created_at);

CREATE TABLE IF NOT EXISTS course_attendance (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    session_date  DATETIME DEFAULT (datetime('now')),
    status        VARCHAR(20) DEFAULT 'present',
    recorded_by_id INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_course_attendance_enrollment_id ON course_attendance(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_course_attendance_session_date ON course_attendance(session_date);

CREATE TABLE IF NOT EXISTS certificates (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id    INTEGER NOT NULL REFERENCES enrollments(id),
    certificate_code VARCHAR(64) NOT NULL UNIQUE,
    issued_at        DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_certificates_enrollment_id ON certificates(enrollment_id);
CREATE INDEX IF NOT EXISTS ix_certificates_certificate_code ON certificates(certificate_code);

-- ============================================================================
-- 6. CRM & CHAT  (models_crm.py)
-- ============================================================================

CREATE TABLE IF NOT EXISTS chat_messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id  INTEGER NOT NULL REFERENCES users(id),
    room_id    VARCHAR(100),
    content    TEXT NOT NULL,
    created_at DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_sender_id ON chat_messages(sender_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_room_id ON chat_messages(room_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages(created_at);

CREATE TABLE IF NOT EXISTS consolidation_pipeline (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name         VARCHAR(100) NOT NULL,
    last_name          VARCHAR(100) NOT NULL,
    phone              VARCHAR(20) NOT NULL,
    source             VARCHAR(100),
    stage              VARCHAR(20) DEFAULT 'new',
    notes              TEXT,
    assigned_pastor_id INTEGER REFERENCES users(id),
    created_at         DATETIME DEFAULT (datetime('now')),
    updated_at         DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_consolidation_pipeline_first_name ON consolidation_pipeline(first_name);
CREATE INDEX IF NOT EXISTS ix_consolidation_pipeline_last_name ON consolidation_pipeline(last_name);
CREATE INDEX IF NOT EXISTS ix_consolidation_pipeline_stage ON consolidation_pipeline(stage);

CREATE TABLE IF NOT EXISTS agenda_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               VARCHAR(200) NOT NULL,
    description         TEXT,
    start_at            DATETIME NOT NULL,
    end_at              DATETIME,
    location            VARCHAR(200),
    is_all_day          INTEGER DEFAULT 1,
    created_by_user_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          DATETIME DEFAULT (datetime('now')),
    updated_at          DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_agenda_events_title ON agenda_events(title);
CREATE INDEX IF NOT EXISTS ix_agenda_events_start_at ON agenda_events(start_at);
CREATE INDEX IF NOT EXISTS ix_agenda_events_end_at ON agenda_events(end_at);
CREATE INDEX IF NOT EXISTS ix_agenda_events_is_all_day ON agenda_events(is_all_day);
CREATE INDEX IF NOT EXISTS ix_agenda_events_created_by_user_id ON agenda_events(created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_agenda_events_created_at ON agenda_events(created_at);

CREATE TABLE IF NOT EXISTS crm_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                VARCHAR(200) NOT NULL,
    description         TEXT,
    event_date          DATETIME,
    event_type          VARCHAR(20) DEFAULT 'PERMANENT',
    start_time          VARCHAR(50),
    end_time            VARCHAR(50),
    day_of_week         INTEGER,
    month_day           VARCHAR(10),
    location            VARCHAR(200),
    status              VARCHAR(20) DEFAULT 'SCHEDULED',
    cancellation_reason TEXT,
    target_audience     VARCHAR(50) DEFAULT 'ALL',
    target_role_id      INTEGER REFERENCES role_definitions(id),
    target_role_ids     TEXT,
    target_member_ids   TEXT,
    fixed_date          DATETIME,
    created_at          DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_crm_events_name ON crm_events(name);
CREATE INDEX IF NOT EXISTS ix_crm_events_event_date ON crm_events(event_date);
CREATE INDEX IF NOT EXISTS ix_crm_events_event_type ON crm_events(event_type);
CREATE INDEX IF NOT EXISTS ix_crm_events_status ON crm_events(status);
CREATE INDEX IF NOT EXISTS ix_crm_events_created_at ON crm_events(created_at);

CREATE TABLE IF NOT EXISTS event_assignments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id     INTEGER NOT NULL REFERENCES crm_events(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    member_id    INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    role         VARCHAR(50) NOT NULL,
    created_at   DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_event_assignments_event_id ON event_assignments(event_id);
CREATE INDEX IF NOT EXISTS ix_event_assignments_session_date ON event_assignments(session_date);
CREATE INDEX IF NOT EXISTS ix_event_assignments_member_id ON event_assignments(member_id);
CREATE INDEX IF NOT EXISTS ix_event_assignments_role ON event_assignments(role);

CREATE TABLE IF NOT EXISTS event_attendances (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id     INTEGER NOT NULL REFERENCES crm_events(id) ON DELETE CASCADE,
    session_date DATE NOT NULL DEFAULT (date('now')),
    member_id    INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    status       VARCHAR(30) DEFAULT 'present',
    role_at_event VARCHAR(30) DEFAULT 'attendee',
    source       VARCHAR(30) DEFAULT 'manual',
    check_in_at  DATETIME,
    check_out_at DATETIME,
    notes        TEXT,
    scanned_at   DATETIME DEFAULT (datetime('now')),
    attended     INTEGER DEFAULT 1,
    UNIQUE(event_id, session_date, member_id)
);
CREATE INDEX IF NOT EXISTS ix_event_attendances_event_id ON event_attendances(event_id);
CREATE INDEX IF NOT EXISTS ix_event_attendances_session_date ON event_attendances(session_date);
CREATE INDEX IF NOT EXISTS ix_event_attendances_member_id ON event_attendances(member_id);
CREATE INDEX IF NOT EXISTS ix_event_attendances_status ON event_attendances(status);
CREATE INDEX IF NOT EXISTS ix_event_attendances_role_at_event ON event_attendances(role_at_event);
CREATE INDEX IF NOT EXISTS ix_event_attendances_source ON event_attendances(source);
CREATE INDEX IF NOT EXISTS ix_event_attendances_check_in_at ON event_attendances(check_in_at);
CREATE INDEX IF NOT EXISTS ix_event_attendances_check_out_at ON event_attendances(check_out_at);
CREATE INDEX IF NOT EXISTS ix_event_attendances_scanned_at ON event_attendances(scanned_at);

CREATE TABLE IF NOT EXISTS counseling_tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       INTEGER NOT NULL REFERENCES members(id),
    pastor_id       INTEGER REFERENCES users(id),
    subject         VARCHAR(200) NOT NULL,
    notes           TEXT,
    status          VARCHAR(50) DEFAULT 'open',
    priority_level  VARCHAR(20) DEFAULT 'NORMAL',
    sentiment_score REAL,
    sentiment_label VARCHAR(20),
    created_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_counseling_tickets_member_id ON counseling_tickets(member_id);
CREATE INDEX IF NOT EXISTS ix_counseling_tickets_pastor_id ON counseling_tickets(pastor_id);
CREATE INDEX IF NOT EXISTS ix_counseling_tickets_status ON counseling_tickets(status);
CREATE INDEX IF NOT EXISTS ix_counseling_tickets_priority_level ON counseling_tickets(priority_level);
CREATE INDEX IF NOT EXISTS ix_counseling_tickets_created_at ON counseling_tickets(created_at);

CREATE TABLE IF NOT EXISTS prayer_requests (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_name  VARCHAR(200) NOT NULL,
    request_text    TEXT NOT NULL,
    category        VARCHAR(50) DEFAULT 'General',
    is_public       INTEGER DEFAULT 0,
    source          VARCHAR(50) DEFAULT 'crm',
    status          VARCHAR(50) DEFAULT 'pending',
    created_at      DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_prayer_requests_requester_name ON prayer_requests(requester_name);
CREATE INDEX IF NOT EXISTS ix_prayer_requests_is_public ON prayer_requests(is_public);
CREATE INDEX IF NOT EXISTS ix_prayer_requests_source ON prayer_requests(source);
CREATE INDEX IF NOT EXISTS ix_prayer_requests_status ON prayer_requests(status);
CREATE INDEX IF NOT EXISTS ix_prayer_requests_created_at ON prayer_requests(created_at);

CREATE TABLE IF NOT EXISTS ministries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    leader_id   INTEGER REFERENCES members(id),
    created_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_ministries_name ON ministries(name);

CREATE TABLE IF NOT EXISTS members (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    family_id        INTEGER REFERENCES families(id) ON DELETE SET NULL,
    first_name       VARCHAR(100) NOT NULL,
    last_name        VARCHAR(100) NOT NULL,
    email            VARCHAR(100),
    phone            VARCHAR(20),
    church_role      VARCHAR(50) DEFAULT 'Miembro',
    is_baptized      INTEGER DEFAULT 0,
    spiritual_status VARCHAR(50) DEFAULT 'Nuevo',
    talents          TEXT,
    spiritual_gifts  TEXT,
    pastoral_notes   TEXT,
    created_at       DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_members_user_id ON members(user_id);
CREATE INDEX IF NOT EXISTS ix_members_family_id ON members(family_id);
CREATE INDEX IF NOT EXISTS ix_members_first_name ON members(first_name);
CREATE INDEX IF NOT EXISTS ix_members_last_name ON members(last_name);
CREATE INDEX IF NOT EXISTS ix_members_email ON members(email);
CREATE INDEX IF NOT EXISTS ix_members_phone ON members(phone);
CREATE INDEX IF NOT EXISTS ix_members_church_role ON members(church_role);
CREATE INDEX IF NOT EXISTS ix_members_is_baptized ON members(is_baptized);
CREATE INDEX IF NOT EXISTS ix_members_spiritual_status ON members(spiritual_status);
CREATE INDEX IF NOT EXISTS ix_members_created_at ON members(created_at);

CREATE TABLE IF NOT EXISTS positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category    VARCHAR(50),
    is_active   INTEGER DEFAULT 1,
    created_at  DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_positions_name ON positions(name);
CREATE INDEX IF NOT EXISTS ix_positions_category ON positions(category);
CREATE INDEX IF NOT EXISTS ix_positions_is_active ON positions(is_active);
CREATE INDEX IF NOT EXISTS ix_positions_created_at ON positions(created_at);

CREATE TABLE IF NOT EXISTS member_positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id   INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    position_id INTEGER NOT NULL REFERENCES positions(id) ON DELETE CASCADE,
    start_date  DATETIME,
    end_date    DATETIME,
    is_active   INTEGER DEFAULT 1,
    notes       TEXT,
    created_at  DATETIME DEFAULT (datetime('now')),
    UNIQUE(member_id, position_id, start_date)
);
CREATE INDEX IF NOT EXISTS ix_member_positions_member_id ON member_positions(member_id);
CREATE INDEX IF NOT EXISTS ix_member_positions_position_id ON member_positions(position_id);
CREATE INDEX IF NOT EXISTS ix_member_positions_start_date ON member_positions(start_date);
CREATE INDEX IF NOT EXISTS ix_member_positions_end_date ON member_positions(end_date);
CREATE INDEX IF NOT EXISTS ix_member_positions_is_active ON member_positions(is_active);
CREATE INDEX IF NOT EXISTS ix_member_positions_created_at ON member_positions(created_at);

CREATE TABLE IF NOT EXISTS consolidation_cases (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id          INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    stage              VARCHAR(20) DEFAULT 'new',
    status             VARCHAR(20) DEFAULT 'active',
    source             VARCHAR(100),
    last_contact_at    DATETIME,
    next_contact_at    DATETIME,
    assigned_pastor_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    assigned_leader_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
    notes              TEXT,
    created_at         DATETIME DEFAULT (datetime('now')),
    updated_at         DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_member_id ON consolidation_cases(member_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_stage ON consolidation_cases(stage);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_status ON consolidation_cases(status);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_last_contact_at ON consolidation_cases(last_contact_at);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_next_contact_at ON consolidation_cases(next_contact_at);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_assigned_pastor_id ON consolidation_cases(assigned_pastor_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_assigned_leader_id ON consolidation_cases(assigned_leader_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_created_at ON consolidation_cases(created_at);
CREATE INDEX IF NOT EXISTS ix_consolidation_cases_updated_at ON consolidation_cases(updated_at);

CREATE TABLE IF NOT EXISTS consolidation_assignments (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id               INTEGER NOT NULL REFERENCES consolidation_cases(id) ON DELETE CASCADE,
    assigned_by_member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    assigned_to_member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
    reason                TEXT,
    priority              VARCHAR(20) DEFAULT 'normal',
    start_date            DATETIME DEFAULT (datetime('now')),
    end_date              DATETIME,
    status                VARCHAR(20) DEFAULT 'active',
    created_at            DATETIME DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_consolidation_assignments_case_id ON consolidation_assignments(case_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_assignments_assigned_by_member_id ON consolidation_assignments(assigned_by_member_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_assignments_assigned_to_member_id ON consolidation_assignments(assigned_to_member_id);
CREATE INDEX IF NOT EXISTS ix_consolidation_assignments_priority ON consolidation_assignments(priority);
CREATE INDEX IF NOT EXISTS ix
