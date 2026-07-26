# Auditoría Forense — Módulo de Mensajería CCF

**Fecha:** 2026-07-25
**Alcance:** WebSocket en tiempo real, Notificaciones por usuario, Chat interno (CommunicationLog), Multi-Tenant (Axioma 3)
**Clasificación:** CONFIDENCIAL — Solo para equipo técnico CCF

---

## 1. Resumen Ejecutivo

El módulo de mensajería de CCF tiene **5 hallazgos críticos**, **6 altos** y **8 medios** que afectan completitud, consistencia y seguridad. Además, la arquitectura actual está por debajo de lo que ofrecen plataformas líderes (Intercom, Zendesk, Slack, Teams) y significativamente por encima de plataformas iglesia (Planning Center, Breeze, Faithlife) — pero sin innovación diferenciadora.

Este documento documenta los hallazgos y presenta un **plan de transformación en 5 fases** para elevar el módulo a nivel enterprise con funcionalidades que no existen en ninguna plataforma del mercado.

---

## 2. Hallazgos de la Auditoría Forense

### 2.1 CRÍTICOS (C-01 a C-05)

#### C-01: `CommunicationLog` no tiene columna `deleted_at` pero el CRUD la usa
- **Ubicación:** `backend/models_crm.py:677-698` vs `backend/crud/crm_/communication.py:184`
- **Problema:** `delete_communication_log()` ejecuta `row.deleted_at = _utcnow()` pero el modelo NO tiene columna `deleted_at`. Esto lanza `AttributeError` en runtime.
- **Impacto:** Soft-delete roto. Viola REGLAS.md §6 ("Usar deleted_at para entidades protegidas").
- **Corrección:** Agregar `deleted_at = Column(DateTime(timezone=True), nullable=True)` al modelo + migración.

#### C-02: `GET /messaging/history` no filtra registros soft-deleted
- **Ubicación:** `backend/crud/crm_/communication.py:140-148`
- **Problema:** `get_communication_logs()` no aplica filtro `deleted_at IS NULL`. Cuando se arregle C-01, los registros "eliminados" seguirían apareciendo.
- **Corrección:** Agregar `.filter(models.CommunicationLog.deleted_at.is_(None))` a la query.

#### C-03: WebSocket no valida permisos de módulo (`messaging:read`)
- **Ubicación:** `backend/api/messaging.py:115-141`
- **Problema:** El endpoint WebSocket decodifica JWT y valida `sub` no vacío, pero NO invoca `require_module_access("messaging", "read")`. Un usuario sin permisos podría conectarse.
- **Corrección:** Agregar validación de permisos de módulo tras decodificar el JWT.

#### C-04: `presence_join` publicado a Redis pero ignorado en `_dispatch()`
- **Ubicación:** `backend/mesh_websockets.py:88-93` (publica) vs `70-78` (dispatch)
- **Problema:** `connect()` publica `{"type": "presence_join", ...}` a Redis, pero `_dispatch()` solo maneja `broadcast`, `notify`, `presence_leave`. En multi-instancia, la presencia es local-only.
- **Corrección:** Agregar handler para `presence_join` en `_dispatch()` que actualice `rooms` localmente.

#### C-05: `POST /crm/messaging/send` con `persona_id` directo NO valida sede del destinatario
- **Ubicación:** `backend/api/crm/pastoral.py:656-657`
- **Problema:** Cuando se envía `persona_id` directo (no vía `target_segments`), el código hace `target_personas = [{"id": persona_id}]` SIN llamar a `_get_scoped_persona` ni `_scope_by_user_sede_via_persona`. Un staff de sede_A podría enviar a persona de sede_B.
- **Corrección:** Agregar `_get_scoped_persona(db, current_user, persona_id)` antes de construir `target_personas`.

### 2.2 ALTOS (A-01 a A-06)

| ID | Hallazgo | Archivo | Corrección |
|---|---|---|---|
| A-01 | `presence/{room}` retorna `client_id` raw sin resolución de identidad | `messaging.py:144-148` | Resolver `client_id` → `persona_id` → nombre |
| A-02 | `useMeshSocket` (frontend) conecta SIN autenticación | `hooks/useMeshSocket.ts` | Agregar token JWT al connect |
| A-03 | `schemas.CommunicationLog` omite `campaign_name`, `recipient_phone`, `is_read`, `external_id` | `schemas/notifications.py:37-45` | Extender schema de respuesta |
| A-04 | `channel` campo libre sin validación de enum | `schemas/notifications.py:24` | Usar `Literal["internal","WhatsApp","SMS","Email"]` |
| A-05 | `Notification` model sin índice explícito en `user_id` | `models_auth.py:193-202` | Agregar `Index("ix_auth_notifications_user_id", "user_id")` |
| A-06 | `mark_all_read` no retorna count de items marcados | `messaging.py:203-211` | Retornar `{"status":"success","marked_count": N}` |

