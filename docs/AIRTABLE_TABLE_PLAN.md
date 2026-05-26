# Airtable-like Table — Plan de Trabajo Completo

**Fecha:** 2026-05-25  
**Objetivo:** Tabla 100% funcional como Airtable en toda la plataforma  
**Estado actual:** 3 componentes de tabla (UniversalTableView, TaskTableView, DataTable) — ninguno al nivel Airtable

---

## 📊 Estado Actual vs Airtable

| Feature | Airtable | Nosotros | Gap |
|---------|----------|----------|-----|
| Edición inline por celda | ✅ Click → editar | ⚠️ Solo TaskTableView | 🔴 |
| Resize de columnas (drag) | ✅ | ❌ | 🔴 |
| Reordenar columnas (drag) | ✅ | ❌ | 🔴 |
| Reordenar filas (drag) | ✅ | ❌ | 🔴 |
| Tipos de celda (16+) | ✅ | 9 tipos básicos | 🟡 |
| Filtros con operadores | ✅ (contiene, es, vacío, >, <) | ❌ Solo texto | 🔴 |
| Agrupar por múltiples | ✅ | ⚠️ Solo 1 columna | 🟡 |
| Multi-column sort | ✅ | ✅ | ✅ |
| Bulk edit | ✅ | ⚠️ UI placeholder | 🔴 |
| Vistas guardadas por usuario | ✅ | ❌ | 🔴 |
| Formato condicional | ✅ | ❌ | 🔴 |
| Celdas de relación (link to record) | ✅ | ❌ | 🔴 |
| Fórmulas | ✅ | ❌ | 🔴 |
| Rollup / Lookup | ✅ | ❌ | 🔴 |
| Undo/Redo | ✅ | ⚠️ Botones no funcionales | 🔴 |
| Navegación teclado (arrow keys) | ✅ | ❌ | 🔴 |
| Copy/paste entre celdas | ✅ | ❌ | 🔴 |
| Congelar columnas | ✅ | ❌ | 🔴 |
| Virtualización (>1000 filas) | ✅ | ❌ | 🔴 |
| Historial/auditoría de celda | ✅ | ❌ | 🔴 |
| Crear campo desde tabla ("+ Columna") | ✅ | ⚠️ Botón no funcional | 🔴 |
| Comentarios en celda | ✅ | ❌ | 🔴 |
| Attachments en celda | ✅ | ❌ | 🔴 |

---

## 🏗️ Arquitectura Propuesta

### Stack Técnico
- **Motor:** `@tanstack/react-table` (ya instalado) — reemplazar tablas manuales
- **Virtualización:** `@tanstack/react-virtual` (nuevo) — para >1000 filas
- **Drag & Drop:** `@dnd-kit/core` + `@dnd-kit/sortable` (ya instalados) — columnas y filas
- **Popovers:** `@radix-ui/react-popover` (ya instalado) — celdas editables
- **Comando:** `cmdk` (ya instalado) — command palette para edición
- **Animación:** `framer-motion` (ya instalado) — transiciones

### Componentes Nuevos

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| `AirTableView<T>` | `components/ui/AirTableView.tsx` | Componente principal, motor TanStack |
| `AirTableCell<T>` | `components/ui/AirTableCell.tsx` | Celda editable genérica |
| `AirTableCellTypes/` | `components/ui/AirTableCellTypes/` | 16 tipos de celda |
| `AirTableToolbar` | `components/ui/AirTableToolbar.tsx` | Toolbar con filtros, agrupación, columnas |
| `AirTableHeader` | `components/ui/AirTableHeader.tsx` | Header con resize, drag, freeze |
| `AirTableGroupRow` | `components/ui/AirTableGroupRow.tsx` | Fila de grupo colapsable |
| `AirTableBulkBar` | `components/ui/AirTableBulkBar.tsx` | Barra de acciones masivas |
| `useAirTable` | `hooks/useAirTable.ts` | Hook principal con undo/redo, optimistic |
| `useColumnResize` | `hooks/useColumnResize.ts` | Hook para resize con drag |
| `useKeyboardNav` | `hooks/useKeyboardNav.ts` | Navegación tipo spreadsheet |
| `useCellHistory` | `hooks/useCellHistory.ts` | Historial de cambios por celda |
| `tableContext` | `context/tableContext.tsx` | Contexto compartido para celdas |

---

## 📋 Plan de Implementación por Fases

