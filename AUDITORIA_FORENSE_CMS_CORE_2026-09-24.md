# Auditoría Forense Integral — Módulo CMS Core y Tipos de Sección (core)
**Plataforma Comunidad Cristiana Fe (CCF)**  
**Fecha:** 24 de Septiembre de 2026  
**Identificador de Auditoría:** `TKT-AUDIT-CMS-CORE-01`  
**Módulo:** `cms` (Suite Core, Tipos de Sección, Custom Types y Showroom UI Kit)  
**Auditor Responsable:** `agy` (Auditor Forense de Arquitectura de Plataforma)  
**Ingeniero de Desarrollo:** `agy2` (Pair Programmer / Implementador Dev)  
**Rama de Integración:** `integration/cms-aniversario-to-main`  
**Estado:** **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)**

---

## 1. Resumen Ejecutivo y Alcance

La presente auditoría forense evalúa de manera exhaustiva y holística el núcleo operativo y estructural del Content Management System (CMS) de la Plataforma CCF. Este núcleo comprende el centro de mando del CMS, el catálogo y parametrizador de tipos de secciones (`section-types`), la administración de esquemas de contenido personalizado (`custom-types`) y el showroom interactivo de componentes visuales (`ui-kit`).

El análisis cubrió tanto la capa de arquitectura backend (modelos relacionales, esquemas Pydantic, migraciones y endpoints `/api/cms/v2/section-types`), como la suite frontend en Next.js 15 + React 19 compuesta por 4 vistas canónicas con un total de 1,927 líneas de código:
1. `frontend/src/app/plataforma/cms/page.tsx` (800 líneas) — Dashboard central del CMS.
2. `frontend/src/app/plataforma/cms/section-types/page.tsx` (625 líneas) — Gestión y parametrización de tipos de sección.
3. `frontend/src/app/plataforma/cms/custom-types/page.tsx` (196 líneas) — Gestor de tipos y campos personalizados.
4. `frontend/src/app/plataforma/cms/ui-kit/page.tsx` (306 líneas) — Catálogo y showroom de componentes del Design System CMS.

---

## 2. Hallazgos Forenses Detectados

### [H-CMS-CORE-01] Presencia de Selectores `dark:` Redundantes y Clases Tailwind Hardcodeadas No Semánticas
- **Severidad:** Media (Deuda técnica visual / Violación de Regla 2 de Frontend).
- **Archivos Afectados (Telemetría Canónica agy):**
  - `frontend/src/app/plataforma/cms/page.tsx` (800 líneas): **95** selectores `dark:`, **0** clases TW hardcodeadas.
  - `frontend/src/app/plataforma/cms/section-types/page.tsx` (625 líneas): **53** selectores `dark:`, **6** clases TW hardcodeadas.
  - `frontend/src/app/plataforma/cms/custom-types/page.tsx` (196 líneas): **0** selectores `dark:`, **3** clases TW hardcodeadas.
  - `frontend/src/app/plataforma/cms/ui-kit/page.tsx` (306 líneas): **6** selectores `dark:`, **0** clases TW hardcodeadas.
- **Total Hallazgo:** 154 selectores `dark:` y 9 clases Tailwind hardcodeadas no semánticas.
- **Impacto:** Los selectores `dark:` interfieren con el selector de temas global de CCF (10 paletas cromáticas), impidiendo la reactividad armónica entre modos claro y oscuro. Se requiere migrar a tokens semánticos del sistema (`hsl(var(--*))`).

---

## 3. Evaluación de los 8 Ejes Canónicos de Arquitectura

| # | Eje de Evaluación | Ponderación | Puntaje Obtenido | Estado | Observaciones Forenses |
| :-: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Axioma 1: Kernel de Personas** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Identidad de autores y administradores vinculada canónicamente a `personas.id` vía `actor_persona_id` y `auth_users.id`. Cero tablas paralelas de seres humanos. |
| **2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Campos temporales en UTC (`DateTime(timezone=True)`). Desactivación lógica garantizada mediante `is_active` y soft deletes en `cms_section_types`. |
| **3** | **Axioma 3: Aislamiento Multi-Tenant** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Gobernanza estricta por sede/tenant a través de `sede_id` autenticado y alcance ministerial global donde aplica. |
| **4** | **Drawers vs Modales Centrados** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Cero modales centrados (`AlertDialog` = 0) en los flujos operativos. Uso estricto de paneles laterales deslizantes (`SidePanel` / Drawer) en `section-types` y `custom-types`. |
| **5** | **Tokens Semánticos del Design System** | 15.0% | **9.0 / 15.0** | 🟡 OBSERVADO | **H-CMS-CORE-01**: Se detectaron 154 selectores `dark:` y 9 clases Tailwind hardcodeadas que deben sustituirse por tokens HSL semánticos. |
| **6** | **Peticiones HTTP y Rutas Canónicas** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | 100% de peticiones a través de `apiFetch()` (`@/lib/http` y clientes canónicos). Prefijo estricto `/plataforma/cms/...` en toda la navegación. |
| **7** | **TypeScript Estricto y Balance Sintáctico** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | Cero errores de tipado, tipado explícito de interfaces y balance sintáctico perfecto (`c:0 p:0 b:0`) en los 4 archivos. |
| **8** | **Manejo de Estados de UI** | 5.0% | **5.0 / 5.0** | 🟢 CUMPLE | Estados de carga (`Skeleton` / `Loader`), estados vacíos informativos (`EmptyState`) y feedback reactivo mediante notificaciones `toast`. |
| **TOTAL** | **Evaluación Global de Calidad** | **100.0%** | **89.0 / 100** | 🟡 **GRADO A** | **Aprobado Condicionado a Remediación Técnica (H-CMS-CORE-01)** |

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** La suite CMS Core y Tipos de Sección presenta una sólida arquitectura de datos y cumplimiento axiomático. Se autoriza la transición a la fase de remediación atómica para solventar las 163 anomalías visuales del hallazgo **H-CMS-CORE-01**.

