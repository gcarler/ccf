# Checklist de Producción — Mensajería / Chat CCF

**Propósito:** criterio único de salida para declarar el módulo de Mensajería/Chat listo al 100% en producción.

**Estado actual:** **NO LISTO AL 100%**.

**Última auditoría E2E registrada:** 2026-08-01.

- Batería profunda frontend: **16/17 pruebas pasan**.
- Fallo abierto: `tests/e2e/messaging/chat-admin.spec.ts` — 401 del layout y `Config load failed`.
- Smoke autenticado oficial: **5 pruebas omitidas** por falta de credenciales E2E.
- Auditoría dirigida de seguridad: **9 pruebas nuevas + 79 regresiones relacionadas pasan**.
- No se deben marcar estos resultados como aprobación de producción.

---

## 0. Regla de salida

El módulo solo puede declararse **100% listo** cuando todas las casillas obligatorias estén marcadas y exista evidencia enlazada o archivada.

### Bloqueadores absolutos

No aprobar el release si existe alguno de estos puntos:

- [ ] Fallo en una prueba de aislamiento multi-sede o fuga de conversaciones/mensajes/adjuntos.
- [ ] Fallo en autorización WebSocket, reconexión, broadcast o presencia.
- [ ] Fallo en enviar, listar, marcar como leído o eliminar mensajes propios.
- [ ] Fallo en descarga autenticada de adjuntos o bypass de tenant isolation.
- [ ] Fallo E2E en un flujo crítico de usuario.
- [ ] Prueba E2E crítica omitida por falta de credenciales, configuración o servicio.
- [ ] Error 401/403/500 no explicado en una ruta de mensajería.
- [ ] Notificación de un usuario modificable por otro usuario.
- [ ] Envío a una persona de otra sede.
- [ ] Cambio involuntario de una ruta pública de Community a una ruta autenticada.
- [ ] Typecheck, lint crítico o build de producción fallando por archivos del alcance.
- [ ] Migraciones pendientes, rollback no probado o cambios de contrato sin documentar.

Los warnings visuales menores pueden registrarse, pero **no se acepta como warning** un 401, un skip de autenticación o un error de consola en una ruta crítica hasta demostrar que es ruido externo y no afecta el flujo.

**Prohibición de aprobación por excepción:** bajo ninguna circunstancia se puede aprobar por excepción, deuda técnica o aceptación de riesgo un fallo de seguridad, aislamiento multi-sede, autorización RBAC/WebSocket, flujo crítico E2E o prueba crítica omitida. Esos resultados mantienen el release bloqueado hasta su corrección y nueva evidencia.

---

## 1. Alcance y contratos

### Superficies que deben certificarse

- [ ] Inbox y notificaciones internas: `/api/messaging/*`.
- [ ] Chat directo: `/api/chat/*`.
- [ ] Presencia: `/api/messaging/presence/{room}` y gateway WebSocket.
- [ ] Adjuntos: upload, URL autenticada, descarga, validación de magic bytes y aislamiento por sede.
- [ ] Community pública: `/api/community/cards`, `/api/community/grupos`, `/api/community/events`.
- [ ] Bridge CRM: `/api/crm/messaging/*`.
- [ ] Workspace de Projects: chat contextual, Inbox contextual y eventos WebSocket de proyecto.
- [ ] Rutas frontend canónicas y legacy documentadas.

### Fuentes de verdad

- [ ] `docs/ESTADO_CHAT.md` está actualizado.
- [ ] `docs/ESTADO_MESSAGING_COMMUNITY.md` está actualizado.
- [ ] `docs/MESSAGING_COMMUNITY_API_CONTRACTS.md` coincide con el código.
- [ ] `docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md` coincide con los guards reales.
- [ ] Se documentan explícitamente las diferencias entre `/messaging`, `/chat`, Community y CRM.
- [ ] No existe una segunda fuente de verdad para mensajes, notificaciones o estados de lectura.

---

## 2. Backend: funcionalidad y contratos

Ejecutar desde `/root/ccf`:

```bash
./venv/bin/python scripts/test_messaging_quality.py
```

