# Auditoría Forense Integral: Módulo Soporte y Mesa de Ayuda (Tickets, FAQs, Tutoriales e Historial) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `support` (Soporte Técnico, Mesa de Ayuda, Tickets Eclesiales, FAQs, Base de Conocimiento KB, Tutoriales e Historial)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-SUPPORT-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.3 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Soporte y Mesa de Ayuda (`support`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales, operativas y documentales:
- **Backend y Endpoints Transversales:**
  - `backend/api/support.py` (120 líneas): gestión y ciclo de vida de tickets con RBAC de administrador y plataforma, aislamiento multi-tenant por sede y vinculación estricta de actor.
  - `backend/api/support_kb.py` (95 líneas): catálogo de categorías y artículos de la Base de Conocimiento (Knowledge Base).
  - `backend/crud/crm_/support.py` (112 líneas): operaciones CRUD de tickets con soft-delete persistido en `deleted_at`.
  - `backend/models_crm.py`: modelo ORM `SupportTicket` con PK UUIDv4, FK a `personas.id` y FK a `sedes.id`.
  - `backend/schemas/operational.py`: esquemas Pydantic `SupportTicketCreate` y `SupportTicket`.
- **Frontend y Vistas Operativas (7 Archivos Canónicos):**
  1. `frontend/src/app/plataforma/support/page.tsx` (Hub Central de Soporte)
  2. `frontend/src/app/plataforma/support/layout.tsx` (Layout Base y Navegación de Soporte)
  3. `frontend/src/app/plataforma/support/tickets/page.tsx` (Gestor y Vista Detallada de Tickets)
  4. `frontend/src/app/plataforma/support/history/page.tsx` (Historial de Solicitudes y Atenciones)
  5. `frontend/src/app/plataforma/support/tutorials/page.tsx` (Centro de Tutoriales y Guías de Uso)
  6. `frontend/src/app/plataforma/support/contact/page.tsx` (Formulario Canónico de Contacto)
  7. `frontend/src/app/plataforma/support/kb/page.tsx` (Explorador de Base de Conocimientos KB)
