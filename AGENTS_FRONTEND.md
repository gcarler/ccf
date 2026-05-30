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

### 2. Glory Houses → Grupos de Evangelismo / Casas de Gloria

El concepto "Glory House" o "Casa de Gloria" en la UI debe presentarse como **Grupo de Evangelismo** o **Casa de Gloria**, dependiendo del contexto. En inglés técnico puede persistir `glory_houses` en la DB, pero el frontend etiqueta:

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

**Prohibido** usar colores fijos de Tailwind (`bg-blue-500`, `border-gray-200`, `text-gray-800`) en componentes del sistema.

Usar exclusivamente variables CSS semánticas:

```tsx
// ✅ CORRECTO
<div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))]" />
<button className="bg-[hsl(var(--primary))] text-white" />

// ❌ INCORRECTO
<div className="bg-white border border-gray-200 text-gray-800" />
<button className="bg-blue-500 text-white" />
```

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
const data = await apiFetch('/api/grupos');

// POST
const result = await apiFetch('/api/grupos', {
  method: 'POST',
  body: JSON.stringify(payload),
});
```

### 9. Sistema de Diseño (Design System)

Usar los componentes del sistema de diseño en `frontend/src/design/components/`:

| Componente | Uso |
|---|---|
| `DSButton` | Botones principales |
| `DSBadge` | Etiquetas / badges |
| `DSCard` | Cards contenedoras |
| `DSMetric` | Métricas / KPIs |
| `DSSkeleton` | Estados de carga |
| `DSSectionHeader` | Encabezados de sección |
| `DSToolbarChip` | Chips de toolbar |
| `DSCommandEntry` | Entrada de comando |

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

---

> **"El frontend no es decoración; es la capa que traduce la arquitectura en experiencia. Cada componente debe reflejar las reglas del kernel."**
> — Diseño CCF