Resultado requerido: **exit 0, todas las suites internas pasan**.

### CRUD de chat

- [ ] Crear conversación con participantes válidos.
- [ ] Evitar conversaciones duplicadas cuando el contrato lo impida.
- [ ] Listar únicamente conversaciones visibles para el usuario.
- [ ] Listar mensajes con `limit` y cursor `before`.
- [ ] Enviar mensaje no vacío.
- [ ] Preservar menciones y generar notificaciones correspondientes.
- [ ] Marcar conversación/mensaje como leído.
- [ ] Eliminar únicamente mensajes propios mediante soft delete.
- [ ] El mensaje eliminado no aparece en lecturas posteriores.
- [ ] Errores de contrato devuelven códigos y shapes documentados.

### Inbox y notificaciones

- [ ] Listar notificaciones del usuario autenticado.
- [ ] Marcar una notificación propia como leída.
- [ ] Marcar todas las notificaciones propias como leídas.
- [ ] Rechazar modificación de una notificación ajena.
- [ ] Mantener ownership después de refresh de token.
- [ ] Inbox interno filtra por sede y permisos reales.
- [ ] Historial interno filtra por sede.
- [ ] `POST /messaging/send` rechaza destinatarios cross-sede.

### CRM bridge

- [ ] `GET /api/crm/messaging/history` mantiene el scope CRM/persona/sede.
- [ ] `GET /api/crm/messaging/history/{id}` rechaza recursos fuera de scope.
- [ ] `POST /api/crm/messaging/send` valida target y permisos CRM.
- [ ] El bridge CRM no se mezcla con `/api/messaging/history`.

### Pruebas backend ampliadas

```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_chat_sede_isolation.py \
  tests/test_api_integration.py \
  tests/test_structural_contracts.py
```

Si el cambio toca adjuntos, notificaciones o RBAC, ejecutar además las pruebas específicas existentes del área y adjuntar el listado exacto de archivos ejecutados.

---

## 3. Seguridad, tenant isolation y RBAC

### Aislamiento multi-sede

Probar con al menos dos usuarios pertenecientes a sedes distintas:

- [ ] Usuario A no lista conversaciones privadas de usuario/sede B.
- [ ] Usuario A no lee mensajes por ID pertenecientes a sede B.
- [ ] Usuario A no puede marcar como leído una notificación de B.
- [ ] Usuario A no puede descargar un adjunto de B.
- [ ] Usuario A no puede enviar a una persona de B.
- [ ] Usuario A no puede ver presencia sensible de una sala fuera de scope.
- [ ] Los rechazos no filtran existencia: usar 404 donde el contrato lo exige.
- [ ] No existen consultas sin filtro `sede_id` en superficies privadas.

### Matriz mínima de roles

Verificar con usuarios reales o fixtures de integración. **El guard real vigente para `backend/api/chat.py` y la mayoría de `backend/api/messaging.py` es `messaging:read` / `messaging:edit`; `chat:read` / `chat:write` aparece en documentación histórica y no debe usarse para declarar aprobación sin contrastarlo con el código.**

Comando reproducible para RBAC y aislamiento:

```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_permissions_granular.py \
  tests/test_messaging_audit_phase1.py \
  tests/test_chat_sede_isolation.py \
  tests/test_messaging_sede_isolation.py -v --tb=short
```

| Rol | Notifications | Chat lectura (`messaging:read`) | Chat escritura (`messaging:edit`) | History/Send interno | Community pública | Community mutación |
|---|---:|---:|---:|---:|---:|---:|
| Administrador | Sí | Sí | Sí | Sí | Sí | Sí |
| Gestor persistido | Sí | Sí | Sí | Sí vía `academy:manage` heredado | Sí | Sí |
| Editor persistido | Sí | Sí | Sí | No salvo que tenga `academy:manage` | Sí | Sí |
| Lector persistido | Sí | Sí | No | No | Sí | No |
| Miembro | No | No | No | No | Sí | No |

