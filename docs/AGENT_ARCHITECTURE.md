# Arquitectura de Persona Central — Modelo Agente Industrial

## Visión

La plataforma CCF gira alrededor de **PERSONAS** (agentes). Una persona fluye por todos los módulos: iglesia, academia, evangelismo, proyectos, finanzas. Cada persona tiene:

- **Una identidad canónica** (quién es)
- **Múltiples roles contextuales** (qué es en cada contexto)
- **Actividades unificadas** (qué hace, dónde, cuándo)
- **Un estado de jornada** (dónde está en su caminar)

---

## 1. MODELO DE DATOS

### 1.1 Tabla Central: `agents` (Persona Canónica)

```sql
CREATE TABLE agents (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(20) UNIQUE NOT NULL,     -- "CCF-AGENT-00001"
    first_name      VARCHAR(100) NOT NULL,
    last_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(255) UNIQUE,
    phone           VARCHAR(50) UNIQUE,
    avatar_url      VARCHAR(500),
    
    -- Estado espiritual (máquina de estados formal)
    spiritual_stage VARCHAR(30) NOT NULL DEFAULT 'visitor',
    -- visitor → believer → disciple → servant → leader → pastor
    
    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Audit
    created_by      INT REFERENCES agents(id),
    updated_by      INT REFERENCES agents(id)
);

CREATE INDEX idx_agents_email ON agents(email) WHERE email IS NOT NULL;
CREATE INDEX idx_agents_phone ON agents(phone) WHERE phone IS NOT NULL;
CREATE INDEX idx_agents_spiritual_stage ON agents(spiritual_stage);
```

### 1.2 Tabla: `agent_auth` (Credenciales de Login)

```sql
CREATE TABLE agent_auth (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255),  -- NULL para OAuth-only
    provider        VARCHAR(30) DEFAULT 'local',  -- local, google, facebook
    provider_id     VARCHAR(255),
    is_email_verified BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ,
    UNIQUE(agent_id, provider)
);
```

### 1.3 Tabla: `agent_contact` (Contactos Versionados)

```sql
CREATE TABLE agent_contact (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    type            VARCHAR(20) NOT NULL,  -- email, phone, address, whatsapp
    value           VARCHAR(500) NOT NULL,
    is_primary      BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    created_by      INT REFERENCES agents(id)
);
```

### 1.4 Tabla: `agent_roles` (Roles Contextuales — TODOS unificados)

```sql
CREATE TABLE agent_roles (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    role_type       VARCHAR(30) NOT NULL,
    -- platform, church, ministry, event, project, evangelism, academy
    role_value      VARCHAR(50) NOT NULL,
    -- admin, pastor, docente, miembro, visitante, lider, MC, preacher, etc.
    context_id      INT,              -- FK contextual (event_id, project_id, etc.)
    context_type    VARCHAR(30),      -- event, project, glory_house, course
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,      -- NULL = rol activo
    is_primary      BOOLEAN DEFAULT FALSE,
    created_by      INT REFERENCES agents(id)
);

CREATE INDEX idx_agent_roles_lookup ON agent_roles(agent_id, role_type, role_value);
```

### 1.5 Tabla: `agent_activities` (Actividad Unificada)

```sql
CREATE TABLE agent_activities (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    activity_type   VARCHAR(40) NOT NULL,
    -- attendance, enrollment, donation, service, interaction, milestone
    
    source_type     VARCHAR(30) NOT NULL,
    -- crm_event, glory_house, course, donation_form, ministry, counseling
    
    source_id       INT,            -- ID del evento/sesión/curso/donación
    status          VARCHAR(30),    -- present, absent, active, completed, etc.
    notes           TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_activities_lookup ON agent_activities(agent_id, activity_type, occurred_at);
CREATE INDEX idx_agent_activities_source ON agent_activities(source_type, source_id);
```

### 1.6 Tabla: `agent_families` (Relaciones Familiares)

```sql
CREATE TABLE agent_families (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    related_agent_id INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    relationship    VARCHAR(30) NOT NULL,
    -- spouse, child, parent, sibling, guardian
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, related_agent_id, relationship)
);
```

### 1.7 Tabla: `agent_journey` (Transiciones de Estado Auditadas)

