# Contratos API — Módulo Mensajería y Chat Directo

**Última actualización:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Routers Backend:**
- `backend/api/chat.py` (Montado en `/api`, tag `chat`)
- `backend/api/messaging.py` (Montado en `/api`, tag `messaging`)  
**Frontend Canónico:** `/plataforma/messages`  
**Autenticación:** Bearer JWT (`Authorization: Bearer <token>`) via Auth v3  
**Taxonomía RBAC:** `messaging:read`, `messaging:edit`, `require_staff_or_admin`

---

## 1. Principios de Diseño y Seguridad

1. **Aislamiento Multi-Tenant Estricto (Axioma 3):**
   - Todo acceso está delimitado por `sede_id` obtenido mediante `get_user_sede_id(db, current_user.id)`.
   - Las conversaciones no almacenan `sede_id` explícito; su pertenencia de sede se deriva de la alineación de todos sus participantes. Intentar involucrar usuarios de diferentes sedes es rechazado (HTTP 403/404).
   - Superadministradores sin sede asignada operan en modo global (`sede_id is None`).

2. **Prevención de Fugas de Existencia (BOLA Defense):**
   - Si un usuario consulta una conversación, mensaje, notificación o adjunto que no le pertenece o es cross-sede, el backend responde **HTTP 404 Not Found** uniforme en vez de 403 Forbidden, imposibilitando el barrido o adivinanza de UUIDs.

3. **Defensa contra Condiciones de Carrera (TOCTOU Defense):**
   - Antes de mutar o eliminar mensajes, marcar como leído o emitir notificaciones, se re-verifica la participación activa del actor en tiempo de commit (`_assert_actor_still_participant_at_commit_time`).

4. **Validación de Archivos y Adjuntos:**
   - La subida de adjuntos valida estrictamente el MIME type y verifica los *magic bytes* reales de imágenes (PNG, JPEG, WEBP) y documentos (PDF).
   - Los archivos se almacenan en rutas aisladas por sede: `/static/chat_attachments/{sede_id}/`.
   - La descarga es autenticada y requiere ser participante activo de la conversación asociada.

5. **Tiempo Real (WebSocket & Redis Pub/Sub):**
   - Canal unificado de WebSocket en `/api/messaging/ws` con soporte de rooms (`dm_{conv_id}`, `project_{id}`, públicas).
   - Rate limiting de broadcast (10 eventos/minuto por usuario) para mitigar spam/flooding.

---

## 2. Superficie de Endpoints — Chat Directo (`/api/chat/*`)

### 2.1 Búsqueda de Usuarios para Chat y Menciones
- **Método y Ruta:** `GET /api/chat/users/search`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Busca personas activas registradas en la misma sede para iniciar conversaciones o sugerir @menciones. Excluye automáticamente al usuario autenticado. Admite prefijos `@` que son despojados de forma transparente. Implementa normalización NFD para soportar búsquedas insensibles a tildes/acentos.
- **Parámetros de Query:**
  - `q` (string, obligatorio, min: 1, max: 100): Término de búsqueda (nombre, apellido o username).
  - `limit` (integer, opcional, default: 10, max: 50): Límite de resultados.
- **Respuesta (200 OK):**
  ```json
  [
    {
      "id": "c1f72b9a-1111-4444-8888-abcdef123456",
      "username": "carlos.mora",
      "name": "Carlos Mora",
      "email": "carlos@ejemplo.com",
      "avatar_url": "/api/static/avatars/carlos.jpg",
      "church_role": "Líder de Jóvenes"
    }
  ]
  ```
- **Errores comunes:**
  - `401 Unauthorized`: Token no proporcionado o expirado.
  - `403 Forbidden`: Usuario sin permiso `messaging:read`.
  - `422 Unprocessable Entity`: Parámetro `q` vacío o excediendo longitud máxima.

---