- [ ] Cada resultado observado coincide con `MESSAGING_COMMUNITY_RBAC_MATRIX.md` y con los guards del commit probado.
- [ ] Se verifica la asimetría vigente: `history/send` usa el gate heredado `academy:manage`, no se asume `messaging:*`.
- [ ] Se verifica que `community/cards` continúe público solo si esa excepción está aprobada explícitamente.
- [ ] Tokens expirados renuevan correctamente o redirigen a login sin bucles.
- [ ] Sin token no se muestran datos privados ni se abren sockets autorizados.

---

## 4. WebSocket, tiempo real y presencia

- [ ] El handshake exige la autorización definida por el contrato.
- [ ] El usuario no puede suscribirse a una room fuera de su scope.
- [ ] `direct_message` llega al destinatario correcto.
- [ ] `project_message` llega únicamente al proyecto correcto.
- [ ] `notification:new` llega únicamente al usuario correcto.
- [ ] La presencia refleja join/leave y no filtra usuarios fuera de scope.
- [ ] Reconexión con backoff funciona después de cierre inesperado.
- [ ] La UI no duplica mensajes cuando llegan POST y WebSocket en distinto orden.
- [ ] La UI no abre conexiones duplicadas al cambiar Chat/Inbox.
- [ ] REST se usa como fuente de verdad después de reconectar.
- [ ] Un evento malformado no rompe el componente ni deja estado corrupto.
- [ ] Se registran métricas/logs mínimos de conexión, cierre y error sin incluir contenido sensible.

Pruebas frontend existentes relacionadas:

```bash
cd /root/ccf/frontend
pnpm exec vitest run \
  src/hooks/useWorkspaceSocket.test.ts \
  src/app/plataforma/messages/_hooks/useChatThread.test.ts
```

Evidencia adicional requerida para producción:

```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_messaging_audit_phase1.py \
  tests/test_projects_chat_websocket.py \
  tests/test_cms_v2_presence.py -v --tb=short
```

- [x] Prueba automatizada del handshake con token ausente/inválido, usuario inactivo y permiso ausente.
- [x] Prueba automatizada de room privada no autorizada y DM autorizado con dos participantes del mismo tenant.
- [x] Prueba automatizada de presencia privada: participante permitido, no participante same-sede y usuario cross-sede rechazados con 404.
- [ ] Captura/log de reconexión después de caída del socket.
- [x] Confirmación automatizada de autorización de room con usuario de otra sede.

---

## 5. Adjuntos

### Upload

- [ ] Solo usuarios autorizados pueden subir adjuntos.
- [ ] El backend valida tamaño máximo.
- [ ] El backend valida MIME declarado y magic bytes reales.
- [ ] Archivos con extensión/MIME falsificado son rechazados.
- [ ] Nombre de archivo se sanitiza.
- [ ] El almacenamiento queda aislado por sede/tenant.
- [ ] No se persisten rutas controladas por el cliente sin normalización.

### Descarga

- [ ] La URL de descarga requiere autenticación.
- [ ] La descarga valida ownership, participación o scope de sede.
- [ ] Un usuario de otra sede recibe rechazo seguro.
- [ ] Un usuario sin permiso no puede obtener el blob cambiando el ID.
- [ ] Adjuntos antiguos mantienen compatibilidad según la política aprobada.
- [ ] URLs legacy no se convierten en acceso público accidental.
- [ ] Se registra auditoría sin almacenar secretos ni contenido sensible.

### Evidencia

Comando reproducible para las pruebas de adjuntos actualmente existentes:

```bash
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_chat_100pct_coverage.py -k 'attachment or upload' -v --tb=short
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_cms_upload_and_image_hardening.py -k 'spoofed_mime' -v --tb=short
```

Estos comandos cubren upload, tipos inválidos, tamaño, referencias protegidas y MIME spoofing donde los tests existentes lo implementan; no deben presentarse como cobertura completa de descarga autenticada. Si el filtro no encuentra pruebas, el resultado es un bloqueo de cobertura. Antes del release debe existir además un test ejecutable y explícito para `GET /api/chat/attachments/{conversation_id}/{sede_bucket}/{filename}` con token válido, token ausente, participante ajeno y usuario cross-sede.

