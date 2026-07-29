# Plan de Cleanup: Tipos débiles en tests de frontend

## Contexto
`frontend/tsconfig.json` ya tiene `"strict": true`, por lo que el build pasa. Sin embargo, los tests aún contienen muchos `as` y `any` que pueden ocultar errores de contrato y dificultan el mantenimiento. Este plan prioriza los cambios para reducir deuda técnica sin romper el runtime.

---

## Estado actual

> **Última actualización:** 2026-07-29

- **Tareas completadas:** 10/10 (incluyendo la creación de factorías y refactor de todos los tests de proyectos identificados).
- **Estado del build:** `npx tsc --noEmit` pasa sin errores.
- **Estado de tests afectados:** 45/45 tests pasan en los 16 archivos de test modificados.
- **Factorías creadas:** `frontend/src/test-utils/factories.ts` con `createMockProject` y `createMockTask`.

### Resumen de cambios ya aplicados

| Tarea | Archivo(s) | Cambio realizado |
|-------|------------|------------------|
| 1 | `frontend/src/lib/__tests__/useProjectPageData.phases.test.tsx` | `(apiFetch as ReturnType<typeof vi.fn>)` → `vi.mocked(apiFetch)` |
| 2-3 | `frontend/tests/http.test.ts` | `vi.spyOn(globalThis, 'fetch')` en vez de `(globalThis as any).__ccfOriginalFetch`; assertions con `toHaveBeenCalledWith` |
| 4 | `frontend/src/components/ui/AgGridTable.test.tsx` | mock de `AgGridReact` con `MockAgGridProps` |
| 4 | `frontend/src/components/ui/OptimizedImage.test.tsx` | mock de `next/image` con `ImageProps` |
| 5 | `frontend/tests/project-tasks-data.test.ts` | datos inline tipados como `ProjectRecord[]` sin `as any` |
| 6-7 | `frontend/src/lib/__tests__/projects-views-integration.test.tsx` | `FAKE_PROJECT: ProjectRecord`; removido cast manual de `priority` |
| 8 | `frontend/src/components/ui/PersonaSelect.test.tsx` | mock de `useAuth` tipado como `Partial<AuthContextType>` |
| 9 | `frontend/src/components/projects/TaskCommentSection.test.tsx` | comentarios mockeados tipados como `ProjectCommentItem[]` |
| 10 | `frontend/src/app/plataforma/projects/views/*.test.tsx` | uso de `createMockProject` |
| 10 | `frontend/src/components/projects/ProjectTableView.test.tsx`, `ProjectKanbanBoard.test.tsx`, `TaskTableView.test.tsx` | uso de `createMockTask` |
| Soporte | `frontend/src/context/AuthContext.tsx` | exportado `AuthContextType` para permitir mocks tipados |
| Soporte | `frontend/src/test-utils/factories.ts` | creadas factorías reutilizables |

---

## Categorización de hallazgos

| Categoría | Ejemplos | Acción |
|-----------|----------|--------|
| **Seguro / legítimo** | `container.firstChild as HTMLElement`, `as unknown as Canvas`, `as const`, mocks de bibliotecas externas | No tocar |
| **Eliminable con tipado correcto** | `{...} as ProjectRecord`, `{...} as any`, `null as any` | Tipar los datos o usar factorías |
| **Mejorable con tipos de mock** | `(props: any) => ...` en `vi.mock` | Reemplazar por `ComponentProps<...>` |
| **Aceptable en E2E** | `body: any`, `(window as any).__wsDispatch`, `as Record<string, unknown>` | Dejarlo salvo que sea trivial |

---

## Top 10 tareas de cleanup (priorizadas)

### Alta prioridad

1. **`frontend/src/lib/__tests__/useProjectPageData.phases.test.tsx`**
   - Cambio: `(apiFetch as ReturnType<typeof vi.fn>)` → `vi.mocked(apiFetch)`
   - Ubicación del símbolo: `apiFetch` se importa desde `frontend/src/lib/http.ts`.
   - Estado: ✅ Completado.
   - Motivo: API nativa de Vitest para mocks tipados.
   - Criterio de aceptación: ningún `as ReturnType<typeof vi.fn>` en tests que mockeen `apiFetch`.

2. **`frontend/tests/http.test.ts`**
   - Cambio: eliminar `(globalThis as any).__ccfOriginalFetch` y usar `vi.spyOn(globalThis, 'fetch')`.
   - Ubicación del símbolo: función `apiFetch` en `frontend/src/lib/http.ts` usa `globalThis.fetch` como fallback.
   - Estado: ✅ Completado.
   - Motivo: evita mutar propiedades de `globalThis` sin tipo.
   - Criterio de aceptación: no quedan propiedades mágicas en `globalThis`; el mock se restaura automáticamente con `vi.restoreAllMocks()`.

