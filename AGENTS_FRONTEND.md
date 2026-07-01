# Estándares de Frontend — Plataforma CCF

**Versión:** 1.0
**Audiencia:** Desarrolladores Frontend, Diseñadores UX y Agentes de IA
**Relación:** Complementa y extiende las reglas de `AGENTS.md` (Manual v2.1)

---

## 🧠 Principios Fundamentales

### 1. Las personas NO son "miembros"

En el frontend de CCF **nunca** se usa la palabra "miembro" para referirse a una persona registrada en el kernel. El término correcto es **personas**.

| ❌ Incorrecto | ✅ Correcto |
|---|---|
| `members_count` (en UI) | `total_personas` |
| "Lista de miembros" | "Directorio de personas" |
| `MemberCard` | `PersonaCard` |
| `membership_status` | `persona_role_assignments` |

**Excepción:** La tabla/grupo de base de datos puede llamarse internamente "miembros" solo si se refiere a un rol específico (rol B del Axioma 2), pero la UI **siempre** debe presentarlo como "integrantes", "participantes" o "personas del grupo".

### 2. Grupos Comunitarios y de Evangelismo

El concepto de grupos comunitarios y de evangelismo debe presentarse como **Grupo de Evangelismo**, **Grupo Comunitario** o **Casa de Gloria**, dependiendo del contexto. El código, rutas y APIs deben usar nombres canónicos en español (`grupos`, `grupos_evangelismo`).

| Contexto | Término UI |
|---|---|
| Público / landing | "Casas de Gloria" |
| Plataforma / admin | "Grupos de Evangelismo" |
| API interna | `grupos_evangelismo` |

### 3. Drawers, no Modales (Cero Modales Bloqueantes)

**Regla inquebrantable:** No se usan `<Dialog>`, `<Modal>` ni ventanas emergentes bloqueantes para crear, editar o ver detalles.

✅ **Siempre usar:** Paneles laterales deslizables (`<Drawer>`, `<SidePanel>`, `<RightPanel>`)
✅ **Para anidamiento:** "Drawer Stacking" — los drawers se apilan y se puede navegar hacia atrás sin perder contexto

```tsx
// ✅ CORRECTO
import { RightPanel } from '@/components/ui/RightPanel';
<RightPanel open={true} onClose={handleClose}>
  <ExpedienteContent />
</RightPanel>

// ❌ INCORRECTO
import { Dialog } from '@headlessui/react';
<Dialog open={true} onClose={handleClose}>...</Dialog>
```

### 4. Tokens Semánticos (Colores del Sistema)

**Prohibido** usar colores fijos de Tailwind en componentes del sistema. Usar exclusivamente variables CSS semánticas.

#### 🔵 Paleta de colores CCF — SOLO AZULES

La plataforma usa **exclusivamente tonos azules**. Está **estrictamente prohibido** usar `indigo`, `violet` o `purple` en cualquier botón, badge, borde, texto o fondo de la UI.

| Color | RGB | Tailwind | Uso |
|---|---|---|---|
| **Azul oscuro** | `rgb(0, 27, 72)` | `ccf-blue-dark` | Headings, branding, texto principal de auth |
| **Azul medio** | `rgb(0, 69, 129)` | `ccf-blue-medium` | Hover de botones primarios |
| **Azul primario** | `rgb(1, 138, 189)` | `ccf-blue-light` / `hsl(var(--primary))` | Botones, links, iconos de acción |
| **Azul pálido** | `rgb(221, 232, 240)` | `ccf-blue-pale` | Fondos de badges, highlights |

#### Variables CSS — modo claro (`[data-theme="day"]`)

```css
--primary: 197 98% 37%;          /* rgb(1,138,189) — azul CCF principal */
--primary-foreground: 0 0% 100%; /* blanco para texto sobre botones */
--bg-primary: 0 0% 100%;
--bg-secondary: 210 40% 98%;
--surface-1: 0 0% 100%;
--surface-2: 210 40% 98%;
--surface-3: 210 40% 96.1%;
--text-primary: 222 47% 11%;
--text-secondary: 215 16% 47%;
--border: 214 32% 91%;
--destructive: 0 84.2% 60.2%;   /* rojo — solo para acciones destructivas */
--secondary: 142 76% 36%;        /* verde — confirmaciones / éxito */
```

#### Variables CSS — modo oscuro (`[data-theme="night"]`)