### 2.2 Listar Conversaciones del Usuario
- **Método y Ruta:** `GET /api/chat/conversations`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Retorna todas las conversaciones directas en las que participa el usuario autenticado, ordenadas por actividad reciente. Incluye información enriquecida de participantes, último mensaje y conteo optimizado por lote de mensajes no leídos (`unread_count`).
- **Respuesta (200 OK):** Array de `ConversationRead`:
  ```json
  [
    {
      "id": "e9b2512a-3333-4444-9999-123456789abc",
      "title": null,
      "is_group": false,
      "created_at": "2026-09-01T14:30:00Z",
      "updated_at": "2026-09-05T18:22:10Z",
      "last_message_at": "2026-09-05T18:22:10Z",
      "last_message_content": "Nos vemos en la reunión general",
      "last_message_sender_id": "c1f72b9a-1111-4444-8888-abcdef123456",
      "unread_count": 2,
      "participants": [
        {
          "id": "c1f72b9a-1111-4444-8888-abcdef123456",
          "user_id": "c1f72b9a-1111-4444-8888-abcdef123456",
          "name": "Carlos Mora",
          "avatar_url": "/api/static/avatars/carlos.jpg",
          "role": "MEMBER"
        }
      ]
    }
  ]
  ```

---

### 2.3 Crear o Resolver Conversación
- **Método y Ruta:** `POST /api/chat/conversations`
- **Permiso Requerido:** `messaging:edit`
- **Descripción:** Crea una nueva conversación 1-a-1 o grupal. Si ya existe una conversación directa previa con exactamente los mismos participantes 1-a-1, se devuelve de forma idempotente la conversación existente. Valida estrictamente que todos los participantes pertenezcan a la misma sede del actor.
- **Cuerpo de la Petición:**
  ```json
  {
    "participant_ids": ["c1f72b9a-1111-4444-8888-abcdef123456"],
    "title": "Coordinación Retiro 2026"
  }
  ```
- **Respuesta (201 Created):** `ConversationRead` (mismo schema que en el listado).
- **Errores comunes:**
  - `400 Bad Request`: Menos de 1 participante especificado o participante duplicado.
  - `403 Forbidden`: Intento de iniciar conversación con usuarios de otra sede (Axioma 3).
  - `404 Not Found`: Uno o más IDs de participantes no corresponden a personas existentes.

---

### 2.4 Listar Mensajes de una Conversación
- **Método y Ruta:** `GET /api/chat/conversations/{conv_id}/messages`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Obtiene los mensajes de una conversación de forma paginada por cursor (más recientes primero). Verifica pertenencia del actor y alineación de sede.
- **Parámetros de Path:**
  - `conv_id` (UUID string): Identificador de la conversación.
- **Parámetros de Query:**
  - `limit` (integer, opcional, default: 50, max: 200): Cantidad de mensajes por lote.
  - `before` (string, opcional): Cursor ISO 8601 timestamp (ej. `2026-09-05T12:00:00Z`) o UUID para paginación hacia atrás.
- **Respuesta (200 OK):** Array de `DirectMessageItem`:
  ```json
  [
    {
      "id": "f5a11c88-aaaa-bbbb-cccc-001122334455",
      "sender_id": "c1f72b9a-1111-4444-8888-abcdef123456",
      "sender_name": "Carlos Mora",
      "content": "Adjunto el cronograma del evento @maria",
      "created_at": "2026-09-05T18:22:10Z",
      "is_read": true,
      "attachment_url": "/api/chat/attachments/e9b2512a.../sede-uuid/cronograma.pdf",
      "attachment_type": "application/pdf",
      "attachment_name": "cronograma.pdf",
      "attachment_size": 245760,
      "reply_to_id": null,
      "reply_preview": null,
      "mentions": ["maria.gonzalez"]
    }
  ]
  ```
- **Errores comunes:**
  - `404 Not Found`: Conversación inexistente o usuario no es participante (BOLA safe).

---

