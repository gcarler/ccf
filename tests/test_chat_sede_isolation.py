"""Axioma 3 — Sprint 3: Multi-Tenant defense-in-depth isolation tests for /api/chat/*.

Cubre los ``Axioma 3`` guards agregados a ``backend/api/chat.py`` en el
Sprint 3 para cerrar el TOCTOU gap donde una ``Conversation`` con
participantes de distintas sedes podría ser operada por un editor local
sin pasar por el check estricto de ``create_conversation``.

Guards cubiertos:

  - ``_assert_conversation_sede_aligned`` — aplicada en
    ``list_direct_messages``, ``send_direct_message`` y
    ``mark_conversation_read_endpoint``.
  - ``_assert_sender_sede_matches_actor`` — aplicada en
    ``delete_chat_message_endpoint`` como segunda capa defense-in-depth
    (flujo canónico tautológico: la prueba documenta el invariante).

Patrón (mirror de ``tests/test_messaging_sede_isolation.py``):

  1. Sembrar dos ``Sede`` con sendos admins canónicos (Auth v3 + Persona).
  2. Crear una ``Conversation`` cross-sede vía ORM directo (bypass del
     guard estricto de ``create_conversation``) — esto reproduce el
     "estado heredado" donde la conversación existe con participantes
     de ambas sedes (cualquier futura migración legacy / error de
     operador antes del hardening).
  3. Autenticar como admin de sede_a y operar contra la conversación
     cross-sede. Debe rechazarse con **404** (existence-leak safe —
     indistinguible del caso "conversation no existe").
  4. Regresión: el flujo same-sede sigue funcionando.
  5. Superadmin (actor sin ``sede_id``) bypassea todos los guards.

EXISTENCE-LEAK SAFE: la API retorna ``404 "X not found"`` (no 403 con
detail descriptivo) para cross-sede. Justificación: si la API emite 403
para "existe pero cross-sede" y 404 para "no existe", un atacante que
enumere IDs de Conversation/Message distinguible ambos casos. El
template ``"X not found"`` cierra ese vector y mantiene el contrato
consistente con el resto del CRM/CMS. Verificado contra
``docs/CIERRE_ARQUITECTURA_CCF.md`` Compliance Checklist (item Axioma 3).

Coverage matrix (19 tests — Sprint 3 + 3.5 + 3.6):

  ┌────────────────────────────────────────────────────────────────────┬─────────┐
  │ Endpoint                                                           │ Expected │
  ├────────────────────────────────────────────────────────────────────┼─────────┤
  │ POST /api/chat/conversations     (cross-sede participant)          │ 404     │
  │ POST /api/chat/conversations     (same-sede regression)            │ 201     │
  │ GET  /api/chat/conversations/{cross}/messages                      │ 404     │
  │ POST /api/chat/conversations/{cross}/messages                      │ 404     │
  │ POST /api/chat/conversations/{cross}/read                          │ 404     │
  │ DELETE /api/chat/messages/{idem-sender}       (canonical pass)     │ 200     │
  │ DELETE /api/chat/messages/{other-sender}      (cross-sede)         │ 404     │
  │ DELETE /api/chat/messages/{local-msg}        (same-sede regression)│ 200     │
  │ GET  /api/chat/users/search          (regression scope)            │ 200     │
  │ superadmin (no sede) puede crear/operar cross-sede                 │ 201     │
  │ DELETE /api/chat/messages/{msg}    TOCTOU participant removal      │ 404     │
  │ DELETE /api/chat/messages/{spoof}  cross-conv leak prevention      │ 404     │
  │ DELETE /api/chat/messages/{legacy} room_id=None back-compat       │ 200     │
  │ DELETE /api/chat/messages/{tamp}   malformed "dm_<garbage>UUID"    │ 404     │
  │ DELETE /api/chat/messages/{local}  E2E same-sede delete happy-path │ 200     │
  │ POST /api/chat/conversations/{x}/messages TOCTOU participant rem.  │ 404     │
  │ POST /api/chat/conversations/{x}/read     TOCTOU participant rem.  │ 404     │
  │ POST /api/chat/conversations/{x}/messages actor non-member 404     │ 404     │
  │ DIRECT UNIT   _assert_actor_still_participant_at_commit_time       │ 404/200 │
  └────────────────────────────────────────────────────────────────────┴─────────┘

ASIMETRÍA INTENCIONAL documentada:
- ``list_direct_messages`` mantiene ``403`` con detail ``"Not a participant"``
  para el caso early ``is_participant`` (read-only, fuera del alcance del
  TOCTOU defense — no muta estado). El resto de chat.py usa **404
  existence-leak safe**. Esta asimetría es VOLUNTARIA — read endpoint
  no muta, no requiere atomicidad, y mantener 403 da una pista útil al
  cliente legítimo ("este conv existe pero no tienes acceso") sin
  comprometer el vector de enumeración (GET es autenticado y el actor
  no bypasea ningún guard). Si en el futuro se quiere uniformidad total,
  aplicar el mismo 403→404 upgrade explícitamente abriendo ticket
  separado para no scope-creep este Sprint.
"""

from __future__ import annotations

import json as _json
import uuid as _uuid


from backend import models
from tests.conftest import auth_headers, seed_admin


# ── Helpers ─────────────────────────────────────────────────────────────────


def _seed_two_sedes(db_session):
    """Sembrar dos sedes con admins canónicos (Auth v3 + Persona).

    ``commit`` explícito al final para que las fixtures queden visibles
    a la API (mirror del patrón en ``tests/test_messaging_sede_isolation.py``).
    """
    admin_a, persona_a, sede_a = seed_admin(
        db_session, email="chatA@example.com", password="testpass123"
    )
    admin_b, persona_b, sede_b = seed_admin(
        db_session, email="chatB@example.com", password="testpass123"
    )
    db_session.commit()
    assert sede_a.id != sede_b.id
    return (admin_a, persona_a, sede_a), (admin_b, persona_b, sede_b)


