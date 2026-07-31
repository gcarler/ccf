"""CMS v2 Presence Real-Time Collaboration Module (Fase 4 / M2).

Provides WebSocket and REST endpoints for tracking real-time presence of users
editing pages in the CMS Page Builder.
"""
from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
from typing import Dict, List, Set, Tuple

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from backend.core.permissions import ALGORITHM, SECRET_KEY

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cms_v2_presence"])

# Predefined palette for deterministic user colors
DEFAULT_PALETTE = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#EF4444",  # Red
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#6366F1",  # Indigo
    "#84CC16",  # Lime
    "#D97706",  # Orange
]


def _compute_initials(name: str) -> str:
    """Computes 1-2 character uppercase initials from user name."""
    if not name:
        return "U"
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


def _compute_color(user_id: str) -> str:
    """Computes a deterministic hex color based on user_id hash."""
    if not user_id:
        return DEFAULT_PALETTE[0]
    hash_val = sum(ord(c) for c in str(user_id))
    return DEFAULT_PALETTE[hash_val % len(DEFAULT_PALETTE)]


def _parse_user_from_token(token: str | None) -> dict:
    """Decodes JWT, JSON payload, or fallback plain token string to user presence dict.

    Returns a dict containing:
      {
        "user_id": str,
        "id": str,
        "name": str,
        "avatar_initials": str,
        "initials": str,
        "color": str,
      }
    """
    if not token:
        user_id = "anon-user"
        return {
            "user_id": user_id,
            "id": user_id,
            "name": "Usuario Anónimo",
            "avatar_initials": "UA",
            "initials": "UA",
            "color": DEFAULT_PALETTE[0],
        }

    # 1. Attempt JWT decoding
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = str(payload.get("sub") or payload.get("user_id") or payload.get("id") or "user")
        name = str(payload.get("name") or payload.get("full_name") or payload.get("email") or f"Usuario {user_id[:6]}")
        initials = str(payload.get("avatar_initials") or payload.get("initials") or _compute_initials(name))
        color = str(payload.get("color") or _compute_color(user_id))
        return {
            "user_id": user_id,
            "id": user_id,
            "name": name,
            "avatar_initials": initials,
            "initials": initials,
            "color": color,
        }
    except (JWTError, Exception):
        pass

    # 2. Attempt JSON decoding (direct or URL encoded)
    try:
        decoded_str = urllib.parse.unquote(token)
        data = json.loads(decoded_str)
        if isinstance(data, dict):
            user_id = str(data.get("user_id") or data.get("id") or "user")
            name = str(data.get("name") or data.get("full_name") or f"Usuario {user_id[:6]}")
            initials = str(data.get("avatar_initials") or data.get("initials") or _compute_initials(name))
            color = str(data.get("color") or _compute_color(user_id))
            return {
                "user_id": user_id,
                "id": user_id,
                "name": name,
                "avatar_initials": initials,
                "initials": initials,
                "color": color,
            }
    except Exception:
        pass

    # 3. Plain text string fallback (e.g. user ID or plain token)
    user_id = str(token)
    name = f"Usuario {user_id[:6]}"
    initials = _compute_initials(name)
    color = _compute_color(user_id)
    return {
        "user_id": user_id,
        "id": user_id,
        "name": name,
        "avatar_initials": initials,
        "initials": initials,
        "color": color,
    }


class PresenceManager:
    """In-memory active WebSocket connection manager keyed by (site_key, slug)."""

    def __init__(self):
        # Maps (site_key, slug) tuple to dict of { WebSocket: user_payload_dict }
        self.rooms: Dict[Tuple[str, str], Dict[WebSocket, dict]] = {}

    async def connect(self, websocket: WebSocket, site_key: str, slug: str, user: dict):
        """Accepts connection, stores user, and broadcasts active presence."""
        await websocket.accept()
        key = (site_key, slug)
        if key not in self.rooms:
            self.rooms[key] = {}
        self.rooms[key][websocket] = user
        logger.info(f"Presence connect: user={user['user_id']} site={site_key} slug={slug}")
        await self.broadcast_presence(site_key, slug)

    async def disconnect(self, websocket: WebSocket, site_key: str, slug: str):
        """Removes websocket connection and broadcasts updated presence list."""
        key = (site_key, slug)
        if key in self.rooms:
            user = self.rooms[key].pop(websocket, None)
            if user:
                logger.info(f"Presence disconnect: user={user['user_id']} site={site_key} slug={slug}")
            if not self.rooms[key]:
                del self.rooms[key]
        await self.broadcast_presence(site_key, slug)

    def get_presence_users(self, site_key: str, slug: str) -> List[dict]:
        """Returns unique list of present users for specified page."""
        key = (site_key, slug)
        if key not in self.rooms:
            return []

        seen_ids: Set[str] = set()
        unique_users: List[dict] = []

        for user in self.rooms[key].values():
            uid = user.get("user_id") or user.get("id")
            if uid and uid not in seen_ids:
                seen_ids.add(uid)
                unique_users.append(user)

        return unique_users

    async def broadcast_presence(self, site_key: str, slug: str):
        """Broadcasts current presence list to all connected clients for a page."""
        key = (site_key, slug)
        if key not in self.rooms:
            return

        users = self.get_presence_users(site_key, slug)
        payload = {
            "type": "presence_update",
            "presence_users": users,
        }
        message_text = json.dumps(payload)

        stale_sockets: List[WebSocket] = []
        for ws in list(self.rooms[key].keys()):
            try:
                await ws.send_text(message_text)
            except Exception as err:
                logger.warning(f"Failed to send presence update: {err}")
                stale_sockets.append(ws)

        for ws in stale_sockets:
            if ws in self.rooms.get(key, {}):
                del self.rooms[key][ws]


# Global presence manager instance
presence_manager = PresenceManager()


@router.websocket("/ws/presence/{site_key}/{slug}")
async def websocket_presence(
    websocket: WebSocket,
    site_key: str,
    slug: str,
    token: str = Query(default=None),
):
    """WebSocket endpoint for page presence collaboration."""
    user = _parse_user_from_token(token)
    await presence_manager.connect(websocket, site_key, slug, user)
    try:
        while True:
            # Keep connection open and handle incoming ping/messages
            data = await websocket.receive_text()
            # If client sends a ping or custom message, echo/process if needed
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        await presence_manager.disconnect(websocket, site_key, slug)
    except Exception as exc:
        logger.error(f"Error in presence WS loop: {exc}")
        await presence_manager.disconnect(websocket, site_key, slug)


@router.get("/sites/{site_key}/pages/{slug}/presence")
def get_page_presence(site_key: str, slug: str):
    """REST endpoint returning current presence users for specified page."""
    users = presence_manager.get_presence_users(site_key, slug)
    return {"presence_users": users}
