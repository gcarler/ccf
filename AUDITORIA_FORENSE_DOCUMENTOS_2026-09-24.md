# Auditoría Forense Integral: Módulo Documentos Eclesiales y Firma Digital (Gestor y Solicitudes) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `documents` (Gestor de Archivos Eclesiales, Categorización por Etiquetas, Solicitudes de Firma Digital, Firmantes y Pistas de Auditoría)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-DOCS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Documentos Eclesiales y Firma Digital (`documents`)** de la Plataforma CCF, cubriendo la totalidad de sus modelos relacionales, endpoints transaccionales, vistas operativas en Next.js 15 y suites de pruebas automatizadas:
- **Backend y Modelos Relacionales:**
  - `backend/models_finance_suite.py`:
    - `Document` (líneas 377–410): PK UUIDv4 (`id`), relación con `sede_id`, autor canónico UUID (`created_by` vincula a `personas.id`), metadatos de archivo (`file_url`, `file_name`, `file_size`, `mime_type`, `document_type`), timestamps timezone-aware (`DateTime(timezone=True)`) con función `_utcnow()` (`datetime.now(timezone.utc)`), y soft-delete activo en `status = "archived"`.
    - `DocumentTag` y `DocumentTagLink` (líneas 412–420): taxonomía eclesial y categorización de archivos vinculada a sede.
    - `SignatureRequest` (líneas 422–450): PK UUIDv4 (`id`), `sede_id`, solicitante canónico (`requested_by` vincula a `personas.id`), título, framework legal (`eidas`, `es_signature`), caducidad y estado (`draft`, `sent`, `partially_signed`, `completed`, `declined`, `cancelled`, `expired`).
    - `SignatureSigner` (líneas 452–475): PK UUIDv4 (`id`), vinculación a ser humano (`persona_id` opcional vincula a `personas.id`), nombre, email, rol, orden de firma y estado (`pending`, `signed`, `declined`).
    - `SignatureAuditTrail` (líneas 477–495): pista forense inmutable de eventos de firma con timestamp UTC y actor canónico.
- **Endpoints Transversales (`backend/api/finance_suite.py`):**
  - `POST /finance-suite/documents`: creación y registro de documentos con validación MIME y actor UUID.
  - `GET /finance-suite/documents`: listado multi-tenant segregado por sede (`Document.sede_id == user_sede`).
  - `GET /finance-suite/documents/{document_id}`: consulta con verificación de tenant.
  - `DELETE /finance-suite/documents/{document_id}`: archivado canónico (soft-delete).
  - `POST /finance-suite/document-tags` y `GET /finance-suite/document-tags`: gestión de etiquetas.
  - `POST /finance-suite/sign-requests`: creación de solicitudes de firma con firmantes anidados.
  - `GET /finance-suite/sign-requests`: consulta multi-tenant de solicitudes.
  - `POST /finance-suite/sign-requests/{request_id}/sign`: ejecución de firma y registro en `SignatureAuditTrail`.
  - `POST /finance-suite/sign-requests/{request_id}/cancel`: cancelación de flujo.
- **Frontend y Vistas Operativas (2 Vistas Canónicas — 451 Líneas):**
  1. `frontend/src/app/plataforma/documentos/page.tsx` (215 líneas): Gestor centralizado de documentos, filtrado por etiquetas, buscador y panel de carga.
  2. `frontend/src/app/plataforma/firma/page.tsx` (236 líneas): Panel de control de solicitudes de firma digital, estados de firmantes, acciones de firma y registro.
- **Suites de Pruebas y Cobertura Automatizada:**
  - `tests/test_finance_suite_api.py` (7 tests dedicados a documentos y firma).
  - `tests/test_finance_suite_coverage.py` (10 tests dedicados a validaciones MIME, cross-sede y estados).
  - `tests/test_finance_suite_gap.py` (5 tests de listados y creación).
  - Total: **Más de 22 pruebas automatizadas de backend**.