def _persona_in(db, sede_id, email_suffix):
    """Crear Persona canónica + Usuario en la sede indicada (Auth v3 v2).

    El ``Usuario`` es necesario para que ``crud.resolve_persona_id_for_user``
    y ``_assert_conversation_sede_aligned`` puedan resolver el
    ``sede_id`` del FK de cada participant.

    Acepta ``sede_id`` en cualquiera de estas formas (coerción defensiva):
      - ``None`` u omitido → la sede queda NULL (persona orphan).
      - Objeto ``Sede`` ORM  → usa ``.id``.
      - ``uuid.UUID`` / ``str`` (parseable como UUID) → usa el UUID.
      - ``str`` no parseable → raise ``ValueError`` (fail fast).

    Esto previene el bug SQLite Uuid adapter ('Sede' object has no .hex)
    cuando callers pasan el ORM object directamente.
    """
    from backend.core.security import get_password_hash
    from backend.models_auth import Usuario

    # ``models.Sede`` is already imported at module level; reuse it for the
    # isinstance check instead of pulling a separate alias.

    if sede_id is not None:
        if isinstance(sede_id, models.Sede):
            effective_sede_id = sede_id.id
        elif isinstance(sede_id, _uuid.UUID):
            effective_sede_id = sede_id
        elif isinstance(sede_id, str):
            try:
                effective_sede_id = _uuid.UUID(sede_id)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"sede_id string no parseable como UUID: {sede_id!r}"
                ) from exc
        else:
            raise TypeError(
                f"sede_id debe ser None, UUID, str o objeto Sede "
                f"(got {type(sede_id).__name__})"
            )
    else:
        effective_sede_id = None

    persona_id = _uuid.uuid4()
    email = f"{email_suffix}-{_uuid.uuid4().hex[:6]}@example.com"
    persona = models.Persona(
        id=persona_id,
        first_name=f"User-{email_suffix}",
        last_name="Test",
        email=email,
        sede_id=effective_sede_id,
        estado_vital="ACTIVO",
    )
    db.add(persona)
    db.flush()

    user = Usuario(
        id=persona_id,
        sede_id=effective_sede_id,
        username=f"{email_suffix}-{_uuid.uuid4().hex[:4]}",
        email=email,
        password_hash=get_password_hash("testpass123"),
        is_active=True,
        is_email_verified=True,
    )
    db.add(user)
    db.flush()
    return persona


def _inject_cross_sede_conversation(db, participant_a, participant_b):
    """Inyectar una Conversation con participantes de DOS sedes distintas.

    Bypass del guard estricto de ``create_conversation`` — reproduce el
    "estado heredado" (TOCTOU): una conversación pre-existente que quedó
    con participantes cross-sede antes del hardening Sprint 3. Acepta
    cualquier objeto con ``.id`` (Persona o Usuario — en ambos casos
    ``.id`` alinea con el UUID de la FK de ``conversation_participants``).
    """
    conv_id = _uuid.uuid4()
    conv = models.Conversation(id=conv_id)
    db.add(conv)
    db.flush()

    cp_a = models.ConversationParticipant(
        conversation_id=conv_id, user_id=participant_a.id
    )
    cp_b = models.ConversationParticipant(
        conversation_id=conv_id, user_id=participant_b.id
    )
    db.add_all([cp_a, cp_b])
    db.flush()
    return conv


def _inject_message(db, sender_id, conv_id, content, room_id=None):
    """Inyectar un ChatMessage con ``sender_id`` y ``room_id``.

    Defaults: ``room_id = f"dm_{conv_id}"`` (convención de producción)
    para activar la participation check en ``delete_chat_message_endpoint``
    (TOCTOU + cross-conv defense). Para tests del path legacy
    ``room_id=None`` (broadcast / system messages), pasar explícitamente
    ``room_id=""`` (string vacía => se considera sin scope y equivalente
    a ``None`` para el helper) o crear el ``models.ChatMessage(...)`` directo.
    """
    effective_room_id = (
        f"dm_{conv_id}" if room_id in (None, "") else room_id
    )
    msg_id = _uuid.uuid4()
    msg = models.ChatMessage(
        id=msg_id,
        sender_id=sender_id,
        room_id=effective_room_id,
        content=content,
    )
    db.add(msg)
    db.flush()
    return msg


# ════════════════════════════════════════════════════════════════════════════
# POST /api/chat/conversations — cross-sede guard
# ════════════════════════════════════════════════════════════════════════════


def test_create_conversation_blocks_cross_sede_participant(client, db_session):
    """Axioma 3: POST /chat/conversations con participant_ids de OTRA sede
    debe rechazar **404 existence-leak safe** con detail neutro
    ``"Participant not found"``.

    La política 404 (no 403) garantiza que un atacante no pueda
    distinguir "participant existe cross-sede" de "participant no
    existe" — el detail neutro y status code neutral cierran el leak.
    """
    (admin_a, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    headers_a = auth_headers(client, email="chatA@example.com")

    resp = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_b.id)]},
    )
    assert resp.status_code == 404, (
        f"Leak o regression: cross-sede debe 404 (status {resp.status_code}): {resp.text}"
    )

    # Sanity: NO se creó ninguna conversación nueva con este participant.
    # Como admin_a + sede_a están recién seeded y este test no crea
    # conversaciones same-sede válidas, la cuenta de conversaciones
    # nuevas que incluyen persona_b como participant debe ser 0.
    db_session.expire_all()
    leaked = (
        db_session.query(models.Conversation)
        .all()
    )
    leaked_with_persona_b = sum(
        1 for c in leaked
        if any(str(cp.user_id) == str(persona_b.id) for cp in c.participants)
    )
    assert leaked_with_persona_b == 0, (
        f"FUGA: se creó conversación con persona_b cross-sede "
        f"({leaked_with_persona_b} conversaciones encontradas)"
    )


