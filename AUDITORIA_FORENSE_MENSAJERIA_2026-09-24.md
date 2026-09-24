# Auditoría Forense Integral: Módulo Mensajería Eclesial, Chat e Inbox (Conversaciones, Drawers y Bandeja) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `messaging` (Mensajería Directa Eclesial, Chat en Tiempo Real, Bandeja de Entrada Unificada Inbox, Comentarios y NewConversationDrawer)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-MESSAGING-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Mensajería Eclesial, Chat e Inbox (`messaging`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales, operativas y documentales:
- **Backend y Endpoints Transversales:**
  - `backend/models_crm.py` (líneas 31–83): modelos transaccionales `ChatMessage`, `Conversation` y `ConversationParticipant`. Claves primarias UUIDv4, `sender_id` con FK a `auth_users.id` (`personas.id`), `ConversationParticipant.user_id` con FK a `auth_users.id` y soft-deletes activos.
  - `backend/api/messaging.py`: endpoints transaccionales `/messaging/conversations`, `/messaging/conversations/{id}/messages`, `/messaging/send`, `/messaging/unread-count`, `/messaging/search`.
  - `backend/api/chat.py`: endpoints de chat en tiempo real, canales ministeriales, mensajes directos y soporte para adjuntos.
  - `backend/api/comments.py`: gestión de hilos de comentarios transversales.
  - `backend/services/messaging.py` y `backend/services/messaging_outcomes.py`: lógica de negocio para despacho de notificaciones, métricas de respuesta y trazabilidad pastoral.
- **Frontend y Vistas Operativas (11 Archivos Canónicos):**
  1. `frontend/src/app/plataforma/messages/page.tsx` (Hub de Mensajería Directa)
  2. `frontend/src/app/plataforma/messages/_components/ConversationSidebar.tsx` (Lista de Conversaciones y Filtros)
  3. `frontend/src/app/plataforma/messages/_components/MessageBubble.tsx` (Burbujas de Chat, Adjuntos y Estados de Entrega)
  4. `frontend/src/app/plataforma/messages/_components/MessageInput.tsx` (Entrada de Texto, Emojis y Subida de Archivos)
  5. `frontend/src/app/plataforma/messages/_components/MessageList.tsx` (Contenedor de Hilos y Scroll Automático)
  6. `frontend/src/app/plataforma/messages/_components/NewConversationDrawer.tsx` (Panel Deslizante Canónico de Nueva Conversación)
  7. `frontend/src/app/plataforma/inbox/page.tsx` (Bandeja Unificada de Entrada)
  8. `frontend/src/app/plataforma/inbox/layout.tsx` (Layout de Bandeja de Entrada)
  9. `frontend/src/app/plataforma/inbox/chat/page.tsx` (Vista de Chats en Bandeja)
  10. `frontend/src/app/plataforma/inbox/comments/page.tsx` (Gestor de Comentarios en Bandeja)
  11. `frontend/src/app/plataforma/inbox/messages/page.tsx` (Enrutamiento Auxiliar de Mensajes)
