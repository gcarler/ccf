# 📖 Glosario Rápido de Frontend CCF

**Para usar cuando un agente de IA toque el frontend.**

## Términos Correctos en UI

| Contexto | Término UI correcto | Evitar |
|---|---|---|
| Cualquier persona en el sistema | persona, integrante, participante | miembro, member |
| Grupo pequeño comunitario | Grupo Pequeño / Comunidad | Cell Group, Célula |
| Grupo de evangelismo | Grupo de Evangelismo / Casa de Gloria | nombres heredados en inglés |
| Líder de grupo | Líder | no hay tabla "líderes" |
| Cantidad de personas en grupo | total_personas, Integrantes | members_count, Miembros |
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

## Regla de oro

> Si el backend dice "personas", el frontend dice "personas". 
> Nunca inventes términos que no existen en el kernel.