- **Suites de Pruebas y Aseguramiento:** 63 pruebas automatizadas en total, destacando 15 pruebas de aislamiento y cobertura en `tests/test_support_sede_isolation.py`, `tests/test_support_tables_api.py` y `tests/test_support_coverage.py`.
- **Documentación Canónica:** `docs/ESTADO_SUPPORT.md`, `docs/AUDITORIA_FORENSE_SUPPORT.md` y `docs/WORKSPACE_QA_CHECKLIST.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. En `backend/models_crm.py:1140`, `SupportTicket.user_id` refiere obligatoriamente a `personas.id` (`ForeignKey("personas.id")`). En `backend/api/support.py`, `create_support_ticket` resuelve la persona canónica mediante `resolve_persona_id_for_user(db, current_user.id)`. Cero tablas paralelas de personas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Columnas `created_at`, `updated_at`, `deleted_at` son `DateTime(timezone=True)`. Backend opera con `_utcnow()` (`dt.datetime.now(dt.timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100% (0 ocurrencias). Soft-delete activo en `deleted_at` (QC-06).
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. `_actor_sede_uuid(db, current_user, persona_id)` obtiene `sede_id` de la persona autenticada; usuarios sin sede reciben `HTTPException(403)`. Administradores de sede no pueden listar ni mutar tickets de sedes ajenas (`tests/test_support_sede_isolation.py`).
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0) en los 7 archivos de frontend. La navegación y visualización de tickets se estructura mediante rutas y paneles dedicados.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 62%):** **Hallazgo H-SUPP-01**. Se detectan **90 clases Tailwind hardcodeadas** (`bg-white`, `border-white`, `text-white`, `bg-black/20`, etc.) y **145 selectores `dark:`** en los 7 archivos de frontend.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 7 archivos auditados utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación unificada bajo `/plataforma/support/...`.
8. **Compilación y Pruebas Backend (100%):** Suites dedicadas con 63 pruebas automatizadas. Balance sintáctico estricto en los 7 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `SupportTicket.user_id` FK directa a `personas.id`. Resolución de actor vía `resolve_persona_id_for_user`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Cero llamadas a `datetime.utcnow()`. Soft-delete activo en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** `_actor_sede_uuid` inyecta sede canónica. Filtro estricto en listados y mutaciones. Suites de aislamiento adversarial verificadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 7 archivos auditados. 0 modales centrados (`AlertDialog` = 0). Navegación canónica fluida. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (62%). Hallazgo H-SUPP-01.** 90 clases Tailwind hardcodeadas y 145 selectores `dark:` en los 7 archivos de Soporte. | 15% | **62/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 7 archivos auditados. Cero llamadas a `fetch()` crudo. 100% de consultas gestionadas a través de `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 63 tests automatizados en backend (`test_support_coverage.py`, `test_support_sede_isolation.py`, `test_support_tables_api.py`, etc.). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** `docs/ESTADO_SUPPORT.md`, `docs/AUDITORIA_FORENSE_SUPPORT.md` y `docs/WORKSPACE_QA_CHECKLIST.md` sincronizados. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (62 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.30 + 10.0 + 10.0 + 5.0 = \mathbf{89.30 / 100} \approx \mathbf{89.3 / 100}$$

**Calificación Inicial:** **Grado A (89.3 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Soporte y Mesa de Ayuda cuenta con una arquitectura de backend ejemplar: vinculación canónica a `personas.id` (Axioma 1), UTC estricto con soft-deletes (Axioma 2), y aislamiento multi-tenant validado adversarialmente (Axioma 3). En la interfaz de usuario no existen modales centrados (0 `AlertDialog`), pero se identifica el hallazgo **H-SUPP-01** (90 clases Tailwind hardcodeadas y 145 selectores `dark:` en los 7 archivos). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 7 Archivos de Frontend de Soporte

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/support/layout.tsx` | 56 | 0 | 1 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-SUPP-01) |
| 2 | `frontend/src/app/plataforma/support/history/page.tsx` | 118 | 4 | 13 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-SUPP-01) |
| 3 | `frontend/src/app/plataforma/support/tutorials/page.tsx` | 109 | 12 | 15 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-SUPP-01) |
| 4 | `frontend/src/app/plataforma/support/contact/page.tsx` | 172 | 15 | 28 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-SUPP-01) |
| 5 | `frontend/src/app/plataforma/support/kb/page.tsx` | 252 | 8 | 18 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-SUPP-01) |
| 6 | `frontend/src/app/plataforma/support/tickets/page.tsx` | 281 | 12 | 25 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-SUPP-01) |
| 7 | `frontend/src/app/plataforma/support/page.tsx` | 432 | 39 | 45 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-SUPP-01) |
| **TOTAL** | **7 Archivos Auditados** | **1,420** | **90** | **145** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-SUPP-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Layout, Historial, Tutoriales y Contacto (`TKT-SUPP-REMEDIATION-01`)
- **Archivos a intervenir (4 archivos):**
  1. `frontend/src/app/plataforma/support/layout.tsx` (0 clases TW + 1 `dark:`)
  2. `frontend/src/app/plataforma/support/history/page.tsx` (4 clases TW + 13 `dark:`)
  3. `frontend/src/app/plataforma/support/tutorials/page.tsx` (12 clases TW + 15 `dark:`)
  4. `frontend/src/app/plataforma/support/contact/page.tsx` (15 clases TW + 28 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind (`bg-white/5`, `border-white/5`, `border-white/10`, `text-white`, `to-orange-600`, etc.) por tokens semánticos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes.
- **Total incidencias a erradicar:** 31 clases TW / 57 selectores `dark:`.
- **Commit atómico:** `feat(support): Remediación de Tokens Semánticos en Layout, Historial, Tutoriales y Contacto (H-SUPP-01 Fase 1)`.

### Fase 2: Base de Conocimientos (KB), Tickets y Hub Principal (`TKT-SUPP-REMEDIATION-02`)
- **Archivos a intervenir (3 archivos):**
  1. `frontend/src/app/plataforma/support/kb/page.tsx` (8 clases TW + 18 `dark:`)
  2. `frontend/src/app/plataforma/support/tickets/page.tsx` (12 clases TW + 25 `dark:`)
  3. `frontend/src/app/plataforma/support/page.tsx` (39 clases TW + 45 `dark:`)
- **Acciones específicas:**
  - Sustituir clases Tailwind hardcodeadas (`bg-white`, `bg-white/5`, `bg-white/10`, `border-white/5`, `border-white/10`, `text-white`, `bg-black/20`, etc.) por tokens semánticos del Design System.
  - Erradicar selectores `dark:` y opacidades no semánticas.
  - Preservar 0 modales centrados y 100% `apiFetch`.
- **Total incidencias a erradicar:** 59 clases TW / 88 selectores `dark:`.
- **Commit atómico:** `feat(support): Remediación de Tokens Semánticos en Base de Conocimientos, Tickets y Hub (H-SUPP-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-SUPP-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 7 archivos.
3. Se procederá con `TKT-SUPP-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/support`
   - `/plataforma/support/tickets`
   - `/plataforma/support/history`
   - `/plataforma/support/tutorials`
   - `/plataforma/support/contact`
   - `/plataforma/support/kb`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.3 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-SUPP-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