### 2.3 MEDIOS (M-01 a M-08)

| ID | Hallazgo | Corrección |
|---|---|---|
| M-01 | `GET /messaging/notifications` sin paginación offset/cursor | Agregar `offset` param |
| M-02 | `GET /messaging/history` sin paginación offset/cursor | Agregar `offset` param |
| M-03 | Dos sistemas de notificación paralelos sin unificación | API unificada que consolide ambos |
| M-04 | WebSocket room names arbitrarios sin allowlist | Validar formato `project_{uuid}`, `dm_{uuid}`, `global` |
| M-05 | `POST /messaging/notifications` broadcast sin rate limit | Agregar rate limit por usuario |
| M-06 | `Notification` sin relación `sede_id` a nivel tabla | Agregar columna `sede_id` nullable |
| M-07 | `DELETE /chat/messages/{message_id}` sin sede validation explícita | Agregar `_get_scoped_persona` check |
| M-08 | Frontend `BackendNotification.id` typed as `number` (debería ser UUID string) | Corregir tipo a `string` |

---

## 3. Benchmark de Mercado

### 3.1 Lo que ofrecen los líderes (Intercom, Zendesk, Slack, Teams)

| Categoría | Intercom | Zendesk | Slack | Teams |
|---|---|---|---|---|
| Typing indicators | ✅ | ✅ | ✅ | ✅ |
| Read receipts | ✅ (agent) | ✅ | ✅ | ✅ |
| Presence | ✅ | ✅ | ✅ (custom status) | ✅ (DND, OOO) |
| Reactions | ✅ | ✅ | ✅ (custom) | ✅ (multi) |
| Threads | ✅ | ✅ | ✅ (deep) | ✅ |
| AI Chatbot | Fin (GPT-4) | AI Agents | Claude 4.6 | Copilot (GPT-5.4) |
| AI Copilot | ✅ | ✅ | ✅ | ✅ |
| Sentiment Analysis | ✅ | ✅ | ❌ | ❌ |
| Smart Routing | ✅ | ✅ | ✅ | ✅ |
| SLA Management | ✅ | ✅ | ❌ | ❌ |
| Omnichannel | ✅ | ✅ (best) | Limited | Limited |
| Analytics | ✅ (advanced) | ✅ (Explore) | ✅ (Business+) | ✅ (Viva) |
| Webhooks | ✅ | ✅ | ✅ | ✅ |
| API | REST | REST | REST+MCP | Graph |
| Marketplace | 450+ apps | 1,500+ apps | 2,600+ apps | 1,000+ apps |

### 3.2 Lo que ofrecen plataformas iglesia

| Categoría | Planning Center | Breeze | Faithlife |
|---|---|---|---|
| Typing indicators | ❌ | ❌ | ❌ |
| Read receipts | ❌ | ❌ | ❌ |
| Presence | ❌ | ❌ | ❌ |
| AI | ❌ | ❌ | ❌ |
| Real-time chat | ✅ (nuevo 2026) | ❌ | ✅ (básico) |
| Multi-channel | Email+Push | Email+SMS básico | Push+Email |
| Analytics | Asistencia+Diezmo | Reportes básicos | Engagement |
| WhatsApp | ❌ | ❌ | ❌ |
| Groups | ✅ | ✅ | ✅ |

### 3.3 El gap de oportunidad para CCF

**Ninguna plataforma iglesia ofrece:**
- Typing indicators / read receipts
- AI-powered pastoral care
- Real-time engagement analytics
- WhatsApp nativo
- Intelligent volunteer routing
- Spiritual growth tracking con automations

**CCF puede ser la PRIMERA plataforma iglesia en ofrecer:**
1. AI Pastoral Copilot (responder consultas, sugerir follow-ups)
2. Congregation Intelligence (engagement scoring, attendance prediction)
3. Unified Omnichannel Inbox (WhatsApp + SMS + Email + Chat interno)
4. Automated Spiritual Journeys (onboarding → discipulado → liderazgo)
5. Real-time Service Interaction (polls, Q&A, prayer wall durante el servicio)

