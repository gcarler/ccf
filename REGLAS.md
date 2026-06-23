# Manual de Estándares de Desarrollo y Arquitectura - Plataforma CCF

**Versión:** 2.1 (Enterprise-Grade - Anti-Data-Loss Enforced)
**Autor:** Arquitectura de Software y DBA Principal
**Audiencia:** Desarrolladores Backend, Frontend, DBAs y Agentes de IA

---

## 🧭 1. Introducción y Axiomas Fundamentales

La plataforma de la Comunidad Cristiana El Faro (CCF) no es un software tradicional de gestión de iglesias; es un ecosistema multiagente distribuido que automatiza y mide el crecimiento eclesiástico, académico, de proyectos y de consolidación pastoral en torno a un único núcleo.

Cualquier línea de código escrita para esta plataforma debe respetar de manera inquebrantable estos tres axiomas de diseño:

### Axioma 1: El Kernel Centrado en la Persona (Single Source of Truth)

**La Regla:** No se crean tablas paralelas que representen seres humanos bajo otros nombres (como "Estudiantes", "Voluntarios", "Donantes" o "Líderes"). Todo apunta al UUID central de la tabla `personas`.

**Justificación:** Una persona es una sola entidad biológica en todo el sistema. Su ficha demográfica vive en el Kernel. Si es un estudiante, un caso en el CRM, o un líder de célula, estos roles son satélites que se anexan a su ID de persona.

**En código:**
```python
# CORRECTO: FK a personas.id
persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))

# INCORRECTO: FK a users.id para representar una persona
user_id = Column(Integer, ForeignKey("users.id"))
```

### Axioma 2: Identidad Tridimensional y Contextual

El perfil de la persona se compone de tres dimensiones independientes que coexisten simultáneamente:

| Dimensión | Tabla | Ejemplos |
|---|---|---|
| **A: Ministerios/Oficios** | `persona_ministries` | Pastor, Maestro, Evangelista |
| **B: Roles de Iglesia/Crecimiento** | `persona_church_roles` / `persona_role_assignments` | Líder, Servidor, Miembro, Visitante |
| **C: Roles de Plataforma/Permisos** | `auth_roles` / `auth_user_module_roles` | ADMINISTRADOR, GESTOR, EDITOR, LECTOR |

**La Regla:** Una persona puede tener simultáneamente rol A="Maestro", rol B="Líder de Célula", y rol C="EDITOR". Ninguna dimensión excluye a las otras.

### Axioma 3: Aislamiento Territorial Multi-Tenant (`sede_id`)

**La Regla:** Ninguna transacción, consulta (SELECT), reporte o acción puede cruzar fronteras entre diferentes campus/sedes de la iglesia.

**Justificación:** Los datos de la Sede Norte están aislados de la Sede Sur. Toda consulta de lectura del backend debe filtrar de forma obligatoria por `sede_id`, el cual se extrae estrictamente del token de sesión JWT del usuario autenticado.

```python
# CORRECTO: filtrar por sede_id del usuario autenticado
sede_id = get_user_sede_id(db, current_user.id)
personas = db.query(Persona).filter(Persona.sede_id == sede_id).all()

# INCORRECTO: endpoint sin filtro sede_id — ¡fuga de datos!
personas = db.query(Persona).all()
```

---

## 💾 2. Estándares de Base de Datos (PostgreSQL)

### A. Paradigma de Identificadores UUID Absolutos

**Obligatorio:** Se prohíbe el uso de claves primarias autoincrementales (Integer serial) en cualquier tabla relacional, catálogo o tabla transaccional expuesta a las APIs. Todo debe usar identificadores únicos de 128 bits:

```python
id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

**Justificación:** Evita la colisión de llaves primarias en migraciones e integraciones distribuidas, y previene ataques IDOR (adivinación de recursos en URLs).

**Excepciones permitidas:**
- Tablas de catálogo interno (ej: `sedes`, `evangelism_strategies`)
- Tablas de configuración (`badges`, `levels`)
- Tablas con < 100 registros esperados

**Regla práctica:** Si la tabla tiene FK a `personas.id`, su PK DEBE ser UUID. Si es un catálogo maestro, puede usar SERIAL.

### B. Normalización y Cero Redundancia

No se permiten columnas duplicadas. Si un dato (como `church_role`) vive en una tabla relacional normalizada, no debe existir como columna física en la tabla `personas`. El backend o las vistas materializadas deben resolver los datos haciendo JOINS.

```python
# INCORRECTO: church_role como columna en Persona
class Persona(Base):
    church_role = Column(String(50))  # ❌ Redundante

