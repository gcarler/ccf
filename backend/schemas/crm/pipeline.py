from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas._common import AwareDateTime, orm_config


class PipelineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    pipeline_type: str
    description: str | None = None
    sede_id: UUID | None = None
    is_active: bool = True


class PipelineResponse(BaseModel):
    model_config = orm_config

    id: UUID
    sede_id: UUID
    name: str
    pipeline_type: str
    description: str | None = None
    is_active: bool
    created_at: AwareDateTime
    updated_at: AwareDateTime


class PipelineStageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_id: UUID | None = None
    name: str = Field(min_length=1, max_length=100)
    order_index: int = Field(ge=0)
    requires_action: bool = True


class PipelineStageResponse(BaseModel):
    model_config = orm_config

    id: UUID
    pipeline_id: UUID
    name: str
    order_index: int
    requires_action: bool
    created_at: AwareDateTime


# --- Payloads de automatizaciones (Kanban / Flow Builder / Branching) ---


class AutomationFlowCreate(BaseModel):
    """Payload de POST /automations/flows.

    Axioma 3: ``sede_id`` se resuelve server-side; el cliente no puede inyectarlo.
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class AutomationNodePayload(BaseModel):
    """Nodo de grafo de automatización.

    El editor envía nodos ricos de react-flow; los tests y clientes ligeros
    envían el identificador como string. Ambas formas son válidas.
    """

    model_config = ConfigDict(extra="allow")

    id: UUID | str | None = None
    type: str | None = None
    position: dict[str, Any] | None = None
    data: dict[str, Any] | None = None


class AutomationEdgePayload(BaseModel):
    """Arista de grafo de automatización (source → target, con puerto opcional)."""

    model_config = ConfigDict(extra="allow")

    source: UUID | str | None = None
    source_id: UUID | str | None = None
    target: UUID | str | None = None
    target_id: UUID | str | None = None
    source_port: str | None = None


class AutomationConditionPayload(BaseModel):
    """Condición de branching evaluada por los endpoints de traversing."""

    model_config = ConfigDict(extra="allow")

    key: str | None = None
    operator: str | None = None
    condition_type: str | None = None
    value: str | float | int | bool | None = None
    condition_value: str | float | int | bool | None = None


class AutomationGraphPayload(BaseModel):
    """Payload de los endpoints de validación de grafos de flujos.

    Todos los campos son opcionales: cuerpo ausente o ``{}`` equivalen a un
    grafo vacío con fallback a la base de datos. Los nodos se preservan de
    forma polimórfica (dict rico o string) porque el servicio legacy
    ``get_graph_from_payload_or_db`` acepta ambas formas.
    """

    model_config = ConfigDict(extra="ignore")

    flow_id: UUID | None = None
    flow_data: AutomationFlowData | None = None
    node: dict[str, Any] | None = None
    nodes: list[Any] = Field(default_factory=list)
    edges: list[Any] = Field(default_factory=list)
    node_id: str | None = None
    nodes_count: int | None = None
    path: list[Any] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)
    conditions: list[AutomationConditionPayload] = Field(default_factory=list)


class AutomationFlowData(BaseModel):
    """Cuerpo del grafo embebido (``flow_data``) opcionalmente en el payload."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[AutomationNodePayload] = Field(default_factory=list)
    edges: list[AutomationEdgePayload] = Field(default_factory=list)


def automation_payload_to_dict(payload: AutomationGraphPayload | None) -> dict[str, Any]:
    """Convierte el payload tipado al dict plano que consume el servicio legacy.

    ``exclude_unset`` preserva exactamente las claves que envió el cliente:
    un cuerpo ``{}`` se queda como ``{}`` (el servicio hace fallback a base de
    datos) y los valores ``None`` de ``variables`` no se descartan.
    """

    if payload is None:
        return {}
    return payload.model_dump(mode="json", exclude_unset=True)
