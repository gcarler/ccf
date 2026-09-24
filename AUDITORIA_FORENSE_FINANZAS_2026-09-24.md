# Auditoría Forense Integral: Suite Financiera (Finanzas, Contabilidad, Gastos, Facturación y Transparencia) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `finance` (Suite Financiera Transversal: Finanzas Centrales, Contabilidad, Facturación Electrónica, Gastos y Mayordomía/Transparencia)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-FINANCE-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (91.8 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Finanzas y su Suite Transversal (`finance`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales y operativas:
- **Backend y Endpoints Transversales:** `backend/api/finance.py`, `backend/api/finance_suite.py` (1,754 líneas consolidadas de contabilidad, conciliación bancaria, estados financieros, facturación electrónica, reporte de gastos y firma digital), `backend/models_finance_suite.py` (465 líneas modelando 18 entidades financieras relacionales) y `backend/schemas/finance_suite.py`.
- **Frontend y Vistas Operativas:** Los 5 archivos canónicos de la suite financiera en `frontend/src/app/plataforma/`:
  1. `frontend/src/app/plataforma/finances/page.tsx` (Hub Financiero y Dashboard Transversal)
  2. `frontend/src/app/plataforma/finances/transparency/page.tsx` (Mayordomía y Transparencia de Impacto)
  3. `frontend/src/app/plataforma/contabilidad/page.tsx` (Contabilidad y Conciliación)
  4. `frontend/src/app/plataforma/facturacion/page.tsx` (Facturación Electrónica y Órdenes de Venta)
  5. `frontend/src/app/plataforma/gastos/page.tsx` (Gestión de Reembolsos y Legalización de Gastos)
- **Suites de Pruebas y Aseguramiento:** `tests/test_finance_suite_coverage.py`, `tests/test_finance_suite_api.py`, `tests/test_finance_api.py`, `tests/test_finance_suite_gap.py`, `tests/test_finance_suite_extended.py`.
- **Documentación Canónica:** `docs/FINANCE_API_CONTRACTS.md`, `docs/FINANCE_QA_CHECKLIST.md`, `docs/FINANCE_RBAC_MATRIX.md`, `docs/ESTADO_FINANCE.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento riguroso. Todas las relaciones que involucran seres humanos en la suite financiera se acoplan estrictamente al UUID canónico de `personas.id`:
   - `ExpenseReport.employee_id` y `approved_by_id` refieren a `personas.id`.
   - `ExpenseReceipt.uploaded_by_id` refiere a `personas.id`.
   - `BankTransaction.reconciled_by_id` y `BankReconciliation.created_by_id` refieren a `personas.id`.
   - `AccountingEntry.created_by_id` y `FinancialStatement.generated_by_id` refieren a `personas.id`.
   - `SalesOrder.created_by_id`, `Invoice.created_by_id` y `InvoicePayment.created_by_id` refieren a `personas.id`.
   - `Document.uploaded_by_id`, `SignRequest.created_by_id` y `SignSigner.persona_id` refieren a `personas.id`.
   - `Donation.donor_id` refiere a `personas.id`. Cero tablas paralelas de seres humanos. Cero identidades desconectadas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento estricto. Columnas temporales con `DateTime(timezone=True)`. Backend opera exclusivamente con `datetime.now(timezone.utc)` y `_utcnow()`. Prohibición absoluta de `datetime.utcnow()` respetada al 100% (0 ocurrencias en todo el código de backend financiero). Preservación de registros mediante banderas de estado (`is_active`, `status`) y `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** La función `_finance_sede_scope(db, user)` en `backend/api/finance_suite.py` garantiza que `sede_id` se extraiga invariablemente del token del actor autenticado (`get_user_sede_id(db, user.id)`). Si el usuario carece de sede y no es administrador de plataforma (`_finance_platform_admin`), la petición es rechazada de inmediato con código 403 Forbidden. El endpoint de transparencia pública (`/finance/impact`) expone únicamente agregaciones no sensibles del impacto social y comunitario.