3. **`frontend/tests/http.test.ts`**
   - Cambio: reemplazar el cast manual de `mockFetch.mock.calls[0]` por `expect(mockFetch).toHaveBeenCalledWith(...)` con matchers.
   - Estado: ✅ Completado.
   - Motivo: elimina `as unknown as [...]` y mejora legibilidad.
   - Criterio de aceptación: assertions que no usen `mock.calls[0]` ni casts manuales.
   - Dependencia: debe completarse después de la tarea 2.

4. **`frontend/src/components/ui/AgGridTable.test.tsx` y `OptimizedImage.test.tsx`**
   - Cambio: `(props: any)` → `(props: React.ComponentProps<typeof Component>)` o interfaz mínima.
   - Ubicación de los mocks: `vi.mock('ag-grid-react')` y `vi.mock('next/image')` respectivamente.
   - Estado: ✅ Completado.
   - Motivo: detecta cambios en el contrato de props.
   - Criterio de aceptación: no queda `props: any` en mocks de componentes internos.

### Media prioridad

5. **`frontend/tests/project-tasks-data.test.ts`**
   - Cambio: remover `as any` de los objetos inline y tiparlos como `ProjectRecord[]`.
   - Ubicación de la función: `flattenProjectTasks` en `frontend/src/app/plataforma/projects/tasks/taskList.ts`.
   - Estado: ✅ Completado.
   - Motivo: seguridad en los datos de prueba de tareas.
   - Criterio de aceptación: datos de prueba tipados sin `as any`; la función de negocio compila sin necesidad de casts.
   - Dependencia: recomendable completar antes de la tarea 10 (factorías).

6. **`frontend/src/lib/__tests__/projects-views-integration.test.tsx`**
   - Cambio: eliminar `} as any` del proyecto mockeado y construir un `ProjectRecord` válido.
   - Estado: ✅ Completado.
   - Motivo: test de integración crítico; debe reflejar la forma real.
   - Criterio de aceptación: el objeto `FAKE_PROJECT` está declarado con tipo `ProjectRecord` y no usa `as any`.

7. **`frontend/src/lib/__tests__/projects-views-integration.test.tsx`**
   - Cambio: eliminar `payload.priority as ProjectTaskRecord["priority"]`. Corregir la firma de `createTask` para que acepte el literal union.
   - Ubicación de `createTask`: función helper local dentro del mismo test.
   - Estado: ✅ Completado.
   - Motivo: evita cast manual en el payload.
   - Criterio de aceptación: el payload se tipa con `ProjectTaskRecord["priority"]` y no requiere cast.
   - Dependencia: debe completarse después de la tarea 6.

8. **`frontend/src/components/ui/PersonaSelect.test.tsx`**
   - Cambio: `} as any` del contexto → `Partial<AuthContextType>`.
   - Ubicación del tipo: `frontend/src/context/AuthContext.tsx` exporta `AuthContextType`.
   - Estado: ✅ Completado.
   - Motivo: seguridad en mocks de contexto.
   - Criterio de aceptación: el mock de `useAuth` no usa `as any`; el tipo `AuthContextType` está exportado desde el módulo real.
   - Dependencia: requiere exportar `AuthContextType` desde `AuthContext.tsx`.

9. **`frontend/src/components/projects/TaskCommentSection.test.tsx`**
   - Cambio: eliminar `] as any` del array de comentarios mockeados y tiparlo con la interfaz `ProjectCommentItem`.
   - Estado: ✅ Completado.
   - Motivo: asegura que el componente reciba datos válidos.
   - Criterio de aceptación: los comentarios de prueba están tipados como `ProjectCommentItem[]` y no usan `as any`.

### Baja prioridad

10. **Tests de vistas de proyectos (`ProjectsBoardView`, `ProjectsTableView`, etc.)**
    - Cambio: crear una factoría `createMockTask(overrides?: Partial<ProjectTaskRecord>)` y `createMockProject(overrides?: Partial<ProjectRecord>)`.
    - Ubicación de las factorías: `frontend/src/test-utils/factories.ts`.
    - Estado: ✅ Completado.
    - Motivo: mantenibilidad. Elimina decenas de `} as ProjectRecord` / `} as ProjectTaskRecord`.
    - Criterio de aceptación: no quedan `} as ProjectRecord` ni `} as ProjectTaskRecord` en tests de frontend; todas las entidades se crean mediante factorías.
    - Dependencias: requiere que los tipos `ProjectRecord` y `ProjectTaskRecord` estén disponibles y que la ruta `@/test-utils/factories` esté en el path alias del proyecto.

---

