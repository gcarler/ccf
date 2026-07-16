# Politica de UI Base Protegida — Plataforma Compartida

## 1. Proposito

Este documento fija la superficie UI compartida que no puede tratarse como cambio local de modulo. Su objetivo es cortar regresiones redundantes: cuando se toca layout, grids o editores reutilizados, el owner real es plataforma compartida.

## 2. Superficie protegida

### 2.1. Shell de plataforma

- `frontend/src/components/WorkspaceLayout.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/components/WorkspaceMainSidebar.tsx`
- `frontend/src/components/WorkspaceMiniSidebar.tsx`
- `frontend/src/lib/workspaceAccess.ts`
- `frontend/src/lib/protectedRouteAccess.ts`
- `frontend/src/components/WorkspaceToolbar.tsx`
- `frontend/src/components/WorkspaceInbox.tsx`

Contrato:

- `WorkspaceLayout` es el shell de `/plataforma/**`.
- Resuelve permisos por ruta y filtra navegacion via `hasModuleAccess(...)`.
- `ProtectedRoute` debe gatear por `allowedPermissions` cuando el modulo ya tiene permiso canónico; `allowedRoles` queda solo para compatibilidad legacy.
- El filtrado de rutas del shell y del mini sidebar debe salir de `frontend/src/lib/workspaceAccess.ts`, no de mapas locales duplicados.
- Persiste estado de sidebars y focus mode en `localStorage`.
- Coordina capas `S1` y `S2`; romper esta logica impacta CRM, Projects, Evangelism, Agenda, Academy, CMS, Community y Admin.

### 2.2. Primitivas de datos reutilizadas

- `frontend/src/components/ui/TableView.tsx`
- `frontend/src/components/ui/UniversalTableView.tsx`
- `frontend/src/components/ui/UniversalCalendarView.tsx`
- `frontend/src/components/ui/UniversalGanttView.tsx`
- `frontend/src/components/ui/inline-editors/*.tsx`

Contrato:

- `TableView` y `UniversalTableView` son primitives cross-modulo para vistas tabulares.
- `UniversalCalendarView` y `UniversalGanttView` son primitives compartidas para vistas temporales.
- `inline-editors` define comportamiento de edicion embebida que otros modulos consumen como contrato visual y funcional.

### 2.3. AG Grid como dependencia compartida

Archivos observados el `2026-07-16`:

- `frontend/src/lib/agGrid.ts`
- `frontend/src/components/ui/TableView.tsx`
- `frontend/src/components/ui/UniversalTableView.tsx`
- `frontend/src/components/projects/ProjectTableView.tsx`
- `frontend/src/components/projects/TaskTableView.tsx`
- `frontend/src/components/crm/CrmTableView.tsx`
- `frontend/src/components/crm/CrmViews.tsx`

Contrato:

- La plataforma usa `themeQuartz` y registra `AllCommunityModule` una sola vez desde `frontend/src/lib/agGrid.ts`.
- No se debe mezclar Theming API con CSS legacy de AG Grid en la misma pagina.
- No se aprueba codigo nuevo que reintroduzca `ag-grid.css` o temas legacy de clase.
- La inicializacion de modulos AG Grid se considera parte del contrato compartido porque una falla deja grids completos sin renderizar.
- Los wrappers por modulo no deben volver a llamar `ModuleRegistry.registerModules(...)` directamente.

## 3. Regla de clasificacion

Se clasifica como cambio de plataforma compartida si toca cualquiera de estos puntos:

- layout, sidebars, toolbar, overlays o focus mode de `WorkspaceLayout`
- permisos o filtrado de navegacion dentro del shell
- tablas base o sus temas AG Grid
- edicion inline reutilizada por mas de un modulo
- componentes de calendario o gantt reutilizados por mas de un modulo

No clasificar como cambio local aunque el bug se vea solo en una ruta. Si nace aqui, el owner es plataforma.

## 4. Flujo obligatorio de cambio

1. leer `ESTADO_PLATAFORMA_COMPARTIDA.md`
2. leer este documento
3. identificar modulos consumidores impactados
4. editar la primitive compartida o aislar una wrapper por modulo si el comportamiento no debe ser global
5. correr validacion canonica de plataforma
6. revisar manualmente al menos CRM, Projects y Evangelism

## 5. Validacion minima obligatoria

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
cd /root/ccf/frontend && npm run build
```

Checks manuales minimos:

- `/plataforma/crm/personas`
- `/plataforma/projects`
- `/plataforma/evangelism`

Si el cambio toca `WorkspaceLayout`, validar ademas una ruta con sidebar protegida por permisos:

- `/plataforma/admin`
- `/plataforma/community`
- `/plataforma/spiritual-life`

## 6. Anti-patrones prohibidos

- arreglar un modulo duplicando una primitive compartida
- cambiar `WorkspaceLayout` para resolver un caso local sin medir impacto global
- registrar AG Grid de forma inconsistente entre pantallas
- mezclar `themeQuartz` con `ag-grid.css` o themes legacy
- cambiar `inline-editors` sin revisar consumidores existentes

## 7. Criterio de salida

`PEND-UI-BASE-001` se considera cerrado cuando:

- la superficie protegida queda documentada
- el owner de plataforma queda explicito
- la validacion minima queda definida
- el plan modular y los handovers enlazan esta politica

Estado:

- `PEND-UI-BASE-001` cerrada el `2026-07-16` con este documento y referencias cruzadas en la capa de plataforma compartida.