- [ ] Prueba de upload válido.
- [ ] Prueba de MIME spoofing.
- [x] Prueba de descarga autenticada.
- [x] Prueba de descarga sin token.
- [x] Prueba cross-sede y participante heredado cross-sede.
- [x] Prueba de adjunto inexistente.
- [x] Verificación de que el mount estático público no reemplaza la ruta protegida de chat.

---

## 6. Frontend unitario e integración

Desde `/root/ccf/frontend`:

```bash
pnpm exec vitest run \
  src/hooks/useWorkspaceSocket.test.ts \
  src/app/plataforma/messages/_hooks/useChatThread.test.ts \
  src/app/plataforma/messages/_hooks/useConversations.test.ts \
  src/components/projects/ProjectContextPanel.test.tsx \
  src/hooks/useProjectInbox.test.ts
```

- [ ] Estados loading, vacío y error tienen UI controlada.
- [ ] Enviar mensaje muestra error si falla el POST.
- [ ] El hilo no pierde mensajes al reconectar.
- [ ] El contador no leído no retrocede por una respuesta REST obsoleta.
- [ ] Búsqueda, paginación y filtros no mezclan conversaciones.
- [ ] Menciones no generan XSS.
- [ ] Teclado y lectores de pantalla funcionan en tabs, composer y acciones.
- [ ] El layout móvil no produce overflow horizontal.
- [ ] No hay `console.error` nuevo en rutas críticas.

---

## 7. E2E frontend

### Batería profunda frontend con mocks

Esta batería valida composición y comportamiento del frontend. **No certifica por sí sola autenticación real, RBAC, aislamiento multi-sede, adjuntos ni el backend.** Debe reportarse separada de la batería real.

```bash
cd /root/ccf/frontend
PLAYWRIGHT_BASE_URL=http://localhost:3000 \
  npx playwright test tests/e2e/messaging/direct-messages.spec.ts \
  tests/e2e/messaging/chat-admin.spec.ts \
  tests/e2e/messaging/chat-admin-center.spec.ts \
  tests/e2e/messaging/comments-admin-center.spec.ts \
  tests/e2e/crm/messaging.spec.ts \
  --workers 1 --reporter=list
```

- [ ] 100% de pruebas pasan: `failed = 0`.
- [ ] `skipped = 0`.
- [ ] Fallos de consola no explicados: `0`.
- [ ] Respuestas API inesperadas `>= 400`: `0`.
- [ ] El runner se ejecuta secuencialmente; no lanzar varios runners administrados en paralelo porque comparten `.next` y reportes.
- [ ] Cualquier excepción aprobada debe tener issue, causa, impacto, mitigación y firma; nunca se convierte automáticamente en warning.

### Smoke autenticado real

Configurar explícitamente:

```bash
export E2E_AUTH_ENABLED=1
export E2E_EMAIL='usuario-e2e-real'
export E2E_PASSWORD='secreto-e2e-real'
export E2E_API_URL='http://127.0.0.1:8000/api'
```

Ejecutar:

```bash
cd /root/ccf/frontend
npm run test:e2e:messaging
```

- [ ] Las 5 rutas del smoke ejecutan, no quedan `skipped`.
- [ ] `/plataforma/messages` carga sin 401/403/500.
- [ ] `/plataforma/inbox/chat` carga sin 401/403/500.
- [ ] `/plataforma/community` carga según su contrato público/autenticado.
- [ ] `/plataforma/community/events` carga o muestra vacío controlado.
- [ ] No hay errores de consola ni assets rotos.

### Pruebas backend de integración y seguridad

La batería mockeada anterior no sustituye estas pruebas. Este comando valida integración backend, contratos, permisos, aislamiento y lógica de tiempo real; **no es un E2E con dos navegadores/usuarios reales**:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_chat_api.py \
  tests/test_chat_extended.py \
  tests/test_chat_gap.py \
  tests/test_chat_100pct_coverage.py \
  tests/test_messaging.py \
  tests/test_messaging_api.py \
  tests/test_messaging_audit_phase1.py \
  tests/test_messaging_100pct.py \
  tests/test_messaging_100pct_coverage.py \
  tests/test_messaging_sede_isolation.py \
  tests/test_chat_sede_isolation.py \
  tests/test_projects_chat_websocket.py \
  tests/test_cms_v2_presence.py \
  tests/test_permissions_granular.py
