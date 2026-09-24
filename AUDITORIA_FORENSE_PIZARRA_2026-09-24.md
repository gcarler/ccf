# Auditoría Forense Integral: Módulo Pizarra Eclesial Colaborativa (Canvas, Herramientas, Comentarios y WebSocket) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `whiteboard` (Pizarra Eclesial Interactiva, Canvas Colaborativo, Herramientas de Dibujo, Comentarios y WebSocket en Tiempo Real)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-WHITEBOARD-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Pizarra Eclesial Colaborativa (`whiteboard`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales, servicios de canvas interactivo, protocolo WebSocket de sincronización y suites de pruebas automatizadas:
- **Backend y Endpoints Transversales:**
  - `backend/models_projects.py` (líneas 84–98): modelo canónico transaccional `ProjectWhiteboard`. PK UUIDv4 (`id`), relación 1:1 con `Project` (`project_id`), `elements_json` validado, `thumbnail_url`, timestamps timezone-aware (`DateTime(timezone=True)`) con `_utcnow` (`datetime.now(timezone.utc)`), y soft-delete activo en `deleted_at`.
  - `backend/api/projects.py`:
    - `GET /projects/whiteboards`: listado multi-tenant segregado por sede (`Project.sede_id == user_sede`).
    - `GET /projects/{project_id}/whiteboard`: consulta de pizarra con validación de sede.
    - `POST /projects/{project_id}/whiteboard`: guardado con `_validate_whiteboard_json` y actor canónico UUID.
    - `DELETE /projects/{project_id}/whiteboard`: soft-delete canónico `deleted_at = _utcnow()`.
    - `POST /projects/{project_id}/whiteboard/thumbnail`: subida segura de miniatura con `storage_service`.
    - `WebSocket /projects/{project_id}/whiteboard/ws`: colaboración en tiempo real con aislamiento por sala de proyecto y verificación de token/sede.
- **Frontend y Vistas Operativas (5 Archivos Canónicos — 3,375 Líneas):**
  1. `frontend/src/app/plataforma/whiteboard/page.tsx` (209 líneas): Hub principal de pizarras, tarjetas con previsualización, filtros y estados vacíos.
  2. `frontend/src/app/plataforma/whiteboard/[id]/page.tsx` (56 líneas): Vista de carga y renderizado de la pizarra específica por ID.
  3. `frontend/src/app/plataforma/whiteboard/new/page.tsx` (214 líneas): Asistente de creación de nueva pizarra vinculada a proyectos.
  4. `frontend/src/components/whiteboard/WhiteboardComments.tsx` (81 líneas): Panel lateral deslizante de comentarios e hilos colaborativos.
  5. `frontend/src/components/whiteboard/WhiteboardEditor.tsx` (2,815 líneas): Editor central de pizarra con canvas interactivo, barra de herramientas, paleta de colores, capas, formas y sincronización WebSocket.
- **Suites de Pruebas y Aseguramiento:**
  - `tests/test_projects_whiteboard_roundtrip.py` (20 pruebas): validación de JSON estricto, payloads malformados, roundtrip POST -> GET, soft-delete, restauración y subida de miniaturas.
  - `tests/test_projects_whiteboard_websocket.py` (11 pruebas): seguridad WebSocket, rechazo sin token, aislamiento multi-tenant cross-sede, broadcasting de cursores y replicación de objetos.
  - Total: **31 pruebas automatizadas de backend**.
