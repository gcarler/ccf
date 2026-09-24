# Auditoría Forense Integral: Módulo Grupos de Vida y Células Eclesiales (groups) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Inicial)  
**Módulo Auditado:** `groups` (Grupos de Vida, Red Celular Eclesial, Familias Espirituales, Histórico de Asistencia, Analítica Celular y Mapeo Geoespacial)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-GROUPS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Grupos de Vida y Células Eclesiales (`groups`)** de la Plataforma CCF, cubriendo la infraestructura frontend en Next.js 15, su vinculación canónica con el Kernel de Personas (`Axioma 1`), la consistencia cronológica en UTC y soft-deletes (`Axioma 2`), el aislamiento multi-tenant por sede territorial (`Axioma 3`), la prohibición de modales centrados (`AlertDialog` = 0 / uso de Drawers), la conformidad con los tokens semánticos CSS del Design System CCF y la suite de pruebas backend:
- **Estructura Operativa y Vistas Auditadas (5 Vistas Canónicas — 761 Líneas):**
  1. `frontend/src/app/plataforma/groups/page.tsx` (88 líneas): Tablero principal de grupos de vida, resumen de células activas y navegación contextual.
  2. `frontend/src/app/plataforma/groups/family/page.tsx` (155 líneas): Módulo de familias de grupos y árboles celulares espirituales.
  3. `frontend/src/app/plataforma/groups/history/page.tsx` (150 líneas): Registro cronológico e histórico de reuniones, reportes semanales y asistencias.
  4. `frontend/src/app/plataforma/groups/analytics/page.tsx` (195 líneas): Métricas analíticas de crecimiento celular, conversión, multiplicación y retención.
  5. `frontend/src/app/plataforma/groups/map/page.tsx` (173 líneas): Visualización cartográfica y geoespacial de células en el territorio.
- **Integración con Modelos y Backend:**
  - Persistencia canónica en base de datos (`backend/crud/crm_/groups.py` y modelos de evangelismo/comunidad).
  - Vínculo 1:1 de anfitriones y líderes celulares hacia `personas.id` (`auth_users.id`).
  - Suite de pruebas backend `tests/test_crm_crud_groups.py` ejecutada con éxito (40/40 tests passing, 100% OK en 9.55s).
- **Documentación Canónica:**
  - `docs/CRM_API_CONTRACTS.md`, `docs/PLATAFORMA_AUTH_RBAC_API_UI.md` y `docs/PLATAFORMA_MATRIZ_MODULAR.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. Toda persona involucrada en un grupo (líder, colíder, anfitrión, asistente) referencia la identidad única en `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Fechas de reunión, reportes de asistencia y auditoría temporal manejadas en UTC (`datetime.now(timezone.utc)` / `_utcnow()`). Borrado lógico implementado con `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. Los grupos celulares y sus reportes se segregan estrictamente por `sede_id` del usuario autenticado (`get_user_sede_id()`).
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0, `Dialog` = 0). Las interacciones operan con paneles laterales deslizantes y layouts directos.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-GRP-01**. Se detectan **78 clases Tailwind hardcodeadas** (`bg-white`, `text-gray-*`, `bg-gray-*`, `border-gray-*`, `bg-blue-*`, etc.) y **68 selectores `dark:`** distribuidos entre las 5 vistas del módulo.
6. **Regla Frontend 3 (Cliente HTTP y Rutas Canónicas — 100%):** 100% `apiFetch()` para peticiones internas (0 `fetch()` crudo). Rutas con prefijo canónico `/plataforma/groups/...`.
7. **Compilación y Pruebas Backend (100%):** Cobertura exhaustiva en `tests/test_crm_crud_groups.py` (40 de 40 pruebas aprobadas, 100% OK en 9.55s) y balance sintáctico estricto en frontend (`curlies=0, parens=0, brackets=0`).
8. **Estado Documental (100%):** Documentación ministerial y técnica plenamente sincronizada.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Líderes y asistentes vinculados a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps y bajas lógicas (`deleted_at`) en UTC canónico. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Segregación celular por `sede_id`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers/Wizards | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Flujos laterales y tableros. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-GRP-01.** 78 clases Tailwind hardcodeadas y 68 selectores `dark:` redundantes. | 15% | **60/100** | 🟡 **REQUIERE FASE 1** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; rutas canónicas `/plataforma/...` | **Cumplimiento pleno (100%).** 100% `apiFetch()`. Rutas prefijadas con `/plataforma/groups/...`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** `test_crm_crud_groups.py` pasando 40/40 tests (100% OK). Balance sintáctico estricto. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Arquitectura y contratos celulares alineados con el estándar de plataforma. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Grupos de Vida y Células Eclesiales (`groups`) exhibe una arquitectura sólida, con validación backend impecable (40/40 tests aprobados) y aislamiento multi-tenant estricto. Se detecta el hallazgo **H-GRP-01** (68 selectores `dark:` y 78 clases Tailwind hardcodeadas) distribuido en las 5 vistas. Se aprueba condicionado a su remediación técnica inmediata.

---

## 4. Inventario Detallado de las Vistas Frontend de Groups

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/groups/page.tsx` | 88 | **2** | **2** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-GRP-01) |
| 2 | `frontend/src/app/plataforma/groups/family/page.tsx` | 155 | **33** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-GRP-01) |
| 3 | `frontend/src/app/plataforma/groups/history/page.tsx` | 150 | **14** | **20** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-GRP-01) |
| 4 | `frontend/src/app/plataforma/groups/analytics/page.tsx` | 195 | **13** | **19** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-GRP-01) |
| 5 | `frontend/src/app/plataforma/groups/map/page.tsx` | 173 | **16** | **27** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-GRP-01) |
| **TOTAL** | **5 Vistas Canónicas** | **761** | **78** | **68** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en Fases Atómicas