# CORRECTO: church_role en tabla relacional
class PersonaRoleAssignment(Base):
    persona_id = Column(UUID, ForeignKey("personas.id"))
    role_name = Column(String(50))  # ✅ Normalizado
```

### C. Borrados Lógicos (Soft Deletes)

Está estrictamente prohibido ejecutar la instrucción física `DELETE` sobre el Kernel de personas o tablas transaccionales de alta relevancia.

Las entidades deben incorporar un campo `deleted_at` (de tipo `TIMESTAMP WITH TIME ZONE`) o una columna de estado de actividad (`estado_vital = 'INACTIVO'`).

```python
# CORRECTO: Soft delete
persona.estado_vital = "INACTIVO"
db.commit()

# CORRECTO: Soft delete con timestamp
caso.deleted_at = datetime.utcnow()
db.commit()

# INCORRECTO: destrucción irreversible
db.delete(persona)
```

### D. Control del Tiempo (Huso Horario Estricto)

Todos los campos de fecha y hora que requieran persistir una marca temporal deben usar obligatoriamente el tipo de dato `TIMESTAMP WITH TIME ZONE` (en SQLAlchemy: `DateTime(timezone=True)`). El servidor siempre almacena en formato UTC, y el frontend se encarga de formatear la hora según el huso horario local de la sede.

```python
# CORRECTO
created_at = Column(DateTime(timezone=True), server_default=func.now())

# INCORRECTO
created_at = Column(DateTime)
```

### E. Restricciones de Exclusión (Race Conditions)

Para evitar colisiones físicas en reservas de salones o vehículos en la agenda, se debe aplicar a nivel de motor de base de datos la restricción de exclusión mediante índices GIST:

```sql
ALTER TABLE agenda_reserva_recursos ADD CONSTRAINT sin_colisiones_fisicas 
EXCLUDE USING gist (recurso_id WITH =, tsrange(bloqueo_inicio, bloqueo_fin) WITH &&);
```

### F. Protocolo de Migración Segura de Tipos de Datos (Anti-Data-Loss)

Al realizar migraciones estructurales de tipos de datos en claves primarias (PK) y foráneas (FK) (por ejemplo, de Integer a UUID), se corre el riesgo latente de romper la integridad referencial histórica si se eliminan columnas de manera prematura.

**🚨 El Antipatrón Catastrófico:** Si un desarrollador elimina la clave primaria entera de la tabla padre para crear la nueva columna UUID, rompe inmediatamente la posibilidad de hacer un JOIN con las tablas hijas para mapear sus registros. Aunque exista una tabla de backup, esta solo tendrá los enteros antiguos pero no los nuevos UUIDs, dejando huérfanas todas las relaciones históricas en cascada.

**🛠️ Receta de Migración Segura en 6 Pasos (SQL de Obligatorio Cumplimiento)**

Para migrar de manera incondicional una PK y sus FKs asociadas (Ej: sedes.id de Integer a UUID afectando a la tabla hija grupos_evangelismo):

```sql
-- =====================================================================
-- PASO 1: ADICIÓN DE LA NUEVA CLAVE TEMPORAL EN PADRE
-- =====================================================================
ALTER TABLE sedes ADD COLUMN uuid_id UUID DEFAULT gen_random_uuid();
UPDATE sedes SET uuid_id = gen_random_uuid() WHERE uuid_id IS NULL;

-- =====================================================================
-- PASO 2: ADICIÓN DE LA COLUMNA TEMPORAL EN LAS TABLAS HIJAS
-- =====================================================================
ALTER TABLE grupos_evangelismo ADD COLUMN sede_uuid UUID;

-- =====================================================================
-- PASO 3: POBLACIÓN DE DATOS CRUZADA (EL MAPEO MOLECULAR)
-- =====================================================================
UPDATE grupos_evangelismo 
SET sede_uuid = sedes.uuid_id 
FROM sedes 
WHERE grupos_evangelismo.sede_id = sedes.id;