```

- [ ] `failed = 0` y `errors = 0`.
- [ ] No pruebas críticas omitidas.
- [ ] Evidencia de usuario A contra sede B y usuario B contra sede A.
- [ ] Las respuestas de autorización coinciden con el contrato, incluyendo 404 existence-leak safe cuando corresponda.

### E2E real autenticado pendiente de certificación

Para llamarlo E2E real se requiere un spec ejecutable con dos usuarios autenticados, dos sedes y servicios reales. Debe cubrir login, carga del workspace, conversación, envío, lectura, WebSocket, presencia y descarga de adjuntos. La batería frontend mockeada y el pytest backend anterior **no sustituyen** este requisito.

- [ ] Existe un spec/fixture versionado que crea o provisiona los dos usuarios y sedes de prueba.
- [ ] El spec ejecuta sin `skip` con credenciales E2E controladas.
- [ ] Usuario A no puede leer, recibir por WebSocket ni descargar datos de B.
- [ ] Usuario A no puede enviar a una persona de B.
- [ ] El resultado queda archivado con trazas, logs y artefactos.

Mientras no exista y pase ese spec, esta casilla permanece bloqueada.

- [ ] `failed = 0` y `errors = 0`.
- [ ] No pruebas críticas omitidas.
- [ ] Evidencia de usuario A contra sede B y usuario B contra sede A.
- [ ] Las respuestas de autorización coinciden con el contrato, incluyendo 404 existence-leak safe cuando corresponda.

### Contrato de lectura

No mezclar esta operación con un contrato inexistente:

- [ ] `POST /api/chat/conversations/{conversation_id}/read` es la ruta vigente para marcar la conversación como leída.
- [ ] Se confirma contra `backend/api/chat.py` que no existe una ruta `PATCH /api/chat/messages/{message_id}/read`; el frontend y la documentación no deben intentar usarla.
- [ ] La documentación y el frontend usan exactamente el método/ruta que expone el backend; cualquier divergencia debe resolverse antes del release.

### Pruebas concretas de adjuntos y tiempo real

- [ ] Ejecutar y registrar `tests/test_chat_100pct_coverage.py` y `tests/test_cms_upload_and_image_hardening.py` para upload, tipos y MIME spoofing; usar los comandos reproducibles indicados arriba.
- [ ] Ejecutar `tests/test_migrate_chat_attachment_urls.py` si el release toca compatibilidad de URLs antiguas.
- [ ] Ejecutar `tests/test_messaging_audit_phase1.py` para autorización de rooms DM, permisos `messaging:read`, rechazo cross-sede y allowlist de rooms.
- [ ] Ejecutar `tests/test_projects_chat_websocket.py` para broadcast de proyecto y `tests/test_cms_v2_presence.py` únicamente para el flujo de presencia CMS.
- [ ] Mantener una prueba dedicada del handshake real `GET /api/messaging/ws/{client_id}` (token inválido, usuario inactivo, sin `messaging:read` y room no autorizada); si no existe, la evidencia manual autenticada y el issue de cobertura son obligatorios y bloquean el 100%.
- [ ] Ejecutar las pruebas de `useWorkspaceSocket` y `useChatThread` para ciclo de vida del cliente.
- [x] Evidencia automatizada en `tests/test_messaging_security_gaps.py` para `GET /api/chat/attachments/{conversation_id}/{sede_bucket}/{filename}` con token válido, token ausente, usuario no participante, usuario cross-sede, participante heredado cross-sede y archivo inexistente.
- [x] Evidencia automatizada en `tests/test_messaging_security_gaps.py` de `GET /messaging/ws/{client_id}` con token inválido, usuario inactivo, permiso ausente, room no autorizada, room autorizada y broadcast a dos participantes del mismo tenant.

### Compatibilidad de rutas

- [ ] `/plataforma/inbox/messages` redirige a `/plataforma/messages` según contrato.
- [ ] `/plataforma/community/messages` redirige a `/plataforma/messages` según contrato.
- [ ] Los enlaces internos apuntan a la ruta canónica.
- [ ] No se rompe el deep link con `?conv={id}`.

---

## 8. Calidad, build y operación

- [ ] `pnpm exec eslint` de las superficies modificadas pasa.
- [ ] `pnpm exec tsc --noEmit` pasa sin errores del alcance de Mensajería.
- [ ] `pnpm run build` pasa.
- [ ] `git diff --check` pasa en el cambio.
- [ ] Backend lint pasa en routers/services modificados.
- [ ] No hay migraciones pendientes para el release.
- [ ] Backup y rollback están documentados.
- [ ] Variables de entorno de producción están presentes y no aparecen en logs.
- [ ] Redis/WebSocket, backend, frontend y almacenamiento están monitorizados.
- [ ] Hay alertas para errores 401/403/5xx y desconexiones WebSocket.
- [ ] Hay un runbook para revocar sesiones y rotar secretos.
- [ ] Hay un runbook para desactivar temporalmente envío/adjuntos sin tumbar lectura.

---

## 9. Evidencia mínima del release

Archivar junto al release:

- [ ] Salida completa de `scripts/test_messaging_quality.py`.
- [ ] Salida de pruebas de aislamiento y contratos.
- [ ] Reporte HTML de Playwright.
- [ ] Lista exacta de pruebas E2E ejecutadas y resultado.
- [ ] Evidencia de cero `skipped` en el smoke autenticado.
- [ ] Evidencia de upload/download autenticado de adjuntos.
- [ ] Matriz RBAC firmada por responsable técnico.
- [ ] Evidencia de dos usuarios/sedes para aislamiento.
- [ ] Resultado de build y typecheck.
- [ ] Hash del commit liberado.
- [ ] Plan de rollback y responsable de ejecución.

---

## 10. Bloqueadores actuales conocidos

Estos puntos deben cerrarse antes de marcar el documento como aprobado:

1. [ ] Corregir o aislar correctamente los dos 401 y `Config load failed` que hacen fallar `chat-admin.spec.ts`.
2. [ ] Ejecutar el smoke oficial con credenciales E2E reales; no aceptar las 5 pruebas `skipped` como aprobación.
3. [x] Ejecutar pruebas dirigidas de adjuntos autenticados, spoofing, descarga, mount estático y cross-sede: 9 nuevas + regresiones verdes.
4. [x] Ejecutar evidencia de autorización WebSocket, DM autorizado, room no autorizada y presencia cross-sede: 9 nuevas + regresiones verdes.
5. [ ] Crear y aprobar el E2E integral con dos usuarios, dos sedes y servicios reales, incluyendo reconexión.
6. [ ] Resolver cualquier fallo del script backend canónico antes del release.
7. [ ] Confirmar que los errores globales ajenos de TypeScript no oculten errores de Mensajería; el typecheck del alcance de Mensajería debe quedar limpio.

---

## 11. Firma de salida

### Responsable técnico

- Nombre: ______________________________
- Fecha: _______________________________
- Commit/tag: __________________________
- Evidencia: ____________________________

### QA

- Nombre: ______________________________
- Fecha: _______________________________
- Resultado E2E: ______ / ______
- Resultado backend: ______ / ______
- Resultado RBAC/isolation: _____________

### Producto / Operaciones

- Nombre: ______________________________
- Fecha: _______________________________
- Rollback probado: Sí [ ] No [ ]
- Aprobación final: Sí [ ] No [ ]

> **Declaración obligatoria:** solo marcar “Aprobación final: Sí” cuando no existan bloqueadores, no haya pruebas críticas omitidas, todas las pruebas de seguridad/aislamiento/autorización/E2E crítica hayan pasado y toda la evidencia esté archivada. Ninguna excepción puede dispensar un fallo de seguridad, aislamiento multi-sede, autorización, flujo crítico E2E o prueba crítica omitida.