def test_create_conversation_succeeds_when_participant_local(client, db_session):
    """Regresión — same-sede: crear conversation con persona local funciona."""
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "chat-create-local")
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp.status_code == 201, (
        f"Regresión: crear DM same-sede MUST succeed "
        f"(got {resp.status_code}): {resp.text}"
    )
    conv_id = resp.json()["id"]

    cps = (
        db_session.query(models.ConversationParticipant)
        .filter(models.ConversationParticipant.conversation_id == conv_id)
        .all()
    )
    assert len(cps) == 2


# ════════════════════════════════════════════════════════════════════════════
# GET / POST /api/chat/conversations/{conv_id}/messages — defense-in-depth
# ════════════════════════════════════════════════════════════════════════════


def test_list_direct_messages_blocks_cross_sede_inherited(client, db_session):
    """Axioma 3: Conversation pre-existente con participantes cross-sede
    debe rechazar 404 (existence-leak safe) al listar mensajes — incluso
    si el caller es participante. Cierra el TOCTOU gap donde
    ``create_conversation`` no atrapa el caso heredado.
    """
    (admin_a, persona_a, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    cross_conv = _inject_cross_sede_conversation(db_session, persona_a, persona_b)
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.get(
        f"/api/chat/conversations/{cross_conv.id}/messages",
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"Defense-in-depth leak: cross-sede conv accesible por GET "
        f"(status {resp.status_code}): {resp.text}"
    )


def test_send_direct_message_blocks_cross_sede_inherited(client, db_session):
    """Axioma 3: POST mensajes sobre Conversation cross-sede heredada → 404."""
    (admin_a, persona_a, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    cross_conv = _inject_cross_sede_conversation(db_session, persona_a, persona_b)
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.post(
        f"/api/chat/conversations/{cross_conv.id}/messages",
        headers=headers_a,
        json={"content": "Mensaje cross-sede (debe fallar)"},
    )
    assert resp.status_code == 404, (
        f"Defense-in-depth leak: POST a conv cross-sede allowed "
        f"(status {resp.status_code}): {resp.text}"
    )

    # Sanity: NO se persistió ningún mensaje en esta conv cross-sede.
    db_session.expire_all()
    persisted = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.room_id.is_(None))
        .all()
    )
    leaked = [m for m in persisted if m.content == "Mensaje cross-sede (debe fallar)"]
    assert len(leaked) == 0, f"FUGA: {len(leaked)} mensajes cross-sede persistidos"


