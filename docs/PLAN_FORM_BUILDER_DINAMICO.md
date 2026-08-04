# PLAN FORM BUILDER DINÁMICO (cms_forms)

**Propietario:** Plataforma CCF
**Estado:** Borrador — pendiente de aprobación
**Alcance:** Render dinámico de `CmsForm` + constructor admin con DnD + integración con preinscripción de eventos
**Compatibilidad:** Backward-compatible (los `CmsForm` existentes con schema de 6 tipos siguen funcionando)

---

## 1. Problema

Hoy el constructor de formularios del CMS (`/plataforma/cms/forms`) permite definir
campos en el **backend** (`cms_forms.fields = [...]`), pero:

1. El **sitio público NO renderiza** formularios dinámicamente desde el builder.
   Las secciones `contact_form` / `prayer_form` de `cms_v2_sections.py` tienen
   campos **hardcodeados** (`name`, `email`, `phone`, `notes`) y ignoran los
   `fields` definidos en el `CmsForm`. El endpoint `POST /public/forms/{id}/submit`
   existe y captura respuestas, pero ningún componente pinta el formulario.
2. La **preinscripción de eventos** (`/public/events/[event_id]/register`)
   tiene campos **fijos en React** (first_name, last_name, email, phone,
   accept_contact). Cada evento pide información distinta (edad, iglesia de
   procedencia, alergias, acompañantes, etc.) y hoy requiere tocar código.
3. El **constructor admin** es un MVP: 6 tipos de campo, reordenar con flechas
   ↑/↓ (sin drag-and-drop real), sin preview en vivo, sin lógica condicional,
   sin validación custom, sin captcha.

## 2. Objetivo

Que un editor (sin tocar código) pueda:

1. **Diseñar** un formulario en el admin con DnD real, preview en vivo, tipos
   avanzados, validación y condicionales.
2. **Vincular** ese formulario a un evento de preinscripción (o a una sección
   del sitio CMS) para que se renderice **dinámicamente** en el público.
3. Que el **backend valide** server-side los campos (tipos, obligatorios,
   regex, longitud, opciones válidas, condicionales) antes de persistir la
   respuesta — cero confianza en el cliente.

## 3. Modelo de datos (extensiones a `cms_forms.fields`)

El JSON `fields` de `CmsForm` hoy es una lista de dicts sueltos. Se formaliza
con un **contrato de campo** versionado y validado en el backend.

### 3.1 Schema de campo (Pydantic `CmsFormFieldSpec`)

```python
FIELD_TYPES = Literal[
    "text", "email", "phone", "textarea", "select", "checkbox",  # existentes
    "number", "date", "datetime", "url",                          # nuevos básicos
    "select_multiple", "radio",                                   # nuevas opciones
    "rating", "slider",                                            # nuevas escalas
    "file",                                                        # nuevo adjunto
    "section", "page",                                             # nuevos agrupadores
    "captcha", "divider",                                          # nuevos utilitarios
]
```

```python
class CmsFormFieldSpec(BaseModel):
    """Contrato de un campo de CmsForm validado por el backend."""
    id: str = Field(..., min_length=1, max_length=80)
    type: FIELD_TYPES
    label: str = Field(..., min_length=1, max_length=200)
    hint: Optional[str] = Field(default=None, max_length=400)          # ayuda bajo el campo
    placeholder: Optional[str] = Field(default=None, max_length=200)
    required: bool = False
    default_value: Any = None                                        # prefijado
    options: Optional[list[str]] = None                              # para select/radio/select_multiple
    allow_other: bool = False                                        # "+ Otra" en select/radio
    min_length: Optional[int] = Field(default=None, ge=0, le=10000)  # text/textarea
    max_length: Optional[int] = Field(default=None, ge=1, le=50000)
    min_value: Optional[float] = None                                # number/slider/rating
    max_value: Optional[float] = None
    step: Optional[float] = Field(default=None, gt=0)                # number/slider
    regex_pattern: Optional[str] = None                              # validación custom (text/email/url)
    regex_message: Optional[str] = Field(default=None, max_length=200)
    accept: Optional[str] = None                                     # mime types para file (ej "image/*")
    max_file_mb: Optional[float] = Field(default=None, gt=0, le=50)  # límite tamaño adjunto
    # Lógica condicional — mostrar este campo solo si otro cumple una condición
    visible_if: Optional[CmsFormCondition] = None
    # Multi-step: en qué página va (0 = todo en una página; page=1,2,3.. agrupa)
    page: int = 0
```

```python
class CmsFormCondition(BaseModel):
    """Condición de visibilidad de un campo (lógica condicional)."""
    field_id: str                                                   # el campo que se evalúa
    operator: Literal["eq", "neq", "in", "not_in", "contains", "gt", "lt", "gte", "lte", "checked", "empty", "not_empty"]
    value: Any = None                                                # valor de comparación
```

### 3.2 Config de formulario (`CmsForm` columnas nuevas)