---

## 4. Plan de Transformación — 5 Fases

### FASE 1: Sanación de Críticos (Semanas 1-2)
> Cerrar los 5 hallazgos críticos + 6 altos. Cero regressión.

| Tarea | Archivos | Prioridad |
|---|---|---|
| C-01: Agregar `deleted_at` a `CommunicationLog` | `models_crm.py`, migración alembic | CRÍTICO |
| C-02: Filtrar `deleted_at IS NULL` en `get_communication_logs` | `crud/crm_/communication.py` | CRÍTICO |
| C-03: Agregar validación de permisos en WebSocket | `api/messaging.py` | CRÍTICO |
| C-04: Handler `presence_join` en `_dispatch()` | `mesh_websockets.py` | CRÍTICO |
| C-05: Scope check en `persona_id` directo | `api/crm/pastoral.py` | CRÍTICO |
| A-01: Resolver `client_id` → `persona_id` en presence | `api/messaging.py`, `mesh_websockets.py` | ALTO |
| A-02: Autenticar `useMeshSocket` | `hooks/useMeshSocket.ts`, `lib/websocket.ts` | ALTO |
| A-03: Extender schema `CommunicationLog` | `schemas/notifications.py` | ALTO |
| A-04: Enum para `channel` | `schemas/notifications.py`, `models_crm.py` | ALTO |
| A-05: Índice `user_id` en notifications | `models_auth.py`, migración | ALTO |
| A-06: Retornar `marked_count` en `mark_all_read` | `api/messaging.py`, `crud/crm_/notifications.py` | ALTO |
| Tests: WebSocket auth negativa | `tests/test_messaging_websocket_auth.py` | ALTO |
| Tests: Cross-sede para C-05 | `tests/test_messaging_sede_isolation.py` | ALTO |

### FASE 2: Infraestructura Pro (Semanas 3-4)
> Construir la base para funcionalidades avanzadas.

#### 2.1 Unified Message Model
```python
class UnifiedMessage(Base):
    """Mensaje unificado que reemplaza CommunicationLog + ChatMessage."""
    __tablename__ = "unified_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    room_id = Column(String(100), index=True)  # "dm_{uuid}", "group_{uuid}", "channel_{slug}"
    channel = Column(SAEnum("internal","whatsapp","sms","email","push"), index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(20), default="text")  # text, image, file, audio, video, location, contact
    
    # Metadata
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("unified_messages.id"), nullable=True)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("unified_messages.id"), nullable=True, index=True)
    campaign_name = Column(String(120), nullable=True)
    external_id = Column(String(120), nullable=True, index=True)
    
    # State
    status = Column(SAEnum("draft","queued","sent","delivered","read","failed"), default="draft", index=True)
    outcome = Column(String(50), default="sent")
    is_pinned = Column(Boolean, default=False)
    is_starred = Column(Boolean, default=False)
    
    # Multi-tenant
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    read_at = Column(DateTime(timezone=True), nullable=True)
```

#### 2.2 Message Status Tracking
```python
class MessageStatus(Base):
    """Tracking de entrega/lectura por destinatario."""
    __tablename__ = "message_statuses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("unified_messages.id"), index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), index=True)
    status = Column(SAEnum("sent","delivered","read","failed"), index=True)
    timestamp = Column(DateTime(timezone=True), default=_utcnow)
    
    __table_args__ = (UniqueConstraint("message_id", "recipient_id"),)
```

#### 2.3 Typing Indicators (WebSocket Event)
```python
# Evento WebSocket: typing_indicator
{
    "event": "typing_start",
    "room_id": "dm_{uuid}",
    "user_id": "persona_{uuid}",
    "timestamp": "2026-07-25T10:30:00Z"
}
```

#### 2.4 Read Receipts (WebSocket Event + DB)
```python
# Cuando un usuario lee un mensaje:
# 1. Frontend envía POST /chat/conversations/{id}/read
# 2. Backend actualiza MessageStatus → "read"
# 3. Backend emite evento WebSocket a la sala:
{
    "event": "message_read",
    "message_id": "uuid",
    "reader_id": "persona_{uuid}",
    "read_at": "2026-07-25T10:30:00Z"
}
```