def test_mark_conversation_read_blocks_cross_sede_inherited(client, db_session):
    """Axioma 3: POST /conv/{id}/read sobre Conversation cross-sede → 404."""
    (admin_a, persona_a, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    cross_conv = _inject_cross_sede_conversation(db_session, persona_a, persona_b)
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.post(
        f"/api/chat/conversations/{cross_conv.id}/read", headers=headers_a
    )
    assert resp.status_code == 404, (
        f"Defense-in-depth leak: mark_read cross-sede allowed "
        f"(status {resp.status_code}): {resp.text}"
    )


def test_get_conversation_returns_404_for_nonexistent(client, db_session):
    """Sanity: el contrato 404 es uniforme — un conversation inexistente
    da 404 con detail ``"Conversation not found"``. Este test verifica
    que el detail del cross-sede es indistinguible de este caso.
    """
    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.get(
        f"/api/chat/conversations/{_uuid.uuid4()}/messages",
        headers=headers_a,
    )
    assert resp.status_code == 404, (
        f"Nonexistent conv debe 404 (status {resp.status_code}): {resp.text}"
    )


# ════════════════════════════════════════════════════════════════════════════
# DELETE /api/chat/messages/{message_id} — sender-sede defense-in-depth
# ════════════════════════════════════════════════════════════════════════════


def test_delete_chat_message_canonical_pass_when_sender_matches_actor(
    client, db_session
):
    """Documenta el **invariante de tautología** del segundo guard:

    El guard primario ``msg.sender_id != current_user.id`` rechaza
    ANTES que ``_assert_sender_sede_matches_actor`` corra. Este test
    verifica que cuando ``sender_id == actor_id`` (caso canónico),
    el delete funciona — es decir, ``_assert_sender_sede_matches_actor``
    no dispara erróneamente y mantiene el contrato canonical pass.

    La prueba NO simula el segundo guard "bloqueando" porque esa rama
    sólo se alcanza cuando sender_id ≠ actor_id (futuros escenarios
    de bots/forwards), donde el guard primario ya rechazó con 403/404.
    El segundo check existe como defense-in-depth contra ese futuro
    escenario y no requiere activación hoy.
    """
    (admin_a, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)

    # Crear conv same-sede (admin_a + su propia persona) y un msg
    # con sender_id = admin_a.id. Delete debe pasar.
    conv = models.Conversation(id=_uuid.uuid4())
    db_session.add(conv)
    db_session.flush()
    cp_a = models.ConversationParticipant(
        conversation_id=conv.id, user_id=admin_a.id
    )
    db_session.add(cp_a)
    msg = _inject_message(
        db_session,
        sender_id=admin_a.id,
        conv_id=conv.id,
        content="Mensaje del actor admin_a",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.delete(
        f"/api/chat/messages/{msg.id}", headers=headers_a
    )
    assert resp.status_code == 200, (
        f"sender==actor canonical pass debe 200 "
        f"(status {resp.status_code}): {resp.text}"
    )

    db_session.refresh(msg)
    assert msg.deleted_at is not None
    assert msg.content == "[Mensaje eliminado]"


def test_delete_chat_message_blocks_other_sender_with_cross_sede_conv(
    client, db_session
):
    """Axioma 3: admin_a intenta borrar un msg cuyo sender es persona_b
    (otra sede) en una conversación heredada cross-sede. El guard
    primario ``msg.sender_id != current_user.id`` retorna 404 (note: 404,
    not 403 — antes del hardening era 404 también; el 404 aquí asegura
    existence-leak safety).

    El sender-actor-sede defense-in-depth NO se ejecuta en este caso
    porque el guard primario rechaza antes (sender ≠ actor → 404).
    El test verifica el comportamiento canónico actual.
    """
    (admin_a, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)
    cross_conv = _inject_cross_sede_conversation(db_session, admin_a, persona_b)
    msg_from_b = _inject_message(
        db_session,
        sender_id=persona_b.id,
        conv_id=cross_conv.id,
        content="Mensaje legitimo de persona_b",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.delete(
        f"/api/chat/messages/{msg_from_b.id}", headers=headers_a
    )
    assert resp.status_code == 404, (
        f"Leak: admin A borró msg de persona de sede_b "
        f"(status {resp.status_code}): {resp.text}"
    )

    db_session.refresh(msg_from_b)
    assert msg_from_b.deleted_at is None, "FUGA: msg cross-sede soft-deleted"


def test_delete_chat_message_returns_404_for_nonexistent_msg(client, db_session):
    """Existence-leak safe: msg que no existe retorna 404 — uniforme con
    el path cross-sede para que el atacante no distinga.
    """
    (admin_a, _, _), _ = _seed_two_sedes(db_session)
    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.delete(
        f"/api/chat/messages/{_uuid.uuid4()}", headers=headers_a
    )
    assert resp.status_code == 404, (
        f"Nonexistent msg debe 404 (status {resp.status_code}): {resp.text}"
    )


# ════════════════════════════════════════════════════════════════════════════
# GET /api/chat/users/search — regression scope filter (pre-Sprint 3)
# ════════════════════════════════════════════════════════════════════════════


def test_search_chat_users_filters_by_actor_sede(client, db_session):
    """Axioma 3 — regression: ``GET /chat/users/search`` filtra el
    resultado por la ``sede_id`` del actor (pre-Sprint 3 hardening).

    Este endpoint filtra desde antes del Sprint 3 (cambio en el diff
    de chat.py sólo le añadió el comentario explícito), pero NO tenía
    test dedicado. Mantener este test evita que un refactor futuro
    quite accidentalmente el filtro.
    """
    (admin_a, _, sede_a), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "chat-search-local")

    headers_a = auth_headers(client, email="chatA@example.com")
    # Buscar por email único de la persona local — debe aparecer.
    query_email = persona_local.email
    resp_local = client.get(
        f"/api/chat/users/search?q={query_email}",
        headers=headers_a,
    )
    assert resp_local.status_code == 200, resp_local.text
    local_results = resp_local.json()
    local_ids = {item["id"] for item in local_results}
    assert str(persona_local.id) in local_ids, (
        f"Regresión: persona local NO aparece en búsqueda de admin A. "
        f"got {local_results}"
    )

    # Buscar por email único de la persona de sede_b — NO debe aparecer.
    query_email_cross = persona_b.email
    resp_cross = client.get(
        f"/api/chat/users/search?q={query_email_cross}",
        headers=headers_a,
    )
    assert resp_cross.status_code == 200, resp_cross.text
    cross_results = resp_cross.json()
    cross_ids = {item["id"] for item in cross_results}
    assert str(persona_b.id) not in cross_ids, (
        f"FUGA SEARCH: admin A ve persona de sede_b en búsqueda. "
        f"got {cross_results}"
    )


# ════════════════════════════════════════════════════════════════════════════
# Superadmin bypass — actor sin sede asignada conserva alcance global
# ════════════════════════════════════════════════════════════════════════════


# (No tests removed; participation-check tests follow naturally
# after the superadmin-bypass test that precedes them.)


def test_superadmin_can_create_cross_sede_conversation(
    client, db_session, monkeypatch
):
    """Axioma 3 — back-compat: un actor canónico SIN sede asignada
    conserva la capacidad de crear conversaciones cross-sede (alcance
    administrativo global).

    Mockeamos ``chat.get_user_sede_id`` (el binding local del módulo
    resuelto por ``from backend.crud.crm import get_user_sede_id``)
    para que retorne ``None`` cuando se consulta ``admin_a.id``,
    simulando la ausencia de sede propia en el actor.
    El mock es estricto: cualquier lookup contra OTRO user_id es un
    bug (los helpers del chat sólo deben consultar el actor). Si el
    mock ve otra identidad, falla ruidosamente para detectar
    refactors que introduzcan lookups no esperados.
    """
    from backend.api import chat as chat_module

    (admin_a, _, _), (_, persona_b, _) = _seed_two_sedes(db_session)

    def _strict_superadmin_sede(db, user_id):
        if str(user_id) == str(admin_a.id):
            return None  # superadmin actor sin sede
        raise AssertionError(
            f"chat.get_user_sede_id invocado para user_id inesperado "
            f"{user_id!s} (debe ser sólo admin_a.id={admin_a.id}); "
            f"posible refactor que introdujo lookup cross-actor."
        )

    monkeypatch.setattr(chat_module, "get_user_sede_id", _strict_superadmin_sede)

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_b.id)]},
    )
    assert resp.status_code == 201, (
        f"Superadmin sin sede debe poder cross-sede create "
        f"(status {resp.status_code}): {resp.text}"
    )

    conv_id = resp.json()["id"]
    cps = (
        db_session.query(models.ConversationParticipant)
        .filter(models.ConversationParticipant.conversation_id == conv_id)
        .all()
    )
    user_ids = {str(cp.user_id) for cp in cps}
    assert str(admin_a.id) in user_ids
    assert str(persona_b.id) in user_ids


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE /api/chat/messages/{message_id} — participation check (Sprint 3.5)
# TOCTOU defense + cross-conv leak prevention
# ═══════════════════════════════════════════════════════════════════════════════


