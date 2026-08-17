"""Embedded Streamable HTTP MCP server for the CCF CMS."""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware

from backend.api.mcp.auth import _authenticate_request
from backend.core.database import SessionLocal

from .cms_tools import register_cms_tools

mcp = FastMCP(
    name="CCF CMS",
    instructions=(
        "Herramientas oficiales del CMS CCF. Respeta siempre RBAC, sede_id y el workflow draft/preview/publish. "
        "Las herramientas de escritura requieren autorización del usuario y las operaciones destructivas deben "
        "ser confirmadas por el cliente MCP."
    ),
    streamable_http_path="/",
    stateless_http=True,
    json_response=True,
)
register_cms_tools(mcp)

mcp_app = mcp.streamable_http_app()


class CCFMCPAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        db = SessionLocal()
        try:
            try:
                await _authenticate_request(request, db)
            except HTTPException as exc:
                return JSONResponse(
                    {"detail": exc.detail},
                    status_code=exc.status_code,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)
        finally:
            db.close()


mcp_app.add_middleware(CCFMCPAuthenticationMiddleware)

__all__ = ["mcp", "mcp_app"]