```sql
CREATE TABLE agent_journey (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    from_stage      VARCHAR(30),
    to_stage        VARCHAR(30) NOT NULL,
    reason          VARCHAR(100),
    triggered_by    VARCHAR(30),  -- manual, auto_rule, course_completed, event_attendance
    triggered_by_id INT,          -- ID de la persona que lo desencadenó
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agent_journey_agent ON agent_journey(agent_id, created_at DESC);
```

### 1.8 Tabla: `agent_permissions` (Permisos Derivados de Roles)

```sql
CREATE TABLE agent_permissions (
    id              SERIAL PRIMARY KEY,
    agent_id        INT NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    permission      VARCHAR(50) NOT NULL,
    -- system:config, crm:manage, academy:edit, evangelism:lead, etc.
    granted_via     VARCHAR(50),  -- role:admin, ministry:lider, etc.
    granted_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    UNIQUE(agent_id, permission)
);
```

---

## 2. MAPA DE MIGRACIÓN (Tablas existentes → Nuevo modelo)

| Tabla Existente | Campo Actual | Nuevo Campo | Estrategia |
|---|---|---|---|
| `users` | id, email, username, password | → `agent_auth` | Uno-a-uno con agents |
| `members` | id, user_id, first_name, last_name | → `agents` | Migrar a agents |
| `members.church_role` | texto libre | → `agent_roles` (role_type='church') | Migrar |
| `members.spiritual_status` | texto libre | → `agents.spiritual_stage` | Normalizar |
| `members.phone/email` | columnas | → `agent_contact` | Migrar |
| `consolidation_pipeline` | first_name, last_name, phone | → `agents` + vincular | Vincular o crear |
| `newsletter_subscriptions` | email | → `agent_contact` + `agents` | Resolver a agent |
| `prayer_requests` | requester_name | → `agents` | Resolver o crear |
| `donations` | person_id, member_id | → `agent_id` FK | Unificar a agent_id |
| `spiritual_milestones` | person_id | → `agent_id` FK | Unificar |
| `event_attendances` | member_id | → `agent_id` + `agent_activities` | Doble write → migrar |
| `glory_house_attendance` | member_id | → `agent_id` + `agent_activities` | Doble write → migrar |
| `course_attendance` | enrollment_id | → `agent_activities` | Nuevo modelo |
| `glory_houses` | leader_id, assistant_id | → `agent_roles` (role_type='evangelism') | Migrar |
| `event_assignments` | member_id, role | → `agent_roles` (role_type='event') | Migrar |
| `project_tasks` | assignee_id (users.id) | → `agent_roles` (role_type='project') | Migrar |
| `enrollments` | user_id | → `agent_roles` (role_type='academy') | Migrar |

---

## 3. BACKEND — API DESIGN

### 3.1 Servicio Central: `AgentService`

```python
# /root/ccf/backend/services/agent_service.py

class AgentService:
    """Servicio central de identidad y jornada de personas."""
    
    def resolve_agent(self, email: str = None, phone: str = None, user_id: int = None) -> Agent:
        """Resuelve una persona por cualquier identificador."""
    
    def create_agent(self, data: AgentCreate) -> Agent:
        """Crea una persona con credenciales, roles y contacto."""
    
    def merge_agents(self, primary_id: int, secondary_id: int) -> Agent:
        """Fusiona dos personas duplicadas (mantiene historial)."""
    
    def transition_stage(self, agent_id: int, to_stage: str, reason: str, triggered_by: int):
        """Transición de estado espiritual con auditoría."""
    
    def get_full_profile(self, agent_id: int) -> AgentProfile:
        """Perfil completo: identidad + roles + actividades + jornada."""
    
    def get_activity_timeline(self, agent_id: int, limit: int = 100) -> list[Activity]:
        """Timeline unificado de todas las actividades."""
    
    def derive_permissions(self, agent_id: int) -> list[str]:
        """Calcula permisos efectivos basados en roles contextuales."""
    
    def auto_link_user_member(self, email: str, user_id: int) -> Agent:
        """Auto-vincula User y Member por email coincidente."""
    
    def find_duplicates(self, similarity: float = 0.85) -> list[DuplicatePair]:
        """Detecta personas duplicadas por nombre/email/teléfono."""
```

