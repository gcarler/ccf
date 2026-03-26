-- 0. CONFIGURACIÓN INICIAL Y EXTENSIONES
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector"; -- Para Inteligencia Artificial (Embeddings)
CREATE EXTENSION IF NOT EXISTS "fuzzystrmatch"; -- Para limpieza de duplicados
CREATE EXTENSION IF NOT EXISTS "btree_gist"; -- Necesario para exclusión de rangos de tiempo

-- 1. ESQUEMA DE IDENTIDAD (Acceso y Seguridad)
CREATE SCHEMA IF NOT EXISTS identity;

CREATE TABLE identity.roles (
    role_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL, -- Admin, Pastor, Líder, Agente
    permissions JSONB -- Permisos granulares
);

CREATE TABLE identity.users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role_id INT REFERENCES identity.roles(role_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. ESQUEMA DE MEMBRESÍA Y TALENTO
CREATE SCHEMA IF NOT EXISTS membership;

CREATE TABLE membership.families (
    family_id SERIAL PRIMARY KEY,
    family_name VARCHAR(100) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE membership.ecclesiastical_offices (
    office_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL -- Apóstol, Profeta, Evangelista, Pastor, Maestro, Ministro, Servidor
);

CREATE TABLE membership.skills (
    skill_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL, -- 'Edición de Video', 'Canto', 'Moderación Online'
    category VARCHAR(50)
);

CREATE TYPE membership.gender AS ENUM ('M', 'F');
CREATE TYPE membership.member_status AS ENUM ('Activo', 'Inactivo', 'En Observación', 'Fallecido');

CREATE TABLE membership.persons (
    person_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    family_id INT REFERENCES membership.families(family_id) ON DELETE SET NULL,
    office_id INT REFERENCES membership.ecclesiastical_offices(office_id),
    mentor_id UUID REFERENCES membership.persons(person_id),
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    document_id VARCHAR(20) UNIQUE,
    gender membership.gender,
    birth_date DATE,
    email VARCHAR(150) UNIQUE,
    phone_mobile VARCHAR(20),
    status membership.member_status DEFAULT 'Activo',
    is_baptized BOOLEAN DEFAULT FALSE, -- Acceso rápido al estado de bautismo
    preferred_platform VARCHAR(50), -- Zoom, WhatsApp, Presencial
    location_coords POINT, -- Coordenadas para geointeligencia
    user_id UUID REFERENCES identity.users(user_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE membership.person_skills (
    person_id UUID REFERENCES membership.persons(person_id),
    skill_id INT REFERENCES membership.skills(skill_id),
    PRIMARY KEY (person_id, skill_id)
);

CREATE TABLE membership.ministries (
    ministry_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    leader_id UUID REFERENCES membership.persons(person_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE membership.person_ministry_assignments (
    assignment_id SERIAL PRIMARY KEY,
    person_id UUID REFERENCES membership.persons(person_id),
    ministry_id INT REFERENCES membership.ministries(ministry_id),
    position_title VARCHAR(100),
    is_head_of_ministry BOOLEAN DEFAULT FALSE,
    joined_at DATE DEFAULT CURRENT_DATE
);

-- 3. ESQUEMA CMS Y EDUCACIÓN
CREATE SCHEMA IF NOT EXISTS web_content;

CREATE TYPE web_content.post_type AS ENUM ('Testimonio', 'Predica', 'Curso', 'Noticia', 'Evento');
CREATE TYPE web_content.course_access_level AS ENUM ('Abierto', 'Membresia', 'Liderazgo');

CREATE TABLE web_content.categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE web_content.posts (
    post_id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    post_type web_content.post_type NOT NULL,
    category_id INT REFERENCES web_content.categories(category_id),
    author_id UUID REFERENCES membership.persons(person_id),
    featured_image TEXT,
    video_url TEXT,
    audio_url TEXT,
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP,
    meta_description VARCHAR(160),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE web_content.courses (
    course_id SERIAL PRIMARY KEY,
    post_id INT UNIQUE REFERENCES web_content.posts(post_id) ON DELETE CASCADE,
    access_level web_content.course_access_level NOT NULL DEFAULT 'Abierto',
    capacity INT, -- 0 para ilimitado
    meeting_link TEXT, -- Zoom/Meet
    is_active BOOLEAN DEFAULT TRUE
);

-- 4. ESQUEMA DE HITOS ESPIRITUALES
CREATE SCHEMA IF NOT EXISTS spiritual_life;

CREATE TYPE spiritual_life.milestone_type AS ENUM ('Decision_Fe', 'Bautismo_Aguas', 'Bautismo_Espiritu', 'Miembro_Oficial');

CREATE TABLE spiritual_life.milestones (
    milestone_id SERIAL PRIMARY KEY,
    person_id UUID REFERENCES membership.persons(person_id),
    type spiritual_life.milestone_type NOT NULL,
    event_date DATE NOT NULL,
    minister_id UUID REFERENCES membership.persons(person_id), -- Quién bautizó
    certificate_url TEXT, -- Link al acta digital
    witness_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. ESQUEMA DE DISCIPULADO
CREATE SCHEMA IF NOT EXISTS discipleship;

CREATE TABLE discipleship.levels (
    level_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- 'Nivel 1: Fundamentos', 'Nivel 2: Liderazgo'
    order_index INT UNIQUE
);

CREATE TABLE discipleship.student_progress (
    progress_id SERIAL PRIMARY KEY,
    person_id UUID REFERENCES membership.persons(person_id),
    level_id INT REFERENCES discipleship.levels(level_id),
    status VARCHAR(20) DEFAULT 'En Curso', -- 'Completado', 'Suspendido'
    mentor_id UUID REFERENCES membership.persons(person_id),
    completion_date DATE
);

-- 6. ESQUEMA CRM Y CONSEJERÍA
CREATE SCHEMA IF NOT EXISTS crm;

CREATE TYPE crm.interaction_type AS ENUM ('Llamada', 'Visita', 'Email', 'WhatsApp', 'Consejería', 'Otro');

CREATE TABLE crm.interactions (
    interaction_id SERIAL PRIMARY KEY,
    person_id UUID REFERENCES membership.persons(person_id),
    agent_id UUID REFERENCES membership.persons(person_id),
    interaction_type crm.interaction_type NOT NULL,
    notes TEXT,
    follow_up_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crm.counseling_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES membership.persons(person_id),
    pastor_id UUID REFERENCES membership.persons(person_id),
    intake_notes_json JSONB, -- Notas de la sesión
    confidentiality_level INT DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. ESQUEMA DE FINANZAS E IMPACTO
CREATE SCHEMA IF NOT EXISTS finances;

CREATE TABLE finances.funds (
    fund_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_public BOOLEAN DEFAULT TRUE,
    current_balance NUMERIC(15,2) DEFAULT 0
);

CREATE TABLE finances.donations (
    donation_id SERIAL PRIMARY KEY,
    person_id UUID REFERENCES membership.persons(person_id),
    fund_id INT REFERENCES finances.funds(fund_id),
    amount NUMERIC(15,2) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE finances.expenditures (
    expenditure_id SERIAL PRIMARY KEY,
    fund_id INT REFERENCES finances.funds(fund_id),
    amount NUMERIC(15,2) NOT NULL,
    category VARCHAR(100), -- 'Misiones', 'Ayuda Social'
    proof_url TEXT
);

CREATE TABLE finances.mission_impact (
    impact_id SERIAL PRIMARY KEY,
    expenditure_id INT REFERENCES finances.expenditures(expenditure_id),
    impact_metric VARCHAR(100), -- 'Biblias entregadas', 'Raciones de comida'
    quantity INT
);

-- 8. ESQUEMA DE ACTIVOS E INVENTARIO
CREATE SCHEMA IF NOT EXISTS assets;

CREATE TABLE assets.items (
    item_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    brand VARCHAR(100),
    serial_number VARCHAR(100) UNIQUE,
    purchase_price NUMERIC(15,2),
    current_status VARCHAR(50) DEFAULT 'Disponible'
);

CREATE TABLE assets.maintenance_logs (
    log_id SERIAL PRIMARY KEY,
    item_id UUID REFERENCES assets.items(item_id),
    service_date DATE NOT NULL,
    description TEXT
);

-- 9. ANALÍTICA DE CRECIMIENTO (VISTAS)
CREATE SCHEMA IF NOT EXISTS analytics;

-- Vista: Candidatos al Bautismo
CREATE OR REPLACE VIEW analytics.v_baptism_candidates AS
SELECT 
    p.person_id,
    p.first_name || ' ' || p.last_name as full_name,
    p.email,
    p.phone_mobile
FROM membership.persons p
JOIN discipleship.student_progress sp ON p.person_id = sp.person_id
JOIN discipleship.levels l ON sp.level_id = l.level_id
WHERE l.name ILIKE '%Fundamentos%' 
  AND sp.status = 'Completado'
  AND p.is_baptized = FALSE;

-- Vista Radar del Pastor (KPIs)
CREATE OR REPLACE VIEW analytics.v_pastor_radar AS
SELECT
    (SELECT COUNT(*) FROM membership.persons WHERE status = 'Activo') as membresia_viva,
    (SELECT COUNT(*) FROM spiritual_life.milestones WHERE type = 'Bautismo_Aguas' AND (event_date > CURRENT_DATE - INTERVAL '1 year')) as bautismos_este_año,
    (SELECT COUNT(*) FROM discipleship.student_progress WHERE status = 'En Curso') as estudiantes_activos,
    (SELECT COALESCE(SUM(amount), 0) FROM finances.donations WHERE transaction_date > CURRENT_DATE - INTERVAL '30 days') as recaudacion_mes;
