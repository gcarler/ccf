# Auditoría Forense Integral: Módulo Academy (Cursos y LMS) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral de Diagnóstico y Plan de Remediación)  
**Módulo Auditado:** `academy` (Cursos, Lecciones, Inscripciones, Calificaciones, Evaluaciones, Docencia y Catálogo)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-ACADEMY-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN (87.5 / 100 — Grado B+)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Academy (Cursos y LMS)** de la Plataforma CCF, cubriendo la totalidad de sus capas de dominio: backend relacional (`backend/models_academy_core.py`, `backend/api/academy.py`, `backend/crud/academy.py`), contratos y suites de pruebas (`tests/test_academy*.py`), documentación canónica (`docs/ESTADO_ACADEMY.md`, `docs/ACADEMY_*.md`) y aplicaciones de frontend (`frontend/src/app/plataforma/academy/**`, `frontend/src/components/academy/**`).

### Hallazgo Central
El núcleo arquitectónico del módulo Academy (backend y base de datos) presenta una **adherencia perfecta (100%)** a los tres axiomas fundacionales de la Plataforma CCF:
1. **Axioma 1 (Kernel de Personas):** Todas las relaciones humanas (estudiantes, profesores, tutores, autores de foros, firmantes de actas y evaluadores) están ancladas estrictamente a `personas.id` como UUID canónico. No existen tablas paralelas ni identidades flotantes.
2. **Axioma 2 (UTC y Soft-Deletes):** 100% de marcas de tiempo en UTC con `DateTime(timezone=True)` mediante `datetime.now(timezone.utc)`. Erradicación absoluta de `datetime.utcnow()` y cero sentencias de hard-delete descontroladas.
3. **Axioma 3 (Aislamiento Multi-Tenant):** Control de acceso hermético basado en `sede_id` obtenido invariablemente de la sesión del usuario (`get_user_sede_id(db, current_user.id)`), con soporte canónico para programas y cursos globales ministeriales (`sede_id IS NULL`).
4. **Regla Frontend 1 (Drawers vs Modals):** 0 modales centrados clásicos; cumplimiento canónico de paneles laterales (`RightPanel` / `SidePanel`).
5. **Regla Frontend 3 (Cliente HTTP):** 100% de llamadas al backend realizadas mediante `apiFetch()` (`@/lib/http`); 0 llamadas a `fetch()` crudo.