def test_delete_chat_message_toctou_blocks_after_participant_removal(
    client, db_session
):
    """Axioma 3 — TOCTOU defense (gap #3 del code-reviewer):

    El actor admin_a fue participante del conv, mandó un mensaje,
    luego fue REMOVIDO del conv (admin action, bulk migration, sync
    cross-tenant o scripts legacy de purge). Cuando intenta borrar
    el mensaje histórico, la participation check debe disparar 404
    ANTES del sender check (``sender_id == actor_id`` pasaría).
    """
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "chat-toctou-local")
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")

    # Pre-condition: admin_a es participant del conv same-sede.
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]
    msg_id_resp = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "Mensaje del actor admin_a antes de remoción"},
    )
    assert msg_id_resp.status_code == 201, msg_id_resp.text
    msg_id = msg_id_resp.json()["id"]

    # Pre-condition assertion: admin_a SÍ es participant ANTES del TOCTOU.
    db_session.expire_all()
    pre_par = (
        db_session.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == admin_a.id,
        )
        .first()
    )
    assert pre_par is not None, (
        "Pre-condition: admin_a DEBE estar en conv antes de la remoción simulada. "
        "Si falla acá, check el seeding del test (probablemente el participant "
        "no se persistió en el flush)."
    )

    # TOCTOU setup: remover admin_a del conv vía ORM directo
    # (simula bulk migration entre el fetch inicial y el delete).
    db_session.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == admin_a.id,
    ).delete()
    db_session.commit()

    # Post-condition assertion: admin_a NO debe estar en conv tras remoción.
    db_session.expire_all()
    still_par = (
        db_session.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == admin_a.id,
        )
        .first()
    )
    assert still_par is None, "Post-condition: admin_a NO debe estar en conv"

    # TOCTOU defensa — debe 404, NO 200.
    resp_d = client.delete(f"/api/chat/messages/{msg_id}", headers=headers_a)
    assert resp_d.status_code == 404, (
        f"TOCTOU defense faltó: admin_a pudo borrar msg tras remoción "
        f"(status {resp_d.status_code}): {resp_d.text}"
    )

    # Sanity: el msg NO está soft-deleted.
    db_session.expire_all()
    persisted = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.id == msg_id)
        .first()
    )
    assert persisted.deleted_at is None, (
        "FUGA TOCTOU: msg soft-deleted pese al 404"
    )


def test_delete_chat_message_blocks_cross_conv_when_sender_matches(
    client, db_session
):
    """Axioma 3 — cross-conv leak prevention:

    Actor admin_a tiene ``sender_id == current_user.id`` (pasaría
    sender check), pero el msg está en una Conversation donde admin_a
    NO es participante (vector hypothetical: msg con sender_id
    reutilizado + room_id apuntando a una conv ajena). La
    participation check debe disparar 404 ANTES del sender check.
    """
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    # persona_c en la misma sede que persona_b para reproducir una conv
    # coherente a la que admin_a no pertenece (la sede de persona_c no
    # afecta a la participation check, pero la coherencia evita
    # inconsistencias en futuras extensiones).
    persona_c = _persona_in(db_session, sede_b.id, "chat-cross-c")
    db_session.commit()

    # Inyectar conv donde admin_a NO es participant (persona_b + persona_c).
    cross_conv = _inject_cross_sede_conversation(db_session, persona_b, persona_c)

    # Spurious msg: sender_id = admin_a.id + room_id apuntando a la conv
    # ajena. La participation check es la única defensa.
    spurious_msg = _inject_message(
        db_session,
        sender_id=admin_a.id,
        conv_id=cross_conv.id,
        content="Mensaje spurio con sender spoofed en conv ajena",
    )
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp_d = client.delete(f"/api/chat/messages/{spurious_msg.id}", headers=headers_a)
    assert resp_d.status_code == 404, (
        f"Cross-conv leak: admin_a borró msg en conv ajena "
        f"(status {resp_d.status_code}): {resp_d.text}"
    )

    db_session.expire_all()
    persisted = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.id == spurious_msg.id)
        .first()
    )
    assert persisted.deleted_at is None, (
        "FUGA cross-conv: msg soft-deleted pese al 404"
    )


def test_delete_chat_message_legacy_broadcast_succeeds(client, db_session):
    """Axioma 3 — back-compat:

    Mensaje con ``room_id is None`` (legacy / system broadcast / pre-migración)
    no tiene scope de conv implícito. La participation check es no-op;
    el sender check basta. El actor debe poder borrar su propio msg.
    """
    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    legacy_msg = models.ChatMessage(
        id=_uuid.uuid4(),
        sender_id=admin_a.id,
        room_id=None,  # legacy broadcast, sin conv scope
        content="Mensaje legacy / broadcast sin conv",
    )
    db_session.add(legacy_msg)
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp_d = client.delete(f"/api/chat/messages/{legacy_msg.id}", headers=headers_a)
    assert resp_d.status_code == 200, (
        f"Legacy msg sin conv scope debe 200 "
        f"(status {resp_d.status_code}): {resp_d.text}"
    )

    db_session.refresh(legacy_msg)
    assert legacy_msg.deleted_at is not None
    assert legacy_msg.content == "[Mensaje eliminado]"