-- =====================================================================
-- PASO 4: VALIDACIÓN DE DATOS E INTEGRIDAD
-- =====================================================================
ALTER TABLE grupos_evangelismo ALTER COLUMN sede_uuid SET NOT NULL;

-- =====================================================================
-- PASO 5: REMOCIÓN DE RESTRICCIONES Y COLUMNAS ANTIGUAS
-- =====================================================================
ALTER TABLE grupos_evangelismo DROP CONSTRAINT IF EXISTS fk_grupos_sede_id;
ALTER TABLE sedes DROP CONSTRAINT IF EXISTS sedes_pkey CASCADE;
ALTER TABLE grupos_evangelismo DROP COLUMN sede_id;
ALTER TABLE sedes DROP COLUMN id;

-- =====================================================================
-- PASO 6: RENOMBRADO Y ESTABLECIMIENTO DE LAS NUEVAS CLAVES DEFINITIVAS
-- =====================================================================
ALTER TABLE sedes RENAME COLUMN uuid_id TO id;
ALTER TABLE sedes ADD CONSTRAINT sedes_pkey PRIMARY KEY (id);

ALTER TABLE grupos_evangelismo RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE grupos_evangelismo ADD CONSTRAINT fk_grupos_sede_id 
    FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;
```

**⚠️ NUNCA ejecutes el Paso 5 sin antes completar y verificar el Paso 3. El Paso 3 es la barrera que evita la pérdida masiva de datos históricos.**

---

## ⚡ 3. Estándares del Backend (FastAPI + SQLAlchemy)

### A. Tipado Estricto de Parámetros

Todos los parámetros de CRUD, esquemas de Pydantic y firmas de métodos de APIs que manejen referencias a sedes, personas o recursos deben estar tipados de manera estricta como UUID (o mapeados mediante librerías de validación). No se permite el tipado genérico como int o str libre.

```python
# CORRECTO
persona_id: str  # UUID como string en Pydantic
sede_id: int     # sede_id para catálogos puede ser int

# INCORRECTO
persona_id: int
```

### B. Inyección de Contexto en Endpoints

El backend no debe confiar a ciegas en los datos de sede o creadores que envía el frontend. El `sede_id` y el `user_id` de la persona que opera la petición deben inyectarse en el backend a partir de la decodificación segura del token JWT de la sesión.

```python
# CORRECTO: extraer sede_id del JWT
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.headers["Authorization"].split(" ")[1]
    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    return user

# INCORRECTO: aceptar sede_id del body
class CrearCasoRequest(BaseModel):
    persona_id: str
    sede_id: int  # ❌ Viene del frontend, no es confiable
```

### C. Autorización "Owner-Only" (Regla de Propiedad)

Por defecto, el rol de acceso global `LECTOR` solo tiene permisos de lectura y escritura contextual sobre los recursos de los que es propietario:

```python
# El backend debe validar que el dueño del recurso coincida con el usuario autenticado
if usuario_autenticado.rol_global == "LECTOR" and recurso.persona_id != usuario_autenticado.id:
    raise HTTPException(status_code=403, detail="Operación no permitida sobre este recurso")
```

Un `LECTOR` puede crear, editar o eliminar sus propias tareas entregadas o comentarios en foros, pero no puede ver, modificar o eliminar el progreso académico o expedientes CRM de sus compañeros.

### D. Prohibición de `@property` en Queries de SQLAlchemy

**Regla:** No se pueden usar propiedades decoradas con `@property` como argumentos en métodos `.filter()`, `.order_by()` o cualquier cláusula SQL de SQLAlchemy. Las propiedades de Python no existen a nivel de base de datos.

```python
# ❌ ROMPE: @property no se traduce a SQL
class SesionGrupo(Base):
    fecha_sesion = Column(DateTime)
    
    @property
    def session_date(self):
        return self.fecha_sesion.date()

db.query(SesionGrupo).filter(SesionGrupo.session_date >= cutoff)

