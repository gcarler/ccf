# 📖 Glosario Rápido de Frontend CCF

**Para usar cuando un agente de IA toque el frontend.**

## Términos Correctos en UI

| Contexto | Término UI correcto | Evitar |
|---|---|---|
| Cualquier persona en el sistema | persona, integrante, participante | termino heredado |
| Grupo pequeño comunitario | Grupo Pequeño / Comunidad | Cell Group, Célula |
| Grupo de evangelismo | Grupo de Evangelismo / Casa de Gloria | nombres heredados en inglés |
| Líder de grupo | Líder | no hay tabla "líderes" |
| Cantidad de personas en grupo | total_personas, Integrantes | conteo heredado |
| Usuario de la plataforma | usuario (solo para login) | no confundir con persona |

## Convenciones de UI

- **Drawers laterales** para detalles (nunca modales)
- **Tokens semánticos** para colores (nunca colores fijos)
- **Carga por pestañas** en perfiles (nunca full-profile)
- **apiFetch** para llamadas API (nunca fetch directo)
- **Rutas** siempre bajo `/plataforma/{modulo}`
- **DS Components** del design system (ver tabla abajo)

## DS Components - Design System

Importar desde `@/design`:

| Componente | Uso principal | Variantes |
|---|---|---|
| `DSButton` | Acciones | primary, secondary, ghost |
| `DSBadge` | Estados | slate, blue, emerald, amber |
| `DSCard` | Contenedores | light, dark, glass |
| `DSMetric` | KPIs | blue, emerald, amber |
| `DSChart` | Gráficos | line, area, bar |
| `DSInput` | Formularios | con label, error, icon |
| `DSSelect` | Formularios | con label, placeholder |
| `DSModal` | Diálogos | sm, md, lg |
| `DSTable` | Listas | con sorting |
| `DSTabs` | Navegación | con icons |
| `DSTooltip` | Info hover | top, right, bottom, left |
| `DSToast` | Notificaciones | success, error, warning, info |
| `DSSkeleton` | Loading | sm, md, lg, xl, pill |
| `DSSectionHeader` | Títulos | left, center |
| `DSToolbarChip` | Filtros | soft, solid, outline |
| `DSCommandEntry` | Command palette | active, inactive |

## Utilidades compartidas (`@/lib`)

| Utilidad | Uso | Import |
|---|---|---|
| `filtroAPersonas(name, query)` | Filtro reutilizable de búsqueda de personas: normaliza acentos/case/espacios; una palabra casa con nombre o apellido ("meza" encuentra "Luis Ricardo Meza") y varias palabras por subsecuencia ("juan meza" encuentra "Juan Luis Meza"). Query vacío → true. | `import { filtroAPersonas } from '@/lib/filtroAPersonas'` |
| `filtroAPersona(persona, query)` | Búsqueda sobre una persona completa. Con `@` inicial → busca por **username** de la cuenta (estilo mensajería: `@gscarlosernesto`). Sin `@` → nombre/apellido, email, teléfonos, documento y rol. Reemplaza el patrón `filtroAPersonas(...) || normalizar(email).includes(...) || ...` repetido en cada pantalla. | `import { filtroAPersona } from '@/lib/filtroAPersonas'` |
| `normalizarBusquedaPersona(value)` | Normaliza un texto para comparación (minúsculas, sin acentos, espacios simples). Con cache interno acotado. | `import { normalizarBusquedaPersona } from '@/lib/filtroAPersonas'` |

> **Regla:** al buscar personas en cualquier módulo, usar `filtroAPersona(persona, query)` (o `filtroAPersonas` solo para nombre) — no escribir filtros propios con `startsWith`/`includes` (pierden acentos y nombres compuestos).

## Menciones estilo mensajería

| Componente | Uso | Import |
|---|---|---|
| `PersonaMentionInput` | Input con mención de **usuarios** estilo mensajería: escribes `@gscarlosernesto` → dropdown con usernames que coinciden → Enter/clic inserta `@username `. Con navegación por flechas, Escape y dedupe de menciones. | `import PersonaMentionInput from '@/components/ui/PersonaMentionInput'` |

## Regla de oro

> Si el backend dice "personas", el frontend dice "personas".
> Nunca inventes términos que no existen en el kernel.