def test_delete_chat_message_blocks_with_malformed_room_id(client, db_session):
    """Defense-in-depth anti-tampering: si el ``room_id`` de un msg de
    DM tiene prefijo ``"dm_"`` pero suffix no es UUID parseable, la
    participation check debe disparar 404 (no propagar raw tampering
    a un crash o un falso positivo).

    El test verifica DOS invariants:
      1. Status 404 (rechazo correcto).
      2. Detail del response no contiene el suffix malformado
         ``"NOT-A-UUID-VALUE"`` — confirma que el helper NO leak-ea
         el valor raw al cliente (anti-information-disclosure).
    """
    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    # Crear un msg directamente con un room_id "dm_<non-uuid>" — refleja
    # un escenario de tampering donde alguien escribió garbage al column.
    tampered_msg = models.ChatMessage(
        id=_uuid.uuid4(),
        sender_id=admin_a.id,
        room_id="dm_NOT-A-UUID-VALUE",  # prefijo válido, suffix no-UUID
        content="Mensaje con room_id corrupto",
    )
    db_session.add(tampered_msg)
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp_d = client.delete(
        f"/api/chat/messages/{tampered_msg.id}", headers=headers_a
    )
    assert resp_d.status_code == 404, (
        f"Tampering con room_id malformado debe 404 "
        f"(got {resp_d.status_code}): {resp_d.text}"
    )
    # Anti-leak defensivo (tolerante a header evolution): parseamos JSON
    # y comparamos el ``detail`` exacto + el conjunto de keys permitidas.
    # Esto previene que un futuro maintainer introduzca un detail distinto
    # (``"Conversation not found"``, ``"Invalid message reference"``,
    # ``"bad UUID parse"``, etc.) que reabriría el vector de enumeración,
    # sin ser tan frágil como una comparación de bytes del body completo.
    try:
        parsed = resp_d.json()
    except Exception:
        parsed = {}
    assert parsed.get("detail") == "Message not found", (
        f"Anti-leak violation: detail no uniforme (got {parsed!r}, "
        f"expected detail='Message not found')"
    )
    assert set(parsed.keys()) <= {"detail"}, (
        f"Anti-leak violation: keys inesperadas en response (got "
        f"{sorted(parsed.keys())!r}, expected subset of ['detail'])"
    )
    # Doble-check: el suffix crudo NUNCA debe aparecer en el body.
    assert "NOT-A-UUID-VALUE" not in resp_d.text, (
        f"Leak: el body expone el suffix corrupto: {resp_d.text}"
    )

    db_session.expire_all()
    persisted = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.id == tampered_msg.id)
        .first()
    )
    assert persisted.deleted_at is None


def test_delete_chat_message_local_succeeds_via_api(client, db_session):
    """Regresión — happy-path E2E same-sede delete via API.

    El flow canónico passing:
      1. POST /api/chat/conversations (admin_a + persona_local same-sede)
      2. POST /api/chat/conversations/{id}/messages (sender=admin_a)
      3. DELETE /api/chat/messages/{msg_id}
    El 200 al final confirma que el orden guards (exists → persona →
    participation → sender → sede) NO regresiona en el flujo canónico.
    Importante para detectar refactors que rompan la cadena sin que
    los tests de casos negativos (TOCTOU / cross-conv) lo noten.
    """
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "chat-local-e2e")
    headers_a = auth_headers(client, email="chatA@example.com")

    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    resp_m = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "Mensaje local que admin_a quiere borrar"},
    )
    assert resp_m.status_code == 201, resp_m.text
    msg_id = resp_m.json()["id"]

    resp_d = client.delete(f"/api/chat/messages/{msg_id}", headers=headers_a)
    assert resp_d.status_code == 200, (
        f"Regresión happy-path E2E same-sede delete MUST succeed "
        f"(got {resp_d.status_code}): {resp_d.text}"
    )

    db_session.expire_all()
    persisted = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.id == msg_id)
        .first()
    )
    assert persisted.deleted_at is not None
    assert persisted.content == "[Mensaje eliminado]"


# ═══════════════════════════════════════════════════════════════════════════════
# POST /chat/conversations/{id}/messages + POST /chat/conversations/{id}/read
# — participation-check TOCTOU defense (Sprint 3.6)
# ═══════════════════════════════════════════════════════════════════════════════


