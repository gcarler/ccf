# Manual de Estándares de Desarrollo y Arquitectura — Plataforma CCF

**Versión:** 2.1 (Enterprise-Grade — Anti-Data-Loss Enforced)  
**Autor:** Arquitectura de Software y DBA Principal  
**Audiencia:** Desarrolladores Backend, Frontend, DBAs y Agentes de IA  
**Última actualización:** 2026-05-29

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

**En código:**
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
caso.deleted_at = datetime.now(timezone.utc)
db.commit()

# INCORRECTO: Hard delete
db.delete(persona)
db.commit()
```

### D. Control del Tiempo (Huso Horario Estricto)

Todos los campos de fecha y hora deben usar `TIMESTAMP WITH TIME ZONE`:

```python
# CORRECTO
created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# INCORRECTO
created_at = Column(DateTime)  # Sin timezone
```

El servidor siempre almacena en UTC, y el frontend se encarga de formatear la hora según el huso horario local de la sede.

### E. Restricciones de Exclusión (Race Conditions)

Para evitar colisiones físicas en reservas (salones, vehículos), aplicar restricción GIST a nivel de motor:

```sql
ALTER TABLE agenda_reserva_recursos 
ADD CONSTRAINT sin_colisiones_fisicas 
EXCLUDE USING gist (
    recurso_id WITH =, 
    tsrange(fecha_inicio, fecha_fin) WITH &&
);
```

### F. Protocolo de Migración Segura de Tipos de Datos (Anti-Data-Loss)

Al migrar PK/FK de Integer a UUID, seguir estos 6 pasos **en orden exacto**. La omisión del Paso 3 causa pérdida irreversible de relaciones históricas.

**🚨 El Antipatrón Catastrófico:** Si se elimina la PK entera de la tabla padre para crear la nueva columna UUID, se rompe inmediatamente la posibilidad de hacer JOIN con las tablas hijas. La tabla de backup solo tendrá los enteros antiguos pero no los nuevos UUIDs, dejando huérfanas todas las relaciones.

**🛠️ Receta de 6 Pasos (Ejemplo: `sedes.id` Integer→UUID, hija `grupos_evangelismo.sede_id`):**

```sql
-- PASO 1: Nueva columna temporal en PADRE (conservando PK original)
ALTER TABLE sedes ADD COLUMN uuid_id UUID DEFAULT gen_random_uuid();
UPDATE sedes SET uuid_id = gen_random_uuid() WHERE uuid_id IS NULL;

-- PASO 2: Columna temporal en HIJAS
ALTER TABLE grupos_evangelismo ADD COLUMN sede_uuid UUID;

-- PASO 3: MAPEO MOLECULAR — cruzar por la PK entera que sigue activa
-- ESTE PASO GARANTIZA LA INTEGRIDAD DE LAS RELACIONES HISTÓRICAS
UPDATE grupos_evangelismo 
SET sede_uuid = sedes.uuid_id 
FROM sedes 
WHERE grupos_evangelismo.sede_id = sedes.id;

-- PASO 4: Validación — verificar cero huérfanos
ALTER TABLE grupos_evangelismo ALTER COLUMN sede_uuid SET NOT NULL;

-- PASO 5: Remover restricciones y columnas antiguas
ALTER TABLE grupos_evangelismo DROP CONSTRAINT IF EXISTS fk_grupos_sede_id;
ALTER TABLE sedes DROP CONSTRAINT IF EXISTS sedes_pkey CASCADE;
ALTER TABLE grupos_evangelismo DROP COLUMN sede_id;
ALTER TABLE sedes DROP COLUMN id;

-- PASO 6: Renombrar y recrear PK/FKs definitivas
ALTER TABLE sedes RENAME COLUMN uuid_id TO id;
ALTER TABLE sedes ADD CONSTRAINT sedes_pkey PRIMARY KEY (id);
ALTER TABLE grupos_evangelismo RENAME COLUMN sede_uuid TO sede_id;
ALTER TABLE grupos_evangelismo ADD CONSTRAINT fk_grupos_sede_id 
    FOREIGN KEY (sede_id) REFERENCES sedes(id) ON DELETE CASCADE;
```

> ⚠️ **NUNCA** ejecutar PASO 5 sin haber completado y verificado el PASO 3.

---

## ⚡ 3. Estándares del Backend (FastAPI + SQLAlchemy)

### A. Tipado Estricto de Parámetros

Todos los parámetros que manejen referencias a personas o recursos deben estar tipados como UUID:

```python
# CORRECTO
persona_id: str  # UUID como string en Pydantic

