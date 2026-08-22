"""FastMCP 2.0 Unified Gateway Router for CCF Platform.

Provides unified endpoint routing, dynamic tool discovery, zero-trust context propagation,
mcp:execute RBAC permission verification, and audit telemetry logging into tool_execution_logs.
"""

from __future__ import annotations

import inspect
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend import models
from backend.core.database import get_db
from backend.core.permissions import get_current_active_user, oauth2_scheme
from backend.mcp_auth import (
    _effective_user_scopes,
    has_mcp_execute_permission,
    set_mcp_auth_context,
)
from backend.models_agents import ToolExecutionLog

logger = logging.getLogger("CCF-FastMCP-Gateway")

router = APIRouter(prefix="/mcp", tags=["FastMCP Gateway"])


def _load_domain_servers() -> Dict[str, Any]:
    """Carga y mapea los 6 servidores FastMCP canónicos de dominio CCF."""
    from backend.mcp_academy import academy_mcp
    from backend.mcp_agenda import agenda_mcp
    from backend.mcp_cms import cms_mcp
    from backend.mcp_crm import crm_mcp
    from backend.mcp_evangelism import mass_event_mcp
    from backend.mcp_governance import mcp_app as governance_mcp

    return {
        "crm": crm_mcp,
        "cms": cms_mcp,
        "academy": academy_mcp,
        "agenda": agenda_mcp,
        "calendar": agenda_mcp,
        "evangelism": mass_event_mcp,
        "governance": governance_mcp,
    }


CANONICAL_SERVERS = ["crm", "cms", "academy", "agenda", "evangelism", "governance"]


def get_mcp_server(server_name: str):
    servers = _load_domain_servers()
    name = server_name.strip().lower()
    if name not in servers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MCP server '{server_name}' not found. Available: {CANONICAL_SERVERS}",
        )
    return servers[name]


def _format_tool(t: Any) -> Dict[str, Any]:
    name = getattr(t, "name", str(t))
    desc = getattr(t, "description", "") or ""
    params = getattr(t, "parameters", {}) or {}
    return {
        "name": name,
        "description": desc,
        "parameters": params,
    }


def _resolve_tool_in_server(server: Any, tool_name: str) -> Any:
    tools_dict = getattr(getattr(server, "_tool_manager", None), "_tools", {})
    if tool_name in tools_dict:
        return tools_dict[tool_name]
    for key, val in tools_dict.items():
        if key.lower() == tool_name.lower():
            return val
    return None


def _find_tool_across_all_servers(tool_name: str) -> tuple[Optional[str], Optional[Any]]:
    servers = _load_domain_servers()
    for s_name, s_obj in servers.items():
        t = _resolve_tool_in_server(s_obj, tool_name)
        if t is not None:
            return s_name, t
    return None, None


class McpToolCallRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre de la herramienta FastMCP")
    tool_name: Optional[str] = Field(None, description="Alias para el nombre de la herramienta")
    tool: Optional[str] = Field(None, description="Alias para el nombre de la herramienta")
    arguments: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Argumentos de la herramienta")
    args: Optional[Dict[str, Any]] = Field(None, description="Alias para argumentos")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Alias para argumentos")


def _record_tool_telemetry(
    db: Session,
    sede_id: Optional[UUID],
    persona_id: Optional[UUID],
    tool_name: str,
    request_id: str,
    arguments: Dict[str, Any],
    result_summary: Optional[str],
    execution_time_ms: int,
    tokens_used: int = 0,
    status_str: str = "success",
) -> None:
    """Persiste log de telemetría y trazabilidad en tool_execution_logs."""
    try:
        clean_args = arguments.copy() if isinstance(arguments, dict) else {}
        log_entry = ToolExecutionLog(
            id=uuid.uuid4(),
            sede_id=sede_id,
            persona_id=persona_id,
            tool_name=tool_name,
            request_id=request_id,
            arguments=clean_args,
            result_summary=result_summary[:1000] if result_summary else None,
            tokens_used=tokens_used,
            execution_time_ms=execution_time_ms,
            status=status_str,
        )
        db.add(log_entry)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to persist ToolExecutionLog: %s", exc)
        db.rollback()


# ──────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────


@router.get("/servers")
def list_servers():
    """Lista todos los servidores MCP de dominio registrados en la plataforma."""
    return {
        "servers": CANONICAL_SERVERS,
        "count": len(CANONICAL_SERVERS),
        "gateway_version": "2.0.0-PRO",
    }


@router.get("/tools")
def list_all_domain_tools(
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user),
):
    """Descubre dinámicamente todas las herramientas FastMCP registradas en todos los servidores."""
    if not has_mcp_execute_permission(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere: mcp:execute",
        )

    servers = _load_domain_servers()
    all_tools: List[Dict[str, Any]] = []
    seen_names = set()

    for s_name in CANONICAL_SERVERS:
        s_obj = servers.get(s_name)
        if not s_obj:
            continue
        tools_dict = getattr(getattr(s_obj, "_tool_manager", None), "_tools", {})
        for t in tools_dict.values():
            t_data = _format_tool(t)
            if t_data["name"] not in seen_names:
                seen_names.add(t_data["name"])
                t_data["server"] = s_name
                all_tools.append(t_data)

    return {
        "count": len(all_tools),
        "tools": all_tools,
    }


@router.get("/{server_name}/tools/list")
@router.get("/{server_name}/tools")
def list_server_tools(
    server_name: str,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user),
):
    """Lista todas las herramientas provistas por un servidor MCP específico."""
    if not has_mcp_execute_permission(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere: mcp:execute",
        )

    server = get_mcp_server(server_name)
    tools_dict = getattr(getattr(server, "_tool_manager", None), "_tools", {})
    tools = [_format_tool(t) for t in tools_dict.values()]

    return {
        "server": server_name.lower(),
        "count": len(tools),
        "tools": tools,
    }