### 3.2 Endpoints

```
# ── Agent Core ──
GET    /api/agents/{id}/profile          # Perfil completo
GET    /api/agents/{id}/timeline         # Actividad unificada
GET    /api/agents/{id}/roles            # Todos los roles
POST   /api/agents/{id}/roles            # Asignar rol
DELETE /api/agents/{id}/roles/{role_id}  # Remover rol
PUT    /api/agents/{id}/stage            # Transición de estado
GET    /api/agents/search?q=...          # Búsqueda fuzzy

# ── Agent Auth ──
POST   /api/agents/{id}/auth             # Crear credencial de login
POST   /api/agents/{id}/auth/verify      # Verificar email
POST   /api/auth/login                   # (existente, usa agent_auth)
POST   /api/auth/register                # → crea Agent + AgentAuth

# ── Agent Activities ──
GET    /api/agents/{id}/activities       # Todas las actividades
POST   /api/agents/{id}/activities       # Registrar actividad
GET    /api/agents/{id}/attendance       # Solo asistencias
POST   /api/agents/{id}/attendance       # Registrar asistencia (unificada)

# ── Agent Families ──
GET    /api/agents/{id}/families         # Relaciones familiares
POST   /api/agents/{id}/families         # Agregar relación

# ── Admin ──
GET    /api/admin/agents/duplicates      # Detectar duplicados
POST   /api/admin/agents/{id}/merge      # Fusionar dos personas
GET    /api/admin/agents/stage-transitions # Historial de transiciones

# ── Public (creación de agentes) ──
POST   /api/public/contact               # → crea Agent + actividad
POST   /api/public/newsletter            # → crea Agent + role 'subscriber'
POST   /api/public/register              # → crea Agent + AgentAuth
```

### 3.3 Guard de Permisos Actualizado

```python
# /root/ccf/backend/core/agent_permissions.py

def require_agent_permission(permission: str):
    """Guard que verifica permisos derivados de roles del agente."""
    def guard(current_agent: Agent = Depends(get_current_agent)):
        permissions = AgentService.derive_permissions(current_agent.id)
        if permission not in permissions:
            raise HTTPException(403, f"Permiso insuficiente: {permission}")
        return current_agent
    return guard
```

---

## 4. FRONTEND — Componentes React

### 4.1 Perfil Completo de Persona

```
/persons/{id}
├── Header (foto, nombre, estado espiritual, badges)
├── Tabs:
│   ├── General (datos de contacto, familia)
│   ├── Roles (tabla de todos los roles activos/históricos)
│   ├── Jornada (línea de tiempo de transiciones de estado)
│   ├── Actividades (timeline unificado de todas las actividades)
│   ├── Academia (cursos, progreso, certificados)
│   ├── Evangelismo (grupos, asistencias, sesiones)
│   ├── Finanzas (donaciones, compromisos)
│   └── Consejería (casos, tickets, interacciones pastorales)
```

### 4.2 Búsqueda y Resolución de Personas

```tsx
// /root/ccf/frontend/src/components/AgentSearch.tsx
// Input de búsqueda que resuelve personas por nombre, email, teléfono
// Sugiere fusiones si detecta duplicados
```

### 4.3 Asignación de Roles Contextuales

```tsx
// /root/ccf/frontend/src/components/AgentRoleManager.tsx
// Permite asignar/quitar roles en cualquier contexto:
// - Platform: admin, pastor, docente, coordinador
// - Church: visitante, miembro, servidor, líder
// - Ministry: alabanza, niños, jóvenes, etc.
// - Event: MC, predicador, ofrenda
// - Evangelism: líder, asistente, anfitrión
// - Project: asignado, observador
// - Academy: estudiante, docente, certificado
```

### 4.4 Timeline Unificado

```tsx
// /root/ccf/frontend/src/components/AgentTimeline.tsx
// Muestra TODAS las actividades en orden cronológico:
// 📅 Asistió a "Servicio Dominical" — 2026-05-25
// 📚 Se inscribió en "Fundamentos de Fe" — 2026-05-20
// 💰 Donó $50,000 — 2026-05-18
// 🏠 Registrado como asistente en "Faro Esperanza" — 2026-05-15
// 🎓 Completó curso "Bautismo" — 2026-05-10
// 🙏 Recibió consejería pastoral — 2026-05-08
// ⬆️ Transición: Visitante → Creyente — 2026-05-05
```