### Fase 1: Cimientos — Motor TanStack + Tipos de Celda (4h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 1.1 | Instalar `@tanstack/react-virtual` | `package.json` | Baja |
| 1.2 | Crear `AirTableView` — motor TanStack completo | `components/ui/AirTableView.tsx` | Alta |
| 1.3 | Crear `AirTableCell` genérico con edición | `components/ui/AirTableCell.tsx` | Alta |
| 1.4 | **Tipos de celda** (16 tipos): | `components/ui/AirTableCellTypes/` | Alta |
| | `TextCell` — texto multilinea | | Media |
| | `NumberCell` — numérico con formato | | Media |
| | `SelectCell` — single select con popover | | Media |
| | `MultiSelectCell` — multi select con tags | | Media |
| | `DateCell` — date picker inline | | Media |
| | `DateTimeCell` — date + time | | Media |
| | `CheckboxCell` — toggle checkbox | | Baja |
| | `RatingCell` — estrellas 1-5 | | Baja |
| | `PhoneCell` — formato teléfono | | Baja |
| | `EmailCell` — link mailto | | Baja |
| | `URLCell` — link externo | | Baja |
| | `UserCell` — persona (usar UserPicker) | | Media |
| | `RelationCell` — link a otro registro | | Alta |
| | `AttachmentCell` — archivos (usar upload) | | Alta |
| | `FormulaCell` — readonly, calculado | | Alta |
| | `RollupCell` — agregado de relación | | Alta |
| 1.5 | Crear `tableContext` para compartir estado | `context/tableContext.tsx` | Media |
| 1.6 | Crear `useAirTable` hook (undo/redo, optimistic) | `hooks/useAirTable.ts` | Alta |

### Fase 2: Columnas — Resize, Drag, Freeze, Crear (3h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 2.1 | `AirTableHeader` con resize por drag | `components/ui/AirTableHeader.tsx` | Alta |
| 2.2 | Reordenar columnas con `@dnd-kit` | `AirTableHeader.tsx` | Media |
| 2.3 | Congelar columnas (sticky left) | `AirTableHeader.tsx` | Media |
| 2.4 | Visibilidad de columnas (toggle) | `AirTableToolbar.tsx` | Baja |
| 2.5 | Crear campo desde tabla ("+ Columna") | `AirTableToolbar.tsx` | Media |
| 2.6 | Renombrar campo (doble click en header) | `AirTableHeader.tsx` | Baja |
| 2.7 | Cambiar tipo de campo desde header | `AirTableHeader.tsx` | Media |
| 2.8 | Persistir configuración de columnas | `useAirTable.ts` | Media |

### Fase 3: Filas — Drag, Bulk Edit, Virtualización (3h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 3.1 | Reordenar filas con `@dnd-kit/sortable` | `AirTableView.tsx` | Media |
| 3.2 | Selección múltiple (checkbox) | `AirTableView.tsx` | Baja |
| 3.3 | Bulk edit: cambiar campo en todas las seleccionadas | `AirTableBulkBar.tsx` | Alta |
| 3.4 | Bulk delete con confirmación | `AirTableBulkBar.tsx` | Baja |
| 3.5 | Virtualización con `@tanstack/react-virtual` | `AirTableView.tsx` | Alta |
| 3.6 | Altura de fila variable (auto-wrap texto) | `AirTableRow.tsx` | Media |
| 3.7 | Quick-add row (última fila vacía) | `AirTableView.tsx` | Media |
| 3.8 | Duplicar fila | `AirTableView.tsx` | Baja |

### Fase 4: Navegación — Keyboard, Copy/Paste, Undo/Redo (3h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 4.1 | `useKeyboardNav` — arrow keys entre celdas | `hooks/useKeyboardNav.ts` | Alta |
| 4.2 | Tab/Shift+Tab entre celdas | `useKeyboardNav.ts` | Media |
| 4.3 | Enter para editar, Escape para cancelar | `AirTableCell.tsx` | Baja |
| 4.4 | Copy (Ctrl+C) de celda/rango | `hooks/useClipboard.ts` | Alta |
| 4.5 | Paste (Ctrl+V) en celda/rango | `hooks/useClipboard.ts` | Alta |
| 4.6 | Ctrl+Z undo / Ctrl+Y redo | `useAirTable.ts` | Alta |
| 4.7 | Historial de comandos (stack de undo) | `useAirTable.ts` | Media |
| 4.8 | Indicador visual de celda activa | `AirTableCell.tsx` | Baja |

### Fase 5: Filtros y Agrupación Avanzada (3h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 5.1 | Filtros con operadores (contiene, es, vacío, >, <) | `AirTableToolbar.tsx` | Alta |
| 5.2 | Multi-filtro con AND/OR | `AirTableToolbar.tsx` | Alta |
| 5.3 | Chips de filtros activos con dismiss | `AirTableToolbar.tsx` | Baja |
| 5.4 | Filtros rápidos por tipo de celda | `AirTableCellTypes/` | Media |
| 5.5 | Agrupar por múltiples columnas | `AirTableGroupRow.tsx` | Alta |
| 5.6 | Grupos colapsables con animación | `AirTableGroupRow.tsx` | Media |
| 5.7 | Aggregations por grupo (count, sum, avg) | `AirTableGroupRow.tsx` | Media |
| 5.8 | Persistir filtros y agrupación | `useAirTable.ts` | Media |