```css
--primary: 197 78% 50%;          /* azul CCF más claro para fondos oscuros */
--primary-foreground: 0 0% 100%;
--bg-primary: 222 47% 4%;
--bg-secondary: 222 47% 6%;
--surface-1: 222 47% 4%;
--surface-2: 222 47% 10%;
--surface-3: 222 47% 15%;
--text-primary: 210 40% 98%;
--text-secondary: 215 20.2% 65.1%;
--border: 217 33% 17%;
--destructive: 0 62.8% 30.6%;
--secondary: 142 71% 45%;
```

#### Uso correcto en JSX

```tsx
// ✅ CORRECTO — botón primario
<button className="bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary)/0.85)]" />

// ✅ CORRECTO — panel/card
<div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))]" />

// ✅ CORRECTO — badge de acción
<span className="bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-900/20 dark:text-blue-400" />

// ❌ INCORRECTO — violaciones de color
<button className="bg-indigo-600" />   // indigo → reemplazar por hsl(var(--primary))
<button className="bg-violet-500" />   // violet → reemplazar por hsl(var(--primary))
<button className="bg-purple-600" />   // purple → reemplazar por hsl(var(--primary))
```

#### Colores de Tailwind permitidos para decoración categórica (iconos, estadísticas)

Cuando se usan colores para **diferenciar categorías** (no botones ni UI chrome), se permiten:
- `blue-*` — categoría de proyectos, datos
- `green-*` / `emerald-*` — éxito, activo, crecimiento
- `red-*` / `rose-*` — error, inactivo, peligro
- `amber-*` / `yellow-*` — advertencia, pendiente
- `teal-*` / `cyan-*` — evangelismo, comunidad

**Nunca** `indigo-*`, `violet-*`, `purple-*` aunque sea decorativo.

**Variables semánticas disponibles:**
| Variable | Uso |
|---|---|
| `--surface-1` | Fondo de panel/card principal |
| `--surface-2` | Fondo secundario (inputs, toolbars) |
| `--surface-3` | Fondo terciario (zonas de drop/borde punteado) |
| `--border` | Color de bordes |
| `--text-primary` | Texto principal |
| `--text-secondary` | Texto secundario / metadata |
| `--primary` | Color primario de acción / acento |
| `--secondary` | Color secundario |

### 5. Carga Perezosa por Pestañas (Lazy Loading)

El perfil de una persona **nunca** se carga completo en una sola petición. Las secciones se dividen en tabs independientes:

```tsx
// ✅ CORRECTO
<Tabs>
  <Tab label="CRM" onSelect={() => fetchCrmCasos(personaId)} />
  <Tab label="Academia" onSelect={() => fetchAcademy(personaId)} />
  <Tab label="Proyectos" onSelect={() => fetchProyectos(personaId)} />
  <Tab label="Agenda" onSelect={() => fetchAgenda(personaId)} />
</Tabs>

// ❌ INCORRECTO
fetch(`/api/personas/${personaId}/full-profile`)
```

### 6. Cero Modales de Creación

**Regla:** La creación de recursos (personas, grupos, casos, cursos, proyectos, tareas) se hace desde la página del módulo correspondiente con un Drawer lateral o redirigiendo a una página dedicada.

**Prohibido:**
- `UniversalCreationModal.tsx` — cualquier modal de creación debe ser reemplazado por un Drawer o página
- Modales tipo "Crear nueva persona", "Añadir grupo", "Nuevo proyecto"

### 7. Convención de Rutas

Todas las rutas de plataforma siguen:

```
/plataforma/{modulo}[/{submodulo}][/{id}]
```

| Ruta | Propósito |
|---|---|
| `/plataforma/personas` | Directorio de personas (kernel) |
| `/plataforma/community/grupos` | Grupos pequeños / vida comunitaria |
| `/plataforma/evangelism/grupos` | Grupos de evangelismo |
| `/plataforma/crm` | CRM |
| `/plataforma/academy` | Academia |
| `/plataforma/groups` | Grupos (vista consolidada) |
| `/plataforma/proyectos` | Proyectos |

### 8. Prefijo de API

Todas las llamadas al backend usan `apiFetch('/endpoint')` de `@/lib/http`:

```tsx
import { apiFetch } from '@/lib/http';

// GET
const data = await apiFetch('/grupos');

// POST
const result = await apiFetch('/grupos', {
  method: 'POST',
  body: JSON.stringify(payload),
});
```

### 9. Sistema de Diseño (Design System)

Usar los componentes del sistema de diseño en `frontend/src/design/components/`:

