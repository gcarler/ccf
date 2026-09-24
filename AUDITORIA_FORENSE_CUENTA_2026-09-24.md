# Auditoría Forense Integral: Módulo Mi Cuenta y Perfil Ministerial (account) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `account` (Gestión de Perfil Ministerial, Datos Personales, Credenciales de Cuenta, Preferencias, Roles y Pistas de Auditoría de Usuario)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-ACCOUNT-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Mi Cuenta y Perfil Ministerial (`account`)** de la Plataforma CCF, cubriendo sus dos vistas canónicas en Next.js 15, la integración con el Kernel de Personas (`Axioma 1`), los mecanismos de autenticación y actualización de credenciales, y las suites de pruebas automatizadas:
- **Backend y Modelos Relacionales:**
  - `backend/models_crm.py` (tabla canónica `personas`): PK UUIDv4 (`id`), relación con `sede_id`, datos personales (`nombre`, `apellido`, `email`, `telefono`), perfil ministerial, cargos y dones. Identidad unificada con `auth_users.id` (Axioma 1).
  - Timestamps timezone-aware (`DateTime(timezone=True)`) con `_utcnow()` (`datetime.now(timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `deleted_at` e `is_active`.
- **Endpoints Transversales:**
  - `GET /crm/personas/me/profile`: consulta del perfil ministerial y personal del usuario en sesión.
  - `PATCH /crm/personas/me/profile`: actualización de datos ministeriales y de contacto con validación de actor UUID canónico.
  - `PATCH /v3/auth/me`: actualización de credenciales e identidad de acceso.
  - `POST /v3/auth/send-verification-email`: verificación de seguridad de correo electrónico.
- **Frontend y Vistas Operativas (2 Vistas Canónicas — 715 Líneas):**
  1. `frontend/src/app/plataforma/account/page.tsx` (434 líneas): Centro de control de cuenta de usuario, pestañas de perfil, seguridad, sesiones activas, preferencias y navegación modular.
  2. `frontend/src/app/plataforma/account/ministry-profile/page.tsx` (281 líneas): Perfil ministerial especializado con insignias eclesiales, nivel de experiencia (XP), áreas de servicio y llamado pastoral.
- **Suites de Pruebas y Cobertura Automatizada:**
  - `tests/test_crm_rbac_http.py`: validación de permisos, protección 401 sin autenticación y mutaciones autorizadas en `/api/crm/personas/me/profile`.
  - `tests/test_crm_api_personas.py`: pruebas de contrato, roundtrip GET y PATCH de perfil.
  - `tests/test_auth_v3_core.py`: pruebas del ciclo de vida de autenticación e identidad de cuenta.
- **Documentación Canónica:**
  - `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`, `docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md` y `docs/KERNEL_QA_CHECKLIST.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. La cuenta y el perfil ministerial se resuelven exclusivamente sobre `personas.id` (`/crm/personas/me/profile`) compartiendo el mismo UUID con `auth_users.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Timestamps en `DateTime(timezone=True)` con `_utcnow()` (`datetime.now(timezone.utc)`). Cero `datetime.utcnow()`. Soft-delete activo en `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. El perfil de cuenta opera con el contexto de sede canónico del usuario autenticado (`get_user_sede_id()`). Protegido contra escalación horizontal.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0). Navegación por pestañas laterales y paneles dedicados.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-ACC-01**. Se detectan **78 clases Tailwind hardcodeadas** (`text-white`, `bg-white/5`, `border-white/10`, `border-white/5`, `bg-[#111418]`, etc.) y **55 selectores `dark:`** en las 2 vistas de frontend.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Ambas vistas consumen exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Rutas protegidas bajo el prefijo canónico `/plataforma/account` y `/plataforma/account/ministry-profile`.
8. **Compilación y Pruebas Backend (100%):** Tests dedicados pasando en backend. Balance sintáctico estricto en ambos archivos (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Perfil ministerial y cuenta mapean 1:1 a `personas.id` (`auth_users.id`). Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Soft-delete en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Acceso acotado a la identidad y sede del usuario en sesión (`current_user.id`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Estructura basada en paneles y pestañas laterales. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-ACC-01.** 78 clases Tailwind hardcodeadas y 55 selectores `dark:` en los 2 archivos canónicos. | 15% | **60/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 100% de llamadas a la API a través de `apiFetch()` de `@/lib/http`. Cero `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Pruebas pasando en suites de CRM y Auth v3. Balance sintáctico estricto en frontend. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos de autenticación y matrices RBAC sincronizados con la gobernanza CCF. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Mi Cuenta y Perfil Ministerial (`account`) cuenta con una sólida subordinación al Kernel de Personas (Axioma 1) y al modelo de seguridad multi-tenant de la plataforma (Axioma 3). Las llamadas internas utilizan 100% `apiFetch()` y no existen modales centrados (`AlertDialog` = 0). No obstante, se detecta el hallazgo **H-ACC-01** (55 selectores `dark:` y 78 clases Tailwind hardcodeadas entre ambas vistas). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de las 2 Vistas de Frontend de Account

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/account/page.tsx` | 434 | **50** | **55** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-ACC-01) |
| 2 | `frontend/src/app/plataforma/account/ministry-profile/page.tsx` | 281 | **28** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-ACC-01) |
| **TOTAL** | **2 Vistas Canónicas** | **715** | **78** | **55** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-ACC-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Panel Central de Cuenta (`TKT-ACC-REMEDIATION-01`)
- **Archivo a intervenir (1 archivo — 434 líneas):**
  1. `frontend/src/app/plataforma/account/page.tsx` (50 TW / 55 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-white/5`, `border-white/10`, `border-white/5`, `bg-[#111418]`, `dark:bg-white/5`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))` y `hsl(var(--text-secondary))`.
  - Erradicar 55 selectores `dark:` redundantes.
  - Preservar estructura de pestañas laterales, 100% `apiFetch` y balance sintáctico estricto.
- **Total incidencias a erradicar:** 50 clases TW / 55 selectores `dark:`.
- **Commit atómico:** `feat(account): Remediación de Tokens Semánticos en Vista de Cuenta (H-ACC-01 Fase 1)`.

### Fase 2: Perfil Ministerial (`TKT-ACC-REMEDIATION-02`)
- **Archivo a intervenir (1 archivo — 281 líneas):**
  2. `frontend/src/app/plataforma/account/ministry-profile/page.tsx` (28 TW / 0 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-white/5`, `border-white/10`, `border-white/5`, etc.) por variables semánticas reactivas del Design System CCF.
  - Mantener balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 28 clases TW.
- **Commit atómico:** `feat(account): Remediación de Tokens Semánticos en Perfil Ministerial (H-ACC-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-ACC-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 2 archivos.
3. Se procederá con `TKT-ACC-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/account`
   - `/plataforma/account/ministry-profile`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Mi Cuenta y Perfil Ministerial (`account`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-ACC-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