---

## 5. ESTRATEGIA DE MIGRACIÓN (Phased Rollout)

### Fase 1 — Creación de Infraestructura (No rompe nada)
1. Crear nuevas tablas (`agents`, `agent_auth`, `agent_roles`, `agent_activities`)
2. Crear `AgentService` en backend
3. Crear endpoint `GET /agents/{id}/profile`
4. Frontend: componente `AgentTimeline`

### Fase 2 — Dual Write (Escribir en ambos lados)
1. Modificar creación de Members/Users para también crear Agent
2. Modificar registro de asistencia para escribir en `agent_activities`
3. Modificar registro de roles para escribir en `agent_roles`
4. Migración retroactiva: crear Agents para todos los Members/Users existentes

### Fase 3 — Migración de Lectura (Cambiar queries al nuevo modelo)
1. `GET /crm/members/{id}` → usa `agents` como fuente
2. `GET /auth/me` → usa `agents` como fuente
3. Timeline unificado en producción
4. Detección de duplicados en producción

### Fase 4 — Deprecación (Eliminar lo viejo)
1. Eliminar escritura en tablas viejas
2. Migrar FKs: `donations.person_id` → `donations.agent_id`
3. Eliminar tablas huérfanas
4. Eliminar campos duplicados en `members` y `users`

---

## 6. BENEFICIOS DE ESTA ARQUITECTURA

| Problema Actual | Solución con Agentes |
|---|---|
| 2+ identidades separadas | **Una identidad canónica** con vistas especializadas |
| Roles en 7 tablas diferentes | **Una tabla `agent_roles`** con discriminador contextual |
| 3 tablas de asistencia | **Una tabla `agent_activities`** unificada |
| Pipeline lead sin FK | **Agent con role_type='pipeline'** |
| No hay perfil completo | **`GET /agents/{id}/profile`** con todo |
| Visitante no tiene cuenta | **Agent con spiritual_stage='visitor'** + opcional auth |
| No hay auditoría de transiciones | **`agent_journey`** registra cada cambio |
| Duplicados silenciosos | **`find_duplicates()`** con merge tool |
| Permisos hardcodeados | **`agent_permissions`** derivados de roles |

---

## 7. DIAGRAMA ARQUITECTÓNICO FINAL

```
┌──────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐│
│  │ AgentProfile │ │ AgentTimeline│ │ AgentSearch  │ │RoleManager   ││
│  │  (perfil     │ │ (actividad   │ │ (resolución  │ │(asignación   ││
│  │   completo)  │ │  unificada)  │ │  de personas)│ │  de roles)   ││
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘│
│         │                │                │                │         │
└─────────┼────────────────┼────────────────┼────────────────┼─────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                        AgentService                              │ │
│  │  resolve() create() merge() transition() get_profile()          │ │
│  │  get_timeline() derive_permissions() auto_link() find_dupes()   │ │
│  └──────────────────────────┬──────────────────────────────────────┘ │
│                             │                                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│
│  │ AuthGuard   │ │ RoleGuard   │ │ActivityAPI  │ │PermissionEngine ││
│  │(agent_auth) │ │(agent_roles)│ │(unified)    │ │(derived)        ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘│
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      DATABASE (PostgreSQL)                           │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                         AGENTS (core)                           │ │
│  │  agents, agent_auth, agent_contact, agent_roles,                │ │
│  │  agent_activities, agent_families, agent_journey,               │ │
│  │  agent_permissions                                             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐│
│  │ Modules     │ │ Modules     │ │ Modules     │ │ Migration       ││
│  │ (academy)   │ │ (evangelism)│ │ (projects)  │ │ (old tables →   ││
│  │ → agent_id  │ │ → agent_id  │ │ → agent_id  │ │  new agents)    ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

---

**¿Quieres que implemente esta arquitectura?** Recomendaría empezar por la **Fase 1** (crear las tablas y el servicio sin romper nada existente) e ir avanzando gradualmente.
