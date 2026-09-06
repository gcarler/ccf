# Matriz RBAC Canónica — Módulo Mensajería y Chat Directo

**Última actualización:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Módulo:** `messaging`  
**Routers:** `backend/api/chat.py` y `backend/api/messaging.py`  
**Guards de Autorización:**
- `require_module_access("messaging", "read")`
- `require_module_access("messaging", "edit")`
- `require_staff_or_admin`

---

## 1. Taxonomía de Permisos Canónicos

El sistema de permisos desacoplado de CCF define los siguientes permisos para el módulo de Mensajería:

| Permiso | Etiqueta | Descripción Operativa |
|---|---|---|
| `messaging:read` | Mensajes: lector | Permite acceder a la interfaz de mensajes, consultar conversaciones propias, listar mensajes, buscar usuarios de la misma sede para @menciones o nuevos chats, recibir notificaciones y descargar adjuntos autorizados. |
| `messaging:edit` | Mensajes: editor | Permite crear conversaciones, enviar mensajes directos, subir archivos adjuntos, eliminar mensajes propios (soft-delete) y marcar conversaciones como leídas. **Incluye jerárquicamente `messaging:read`**. |
| `require_staff_or_admin` | Guard de Staff | Restringido a roles administrativos (`ADMINISTRADOR`, `GESTOR`, `STAFF`) para envío de comunicaciones internas (`/messaging/send`) y visualización del registro de envíos (`/messaging/history`). |

---

## 2. Asignación de Roles de Plataforma

La asignación base de permisos por rol en la plataforma (`backend/core/permissions.py`) opera de la siguiente manera:

| Rol de Plataforma | `messaging:read` | `messaging:edit` | `require_staff_or_admin` | Ámbito de Sede (Multi-Tenant) |
|---|:---:|:---:|:---:|---|
| **Super administrador** | ✅ | ✅ | ✅ | **Global** (`sede_id is None` o sede asignada con bypass total). |
| **Administrador** | ✅ | ✅ | ✅ | **Sede propia** (Estrictamente delimitado por `current_user.sede_id`). |
| **Gestor** | ✅ | ✅ | ✅ | **Sede propia** (Gestión de comunicaciones y chats de la sede). |
| **Editor** | ✅ | ✅ | ❌ | **Sede propia** (Participación en chats y mensajería interna). |
| **Lector** | ⚠️ | ⚠️ | ❌ | Requiere asignación explícita de rol modular `messaging` o permiso grant. |
| **Miembro** | ⚠️ | ⚠️ | ❌ | Requiere asignación explícita de rol modular `messaging` o permiso grant. |
| **Estudiante / Aspirante** | ❌ | ❌ | ❌ | Sin acceso por defecto al inbox ministerial de la plataforma. |

> [!NOTE]
> Usuarios sin rol global administrativo pueden recibir grants modulares vía `UsuarioRolModulo` o `UsuarioPermisoOverride`, permitiéndoles acceso exclusivo al módulo `messaging` sin elevar privilegios en otros módulos.

---

## 3. Matriz Detallada de Endpoints vs Permisos

