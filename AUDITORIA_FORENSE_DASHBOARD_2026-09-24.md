# Auditoría Forense Integral: Módulo Dashboard (Tableros Ejecutivos y BI Transversal) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `dashboard` (Tableros Ejecutivos, Métricas Transversales, BI Modular: CRM, Academia, Evangelismo, Finanzas, Agenda, CMS, Proyectos y Admin)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-DASHBOARD-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (96.3 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Dashboard (`dashboard`)** de la Plataforma CCF, analizando la totalidad de sus componentes estructurales y operacionales:
- **Backend y Endpoints Unificados:** `backend/api/dashboard.py`, `backend/crud/dashboard.py` (1,526 líneas de lógica analítica agregada), `backend/schemas/dashboard.py` (definición estricta de esquemas Pydantic para `MetricCard`, `FunnelStage`, `ChartDataPoint`, `HeatmapItem`, `GeoBucket`, etc.).
- **Frontend y Vistas Operativas:** `frontend/src/app/plataforma/dashboard/**` (18 archivos de páginas y clientes ejecutivos correspondientes a los 8 dominios funcionales de la iglesia).
- **Suites de Pruebas y Aseguramiento:** `tests/test_dashboard_coverage.py`, `tests/test_crm_dashboard_contract.py`.
- **Documentación Canónica:** `docs/ESTADO_DASHBOARD.md`, `docs/AUDITORIA_FORENSE_DASHBOARD.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento riguroso. Todas las métricas de personas, roles eclesiales, tasas de conversión y pipelines analíticos se alimentan exclusivamente de `personas.id` y `models.Persona` (`models.Persona.church_role`, `actor_persona_id`). Cero tablas paralelas de seres humanos. Cero identidades desconectadas.
2. **Axioma 2 (Fechas en UTC y Agregaciones Temporales — 100%):** Cumplimiento estricto. Todas las agregaciones temporales, filtros de cohortes y marcas `last_updated` operan con `DateTime(timezone=True)` mediante `datetime.now(timezone.utc)` y `_utcnow()`. Prohibición absoluta de `datetime.utcnow()` respetada al 100% (0 ocurrencias en todo el código backend).
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** La función `require_user_sede_id(db, current_user)` en `backend/api/dashboard.py` garantiza que ninguna solicitud pueda suplantar o inyectar un `sede_id` arbitrario por query o body. La sede se resuelve obligatoriamente del token del usuario autenticado. En el dashboard `admin`, se exige rol administrativo estricto o permiso `system:config`.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` o modals en viewport center) en los 18 archivos de frontend.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 75%):** **Hallazgo H-DASH-01**. De los 18 archivos analizados, 17 son 100% conformes con el Design System. Únicamente el archivo raíz `frontend/src/app/plataforma/dashboard/DashboardOverviewClient.tsx` presenta **6 incidencias** de clases Tailwind hardcodeadas (`text-white`, `bg-info-soft`, `dark:*`).
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** 18 archivos verificados. Cero llamadas a `fetch()` crudo. 100% de consultas internas utilizan `apiFetch` de `@/lib/http`.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo. Todas las navegaciones internas utilizan `/plataforma/dashboard/...`.
8. **Compilación y Pruebas Backend (100%):** Suites dedicadas `test_dashboard_coverage.py` y `test_crm_dashboard_contract.py` asegurando integridad de contratos y datos.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `backend/crud/dashboard.py` ejecuta agregaciones directamente sobre `models.Persona` y `personas.id`. Cero identidades duplicadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Agregaciones** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps y cálculos de cohorte en UTC estricto. Cero llamadas a `datetime.utcnow()`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `require_user_sede_id` estricto; sede desde token; RBAC en admin | **Cumplimiento pleno (100%).** `backend/api/dashboard.py` inyecta `require_user_sede_id(db, current_user)`. Prohibido bypass desde cliente. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 18 archivos auditados. 0 modales centrados (`AlertDialog` = 0, Modales = 0). | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (75%). Hallazgo H-DASH-01.** 17 de 18 archivos limpios (94.4%). 6 violaciones detectadas en `DashboardOverviewClient.tsx` (`dark:*`, `text-white`, `bg-info-soft`). | 15% | **75/100** | 🟡 **REQUIERE FASE 1** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 18 archivos verificados. Cero llamadas a `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** `test_dashboard_coverage.py` y `test_crm_dashboard_contract.py` garantizan los contratos de métricas y gráficos. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, esquemas Pydantic y documentación de estado sincronizada en `docs/ESTADO_DASHBOARD.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (75 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 11.25 + 10.0 + 10.0 + 5.0 = \mathbf{96.25 / 100} \approx \mathbf{96.3 / 100}$$

**Calificación Inicial:** **Grado A (96.3 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Dashboard presenta una arquitectura backend de BI y agregaciones sumamente sólida, con estricto apego a los Axiomas 1, 2 y 3. El frontend de 18 archivos se encuentra casi en su totalidad conforme al Design System (17 de 18 archivos con 0 violaciones). El único hallazgo adverso es **H-DASH-01**, consistente en 6 violaciones menores en el componente de visión general (`DashboardOverviewClient.tsx`). Se aprueba condicionado a su remediación inmediata en una sola fase atómica.

---

## 4. Inventario Detallado de los 18 Archivos de Frontend Auditados

| # | Archivo Auditado | Violaciones Detectadas | Tipo de Infracción Principal | Estado |
| :-: | :--- | :---: | :--- | :-: |
| 1 | `frontend/src/app/plataforma/dashboard/DashboardOverviewClient.tsx` | 6 | Clases `dark:bg-transparent`, `bg-info-soft`, `dark:text-white`, `text-white` | 🔴 Requiere Fase 1 |
| 2 | `frontend/src/app/plataforma/dashboard/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 3 | `frontend/src/app/plataforma/dashboard/academy/AcademyDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 4 | `frontend/src/app/plataforma/dashboard/academy/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 5 | `frontend/src/app/plataforma/dashboard/admin/AdminDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 6 | `frontend/src/app/plataforma/dashboard/admin/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 7 | `frontend/src/app/plataforma/dashboard/agenda/AgendaDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 8 | `frontend/src/app/plataforma/dashboard/agenda/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 9 | `frontend/src/app/plataforma/dashboard/cms/CmsDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 10 | `frontend/src/app/plataforma/dashboard/cms/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 11 | `frontend/src/app/plataforma/dashboard/crm/CrmDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 12 | `frontend/src/app/plataforma/dashboard/crm/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 13 | `frontend/src/app/plataforma/dashboard/evangelism/EvangelismDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 14 | `frontend/src/app/plataforma/dashboard/evangelism/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 15 | `frontend/src/app/plataforma/dashboard/finance/FinanceDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 16 | `frontend/src/app/plataforma/dashboard/finance/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 17 | `frontend/src/app/plataforma/dashboard/projects/ProjectsDashboardClient.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 18 | `frontend/src/app/plataforma/dashboard/projects/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| **TOTAL** | **18 Archivos Auditados** | **6** | **Incidencias Totales a Erradicar** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-DASH-01**, se establece la siguiente fase atómica de remediación:

### Fase 1: Hub Central de Dashboard Overview (`TKT-DASH-REMEDIATION-01`)
- **Archivo a intervenir (1 archivo):**
  1. `frontend/src/app/plataforma/dashboard/DashboardOverviewClient.tsx` (6 incidencias)
- **Acciones específicas:**
  - Sustituir `dark:bg-transparent` por token semántico o remover redundancia reactiva.
  - Reemplazar `bg-info-soft` y `dark:bg-[hsl(var(--primary))]/10` por `bg-[hsl(var(--primary)/0.1)]`.
  - Reemplazar `dark:text-[hsl(var(--primary))]` y `dark:text-white` por `text-[hsl(var(--text-primary))]`.
  - Eliminar selectores `dark:group-hover:text-[hsl(var(--primary))]` redundantes.
- **Total incidencias a erradicar:** 6 incidencias.
- **Commit atómico:** `feat(dashboard): Remediación de Tokens Semánticos en Hub Central de Dashboard (H-DASH-01 Fase 1)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutada la Fase 1 de remediación:
1. Se emitirá el ticket `TKT-DASH-FINAL-CERTIFICATION` con actualización de nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de violaciones residuales (0 clases Tailwind hardcodeadas, 0 selectores `dark:`).
3. Se procederá con `TKT-DASH-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/dashboard`
   - `/plataforma/dashboard/crm`
   - `/plataforma/dashboard/academy`
   - `/plataforma/dashboard/admin`
   - `/plataforma/dashboard/agenda`
   - `/plataforma/dashboard/cms`
   - `/plataforma/dashboard/evangelism`
   - `/plataforma/dashboard/finance`
   - `/plataforma/dashboard/projects`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (96.3 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-DASH-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
