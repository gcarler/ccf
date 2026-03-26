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


SYSTEM_PROMPT = """You are CCF's autonomous ops agent. Summarize anomalies, propose tasks, and request data when needed."""


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
        payload = self.client.responses.create(
            model="o4-mini",
            reasoning={"effort": "medium"},
            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": f"Metrics: {json.dumps(metrics)}\nSummary: {summary}",
                },
            ],
            temperature=0.2,
        )
        content = payload.output[0].content[0].text
        return schemas.AgentInsightCreate(
            title="Diagn??stico autom??tico",
            insight_type="diagnostic",
            payload=content,
        )


def bootstrap_diagnostic_task(summary: str, metrics: Dict[str, Any]) -> None:
    orchestrator = AgentOrchestrator()
    insight = orchestrator.run_diagnosis(summary, metrics)
    db: Session = SessionLocal()
    try:
        crud.create_agent_insight(db, insight)
        crud.create_agent_task(
            db,
            schemas.AgentTaskCreate(
                title="Revisar diagn??stico autom??tico",
                description=insight.payload[:500],
                priority="high",
                source="agent",
            ),
            status="pending_review",
        )
    finally:
        db.close()