#### 2.5 Presence System Rediseñado
```python
class UserPresence(Base):
    """Estado de presencia de cada usuario."""
    __tablename__ = "user_presences"
    
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), primary_key=True)
    status = Column(SAEnum("online","away","busy","dnd","offline"), default="offline")
    status_text = Column(String(100), nullable=True)  # "En reunión de equipo", "Orando"
    last_seen_at = Column(DateTime(timezone=True), default=_utcnow)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
```

#### 2.6 Endpoints Nuevos Fase 2

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/messaging/typing/{room_id}` | Obtener quién está escribiendo |
| `POST` | `/messaging/typing/{room_id}` | Notificar que estoy escribiendo |
| `GET` | `/messaging/presence` | Presencia de todos los usuarios de la sede |
| `PATCH` | `/messaging/presence` | Actualizar mi presencia |
| `GET` | `/messaging/search` | Búsqueda full-text en mensajes |
| `GET` | `/messaging/threads/{thread_id}` | Obtener hilo de conversación |
| `POST` | `/messaging/pin/{message_id}` | Fijar mensaje |
| `POST` | `/messaging/star/{message_id}` | Marcar mensaje como favorito |
| `GET` | `/messaging/pinned/{room_id}` | Mensajes fijados de una sala |
| `GET` | `/messaging/starred` | Mis mensajes favoritos |

### FASE 3: AI Pastoral Copilot (Semanas 5-8)
> La funcionalidad diferenciadora que NINGUNA plataforma iglesia tiene.

#### 3.1 AI Response Suggestions
```python
class AiSuggestion(Base):
    """Sugerencias de respuesta AI para staff pastoral."""
    __tablename__ = "ai_suggestions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    message_id = Column(UUID(as_uuid=True), ForeignKey("unified_messages.id"), index=True)
    suggested_response = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    context_type = Column(String(50))  # "prayer_request", "counseling", "general", "follow_up"
    accepted = Column(Boolean, nullable=True)  # None=pending, True=accepted, False=rejected
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 3.2 Sentiment Analysis Pipeline
```python
class MessageSentiment(Base):
    """Análisis de sentimiento de mensajes."""
    __tablename__ = "message_sentiments"
    
    message_id = Column(UUID(as_uuid=True), ForeignKey("unified_messages.id"), primary_key=True)
    sentiment = Column(SAEnum("positive","neutral","negative","urgent","crisis"), index=True)
    score = Column(Float, nullable=False)  # -1.0 to 1.0
    keywords = Column(JSON, nullable=True)  # ["oración", "enfermedad", "familia"]
    flagged = Column(Boolean, default=False)  # True si detecta crisis/urgencia
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 3.3 Smart Follow-Up Automation
```python
class FollowUpRule(Base):
    """Reglas de seguimiento automático."""
    __tablename__ = "follow_up_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(50), nullable=False)  # "first_visit", "no_attendance_3w", "prayer_request", "new_member"
    trigger_conditions = Column(JSON, nullable=True)  # {"days_inactive": 21, "min_attendance": 2}
    action_type = Column(String(50), nullable=False)  # "send_message", "create_task", "notify_leader", "schedule_call"
    action_config = Column(JSON, nullable=False)  # {"channel": "whatsapp", "template": "follow_up_v1"}
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 3.4 Congregational Intelligence Dashboard
```python
class CongregationMetric(Base):
    """Métricas agregadas de congregación por sede."""
    __tablename__ = "congregation_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    metric_type = Column(String(50), nullable=False, index=True)  
    # "engagement_score", "attendance_trend", "giving_pattern", 
    # "volunteer_retention", "new_member_conversion", "spiritual_growth_index"
    metric_value = Column(Float, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    breakdown = Column(JSON, nullable=True)  # {"by_age": {...}, "by_ministry": {...}}
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 3.5 Endpoints AI

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/ai/suggest-response` | Obtener sugerencias de respuesta para un mensaje |
| `POST` | `/ai/analyze-sentiment` | Analizar sentimiento de un mensaje |
| `GET` | `/ai/follow-ups` | Listar follow-ups pendientes para mi sede |
| `POST` | `/ai/follow-ups` | Crear regla de seguimiento |
| `GET` | `/ai/congregation-insights` | Dashboard de métricas de congregación |
| `GET` | `/ai/engagement-score/{persona_id}` | Score de engagement de una persona |
| `POST` | `/ai/pastoral-summary` | Generar resumen pastoral de conversaciones |