# ✅ CORRECTO: usar la columna directamente
db.query(SesionGrupo).filter(SesionGrupo.fecha_sesion >= cutoff)
```

### E. Registro Obligatorio de Nuevos Módulos

Todo nuevo módulo (modelos, schemas, CRUD, API) debe registrarse en:

1. `backend/models.py` — importar el modelo
2. `backend/api/__init__.py` — importar y registrar el router
3. Solo si necesita inicialización especial: `backend/app.py`

---

## 🎨 4. Estándares del Frontend (Next.js + Tailwind CSS)

### A. UX Clean Productivity (Cero Modales Bloqueantes)

**La Regla:** Se prohíbe el uso de ventanas emergentes (Modales / Dialogs) que bloqueen el centro de la pantalla para crear, editar o visualizar información detallada de expedientes, tareas o fichas.

**Estándar UX:** Deben utilizarse Paneles Laterales Deslizables (Drawers). Si el flujo requiere abrir información anidada (ej. abrir una tarea dentro del expediente de un caso), se debe implementar un apilamiento de paneles deslizables ("Drawer Stacking"), permitiendo al usuario volver atrás de forma orgánica sin perder el contexto visual.

```tsx
// CORRECTO: Drawer lateral
<Drawer open={true} onClose={handleClose}>
  <ExpedienteContent casoId={id} />
</Drawer>

// INCORRECTO: Modal bloqueante
<Dialog open={true} onClose={handleClose}>
  <ExpedienteContent casoId={id} />
</Dialog>
```

### B. Uso de Tokens Semánticos en Tailwind

No se permiten colores fijos codificados en duro (como `bg-blue-500` o `border-gray-200`) para componentes estructurales del sistema. Se debe hacer uso exclusivo de las variables semánticas del sistema de diseño mapeadas en la configuración de Tailwind.

```html
<!-- INCORRECTO: -->
<div class="bg-white border border-gray-200 text-gray-800"></div>

<!-- CORRECTO: -->
<div class="bg-sistema-panel border border-sistema-linea text-sistema-texto-primario"></div>
```

### C. Carga Perezosa de Perfiles (Lazy Loading)

Cuando el frontend pinta el perfil de una persona, no debe solicitar todo su historial a la vez mediante consultas masivas. Las consultas deben dividirse de manera modular en pestañas independientes (CRM, Academia, Proyectos, Agenda) que carguen su información bajo demanda con llamadas API independientes.

```tsx
// CORRECTO: llamadas por pestaña
<Tabs>
  <Tab label="CRM" onSelect={() => fetchCrmCasos(personaId)} />
  <Tab label="Academia" onSelect={() => fetchAcademy(personaId)} />
  <Tab label="Proyectos" onSelect={() => fetchProyectos(personaId)} />
</Tabs>

// INCORRECTO: todo en una sola llamada masiva
fetch(`/api/personas/${personaId}/full-profile`)
```

### D. Convención de Rutas

Todas las rutas del frontend deben seguir la convención: `/plataforma/{module}[/{id}]`

```
/plataforma/personas
/plataforma/personas/{uuid}
/plataforma/crm
/plataforma/evangelismo/grupos
/plataforma/academia/cursos
/plataforma/proyectos
```

### E. Prefijo de API

Todas las llamadas al backend deben usar `apiFetch('/endpoint')`. El prefijo `/api` se añade automáticamente mediante `apiUrl()`.

---

## 🚦 5. Guía de Integración para Nuevos Requerimientos

Antes de alterar la base de datos o proponer cambios en el Kernel de personas, filtrar todo requerimiento bajo el siguiente árbol de decisión de 3 niveles:

```
                    ┌─────────────────────────────────────────┐
                    │    Requerimiento de Negocio Nuevo       │
                    └────────────────────┬────────────────────┘
                                         │
                                         ▼
              ┌───────────────────────────────────────────┐
    ¿El       │                                           │
    requerim. │   Nivel 1: Ficha Molecular                │
    representa│   (¿Es una Persona?)                      │
    a un  ───►│                                           │ ───► Se registra en 'personas'
    ser       │   Si el requerimiento habla de un ser     │      del Kernel aplicando tags
    humano?   │   humano, NO se crea tabla nueva.         │      dinámicos.
              │   Se apunta al UUID de personas.          │
              └───────────────────────────────────────────┘
                                         │ No
                                         ▼
              ┌───────────────────────────────────────────┐
              │   Nivel 2: Extensión JSONB                │
    ¿Exige    │   (Atributos Dinámicos)                   │
    capturar  │                                           │
    datos muy │   Si los datos son muy variables y no     │ ───► Se guardan atributos
    variables?│   justifican columnas normalizadas,       │      dinámicos en campo JSONB
          ───►│   usa un campo JSONB en una tabla         │      en tabla satélite.
              │   satélite vinculada por FK.             │
              └───────────────────────────────────────────┘
                                         │ No
                                         ▼
              ┌───────────────────────────────────────────┐
              │   Nivel 3: Bus de Eventos                 │
    ¿Requiere │   (Enlace Polimórfico)                    │
    conectar  │                                           │
    flujos    │   Si el requerimiento necesita conectar   │ ───► Usar enlace polimórfico
    con la    │   la agenda o calendarios de la sede,     │      (modulo_origen +
    agenda o  ───►│   usa el enlace polimórfico con         │      entidad_origen_id).
    calendarios?│   (modulo_origen, entidad_origen_id).    │
              └───────────────────────────────────────────┘
