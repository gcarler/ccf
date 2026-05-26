# PLAN DE TRABAJO — SISTEMA MULTIAGENTE CCF "SUPER PRO"

**Fecha:** 2026-05-26
**Objetivo:** Llevar el sistema multiagente de "tiene la estructura" a "super pro" — un grafo de agentes interconectados con herramientas reales, memoria y orquestación.

---

## DIAGNÓSTICO ACTUAL (resumen)

| Capa | Estado | Problema |
|---|---|---|
| Modelos Agent | 8/10 | Faltan AgentTask y AgentInsight como modelos |
| Migraciones | 0/1 | Tablas de agentes sin migración Alembic |
| Knowledge Base | MOCK | 4 docs hardcodeados, sin búsqueda real |
| Event Warehouse | VACÍO | persist_event() nunca se llama |
| Multiagente | 1/∞ | Solo "Optimus", no hay registry ni routing |
| Tool Calling | 0 | Ningún agente puede invocar herramientas |
| Memoria | 0 | Cada ask es stateless |
| Event Bus | NO-OP | Se publica pero nadie consume |
| WebSockets | INERTE | Manager definido, nunca conectado |
| Messaging | MOCK | Sin WhatsApp/SMS/email real |

---

## FASE 1: FUNDAMENTOS — Arreglar lo que está roto (4 horas)

### 1.1 Crear modelos AgentTask y AgentInsight
- `backend/models_agents.py` — agregar `AgentTask` y `AgentInsight` con relaciones
- Campos: title, description, status, priority, assigned_agent_id, payload, metadata
- Indexar por agent_id, status, created_at

### 1.2 Crear migración Alembic para TODAS las tablas de agentes
- `0035_agent_tables_complete` — agents, agent_auth, agent_contact, agent_roles, agent_activities, agent_families, agent_journey, agent_permissions, agent_tasks, agent_insights
- Seed data: crear al menos 1 agente "Optimus" con rol `ai_agent`
- Verificar que todas las columnas JSON usen tipo correcto

### 1.3 Verificar dual-write hooks
- `sync_member_to_agent()` y `sync_user_to_agent()` — confirmar que funcionan
- Crear endpoint de diagnóstico: `GET /agents/sync/status`

**Entregables:**
- ✅ AgentTask y AgentInsight definidos en models_agents.py
- ✅ Migración 0035 con las 12 tablas
- ✅ Seed: agente "Optimus" creado
- ✅ Tests: crear tarea, crear insight, buscar agente

---

## FASE 2: KNOWLEDGE BASE REAL — Que Optimus sepa cosas (5 horas)

### 2.1 Crear tabla `agent_knowledge_base`
- Modelo: id, title, content, category, embedding (pgvector o JSON), source_module, created_at, updated_at, is_active
- Embeddings: si PostgreSQL tiene pgvector, usarlo. Si no, JSON + búsqueda full-text

### 2.2 Indexador automático de conocimiento
- Servicio `KnowledgeIndexer` que escanea:
  - Cursos activos → indexa títulos y descripciones
  - Estrategias de evangelismo → indexa nombres y objetivos
  - Proyectos activos → indexa milestones y tareas
  - CRM members → indexa estadísticas (no datos personales)
  - System variables → indexa configuraciones
- Se ejecuta al startup y se puede trigger manualmente

### 2.3 Búsqueda real en KB
- Reemplazar `search_knowledge_base()` mock con búsqueda real
- Full-text search en PostgreSQL (`tsvector`)
- Ranking por relevancia (tf-idf o similar)
- Retorna top-K documentos con snippets

### 2.4 Población inicial de KB
- Script que indexa todo el contenido existente
- Endpoint: `POST /agents/kb/rebuild` (admin only)

**Entregables:**
- ✅ Tabla agent_knowledge_base con búsqueda full-text
- ✅ KnowledgeIndexer funcional
- ✅ search_knowledge_base() real (no mock)
- ✅ Endpoint /agents/kb/rebuild
- ✅ Tests: búsqueda retorna resultados relevantes

---

## FASE 3: TOOL CALLING — Que los agentes puedan actuar (6 horas)

### 3.1 Definir protocolo de herramientas
- `AgentTool` — clase base con: name, description, parameters (JSON Schema), execute()
- `ToolRegistry` — registro central de herramientas disponibles
- Cada módulo registra sus herramientas al startup

### 3.2 Herramientas base por módulo
| Módulo | Herramientas |
|---|---|
| CRM | `crm_search_member`, `crm_update_pipeline`, `crm_create_task` |
| Academy | `academy_search_course`, `academy_get_enrollment`, `academy_create_certificate` |
| Projects | `projects_search_task`, `projects_update_status`, `projects_create_task` |
| Evangelism | `evangelism_get_strategy`, `evangelism_get_groups`, `evangelism_log_session` |
| Members | `members_search`, `members_get_profile`, `members_update_church_role` |
| Analytics | `analytics_get_radar`, `analytics_get_events`, `analytics_proactive_analysis` |