### 2.5 Enviar Mensaje a una Conversación
- **Método y Ruta:** `POST /api/chat/conversations/{conv_id}/messages`
- **Permiso Requerido:** `messaging:edit`
- **Descripción:** Envía un mensaje a la conversación. Procesa @menciones notificando a los participantes involucrados, registra referencias a respuestas (`reply_to_id`), asocia metadatos de adjuntos previamente subidos, y transmite el evento en tiempo real vía WebSocket a la room `dm_{conv_id}`.
- **Parámetros de Path:**
  - `conv_id` (UUID string): Identificador de la conversación.
- **Cuerpo de la Petición:**
  ```json
  {
    "content": "Revisado el documento, todo en orden.",
    "attachment_url": "/api/chat/attachments/e9b2512a.../sede-uuid/doc.pdf",
    "attachment_type": "application/pdf",
    "attachment_name": "doc.pdf",
    "attachment_size": 102400,
    "reply_to_id": "f5a11c88-aaaa-bbbb-cccc-001122334455",
    "mentions": ["maria.gonzalez"]
  }
  ```
- **Respuesta (201 Created):** Objeto `DirectMessageItem` con el mensaje creado.
- **Errores comunes:**
  - `404 Not Found`: Conversación inexistente o usuario no es participante.
  - `422 Unprocessable Entity`: Contenido vacío o referencia `reply_to_id` inválida.

---

### 2.6 Listar Mensajes Propios
- **Método y Ruta:** `GET /api/chat/my-messages`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Consulta histórica paginada de todos los mensajes enviados por el usuario autenticado en conversaciones autorizadas.
- **Parámetros de Query:**
  - `limit` (integer, opcional, default: 50, max: 200).
  - `offset` (integer, opcional, default: 0).
- **Respuesta (200 OK):** Array de `ChatMessageAdminRead`.

---

### 2.7 Listar Mensajes donde Fui Mencionado
- **Método y Ruta:** `GET /api/chat/mentions`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Retorna los mensajes donde el usuario autenticado fue etiquetado con @mención dentro de conversaciones a las que pertenece.
- **Parámetros de Query:**
  - `limit` (integer, opcional, default: 50, max: 200).
  - `offset` (integer, opcional, default: 0).
- **Respuesta (200 OK):** Array de `ChatMessageAdminRead`.

---

### 2.8 Marcar Conversación como Leída
- **Método y Ruta:** `POST /api/chat/conversations/{conv_id}/read`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Actualiza la marca de tiempo `last_read_at` del participante actual en la conversación especificada, reseteando su `unread_count`.
- **Parámetros de Path:**
  - `conv_id` (UUID string): Identificador de la conversación.
- **Respuesta (200 OK):**
  ```json
  { "ok": true }
  ```
- **Errores comunes:**
  - `404 Not Found`: Conversación no encontrada o no es participante (BOLA safe).

---

### 2.9 Eliminar Mensaje Propio (Soft Delete)
- **Método y Ruta:** `DELETE /api/chat/messages/{message_id}`
- **Permiso Requerido:** `messaging:edit`
- **Descripción:** Aplica borrado lógico (`deleted_at = now()`, `content = "[Mensaje eliminado]"`) sobre un mensaje emitido por el propio usuario. Nunca se ejecuta borrado físico (`0 db.delete`).
- **Parámetros de Path:**
  - `message_id` (UUID string): Identificador del mensaje.
- **Respuesta (200 OK):**
  ```json
  { "ok": true }
  ```
- **Errores comunes:**
  - `404 Not Found`: Mensaje inexistente, ya eliminado, o perteneciente a otro usuario (uniform 404 existence-leak safe).

---

### 2.10 Descarga Autenticada de Adjuntos
- **Método y Ruta:** `GET /api/chat/attachments/{conversation_id}/{sede_bucket}/{filename}`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Sirve el archivo binario adjunto tras validar rigurosamente que el usuario sea participante de la conversación y que el `sede_bucket` coincida con la sede del usuario. No se expone públicamente.
- **Parámetros de Path:**
  - `conversation_id` (UUID): ID de la conversación asociada.
  - `sede_bucket` (UUID string o `_global`): Sede de aislamiento.
  - `filename` (string): Nombre saneado del archivo en disco.