```sql
ALTER TABLE cms_forms
    ADD COLUMN settings_json      JSON  NOT NULL DEFAULT '{}',
    ADD COLUMN captcha_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN captcha_provider  VARCHAR(20) NOT NULL DEFAULT 'hcaptcha',
    ADD COLUMN honeypot_enabled  BOOLEAN NOT NULL DEFAULT TRUE;
```

`settings_json` contendrá configuración de presentación (multi-step, color del
botón, etc.) y se valida con `CmsFormSettings` (sin secretos — los keys de
hCaptcha viven en variables de entorno).

### 3.3 `event_registrations` + `CrmEvent.form_id`

```python
# CrmEvent (en crm_events)
form_id = Column(UUID, ForeignKey("cms_forms.id", ondelete="SET NULL"), nullable=True)
```

Si `event.form_id` está seteado, el GET `/public/events/{id}` devuelve el
`form_id` y el frontend lo usa para renderizar el `CmsFormRenderer`. Si no, se
usa el form fijo actual (backward-compat).

Los campos del formulario se capturan en `event_registrations.extras` (JSON ya
existente), bajo la clave `_form_data` — o para endpoints `submit` genéricos
en `cms_form_submissions.data` como hoy.

## 4. Migración

Una migración idempotente:

```python
# 20260804_0002_cms_form_builder_dinamico.py
# - ADD COLUMN settings_json, captcha_enabled, captcha_provider, honeypot_enabled a cms_forms
# - ADD COLUMN form_id a crm_events (FK a cms_forms.id, ON DELETE SET NULL)
# - Idempotente (_has_column) + reversible
```

No se alteran los `fields` existentes (son JSON向后-compatibles).

## 5. API Contracts (backend)

### 5.1 Render público del `CmsForm`

```python
GET /api/public/forms/{form_id}
→ CmsFormPublicRead  # sin notify_emails, solo lo necesario para renderizar
```

```python
class CmsFormPublicRead(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    fields: list[CmsFormFieldSpec]   # contratos validados
    submit_button_text: str
    success_message: str
    captcha_enabled: bool
    captcha_site_key: Optional[str] = None  # hCaptcha site key (público)
    honeypot_enabled: bool
    settings_json: dict
    is_active: bool
```

Si `is_active=False` → 404.

### 5.2 Submit público con validación server-side

```python
POST /api/public/forms/{form_id}/submit
Body: {
    "data": { "<field_id>": "<value>", ... },
    "captcha_token": "..."  # si captcha_enabled, obligatorio
    "_hp": ""               # honeypot — debe venir vacío
}
→ { "success": true, "submission_id": "..." }
```

El backend **valida server-side**:
1. Cada `field_id` en `data` corresponde a un campo del formulario.
2. Campos `required` presentes y no vacíos.
3. Tipos válidos (email con regex, número numérico, etc.).
4. `options` válidos para select/radio.
5. `regex_pattern`, `min/max_length`, `min/max_value` cumplidos.
6. `visible_if` (condicionales) — los campos ocultos no deben llegar.
7. Honeypot vacío (si `honeypot_enabled`).
8. hCaptcha válido (si `captcha_enabled`) — POST a
   `https://api.hcaptcha.com/siteverify` con `HCAPTCHA_SECRET`.

### 5.3 Admin

Reuso endpoints existentes (`listCmsForms`, `putCmsForm`, etc.) — el frontend
envía el `fields` con el nuevo schema. El backend valida con
`CmsFormFieldSpec` en `CmsFormCreate`/`CmsFormUpdate`.

### 5.4 Preinscripción de eventos

```python
GET /api/public/events/{event_id}
→ PublicEventRead  # + form_id: Optional[UUID] = None
```

Si `form_id` seteado, el frontend hace `GET /public/forms/{form_id}` y
renderiza con `CmsFormRenderer`. El submit va a
`POST /public/events/{event_id}/register` con `extras._form_data = {...}` o
(según prefieras) directo a `POST /public/forms/{form_id}/submit`.

**Decisión:** el submit del pre-registro sigue yendo a
`/public/events/{event_id}/register` (para crear `EventRegistration` + QR),
pero el payload incluye `form_data: dict` que el backend valida contra el
`CmsForm` y persiste en `event_registrations.extras._form_data`.

### 5.5 hCaptcha config

```python
# Settings (env)
HCAPTCHA_SITE_KEY: str = ""     # público, va al frontend
HCAPTCHA_SECRET_KEY: str = ""   # secreto, usa siteverify server-side
```

Si `captcha_enabled=True` pero los keys no están configurados → 500 con
mensaje claro (misconfiguration detected).

### 5.6 Render dinámico en secciones CMS

La sección `contact_form` del `PublicSectionRenderer` se amplía para, si
`props_json.form_id` está seteado, renderizar `CmsFormRenderer` en vez del
form hardcoded. `prayer_form` igual.

## 6. Frontend admin (constructor)

Componente: `frontend/src/app/plataforma/cms/forms/page.tsx` (refactor mayor).

### 6.1 Drag-and-drop con @dnd-kit

