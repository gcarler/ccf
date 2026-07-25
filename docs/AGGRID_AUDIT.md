# Auditoría Técnica: Configuración de AG Grid en la Plataforma CCF

**Fecha de auditoría:** 2026-07-25  
**Autor:** Buffy (Freebuff)  
**Módulo afectado:** Frontend — Plataforma CCF (Proyectos, CRM, UI genérica)  
**Estado:** Consolidación implementada y validada  

---

## 1. Resumen Ejecutivo

Se realizó una auditoría completa del uso de **AG Grid** en la plataforma frontend. Se encontró que cada componente que renderizaba una tabla definía su propio tema (`themeQuartz.withParams()`), duplicaba la detección de modo oscuro mediante `MutationObserver` yendo directamente al DOM, e importaba `AgGridReact` desde `ag-grid-react` en lugar de consumir un componente del **design system**. Esto generaba inconsistencias visuales, deuda técnica y riesgo de fugas de rendimiento.

Se ejecutó un plan de consolidación que centraliza:
- El tema en `frontend/src/design/agGridTheme.ts`.
- La detección de modo oscuro en `frontend/src/hooks/useDarkMode.ts`.
- Un wrapper genérico en `frontend/src/components/ui/AgGridTable.tsx`.
- La refactorización de todos los consumidores directos en `projects/`, `crm/` y `components/ui/`.

### Resultado clave
- **0 imports directos** a `ag-grid-community`/`ag-grid-react` en los archivos refactorizados del dominio.
- **Tests unitarios:** 18/18 pasaron en los archivos de prueba relacionados.
- **TypeScript:** solo errores pre-existentes, ninguno introducido por la refactorización.

---

## 2. Alcance

La auditoría cubrió todos los archivos frontend que instancian `AgGridReact` o importan tipos de AG Grid:

- `frontend/src/components/ui/TableView.tsx`
- `frontend/src/components/ui/UniversalTableView.tsx`
- `frontend/src/components/projects/ProjectTableView.tsx`
- `frontend/src/components/projects/TaskTableView.tsx`
- `frontend/src/components/projects/TitleCellEditor.tsx`
- `frontend/src/components/crm/CrmTableView.tsx`
- `frontend/src/components/crm/CrmViews.tsx`
- `frontend/src/lib/agGrid.ts`
- `frontend/src/design/tokens-semantic.ts`

---

## 3. Hallazgos

### H-1. Fragmentación de definiciones de tema

Se identificaron **cuatro (4) definiciones independientes** de `themeQuartz.withParams()`:

| Archivo | Definición | Problema |
| --- | --- | --- |
| `frontend/src/components/ui/TableView.tsx` | Tema inline para light/dark | Colores hardcodeados (`#ffffff`, `#1e293b`, `rgb(15 23 42)`, `#64748b`) |
| `frontend/src/components/ui/UniversalTableView.tsx` | Tema inline para light/dark | Colores hardcodeados similares |
| `frontend/src/lib/projects/agGridTheme.ts` | Tema específico de Proyectos | Usaba CSS vars que `themeQuartz` no resuelve siempre |
| `frontend/src/components/crm/CrmTableView.tsx` y `CrmViews.tsx` | Temas inline por módulo | Inconsistencia con tokens del design system |

**Impacto:** Cualquier cambio de diseño requería editar múltiples archivos. Los colores hardcodeados rompían la coherencia en modo oscuro o con temas personalizados.

### H-2. Duplicación de observadores de modo oscuro

Cada instancia de tabla instanciaba su propio `MutationObserver` para escuchar cambios de clase `dark` en `document.documentElement`.

```tsx
const observer = new MutationObserver(callback);
observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
```

**Impacto:** Sobrecarga innecesaria en vistas con varias tablas y riesgo real de fugas de memoria si el componente no limpiaba correctamente el observador.

### H-3. Imports directos a paquetes de AG Grid desde componentes de dominio

Los componentes de `projects/` y `crm/` importaban directamente:

```tsx
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';
```

**Impacto:** Se rompía la capa de abstracción del design system. No había un único punto de control para versiones, licencias o temas.

### H-4. Falta de wrapper tipo-safe

No existía un componente `DataTable` / `AgGridTable` que encapsulara:
- Registro de módulos (`frontend/src/lib/agGrid.ts`).
- Aplicación automática del tema.
- Forwarding de `ref` hacia `AgGridReact`.
- Preservación del tipo genérico `TData`.

**Impacto:** Cada consumidor repetía la misma configuración. Los callbacks como `getRowId` o `onRowClicked` perdían tipado porque no había forma de pasar `TData` a través de `forwardRef` sin un wrapper genérico.

### H-5. Uso inconsistente de tokens semánticos

Los temas inline usaban colores literales en lugar de los tokens del design system (`semanticColorsLight` / `semanticColorsDark`). Algunos valores mezclaban `hsla(...)` con variables CSS mal soportadas por AG Grid, por ejemplo:

```tsx
selectedRowBackgroundColor: 'hsla(var(--primary-hsl),0.15)'
```