### Fase 6: Formato y UX (2h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 6.1 | Formato condicional (reglas por valor) | `AirTableCell.tsx` | Alta |
| 6.2 | Color de fila por condición | `AirTableRow.tsx` | Media |
| 6.3 | Barra de progreso visual en celdas | `ProgressCell` | Baja |
| 6.4 | Badges/tags con colores | `MultiSelectCell` | Baja |
| 6.5 | Avatar stack en UserCell | `UserCell` | Media |
| 6.6 | Skeleton loading para filas | `AirTableView.tsx` | Baja |
| 6.7 | Empty state con acción | `AirTableView.tsx` | Baja |
| 6.8 | Tooltip en celdas truncadas | `AirTableCell.tsx` | Baja |

### Fase 7: Avanzado — Fórmulas, Relaciones, Attachments (4h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 7.1 | Motor de fórmulas básico | `FormulaCell.tsx` | Muy Alta |
| 7.2 | Funciones: SUM, AVG, COUNT, CONCAT, IF, TODAY | `FormulaCell.tsx` | Alta |
| 7.3 | Referencias a otras celdas ({columna}) | `FormulaCell.tsx` | Alta |
| 7.4 | Rollup: agregar de relación | `RollupCell.tsx` | Alta |
| 7.5 | RelationCell: selector de registros | `RelationCell.tsx` | Alta |
| 7.6 | AttachmentCell: upload inline | `AttachmentCell.tsx` | Alta |
| 7.7 | Preview de imágenes en celda | `AttachmentCell.tsx` | Media |
| 7.8 | Historial/auditoría de celda | `useCellHistory.ts` | Alta |

### Fase 8: Persistencia y Backend (3h)

| # | Tarea | Archivos | Complejidad |
|---|-------|----------|-------------|
| 8.1 | Endpoint `GET /api/tables/{id}/schema` | `backend/api/tables.py` | Media |
| 8.2 | Endpoint `PATCH /api/tables/{id}/rows/{row_id}` | `backend/api/tables.py` | Media |
| 8.3 | Endpoint `POST /api/tables/{id}/rows/bulk` | `backend/api/tables.py` | Media |
| 8.4 | Endpoint `PATCH /api/tables/{id}/columns` | `backend/api/tables.py` | Media |
| 8.5 | Modelo `TableSchema` (campos, tipos, orden) | `backend/models_tables.py` | Media |
| 8.6 | Modelo `TableView` (vistas guardadas) | `backend/models_tables.py` | Media |
| 8.7 | Modelo `TableRowHistory` (auditoría) | `backend/models_tables.py` | Media |
| 8.8 | Migraciones Alembic | `alembic/versions/` | Media |

---

## ⏱️ Resumen

| Fase | Alcance | Tiempo | Complejidad |
|------|---------|--------|-------------|
| **1** | Motor TanStack + 16 tipos de celda | 4h | 🔴🔴🔴 |
| **2** | Columnas (resize, drag, freeze, crear) | 3h | 🔴🔴 |
| **3** | Filas (drag, bulk, virtualización) | 3h | 🔴🔴 |
| **4** | Navegación (keyboard, copy/paste, undo) | 3h | 🔴🔴🔴 |
| **5** | Filtros y agrupación avanzada | 3h | 🔴🔴 |
| **6** | Formato y UX | 2h | 🔴 |
| **7** | Fórmulas, relaciones, attachments | 4h | 🔴🔴🔴 |
| **8** | Backend + persistencia | 3h | 🔴🔴 |
| **TOTAL** | **25 horas** | | |

---

## 🎯 Criterios de Aceptación Final

- [ ] Click en cualquier celda → edita inline (sin panel lateral)
- [ ] Drag en borde de columna → resize
- [ ] Drag en header de columna → reordenar
- [ ] Drag en handle de fila → reordenar filas
- [ ] Arrow keys navegan entre celdas como spreadsheet
- [ ] Ctrl+C / Ctrl+V copia y pega entre celdas
- [ ] Ctrl+Z deshace última edición
- [ ] Filtros con operadores (contiene, es, vacío, >, <, etc.)
- [ ] Agrupar por múltiples columnas
- [ ] Selección múltiple + bulk edit
- [ ] Formato condicional (colores por regla)
- [ ] Fórmulas básicas (SUM, AVG, IF, CONCAT)
- [ ] Celdas de relación (link a otro registro)
- [ ] Virtualización (1000+ filas sin lag)
- [ ] Vistas guardadas por usuario
- [ ] Crear campos desde tabla ("+ Columna")
- [ ] Todo funciona en Projects, CRM, Evangelism, Academy