# INCORRECTO
persona_id: int  # Tipado genérico incorrecto
```

### B. Inyección de Contexto en Endpoints

El backend no debe confiar en los datos de sede que envía el frontend. El `sede_id` debe inyectarse desde el token JWT:

```python
def get_user_sede_id(db: Session, user_id: str) -> Optional[str]:
    persona = db.query(Persona).filter(Persona.id == user_id).first()
    return persona.sede_id if persona else None

@router.get("/personas")
def list_personas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
):
    sede_id = get_user_sede_id(db, current_user.id)
    return search_personas(db, sede_id=sede_id)
```

### C. Autorización "Owner-Only" (Regla de Propiedad)

El rol `LECTOR` solo tiene permisos sobre recursos propios:

```python
if current_user.rol_global == "LECTOR" and recurso.persona_id != current_user.persona_id:
    raise HTTPException(status_code=403, detail="Operación no permitida sobre este recurso")
```

### D. Nombres de Archivos y Convenciones

| Componente | Convención | Ejemplo |
|---|---|---|
| Modelos | `models_{modulo}.py` | `models_crm_core.py` |
| Schemas Pydantic | `schemas/{modulo}.py` | `schemas/crm_core.py` |
| CRUD | `crud/{modulo}.py` | `crud/crm_core.py` |
| API Router | `api/{modulo}.py` | `api/crm_core.py` |
| Servicios | `services/{nombre}.py` | `services/xp_engine.py` |
| Migraciones | `scripts/migrations/{nombre}.sql` | `scripts/migrations/uuid_migration.sql` |

### E. Registro de Nuevos Módulos

Cada módulo nuevo debe registrarse en 3 lugares:
1. `backend/models.py` — import del módulo
2. `backend/api/__init__.py` — router en la lista
3. `backend/app.py` — si requiere inicialización especial

---

## 🎨 4. Estándares del Frontend (Next.js + Tailwind CSS)

### A. UX Clean Productivity (Cero Modales Bloqueantes)

**La Regla:** Se prohíbe el uso de ventanas emergentes (Modales / Dialogs) que bloqueen el centro de la pantalla.

**Estándar UX:** Paneles Laterales Deslizables (Drawers). Si se requiere información anidada, implementar "Drawer Stacking".

```tsx
// CORRECTO: Drawer lateral
<Drawer open={open} onClose={handleClose}>
  <DrawerContent>...</DrawerContent>
</Drawer>

// INCORRECTO: Modal bloqueante
<Modal open={open}>
  <ModalContent>...</ModalContent>
</Modal>
```

### B. Uso de Tokens Semánticos en Tailwind

```html
<!-- INCORRECTO: Colores fijos -->
<div class="bg-white border border-gray-200 text-gray-800">

<!-- CORRECTO: Tokens semánticos -->
<div class="bg-sistema-panel border border-sistema-linea text-sistema-texto-primario">
```

### C. Carga Perezosa (Lazy Loading)

El frontend no debe solicitar todo el historial de una persona a la vez mediante consultas masivas. Las consultas deben dividirse de manera modular en pestañas independientes que carguen su información bajo demanda con llamadas API independientes:

```
/plataforma/personas/{id}?tab=crm      → GET /api/v2/crm/casos?persona_id=X
/plataforma/personas/{id}?tab=academy  → GET /api/v2/academy/enrollments?persona_id=X
/plataforma/personas/{id}?tab=events   → GET /api/v2/agenda/participantes?persona_id=X
```

### D. Rutas y Nombrado

| Tipo | Convención | Ejemplo |
|---|---|---|
| Páginas | `/plataforma/{modulo}` | `/plataforma/crm` |
| Detalle | `/plataforma/{modulo}/{id}` | `/plataforma/crm/personas/{id}` |
| API calls | `apiFetch('/modulo/endpoint')` | `apiFetch('/crm/personas')` |
| Stores | `use{Module}Store` | `useCrmStore` |

---

## 🚦 5. Guía de Integración para Nuevos Requerimientos

Antes de alterar la base de datos o proponer cambios en el Kernel de personas, filtrar todo requerimiento bajo este árbol de decisión:

```
                    ¿El requerimiento
                    representa a un  ───► Nivel 1: Ficha Molecular
                    ser humano?          Se registra en 'personas' del Kernel
                                         aplicando tags dinámicos.
                    │ No
                    ▼
                    ¿El requerimiento
                    exige capturar   ───► Nivel 2: Extensión JSONB
                    datos muy            Se guardan atributos dinámicos
                    variables?           en campo JSONB en tabla satélite.
                    │ No
                    ▼
                    ¿Requiere conectar ───► Nivel 3: Bus de Eventos
                    flujos con la         Se utiliza Enlace Polimórfico
                    agenda/calendarios?   (modulo_origen + entidad_origen_id).