**Impacto:** `themeQuartz.withParams()` no resuelve de forma confiable las CSS custom properties. Esto podía generar diferencias visuales entre entornos o modos.

### H-6. Densidades no normalizadas

Cada tabla definía su propia altura de fila (`rowHeight`) sin una escala común (`compact` / `default` / `comfortable`).

---

## 4. Riesgos Técnicos

| ID | Riesgo | Probabilidad | Impacto | Descripción |
| --- | --- | --- | --- | --- |
| R-1 | Inconsistencia visual | Alta | Medio | Cada tabla podía verse diferente si se editaban temas de forma aislada. |
| R-2 | Fuga de observadores | Media | Medio | Múltiples `MutationObserver` sin centralizar podían acumularse. |
| R-3 | Deuda de mantenimiento | Alta | Medio | Cambiar un color o actualizar AG Grid requería tocar N archivos. |
| R-4 | Problemas de licenciamiento | Baja | Alto | Al no existir un wrapper central, era difícil garantizar el registro correcto de módulos y la futura inclusión de licencias enterprise. |
| R-5 | Pérdida de tipado genérico | Alta | Bajo | Sin wrapper genérico, `data` en callbacks era `unknown`, reduciendo la experiencia de desarrollo. |
| R-6 | SSR / hidratación | Media | Bajo | La detección de tema oscuro desde el DOM podía generar discrepancias entre servidor y cliente. |

---

## 5. Plan de Trabajo Detallado

### Fase 1 — Diagnóstico y contexto
- [x] Leer todos los componentes que usan `AgGridReact`.
- [x] Buscar imports directos a `ag-grid-community` / `ag-grid-react`.
- [x] Revisar `package.json` para confirmar versiones y paquetes instalados.
- [x] Analizar `frontend/src/lib/agGrid.ts` y `frontend/src/design/tokens-semantic.ts`.

### Fase 2 — Diseño de la arquitectura consolidada
- [x] Definir un **único archivo de temas** en el design system: `frontend/src/design/agGridTheme.ts`.
- [x] Definir un **hook centralizado** de modo oscuro: `frontend/src/hooks/useDarkMode.ts`.
- [x] Definir un **wrapper genérico** tipo-safe: `frontend/src/components/ui/AgGridTable.tsx`.
- [x] Establecer la escala de densidad: `compact` (36 px), `default` (40 px), `comfortable` (44 px).

### Fase 3 — Implementación
- [x] Crear `frontend/src/hooks/useDarkMode.ts`.
- [x] Crear `frontend/src/design/agGridTheme.ts` usando tokens semánticos.
- [x] Crear `frontend/src/components/ui/AgGridTable.tsx` con `forwardRef` genérico.
- [x] Refactorizar `frontend/src/components/ui/TableView.tsx`.
- [x] Refactorizar `frontend/src/components/ui/UniversalTableView.tsx`.
- [x] Refactorizar `frontend/src/components/projects/ProjectTableView.tsx`.
- [x] Refactorizar `frontend/src/components/projects/TaskTableView.tsx`.
- [x] Refactorizar `frontend/src/components/projects/TitleCellEditor.tsx`.
- [x] Refactorizar `frontend/src/components/crm/CrmTableView.tsx`.
- [x] Refactorizar `frontend/src/components/crm/CrmViews.tsx`.
- [x] Deprecar `frontend/src/lib/projects/agGridTheme.ts` como re-exportador.
- [x] Exportar el tema desde `frontend/src/design/index.ts`.

### Fase 4 — Validación
- [x] Ejecutar `tsc --noEmit` y confirmar que los errores restantes son pre-existentes.
- [x] Ejecutar tests unitarios de componentes AG Grid.
- [x] Verificar que no quedan imports directos a `ag-grid-community`/`ag-grid-react` en componentes de dominio.

### Fase 5 — Revisión cruzada
- [x] Revisión por `code-reviewer-kimi` para detectar fragilidades en el wrapper genérico y la abstracción del design system.

---

## 6. Arquitectura Resultante

### 6.1 `useDarkMode.ts`

Hook centralizado basado en `useSyncExternalStore` que:
- Suscríbe a cambios de la clase `dark` en `<html>`.
- Fallback a `data-theme="night"` para compatibilidad con ambos proveedores de tema.
- Devuelve un booleano usable por el resto de la aplicación.
- Es SSR-safe: en servidor devuelve `false`.

### 6.2 `design/agGridTheme.ts`

Fábrica de temas `themeQuartz` construida exclusivamente desde los tokens semánticos del design system (`semanticColorsLight`, `semanticColorsDark`). No usa variables CSS directamente porque `themeQuartz.withParams` no las resuelve de forma confiable.

Soporta densidades:
- `compact`: 36 px
- `default`: 40 px
- `comfortable`: 44 px

### 6.3 `components/ui/AgGridTable.tsx`

Wrapper genérico alrededor de `AgGridReact` que:
- Aplica el tema del design system automáticamente.
- Garantiza el registro único de módulos AG Grid.
- Reenvía `ref` para que los consumidores sigan usando `gridRef` como antes.
- Preserva el tipo genérico `TData` en callbacks (`getRowId`, `onRowClicked`, etc.).
- Re-exporta los tipos más usados de `ag-grid-community` para evitar imports directos.