- **Respuesta (200 OK):** `FileResponse` con streaming binario y cabeceras `Content-Disposition`.
- **Errores comunes:**
  - `404 Not Found`: Archivo inexistente, sede no alineada, o caller no es participante.

---

### 2.11 Subida de Archivos Adjuntos
- **Método y Ruta:** `POST /api/chat/upload-attachment`
- **Permiso Requerido:** `messaging:edit`
- **Descripción:** Sube un archivo a la carpeta aislada por sede (`static/chat_attachments/{sede_id}/`). Valida extensiones, MIME types permitidos y firma de *magic bytes* para impedir suplantación de tipo.
- **Form Data:**
  - `file`: Archivo binario (imágenes: PNG, JPG, WEBP; documentos: PDF; audio: MP3, OGG, WAV).
  - `conversation_id` (UUID, opcional): Conversación objetivo para validación anticipada.
- **Respuesta (200 OK):**
  ```json
  {
    "url": "/api/chat/attachments/e9b2512a.../d290f1ee.../archivo.pdf",
    "filename": "archivo.pdf",
    "content_type": "application/pdf",
    "size": 102400
  }
  ```
- **Errores comunes:**
  - `400 Bad Request`: Magic bytes no coinciden con el MIME type declarado o extensión prohibida (ej. `.exe`, `.sh`).
  - `413 Payload Too Large`: Archivo excede límite permitido (máximo 15 MB).

---

## 3. Superficie de Endpoints — Mensajería y Notificaciones (`/api/messaging/*`)

### 3.1 Conexión WebSocket Unificada
- **Ruta:** `WS /api/messaging/ws`
- **Parámetros de Query:**
  - `token` (string, obligatorio): JWT Bearer del usuario autenticado.
  - `client_id` (string, opcional): Identificador persistente del cliente frontend.
  - `rooms` (string, opcional): Lista de rooms separadas por coma a las que suscribirse (ej. `public,dm_e9b2512a...`).
- **Comportamiento:** Valida token y pertenencia a rooms privadas (`dm_*`, `project_*`). Mantiene presencia activa y entrega eventos en tiempo real.

---

### 3.2 Consulta de Presencia en Sala
- **Método y Ruta:** `GET /api/messaging/presence/{room}`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Retorna los clientes conectados a una sala, resolviendo `client_id` a `persona_id` mediante consulta al Kernel. Si la sala es privada (`dm_*`), requiere autorización previa.
- **Parámetros de Path:**
  - `room` (string): Nombre de la sala a consultar.
- **Respuesta (200 OK):**
  ```json
  {
    "room": "dm_e9b2512a-3333-4444-9999-123456789abc",
    "clients": [
      {
        "client_id": "c1f72b9a-1111-4444-8888-abcdef123456",
        "persona_id": "c1f72b9a-1111-4444-8888-abcdef123456"
      }
    ]
  }
  ```

---

### 3.3 Broadcast de Notificación en Tiempo Real
- **Método y Ruta:** `POST /api/messaging/notifications`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Emite un evento en tiempo real a una room autorizada. Sujeto a rate limit estricto de 10 eventos/minuto por usuario respaldado en Redis.
- **Cuerpo de la Petición:**
  ```json
  {
    "room": "dm_e9b2512a-3333-4444-9999-123456789abc",
    "event": "user_typing",
    "body": { "user_id": "c1f72b9a..." }
  }
  ```
- **Respuesta (200 OK):**
  ```json
  { "status": "queued" }
  ```
- **Errores comunes:**
  - `422 Unprocessable Entity`: Campo `room` ausente o nombre de sala inválido.
  - `429 Too Many Requests`: Exceso de rate limit (más de 10 emisiones/min).