```

---

## 📝 6. Formato de Entrega de Código

Cada desarrollador que proponga un cambio de esquema o una funcionalidad nueva debe documentar su entrega siguiendo estrictamente el siguiente formato matricial:

```json
{
  "auditoria_ccf": {
    "capa_evaluada": "DB / BACKEND / FRONTEND",
    "archivo_o_endpoint": "nombre_archivo.py",
    "estado": "PASS",
    "violacion_axioma": "Ninguna",
    "hallazgo_tecnico": "Descripción de la implementación realizada.",
    "correccion_super_pro": "Bloque de código con la implementación o solución."
  }
}
```

---

## 🔥 7. Errores Comunes y Cómo Evitarlos

| # | Error | Incorrecto | Correcto |
|---|---|---|---|
| 1 | `@property` en SQL | `SesionGrupo.session_date` | `SesionGrupo.fecha_sesion` |
| 2 | `persona_id: int` en schemas | `persona_id: int` | `persona_id: str` |
| 3 | Hard DELETE | `db.delete(persona)` | `persona.estado_vital = 'INACTIVO'` |
| 4 | Olvidar `sede_id` en queries | `db.query(Persona).all()` | `db.query(Persona).filter(Persona.sede_id == sede_id).all()` |
| 5 | Tablas compat | `ConsolidationCase` | `CasoCRM` |
| 6 | DateTime sin timezone | `Column(DateTime)` | `Column(DateTime(timezone=True))` |
| 7 | FK a users.id | `ForeignKey("users.id")` | `ForeignKey("personas.id")` |
| 8 | JSONB en vez de JSON | `Column(JSONB)` | `Column(JSON)` |
| 9 | Modales bloqueantes | `<Dialog>` | `<Drawer>` |
| 10 | Colores fijos en Tailwind | `bg-white` | `bg-sistema-panel` |

---

## 🔍 8. Checklist Pre-Commit — 10 Puntos Obligatorios

Antes de cada commit o PR, verificar CADA UNO de estos puntos:

- [ ] 1. ¿Toda query de listado filtra por `sede_id`?
- [ ] 2. ¿Todos los campos `persona_id` son `str` (no `int`) en schemas Pydantic?
- [ ] 3. ¿Todos los `DateTime` usan `timezone=True`?
- [ ] 4. ¿Está ausente `db.delete()` en tablas transaccionales (usando soft delete)?
- [ ] 5. ¿Las FKs a `personas.id` usan tipo `UUID`?
- [ ] 6. ¿Se usa `JSON` (no `JSONB`) para compatibilidad con SQLite?
- [ ] 7. ¿Se referencian las tablas reales del esquema v2 (no las compat)?
- [ ] 8. ¿Se usan los nombres reales de columnas (no propiedades `@property`)?
- [ ] 9. ¿El nuevo módulo está registrado en `models.py` + `api/__init__.py` + `app.py`?
- [ ] 10. ¿Los cambios están documentados en el formato matricial de entrega?

---

## 📚 9. Referencia Rápida — Mapeo de Tablas

### Tablas del Kernel
| Tabla | PK | FK a personas | Propósito |
|---|---|---|---|
| `personas` | UUID | — | Entidad central |
| `users` | Integer | `persona_id` (opcional, nullable) | Autenticación |
| `persona_role_assignments` | UUID | `persona_id` | Roles dimensionales |

### Tablas por Módulo (v2 actual)
| Módulo | Tabla principal | FK a personas |
|---|---|---|
| CRM Core | `crm_casos` | `persona_id`, `asignado_a_id`, `created_by_id` |
| Academy | `academy_courses`, `academy_enrollments` | `persona_id` |
| Agenda | `agenda_participantes` | `persona_id` |
| Evangelism | `grupos_evangelismo`, `sesiones_grupo` | `lider_persona_id` |
| Proyectos | `proyectos`, `tareas_proyecto`, `equipo_proyecto` | `persona_id` |
| Gamificación | `xp_transactions` | `persona_id` |
| Finanzas | `donations` | `persona_id` |

### Tablas Compat (NO USAR — fueron eliminadas en migración v2)
| ❌ Tabla eliminada | ✅ Reemplazo |
|---|---|
| `consolidation_cases` | `crm_casos` |
| `cell_groups` | `grupos_evangelismo` |
| `cell_group_sessions` | `sesiones_grupo` |
| `courses` | `academy_courses` |
| `enrollments` | `academy_enrollments` |
| `projects` | `proyectos` |
| `project_tasks` | `tareas_proyecto` |

---

## 🧠 10. Convenciones de Nomenclatura

### Backend (Python)
| Tipo | Convención | Ejemplo |
|---|---|---|
| Modelos | `models_{modulo}.py` | `models_crm_core.py` |
| Schemas | `schemas/{modulo}.py` | `schemas/crm_core.py` |
| CRUD | `crud/{modulo}.py` | `crud/crm_core.py` |
| API router | `api/{modulo}.py` | `api/crm_core.py` |
| Servicios | `services/{nombre}.py` | `services/xp_engine.py` |
| Migraciones SQL | `scripts/migrations/{nombre}.sql` | `scripts/migrations/add_sede_uuid.sql` |

### Frontend (Next.js)
| Tipo | Convención | Ejemplo |
|---|---|---|
| Páginas | `/plataforma/{modulo}` | `/plataforma/crm` |
| Componentes | PascalCase | `ExpedienteDrawer.tsx` |
| Stores (Zustand) | `use{Modulo}Store` | `useCrmStore` |
| Hooks | `use{Nombre}` | `usePersonaData` |

---

## 🔄 Migraciones Realizadas v3.0 (2026-06-02) — Plan de Batalla CCF COMPLETADO

### ✅ Seguridad Crítica (Fase 0)
- **8 hard deletes eliminados** → soft deletes en endpoints transaccionales:
  - `api/crm/pastoral.py`: `delete_crm_task()`, `delete_crm_role()`, `delete_volunteer()`
  - `api/evangelism_events.py`: `sync_event_assignments()`
  - `api/evangelism_grupos.py`: `submit_attendance()`
  - `crud/projects.py`: `set_project_phases()`
  - `crud/crm.py`: `update_cell_group()` (2 deletes)
  - `api/auth.py`: `delete_ministerial_user()`
- **Filtrado `sede_id`** agregado a `chat.py`, `graph.py`, `agents.py`
- **`build_graph_snapshot()`** actualizado con `sede_id` en 6 resolvers de nodos

### ✅ Base de Datos (Fase 1)
- **5 migraciones Alembic** creadas y encadenadas (`alembic/versions/20260602_*`):
  1. **`add_missing_idx`**: 12 índices B-Tree en FKs sin índice (academy, tareas, documentos)
  2. **`add_soft_delete`**: `deleted_at` + partial index `ix_*_active` en 12 tablas críticas
  3. **`add_sede_id`**: `sede_id UUID REFERENCES sedes(id)` en 5 tablas operativas
  4. **`rename_compat`**: Renombrado condicional de tablas compat (solo si vacías o post-migración)
  5. **`add_gist`**: Constraint `EXCLUDE USING gist` para doble-booking en `agenda_reserva_recursos`
- Todas las migraciones son **idempotentes** con helpers `_col_exists`, `_index_exists`, `_table_exists`, `_constraint_exists`

### ✅ Backend Performance (Fase 2)
- **`selectinload()`** agregado a CRUDs principales:
  - `crud/academy.py`: `get_courses()` → `lessons`, `enrollments`; `get_enrollments()` → `persona`
  - `crud/crm.py`: `get_personas()`, `get_personas_list()`, `get_personas_paginated()` → `family`, `positions`
  - `crud/projects.py`: `get_projects()`, `get_portfolio_summary()` → `owner`, `tasks`
- **Preservado** filtrado `sede_id` existente en todas las queries

### ✅ Frontend Modernización (Fase 3)
- **4 Modales convertidos a Drawers**:
  - `UniversalCreationModal` → `UniversalCreationDrawer`
  - `AssessmentModal` → `AssessmentDrawer`
  - `CertificateModal` → `CertificateDrawer`
  - `PhaseManagerModal` → `PhaseManagerDrawer`
- **Colores hardcodeados** migrados a tokens semánticos HSL (`primary`, `secondary`, `accent`, `destructive`, `text-primary`, `text-secondary`, `bg-primary`, `bg-secondary`, `bg-muted`, `border-primary`)
- **Delay artificial eliminado** en `members/[id]/page.tsx` + `AbortController` agregado para cancelación de requests
- **`apiFetch()`** actualizado con soporte `signal: AbortSignal`

### ✅ Tests y Estabilidad (Fase 4)
- **~78 tests convertidos de ERROR → PASSED/FUNCTIONAL** (migraciones corregidas)
- **Tests auth_v3**: 9/11 pasan (antes 0/13 ejecutables)
- **`app.py`** robustecido: `Base.metadata.create_all()` maneja `DuplicateTable` gracefully
- **Correcciones de migraciones**:
  - `CREATE INDEX CONCURRENTLY` → `CREATE INDEX` (compatible con transacciones)
  - IDs de revisión truncados a ≤32 chars (`varchar(32)` de Alembic)
  - `tsrange` → `tstzrange` (timestamptz compatible)
  - `btree_gist` extension verificada antes de constraint GIST
- **~78 tests rescatados** de ERROR → PASSED/FUNCTIONAL (migraciones corregidas)
- **Tests auth_v3**: 9/11 pasan (antes 0/13 ejecutables)
- **Agent-7 fix**: 16 tests pre-existentes arreglados:
  - CRM Counseling: `pastor_id` UUID → integer fallback
  - Faro attendance: imports faltantes `SesionGrupo`, `GrupoEvangelismo`, `Asistencia`
  - CRM Domain: string UUID → `uuid.UUID()` en `get_persona`, `update_persona`, `delete_persona`
  - Governance: columna `actor_user_id` agregada a `AdminAuditLog`
  - Projects: `deleted_at` agregado a `ProjectPhase`; `_to_uuid(task_id)` en attachments
- **Agent-8**: 43 tests nuevos para 8 APIs sin cobertura (25 passed, 18 xfail documentando bugs)
- **Resultado final suite completa**: **216 passed, 0 failed, 1 skipped, 18 xfailed** (antes: 77 passed, 36 failed, 110 errors)
- Archivos modificados por fixes: `backend/api/evangelism_grupos.py`, `backend/crud/crm.py`, `backend/crud/audit.py`, `backend/core/audit.py`, `backend/models_governance.py`, `backend/models_projects.py`, `backend/api/projects.py`

### ✅ Datos Compat→v2 (Agent-9)
- **Script de migración** creado: `scripts/migrate_compat_to_v2.py` (579 líneas)
  - Migra 9 tablas: `projects`, `courses`, `enrollments`, `users`, `roles`, `consolidation_cases`, `cell_groups`, `cell_group_sessions`, `agenda_events`
  - Idempotente con `compat_id_mapping` (UUID PK, tabla auxiliar)
  - Modo `--dry-run` para previsualizar sin escribir
  - Manejo de errores por registro (continúa ante fallos individuales)
  - Reporte final con totales/migrados/fallidos por tabla
  - Adaptaciones reales: `crm_celulas`/`crm_sesiones` → `grupos_evangelismo`/`sesiones_grupo`
  - `users`→`auth_users` respeta FK `personas.id` vinculada
- **README** creado: `scripts/README_MIGRACION.md` (162 líneas)

### ✅ Frontend Completado (Agent-10)
- **Tokens CSS semánticos** agregados a `globals.css`: `--destructive`, `--secondary`, `--bg-muted`, `--border-primary`
- **2,805 colores hardcodeados** reemplazados en **275 archivos** según tabla de mapeo:
  - `text-gray-*` → `text-[hsl(var(--text-primary/text-secondary))]`
  - `bg-gray-*` / `bg-white` → `bg-[hsl(var(--bg-primary/bg-muted))]`
  - `text-blue-*` / `bg-blue-*` → `[hsl(var(--primary))]`
  - `text-red-*` / `bg-red-*` → `[hsl(var(--destructive))]`
  - `text-green-*` / `bg-green-*` → `[hsl(var(--secondary))]`
  - `border-gray-*` → `border-[hsl(var(--border-primary))]`
- **Build exitoso**: `npm run build` sin errores de compilación
- **38 errores TypeScript pre-existentes** (no introducidos por cambios)

### ✅ Flujo Hilaridad — Evangelismo → CRM (Agent-11)
- **Motor de Proyección Temporal** (`backend/services/evangelism_projection.py`)
  - Genera `N` sesiones `PENDIENTE` automáticamente desde EstrategiaEvangelismo (fecha_inicio + fecha_fin + frecuencia)
  - Soporta: Semanal, Quincenal, Mensual, Bimensual, Trimestral, Semestral, Anual
- **Bridge Automático** (`backend/services/evangelism_crm_bridge.py`)
  - Trigger reactivo: después de insertar `Asistencia` con `es_primera_vez=True` o `requiere_seguimiento=True`
  - Crea `CasoCRM` en pipeline `NUEVOS_VISITANTES` con SLA 48h
  - Sella origen: `origen_estrategia_id`, `origen_grupo_id`, `origen_fecha`
  - Inyecta tags dinámicos: `["VISITANTE_ESTRATEGIA_X", "GRUPO_Y", "SESION_Z"]`
  - Setea `spiritual_status = "VISITANTE_EVANGELISMO"`
  - Respuesta JSON unificada con `evento_integracion` + `metadata`
- **Endpoint modificado** (`backend/api/evangelism_grupos.py`)
  - `submit_attendance()` invoca el bridge automáticamente
  - Registro de visitante crea persona en Kernel + marca `origen_*`
- **Seed pipeline** (`backend/crud/crm_core.py`)
  - `seed_pipeline_nuevos_visitantes(db, sede_id)` idempotente
- **Tests** (`tests/test_evangelism_crm_bridge.py` — 8 tests pasan)
- **Resultado suite**: **224 passed** (antes 216)

### ✅ Arquitectura y CI/CD (Fase 5)
- **Pipeline GitHub Actions** creada (`.github/workflows/ci.yml`):
  - Quality gate backend: Ruff, Bandit, mypy, pytest con coverage ≥70%
  - Quality gate frontend: ESLint, TypeScript, build
  - Verificación de migraciones: upgrade/downgrade/upgrade
  - Deploy condicional a staging (develop) y producción (main)
- **Pre-commit hooks** configurados (`.pre-commit-config.yaml`):
  - Trailing whitespace, EOF, YAML/JSON validation
  - Ruff lint + format
  - Bandit security scan
  - pytest smoke tests + reglas tests
- **Runbook de Producción** creado (`docs/RUNBOOK_PRODUCCION.md`)
  - Arquitectura del sistema, procedimiento de deploy blue-green
  - Rollback (rápido y completo), monitoreo, alertas
  - Escalamiento P1-P4, procedimientos de emergencia
  - Mantenimiento programado (diario/semanal/mensual/trimestral)
- **Análisis Hilaridad** documentado (`analytics/ANALISIS_HILARIDAD_CCF_v1.md`)
  - 506 líneas de análisis punto-a-punto (BD → Backend → Frontend → Tests)

---

> **"El código que escribes hoy es la plataforma que administrarás mañana. Cada atajo que tomas ahora es una deuda que pagarás con intereses en producción."**
> — Arquitectura CCF