### 3.3 Integrar Tool Calling con OpenAI/OpenRouter
- Actualizar `AgentOrchestrator.run_diagnosis()` para usar function calling
- El LLM decide qué herramienta usar y con qué parámetros
- Ejecutar herramienta → pasar resultado al LLM → generar respuesta
- Soporte multi-step: el LLM puede llamar múltiples herramientas en secuencia

### 3.4 Formato de respuesta estructurada
- Las respuestas del LLM ahora incluyen:
  - `tools_used`: lista de herramientas invocadas
  - `tool_results`: resultados de cada llamada
  - `answer`: respuesta final en lenguaje natural
  - `confidence`: score de confianza (0-1)

**Entregables:**
- ✅ ToolRegistry con 15+ herramientas
- ✅ AgentOrchestrator con function calling
- ✅ Cada módulo expone sus herramientas
- ✅ Respuestas estructuradas con tools_used
- ✅ Tests: Optimus resuelve query usando herramientas reales

---

## FASE 4: MULTI-AGENTE REAL — Registry y routing (6 horas)

### 4.1 Agente Registry
- `AgentRegistry` — descubre y registra agentes activos
- Cada agente tiene: id, name, capabilities (lista de tools), model, status, last_seen
- Endpoint: `GET /agents/registry` — ver todos los agentes
- Endpoint: `POST /agents/registry/register` — registrar un agente

### 4.2 Agentes especializados
| Agente | Rol | Herramientas |
|---|---|---|
| **Optimus** | Diagnóstico general | Todas (coordinador) |
| **PastorIA** | Pastoral y CRM | crm_search_member, crm_update_pipeline, crm_create_task, members_get_profile |
| **Académico** | Academia y cursos | academy_search_course, academy_get_enrollment, analytics_get_radar |
| **ProjectBot** | Gestión de proyectos | projects_search_task, projects_update_status, projects_create_task |
| **Evangelista** | Evangelismo y faro en casa | evangelism_get_strategy, evangelism_get_groups, evangelism_log_session |
| **Analista** | Analytics y reportes | analytics_get_radar, analytics_get_events, analytics_proactive_analysis |

### 4.3 Router de agentes
- `AgentRouter` — decide qué agente manejar una query
- Usa keywords + embeddings para routing
- Si ningún agente especializado es relevante → fallback a Optimus
- Soporte de escalado: un agente puede delegar a otro

### 4.4 Endpoint multi-agente
- `POST /agents/ask` ahora:
  1. El Router decide el agente
  2. El agente ejecuta con sus herramientas
  3. Si necesita otro agente → delega
  4. Retorna respuesta + metadata de routing

**Entregables:**
- ✅ AgentRegistry funcional
- ✅ 6 agentes especializados
- ✅ AgentRouter con routing inteligente
- ✅ Endpoint /agents/ask con routing
- ✅ Tests: query ruta al agente correcto

---

## FASE 5: MEMORIA DE CONVERSACIÓN — Contexto persistente (4 horas)

### 5.1 Tabla `agent_conversations`
- Modelo: id, agent_id, user_id, title, created_at, updated_at, is_active
- Modelo: `agent_messages` — id, conversation_id, role (user/assistant/system), content, tools_used, timestamp

### 5.2 Contexto en el Orquestador
- `AgentOrchestrator.run_diagnosis()` ahora acepta `conversation_id`
- Si existe → carga historial de mensajes (últimos N turnos)
- Pasa el historial como contexto al LLM
- Guarda la respuesta en agent_messages

### 5.3 Gestión de contexto
- Límite de tokens: truncar historial si excede el context window
- Resumen automático: si el historial es largo, generar resumen con LLM
- Conversaciones expiran después de X días de inactividad

### 5.4 Endpoints de conversación
- `GET /agents/conversations` — listar conversaciones del usuario
- `POST /agents/conversations` — crear nueva conversación
- `GET /agents/conversations/{id}/messages` — ver historial
- `DELETE /agents/conversations/{id}` — eliminar conversación

**Entregables:**
- ✅ Tablas agent_conversations + agent_messages
- ✅ Contexto persistente en orquestador
- ✅ Gestión de contexto (truncación, resumen)
- ✅ 4 endpoints de conversación
- ✅ Tests: conversación multi-turno con contexto

---

## FASE 6: EVENT BUS FUNCIONAL — Comunicación entre módulos (4 horas)

### 5.1 Crear consumidores de eventos
- `EventConsumer` base class — subscribe(event_type), handle(event)
- Registrar consumidores al startup:
  - `consolidation_stagnant` → IntelligenceMESH analiza
  - `task_overdue` → crea insight + notificación
  - `enrollment_created` → indexa en KB
  - `member_status_changed` → actualiza grafo
  - `spiritual_stage_transition` → registra en journey

### 5.2 Conectar EventBus real
- Auto-detectar Redis si está disponible
- Si no, usar EventBus en memoria (para dev)
- Los módulos publican eventos al hacer acciones importantes