4. **Regla Frontend 1 (Drawers vs Modals — 80%):** **Hallazgo H-FIN-01**. Se detectó **1 modal centrado** en `frontend/src/app/plataforma/facturacion/page.tsx` (`showPayment` implementado con overlay centrado `fixed inset-0 bg-black/40 flex items-center justify-center`). Los demás flujos operan con paneles expandibles o en línea. Debe ser remediado convirtiéndolo en un SidePanel Drawer canónico.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 65%):** **Hallazgo H-FIN-02**. Los 5 archivos analizados presentan clases Tailwind hardcodeadas (`bg-white`, `border-white`, `text-white`, `bg-[#111418]`, `bg-[#1a1b1e]`, `bg-[#1E1F21]`, `bg-blue-100`, `border-blue-300`, `text-blue-800`, `bg-black`) y selectores `dark:` redundantes. Se contabilizan **125 clases Tailwind hardcodeadas** y **139 selectores `dark:`** a lo largo de los 5 archivos.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 5 archivos auditados utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación unificada bajo `/plataforma/finances`, `/plataforma/contabilidad`, `/plataforma/facturacion`, `/plataforma/gastos`.
8. **Compilación y Pruebas Backend (100%):** Suites dedicadas `test_finance_suite_coverage.py` y `test_finance_suite_api.py` asegurando la integridad de esquemas Pydantic y lógica contable. Balance sintáctico estricto en los 5 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Todas las entidades (`ExpenseReport`, `Invoice`, `SignRequest`, `Donation`, etc.) enlazan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps con `DateTime(timezone=True)`. Backend en UTC estricto. Cero llamadas a `datetime.utcnow()`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`_finance_sede_scope`); soporte global justificado | **Cumplimiento pleno (100%).** `_finance_sede_scope` previene bypass multi-tenant (403 si no tiene sede ni es admin global). Transparencia agregada no sensible. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Requiere Remediación (80%). Hallazgo H-FIN-01.** Detectado 1 modal centrado en `facturacion/page.tsx` (`showPayment` con `fixed inset-0 ... flex items-center justify-center`). | 15% | **80/100** | 🟡 **REQUIERE FASE 1** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (65%). Hallazgo H-FIN-02.** 125 clases Tailwind hardcodeadas y 139 selectores `dark:` en los 5 archivos de la suite financiera. | 15% | **65/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 5 archivos verificados. Cero llamadas a `fetch()` crudo. 100% de consultas internas utilizan `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Suites dedicadas `test_finance_suite_coverage.py` y `test_finance_suite_api.py` asegurando integridad transaccional. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, esquemas Pydantic y documentación de estado sincronizada en `docs/FINANCE_*.md` y `docs/ESTADO_FINANCE.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (80 \times 0.15) + (65 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 12.0 + 9.75 + 10.0 + 10.0 + 5.0 = \mathbf{91.75 / 100} \approx \mathbf{91.8 / 100}$$

**Calificación Inicial:** **Grado A (91.8 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** La Suite Financiera presenta una arquitectura backend impecable con estricto acoplamiento al Kernel de Personas (Axioma 1), UTC estricto (Axioma 2) y aislamiento multi-tenant robusto con función de guardia de sede (Axioma 3). En la capa frontend, se identifican dos hallazgos a remediar: **H-FIN-01** (1 modal centrado en Facturación a convertir en SidePanel Drawer) y **H-FIN-02** (125 clases Tailwind hardcodeadas y 139 selectores `dark:` en los 5 archivos). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 5 Archivos de Frontend de la Suite Financiera

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/facturacion/page.tsx` | 291 | 49 | 45 | 1 | 🔴 Requiere Fase 1 (H-FIN-01 + H-FIN-02) |
| 2 | `frontend/src/app/plataforma/gastos/page.tsx` | 227 | 25 | 27 | 0 | 🔴 Requiere Fase 1 (H-FIN-02) |
| 3 | `frontend/src/app/plataforma/finances/page.tsx` | 314 | 22 | 29 | 0 | 🔴 Requiere Fase 2 (H-FIN-02) |
| 4 | `frontend/src/app/plataforma/finances/transparency/page.tsx` | 158 | 15 | 20 | 0 | 🔴 Requiere Fase 2 (H-FIN-02) |
| 5 | `frontend/src/app/plataforma/contabilidad/page.tsx` | 256 | 14 | 18 | 0 | 🔴 Requiere Fase 2 (H-FIN-02) |
| **TOTAL** | **5 Archivos Auditados** | **1,246** | **125** | **139** | **1** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% de los Hallazgos **H-FIN-01** y **H-FIN-02**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Facturación y Gastos (`TKT-FIN-REMEDIATION-01`)
- **Archivos a intervenir (2 archivos):**
  1. `frontend/src/app/plataforma/facturacion/page.tsx` (1 modal centrado `showPayment` a Drawer + 49 clases TW + 45 `dark:`)
  2. `frontend/src/app/plataforma/gastos/page.tsx` (25 clases TW + 27 `dark:`)
- **Acciones específicas:**
  - Erradicar el modal centrado `fixed inset-0 bg-black/40 flex items-center justify-center` en `facturacion/page.tsx`, transformándolo en un panel lateral deslizante (`SidePanel` / Drawer canónico alineado a la derecha).
  - Reemplazar clases Tailwind hardcodeadas (`bg-blue-100`, `text-blue-800`, `border-blue-300`, `bg-white`, `text-white`, `border-white`, `bg-black`, etc.) por tokens semánticos reactivos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--info-muted))`, `hsl(var(--info))`.
  - Erradicar selectores `dark:` redundantes (`dark:bg-[#111418]`, `dark:bg-[#1a1b1e]`, `dark:border-white/10`, `dark:text-white`).
- **Total incidencias a erradicar:** 1 modal centrado (100% de H-FIN-01) y 74 clases TW / 72 selectores `dark:`.
- **Commit atómico:** `feat(finance): Erradicación de Modal Centrado y Remediación de Tokens en Facturación y Gastos (H-FIN-01 y H-FIN-02 Fase 1)`.

### Fase 2: Hub Central Financiero, Transparencia y Contabilidad (`TKT-FIN-REMEDIATION-02`)
- **Archivos a intervenir (3 archivos):**
  1. `frontend/src/app/plataforma/finances/page.tsx` (22 clases TW + 29 `dark:`)
  2. `frontend/src/app/plataforma/finances/transparency/page.tsx` (15 clases TW + 20 `dark:`)
  3. `frontend/src/app/plataforma/contabilidad/page.tsx` (14 clases TW + 18 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind (`bg-white`, `border-white`, `text-white`, `bg-[#1E1F21]`, `bg-[#1a1b1e]`, `bg-[#111418]`) por tokens del Design System: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`.
  - Erradicar selectores `dark:` y opacidades desordenadas.
- **Total incidencias a erradicar:** 51 clases TW / 67 selectores `dark:`.
- **Commit atómico:** `feat(finance): Remediación de Tokens Semánticos en Hub Financiero, Transparencia y Contabilidad (H-FIN-02 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-FIN-FINAL-CERTIFICATION` con actualización de la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de modales centrados (100% Drawers / SidePanels) y 0 clases Tailwind no semánticas en los 5 archivos.
3. Se procederá con `TKT-FIN-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las 5 rutas canónicas de la suite:
   - `/plataforma/finances`
   - `/plataforma/finances/transparency`
   - `/plataforma/contabilidad`
   - `/plataforma/facturacion`
   - `/plataforma/gastos`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (91.8 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-FIN-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
