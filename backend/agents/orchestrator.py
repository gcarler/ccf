from __future__ import annotations

import json
import os
from typing import Any, Dict

# Optional dependency; skip orchestration if missing
try:  # pragma: no cover - optional import
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore

from sqlalchemy.orm import Session

from backend import crud, schemas
from backend.core.database import SessionLocal


SYSTEM_PROMPT = """You are Optimus Brain, the Neural MESH engine for CCF. 
Your goal is to assist users with ministerial management, data analysis, and theological foundations.
Always be professional, concise, and helpful. 
If context from the Knowledge Base is provided, use it to ground your answers.
If you don't know something, offer to notify a pastor or admin."""


class AgentOrchestrator:
    def __init__(self, api_key: str | None = None):
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        self.client = OpenAI(api_key=key)

    def run_diagnosis(self, summary: str, metrics: Dict[str, Any]) -> schemas.AgentInsightCreate:
        if OpenAI is None:
            raise RuntimeError("openai package not installed")
        
        # Build context from metrics if available
        full_context = metrics.get("full_query", summary)
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Data/Context: {json.dumps(metrics)}\n\nQuery/Summary: {summary}\n\nFull Input: {full_context}",
                },
            ],
            temperature=0.7,
        )
        
        content = response.choices[0].message.content
        
        return schemas.AgentInsightCreate(
            title="Respuesta de Optimus",
            insight_type="assistant_response",
            payload=content,
        )


def bootstrap_diagnostic_task(summary: str, metrics: Dict[str, Any]) -> None:
    orchestrator = AgentOrchestrator()
    insight = orchestrator.run_diagnosis(summary, metrics)
    db: Session = SessionLocal()
    try:
        # Solo persistir si el contenido es relevante (evitar ruido)
        content = insight.payload.strip()
        is_relevant = len(content) > 20 and "no lo sé" not in content.lower() and "desconozco" not in content.lower()
        
        if is_relevant:
            crud.create_agent_insight(db, insight)
            crud.create_agent_task(
                db,
                schemas.AgentTaskCreate(
                    title="Revisar análisis de agente",
                    description=insight.payload[:500],
                    priority="medium",
                    source="agent",
                ),
                status="pending_review",
            )
        else:
            print(f"Skipping task persistence: Content not relevant enough ({len(content)} chars)")
    finally:
        db.close()