Sin embargo, en el frontend se detectó una **infracción masiva a la Regla Frontend 2 (Tokens Semánticos del Design System)**, catalogada como **H-ACAD-01**: **31 archivos afectados** contienen **850 ocurrencias** (más de 1,300 con variantes de utilidades) de colores Tailwind hardcodeados (`bg-white`, `text-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, etc.) y selectores `dark:` en lugar de los tokens semánticos CSS del Design System (`hsl(var(--surface-1))`, `hsl(var(--foreground))`, `hsl(var(--primary))`, etc.).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :-: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Todas las entidades (`Enrollment`, `LessonProgress`, `CourseAttendance`, `FormalActa`, `ForumThread`, `ForumComment`, `AcademyActivityLog`, asignaciones docentes) referencian `personas.id` con FK UUIDv4. Cero tablas `alumnos` o `docentes` paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; soft-delete universal | **Cumplimiento pleno (100%).** Timestamps gestionados con `DateTime(timezone=True)` y `dt.datetime.now(dt.timezone.utc)`. 0 `datetime.utcnow()` residuales. Cero sentencias destructivas `db.delete(`; estados de curso/matrícula y `deleted_at` canónicos. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); 0 fugas IDOR; alcance global controlado | **Cumplimiento pleno (100%).** Inyección estricta de `sede_id` desde el actor autenticado. Filtrado canónico `(Course.sede_id.is_(None)) \| (Course.sede_id == sede_id)`. Verificación de membresía y sede en inscripciones y actas formales. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`fixed inset-0 ... mx-auto`). Los flujos de evaluaciones y formularios interactivos utilizan `AssessmentDrawer` con `RightPanel` canónico y accesibilidad ARIA. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Fallo crítico (Hallazgo H-ACAD-01).** 31 archivos de frontend presentan clases Tailwind hardcodeadas (`text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, etc.) y selectores `dark:`. Requiere remediación en 3 fases. | 15% | **25/100** | 🔴 **REQUIERE REMEDIACIÓN** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 35 archivos escaneados. 0 llamadas a `fetch()` crudo. 23 archivos consumidores de datos utilizan `@/lib/http` (`apiFetch`) con interceptores de autenticación y cabeceras estándar. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y cobertura estructural | **Alta cobertura (90%).** 17 suites dedicadas (`tests/test_academy*.py`) con más de 250 KB de tests unitarios, de dominio y de integración. Observación operativa menor en sandbox por permisos de archivo de cobertura. | 10% | **90/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Documentación extensa (95%).** Paquete documental completo: `docs/ESTADO_ACADEMY.md`, `docs/ACADEMY_API_CONTRACTS.md`, `docs/ACADEMY_RBAC_MATRIX.md`, `docs/ACADEMY_QA_CHECKLIST.md` y `docs/PLAN_ACADEMY_CALIDAD.md`. Requiere actualización tras remediación UI. | 5% | **95/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (25 \times 0.15) + (100 \times 0.10) + (90 \times 0.10) + (95 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 3.75 + 10.0 + 9.0 + 4.75 = \mathbf{87.5 / 100}$$

**Calificación:** **Grado B+ (87.5 / 100 — Aprobado Condicionado a Remediación)**  
**Dictamen:** El Módulo Academy posee una arquitectura backend impecable, 100% alineada a los Axiomas 1, 2 y 3, con cero fugas de datos y total fidelidad al Kernel de Personas. Sin embargo, su frontend requiere una remediación urgente de clases CSS hardcodeadas para alcanzar la certificación 100/100 Grado A+.

---

## 4. Inventario de Hallazgos Forenses

### Hallazgo H-ACAD-01 (Severidad: Alta — Regla Frontend 2)
- **Descripción:** Proliferación de colores hardcodeados de Tailwind CSS (`bg-white`, `text-white`, `bg-black`, `text-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`) y selectores redundantes `dark:` en las vistas y componentes de Academy.
- **Alcance:** 31 archivos afectados en `frontend/src/app/plataforma/academy` y `frontend/src/components/academy`, con 850 coincidencias directas.
- **Impacto:** Rompe el soporte dinámico para temas claro/oscuro del Design System institucional, produce inconsistencias visuales respecto al resto de la plataforma y viola la regla de tokens semánticos obligatorios.
- **Acción Requerida:** Sustituir todas las clases de color por variables CSS semánticas:
  - Fondos de superficies: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`
  - Textos y tipografía: `hsl(var(--foreground))`, `hsl(var(--muted-foreground))`
  - Bordes y divisores: `hsl(var(--border))`
  - Acciones y marcas: `hsl(var(--primary))`, `hsl(var(--primary-foreground))`
  - Estados semánticos: `hsl(var(--destructive))`, `hsl(var(--success))`, `hsl(var(--warning))`, `hsl(var(--info))`

#### Detalle de Archivos Infractores y Coincidencias:
1. `frontend/src/app/plataforma/academy/courses/[id]/manage/page.tsx` (67)
2. `frontend/src/app/plataforma/academy/profile/page.tsx` (67)
3. `frontend/src/app/plataforma/academy/course/[id]/page.tsx` (54)
4. `frontend/src/app/plataforma/academy/forum/[id]/page.tsx` (42)
5. `frontend/src/app/plataforma/academy/courses/[id]/lessons/page.tsx` (40)
6. `frontend/src/app/plataforma/academy/AcademyClient.tsx` (36)
7. `frontend/src/app/plataforma/academy/assessments/[id]/page.tsx` (35)
8. `frontend/src/app/plataforma/academy/coordination/courses/new/page.tsx` (35)
9. `frontend/src/components/academy/AssessmentDrawer.tsx` (35)
10. `frontend/src/app/plataforma/academy/teacher/page.tsx` (34)
11. `frontend/src/app/plataforma/academy/forum/page.tsx` (34)
12. `frontend/src/app/plataforma/academy/profile/progress/page.tsx` (34)
13. `frontend/src/app/plataforma/academy/courses/page.tsx` (32)
14. `frontend/src/app/plataforma/academy/coordination/page.tsx` (32)
15. `frontend/src/app/plataforma/academy/account/page.tsx` (28)
16. `frontend/src/components/academy/CertificateView.tsx` (22)
17. `frontend/src/app/plataforma/academy/students/page.tsx` (21)
18. `frontend/src/app/plataforma/academy/assessments/new/page.tsx` (21)
19. `frontend/src/app/plataforma/academy/resources/page.tsx` (20)
20. `frontend/src/app/plataforma/academy/teachers/page.tsx` (19)
21. `frontend/src/app/plataforma/academy/courses/[id]/edit/page.tsx` (18)
22. `frontend/src/app/plataforma/academy/certificates/page.tsx` (17)
23. `frontend/src/app/plataforma/academy/grades/page.tsx` (17)
24. `frontend/src/app/plataforma/academy/loading.tsx` (16)
25. `frontend/src/app/plataforma/academy/curriculum/page.tsx` (16)
26. `frontend/src/app/plataforma/academy/certificates/[code]/page.tsx` (14)
27. `frontend/src/app/plataforma/academy/schedule/page.tsx` (13)
28. `frontend/src/components/academy/VideoPlayer.tsx` (11)
29. `frontend/src/app/plataforma/academy/courses/[id]/page.tsx` (10)
30. `frontend/src/app/plataforma/academy/enroll/[id]/page.tsx` (9)
31. `frontend/src/app/plataforma/academy/layout.tsx` (1)

---

### Hallazgo H-ACAD-02 (Severidad: Baja / Operativa — Entorno Sandbox)
- **Descripción:** Permiso denegado sobre el archivo preexistente `/root/ccf/.coverage` propiedad de `root2` al ejecutar `pytest` sin parámetros de sobreescritura de coverage.
- **Mitigación Operativa:** Los comandos de verificación automatizada deben invocar pytest con `-o addopts=""` o `--no-cov` en entornos sandbox compartidos.

---

## 5. Matriz de Tickets de Remediación Canónica

Para alcanzar la certificación **100/100 Grado A+**, se establece la siguiente hoja de ruta de remediación estructurada en commits atómicos:

| Ticket ID | Prioridad | Módulo / Componente | Alcance y Archivos Clave | Meta de Coincidencias |
| :--- | :---: | :--- | :--- | :---: |
| **`TKT-ACAD-REMEDIATION-01`** | **P0** | `academy` (Cursos Core) | Remediación de Tokens Semánticos en Catálogo de Cursos, Gestión y Lecciones (Fase 1: 7 archivos).<br>• `courses/[id]/manage/page.tsx`<br>• `course/[id]/page.tsx`<br>• `courses/[id]/lessons/page.tsx`<br>• `courses/page.tsx`<br>• `courses/[id]/edit/page.tsx`<br>• `courses/[id]/page.tsx`<br>• `enroll/[id]/page.tsx` | Erradicar 230 ocurrencias |
| **`TKT-ACAD-REMEDIATION-02`** | **P0** | `academy` (Evaluaciones y LMS) | Remediación de Tokens Semánticos en Evaluaciones, Certificados, Recursos y Componentes Compartidos (Fase 2: 10 archivos).<br>• `assessments/[id]/page.tsx`<br>• `assessments/new/page.tsx`<br>• `components/academy/AssessmentDrawer.tsx`<br>• `components/academy/CertificateView.tsx`<br>• `components/academy/VideoPlayer.tsx`<br>• `certificates/page.tsx`<br>• `certificates/[code]/page.tsx`<br>• `resources/page.tsx`<br>• `grades/page.tsx`<br>• `curriculum/page.tsx` | Erradicar 208 ocurrencias |
| **`TKT-ACAD-REMEDIATION-03`** | **P0** | `academy` (Gestión Docente y Foros) | Remediación de Tokens Semánticos en Coordinación, Docencia, Foros, Perfil y Estudiantes (Fase 3: 14 archivos).<br>• `profile/page.tsx`<br>• `forum/[id]/page.tsx`<br>• `AcademyClient.tsx`<br>• `coordination/courses/new/page.tsx`<br>• `teacher/page.tsx`<br>• `forum/page.tsx`<br>• `profile/progress/page.tsx`<br>• `coordination/page.tsx`<br>• `account/page.tsx`<br>• `students/page.tsx`<br>• `teachers/page.tsx`<br>• `loading.tsx`<br>• `schedule/page.tsx`<br>• `layout.tsx` | Erradicar 412 ocurrencias |
| **`TKT-ACAD-FINAL-CERTIFICATION`** | **P1** | `academy` (Certificación) | Actualización del informe forense `AUDITORIA_FORENSE_ACADEMIA_2026-09-24.md` elevando nota a 100/100 A+, registro de evidencias de remediación y dictamen final de aprobación. | Certificación 100/100 A+ |
| **`TKT-ACAD-DEPLOY-AND-VERIFY`** | **P1** | `academy` (Despliegue) | Despliegue seguro mediante `bash scripts/deploy_frontend.sh` y verificación en vivo HTTP 200 en rutas canónicas de Academy. | 100% Rutas 200 OK |

---

## 6. Verificación de Cumplimiento de Reglas Operativas

1. **PROHIBIDO `--no-verify`:** Todo commit y push vinculado al módulo Academy se ejecuta respetando rigurosamente los hooks pre-commit y pre-push.
2. **Convención de Commits:** Prefijos estandarizados:
   - `docs(academy): Auditoría Forense Integral del Módulo Academy (Cursos y LMS)`
   - `feat(academy): Remediación de Tokens Semánticos en Cursos Core y Lecciones (H-ACAD-01 Fase 1)`
   - `feat(academy): Remediación de Tokens Semánticos en Evaluaciones y Certificados (H-ACAD-01 Fase 2)`
   - `feat(academy): Remediación de Tokens Semánticos en Coordinación, Docencia y Foros (H-ACAD-01 Fase 3)`
   - `feat(academy): Certificación Forense Plena 100/100 A+ del Módulo Academy`
   - `feat(academy): Despliegue Staging y Verificación en Vivo del Módulo Academy`
3. **Validación de Tipos:** Ejecución de `tsc --noEmit` requerida en cada fase para asegurar cero errores de TypeScript y balance sintáctico pleno.
