"""Agent Orchestrator — Motor multiagente con tool calling y memoria.

Optimus Brain: motor de diagnóstico con LLM.
Ahora soporta:
- Tool calling (function calling de OpenAI/OpenRouter)
- Memoria de conversaciones
- Multi-step reasoning
- Respuestas estructuradas
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

# Optional dependency
try:  # pragma: no cover
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.core.database import SessionLocal

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


class AgentOrchestrator:
    """Orquestador multiagente con tool calling."""

    def __init__(self, api_key: str | None = None):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")

        key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("API key not configured. Set OPENROUTER_API_KEY or OPENROUTER_API_KEY.")

        is_openrouter = key.startswith("sk-or-")
        base_url = "https://openrouter.ai/api/v1" if is_openrouter else None

        self.client = OpenAI(base_url=base_url, api_key=key)
        self.default_model = "moonshotai/kimi-k2.6" if is_openrouter else "gpt-4o-mini"

    def run_diagnosis(
        self,
        summary: str,
        metrics: Dict[str, Any],
        conversation_id: Optional[UUID] = None,
        use_tools: bool = True,
    ) -> schemas.AgentInsightCreate:
        """Ejecuta diagnóstico con soporte de tool calling.

        Si use_tools=True y hay herramientas registradas, el LLM puede
        invocar herramientas para obtener datos reales.
        """
        if OpenAI is None:
            raise RuntimeError("openai package not installed")

        # Build messages with conversation history if available
        messages = self._build_messages(summary, metrics, conversation_id)

        # Build tools for function calling
        tools = []
        if use_tools:
            from backend.services.tool_registry import tool_registry

            tools = tool_registry.get_openai_tools()

        # Multi-turn iterative tool-calling loop
        max_iterations = 5
        iteration = 0
        total_tokens = 0
        tool_results = []
        content = ""

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

                    from backend.services.tool_registry import tool_registry

                    try:
                        result = tool_registry.execute(tool_name, **tool_args)
                    except Exception as err:
                        result = {"error": str(err)}

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

        # Save conversation to memory if conversation_id provided
        if conversation_id:
            self._save_conversation_turn(
                conversation_id,
                "user",
                summary,
            )
            self._save_conversation_turn(
                conversation_id,
                "assistant",
                content or "",
                tools_used=tool_results,
            )

        return schemas.AgentInsightCreate(
            title="Respuesta de Optimus",
            insight_type="assistant_response",
            payload=content,
            metadata={
                "tools_used": len(tool_results),
                "tool_details": tool_results,
                "model": self.default_model,
            },
        )

    def _build_messages(
        self,
        summary: str,
        metrics: Dict[str, Any],
        conversation_id: Optional[UUID] = None,
    ) -> List[Dict[str, str]]:
        """Construye mensajes para el LLM con historial si existe."""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history if available
        if conversation_id:
            history = self._get_conversation_history(conversation_id)
            messages.extend(history)

        # Add current query
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

    def _get_conversation_history(
        self,
        conversation_id: UUID,
        max_turns: int = 10,
    ) -> List[Dict[str, str]]:
        """Obtiene historial de conversación."""
        try:
            from backend.services.conversation_memory import get_conversation_history

            return get_conversation_history(conversation_id, max_turns)
        except Exception:
            return []

    def _save_conversation_turn(
        self,
        conversation_id: UUID,
        role: str,
        content: str,
        tools_used: list = None,
    ):
        """Guarda un turno de conversación."""
        try:
            from backend.services.conversation_memory import save_conversation_turn

            save_conversation_turn(
                conversation_id,
                role,
                content,
                tools_used=tools_used,
            )
        except Exception as exc:  # pragma: no cover - save_conversation_turn is non-critical
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