### FASE 4: Omnichannel & Automation (Semanas 9-12)
> Unificar todos los canales + automatizar flujos pastorales.

#### 4.1 Canal WhatsApp Real (Meta Business API)
```python
class WhatsAppTemplate(Base):
    """Templates de WhatsApp aprobados por Meta."""
    __tablename__ = "whatsapp_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    template_name = Column(String(100), nullable=False)
    language = Column(String(10), default="es")
    category = Column(String(20))  # "marketing", "utility", "authentication"
    header_type = Column(String(20))  # "text", "image", "video", "document"
    body = Column(Text, nullable=False)
    footer = Column(String(200), nullable=True)
    buttons = Column(JSON, nullable=True)  # [{"type": "quick_reply", "text": "Sí"}, ...]
    meta_template_id = Column(String(100), nullable=True)  # ID en Meta
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 4.2 Workflow Automation Engine
```python
class MessagingWorkflow(Base):
    """Workflows de mensajería automatizada."""
    __tablename__ = "messaging_workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # "event", "schedule", "condition", "manual"
    trigger_config = Column(JSON, nullable=False)
    # {"event": "new_member_registered", "filter": {"church_role": "Miembro"}}
    steps = Column(JSON, nullable=False)
    # [
    #   {"type": "wait", "duration": "3d"},
    #   {"type": "send_channel", "channel": "whatsapp", "template": "welcome_v1"},
    #   {"type": "condition", "field": "attended_since_register", "op": ">=", "value": 1},
    #   {"type": "send_channel", "channel": "email", "template": "week1_checkin"},
    #   {"type": "create_task", "assign_to": "pastor_asignado", "title": "Follow-up personalizado"}
    # ]
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    run_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 4.3 SLA Management
```python
class MessageSLA(Base):
    """SLAs de respuesta por tipo de mensaje."""
    __tablename__ = "message_slas"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    name = Column(String(100), nullable=False)
    message_type = Column(String(50), nullable=False)  # "prayer_request", "counseling", "general", "complaint"
    response_time_hours = Column(Integer, nullable=False)  # Horas para primera respuesta
    escalation_time_hours = Column(Integer, nullable=True)  # Horas para escalar
    escalation_target = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)  # A quién escalar
    is_active = Column(Boolean, default=True)
```

#### 4.4 Endpoints Automation

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/workflows` | Listar workflows |
| `POST` | `/workflows` | Crear workflow |
| `POST` | `/workflows/{id}/run` | Ejecutar workflow manualmente |
| `GET` | `/workflows/{id}/runs` | Historial de ejecuciones |
| `GET` | `/sla` | Listar SLAs configurados |
| `POST` | `/sla` | Crear SLA |
| `GET` | `/sla/breaches` | SLAs violados |
| `POST` | `/whatsapp/templates` | Registrar template |
| `GET` | `/whatsapp/templates` | Listar templates |

### FASE 5: Community & Real-Time Experience (Semanas 13-16)
> Funcionalidades que convierten CCF en la plataforma iglesia definitiva.

#### 5.1 Prayer Wall (Pared de Oración)
```python
class PrayerRequest(Base):
    """Solicitudes de oración de la congregación."""
    __tablename__ = "prayer_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    is_urgent = Column(Boolean, default=False)
    category = Column(String(50))  # "health", "family", "financial", "spiritual", "other"
    status = Column(SAEnum("active","praying","answered","archived"), default="active", index=True)
    prayer_count = Column(Integer, default=0)  # Cuántas personas están orando
    visibility = Column(String(20), default="sede")  # "sede", "all"
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

class PrayerComment(Base):
    """Comentarios/oraciones en solicitudes."""
    __tablename__ = "prayer_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    prayer_request_id = Column(UUID(as_uuid=True), ForeignKey("prayer_requests.id"), index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), index=True)
    content = Column(Text, nullable=False)
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

