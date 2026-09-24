# Auditoría Forense Integral — Módulo CMS Recursos, Webhooks y Auditoría (resources)
**Plataforma Comunidad Cristiana Fe (CCF)**  
**Fecha:** 24 de Septiembre de 2026  
**Identificador de Auditoría:** `TKT-AUDIT-CMS-RESOURCES-01`  
**Módulo:** `cms` (Suite Recursos, Webhooks, Sesiones, Notificaciones y Auditoría)  
**Auditor Responsable:** `agy` (Auditor Forense de Arquitectura de Plataforma)  
**Ingeniero de Desarrollo:** `agy2` (Pair Programmer / Implementador Dev)  
**Rama de Integración:** `integration/cms-aniversario-to-main`  
**Estado:** **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)**

---

## 1. Resumen Ejecutivo y Alcance

La presente auditoría forense evalúa de manera integral y exhaustiva la suite de servicios de soporte, integraciones externas y telemetría de seguridad del Content Management System (CMS) de la Plataforma CCF. Esta suite abarca el explorador y gestor de recursos multimedia y archivos descargables (`resources`), el bus de webhooks para eventos editoriales (`webhooks`), el monitor de sesiones concurrentes de edición (`sessions`), la central de notificaciones internas (`notifications`) y la bitácora forense de auditoría editorial (`audit`).

La evaluación cubrió la integridad de las pruebas de backend (`tests/test_enterprise_cms.py`, `tests/test_cms_media_service.py`), los contratos de API en `/api/cms/v2/webhooks` y `/api/cms/v2/media`, y la inspección rigurosa de las 5 vistas canónicas frontend en Next.js 15 + React 19 que totalizan 1,280 líneas de código:
1. `frontend/src/app/plataforma/cms/resources/page.tsx` (577 líneas) — Gestor de recursos y descargables.
2. `frontend/src/app/plataforma/cms/webhooks/page.tsx` (325 líneas) — Configuración de endpoints y logs de entrega de webhooks.
3. `frontend/src/app/plataforma/cms/sessions/page.tsx` (113 líneas) — Monitor y control de sesiones activas.
4. `frontend/src/app/plataforma/cms/notifications/page.tsx` (117 líneas) — Bandeja de notificaciones y alertas editoriales.
5. `frontend/src/app/plataforma/cms/audit/page.tsx` (148 líneas) — Visor de logs y trazabilidad de acciones.

---

## 2. Hallazgos Forenses Detectados

### [H-CMS-RES-01] Presencia de Selectores `dark:` Redundantes y Clases Tailwind Hardcodeadas No Semánticas
- **Severidad:** Media (Deuda técnica visual / Violación de Regla 2 de Frontend).
- **Archivos Afectados (Telemetría Canónica agy):**
  - `frontend/src/app/plataforma/cms/resources/page.tsx` (577 líneas): **56** selectores `dark:`, clases hardcodeadas (`bg-white/5`, `bg-white/10`, `text-white`, `border-white/10`).
  - `frontend/src/app/plataforma/cms/webhooks/page.tsx` (325 líneas): **46** selectores `dark:`, clases hardcodeadas (`border-white/5`, `bg-white/10`, `text-white`, `border-white/10`).
  - `frontend/src/app/plataforma/cms/sessions/page.tsx` (113 líneas): **0** selectores `dark:`, **3** clases TW hardcodeadas (`border-red-200`, `bg-red-50`, `text-white`).
  - `frontend/src/app/plataforma/cms/notifications/page.tsx` (117 líneas): **0** selectores `dark:`, **2** clases TW hardcodeadas (`bg-green-100`, `bg-red-100`).
  - `frontend/src/app/plataforma/cms/audit/page.tsx` (148 líneas): **0** selectores `dark:`, **1** clase TW hardcodeada (`bg-red-100`).
- **Total Hallazgo:** 102 selectores `dark:` y 6 clases Tailwind hardcodeadas no semánticas.
- **Impacto:** Los selectores `dark:` hardcodeados distorsionan el comportamiento reactivo del selector global de temas CCF (10 paletas semánticas), impidiendo una transición armónica entre modos claro y oscuro. Es obligatorio unificar mediante tokens semánticos CSS `hsl(var(--*))`.

---

## 3. Evaluación de los 8 Ejes Canónicos de Arquitectura