## Criterios de aceptación (Definition of Done)

Para dar por terminado el cleanup se debe cumplir:

1. **Compilación limpia:**
   - `cd /root/ccf/frontend && npx tsc --noEmit` finaliza sin errores.
2. **Tests afectados pasan:**
   - Todos los tests en los 16 archivos modificados pasan (`npx vitest run <lista>`).
3. **Sin `as any` nuevos:**
   - No se introducen `as any` ni `} as RecordType` para ocultar errores de tipo.
4. **Tipos exportados:**
   - Cualquier tipo necesario para mocks está exportado desde su módulo real (no duplicado en tests).
5. **Documentación actualizada:**
   - Este plan refleja el estado real y las rutas de los archivos afectados.

---

## Dependencias entre tareas

```
Tarea 2 (http spy)
    │
    ▼
Tarea 3 (http assertions)
    │
Tarea 8 (AuthContextType exportado)
    │
    ▼
PersonaSelect typed mock
    │
Tarea 5/6/7 (tipar datos inline)
    │
    ▼
Tarea 10 (factorías)
```

- Las tareas **1, 4, 9** son independientes y pueden ejecutarse en cualquier orden.
- Las tareas **2 → 3** deben ir en orden, ya que la segunda depende de tener un `vi.spyOn` para hacer assertions.
- Las tareas **5, 6, 7** se benefician de hacerse antes de la **10**, porque una vez creadas las factorías se reescriben con `createMock*`.
- La tarea **8** depende de exportar `AuthContextType` desde `frontend/src/context/AuthContext.tsx`.
- La tarea **10** depende de que `@/test-utils/factories` esté disponible y de que los tipos `ProjectRecord` / `ProjectTaskRecord` no cambien sin actualizar la factoría.

---

## Esfuerzo y riesgo

- **Esfuerzo estimado:** 2-4 horas de trabajo enfocado.
- **Riesgo:** Bajo. Los cambios afectan solo tests; cualquier error se detecta en compilación o al correr `vitest`.
- **Rollback:** trivial, ya que se tocan archivos de test.

---

## Mecanismo anti-regresión

Para evitar que vuelvan a aparecer `as any` y `as` innecesarios en tests:

1. **Pre-commit hook (opcional):**
   - Agregar un hook de `lint-staged` que ejecute `tsc --noEmit` sobre el frontend antes de permitir el commit.
2. **Regla de ESLint / biome:**
   - Configurar una regla que detecte `as any` en archivos `*.test.{ts,tsx}` y falle en CI.
3. **CI:**
   - Incluir el job de frontend (`npx tsc --noEmit` y `npm run test -- --run`) en `scripts/run_ci.sh`.
4. **Revisión manual:**
   - En PRs que toquen tests, revisar que los mocks usen tipos reales y que no se agreguen casts para silenciar errores.

---

## Comandos de verificación

```bash
cd /root/ccf/frontend

# 1. Typecheck completo
npx tsc --noEmit

# 2. Tests afectados (rápido)
npx vitest run src/lib/__tests__/useProjectPageData.phases.test.tsx tests/http.test.ts src/components/ui/AgGridTable.test.tsx src/components/ui/OptimizedImage.test.tsx tests/project-tasks-data.test.ts src/lib/__tests__/projects-views-integration.test.tsx src/components/ui/PersonaSelect.test.tsx src/components/projects/TaskCommentSection.test.tsx src/app/plataforma/projects/views/ProjectsBoardView.test.tsx src/app/plataforma/projects/views/ProjectsCalendarView.test.tsx src/app/plataforma/projects/views/ProjectsGanttView.test.tsx src/app/plataforma/projects/views/ProjectsGridView.test.tsx src/app/plataforma/projects/views/ProjectsListView.test.tsx src/app/plataforma/projects/views/ProjectsTableView.test.tsx src/app/plataforma/projects/views/accessibility.test.tsx src/components/projects/ProjectTableView.test.tsx src/components/projects/ProjectKanbanBoard.test.tsx

# 3. Tests completos de frontend (más lento)
npm run test -- --run

# 4. Si se modifica mucho: run_ci.sh completo
bash ../scripts/run_ci.sh
```

---

## Notas adicionales

- Los mocks de bibliotecas externas (`framer-motion`, `recharts`, `ag-grid`) pueden seguir usando `any` o `unknown` si el costo de tiparlos no compensa. Regla de pulgar: usar `any` solo si tipar el mock implica más de 10 líneas o reexportar tipos internos no públicos.
- Los casts DOM (`container.firstChild as HTMLElement`) son idiomáticos en Testing Library y se consideran aceptables.
- Los `as const` y `as typeof` en E2E son legítimos para definir tablas de datos.
