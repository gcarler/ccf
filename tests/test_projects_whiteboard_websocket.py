"""TDD suite: WebSocket de colaboración en tiempo real de la pizarra (PZ-05/PZ-13).

Cierra el gap donde el frontend conectaba a ``/api/v1/projects/{id}/whiteboard/ws``
(que no existía → 404) y la colaboración real-time nunca funcionaba en producción.

Contratos cubiertos:

1. Handshake sin token o con token inválido → close 4001.
2. Usuario inactivo → close 4003.
3. Usuario sin acceso de lectura al proyecto (ni rol ni asignación) → 4003.
4. Proyecto cross-sede (Axioma 3) → 4004 (indistinguible de no-existente).
5. Usuario autorizado conecta; un mensaje ``cursor`` se broadcast a TODOS los
   clientes de la room ``wb_{project_id}`` con ``sender_id`` = clientId del
   emisor (para que el emisor filtre su propio eco).
6. Los mensajes ``object_modified``/``object_added``/``object_removed`` se
   replican entre clientes de la misma pizarra con ``sender_id``.
"""

from __future__ import annotations

import asyncio
import uuid as _uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend.api.projects import manager
from backend.app import app
from backend.core.permissions import create_access_token
from tests.conftest import TestingSessionLocal, seed_admin, seed_user_with_role
from tests.factories_projects import create_project_factory


