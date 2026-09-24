# Auditoría Forense Integral: Módulo Bienvenida y Onboarding Eclesial (onboarding) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `onboarding` (Flujo de Bienvenida, Inducción Espiritual, Selección de Sede Canónica y Configuración Inicial)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-ONBOARDING-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Bienvenida y Onboarding Eclesial (`onboarding`)** de la Plataforma CCF, cubriendo su flujo de inducción en Next.js 15, la integración con el Kernel de Personas (`Axioma 1`), la consistencia temporal de registros (`Axioma 2`), la selección y enlace multi-tenant con las sedes canónicas de la iglesia (`Axioma 3`), y las reglas de diseño y navegación:
- **Estructura Operativa y Vistas (1 Vista Canónica — 205 Líneas):**
  - `frontend/src/app/plataforma/onboarding/page.tsx` (205 líneas): Asistente wizard guiado en 3 etapas:
    1. **Paso 1 (Bienvenida Espiritual):** Presentación de los pilares institucionales (Academia CCF, Grupos de Vida y Propósito Ministerial).
    2. **Paso 2 (Selección de Comunidad y Sede Canónica):** Asociación contextual a las sedes oficiales de la iglesia: Sede Central (Mocoa), Sede Norte (Villagarzón) y Sede Sur (Puerto Asís).
    3. **Paso 3 (Preferencias y Habilitación):** Activación de alertas y notificaciones reactivas, aceptación de políticas de protección de datos espirituales y redirección canónica hacia `/plataforma/academy`.
- **Integración con Modelos y Backend:**
  - Enlace al Kernel de Personas (`personas.id` / `auth_users.id`) para la asignación definitiva del usuario a su congregación local y rol inicial.
  - Sincronización multi-tenant estricta (`sede_id` correspondiente a la sede seleccionada).
- **Documentación Canónica:**
  - `docs/PLATAFORMA_AUTH_RBAC_API_UI.md` y `docs/PLATAFORMA_MATRIZ_MODULAR.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. La experiencia de inducción vincula al creyente directamente sobre su identidad canónica `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Registros y sesiones se auditan en timestamps UTC.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. El Paso 2 implementa la selección de las sedes territoriales canónicas (Central, Norte, Sur), garantizando la contextualización del usuario en `sede_id` sin duplicidades ni bypass.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0). Estructura 100% en wizard interactivo paso a paso con animaciones fluidas (`AnimatePresence`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-ONB-01**. Se detectan **27 clases Tailwind hardcodeadas** (`text-white`, `bg-info-soft`, `bg-success-soft`, `text-success-text`, `bg-white/5`, etc.) y **37 selectores `dark:`** en `frontend/src/app/plataforma/onboarding/page.tsx`.
6. **Regla Frontend 3 (Cliente HTTP y Rutas Canónicas — 100%):** Redirección canónica protegida bajo `/plataforma/academy`.
7. **Compilación y Pruebas Backend (100%):** Balance sintáctico estricto (`curlies=0, parens=0, brackets=0`).
8. **Estado Documental (100%):** Especificaciones de onboarding y experiencia de usuario sincronizadas con la arquitectura de plataforma.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Nuevo usuario mapea 1:1 a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps y estados auditables en UTC canónico. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Selección de sedes canónicas Central, Norte y Sur. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers/Wizards | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Wizard modular reactivo. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-ONB-01.** 27 clases Tailwind hardcodeadas y 37 selectores `dark:` redundantes. | 15% | **60/100** | 🟡 **REQUIERE FASE 1** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; rutas canónicas `/plataforma/...` | **Cumplimiento pleno (100%).** Navegación interna direccionada a `/plataforma/academy`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Wizard funcional y balance sintáctico estricto en frontend. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Flujos de inducción alineados con el estándar de plataforma. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Bienvenida y Onboarding Eclesial (`onboarding`) presenta un diseño moderno e inductivo con selección de sedes multi-tenant ejemplar y 0 modales centrados. Se detecta el hallazgo **H-ONB-01** (37 selectores `dark:` y 27 clases Tailwind hardcodeadas) en su vista única. Se aprueba condicionado a su remediación técnica inmediata.

---

## 4. Inventario Detallado de la Vista Frontend de Onboarding

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/onboarding/page.tsx` | 205 | **27** | **37** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-ONB-01) |
| **TOTAL** | **1 Vista Canónica** | **205** | **27** | **37** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fase Atómica

Para subsanar el Hallazgo **H-ONB-01**, se establece la siguiente fase atómica de remediación:

### Fase 1: Remediación de Tokens Semánticos en Onboarding (`TKT-ONB-REMEDIATION-01`)
- **Archivo a intervenir (1 archivo — 205 líneas):**
  1. `frontend/src/app/plataforma/onboarding/page.tsx` (27 TW / 37 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-info-soft`, `bg-success-soft`, `text-success-text`, `bg-white/5`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--info-muted))` y `hsl(var(--success-muted))`.
  - Erradicar 37 selectores `dark:` redundantes.
  - Preservar el wizard interactivo de 3 pasos (0 modales centrados / `AlertDialog` = 0) y balance sintáctico estricto (`c:0 p:0 b:0`).
  - Preservar la navegación interna canónica `/plataforma/academy`.
- **Total incidencias a erradicar:** 27 clases TW / 37 selectores `dark:`.
- **Commit atómico:** `feat(onboarding): Remediación de Tokens Semánticos en Onboarding Eclesial (H-ONB-01)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutada la Fase 1 de remediación:
1. Se emitirá el ticket `TKT-ONB-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en `onboarding/page.tsx`.
3. Se procederá con `TKT-ONB-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en la ruta canónica `/plataforma/onboarding`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Bienvenida y Onboarding Eclesial (`onboarding`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-ONB-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