| Endpoint | Método | Guard Requerido | Nivel Mínimo | Alcance y Aislamiento de Datos |
|---|---|---|---|---|
| `/api/chat/users/search` | `GET` | `require_module_access` | `messaging:read` | Solo usuarios activos de la misma sede (`Persona.sede_id == actor.sede_id`). Excluye al actor. |
| `/api/chat/conversations` | `GET` | `require_module_access` | `messaging:read` | Solo conversaciones donde el usuario figura en `ConversationParticipant`. |
| `/api/chat/conversations` | `POST` | `require_module_access` | `messaging:edit` | Todos los participantes deben pertenecer a la misma sede del actor (403 si cross-sede). |
| `/api/chat/conversations/{id}/messages` | `GET` | `require_module_access` | `messaging:read` | Solo participantes del chat. 404 existence-leak safe si no es participante o es cross-sede. |
| `/api/chat/conversations/{id}/messages` | `POST` | `require_module_access` | `messaging:edit` | Solo participantes. Verificación TOCTOU al commit time. 404 safe. Notifica menciones intra-sede. |
| `/api/chat/my-messages` | `GET` | `require_module_access` | `messaging:read` | Mensajes autorizados enviados por el usuario autenticado. |
| `/api/chat/mentions` | `GET` | `require_module_access` | `messaging:read` | Mensajes donde el usuario fue mencionado en chats autorizados. |
| `/api/chat/conversations/{id}/read` | `POST` | `require_module_access` | `messaging:read` | Actualiza `last_read_at` del caller. Verificación TOCTOU de participación. 404 safe. |
| `/api/chat/messages/{id}` | `DELETE` | `require_module_access` | `messaging:edit` | Solo el remitente del mensaje (`msg.sender_id == current_user.id`). Soft-delete. 404 safe. |
| `/api/chat/attachments/{c_id}/{s_id}/{fn}` | `GET` | `require_module_access` | `messaging:read` | Caller debe ser participante activo de la conversación y `sede_bucket == actor_sede`. |
| `/api/chat/upload-attachment` | `POST` | `require_module_access` | `messaging:edit` | Sube archivo a `/static/chat_attachments/{actor_sede_id}/`. Valida magic bytes y MIME. |
| `/api/messaging/ws` | `WS` | Token JWT handshake | Autenticado | Solo suscribe a rooms públicas o rooms privadas (`dm_*`, `project_*`) autorizadas. |
| `/api/messaging/presence/{room}` | `GET` | `require_module_access` | `messaging:read` | Salas privadas requieren participación activa. 404 safe si no autorizado. |
| `/api/messaging/notifications` | `POST` | `require_module_access` | `messaging:read` | Emisión limitada a salas autorizadas con rate-limit de 10 eventos/min. |
| `/api/messaging/notifications` | `GET` | `require_module_access` | `messaging:read` | Solo notificaciones personales del usuario (`Notification.user_id == caller.persona_id`). |
| `/api/messaging/notifications/{id}` | `PATCH` | `require_module_access` | `messaging:read` | Solo notificaciones personales (ownership BOLA safe, 404 si es ajena). |
| `/api/messaging/notifications/mark-all-read`| `POST`| `require_module_access` | `messaging:read` | Marca leídas únicamente las notificaciones del caller. |
| `/api/messaging/history` | `GET` | `require_staff_or_admin` | Staff / Admin | Historial de envíos masivos filtrado por `Persona.sede_id == user_sede`. |
| `/api/messaging/send` | `POST` | `require_staff_or_admin` | Staff / Admin | Registro de mensaje interno validando que destinatario pertenezca a la misma sede. |

---

## 4. Invariantes de Seguridad y Multi-Tenant (Axioma 3)

1. **Aislamiento Horizontal Estricto:**
   - Ningún usuario, independientemente de su rol (a excepción del superadministrador global), puede emitir mensajes, leer historiales o consultar usuarios de otra sede.
   - Si un participante de otra sede es enviado en la creación de una conversación, la solicitud falla de inmediato con `403 Forbidden` (`detail: "Todos los participantes deben pertenecer a la misma sede"`).

2. **Cierre de Vectores BOLA (Broken Object Level Authorization):**
   - El sistema evita responder `403 Forbidden` al acceder a conversaciones o mensajes de los que el usuario no forma parte.
   - En su lugar, emite `404 Not Found` uniforme para impedir que un atacante determine si un ID arbitrario existe o no en el sistema.

3. **Cierre de Vectores TOCTOU (Time-Of-Check to Time-Of-Use):**
   - Debido a la naturaleza concurrente de los chats, se valida doblemente la participación: una al iniciar la solicitud y otra inmediatamente antes de persistir (`commit`) el mensaje o la marca de lectura.
   - Si un administrador expulsó al participante de la conversación entre el momento del fetch y la mutación, la operación aborta con `404 Not Found`.

4. **Reglas de Acceso en Frontend (`workspaceAccess.ts`):**
   - La ruta `/plataforma/messages` está protegida por:
     ```typescript
     { prefix: "/plataforma/messages", kind: "module", module: "messaging", minLevel: "read" }
     ```
   - Si el usuario carece del permiso `messaging:read`, el frontend bloquea la navegación y redirige a la vista principal autorizada.