| Componente | Uso | Ejemplo |
|---|---|---|
| `DSButton` | Botones (primary, secondary, ghost) | `<DSButton variant="primary">Guardar</DSButton>` |
| `DSBadge` | Etiquetas / badges (slate, blue, emerald, amber) | `<DSBadge tone="emerald" label="Activo" />` |
| `DSCard` | Cards contenedoras (light, dark, glass) | `<DSCard tone="dark">...</DSCard>` |
| `DSMetric` | Métricas / KPIs para dashboards | `<DSMetric label="Usuarios" value="1,248" />` |
| `DSChart` | Gráficos (line, area, bar) con Recharts | `<DSChart type="bar" data={data} />` |
| `DSInput` | Inputs con label, error, helper, icon | `<DSInput label="Email" error="Requerido" />` |
| `DSSelect` | Selects nativos estilizados | `<DSSelect label="País" options={options} />` |
| `DSModal` | Modales con backdrop, focus trap, Escape | `<DSModal open={isOpen} title="Confirmar">` |
| `DSTable` | Tablas con sorting (TanStack Table) | `<DSTable data={data} columns={columns} />` |
| `DSTabs` | Navegación por pestañas | `<DSTabs tabs={tabs}>...</DSTabs>` |
| `DSTooltip` | Tooltips con Radix UI | `<DSTooltip content="Info"><button>` |
| `DSToast` | Notificaciones toast | `toast.success("Guardado")` |
| `DSSkeleton` | Estados de carga / skeleton screens | `<DSSkeleton className="h-4 w-full" />` |
| `DSSectionHeader` | Encabezados de sección con acciones | `<DSSectionHeader title="Título" />` |
| `DSToolbarChip` | Chips de toolbar / filtros | `<DSToolbarChip label="Activos" />` |
| `DSCommandEntry` | Entradas de command palette | `<DSCommandEntry label="Ir a CRM" />` |

**Importar desde `@/design`:**
```tsx
import { DSButton, DSCard, DSInput, DSModal } from '@/design';
```

**Documentación completa:** `frontend/src/design/README.md`

### 10. Manejo de Estado (Zustand)

| Store | Propósito |
|---|---|
| `authStore` | Sesión del usuario |
| `sidebarStore` | Estado del sidebar / drawers |
| `configStore` | Configuración global |
| `toastStore` | Notificaciones toast |

---

## 📁 Estructura de Archivos

```
frontend/src/
├── app/
│   ├── (public)/              # Landing público (sin auth)
│   ├── plataforma/            # App con autenticación
│   │   ├── academy/           # Módulo de academia
│   │   ├── admin/             # Administración
│   │   ├── community/         # Comunidad (grupos, oración, etc.)
│   │   ├── crm/               # CRM
│   │   ├── evangelism/        # Evangelismo
│   │   ├── groups/            # Grupos (consolidado)
│   │   ├── personas/          # Directorio de personas
│   │   └── proyectos/         # Proyectos
│   ├── auth/                  # Auth pages
│   └── layout.tsx
├── components/                # Componentes reutilizables
│   ├── community/             # Componentes de comunidad
│   ├── public/                # Componentes públicos
│   ├── ui/                    # UI atómicos (RightPanel, DataTable, etc.)
│   └── wiki/                  # Wiki components
├── context/                   # Contextos React
├── design/                    # Design System
│   └── components/            # Componentes del DS
├── hooks/                     # Custom hooks
├── lib/                       # Utilidades y API
├── stores/                    # Zustand stores
└── types/                     # TypeScript types
```

---

## ✅ Checklist Pre-Commit (Frontend)

- [ ] 1. ¿Usé `bg-[hsl(var(--surface-*))]` en vez de colores fijos?
- [ ] 2. ¿Evité modales (`<Dialog>`) para crear/editar/ver detalles?
- [ ] 3. ¿Usé Drawer lateral para contenido detallado?
- [ ] 4. ¿Llamé a la API con `apiFetch` (no fetch directo)?
- [ ] 5. ¿Las rutas siguen `/plataforma/{modulo}`?
- [ ] 6. ¿Evité la palabra "miembro" en la UI cuando me refiero a personas?
- [ ] 7. ¿Cargo datos por pestañas (lazy loading) en perfiles?
- [ ] 8. ¿Usé tokens semánticos (`--primary`, `--border`, etc.)?
- [ ] 9. ¿Usé `DSButton` / `DSCard` del design system donde aplica?
- [ ] 10. ¿El módulo nuevo está registrado en el layout de plataforma?
- [ ] 11. **¿El código tiene `indigo`, `violet` o `purple`?** Si hay alguno → BLOQUEADO. Reemplazar por `hsl(var(--primary))` o `blue-*`.

---

> **"El frontend no es decoración; es la capa que traduce la arquitectura en experiencia. Cada componente debe reflejar las reglas del kernel."**
> — Diseño CCF