def _ws_client() -> TestClient:
    """Use Starlette's real WebSocket-capable client for handshake tests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_websocket_manager():
    """Prevent global listener/Redis state from leaking between event loops."""

    def reset_manager() -> None:
        manager.active_connections.clear()
        manager.rooms.clear()
        listener_task = manager.listener_task
        if listener_task and not listener_task.done():
            listener_task.cancel()
        manager.listener_task = None
        # Each Starlette TestClient uses its own event loop. Recreate the
        # lock so the next test cannot await a lock bound to a closed loop.
        manager.listener_lock = asyncio.Lock()
        # MemoryPubSub has no network connection to close; discard its queues
        # so cancelled listeners cannot receive broadcasts from later tests.
        redis_client = manager._redis
        channels = getattr(redis_client, "_pubsub_channels", None)
        if channels is not None:
            channels.clear()

    reset_manager()
    yield
    reset_manager()
    assert not manager.active_connections
    assert not manager.rooms


def _ws_url(project_id, token, client_id=None) -> str:
    base = f"/api/projects/{project_id}/whiteboard/ws?token={token}"
    if client_id:
        base += f"&clientId={client_id}"
    return base


@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ("", 4001),
        ("?token=not-a-jwt", 4001),
    ],
)
def test_whiteboard_ws_rejects_missing_or_invalid_token(query, expected_code):
    fake_project = _uuid.uuid4()
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with _ws_client().websocket_connect(f"/api/projects/{fake_project}/whiteboard/ws{query}"):
            pass
    assert exc_info.value.code == expected_code


def test_whiteboard_ws_rejects_inactive_user(db_session):
    user, _, _ = seed_admin(db_session, email="wb-inactive@example.com")
    user.is_active = False
    db_session.commit()
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(_ws_url(project.id, token)):
                pass
    assert exc_info.value.code == 4003


def test_whiteboard_ws_rejects_user_without_read_access(db_session):
    user, _, _ = seed_user_with_role(
        db_session,
        role_name="wb-noaccess",
        email="wb-noaccess@example.com",
        permisos={"default": "allow"},
    )
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(_ws_url(project.id, token)):
                pass
    assert exc_info.value.code == 4003


def test_whiteboard_ws_rejects_cross_sede_project(db_session):
    user_a, _, sede_a = seed_admin(db_session, email="wb-sede-a@example.com")
    seed_admin(db_session, email="wb-sede-b@example.com")
    token = create_access_token({"sub": str(user_a.id)})
    # Project forced into a DIFFERENT sede than user_a (Axioma 3).
    foreign_sede = db_session.query(type(sede_a)).filter(type(sede_a).id != sede_a.id).first()
    assert foreign_sede is not None, "Second sede from seed_admin should exist"
    project = create_project_factory(db_session, sede_id=foreign_sede.id)

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(_ws_url(project.id, token)):
                pass
    assert exc_info.value.code == 4004


def test_whiteboard_ws_accepts_authorized_user_and_broadcasts_cursor_to_room(db_session):
    user, _, _ = seed_admin(db_session, email="wb-ok@example.com")
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)
    client_a = str(_uuid.uuid4())
    client_b = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project.id, token, client_a)) as ws_a:
            with _ws_client().websocket_connect(_ws_url(project.id, token, client_b)) as ws_b:
                ws_a.send_json({"type": "join", "name": "Alice", "clientId": client_a})
                ws_b.send_json({"type": "join", "name": "Bob", "clientId": client_b})

                ws_a.send_json({"type": "cursor", "x": 120, "y": 80, "name": "Alice"})

                # Both clients in the room receive the cursor with sender_id.
                received_a = ws_a.receive_json()
                received_b = ws_b.receive_json()
                for received in (received_a, received_b):
                    assert received["type"] == "cursor"
                    assert received["x"] == 120
                    assert received["y"] == 80
                    assert received["sender_id"] == client_a


def test_whiteboard_ws_replicates_object_updates_to_peers(db_session):
    user, _, _ = seed_admin(db_session, email="wb-obj@example.com")
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)
    client_a = str(_uuid.uuid4())
    client_b = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project.id, token, client_a)) as ws_a:
            with _ws_client().websocket_connect(_ws_url(project.id, token, client_b)) as ws_b:
                ws_a.send_json({"type": "join", "name": "Alice", "clientId": client_a})
                ws_b.send_json({"type": "join", "name": "Bob", "clientId": client_b})

                obj_data = {"id": "rect-1", "type": "rect", "left": 10, "top": 20}
                ws_a.send_json({"type": "object_added", "objData": obj_data})

                msg_a = ws_a.receive_json()
                msg_b = ws_b.receive_json()
                for msg in (msg_a, msg_b):
                    assert msg["type"] == "object_added"
                    assert msg["objData"]["id"] == "rect-1"
                    assert msg["sender_id"] == client_a

                ws_b.send_json({"type": "object_modified", "objData": {**obj_data, "left": 99}})
                msg_a2 = ws_a.receive_json()
                msg_b2 = ws_b.receive_json()
                for msg in (msg_a2, msg_b2):
                    assert msg["type"] == "object_modified"
                    assert msg["objData"]["left"] == 99
                    assert msg["sender_id"] == client_b

                ws_a.send_json({"type": "object_removed", "objId": "rect-1"})
                msg_a3 = ws_a.receive_json()
                msg_b3 = ws_b.receive_json()
                for msg in (msg_a3, msg_b3):
                    assert msg["type"] == "object_removed"
                    assert msg["objId"] == "rect-1"
                    assert msg["sender_id"] == client_a


def test_whiteboard_ws_ignores_unknown_message_types(db_session):
    user, _, _ = seed_admin(db_session, email="wb-unknown@example.com")
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)
    client_id = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project.id, token, client_id)) as ws:
            ws.send_text("not-json")
            ws.send_json({"type": "something_else", "payload": 1})
            ws.send_json({"type": "join", "name": "Alice", "clientId": client_id})
            # No broadcast should happen for unknown/garbage messages; the
            # connection stays open and receives nothing until a real message.
            ws.send_json({"type": "cursor", "x": 1, "y": 2, "name": "Alice"})
            received = ws.receive_json()
            assert received["type"] == "cursor"
            assert received["sender_id"] == client_id


def test_whiteboard_ws_join_updates_sender_id_from_query(db_session):
    """clientId passed as query param is used as sender_id even without join body."""
    user, _, _ = seed_admin(db_session, email="wb-qparam@example.com")
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)
    client_id = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project.id, token, client_id)) as ws:
            ws.send_json({"type": "cursor", "x": 5, "y": 6, "name": "Alice"})
            received = ws.receive_json()
            assert received["sender_id"] == client_id


def test_whiteboard_ws_rejects_malformed_project_id(db_session):
    """project_id no-UUID responde 4004 (sin DataError de Postgres no manejado)."""
    user, _, _ = seed_admin(db_session, email="wb-malformed@example.com")
    token = create_access_token({"sub": str(user.id)})

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with _ws_client().websocket_connect(
                f"/api/projects/not-a-uuid/whiteboard/ws?token={token}"
            ):
                pass
    assert exc_info.value.code == 4004


def test_whiteboard_ws_rooms_are_isolated_per_project(db_session):
    """Las rooms wb_{project_uuid} no cruzan broadcasts entre proyectos."""
    user, _, _ = seed_admin(db_session, email="wb-isolation@example.com")
    token = create_access_token({"sub": str(user.id)})
    project_1 = create_project_factory(db_session)
    project_2 = create_project_factory(db_session)
    client_1 = str(_uuid.uuid4())
    client_2 = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project_1.id, token, client_1)) as ws_1:
            with _ws_client().websocket_connect(_ws_url(project_2.id, token, client_2)) as ws_2:
                ws_1.send_json({"type": "cursor", "x": 1, "y": 2, "name": "Alice"})
                received_1 = ws_1.receive_json()
                assert received_1["type"] == "cursor"
                assert received_1["sender_id"] == client_1

                ws_1.send_json(
                    {"type": "object_added", "objData": {"id": "rect-iso", "type": "rect"}}
                )
                received_1b = ws_1.receive_json()
                assert received_1b["type"] == "object_added"
                assert received_1b["objData"]["id"] == "rect-iso"

                # Si hubiera cruce de rooms, ws_2 recibiría el broadcast del
                # proyecto_1 ANTES que su propio cursor. El assert final lo
                # detecta: lo que recibe ws_2 debe ser SOLO su propio cursor.
                ws_2.send_json({"type": "cursor", "x": 9, "y": 9, "name": "Bob"})
                received_2 = ws_2.receive_json()
                assert received_2["type"] == "cursor"
                assert received_2["sender_id"] == client_2
                assert received_2.get("objData") is None


def test_whiteboard_ws_join_body_cannot_spoof_sender_id(db_session):
    """El clientId del body del join NO puede suplantar al del query param."""
    user, _, _ = seed_admin(db_session, email="wb-spoof@example.com")
    token = create_access_token({"sub": str(user.id)})
    project = create_project_factory(db_session)
    client_id = str(_uuid.uuid4())

    with patch("backend.core.database.SessionLocal", side_effect=TestingSessionLocal):
        with _ws_client().websocket_connect(_ws_url(project.id, token, client_id)) as ws:
            # Intento de suplantación: join con un clientId ajeno.
            ws.send_json({"type": "join", "name": "Alice", "clientId": "attacker-controlled"})
            ws.send_json({"type": "cursor", "x": 1, "y": 2, "name": "Alice"})
            received = ws.receive_json()
            assert received["type"] == "cursor"
            assert received["sender_id"] == client_id
            assert received["sender_id"] != "attacker-controlled"