Ejemplo de uso:

```tsx
import AgGridTable, { ColDef, type AgGridTableRef } from '@/components/ui/AgGridTable';

const gridRef = useRef<AgGridTableRef>(null);

<AgGridTable<MyRow>
  ref={gridRef}
  density="compact"
  rowData={rows}
  columnDefs={columns}
  getRowId={(params) => params.data.id}
  onRowClicked={(e) => console.log(e.data.name)}
/>
```

---

## 7. Archivos Afectados

### Nuevos archivos
| Archivo | Responsabilidad |
| --- | --- |
| `frontend/src/hooks/useDarkMode.ts` | Detección centralizada de modo oscuro |
| `frontend/src/design/agGridTheme.ts` | Fábrica de temas AG Grid con tokens semánticos |
| `frontend/src/components/ui/AgGridTable.tsx` | Wrapper genérico tipo-safe de `AgGridReact` |

### Archivos refactorizados
| Archivo | Cambio principal |
| --- | --- |
| `frontend/src/components/ui/TableView.tsx` | Usa `AgGridTable`; elimina tema inline y observador duplicado |
| `frontend/src/components/ui/UniversalTableView.tsx` | Usa `AgGridTable`; elimina tema inline y observador duplicado |
| `frontend/src/components/projects/ProjectTableView.tsx` | Usa `AgGridTable`; importa tipos desde el wrapper |
| `frontend/src/components/projects/TaskTableView.tsx` | Usa `AgGridTable`; importa tipos desde el wrapper |
| `frontend/src/components/projects/TitleCellEditor.tsx` | Importa `ICellEditorParams` desde el wrapper |
| `frontend/src/components/crm/CrmTableView.tsx` | Usa `AgGridTable`; elimina tema inline |
| `frontend/src/components/crm/CrmViews.tsx` | Usa `AgGridTable`; elimina tema inline |

### Archivos modificados de soporte
| Archivo | Cambio |
| --- | --- |
| `frontend/src/design/index.ts` | Exporta `agGridTheme` |

### Archivos eliminados
| Archivo | Motivo | Eliminado |
| --- | --- | --- |
| `frontend/src/lib/projects/agGridTheme.ts` | Re-exportador deprecado; ya no había imports y el tema canonical vive en `design/agGridTheme` | 2026-07-25 |

---

## 8. Resultados de Validación

| Validación | Resultado |
| --- | --- |
| Tests unitarios AG Grid (4 suites) | **18/18 passed** |
| `npx tsc --noEmit` | Errores pre-existentes no relacionados; ninguno nuevo introducido |
| Imports directos a `ag-grid-*` en dominio | **0** |
| Observadores duplicados de modo oscuro | **Eliminados** |
| Definiciones de `themeQuartz.withParams` | Reducidas a **1** (`design/agGridTheme.ts`) |

### Errores de TypeScript pre-existentes
La auditoría no introdujo errores, pero el proyecto mantiene algunos problemas heredados que no pertenecen al alcance de esta refactorización, por ejemplo:
- `toHaveNoViolations` no tipado en tests de accesibilidad.
- Tipo `readonly RegExp[]` en algunas definiciones de ruta.
- Uso de `Page` no importado en tests E2E.

Estos deben abordarse en una auditoría transversal de TypeScript.

---

## 9. Recomendaciones Futuras

1. **Migrar a React 19:** cuando el proyecto soporte React 19, simplificar `AgGridTable.tsx` usando `ref` como prop directa en lugar del patrón `forwardRef` + cast.
2. **Auditar licenciamiento:** confirmar si se requiere `ag-grid-enterprise` en algún módulo futuro y centralizar la licencia en `frontend/src/lib/agGrid.ts`.
3. **Tests de regresión visual:** agregar screenshots de Storybook o Playwright para las tablas en modo claro y oscuro.
4. **Documentar Storybook:** crear stories de `AgGridTable` y `UniversalTableView` para el design system.
5. ~~**Eliminar re-exportador deprecado:**~~ ✅ Completado. Se eliminó `frontend/src/lib/projects/agGridTheme.ts` después de confirmar que no tenía imports activos; el tema canonical es `frontend/src/design/agGridTheme.ts`.
6. **Auditar accesibilidad:** verificar que los renderers personalizados (`StatusCell`, `ProgressCell`, `CheckboxRenderer`, etc.) tengan `aria-label` o texto oculto adecuado para lectores de pantalla.

---

## 10. Conclusión

La consolidación de AG Grid en la plataforma CCF eliminó la fragmentación de temas, centralizó la detección de modo oscuro y estableció un wrapper tipo-safe en el design system. Esto reduce la deuda técnica, mejora la coherencia visual y facilita futuras actualizaciones de AG Grid o del sistema de diseño.

**Estado de la auditoría:** Cerrada con éxito.  
**Próximo paso recomendado:** ejecutar la auditoría transversal de TypeScript y agregar tests de regresión visual en Storybook.