@router.post("/{server_name}/tools/call")
async def call_server_tool(
    server_name: str,
    payload: McpToolCallRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user),
    raw_token: str = Depends(oauth2_scheme),
    x_sede_id: Optional[str] = Header(None, alias="X-Sede-ID"),
    x_persona_id: Optional[str] = Header(None, alias="X-Persona-ID"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    """Ejecuta una herramienta FastMCP con propagación de contexto Zero-Trust y auditoría."""
    # 1. Zero-Trust Permission Check: mcp:execute
    if not has_mcp_execute_permission(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permisos insuficientes. Se requiere: mcp:execute",
        )

    # 2. Server lookup
    server = get_mcp_server(server_name)

    # 3. Tool lookup
    target_tool_name = payload.name or payload.tool_name or payload.tool
    if not target_tool_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere el nombre de la herramienta ('name' o 'tool_name')",
        )

    tool_obj = _resolve_tool_in_server(server, target_tool_name)
    if tool_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{target_tool_name}' not found in MCP server '{server_name}'",
        )

    args = payload.arguments if payload.arguments is not None else (payload.args if payload.args is not None else (payload.parameters or {}))

    # 4. Context propagation
    req_id = x_request_id or str(uuid.uuid4())
    effective_sede_id = None
    if x_sede_id:
        try:
            effective_sede_id = UUID(x_sede_id)
        except Exception:
            effective_sede_id = getattr(current_user, "sede_id", None)
    else:
        effective_sede_id = getattr(current_user, "sede_id", None)

    effective_persona_id = None
    if x_persona_id:
        try:
            effective_persona_id = UUID(x_persona_id)
        except Exception:
            effective_persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)
    else:
        effective_persona_id = getattr(current_user, "persona_id", None) or getattr(current_user, "id", None)

    scopes = list(_effective_user_scopes(db, current_user))
    claims = {
        "sub": str(current_user.id),
        "sede_id": str(effective_sede_id) if effective_sede_id else None,
        "persona_id": str(effective_persona_id) if effective_persona_id else None,
    }
    set_mcp_auth_context(raw_token, current_user.id, scopes=scopes, claims=claims)

    # 5. Tool execution & timing
    tool_fn = getattr(tool_obj, "fn", tool_obj)
    start_time = time.perf_counter()
    status_str = "success"
    result_val = None
    error_detail = None

    try:
        if inspect.iscoroutinefunction(tool_fn):
            result_val = await tool_fn(**args)
        else:
            result_val = tool_fn(**args)
    except PermissionError as p_err:
        status_str = "forbidden"
        error_detail = str(p_err)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        _record_tool_telemetry(
            db,
            sede_id=effective_sede_id,
            persona_id=effective_persona_id,
            tool_name=target_tool_name,
            request_id=req_id,
            arguments=args,
            result_summary=f"PermissionError: {error_detail}",
            execution_time_ms=latency_ms,
            status_str=status_str,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_detail)
    except ValueError as v_err:
        status_str = "error"
        error_detail = str(v_err)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        _record_tool_telemetry(
            db,
            sede_id=effective_sede_id,
            persona_id=effective_persona_id,
            tool_name=target_tool_name,
            request_id=req_id,
            arguments=args,
            result_summary=f"ValueError: {error_detail}",
            execution_time_ms=latency_ms,
            status_str=status_str,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_detail)
    except Exception as exc:
        status_str = "error"
        error_detail = str(exc)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        _record_tool_telemetry(
            db,
            sede_id=effective_sede_id,
            persona_id=effective_persona_id,
            tool_name=target_tool_name,
            request_id=req_id,
            arguments=args,
            result_summary=f"Exception: {error_detail}",
            execution_time_ms=latency_ms,
            status_str=status_str,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Tool error: {error_detail}")

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # 6. Telemetry persistence
    summary_str = json.dumps(result_val, ensure_ascii=False) if isinstance(result_val, (dict, list)) else str(result_val)
    _record_tool_telemetry(
        db,
        sede_id=effective_sede_id,
        persona_id=effective_persona_id,
        tool_name=target_tool_name,
        request_id=req_id,
        arguments=args,
        result_summary=summary_str,
        execution_time_ms=latency_ms,
        tokens_used=0,
        status_str=status_str,
    )

    return {
        "success": True,
        "server": server_name.lower(),
        "tool": target_tool_name,
        "result": result_val,
        "latency_ms": latency_ms,
        "request_id": req_id,
    }


@router.post("/tools/call")
async def call_any_tool(
    payload: McpToolCallRequest,
    db: Session = Depends(get_db),
    current_user: models.Usuario = Depends(get_current_active_user),
    raw_token: str = Depends(oauth2_scheme),
    x_sede_id: Optional[str] = Header(None, alias="X-Sede-ID"),
    x_persona_id: Optional[str] = Header(None, alias="X-Persona-ID"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
):
    """Llamado universal: resuelve automáticamente el servidor de dominio adecuado a partir del tool name."""
    target_tool_name = payload.name or payload.tool_name or payload.tool
    if not target_tool_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se requiere el nombre de la herramienta ('name' o 'tool_name')",
        )

    server_name, _tool_obj = _find_tool_across_all_servers(target_tool_name)
    if not server_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Herramienta '{target_tool_name}' no encontrada en ningún servidor MCP registrado",
        )

    return await call_server_tool(
        server_name=server_name,
        payload=payload,
        db=db,
        current_user=current_user,
        raw_token=raw_token,
        x_sede_id=x_sede_id,
        x_persona_id=x_persona_id,
        x_request_id=x_request_id,
    )