### 5.3 Endpoint de eventos
- `GET /events/stream` — Server-Sent Events para tiempo real en frontend
- `POST /events/publish` — publicar evento manualmente (admin)

**Entregables:**
- ✅ EventConsumer con 5+ handlers
- ✅ EventBus conectado a Redis (o fallback memoria)
- ✅ Módulos publican eventos
- ✅ Endpoint SSE para frontend
- ✅ Tests: evento publicado → consumido → acción ejecutada

---

## FASE 7: WEBHOOKS Y MESSAGING REAL (3 horas)

### 7.1 Messaging Gateway real
- Implementar `send_email()` con SMTP real (ya existe el config)
- Implementar `send_whatsapp()` con API real (Twilio o similar)
- Implementar `send_sms()` con API real
- Templates de mensajes: welcome, reminder, alert, celebration

### 7.2 Integración con Automation Engine
- Cuando automation detecta algo → envía mensaje
- Ejemplo: tarea overdue → email al asignado
- Ejemplo: nuevo miembro → WhatsApp de bienvenida

**Entregables:**
- ✅ Email funcional con SMTP
- ✅ WhatsApp/SMS con API externa
- ✅ Templates de mensajes
- ✅ Integración con automation engine

---

## FASE 8: FRONTEND SUPER PRO (4 horas)

### 8.1 Página de Agentes (`/plataforma/agents`)
- Lista de agentes especializados con status
- Click en agente → ver sus capacidades, herramientas, historial
- Crear agente personalizado

### 8.2 Chat con Optimus (mejorado)
- UI de chat tipo conversacional (no solo input + respuesta)
- Mostrar herramientas usadas en cada respuesta
- Historial de conversaciones
- Indicador de agente activo

### 8.3 Panel de conocimiento
- Ver qué hay en la Knowledge Base
- Rebuild index manualmente
- Estadísticas de uso de agentes

**Entregables:**
- ✅ Página /plataforma/agents
- ✅ Chat conversacional mejorado
- ✅ Panel de Knowledge Base
- ✅ Indicador de agente activo

---

## FASE 9: CALIDAD FINAL (2 horas)

### 9.1 Tests integrales
- Tests de cada agente especializado
- Tests de routing (query → agente correcto)
- Tests de tool calling (LLM → herramienta → resultado)
- Tests de memoria (multi-turno con contexto)
- Tests de event bus (publish → consume → acción)

### 9.2 Smoke tests end-to-end
- Preguntar algo → Optimus responde usando herramientas
- Crear miembro → evento → insight generado
- Conversation multi-turno con contexto

### 9.3 Documentación
- Actualizar MESH_MANIFESTO.md con lo implementado
- Documentar herramientas disponibles
- Documentar agentes especializados

**Entregables:**
- ✅ 30+ tests pasando
- ✅ Smoke tests end-to-end
- ✅ Documentación actualizada

---

## RESUMEN DEL PLAN

| Fase | Qué hace | Tiempo | Bloquea |
|---|---|---|---|
| **1. Fundamentos** | Arreglar modelos y migraciones | 4h | Todo lo demás |
| **2. Knowledge Base** | Búsqueda real, no mock | 5h | Fases 3, 4 |
| **3. Tool Calling** | Agentes pueden actuar | 6h | Fases 4, 8 |
| **4. Multi-Agente** | Registry + routing | 6h | Fase 8 |
| **5. Memoria** | Conversaciones con contexto | 4h | Fase 8 |
| **6. Event Bus** | Comunicación entre módulos | 4h | Fase 7 |
| **7. Messaging** | Email/WhatsApp real | 3h | — |
| **8. Frontend** | UI super pro | 4h | — |
| **9. Calidad** | Tests + docs | 2h | — |

**Total: ~38 horas de trabajo**

---

## CRITERIOS DE ÉXITO — "SUPER PRO"

El sistema es "super pro" cuando:

1. ✅ Un usuario hace una pregunta → el router elige el agente correcto → el agente usa herramientas reales → responde con contexto
2. ✅ Un nuevo miembro se registra → se crea agente → se indexa en KB → se envía mensaje de bienvenida → se registra en el grafo
3. ✅ Una tarea se vence → el automation engine detecta → crea insight → notifica al asignado → actualiza el dashboard
4. ✅ Una conversación tiene 20 turnos → el agente recuerda el contexto → resume si es necesario → nunca pierde el hilo
5. ✅ Hay 6 agentes especializados → cada uno sabe hacer algo diferente → pueden delegar entre sí
6. ✅ El frontend muestra todo esto de forma visual → grafo interactivo → chat conversacional → panel de agentes

---

## ORDEN DE EJUCUCIÓN RECOMENDADO

Las fases 1-2-3 son secuenciales (cada una bloquea la siguiente).
Las fases 4-5 pueden ir en paralelo después de la 3.
Las fases 6-7 pueden ir en paralelo después de la 3.
La fase 8 requiere 3, 4 y 5 completadas.
La fase 9 es al final de todo.

```
F1 → F2 → F3 → F4 → F8
              → F5 →/
              → F6 → F7
                        → F9
```