```

---

## 📝 6. Formato de Entrega de Código

Cada cambio debe documentarse siguiendo este formato matricial:

```json
{
  "auditoria_ccf": {
    "capa_evaluada": "DB / BACKEND / FRONTEND",
    "archivo_o_endpoint": "nombre_archivo.py",
    "estado": "PASS",
    "violacion_axioma": "Ninguna",
    "hallazgo_tecnico": "Descripción de la implementación realizada.",
    "correccion_super_pro": "Bloque de código con la implementación."
  }
}
```

---

## 🔥 7. Errores Comunes y Cómo Evitarlos

### Error #1: `@property` en queries SQL
```python
# ❌ ROMPE: @property no existe en PostgreSQL
db.query(SesionGrupo).filter(SesionGrupo.session_date >= cutoff)

# ✅ CORRECTO: usar la columna real
db.query(SesionGrupo).filter(SesionGrupo.fecha_sesion >= cutoff)
```

### Error #2: `persona_id: int` en schemas
```python
# ❌ ROMPE: UUID no es int
class CasoCreate(BaseModel):
    persona_id: int

# ✅ CORRECTO
class CasoCreate(BaseModel):
    persona_id: str
```

### Error #3: Hard DELETE en vez de Soft Delete
```python
# ❌ ROMPE: datos irrecuperables
db.delete(persona)

# ✅ CORRECTO
persona.estado_vital = "INACTIVO"
```

### Error #4: Olvidar `sede_id` en queries
```python
# ❌ FUGA DE DATOS: todas las sedes
def list_personas(db: Session):
    return db.query(Persona).all()

# ✅ CORRECTO
def list_personas(db: Session, sede_id: int):
    return db.query(Persona).filter(Persona.sede_id == sede_id).all()
```

### Error #5: Usar tablas compat en queries
```python
# ❌ ROMPE: tabla eliminada
db.query(ConsolidationCase).all()

# ✅ CORRECTO: usar tabla nueva
db.query(CasoCRM).all()
```

### Error #6: `DateTime` sin `timezone=True`
```python
# ❌ INCONSISTENCIA horaria
fecha = Column(DateTime)

# ✅ CORRECTO
fecha = Column(DateTime(timezone=True))
```

### Error #7: FK a `users.id` en vez de `personas.id`
```python
# ❌ VIOLACIÓN AXIOMA 1
user_id = Column(Integer, ForeignKey("users.id"))

# ✅ CORRECTO
persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"))
```

### Error #8: `JSONB` en vez de `JSON` (incompatible con SQLite)
```python
# ❌ ROMPE en SQLite (desarrollo local)
detalles = Column(JSONB)

# ✅ CORRECTO
detalles = Column(JSON)
```

---

## 🔍 8. Checklist Pre-Commit

Antes de cada commit, verificar:

- [ ] `python -m flake8 backend/ --count` → 0 errores
- [ ] `python -c "import ast; ast.parse(open('file.py').read())"` → sin SyntaxError
- [ ] Ningún `persona_id: int` en schemas para tablas con FK UUID
- [ ] Todas las queries de listado filtran por `sede_id`
- [ ] Ningún `@property` usado en `.filter()` o `.order_by()` de SQLAlchemy
- [ ] Todos los `DateTime` tienen `timezone=True`
- [ ] Ningún `ForeignKey("users.id")` para representar personas
- [ ] Ningún `db.delete()` en tablas transaccionales (usar soft delete)
- [ ] `JSON` (no `JSONB`) para compatibilidad SQLite
- [ ] Cambios documentados en el formato matricial

---

## 📚 9. Referencia Rápida — Mapeo de Tablas

### Tablas del Kernel
| Tabla | PK | FK a personas | Propósito |
|---|---|---|---|
| `personas` | UUID | — | Entidad central |
| `users` | Integer | `persona_id` (opcional) | Autenticación |
| `persona_role_assignments` | UUID | `persona_id` | Roles dimensionales |

### Tablas por Módulo (v2)
| Módulo | Tabla principal | FK a personas |
|---|---|---|
| CRM Core | `crm_casos` | `persona_id`, `asignado_a_id`, `created_by_id` |
| Academy | `academy_enrollments` | `persona_id` |
| Agenda | `agenda_participantes` | `persona_id` |
| Evangelism | `grupos_evangelismo` | `lider_persona_id` |
| Proyectos | `equipo_proyecto` | `persona_id` |
| Gamificación | `xp_transactions` | `persona_id` |
| Finanzas | `donations` | `persona_id` |

---

> **"El código que escribes hoy es la plataforma que administrarás mañana. Cada atajo que tomas ahora es una deuda que pagarás con intereses en producción."**  
> — Arquitectura CCF