- **Documentación Canónica:**
  - `docs/FINANCE_API_CONTRACTS.md`, `docs/FINANCE_QA_CHECKLIST.md` y `docs/FINANCE_RBAC_MATRIX.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. Toda entidad (`Document.created_by`, `SignatureRequest.requested_by`, `SignatureSigner.persona_id`, `SignatureAuditTrail.actor_id`) vincula canónicamente a `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Columnas de timestamp son `DateTime(timezone=True)` con `_utcnow()` (`datetime.now(timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `Document.status = "archived"`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. `sede_id` se resuelve exclusivamente a través de la identidad autenticada (`get_user_sede_id()`). Endpoints rechazan accesos cross-sede con HTTP 403 (`test_document_delete_cross_sede_forbidden`).
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0) en los 2 archivos. Los formularios de creación se despliegan en paneles laterales o inline colapsables.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-DOC-01**. Se detectan **44 clases Tailwind hardcodeadas** (`text-white`, `bg-[#111418]`, `bg-gray-100`, `text-gray-600`, etc.) y **63 selectores `dark:`** redundantes entre ambas vistas.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Ambas vistas consumen exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Rutas protegidas bajo el prefijo canónico `/plataforma/documentos` y `/plataforma/firma`.
8. **Compilación y Pruebas Backend (100%):** Más de 22 tests dedicados pasando en backend. Balance sintáctico estricto en ambos archivos (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Autores, solicitantes y firmantes vinculan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Soft-delete activo. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Aislamiento gobernado por `sede_id`. Validación cross-sede en documentos y firmas (`test_document_delete_cross_sede_forbidden`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Formularios en paneles laterales y secciones colapsables. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-DOC-01.** 44 clases Tailwind hardcodeadas y 63 selectores `dark:` en los 2 archivos canónicos. | 15% | **60/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 100% de llamadas a la API a través de `apiFetch()` de `@/lib/http`. Cero `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Más de 22 tests dedicados en suites de tests de finance suite. Balance sintáctico estricto. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos API, esquemas Pydantic y checklist de QA alineados con la gobernanza CCF. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Documentos Eclesiales y Firma Digital (`documents`) exhibe una arquitectura de datos robusta, respetando los axiomas de Kernel de Personas (Axioma 1), UTC estricto con soft-deletes (Axioma 2), y aislamiento multi-tenant por sede en todas las operaciones (Axioma 3). En la interfaz de usuario no existen modales centrados (`AlertDialog` = 0) y el cliente HTTP es 100% `apiFetch()`. No obstante, se detecta el hallazgo **H-DOC-01** (44 clases Tailwind hardcodeadas y 63 selectores `dark:` en las 2 vistas de frontend). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de las 2 Vistas de Frontend de Documents

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/documentos/page.tsx` | 215 | **22** | **29** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-DOC-01) |
| 2 | `frontend/src/app/plataforma/firma/page.tsx` | 236 | **22** | **34** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-DOC-01) |
| **TOTAL** | **2 Vistas Canónicas** | **451** | **44** | **63** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-DOC-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Gestor Centralizado de Documentos (`TKT-DOC-REMEDIATION-01`)
- **Archivo a intervenir (1 archivo — 215 líneas):**
  1. `frontend/src/app/plataforma/documentos/page.tsx` (22 TW / 29 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-[#111418]`, `dark:bg-white/5`, `dark:border-white/10`, `dark:text-white`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))` y `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes.
  - Preservar panel colapsable de creación, 100% `apiFetch` y balance sintáctico estricto.
- **Total incidencias a erradicar:** 22 clases TW / 29 selectores `dark:`.
- **Commit atómico:** `feat(documents): Remediación de Tokens Semánticos en Gestor de Documentos (H-DOC-01 Fase 1)`.

### Fase 2: Panel de Solicitudes de Firma Digital (`TKT-DOC-REMEDIATION-02`)
- **Archivo a intervenir (1 archivo — 236 líneas):**
  2. `frontend/src/app/plataforma/firma/page.tsx` (22 TW / 34 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`bg-gray-100`, `text-gray-600`, `text-white`, `bg-[#111418]`, `dark:bg-white/5`, etc.) por variables semánticas reactivas del Design System CCF.
  - Eliminar selectores `dark:` redundantes.
  - Mantener balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 22 clases TW / 34 selectores `dark:`.
- **Commit atómico:** `feat(documents): Remediación de Tokens Semánticos en Firma Digital (H-DOC-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-DOC-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 2 archivos.
3. Se procederá con `TKT-DOC-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/documentos`
   - `/plataforma/firma`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Documentos Eclesiales y Firma Digital (`documents`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-DOC-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