`@dnd-kit/core` + `@dnd-kit/sortable` ya instaladas (verificado en
`frontend/package.json`). Reemplazo las flechas ↑/↓ por `SortableContext` +
`useSortable` — arrastrar por el "drag handle" (estirable a móvil).
**Nota:** aunque en la encuesta se propuso `react-beautiful-dnd`, esa librería
NO está instalada y está en modo mantenimiento; `@dnd-kit` ya está presente,
es la sucesora recomendada y soporta teclado/móvil.

### 6.2 Tipos de campo ampliados

Paleta de tipos agrupada:
- **Básicos:** Texto, Email, Teléfono, Texto largo, Número, URL, Fecha, Fecha+hora.
- **Opciones:** Lista desplegable (select múltiple/simple), Radio.
- **Escalas:** Rating (estrellas), Slider.
- **Agrupadores:** Sección (título), Página (multi-step), Divisor.
- **Especiales:** Archivo, Captcha.

### 6.3 Editor por tipo

Configuración específica según `type`:
- `select`/`radio`: editor de opciones (lista editable + toggle "permitir Otro").
- `number`/`slider`: min/max/step.
- `text`/`email`/`url`: regex + mensaje de error + min/max_length.
- `file`: accept (mime) + max_file_mb.
- `divider`/`section`/`page`: solo label.

### 6.4 Lógica condicional (visible_if)

UI tipo "Mostrar si `[campo]` `[operador]` `[valor]`" con dropdowns.
Operadores: `eq`, `neq`, `in`, `not_in`, `contains`, `gt`, `lt`, `gte`,
`lte`, `checked`, `empty`, `not_empty`.

### 6.5 Preview en vivo

Panel derecho que renderiza `CmsFormRenderer` con los campos actuales (modo
"preview" sin submit real). Se actualiza instantáneamente al editar.

### 6.6 Multi-step

Si hay campos con `page > 0`, el renderer muestra progreso (Paso 1/3, 2/3...)
y botones Siguiente/Anterior.

### 6.7 Config de formulario

Drawer ampliado con:
- captcha toggle + provider (hCaptcha) — preview del widget.
- honeypot toggle.
- notify_emails (existente).
- submit_button_text / success_message (existente).
- settings_json: `multi_step_progress_bar: bool`, `button_color: str`.

## 7. Frontend público — `CmsFormRenderer`

Nuevo componente reusable:
`frontend/src/components/public/cms/CmsFormRenderer.tsx`.

Props:
```ts
interface CmsFormRendererProps {
    form: CmsFormPublicRead;        // viene del backend
    onSubmit: (data: Record<string, any>) => Promise<void>;
    submitLabel?: string;           // override
    compact?: boolean;              // modo reducido (embebido)
}
```

Renderiza dinámicamente por `field.type`, con:
- Validación cliente (mirror del backend).
- Soporte de condicionales (`visible_if`) reactivos.
- Multi-step con progreso.
- Honeypot (campo `website` hidden).
- hCaptcha widget (lib `react-hcaptcha` a instalar).
- Estados idle/submitting/success/error.
- Accesibilidad (`label htmlFor`, `aria-live`, `aria-invalid`).

## 8. Tests

### 8.1 Backend (`tests/test_cms_forms_dynamic.py`)

- Validación server-side por tipo (email inválido, número no numérico, select
  fuera de options, regex fail).
- Campos `required` ausentes → 422.
- Condicionales: campo oculto llega → 422 (campos no visibles no se aceptan).
- Honeypot rellenado → 200 silencioso (no persiste).
- hCaptcha mockeado (monkeypatch `siteverify`).
- CmsForm inactivo → 404.
- Render público (`GET /public/forms/{id}`) no expone `notify_emails`.

### 8.2 Integración preinscripción

`tests/test_event_registrations_dynamic_form.py`:
- Evento con `form_id` seteado → register valida `form_data` contra el form.
- Evento sin `form_id` → fallback al flujo fijo existente (regresión).

### 8.3 Frontend

`CmsFormRenderer.test.tsx` — render de tipos, condicional que oculta campo,
multi-step, captcha presente.

## 9. Commit único

```
feat(cms+events): form builder dinámico con DnD, render público y preinscripción configurable
```

## 10. Dependencias frontend nuevas

- `@dnd-kit/core` ✅ (ya instalada)
- `@dnd-kit/sortable` ✅ (ya instalada)
- `@dnd-kit/utilities` ✅ (ya instalada)
- `react-hcaptcha` 🔴 (instalar)

## 11. Variables de entorno

```bash
HCAPTCHA_SITE_KEY=...     # público (frontend renderiza el widget)
HCAPTCHA_SECRET_KEY=...   # secreto (backend siteverify)
```

## 12. Backward-compat y no-regresión

- `CmsForm.fields` existentes (schema simple de 6 tipos) siguen siendo
  válidos — el nuevo `CmsFormFieldSpec` es **superset** (todo campo viejo
  pasa la validación).
- Secciones `contact_form`/`prayer_form` sin `form_id` siguen renderizando el
  form hardcoded (regresión: ningún cambio visible).
- Preinscripción de eventos sin `form_id` usa el form fijo actual.
- El endpoint `POST /public/forms/{id}/submit` sigue back-compat — si recibe
  el schema viejo, lo acepta (validación tolerante para campos sin id).