Para subsanar el Hallazgo **H-GRP-01**, se establece la siguiente fase atómica de remediación:

### Fase 1: Remediación de Tokens Semánticos en Grupos de Vida (`TKT-GRP-REMEDIATION-01`)
- **Archivos a intervenir (5 archivos — 761 líneas):**
  1. `frontend/src/app/plataforma/groups/page.tsx` (2 TW / 2 `dark:`)
  2. `frontend/src/app/plataforma/groups/family/page.tsx` (33 TW / 0 `dark:`)
  3. `frontend/src/app/plataforma/groups/history/page.tsx` (14 TW / 20 `dark:`)
  4. `frontend/src/app/plataforma/groups/analytics/page.tsx` (13 TW / 19 `dark:`)
  5. `frontend/src/app/plataforma/groups/map/page.tsx` (16 TW / 27 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `text-gray-*`, `bg-gray-*`, `border-gray-*`, `bg-blue-*`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))` y `hsl(var(--destructive))`.
  - Erradicar 68 selectores `dark:` redundantes en las 5 vistas.
  - Preservar la arquitectura reactiva, los Drawers y tableros (0 modales centrados / `AlertDialog` = 0) y el balance sintáctico estricto (`c:0 p:0 b:0`).
  - Preservar las rutas canónicas `/plataforma/groups/...`.
- **Total incidencias a erradicar:** 78 clases TW / 68 selectores `dark:`.
- **Commit atómico:** `feat(groups): Remediación de Tokens Semánticos en Grupos de Vida y Células Eclesiales (H-GRP-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-GRP-FINAL-CERTIFICATION`)
- Validar la erradicación total de clases Tailwind no semánticas (0 residuales) en las 5 vistas.
- Actualizar `AUDITORIA_FORENSE_GRUPOS_2026-09-24.md` con la nota certificada de **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final sin observaciones pendientes.
- **Commit atómico:** `docs(groups): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final del Módulo Grupos de Vida y Células Eclesiales`.

---

## 6. Certificación Final y Despliegue Proyectados (`TKT-GRP-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Se ejecutará el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh`.
2. Se verificará en vivo la respuesta HTTP 200 OK y latencia en milisegundos en las 5 rutas canónicas del módulo:
   - `/plataforma/groups`
   - `/plataforma/groups/family`
   - `/plataforma/groups/history`
   - `/plataforma/groups/analytics`
   - `/plataforma/groups/map`
3. Se registrará la telemetría en vivo en las Secciones 6 y 7 de la auditoría y se emitirá el commit atómico `feat(groups): Despliegue Staging y Verificación en Vivo del Módulo Grupos de Vida y Células Eclesiales`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Grupos de Vida y Células Eclesiales (`groups`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-GRP-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
