# Auditoría Forense Integral: Módulo Admin (Gobernanza, Roles y Permisos) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral de Diagnóstico y Plan de Remediación)  
**Módulo Auditado:** `admin` (Usuarios, Roles, Permisos RBAC, Sedes, Auditoría de Sistema, Módulos y Automatizaciones)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-ADMIN-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN (86.5 / 100 — Grado B+)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Admin (Gobernanza, Roles y Permisos)** de la Plataforma CCF, cubriendo la totalidad de sus capas de dominio: backend relacional (`backend/models_auth.py`, `backend/models_users.py`, `backend/models_roles.py`, `backend/api/admin.py`, `backend/crud/admin.py`, `backend/schemas/admin.py`), suites de pruebas (`tests/test_admin*.py`), documentación canónica (`docs/MODULO_ADMIN.md`, `docs/ADMIN_*.md`) y aplicaciones de frontend (`frontend/src/app/plataforma/admin/**`, `frontend/src/components/admin/**`).

### Hallazgo Central
El núcleo arquitectónico del módulo Admin (backend, seguridad y modelo relacional) presenta una **adherencia perfecta (100%)** a los tres axiomas fundacionales de la Plataforma CCF:
1. **Axioma 1 (Kernel de Personas):** Identidad canónica unificada. La creación y gestión de usuarios en `backend/crud/admin.py` genera un único UUIDv4 compartido simultáneamente entre `personas.id` y `auth_users.id` (`Usuario.id = persona_id`). No existen identidades flotantes ni tablas paralelas de seres humanos.
2. **Axioma 2 (UTC y Soft-Deletes):** 100% de marcas de tiempo en UTC con `DateTime(timezone=True)` mediante `_utcnow()` (`datetime.now(timezone.utc)`). Erradicación absoluta de `datetime.utcnow()` y uso estricto de `deleted_at` para roles, usuarios, sedes, canales sociales y categorías.
3. **Axioma 3 (Aislamiento Multi-Tenant):** Control de acceso hermético basado en `sede_id` obtenido invariablemente del usuario autenticado (`sede_id = getattr(current_user, "sede_id", None)`), con aislamiento por query (`Usuario.sede_id == sede_id`) y soporte canónico para gobernanza ministerial global (`_is_global_admin`).
4. **Regla Frontend 1 (Drawers vs Modals):** **0 modales centrados (`AlertDialog` o modals en el centro del viewport)** en los 50 archivos escaneados. Todos los flujos utilizan vistas dedicadas, sidebars y paneles laterales deslizantes.
5. **Regla Frontend 3 (Cliente HTTP):** 100% de llamadas al backend de plataforma realizadas mediante `apiFetch()` (`@/lib/http`); **0 llamadas a `fetch()` crudo** en todo el módulo.