---

### 3.4 Bandeja de Notificaciones del Usuario
- **Método y Ruta:** `GET /api/messaging/notifications`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Obtiene las notificaciones personales del usuario autenticado (ownership estricto por `persona_id`).
- **Parámetros de Query:**
  - `limit` (integer, opcional, default: 20, ge: 1, le: 100).
  - `offset` (integer, opcional, default: 0).
- **Respuesta (200 OK):** Array de `Notification`:
  ```json
  [
    {
      "id": "aa112233-4455-6677-8899-aabbccddeeff",
      "title": "Te mencionaron en un chat",
      "content": "Carlos Mora: Adjunto el cronograma...",
      "type": "mention",
      "url": "/plataforma/messages?conv=e9b2512a...",
      "is_read": false,
      "created_at": "2026-09-05T18:22:11Z"
    }
  ]
  ```

---

### 3.5 Marcar Notificación como Leída
- **Método y Ruta:** `PATCH /api/messaging/notifications/{notification_id}`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Marca una notificación específica como leída. Valida titularidad estricta (retorna 404 si la notificación no pertenece al caller).
- **Respuesta (200 OK):** Objeto `Notification` actualizado.

---

### 3.6 Marcar Todas las Notificaciones como Leídas
- **Método y Ruta:** `POST /api/messaging/notifications/mark-all-read`
- **Permiso Requerido:** `messaging:read`
- **Descripción:** Marca en lote todas las notificaciones pendientes del usuario como leídas.
- **Respuesta (200 OK):**
  ```json
  { "marked_count": 5 }
  ```

---

### 3.7 Historial de Comunicaciones Internas (Staff/Admin)
- **Método y Ruta:** `GET /api/messaging/history`
- **Permiso Requerido:** `require_staff_or_admin` (ADMINISTRADOR, GESTOR, STAFF)
- **Descripción:** Consulta el registro general de comunicaciones internas (`CommunicationLog`). Filtra automáticamente por la `sede_id` del staff vía JOIN con `Persona`.
- **Parámetros de Query:**
  - `limit` (integer, opcional, default: 50, max: 100).
  - `offset` (integer, opcional, default: 0).
- **Respuesta (200 OK):** Array de `CommunicationLog`.

---

### 3.8 Registrar Mensaje Masivo o Despacho Interno
- **Método y Ruta:** `POST /api/messaging/send`
- **Permiso Requerido:** `require_staff_or_admin`
- **Descripción:** Registra una entrada de comunicación interna en `CommunicationLog`. Valida que el destinatario (`persona_id`) pertenezca a la misma sede que el actor.
- **Cuerpo de la Petición:**
  ```json
  {
    "persona_id": "c1f72b9a-1111-4444-8888-abcdef123456",
    "channel": "internal",
    "content": "Aviso pastoral sobre cambios de horario"
  }
  ```
- **Respuesta (200 OK):** Objeto `CommunicationLog` registrado.
- **Errores comunes:**
  - `404 Not Found`: Destinatario inexistente o perteneciente a otra sede.

---

## 4. Matriz Resumen de Códigos de Estado

| Código | Significado en Mensajería / Chat |
|---|---|
| **200 OK** | Lectura o actualización exitosa. |
| **201 Created** | Conversación o mensaje creado exitosamente. |
| **400 Bad Request** | Datos inválidos, adjunto con extensión no permitida o magic bytes incompatibles. |
| **401 Unauthorized** | Token ausente, inválido o expirado. |
| **403 Forbidden** | Operación cross-sede no autorizada o rol sin privilegios requeridos. |
| **404 Not Found** | Recurso inexistente, ajeno al usuario o fuera de la sede del usuario (BOLA defense). |
| **422 Unprocessable Entity** | Fallo de validación Pydantic en payload JSON. |
| **429 Too Many Requests** | Rate limit excedido en broadcasts o envíos (10 eventos/min). |