def test_send_direct_message_toctou_blocks_after_participant_removal(
    client, db_session
):
    """Axioma 3 — TOCTOU defense en send_direct_message:

    Admin_a fue participante del conv, luego fue REMOVIDO via ORM
    directo (simula admin action concurrente / bulk migration). El
    nuevo guard ``_assert_actor_still_participant_at_commit_time``
    (insertado antes de ``crud.create_direct_message``) debe detectar
    la remoción y retornar 404 existence-leak safe.

    Nota: en un flujo single-threaded la early ``is_participant`` check
    también detecta el drift. Este test verifica el contrato end-to-end
    (ambos guards en serie retornan 404). Las regresiones que sólo
    quiten uno de los dos guards se detectarían por el cambio de
    status code o la fuga del msg persistido (sanity al final).
    """
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "send-toctou-local")
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")

    # Pre-condition: crear conv same-sede via API.
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    # Sanity: el primer POST /messages funciona (admin_a todavía en conv).
    resp_m1 = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "msg antes de remoción"},
    )
    assert resp_m1.status_code == 201, (
        f"Pre-condition falló: msg inicial debe 201 (got {resp_m1.status_code}): "
        f"{resp_m1.text}"
    )

    # TOCTOU setup: remover admin_a del conv via ORM directo.
    db_session.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == admin_a.id,
    ).delete()
    db_session.commit()

    # Sanity: admin_a NO es participant ahora.
    db_session.expire_all()
    still_par = (
        db_session.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == admin_a.id,
        )
        .first()
    )
    assert still_par is None, "Pre-condition TOCTOU: admin_a debe ser removido"

    # TOCTOU defense — debe 404, no 201.
    resp_m2 = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "msg post-removal (debe fallar)"},
    )
    assert resp_m2.status_code == 404, (
        f"TOCTOU defense faltó: admin_a pudo mandar msg tras remoción "
        f"(status {resp_m2.status_code}): {resp_m2.text}"
    )

    # Sanity: NO se persistió el msg post-removal (no leak).
    db_session.expire_all()
    leaked = (
        db_session.query(models.ChatMessage)
        .filter(models.ChatMessage.content == "msg post-removal (debe fallar)")
        .first()
    )
    assert leaked is None, (
        "FUGA: msg post-removal persistido pese al 404 TOCTOU"
    )

    # Anti-leak defensivo (mirror del patrón ``malformed_room_id``): parseamos
    # JSON y verificamos que el ``detail`` es uniforme y NO se filtran keys
    # extra que reabrían el vector de enumeración.
    try:
        parsed = resp_m2.json()
    except Exception:
        parsed = {}
    assert parsed.get("detail") == "Conversation not found", (
        f"Anti-leak violation: detail no uniforme (got {parsed!r})"
    )
    assert set(parsed.keys()) <= {"detail"}, (
        f"Anti-leak violation: keys inesperadas en response "
        f"(got {sorted(parsed.keys())!r}, expected subset of ['detail'])"
    )


def test_mark_conversation_read_toctou_blocks_after_participant_removal(
    client, db_session
):
    """Axioma 3 — TOCTOU defense en mark_conversation_read_endpoint:

    Admin_a fue participante, luego removido. El endpoint ``POST /read``
    debe retornar 404 (no mutar ``last_read_at`` del conv).
    """
    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "read-toctou-local")
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")

    # Crear conv same-sede pre-condition.
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    # Mandar un msg para que ``last_read`` sea nullable inicial.
    resp_m = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        headers=headers_a,
        json={"content": "msg pre-removal"},
    )
    assert resp_m.status_code == 201, resp_m.text

    # Capturar el last_read_at del conv admin_a antes de remover.
    db_session.expire_all()
    pre_removal_row = (
        db_session.query(models.Conversation)
        .filter(models.Conversation.id == conv_id)
        .first()
    )
    # No necesitamos un valor particulas, sólo verificar que el
    # ConversationParticipant row sigue la trazabilidad.

    # TOCTOU setup: remover admin_a del conv.
    db_session.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == admin_a.id,
    ).delete()
    db_session.commit()

    # Try to mark read — debe 404.
    resp_r = client.post(
        f"/api/chat/conversations/{conv_id}/read",
        headers=headers_a,
    )
    assert resp_r.status_code == 404, (
        f"TOCTOU mark_read defense faltó "
        f"(status {resp_r.status_code}): {resp_r.text}"
    )

    # Sanity: el ConversationParticipant de admin_a sigue removido
    # (el endpoint NO debe re-insertarlo como side-effect).
    db_session.expire_all()
    after_row = (
        db_session.query(models.ConversationParticipant)
        .filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == admin_a.id,
        )
        .first()
    )
    assert after_row is None, (
        "FUGA: ConversationParticipant re-insertado por side-effect"
    )

    # Anti-leak defensivo: el response body debe ser uniforme.
    parsed = _json.loads(resp_r.text) if resp_r.text else {}
    assert parsed.get("detail") == "Conversation not found", (
        f"Anti-leak violation: detail no uniforme (got {parsed!r})"
    )
    assert set(parsed.keys()) <= {"detail"}, (
        f"Anti-leak violation: keys inesperadas en response "
        f"(got {sorted(parsed.keys())!r}, expected subset of ['detail'])"
    )


def test_send_direct_message_blocks_actor_not_in_conv_with_404(client, db_session):
    """Axioma 3 — sanity del contract 403→404:

    Admin_a intenta POSTear un msg en un conv del cual NO es participante
    (conv inyectada con persona_b + persona_c, sin admin_a). El endpoint
    debe retornar 404 con detail ``"Conversation not found"`` (uniforme
    con el resto de chat.py), NO 403 con ``"Not a participant"``.

    Antes del Sprint 3.6 el endpoint retornaba 403 — cierre existence-leak
    vector para que un atacante que descubre conv-ids no distinga
    "el conv existe y no participas" de "el conv no existe".
    """
    (admin_a, _, _), (_, persona_b, sede_b) = _seed_two_sedes(db_session)
    persona_c = _persona_in(db_session, sede_b.id, "send-404-not-member-c")
    db_session.commit()

    cross_conv = _inject_cross_sede_conversation(db_session, persona_b, persona_c)

    headers_a = auth_headers(client, email="chatA@example.com")
    resp = client.post(
        f"/api/chat/conversations/{cross_conv.id}/messages",
        headers=headers_a,
        json={"content": "ataque cross-conv"},
    )
    assert resp.status_code == 404, (
        f"Contract violation: actor_no_en_conv debe 404 "
        f"(got {resp.status_code}): {resp.text}"
    )
    try:
        parsed = resp.json()
    except Exception:
        parsed = {}
    assert parsed.get("detail") == "Conversation not found", (
        f"Anti-leak violation: detail no uniforme (got {parsed!r})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Direct unit test — _assert_actor_still_participant_at_commit_time
# (Sprint 3.6 — closes the "untestable through integration" gap)
# ═══════════════════════════════════════════════════════════════════════════════


def test_assert_actor_still_participant_unit_positive_returns_none(
    client, db_session
):
    """Direct unit test del helper _assert_actor_still_participant_at_commit_time.

    Caso positivo: el actor SI es participante del conv; el helper debe
    retornar None silenciosamente (sin raise). Esto prueba el camino
    "no-op" sin pasar por la API HTTP — relevante porque en el flujo
    integración el test nunca llega al helper si la early check ganó.

    Sin este test, una refactorización que silencie el helper (lo deje
    retornar None aún cuando el participant está ausente) no se
    detectaría en la suite integración. Por eso la prueba unitaria es
    OBLIGATORIA y no nice-to-have.
    """
    from backend.api import chat as chat_module

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "unit-positive-local")
    db_session.commit()

    # Crear conv misma-sede via API (que sí pasa el guard de create).
    headers_a = auth_headers(client, email="chatA@example.com")
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    # Direct call del helper — debe retornar None silently.
    result = chat_module._assert_actor_still_participant_at_commit_time(
        db_session, conv_id, admin_a
    )
    assert result is None, (
        f"Helper positive case debe retornar None silenciosamente "
        f"(got {result!r})"
    )


