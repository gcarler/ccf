"""Agent Orchestrator — Motor multiagente con FastMCP 2.0 tool calling, telemetría y memoria.

Optimus Brain: motor de diagnóstico y asistencia con LLM.
Soporta:
- Dynamic FastMCP Tool discovery & execution across all 6 domain servers (crm, cms, academy, agenda, evangelism, governance)
- Zero-trust context propagation (actor_persona_id, sede_id, mcp:execute check)
- Telemetry audit logging to tool_execution_logs
- Conversational memory & multi-turn tool calling
- Structured insight generation
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Optional dependency
try:  # pragma: no cover
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.core.database import SessionLocal
from backend.mcp_auth import has_mcp_execute_permission, set_mcp_auth_context
from backend.models_agents import ToolExecutionLog

SYSTEM_PROMPT = (
    "You are Optimus Brain, the Neural MESH engine for CCF.\n"
    "Your goal is to assist users with ministerial management,\n"
    "data analysis, and theological foundations.\n"
    "Always be professional, concise, and helpful.\n"
    "If context from the Knowledge Base is provided, use it.\n"
    "If you don't know something, offer to notify a pastor.\n\n"
    "You have access to tools that can search the church database,\n"
    "get statistics, and retrieve information. Use them for answers."
)


def get_registered_domain_mcp_servers() -> Dict[str, Any]:
    """Carga los servidores FastMCP de dominio registrados en CCF."""
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


class AgentOrchestrator:
    """Orquestador multiagente con soporte para FastMCP 2.0 y ToolRegistry."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")

        key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("API key not configured. Set OPENROUTER_API_KEY or OPENAI_API_KEY.")

        is_openrouter = key.startswith("sk-or-")
        base_url = "https://openrouter.ai/api/v1" if is_openrouter else None

        self.client = OpenAI(base_url=base_url, api_key=key)
        self.default_model = default_model or ("moonshotai/kimi-k2.6" if is_openrouter else "gpt-4o-mini")

    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Descubre dinámicamente las herramientas de todos los servidores FastMCP registrados."""
        servers = get_registered_domain_mcp_servers()
        openai_tools: List[Dict[str, Any]] = []
        seen_names = set()

        for server_name, server in servers.items():
            tools_dict = getattr(getattr(server, "_tool_manager", None), "_tools", {})
            for name, tool in tools_dict.items():
                tool_name = getattr(tool, "name", name)
                if tool_name in seen_names:
                    continue
                seen_names.add(tool_name)

                params = getattr(tool, "parameters", {}) or {"type": "object", "properties": {}}
                desc = getattr(tool, "description", "") or f"Herramienta FastMCP del módulo {server_name}"
                openai_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": desc,
                            "parameters": params,
                        },
                    }
                )
        return openai_tools

    def get_tools(self) -> List[Dict[str, Any]]:
        """Obtiene el catálogo unificado de herramientas (FastMCP + ToolRegistry)."""
        tools = self.get_mcp_tools()
        seen = {t["function"]["name"] for t in tools}

        try:
            from backend.services.tool_registry import tool_registry

            legacy_tools = tool_registry.get_openai_tools()
            for lt in legacy_tools:
                if lt.get("function", {}).get("name") not in seen:
                    tools.append(lt)
                    seen.add(lt["function"]["name"])
        except Exception as exc:
            logger.debug("Failed to load legacy tool_registry: %s", exc)

        return tools

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        user: Optional[models.Usuario] = None,
        sede_id: Optional[UUID] = None,
        persona_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        raw_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ejecuta una herramienta (FastMCP o ToolRegistry) con Zero-Trust y registro de telemetría."""
        req_id = request_id or str(uuid.uuid4())
        start_time = time.perf_counter()
        status_str = "success"
        result: Any = None
        error_detail: Optional[str] = None

        # 1. Look up across FastMCP domain servers
        servers = get_registered_domain_mcp_servers()
        target_tool = None

        for _s_name, server in servers.items():
            tools_dict = getattr(getattr(server, "_tool_manager", None), "_tools", {})
            if tool_name in tools_dict:
                target_tool = tools_dict[tool_name]
                break

        db = SessionLocal()
        try:
            # Check user and permissions if user provided
            if user is not None:
                if not has_mcp_execute_permission(db, user):
                    status_str = "forbidden"
                    error_detail = "Permisos insuficientes. Se requiere: mcp:execute"
                    latency_ms = int((time.perf_counter() - start_time) * 1000)
                    self._log_telemetry(
                        db,
                        sede_id=sede_id or getattr(user, "sede_id", None),
                        persona_id=persona_id or getattr(user, "persona_id", None) or getattr(user, "id", None),
                        tool_name=tool_name,
                        request_id=req_id,
                        arguments=arguments,
                        result_summary=error_detail,
                        execution_time_ms=latency_ms,
                        status_str=status_str,
                    )
                    return {"error": error_detail, "status": 403}

                # Propagate zero-trust auth context
                token_to_use = raw_token or f"orchestrator-internal-{user.id}"
                set_mcp_auth_context(token_to_use, user.id)

            if target_tool is not None:
                # Execute FastMCP tool
                tool_fn = getattr(target_tool, "fn", target_tool)
                try:
                    if inspect.iscoroutinefunction(tool_fn):
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                result = loop.run_until_complete(tool_fn(**arguments))
                            else:
                                result = asyncio.run(tool_fn(**arguments))
                        except RuntimeError:
                            result = asyncio.run(tool_fn(**arguments))
                    else:
                        result = tool_fn(**arguments)
                except PermissionError as p_err:
                    status_str = "forbidden"
                    error_detail = str(p_err)
                    result = {"error": str(p_err)}
                except Exception as exc:
                    status_str = "error"
                    error_detail = str(exc)
                    result = {"error": str(exc)}
            else:
                # Fallback to ToolRegistry
                from backend.services.tool_registry import tool_registry

                try:
                    res = tool_registry.execute(tool_name, **arguments)
                    result = res
                    if isinstance(res, dict) and not res.get("success", True):
                        status_str = "error"
                        error_detail = res.get("error", "Tool execution failed")
                except Exception as exc:
                    status_str = "error"
                    error_detail = str(exc)
                    result = {"error": str(exc)}

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Persist Telemetry Log
            effective_sede = sede_id or (getattr(user, "sede_id", None) if user else None)
            effective_persona = persona_id or (getattr(user, "persona_id", None) or getattr(user, "id", None) if user else None)
            summary_str = json.dumps(result, ensure_ascii=False) if isinstance(result, (dict, list)) else str(result)

            self._log_telemetry(
                db,
                sede_id=effective_sede,
                persona_id=effective_persona,
                tool_name=tool_name,
                request_id=req_id,
                arguments=arguments,
                result_summary=error_detail or summary_str,
                execution_time_ms=latency_ms,
                status_str=status_str,
            )
            return result
        finally:
            db.close()

    def _log_telemetry(
        self,
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
    ):
        """Helper para guardar registros de auditoría de herramientas."""
        try:
            log_entry = ToolExecutionLog(
                id=uuid.uuid4(),
                sede_id=sede_id,
                persona_id=persona_id,
                tool_name=tool_name,
                request_id=request_id,
                arguments=arguments or {},
                result_summary=result_summary[:1000] if result_summary else None,
                tokens_used=tokens_used,
                execution_time_ms=execution_time_ms,
                status=status_str,
            )
            db.add(log_entry)
            db.commit()
        except Exception as exc:
            logger.warning("AgentOrchestrator telemetry persistence failed: %s", exc)
            db.rollback()

    def run_diagnosis(
        self,
        summary: str,
        metrics: Dict[str, Any],
        conversation_id: Optional[UUID] = None,
        use_tools: bool = True,
        user: Optional[models.Usuario] = None,
    ) -> schemas.AgentInsightCreate:
        """Ejecuta diagnóstico con soporte completo de FastMCP 2.0 tool calling."""
        if OpenAI is None:
            raise RuntimeError("openai package not installed")

        messages = self._build_messages(summary, metrics, conversation_id)
        tools = self.get_tools() if use_tools else []

        max_iterations = 5
        iteration = 0
        total_tokens = 0
        tool_results = []
        content = ""

        sede_id = metrics.get("sede_id")
        persona_id = metrics.get("persona_id")
        req_id = metrics.get("request_id") or str(uuid.uuid4())

        while iteration < max_iterations:
            iteration += 1
            try:
                response = self.client.chat.completions.create(
                    model=self.default_model,
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.7,
                    max_tokens=2048,
                )
                if hasattr(response, "usage") and response.usage:
                    total_tokens += getattr(response.usage, "total_tokens", 0)
            except Exception as e:
                logger.error(f"Error calling LLM provider: {e}")
                content = f"Lo siento, ocurrió un problema al conectar con el servicio de IA ({str(e)}). Por favor intenta de nuevo."
                break

            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                messages.append(message)
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else (tc.function.arguments or {})
                    except Exception:
                        tool_args = {}

                    result = self.execute_tool(
                        tool_name=tool_name,
                        arguments=tool_args,
                        user=user,
                        sede_id=sede_id,
                        persona_id=persona_id,
                        request_id=req_id,
                    )

                    tool_results.append(
                        {
                            "tool": tool_name,
                            "args": tool_args,
                            "result": result,
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result,
                        }
                    )
            else:
                content = message.content or ""
                break

        # Save conversation turn
        if conversation_id:
            self._save_conversation_turn(conversation_id, "user", summary)
            self._save_conversation_turn(conversation_id, "assistant", content or "", tools_used=tool_results)

        return schemas.AgentInsightCreate(
            title="Respuesta de Optimus",
            insight_type="assistant_response",
            payload=content,
            metadata={
                "tools_used": len(tool_results),
                "tool_details": tool_results,
                "model": self.default_model,
                "tokens": total_tokens,
            },
        )

    def _build_messages(
        self,
        summary: str,
        metrics: Dict[str, Any],
        conversation_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if conversation_id:
            history = self._get_conversation_history(conversation_id)
            messages.extend(history)

        full_context = metrics.get("full_query", summary)
        kb_context = metrics.get("kb_context", "")

        user_content = ""
        if kb_context:
            user_content += f"Knowledge Base context:\n{kb_context}\n\n"
        if metrics:
            user_content += f"Data: {json.dumps(metrics, ensure_ascii=False)}\n\n"
        user_content += f"Query: {summary}"

        if full_context and full_context != summary:
            user_content += f"\n\nFull Input: {full_context}"

        messages.append({"role": "user", "content": user_content})
        return messages

    def _get_conversation_history(self, conversation_id: UUID, max_turns: int = 10) -> List[Dict[str, str]]:
        try:
            from backend.services.conversation_memory import get_conversation_history

            return get_conversation_history(conversation_id, max_turns)
        except Exception:
            return []

    def _save_conversation_turn(self, conversation_id: UUID, role: str, content: str, tools_used: list = None):
        try:
            from backend.services.conversation_memory import save_conversation_turn

            save_conversation_turn(conversation_id, role, content, tools_used=tools_used)
        except Exception as exc:
            logger.warning("agents: failed to save conversation turn for %s: %s", conversation_id, exc)


def bootstrap_diagnostic_task(
    summary: str,
    metrics: Dict[str, Any],
    conversation_id: UUID = None,
) -> None:
    """Ejecuta diagnóstico y persiste insights/tareas."""
    orchestrator = AgentOrchestrator()
    insight = orchestrator.run_diagnosis(
        summary,
        metrics,
        conversation_id=conversation_id,
    )
    db: Session = SessionLocal()
    try:
        content = insight.payload.strip() if insight.payload else ""
        is_relevant = len(content) > 20 and "no lo sé" not in content.lower() and "desconozco" not in content.lower()

        if is_relevant:
            crud.create_agent_insight(db, insight)
            crud.create_agent_task(
                db,
                schemas.AgentTaskCreate(
                    title="Revisar análisis de agente",
                    description=content[:500],
                    priority="medium",
                    source="agent",
                    metadata=insight.metadata,
                ),
            )
        else:
            logger.debug("Skipping task: content not relevant (%d chars)", len(content))
    finally:
        db.close()