- **Documentación Canónica:**
  - `docs/PROJECTS_API_CONTRACTS.md`, `docs/PROJECTS_QA_CHECKLIST.md` y `docs/PROJECTS_RBAC_MATRIX.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. Toda pizarra está subordinada a un `Project` cuyo `owner_id` vincula a `personas.id`. Los comentarios en `WhiteboardComments.tsx` resuelven a `auth_users.id` (`personas.id`). En logs de actividad `ProjectActivityLog.persona_id` vincula a `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Columnas `created_at`, `updated_at` y `deleted_at` tipadas con `DateTime(timezone=True)` usando `_utcnow()` (`datetime.now(timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. `Project.sede_id` gobierna el acceso. Endpoints REST y conexión WebSocket rechazan accesos cross-sede (`test_whiteboard_ws_rejects_cross_sede_project`).
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0) en los 5 archivos. Los comentarios y herramientas se integran mediante paneles laterales deslizantes.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-WHT-01**. Se detectan **115 clases Tailwind hardcodeadas** (`text-white`, `bg-white/5`, `bg-blue-500`, `text-gray-400`, `bg-black/20`, etc.) y **124 selectores `dark:`** distribuidos en los 5 archivos del módulo.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** El cliente `frontend/src/lib/whiteboards.ts` y todos los hooks consumen exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Rutas protegidas bajo el prefijo canónico `/plataforma/whiteboard/...`.
8. **Compilación y Pruebas Backend (100%):** 31 tests dedicados pasando en backend. Balance sintáctico estricto en los 5 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `Project.owner_id` y autores de comentarios vinculan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Soft-delete en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Aislamiento gobernado por `Project.sede_id`. Validación en REST y WebSocket (`test_whiteboard_ws_rejects_cross_sede_project`). | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0) en los 5 archivos. Paneles laterales para comentarios y controles. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-WHT-01.** 115 clases Tailwind hardcodeadas y 124 selectores `dark:` en los 5 archivos canónicos. | 15% | **60/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 100% de llamadas a la API a través de `apiFetch()` en `whiteboards.ts` y hooks. Cero `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 31 tests dedicados en `test_projects_whiteboard_roundtrip.py` y `test_projects_whiteboard_websocket.py`. Balance sintáctico estricto. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos API y documentación alineados con la arquitectura de proyectos. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Pizarra Eclesial Colaborativa (`whiteboard`) cuenta con una sólida arquitectura backend, cumpliendo los axiomas de Kernel de Personas (Axioma 1), UTC estricto con soft-deletes (Axioma 2), y aislamiento multi-tenant con validación tanto en endpoints REST como en el protocolo WebSocket en tiempo real (Axioma 3, respaldado por 31 tests). En la interfaz de usuario no existen modales centrados (`AlertDialog` = 0) y el cliente HTTP es 100% `apiFetch()`. No obstante, se detecta el hallazgo **H-WHT-01** (115 clases Tailwind hardcodeadas y 124 selectores `dark:` en los 5 archivos de frontend). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 5 Archivos de Frontend de Whiteboard

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/whiteboard/page.tsx` | 209 | **7** | **12** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WHT-01) |
| 2 | `frontend/src/app/plataforma/whiteboard/[id]/page.tsx` | 56 | **2** | **3** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WHT-01) |
| 3 | `frontend/src/app/plataforma/whiteboard/new/page.tsx` | 214 | **9** | **12** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WHT-01) |
| 4 | `frontend/src/components/whiteboard/WhiteboardComments.tsx` | 81 | **17** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WHT-01) |
| 5 | `frontend/src/components/whiteboard/WhiteboardEditor.tsx` | 2,815 | **80** | **97** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-WHT-01) |
| **TOTAL** | **5 Archivos Canónicos** | **3,375** | **115** | **124** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-WHT-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Vistas y Paneles Auxiliares (`TKT-WHT-REMEDIATION-01`)
- **Archivos a intervenir (4 archivos — 560 líneas):**
  1. `frontend/src/app/plataforma/whiteboard/page.tsx` (7 TW / 12 `dark:`)
  2. `frontend/src/app/plataforma/whiteboard/[id]/page.tsx` (2 TW / 3 `dark:`)
  3. `frontend/src/app/plataforma/whiteboard/new/page.tsx` (9 TW / 12 `dark:`)
  4. `frontend/src/components/whiteboard/WhiteboardComments.tsx` (17 TW / 0 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`text-white`, `bg-white/5`, `bg-blue-500`, `text-gray-400`, `border-gray-200`, etc.) por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))` y `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes.
  - Preservar panel lateral de comentarios, 100% `apiFetch` y balance sintáctico estricto.
- **Total incidencias a erradicar:** 35 clases TW / 27 selectores `dark:`.
- **Commit atómico:** `feat(whiteboard): Remediación de Tokens Semánticos en Vistas de Pizarra y Comentarios (H-WHT-01 Fase 1)`.

### Fase 2: Editor Canónico de Pizarra (`TKT-WHT-REMEDIATION-02`)
- **Archivo a intervenir (1 archivo — 2,815 líneas):**
  5. `frontend/src/components/whiteboard/WhiteboardEditor.tsx` (80 TW / 97 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas y selectores `dark:` en barras de herramientas, paleta de colores, selector de trazo, zoom, capas y badges de colaboradores.
  - Implementar tokens semánticos reactivos preservando la compatibilidad con el motor de renderizado canvas.
  - Mantener balance sintáctico estricto (`c:0 p:0 b:0`).
- **Total incidencias a erradicar:** 80 clases TW / 97 selectores `dark:`.
- **Commit atómico:** `feat(whiteboard): Remediación de Tokens Semánticos en WhiteboardEditor (H-WHT-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-WHT-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 5 archivos.
3. Se procederá con `TKT-WHT-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/whiteboard`
   - `/plataforma/whiteboard/new`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Pizarra Eclesial Colaborativa (`whiteboard`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-WHT-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