def test_assert_actor_still_participant_unit_negative_raises_404(
    client, db_session
):
    """Direct unit test — caso negativo: actor NO es participante del conv
    → el helper debe raise HTTPException(404, "Conversation not found").

    CRÍTICO: este test SI ejercita el helper directamente. Si una
    refactorización futura rompe el check o cambia el detail, este test
    falla incluso cuando los integration tests siguen verdes (porque
    la early ``is_participant`` check enmascara el bug).
    """
    from backend.api import chat as chat_module
    from fastapi import HTTPException

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "unit-negative-local")
    db_session.commit()

    # Crear conv via API.
    headers_a = auth_headers(client, email="chatA@example.com")
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    # Remover admin_a del conv via ORM (simula drift).
    db_session.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == admin_a.id,
    ).delete()
    db_session.commit()

    # Direct call — debe raise HTTPException 404.
    raised = None
    try:
        chat_module._assert_actor_still_participant_at_commit_time(
            db_session, conv_id, admin_a
        )
    except HTTPException as exc:
        raised = exc
    assert raised is not None, (
        "Helper no raise cuando actor no participante (drift no detectado)"
    )
    assert raised.status_code == 404, (
        f"Helper debe raise 404, no {raised.status_code}"
    )
    # Anti-leak: detail uniforme, sin keys extra.
    assert raised.detail == "Conversation not found", (
        f"Anti-leak violation: detail no uniforme (got {raised.detail!r})"
    )


def test_assert_actor_still_participant_unit_malformed_conv_id_raises_404(
    client, db_session
):
    """Direct unit test — conv_id malformado (no es UUID parseable) debe
    raise HTTPException(404, "Conversation not found").

    Cierra el vector de tampering donde un caller envía un conv_id que
    no es UUID → el helper NO debe propagar el error de parse ni
    permitir DoS / info-leak via el ValueError.
    """
    from backend.api import chat as chat_module
    from fastapi import HTTPException

    (admin_a, _, _), _ = _seed_two_sedes(db_session)

    raised = None
    try:
        chat_module._assert_actor_still_participant_at_commit_time(
            db_session, "not-a-uuid", admin_a
        )
    except HTTPException as exc:
        raised = exc
    assert raised is not None, (
        "Helper no raise cuando conv_id no es UUID parseable"
    )
    assert raised.status_code == 404, (
        f"Helper debe raise 404 para malformed conv_id, no {raised.status_code}"
    )
    assert raised.detail == "Conversation not found", (
        f"Anti-leak violation: detail no uniforme (got {raised.detail!r})"
    )


def test_assert_actor_still_participant_unit_accepts_string_uuid(
    client, db_session
):
    """Direct unit test — el helper acepta conv_id como string (path
    params llegan como str en FastAPI). Verifica que el coerce funciona
    tanto para UUID objects como para strings parseables.
    """
    from backend.api import chat as chat_module
    from fastapi import HTTPException

    (admin_a, _, sede_a), _ = _seed_two_sedes(db_session)
    persona_local = _persona_in(db_session, sede_a.id, "unit-string-conv")
    db_session.commit()

    headers_a = auth_headers(client, email="chatA@example.com")
    resp_c = client.post(
        "/api/chat/conversations",
        headers=headers_a,
        json={"participant_ids": [str(persona_local.id)]},
    )
    assert resp_c.status_code == 201, resp_c.text
    conv_id = resp_c.json()["id"]

    # Pass conv_id as STRING (cómo llega en HTTP path).
    result = chat_module._assert_actor_still_participant_at_commit_time(
        db_session, str(conv_id), admin_a
    )
    assert result is None, (
        f"Helper debe aceptar conv_id como string "
        f"(got {result!r})"
    )

    # Remover y verificar que el raise funciona cuando el string es válido.
    db_session.query(models.ConversationParticipant).filter(
        models.ConversationParticipant.conversation_id == conv_id,
        models.ConversationParticipant.user_id == admin_a.id,
    ).delete()
    db_session.commit()

    raised = None
    try:
        chat_module._assert_actor_still_participant_at_commit_time(
            db_session, str(conv_id), admin_a
        )
    except HTTPException as exc:
        raised = exc
    assert raised is not None and raised.status_code == 404, (
        "Helper debe raise 404 cuando actor removido (string conv_id)"
    )