- **Suites de Pruebas y Aseguramiento:** 217 pruebas automatizadas en backend distribuidas en 18 suites dedicadas (`test_chat_100pct_coverage.py` [41], `test_chat_sede_isolation.py` [24], `test_messaging_audit_phase1.py` [24], `test_chat_api.py` [16], `test_messaging_security_gaps.py` [15], `test_crm_crud_extended_chat.py` [12], `test_messaging_fase4_owner_and_crud_layer.py` [11], `test_projects_chat_websocket.py` [10], `test_comments_me.py` [9], `test_chat_extended.py` [9], etc.).
- **Documentación Canónica:** `docs/ESTADO_MESSAGING_COMMUNITY.md`, `docs/MESSAGING_COMMUNITY_API_CONTRACTS.md`, `docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md` y `docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. En `backend/models_crm.py`, `ChatMessage.sender_id` y `ConversationParticipant.user_id` vinculan directamente a `auth_users.id`, tabla que comparte 1:1 el mismo UUID con `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Columnas `created_at`, `updated_at`, `last_message_at` y `deleted_at` tipadas con `DateTime(timezone=True)`. Backend opera con `_utcnow()` (`datetime.now(timezone.utc)`). Prohibición absoluta de `datetime.utcnow()` respetada al 100%. Soft-delete activo en `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. Conversaciones y canales de chat subordinados al contexto de sede del usuario autenticado (`get_user_sede_id()`). Suites de aislamiento multi-tenant en `tests/test_chat_sede_isolation.py` (24 tests) y `tests/test_messaging_sede_isolation.py` (7 tests) validan la segregación total de datos entre sedes.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0) en los 11 archivos de frontend. La creación de conversaciones se realiza exclusivamente a través de `NewConversationDrawer` (panel lateral deslizante derecho).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 65%):** **Hallazgo H-MSG-01**. Se detectan **85 clases Tailwind hardcodeadas** (`bg-blue-500`, `text-gray-400`, `border-gray-200`, `bg-white`, `text-white`, `bg-red-500`, etc.) y **118 selectores `dark:`** en 9 de los 11 archivos de frontend.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 11 archivos auditados y sus hooks asociados (`useChatThread.ts`, `useConversations.ts`, `useUserSearch.ts`) utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación bajo `/plataforma/messages`, `/plataforma/inbox`, `/plataforma/inbox/chat` y `/plataforma/inbox/comments`.
8. **Compilación y Pruebas Backend (100%):** Suites dedicadas con 217 pruebas automatizadas. Balance sintáctico estricto en los 11 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `ChatMessage.sender_id` y `ConversationParticipant.user_id` vinculan a `auth_users.id` (`personas.id`). Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps `DateTime(timezone=True)`. Backend usa `_utcnow()` en UTC estricto. Cero llamadas a `datetime.utcnow()`. Soft-delete activo en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Conversaciones y chats segregados por sede_id del token JWT. Suites adversariales `test_chat_sede_isolation.py` (24) y `test_messaging_sede_isolation.py` (7) verificadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 11 archivos auditados. 0 modales centrados (`AlertDialog` = 0). Creación estructurada mediante `NewConversationDrawer`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (65%). Hallazgo H-MSG-01.** 85 clases Tailwind hardcodeadas y 118 selectores `dark:` en los archivos del módulo. | 15% | **65/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 11 archivos auditados. Cero llamadas a `fetch()` crudo. 100% de consultas gestionadas a través de `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 217 tests automatizados en backend (`test_chat_100pct_coverage.py`, `test_chat_sede_isolation.py`, `test_messaging_audit_phase1.py`, etc.). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** `docs/ESTADO_MESSAGING_COMMUNITY.md`, `docs/MESSAGING_COMMUNITY_API_CONTRACTS.md` y `docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md` sincronizados. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (65 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.75 + 10.0 + 10.0 + 5.0 = \mathbf{89.75 / 100} \approx \mathbf{89.8 / 100}$$

**Calificación Inicial:** **Grado A (89.8 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Mensajería, Chat e Inbox cuenta con una arquitectura de backend robusta: vinculación a `personas.id` (Axioma 1), UTC estricto con soft-deletes (Axioma 2), aislamiento multi-tenant verificado con 31 pruebas adversariales (Axioma 3), y 217 tests en total. En la interfaz visual se respetan los drawers laterales (0 `AlertDialog`, `NewConversationDrawer`). No obstante, se detecta el hallazgo **H-MSG-01** (85 clases Tailwind hardcodeadas y 118 selectores `dark:` en 9 archivos de frontend). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 11 Archivos de Frontend de Mensajería e Inbox

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/messages/page.tsx` | 268 | 4 | 8 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 2 | `frontend/src/app/plataforma/messages/_components/ConversationSidebar.tsx` | 163 | 10 | 15 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 3 | `frontend/src/app/plataforma/messages/_components/MessageBubble.tsx` | 168 | 8 | 6 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 4 | `frontend/src/app/plataforma/messages/_components/MessageInput.tsx` | 378 | 10 | 12 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 5 | `frontend/src/app/plataforma/messages/_components/MessageList.tsx` | 119 | 1 | 3 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 6 | `frontend/src/app/plataforma/messages/_components/NewConversationDrawer.tsx` | 82 | 4 | 5 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-MSG-01) |
| 7 | `frontend/src/app/plataforma/inbox/page.tsx` | 232 | 21 | 29 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-MSG-01) |
| 8 | `frontend/src/app/plataforma/inbox/layout.tsx` | 42 | 0 | 0 | 0 | 0 | `c:0 p:0 b:0` | 🟢 100% Canónico |
| 9 | `frontend/src/app/plataforma/inbox/chat/page.tsx` | 306 | 13 | 19 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-MSG-01) |
| 10 | `frontend/src/app/plataforma/inbox/comments/page.tsx` | 396 | 14 | 21 | 0 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-MSG-01) |
| 11 | `frontend/src/app/plataforma/inbox/messages/page.tsx` | 15 | 0 | 0 | 0 | 0 | `c:0 p:0 b:0` | 🟢 100% Canónico |
| **TOTAL** | **11 Archivos Auditados** | **2,169** | **85** | **118** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-MSG-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Mensajería Directa y NewConversationDrawer (`TKT-MSG-REMEDIATION-01`)
- **Archivos a intervenir (6 archivos):**
  1. `frontend/src/app/plataforma/messages/page.tsx` (4 clases TW + 8 `dark:`)
  2. `frontend/src/app/plataforma/messages/_components/ConversationSidebar.tsx` (10 clases TW + 15 `dark:`)
  3. `frontend/src/app/plataforma/messages/_components/MessageBubble.tsx` (8 clases TW + 6 `dark:`)
  4. `frontend/src/app/plataforma/messages/_components/MessageInput.tsx` (10 clases TW + 12 `dark:`)
  5. `frontend/src/app/plataforma/messages/_components/MessageList.tsx` (1 clase TW + 3 `dark:`)
  6. `frontend/src/app/plataforma/messages/_components/NewConversationDrawer.tsx` (4 clases TW + 5 `dark:`)
- **Acciones específicas:**
  - Sustituir clases hardcodeadas (`bg-blue-500`, `text-gray-400`, `bg-white`, `text-white`, etc.) por tokens semánticos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes.
  - Preservar NewConversationDrawer lateral (0 modales), 100% `apiFetch` y balance sintáctico estricto.
- **Total incidencias a erradicar:** 37 clases TW / 49 selectores `dark:`.
- **Commit atómico:** `feat(messaging): Remediación de Tokens Semánticos en Mensajería Directa y NewConversationDrawer (H-MSG-01 Fase 1)`.

### Fase 2: Bandeja Unificada Inbox, Chat y Comentarios (`TKT-MSG-REMEDIATION-02`)
- **Archivos a intervenir (3 archivos):**
  7. `frontend/src/app/plataforma/inbox/page.tsx` (21 clases TW + 29 `dark:`)
  8. `frontend/src/app/plataforma/inbox/chat/page.tsx` (13 clases TW + 19 `dark:`)
  9. `frontend/src/app/plataforma/inbox/comments/page.tsx` (14 clases TW + 21 `dark:`)
- **Acciones específicas:**
  - Sustituir colores Tailwind por tokens semánticos en vistas de bandeja, chats de inbox y paneles de comentarios.
  - Erradicar selectores `dark:` redundantes.
  - Preservar balance sintáctico estricto y 100% `apiFetch`.
- **Total incidencias a erradicar:** 48 clases TW / 69 selectores `dark:`.
- **Commit atómico:** `feat(messaging): Remediación de Tokens Semánticos en Bandeja Unificada Inbox, Chat y Comentarios (H-MSG-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-MSG-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 11 archivos.
3. Se procederá con `TKT-MSG-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/messages`
   - `/plataforma/inbox`
   - `/plataforma/inbox/chat`
   - `/plataforma/inbox/comments`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — Grado A)** para el **Módulo Mensajería Eclesial, Chat e Inbox (`messaging`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-MSG-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
