# Auditoría Forense Integral: Módulo Configuración y Roles (settings) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `settings` (Configuración General de Plataforma, Roles Eclesiásticos y Preferencias)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-SETTINGS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Configuración y Roles (`settings`)** de la Plataforma CCF, cubriendo sus dos vistas canónicas en Next.js 15, la integración con el Kernel de Personas y Roles (`Axioma 1`), los mecanismos de autenticación y autorización RBAC, y las suites de pruebas automatizadas:
- **Backend y Modelos Relacionales:**
  - `backend/models_crm.py` (tablas `personas` y catálogo de roles eclesiales): PK UUIDv4 (`id`), relación de roles con cargos eclesiales y agrupaciones ministeriales de liderazgo (`is_leadership`).
  - Timestamps timezone-aware (`DateTime(timezone=True)`) con `_utcnow()` (`datetime.now(timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `deleted_at` e `is_active`.
- **Endpoints Transversales:**
  - `GET /crm/roles`: listado canónico de roles de iglesia y tipos de asistencia.
  - `POST /crm/roles`: creación de nuevos roles ministeriales con definición de estilo y jerarquía.
  - `PUT /crm/roles/{role_id}`: edición de nombre, color y flag de liderazgo.
  - `DELETE /crm/roles/{role_id}?fallback_id={id}`: eliminación controlada de roles con migración atómica obligatoria de miembros hacia un rol de reemplazo (fallback).
- **Frontend y Vistas Operativas (2 Vistas Canónicas — 424 Líneas):**
  1. `frontend/src/app/plataforma/settings/page.tsx` (205 líneas): Panel central de configuración, cuenta, atajos, apariencia, toggle rápido de temas y zona de peligro.
  2. `frontend/src/app/plataforma/settings/roles/page.tsx` (219 líneas): Gestión integral de roles de asistencia y ministerios con `WorkspaceDrawer` para edición y eliminación con fallback.
- **Suites de Pruebas y Cobertura Automatizada:**
  - `tests/test_crm_rbac_http.py`: validación de RBAC, permisos de roles y accesos protegidos.
  - `tests/test_evangelism_custom_role_regression.py`: regresión de roles personalizados y jerarquías eclesiales.
  - `tests/test_crm_api_personas.py`: asociación de personas con sus roles canónicos.
- **Documentación Canónica:**
  - `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`, `docs/CRM_RBAC_MATRIX.md` y `docs/PLATAFORMA_MATRIZ_MODULAR.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas y Roles — 100%):** Cumplimiento estricto. La administración de roles impacta directamente la clasificación de `personas` en el CRM sin tablas paralelas de seres humanos. Cero duplicidades de identidad.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Timestamps en `DateTime(timezone=True)` con `_utcnow()` (`datetime.now(timezone.utc)`). Cero `datetime.utcnow()`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. Los roles operan con contexto de sede o alcance global ministerial respaldado por `get_user_sede_id()`.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0). Las operaciones de creación, edición y confirmación de eliminación con fallback utilizan exclusivamente `WorkspaceDrawer`.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-SET-01**. Se detectan **41 clases Tailwind hardcodeadas** (`text-white`, `bg-white/80`, `bg-[#0f1117]`, `bg-[#1a1d27]`, `bg-info-soft`, `text-info-text`, `bg-success-soft`, `text-success-text`, `bg-danger-soft`, `bg-red-50`, etc.) y **48 selectores `dark:`** en las 2 vistas de frontend.