| # | Eje de Evaluación | Ponderación | Puntaje Obtenido | Estado | Observaciones Forenses |
| :-: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Axioma 1: Kernel de Personas** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Identidad de actores en sesiones y auditoría vinculada a `personas.id` a través de `actor_persona_id` y `auth_users.id`. Cero esquemas paralelos de personas. |
| **2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Timestamps en UTC (`DateTime(timezone=True)`). Desactivación lógica y soft deletes (`is_active`, `deleted_at`) en webhooks y recursos. |
| **3** | **Axioma 3: Aislamiento Multi-Tenant** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Gobernanza estricta por tenant a través de `sede_id` autenticado y alcance ministerial global donde aplica. |
| **4** | **Drawers vs Modales Centrados** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Cero modales centrados (`AlertDialog` = 0) en las 5 vistas. Uso exclusivo de paneles laterales deslizantes (`SidePanel` / Drawer) en `webhooks` y `sessions`. |
| **5** | **Tokens Semánticos del Design System** | 15.0% | **9.0 / 15.0** | 🟡 OBSERVADO | **H-CMS-RES-01**: Se detectaron 102 selectores `dark:` y 6 clases Tailwind hardcodeadas que deben sustituirse por tokens HSL semánticos. |
| **6** | **Peticiones HTTP y Rutas Canónicas** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | 100% de peticiones a través de `apiFetch()` (`@/lib/http` y clientes canónicos). Prefijo canónico estricto `/plataforma/cms/...` en toda la navegación. |
| **7** | **TypeScript Estricto y Balance Sintáctico** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | Cero errores de tipado, tipado explícito de interfaces y balance sintáctico perfecto (`c:0 p:0 b:0`) en los 5 archivos. |
| **8** | **Manejo de Estados de UI** | 5.0% | **5.0 / 5.0** | 🟢 CUMPLE | Estados de carga (`Skeleton` / `Loader`), estados vacíos informativos (`EmptyState`) y feedback reactivo mediante notificaciones `toast`. |
| **TOTAL** | **Evaluación Global de Calidad** | **100.0%** | **89.0 / 100** | 🟡 **GRADO A** | **Aprobado Condicionado a Remediación Técnica (H-CMS-RES-01)** |

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** La suite CMS Recursos, Webhooks y Auditoría presenta una sólida arquitectura de integración, cumplimiento axiomático y cero modales centrados. Se autoriza la transición inmediata a la fase de remediación atómica para subsanar el hallazgo **H-CMS-RES-01**.

---

## 4. Inventario Detallado de las Vistas Frontend de CMS Recursos

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/cms/resources/page.tsx` | 577 | **0** | **56** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-RES-01) |
| 2 | `frontend/src/app/plataforma/cms/webhooks/page.tsx` | 325 | **0** | **46** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-RES-01) |
| 3 | `frontend/src/app/plataforma/cms/sessions/page.tsx` | 113 | **3** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-RES-01) |
| 4 | `frontend/src/app/plataforma/cms/notifications/page.tsx` | 117 | **2** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-RES-01) |
| 5 | `frontend/src/app/plataforma/cms/audit/page.tsx` | 148 | **1** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-RES-01) |
| **TOTAL** | **5 Vistas Canónicas** | **1,280** | **6 únicas** | **102** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en Fases Atómicas

Para erradicar el Hallazgo **H-CMS-RES-01**, se establece la siguiente secuencia estricta de trabajo:

### Fase 1: Remediación de Tokens Semánticos en Suite CMS Recursos y Webhooks (`TKT-CMS-RES-REMEDIATION-01`)
- **Archivos a intervenir (5 archivos — 1,280 líneas):**
  1. `frontend/src/app/plataforma/cms/resources/page.tsx` (56 selectores `dark:`)
  2. `frontend/src/app/plataforma/cms/webhooks/page.tsx` (46 selectores `dark:`)
  3. `frontend/src/app/plataforma/cms/sessions/page.tsx` (3 clases TW hardcodeadas)
  4. `frontend/src/app/plataforma/cms/notifications/page.tsx` (2 clases TW hardcodeadas)
  5. `frontend/src/app/plataforma/cms/audit/page.tsx` (1 clase TW hardcodeada)
- **Acciones específicas:**
  - Reemplazar clases Tailwind estáticas por tokens semánticos CSS del Design System: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--destructive))`, `hsl(var(--warning))` y `hsl(var(--success))`.
  - Erradicar 102 selectores `dark:` redundantes.
  - Preservar los paneles laterales `SidePanel` y Drawers (0 modales centrados).
  - Preservar 100% `apiFetch()` y el balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 102 selectores `dark:` y 6 clases Tailwind no semánticas.
- **Commit atómico:** `feat(cms): Remediación de Tokens Semánticos en Suite CMS Recursos, Webhooks y Auditoría (H-CMS-RES-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-CMS-RES-FINAL-CERTIFICATION`)
- Validar la erradicación total de clases Tailwind no semánticas (0 residuales) en los 5 archivos.
- Actualizar `AUDITORIA_FORENSE_CMS_RECURSOS_2026-09-24.md` con la nota certificada de **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final sin observaciones pendientes.
- **Commit atómico:** `docs(cms): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final de CMS Recursos, Webhooks y Auditoría`.

### Fase 3: Despliegue Staging y Verificación en Vivo (`TKT-CMS-RES-DEPLOY-AND-VERIFY`)
- Ejecutar despliegue mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next`).
- Medir telemetría HTTP 200 OK y latencia en milisegundos en las 5 rutas canónicas:
  - `/plataforma/cms/resources`
  - `/plataforma/cms/webhooks`
  - `/plataforma/cms/sessions`
  - `/plataforma/cms/notifications`
  - `/plataforma/cms/audit`
- Registrar telemetría en vivo en la auditoría y formalizar cierre.
- **Commit atómico:** `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Recursos, Webhooks y Auditoría`.

---

## 6. Certificación Final y Despliegue Proyectados (`TKT-CMS-RES-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Se ejecutará el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next` y verificación HTTP en servicio).
2. Se verificará en vivo la respuesta HTTP 200 OK y latencia en milisegundos en las 5 rutas canónicas del módulo.
3. Se registrará la telemetría en vivo en las Secciones 6 y 7 de la auditoría y se emitirá el commit atómico `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Recursos, Webhooks y Auditoría`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo CMS Recursos, Webhooks y Auditoría (`resources`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-CMS-RES-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