#### 5.2 Real-Time Service Interaction
```python
class ServiceSession(Base):
    """Sesión de servicio en vivo."""
    __tablename__ = "service_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), index=True)
    title = Column(String(200), nullable=False)
    status = Column(SAEnum("scheduled","live","ended"), default="scheduled", index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    room_id = Column(String(100), nullable=False)  # Para WebSocket

class ServicePoll(Base):
    """Encuestas durante el servicio."""
    __tablename__ = "service_polls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("service_sessions.id"), index=True)
    question = Column(String(500), nullable=False)
    options = Column(JSON, nullable=False)  # ["Opción A", "Opción B", "Opción C"]
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class ServicePollResponse(Base):
    """Respuestas a encuestas del servicio."""
    __tablename__ = "service_poll_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    poll_id = Column(UUID(as_uuid=True), ForeignKey("service_polls.id"), index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), index=True)
    option_index = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    
    __table_args__ = (UniqueConstraint("poll_id", "persona_id"),)
```

#### 5.3 Endpoints Community

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/prayers` | Listar solicitudes de oración |
| `POST` | `/prayers` | Crear solicitud de oración |
| `POST` | `/prayers/{id}/pray` | "Estoy orando" (+1) |
| `POST` | `/prayers/{id}/comment` | Comentar en solicitud |
| `GET` | `/prayers/my` | Mis solicitudes de oración |
| `POST` | `/services` | Crear sesión de servicio en vivo |
| `POST` | `/services/{id}/start` | Iniciar servicio |
| `POST` | `/services/{id}/end` | Finalizar servicio |
| `POST` | `/services/{id}/poll` | Crear encuesta |
| `POST` | `/services/{id}/poll/{poll_id}/vote` | Votar en encuesta |
| `GET` | `/services/{id}/poll/{poll_id}/results` | Resultados de encuesta |
| `WS` | `/services/ws/{session_id}` | WebSocket del servicio en vivo |

---

## 5. Diagrama de Arquitectura Final

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CCF MESSAGING PLATFORM                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   FRONTEND    │  │   MOBILE APP │  │  ADMIN PANEL  │              │
│  │  Next.js+WS  │  │  (Future)    │  │  Dashboard    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                  │                  │                      │
│  ┌──────┴──────────────────┴──────────────────┴───────┐              │
│  │              UNIFIED API GATEWAY                    │              │
│  │         /api/messaging/* + /api/chat/*              │              │
│  │    Auth: RBAC + Axioma 3 + Rate Limiting           │              │
│  └──────┬──────────────────┬──────────────────┬───────┘              │
│         │                  │                  │                      │
│  ┌──────┴──────┐  ┌───────┴──────┐  ┌───────┴──────┐              │
│  │  REAL-TIME   │  │   MESSAGING  │  │  AI LAYER    │              │
│  │  WebSocket   │  │   CORE       │  │  Ollama +    │              │
│  │  Redis PubSub│  │   Unified    │  │  Llama3      │              │
│  │  Presence    │  │   Messages   │  │  Sentiment   │              │
│  │  Typing      │  │   Threads    │  │  Follow-ups  │              │
│  │  Reactions   │  │   Reactions  │  │  Copilot     │              │
│  └──────┬──────┘  └───────┬──────┘  └───────┬──────┘              │
│         │                  │                  │                      │
│  ┌──────┴──────────────────┴──────────────────┴───────┐              │
│  │              UNIFIED MESSAGE STORE                  │              │
│  │         unified_messages + message_statuses         │              │
│  │         PostgreSQL + SeaweedFS (media)              │              │
│  └──────┬──────────────────┬──────────────────┬───────┘              │
│         │                  │                  │                      │
│  ┌──────┴──────┐  ┌───────┴──────┐  ┌───────┴──────┐              │
│  │  CHANNELS    │  │  AUTOMATION  │  │  ANALYTICS   │              │
│  │  WhatsApp    │  │  Workflows   │  │  Congregation │              │
│  │  SMS         │  │  Follow-ups  │  │  Intelligence │              │
│  │  Email       │  │  SLA Engine  │  │  Engagement   │              │
│  │  Push        │  │  Triggers    │  │  Reports      │              │
│  └─────────────┘  └──────────────┘  └──────────────┘              │
│                                                                     │
│  ┌─────────────────────────────────────────────────────┐             │
│  │              COMMUNITY FEATURES                      │             │
│  │  Prayer Wall | Service Live | Groups | Polls         │             │
│  └─────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Roadmap de Implementación

| Fase | Semanas | Entregable | Valor |
|---|---|---|---|
| **Fase 1** | 1-2 | Críticos cerrados, base sólida | Seguridad + estabilidad |
| **Fase 2** | 3-4 | Unified Message Model, Presence, Typing, Read Receipts | UX moderna |
| **Fase 3** | 5-8 | AI Pastoral Copilot, Sentiment, Follow-ups | Diferenciador único |
| **Fase 4** | 9-12 | WhatsApp real, Workflows, SLAs | Omnichannel + automatización |
| **Fase 5** | 13-16 | Prayer Wall, Service Live, Polls | Community engagement |

---

## 7. Estimación de Esfuerzo

| Fase | Backend | Frontend | Tests | Total |
|---|---|---|---|---|
| Fase 1 | 16h | 4h | 8h | **28h** |
| Fase 2 | 40h | 24h | 16h | **80h** |
| Fase 3 | 60h | 32h | 24h | **116h** |
| Fase 4 | 56h | 28h | 20h | **104h** |
| Fase 5 | 40h | 36h | 16h | **92h** |
| **TOTAL** | **212h** | **124h** | **84h** | **420h** |

---

## 8. Criterios de Aceptación por Fase

### Fase 1 ✅ COMPLETA (2026-07-25)
- [x] `delete_communication_log` funciona sin AttributeError (C-01)
- [x] `GET /messaging/history` no retorna registros soft-deleted (C-02)
- [x] WebSocket rechaza usuarios sin `messaging:read` (C-03)
- [x] Presencia cross-instancia funciona via Redis (C-04)
- [x] `POST /crm/messaging/send` con `persona_id` directo valida sede (C-05)
- [x] Todos los tests existentes pasan (sin regressión) — 38/38
- [x] Schema CommunicationLog extendido (A-03)
- [x] Channel enum validado (A-04)
- [x] Index en auth_notifications.user_id (A-05)
- [x] marked_count en mark-all-read (A-06)
- [x] Offset en notifications y history (M-01, M-02)
- [x] Room name allowlist (M-04)
- [x] Rate limit en broadcast (M-05)
- [x] sede_id en notifications (M-06)
- [x] BackendNotification.id type fix (M-08)

### Fase 2
- [ ] `UnifiedMessage` model funciona con ambos paradigmas (DM + internal chat)
- [ ] Typing indicators llegan vía WebSocket a otros usuarios de la sala
- [ ] Read receipts se propagan correctamente
- [ ] Presencia muestra nombre real del usuario (no client_id raw)
- [ ] Búsqueda full-text retorna resultados relevantes
- [ ] Coverage ≥ 70%

### Fase 3
- [ ] AI sugiere respuestas contextuales para mensajes pastorales
- [ ] Sentiment analysis detecta mensajes urgentes/crisis
- [ ] Follow-ups automáticos se crean según reglas configurables
- [ ] Dashboard de engagement muestra métricas por sede
- [ ] Coverage ≥ 75%

### Fase 4
- [ ] WhatsApp messages se envían vía Meta Business API real
- [ ] Workflows se ejecutan según triggers configurados
- [ ] SLAs se monitorean y escalan automáticamente
- [ ] Plantillas de WhatsApp se aprueban y versionan
- [ ] Coverage ≥ 80%

### Fase 5
- [ ] Prayer Wall funciona con oraciones anónimas
- [ ] Service Live permite polls en tiempo real
- [ ] WebSocket propaga eventos del servicio a todos los conectados
- [ ] Coverage ≥ 80%

---

## 9. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Meta rechaza templates de WhatsApp | Media | Alto | Templates genéricos first, personalización después |
| Ollama/Llama3 insuficiente para sentiment analysis | Media | Medio | Fallback a reglas keyword-based |
| Redis pub/sub con lag en alta concurrencia | Baja | Alto | Buffer + retry logic + monitoring |
| Breaking changes en UnifiedMessage | Media | Alto | Migración dual (legacy + unified) con feature flag |
| Alcance creep en Fase 5 | Alta | Medio | Feature flag por sede, releases incrementales |

---

## 10. Referencias

- `REGLAS.md` — Reglas de arquitectura CCF
- `docs/ESTADO_ARQUITECTURA_CCF.md` — Estado actual
- `backend/api/messaging.py` — Router principal de mensajería
- `backend/mesh_websockets.py` — Manager WebSocket Redis
- `backend/services/messaging.py` — Gateway de envío
- `backend/crud/crm_/communication.py` — CRUD CommunicationLog
- `backend/crud/crm_/notifications.py` — CRUD Notifications
- Benchmark: Intercom, Zendesk, Slack, Teams, Planning Center, Breeze, Faithlife