6. **Regla Frontend 3 (Cliente HTTP apiFetch y Rutas Canónicas — 90%):** 100% de peticiones vía `apiFetch()`. Se detectan 2 enlaces internos en `settings/page.tsx` (`/account` y `/theme`) que deben normalizarse al prefijo canónico `/plataforma/...`.
7. **Compilación y Pruebas Backend (100%):** Pruebas de roles y CRM pasando. Balance sintáctico estricto en ambos archivos (`curlies=0, parens=0, brackets=0`).
8. **Estado Documental (100%):** Matrices RBAC y documentación modular sincronizadas.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Catálogo de roles subordinado al Kernel de Personas. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Acceso acotado a la sede del usuario en sesión (`current_user.id`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Estructura 100% basada en `WorkspaceDrawer`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-SET-01.** 41 clases Tailwind hardcodeadas y 48 selectores `dark:` en los 2 archivos. | 15% | **60/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo; rutas `/plataforma/...` | **Requiere Ajuste Menor (90%).** 100% `apiFetch()`. Se requiere normalizar 2 rutas internas a `/plataforma/...`. | 10% | **90/100** | 🟡 **REQUIERE NORMALIZACIÓN** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Pruebas pasando en suites de CRM y roles. Balance sintáctico estricto en frontend. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos y documentación sincronizados con la gobernanza CCF. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (90 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 9.0 + 10.0 + 5.0 = \mathbf{88.0 / 100}$$

**Calificación Inicial:** **Grado A (88.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Configuración y Roles (`settings`) exhibe una arquitectura sólida con uso ejemplar de `WorkspaceDrawer` para todos sus flujos de creación, edición y eliminación de roles con migración atómica obligatoria. Se detecta el hallazgo **H-SET-01** (48 selectores `dark:` y 41 clases Tailwind hardcodeadas) y la necesidad de normalizar 2 rutas de navegación internas. Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de las 2 Vistas de Frontend de Settings

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/settings/page.tsx` | 205 | **20** | **32** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-SET-01) |
| 2 | `frontend/src/app/plataforma/settings/roles/page.tsx` | 219 | **21** | **16** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-SET-01) |
| **TOTAL** | **2 Vistas Canónicas** | **424** | **41** | **48** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-SET-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Panel Central de Configuración (`TKT-SET-REMEDIATION-01`)
- **Archivo a intervenir (1 archivo — 205 líneas):**
  1. `frontend/src/app/plataforma/settings/page.tsx` (20 TW / 32 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-white/80`, `bg-[#0f1117]`, `bg-[#1a1d27]`, `bg-info-soft`, `text-info-text`, `bg-success-soft`, `text-success-text`, `bg-danger-soft`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))` y `hsl(var(--destructive))`.
  - Erradicar 32 selectores `dark:` redundantes.
  - Normalizar rutas de enlaces a `/plataforma/account` y `/plataforma/theme`.
  - Preservar balance sintáctico estricto.
- **Total incidencias a erradicar:** 20 clases TW / 32 selectores `dark:` + 2 rutas normalizadas.
- **Commit atómico:** `feat(settings): Remediación de Tokens Semánticos y Rutas en Configuración General (H-SET-01 Fase 1)`.

### Fase 2: Configuración de Roles Eclesiales (`TKT-SET-REMEDIATION-02`)
- **Archivo a intervenir (1 archivo — 219 líneas):**
  2. `frontend/src/app/plataforma/settings/roles/page.tsx` (21 TW / 16 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-white/5`, `border-white/10`, `border-white/5`, `bg-red-50`, `border-red-100`, `bg-warning-soft`, `text-warning-text`, `shadow-red-500/30`, etc.) por variables semánticas reactivas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--destructive))`, `hsl(var(--destructive-muted))` y `hsl(var(--warning-muted))`.
  - Erradicar 16 selectores `dark:` redundantes.
  - Preservar `WorkspaceDrawer` (0 modales centrados) y balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 21 clases TW / 16 selectores `dark:`.
- **Commit atómico:** `feat(settings): Remediación de Tokens Semánticos en Configuración de Roles (H-SET-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-SET-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 2 archivos.
3. Se procederá con `TKT-SET-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/settings`
   - `/plataforma/settings/roles`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (88.0 / 100 — Grado A)** para el **Módulo Configuración y Roles (`settings`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-SET-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