Sin embargo, en el frontend se detectó una infracción masiva a la **Regla Frontend 2 (Tokens Semánticos del Design System)**, catalogada como **H-ADM-01**: **46 archivos afectados** contienen **1,517 ocurrencias** de colores Tailwind hardcodeados (`bg-white`, `text-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, etc.) y selectores `dark:` en lugar de los tokens semánticos CSS del Design System (`hsl(var(--surface-1))`, `hsl(var(--foreground))`, `hsl(var(--primary))`, etc.).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :-: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `backend/crud/admin.py:285-298` genera un único UUIDv4 que instancia `Persona(id=persona_id)` y `Usuario(id=persona_id)`. Vinculación perfecta al Kernel. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; soft-delete universal | **Cumplimiento pleno (100%).** Timestamps con `DateTime(timezone=True)`. La función `_utcnow()` invoca `dt.datetime.now(dt.timezone.utc)`. 0 `datetime.utcnow()` crudo. Soft-delete con `deleted_at` en todas las entidades clave. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); 0 fugas IDOR; alcance global controlado | **Cumplimiento pleno (100%).** Inyección estricta de `sede_id` desde el actor autenticado. Filtrado canónico `Usuario.sede_id == sede_id` mediante `_visible_auth_users_query`, con bypass controlado para Superadministradores (`_is_global_admin`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 50 archivos escaneados. 0 modales centrados (`AlertDialog` o modals en viewport center). Flujos de edición e inspección alineados con paneles laterales y vistas dedicadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Fallo crítico (Hallazgo H-ADM-01).** 46 archivos de frontend presentan clases Tailwind hardcodeadas (`text-white`, `bg-white`, `bg-black`, `zinc-*`, `gray-*`, `blue-*`, etc.) y selectores `dark:`, con 1,517 ocurrencias totales. Requiere remediación por fases. | 15% | **20/100** | 🔴 **REQUIERE REMEDIACIÓN** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 50 archivos escaneados. 0 llamadas a `fetch()` crudo. Todos los componentes consumidores de datos utilizan `@/lib/http` (`apiFetch`) con interceptores y autenticación canónica. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y cobertura estructural | **Alta cobertura (90%).** 11 suites dedicadas (`tests/test_admin*.py`) que cubren asignación de permisos, roles UUID, usuarios UUID, personas UUID, hitos y automatizaciones. | 10% | **90/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Documentación estructurada (90%).** Paquete documental completo: `docs/MODULO_ADMIN.md`, `docs/ADMIN_API_CONTRACTS.md`, `docs/ADMIN_ARCHITECTURE.md`, `docs/ADMIN_RBAC_MATRIX.md`, `docs/ADMIN_QA_CHECKLIST.md`. | 5% | **90/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (20 \times 0.15) + (100 \times 0.10) + (90 \times 0.10) + (90 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 3.0 + 10.0 + 9.0 + 4.5 = \mathbf{86.5 / 100}$$

**Calificación:** **Grado B+ (86.5 / 100 — Aprobado Condicionado a Remediación)**  
**Dictamen:** El Módulo Admin cuenta con un diseño de backend de gobernanza, seguridad y multi-tenancy ejemplar, 100% alineado con el Kernel de Personas y los Axiomas 1, 2 y 3. Su frontend requiere una remediación estructurada de clases Tailwind hardcodeadas para alcanzar la certificación de excelencia canónica 100/100 Grado A+.

---

## 4. Inventario de Hallazgos Forenses

### Hallazgo H-ADM-01 (Severidad: Alta — Regla Frontend 2)
- **Descripción:** Proliferación masiva de clases de color hardcodeadas de Tailwind CSS (`bg-white`, `text-white`, `bg-black`, `text-black`, `zinc-*`, `gray-*`, `blue-*`, `emerald-*`, `red-*`) y selectores `dark:` en 46 vistas y componentes de administración.
- **Alcance:** 46 archivos afectados en `frontend/src/app/plataforma/admin` y `frontend/src/components/admin`, con un total de 1,517 coincidencias.
- **Impacto:** Inhibe la coherencia visual con el Design System, rompe la tematización unificada y genera desalineación con la regla de tokens semánticos institucionales.
- **Acción Requerida:** Sustitución quirúrgica por variables semánticas:
  - Fondos de tarjetas y contenedores: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`
  - Textos y títulos: `hsl(var(--foreground))`, `hsl(var(--muted-foreground))`
  - Bordes y líneas divisoras: `hsl(var(--border))`
  - Botones y marcas de acción: `hsl(var(--primary))`, `hsl(var(--primary-foreground))`
  - Semántica de estado: `hsl(var(--destructive))`, `hsl(var(--success))`, `hsl(var(--warning))`

#### Top de Archivos Infractores y Coincidencias:
1. `frontend/src/app/plataforma/admin/settings/system/page.tsx` (194)
2. `frontend/src/app/plataforma/admin/identity/page.tsx` (72)
3. `frontend/src/app/plataforma/admin/page.tsx` (65)
4. `frontend/src/app/plataforma/admin/ministerios/page.tsx` (62)
5. `frontend/src/app/plataforma/admin/familias/page.tsx` (58)
6. `frontend/src/app/plataforma/admin/actas/page.tsx` (55)
7. `frontend/src/app/plataforma/admin/finance/page.tsx` (51)
8. `frontend/src/app/plataforma/admin/access/page.tsx` (50)
9. `frontend/src/app/plataforma/admin/donations/config/page.tsx` (47)
10. `frontend/src/app/plataforma/admin/mission-impact/page.tsx` (47)
11. `frontend/src/app/plataforma/admin/donations/page.tsx` (45)
12. `frontend/src/app/plataforma/admin/dashboard/page.tsx` (45)
13. `frontend/src/app/plataforma/admin/maintenance/page.tsx` (45)
14. `frontend/src/app/plataforma/admin/reports/page.tsx` (41)
15. `frontend/src/app/plataforma/admin/finance/funds/page.tsx` (41)
16. `frontend/src/app/plataforma/admin/comments/page.tsx` (38)
17. `frontend/src/app/plataforma/admin/intelligence/page.tsx` (37)
18. `frontend/src/app/plataforma/admin/users/[id]/page.tsx` (37)
19. `frontend/src/app/plataforma/admin/settings/experience/page.tsx` (34)
20. `frontend/src/app/plataforma/admin/settings/contact/page.tsx` (33)
21. *(Resto de 26 archivos con entre 1 y 31 coincidencias).*

---

## 5. Matriz de Tickets de Remediación Canónica

Para erradicar de forma sistemática y segura las 1,517 incidencias de **H-ADM-01** y elevar el Módulo Admin a **100/100 Grado A+**, se establece el siguiente plan de trabajo estructurado en 4 fases de remediación atómica:

| Ticket ID | Prioridad | Módulo / Componente | Alcance y Archivos Clave | Meta de Coincidencias |
| :--- | :---: | :--- | :--- | :---: |
| **`TKT-ADM-REMEDIATION-01`** | **P0** | `admin` (Gobernanza Core, Usuarios y Roles) | Remediación de Tokens Semánticos en Gestión de Usuarios, Roles, Accesos, Identidad y Shell Principal (10 archivos).<br>• `users/page.tsx`<br>• `users/[id]/page.tsx`<br>• `roles/page.tsx`<br>• `access/page.tsx`<br>• `personas/page.tsx`<br>• `identity/page.tsx`<br>• `page.tsx`<br>• `components/admin/AdminHero.tsx`<br>• `components/admin/AdminShell.tsx` | Erradicar 306 ocurrencias |
| **`TKT-ADM-REMEDIATION-02`** | **P0** | `admin` (Configuración de Sistema y Parámetros) | Remediación de Tokens Semánticos en Ajustes Globales, Sedes, Experiencia y Mantenimiento (9 archivos).<br>• `settings/system/page.tsx`<br>• `settings/experience/page.tsx`<br>• `settings/contact/page.tsx`<br>• `settings/socials/page.tsx`<br>• `settings/locations/page.tsx`<br>• `settings/profile/page.tsx`<br>• `settings/sessions/page.tsx`<br>• `settings/page.tsx`<br>• `maintenance/page.tsx` | Erradicar 430 ocurrencias |
| **`TKT-ADM-REMEDIATION-03`** | **P0** | `admin` (Finanzas, Donaciones, Auditoría y Reportes) | Remediación de Tokens Semánticos en Fondos, Tesorería, Donaciones, Auditoría de Sistema, Actas y Comentarios (14 archivos).<br>• `finance/page.tsx`<br>• `finance/funds/page.tsx`<br>• `finance/treasury/page.tsx`<br>• `donations/page.tsx`<br>• `donations/config/page.tsx`<br>• `donations/[id]/page.tsx`<br>• `audit/page.tsx`<br>• `audit/[id]/page.tsx`<br>• `actas/page.tsx`<br>• `comments/page.tsx`<br>• `submissions/page.tsx`<br>• `reports/page.tsx`<br>• `assets/page.tsx`<br>• `testimonials/page.tsx` | Erradicar 419 ocurrencias |
| **`TKT-ADM-REMEDIATION-04`** | **P0** | `admin` (Ministerios, Familias, Impacto y Cursos) | Remediación de Tokens Semánticos en Ministerios, Familias, Impacto Misionero, Analítica, Inteligencia y Contenido (13 archivos).<br>• `ministerios/page.tsx`<br>• `familias/page.tsx`<br>• `mission-impact/page.tsx`<br>• `dashboard/page.tsx`<br>• `dashboard/radar/page.tsx`<br>• `intelligence/page.tsx`<br>• `spiritual-life/milestones/page.tsx`<br>• `analytics/candidates/page.tsx`<br>• `analytics/web-vitals/page.tsx`<br>• `talents/page.tsx`<br>• `content/list/page.tsx`<br>• `content/courses/new/page.tsx`<br>• `content/courses/[id]/page.tsx`<br>• `content/courses/[id]/upload/page.tsx` | Erradicar 362 ocurrencias |
| **`TKT-ADM-FINAL-CERTIFICATION`** | **P1** | `admin` (Certificación) | Actualización del informe forense `AUDITORIA_FORENSE_ADMIN_2026-09-24.md` elevando nota a 100/100 A+, registro de evidencias de remediación y dictamen final de aprobación. | Certificación 100/100 A+ |
| **`TKT-ADM-DEPLOY-AND-VERIFY`** | **P1** | `admin` (Despliegue) | Despliegue seguro mediante `bash scripts/deploy_frontend.sh` y verificación en vivo HTTP 200 en rutas canónicas de Admin. | 100% Rutas 200 OK |

---

## 6. Verificación de Cumplimiento de Reglas Operativas

1. **PROHIBIDO `--no-verify`:** Todo commit y push vinculado al módulo Admin se ejecuta respetando rigurosamente los hooks pre-commit y pre-push.
2. **Convención de Commits:** Prefijos estandarizados:
   - `docs(admin): Auditoría Forense Integral del Módulo Admin (Gobernanza, Roles y Permisos)`
   - `feat(admin): Remediación de Tokens Semánticos en Gobernanza Core, Usuarios y Roles (H-ADM-01 Fase 1)`
   - `feat(admin): Remediación de Tokens Semánticos en Configuración de Sistema y Parámetros (H-ADM-01 Fase 2)`
   - `feat(admin): Remediación de Tokens Semánticos en Finanzas, Donaciones, Auditoría y Reportes (H-ADM-01 Fase 3)`
   - `feat(admin): Remediación de Tokens Semánticos en Ministerios, Familias, Impacto y Cursos (H-ADM-01 Fase 4)`
   - `docs(admin): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final del Módulo Admin`
   - `feat(admin): Despliegue Staging y Verificación en Vivo del Módulo Admin`
3. **Validación de Tipos y Balance:** Ejecución estricta de validación sintáctica de llaves/corchetes y `tsc --noEmit` en cada fase de remediación.