---

## 4. Inventario Detallado de las Vistas Frontend de CMS Core

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/cms/page.tsx` | 800 | **0** | **95** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-CORE-01) |
| 2 | `frontend/src/app/plataforma/cms/section-types/page.tsx` | 625 | **6** | **53** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-CORE-01) |
| 3 | `frontend/src/app/plataforma/cms/custom-types/page.tsx` | 196 | **3** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-CORE-01) |
| 4 | `frontend/src/app/plataforma/cms/ui-kit/page.tsx` | 306 | **0** | **6** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-CORE-01) |
| **TOTAL** | **4 Vistas Canónicas** | **1,927** | **9** | **154** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en Fases Atómicas

Para erradicar el Hallazgo **H-CMS-CORE-01**, se establece la siguiente secuencia estricta de trabajo:

### Fase 1: Remediación de Tokens Semánticos en Suite CMS Core y Tipos de Sección (`TKT-CMS-CORE-REMEDIATION-01`)
- **Archivos a intervenir (4 archivos — 1,927 líneas):**
  1. `frontend/src/app/plataforma/cms/page.tsx` (95 `dark:`, clases TW hardcodeadas)
  2. `frontend/src/app/plataforma/cms/section-types/page.tsx` (53 `dark:`, clases TW hardcodeadas)
  3. `frontend/src/app/plataforma/cms/custom-types/page.tsx` (clases TW hardcodeadas)
  4. `frontend/src/app/plataforma/cms/ui-kit/page.tsx` (6 `dark:`, clases TW hardcodeadas)
- **Acciones específicas:**
  - Reemplazar clases Tailwind estáticas por tokens semánticos CSS del Design System: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--destructive))`, `hsl(var(--warning))` y `hsl(var(--success))`.
  - Erradicar 154 selectores `dark:` redundantes.
  - Preservar los paneles laterales `SidePanel` y Drawers (0 modales centrados).
  - Preservar 100% `apiFetch()` y el balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 154 selectores `dark:` y 9 clases Tailwind no semánticas.
- **Commit atómico:** `feat(cms): Remediación de Tokens Semánticos en Suite CMS Core y Tipos de Sección (H-CMS-CORE-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-CMS-CORE-FINAL-CERTIFICATION`)
- Validar la erradicación total de clases Tailwind no semánticas (0 residuales) en los 4 archivos.
- Actualizar `AUDITORIA_FORENSE_CMS_CORE_2026-09-24.md` con la nota certificada de **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final sin observaciones pendientes.
- **Commit atómico:** `docs(cms): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final de CMS Core y Tipos de Sección`.

### Fase 3: Despliegue Staging y Verificación en Vivo (`TKT-CMS-CORE-DEPLOY-AND-VERIFY`)
- Ejecutar despliegue mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next`).
- Medir telemetría HTTP 200 OK y latencia en milisegundos en las rutas canónicas:
  - `/plataforma/cms`
  - `/plataforma/cms/section-types`
  - `/plataforma/cms/custom-types`
  - `/plataforma/cms/ui-kit`
- Registrar telemetría en vivo en la auditoría y formalizar cierre.
- **Commit atómico:** `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Core y Tipos de Sección`.

---

## 6. Certificación Final y Despliegue Proyectados (`TKT-CMS-CORE-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Se ejecutará el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next` y verificación HTTP en servicio).
2. Se verificará en vivo la respuesta HTTP 200 OK y latencia en milisegundos en las 4 rutas canónicas del módulo.
3. Se registrará la telemetría en vivo en las Secciones 6 y 7 de la auditoría y se emitirá el commit atómico `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Core y Tipos de Sección`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo CMS Core y Tipos de Sección (`core`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-CMS-CORE-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
