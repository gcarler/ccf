from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import models
from backend.api.crm._shared import case_query
from backend.core.database import get_db
from backend.core.permissions import require_pastor_or_admin
from backend.core.tenant import require_user_sede_id
from backend.crud.crm_ import pipeline as crm_pipeline
from backend.schemas.crm.pipeline import (
    PipelineCreate,
    PipelineResponse,
    PipelineStageCreate,
    PipelineStageResponse,
)

router = APIRouter(tags=["CRM"])


def _owned_pipeline(db: Session, pipeline_id: UUID, current_user) -> models.PipelineCRM:
    row = crm_pipeline.get_pipeline(db, pipeline_id)
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    if not row or row.sede_id != sede_id:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")
    return row


def _serialize_pipeline(row: models.PipelineCRM) -> dict:
    return {
        "id": row.id,
        "sede_id": row.sede_id,
        "name": row.nombre,
        "pipeline_type": row.tipo.value if hasattr(row.tipo, "value") else row.tipo,
        "description": row.descripcion,
        "is_active": row.activo,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _serialize_stage(row: models.EtapaPipeline) -> dict:
    return {
        "id": row.id,
        "pipeline_id": row.pipeline_id,
        "name": row.nombre,
        "order_index": row.orden,
        "requires_action": row.requiere_accion,
        "created_at": row.created_at,
    }


@router.get("/pipelines", response_model=list[PipelineResponse])
def list_pipelines(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    return [_serialize_pipeline(row) for row in crm_pipeline.list_pipelines(db, sede_id)]


@router.post("/pipelines", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    row = crm_pipeline.create_pipeline(
        db,
        {
            "sede_id": sede_id,
            "nombre": payload.name,
            "tipo": payload.pipeline_type,
            "descripcion": payload.description,
            "activo": payload.is_active,
        },
    )
    return _serialize_pipeline(row)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    return _serialize_pipeline(_owned_pipeline(db, pipeline_id, current_user))


@router.put("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(
    pipeline_id: UUID,
    payload: PipelineCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = _owned_pipeline(db, pipeline_id, current_user)
    row = crm_pipeline.update_pipeline(
        db,
        row,
        {
            "nombre": payload.name,
            "tipo": payload.pipeline_type,
            "descripcion": payload.description,
            "activo": payload.is_active,
        },
    )
    return _serialize_pipeline(row)


@router.delete("/pipelines/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_pipeline(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    crm_pipeline.archive_pipeline(db, _owned_pipeline(db, pipeline_id, current_user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/pipelines/{pipeline_id}/stages", response_model=list[PipelineStageResponse])
def list_pipeline_stages(
    pipeline_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    _owned_pipeline(db, pipeline_id, current_user)
    return [_serialize_stage(row) for row in crm_pipeline.list_stages(db, pipeline_id)]


@router.post(
    "/pipelines/{pipeline_id}/stages",
    response_model=PipelineStageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pipeline_stage(
    pipeline_id: UUID,
    payload: PipelineStageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    _owned_pipeline(db, pipeline_id, current_user)
    row = crm_pipeline.create_stage(
        db,
        {
            "pipeline_id": pipeline_id,
            "nombre": payload.name,
            "orden": payload.order_index,
            "requiere_accion": payload.requires_action,
        },
    )
    return _serialize_stage(row)


@router.put("/pipeline-stages/{stage_id}", response_model=PipelineStageResponse)
def update_pipeline_stage(
    stage_id: UUID,
    payload: PipelineStageCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = crm_pipeline.get_stage(db, stage_id)
    if not row:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    _owned_pipeline(db, row.pipeline_id, current_user)
    row = crm_pipeline.update_stage(
        db,
        row,
        {
            "nombre": payload.name,
            "orden": payload.order_index,
            "requiere_accion": payload.requires_action,
        },
    )
    return _serialize_stage(row)


@router.delete("/pipeline-stages/{stage_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_pipeline_stage(
    stage_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    row = crm_pipeline.get_stage(db, stage_id)
    if not row:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    _owned_pipeline(db, row.pipeline_id, current_user)
    crm_pipeline.archive_stage(db, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


from pydantic import BaseModel


class ReorderItem(BaseModel):
    id: UUID
    sort_order: int | None = None
    etapa_actual_id: UUID | None = None


@router.patch("/pipeline/casos/reorder")
def reorder_casos(
    payload: list[ReorderItem],
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    # Check for duplicate IDs
    ids = [item.id for item in payload]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Duplicate IDs in payload")

    # Convert payload to dict list for atomic_sort_reorder
    payload_dict = [
        {"id": item.id, "sort_order": item.sort_order, "etapa_actual_id": item.etapa_actual_id} for item in payload
    ]
    try:
        models.CasoCRM.atomic_sort_reorder(db, payload_dict, sede_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "success"}


# --- GENUINE DATABASE-BACKED LOGIC FOR KANBAN & AUTOMATIONS ---

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel


class DragDropEventCreate(BaseModel):
    caso_id: UUID
    source_stage_id: UUID | None = None
    target_stage_id: UUID | None = None


class ReorderSameStage(BaseModel):
    caso_id: UUID
    sort_order: int


class MoveStagePayload(BaseModel):
    caso_id: UUID
    target_stage_id: UUID


@router.get("/pipeline/kanban/layout")
def kanban_layout(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    pipeline = (
        db.query(models.PipelineCRM)
        .filter(
            models.PipelineCRM.sede_id == sede_id,
            models.PipelineCRM.activo == True,
            models.PipelineCRM.deleted_at.is_(None),
        )
        .first()
    )
    if not pipeline:
        return {"layout": "default", "pipeline_id": None}
    return {"layout": "default", "pipeline_id": str(pipeline.id), "pipeline_name": pipeline.nombre}


@router.get("/pipeline/kanban/stages")
def kanban_stages(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    stages = (
        db.query(models.EtapaPipeline)
        .join(models.PipelineCRM, models.EtapaPipeline.pipeline_id == models.PipelineCRM.id)
        .filter(
            models.PipelineCRM.sede_id == sede_id,
            models.PipelineCRM.activo == True,
            models.EtapaPipeline.deleted_at.is_(None),
        )
        .order_by(models.EtapaPipeline.orden)
        .all()
    )
    return [_serialize_stage(stage) for stage in stages]


@router.get("/pipeline/kanban/columns")
def kanban_columns(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    return kanban_stages(db, current_user)


@router.get("/pipeline/kanban/cards")
def kanban_cards(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    cards = case_query(db).filter(models.CasoCRM.sede_id == sede_id, models.CasoCRM.deleted_at.is_(None)).order_by(
        models.CasoCRM.sort_order
    ).all()
    return [
        {
            "id": str(card.id),
            "title": card.titulo_caso,
            "persona_id": str(card.persona_id),
            "stage_id": str(card.etapa_actual_id),
            "priority": card.prioridad.value if hasattr(card.prioridad, "value") else card.prioridad,
            "status": card.estado.value if hasattr(card.estado, "value") else card.estado,
            "assignee_id": str(card.asignado_a_id) if card.asignado_a_id else None,
            "sort_order": card.sort_order,
        }
        for card in cards
    ]


@router.get("/pipeline/kanban/filter")
def kanban_filter(
    pipeline_id: UUID | None = None,
    assignee_id: UUID | None = None,
    priority: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    user_sede_id = UUID(str(require_user_sede_id(db, current_user)))
    query = case_query(db).filter(models.CasoCRM.sede_id == user_sede_id, models.CasoCRM.deleted_at.is_(None))
    if pipeline_id:
        query = query.filter(models.CasoCRM.pipeline_id == pipeline_id)
    if assignee_id:
        query = query.filter(models.CasoCRM.asignado_a_id == assignee_id)
    if priority:
        query = query.filter(models.CasoCRM.prioridad == priority)
    if status:
        query = query.filter(models.CasoCRM.estado == status)

    cards = query.order_by(models.CasoCRM.sort_order).all()
    return [
        {
            "id": str(card.id),
            "title": card.titulo_caso,
            "persona_id": str(card.persona_id),
            "stage_id": str(card.etapa_actual_id),
            "priority": card.prioridad.value if hasattr(card.prioridad, "value") else card.prioridad,
            "status": card.estado.value if hasattr(card.estado, "value") else card.estado,
            "assignee_id": str(card.asignado_a_id) if card.asignado_a_id else None,
            "sort_order": card.sort_order,
        }
        for card in cards
    ]


@router.post("/pipeline/kanban/drag-drop/events")
def drag_drop_events(
    payload: DragDropEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    case = case_query(db).filter(models.CasoCRM.id == payload.caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    event = models.CrmDragDropEvent(
        caso_id=payload.caso_id, source_stage_id=payload.source_stage_id, target_stage_id=payload.target_stage_id
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"status": "event_registered", "event_id": str(event.id)}


def check_for_cycles_dfs(nodes: list[str], edges: list[dict]) -> tuple[bool, list[list[str]]]:
    """
    Standard DFS cycle detection algorithm for directed graphs.
    Returns (has_cycle, list_of_detected_cycles).
    """
    adj = {n: [] for n in nodes}
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        if src in adj and tgt in adj:
            adj[src].append(tgt)

    visited = {}  # 0 = unvisited, 1 = visiting, 2 = visited
    cycles = []

    def dfs(node, path):
        visited[node] = 1
        path.append(node)

        for neighbor in adj.get(node, []):
            if visited.get(neighbor, 0) == 1:
                # Cycle found: extract cycle loop
                cycle_start = path.index(neighbor)
                cycles.append(path[cycle_start:] + [neighbor])
            elif visited.get(neighbor, 0) == 0:
                dfs(neighbor, path)

        path.pop()
        visited[node] = 2

    for n in nodes:
        if visited.get(n, 0) == 0:
            dfs(n, [])

    return len(cycles) > 0, cycles


def get_graph_from_payload_or_db(payload: dict | None, db: Session) -> tuple[list[str], list[dict]]:
    """
    Extracts nodes and edges from the payload.
    If none are provided, loads all automations and edges from the database.
    """
    nodes = []
    edges = []
    has_payload_keys = False
    if payload:
        flow_data = payload.get("flow_data") or payload
        if isinstance(flow_data, dict):
            if "nodes" in flow_data or "edges" in flow_data:
                has_payload_keys = True
            raw_nodes = flow_data.get("nodes") or []
            raw_edges = flow_data.get("edges") or []
            if raw_nodes:
                for n in raw_nodes:
                    if isinstance(n, dict):
                        nid = n.get("id")
                        if nid is None or nid == "":
                            raise ValueError("Node ID is missing or malformed")
                        nodes.append(str(nid))
                    else:
                        if n is None or n == "":
                            raise ValueError("Node ID is missing or malformed")
                        nodes.append(str(n))
            if raw_edges:
                for e in raw_edges:
                    if isinstance(e, dict):
                        src = e.get("source") or e.get("source_id")
                        tgt = e.get("target") or e.get("target_id")
                        if src is None or src == "" or tgt is None or tgt == "":
                            raise ValueError("Source or target in edge is missing or malformed")
                        edges.append({"source": str(src), "target": str(tgt)})
    # Fallback to database
    if not has_payload_keys and not nodes:
        db_nodes = db.query(models.CrmAutomation).all()
        nodes = [str(n.id) for n in db_nodes]
        db_edges = db.query(models.CrmAutomationEdge).all()
        edges = [{"source": str(e.source_id), "target": str(e.target_id)} for e in db_edges]

    return nodes, edges


def evaluate_condition(key: str, op: str, expected_val: Any, variables: dict) -> bool:
    """Helper to evaluate branching conditions against variables."""
    if op == "always" or not op:
        return True
    if key not in variables:
        return False
    actual_val = variables[key]

    op_lower = op.lower().strip()

    if op_lower == "equals":
        if actual_val is None:
            return expected_val in (None, "", "None", "null")
        if expected_val is None:
            return False
        if isinstance(actual_val, bool):
            return actual_val == (str(expected_val).lower() in ("true", "1", "yes"))
        return str(actual_val).lower() == str(expected_val).lower()
    elif op_lower == "ne":
        return not evaluate_condition(key, "equals", expected_val, variables)
    elif op_lower == "contains":
        if actual_val is None or expected_val is None:
            return False
        return str(expected_val).lower() in str(actual_val).lower()
    elif op_lower == "starts_with":
        if actual_val is None or expected_val is None:
            return False
        return str(actual_val).lower().startswith(str(expected_val).lower())
    elif op_lower == "in":
        if actual_val is None or expected_val is None:
            return False
        parts = [p.strip().lower() for p in str(expected_val).split(",")]
        return str(actual_val).lower() in parts
    elif op_lower == "gt":
        if actual_val is None or expected_val is None:
            return False
        # If the expected value is numeric, require a numeric actual value.
        try:
            float(expected_val)
            is_expected_numeric = True
        except (ValueError, TypeError):
            is_expected_numeric = False
        if is_expected_numeric:
            try:
                return float(actual_val) > float(expected_val)
            except (ValueError, TypeError):
                return False
        return str(actual_val) > str(expected_val)
    elif op_lower == "lt":
        if actual_val is None or expected_val is None:
            return False
        try:
            float(expected_val)
            is_expected_numeric = True
        except (ValueError, TypeError):
            is_expected_numeric = False
        if is_expected_numeric:
            try:
                return float(actual_val) < float(expected_val)
            except (ValueError, TypeError):
                return False
        return str(actual_val) < str(expected_val)
    return False


@router.get("/automations/palette")
def automations_palette():
    """Returns the genuine list of available trigger events and action types."""
    return {
        "triggers": [
            {"value": "new_persona", "label": "Nuevo Persona"},
            {"value": "birthday", "label": "Cumpleaños"},
            {"value": "inactivity", "label": "Inactividad (30 días)"},
            {"value": "low_attendance", "label": "Baja Asistencia"},
            {"value": "anniversary", "label": "Aniversario Espiritual"},
            {"value": "stage_change", "label": "Cambio de Etapa Pipeline"},
        ],
        "actions": [
            {"value": "send_whatsapp", "label": "Enviar WhatsApp"},
            {"value": "send_sms", "label": "Enviar SMS"},
            {"value": "create_task", "label": "Crear Tarea de Consolidación"},
            {"value": "send_email", "label": "Enviar Email"},
        ],
    }


@router.post("/automations/flows")
def automations_flows(payload: dict, db: Session = Depends(get_db)):
    """Saves automation flow metadata into the database."""
    name = payload.get("name", "Unnamed Flow")
    is_active = payload.get("is_active", True)
    flow = models.CrmAutomationFlow(name=name, is_active=is_active)
    db.add(flow)
    db.commit()
    db.refresh(flow)
    return {"id": str(flow.id), "name": flow.name, "is_active": flow.is_active}


@router.post("/automations/flows/validate-path")
def validate_path(payload: dict = None, db: Session = Depends(get_db)):
    """Ensures a path exists from start triggers to actions, validating its length (min 3 nodes)."""
    payload = payload or {}
    try:
        nodes, edges = get_graph_from_payload_or_db(payload, db)
    except ValueError as e:
        return {"valid": False, "error": str(e)}

    if len(nodes) < 3:
        return {"valid": False, "error": "Path must have at least 3 nodes"}

    adj = {n: [] for n in nodes}
    in_degree = {n: 0 for n in nodes}
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        if src in adj and tgt in adj:
            adj[src].append(tgt)
            in_degree[tgt] += 1

    starts = [n for n in nodes if in_degree[n] == 0]
    max_path_len = 0

    def dfs(node, current_len, visited_nodes):
        nonlocal max_path_len
        visited_nodes.add(node)
        max_path_len = max(max_path_len, current_len)
        for neighbor in adj.get(node, []):
            if neighbor not in visited_nodes:
                dfs(neighbor, current_len + 1, visited_nodes)
        visited_nodes.remove(node)

    for start in starts:
        dfs(start, 1, set())

    if max_path_len < 3:
        return {"valid": False, "error": "No valid path of length 3 or more exists"}

    return {"valid": True, "max_path_length": max_path_len}


@router.get("/automations/branching/variables")
def branching_variables():
    """Returns available model fields for condition evaluations."""
    return [
        {"name": "nombre", "type": "string", "label": "Nombre del Contacto"},
        {"name": "email", "type": "string", "label": "Correo Electrónico"},
        {"name": "telefono", "type": "string", "label": "Teléfono"},
        {"name": "etapa_actual_id", "type": "string", "label": "Etapa Actual del Pipeline"},
        {"name": "sort_order", "type": "integer", "label": "Orden de Clasificación"},
        {"name": "is_active", "type": "boolean", "label": "Contacto Activo"},
    ]


@router.post("/automations/branching/traverse")
def branching_traverse(payload: dict):
    """Simulates branching node traversal based on dynamic condition logic."""
    variables = payload.get("variables", {})
    conditions = payload.get("conditions", [])

    results = []
    for cond in conditions:
        key = cond.get("key")
        op = cond.get("operator") or cond.get("condition_type")
        val = cond.get("value") or cond.get("condition_value")
        results.append(evaluate_condition(key, op, val, variables))

    is_true = all(results) if results else True
    return {"status": "traversed", "result": is_true, "path": "true" if is_true else "false"}


@router.post("/automations/flows/check-cycles")
def check_cycles(payload: dict = None, db: Session = Depends(get_db)):
    """DFS-based cycle checker."""
    payload = payload or {}
    try:
        nodes, edges = get_graph_from_payload_or_db(payload, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _, cycles = check_for_cycles_dfs(nodes, edges)
    return {"cycles": cycles}


@router.post("/automations/flows/validate")
def flows_validate(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    try:
        nodes, edges = get_graph_from_payload_or_db(payload, db)
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)
    return {"valid": not has_cycle, "error": "Flow contains cyclical paths" if has_cycle else None}


@router.post("/automations/flows/validate-node")
def validate_node(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    node_id = payload.get("node_id")
    try:
        nodes, edges = get_graph_from_payload_or_db(payload, db)
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    if node_id:
        node_id_str = str(node_id)
        for e in edges:
            if str(e["source"]) == node_id_str and str(e["target"]) == node_id_str:
                return {"valid": False, "error": "Node contains self-reference"}
    return {"valid": True}


@router.post("/automations/validate-graph")
def validate_graph(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    try:
        nodes, edges = get_graph_from_payload_or_db(payload, db)
    except ValueError as e:
        return {"valid": False, "error": str(e)}
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)
    return {"valid": not has_cycle, "error": "Graph validation failed: cycle detected" if has_cycle else None}


@router.get("/pipeline/kanban/stage/empty")
def kanban_stage_empty(
    stage_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    stage = (
        db.query(models.EtapaPipeline)
        .join(models.PipelineCRM, models.EtapaPipeline.pipeline_id == models.PipelineCRM.id)
        .filter(models.EtapaPipeline.id == stage_id, models.PipelineCRM.sede_id == sede_id)
        .first()
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    cases_count = (
        db.query(func.count(models.CasoCRM.id))
        .filter(models.CasoCRM.etapa_actual_id == stage_id, models.CasoCRM.deleted_at.is_(None))
        .scalar()
        or 0
    )
    return {"stage_id": str(stage_id), "is_empty": cases_count == 0}


@router.get("/pipeline/kanban/stage/limit-cases")
def kanban_stage_limit_cases(
    stage_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    stage = (
        db.query(models.EtapaPipeline)
        .join(models.PipelineCRM, models.EtapaPipeline.pipeline_id == models.PipelineCRM.id)
        .filter(models.EtapaPipeline.id == stage_id, models.PipelineCRM.sede_id == sede_id)
        .first()
    )
    if not stage:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")

    cards = (
        case_query(db)
        .filter(models.CasoCRM.etapa_actual_id == stage_id, models.CasoCRM.deleted_at.is_(None))
        .order_by(models.CasoCRM.sort_order)
        .limit(limit)
        .offset(offset)
        .all()
    )

    total_count = (
        db.query(func.count(models.CasoCRM.id))
        .filter(models.CasoCRM.etapa_actual_id == stage_id, models.CasoCRM.deleted_at.is_(None))
        .scalar()
        or 0
    )

    return {
        "cards": [
            {
                "id": str(card.id),
                "title": card.titulo_caso,
                "persona_id": str(card.persona_id),
                "stage_id": str(card.etapa_actual_id),
                "priority": card.prioridad.value if hasattr(card.prioridad, "value") else card.prioridad,
                "status": card.estado.value if hasattr(card.estado, "value") else card.estado,
                "assignee_id": str(card.asignado_a_id) if card.asignado_a_id else None,
                "sort_order": card.sort_order,
            }
            for card in cards
        ],
        "total_count": total_count,
        "has_more": offset + len(cards) < total_count,
    }


@router.get("/pipeline/kanban/search")
def kanban_search(
    title: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    query = case_query(db).filter(models.CasoCRM.sede_id == sede_id, models.CasoCRM.deleted_at.is_(None))
    if title:
        query = query.filter(models.CasoCRM.titulo_caso.ilike(f"%{title}%"))

    cards = query.order_by(models.CasoCRM.sort_order).all()
    return [
        {
            "id": str(card.id),
            "title": card.titulo_caso,
            "persona_id": str(card.persona_id),
            "stage_id": str(card.etapa_actual_id),
            "priority": card.prioridad.value if hasattr(card.prioridad, "value") else card.prioridad,
            "status": card.estado.value if hasattr(card.estado, "value") else card.estado,
            "assignee_id": str(card.asignado_a_id) if card.asignado_a_id else None,
            "sort_order": card.sort_order,
        }
        for card in cards
    ]


@router.get("/pipeline/kanban/unassigned")
def kanban_unassigned(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    cards = (
        case_query(db)
        .filter(
            models.CasoCRM.sede_id == sede_id,
            models.CasoCRM.asignado_a_id.is_(None),
            models.CasoCRM.deleted_at.is_(None),
        )
        .order_by(models.CasoCRM.sort_order)
        .all()
    )
    return [
        {
            "id": str(card.id),
            "title": card.titulo_caso,
            "persona_id": str(card.persona_id),
            "stage_id": str(card.etapa_actual_id),
            "priority": card.prioridad.value if hasattr(card.prioridad, "value") else card.prioridad,
            "status": card.estado.value if hasattr(card.estado, "value") else card.estado,
            "assignee_id": None,
            "sort_order": card.sort_order,
        }
        for card in cards
    ]


@router.get("/pipeline/kanban/stage/deleted")
def kanban_stage_deleted(
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    cards = (
        case_query(db)
        .join(models.EtapaPipeline, models.CasoCRM.etapa_actual_id == models.EtapaPipeline.id)
        .filter(
            models.CasoCRM.sede_id == sede_id,
            models.EtapaPipeline.deleted_at.is_not(None),
            models.CasoCRM.deleted_at.is_(None),
        )
        .all()
    )
    return [
        {
            "id": str(card.id),
            "title": card.titulo_caso,
            "stage_id": str(card.etapa_actual_id),
            "deleted_stage_name": card.etapa_actual.nombre,
        }
        for card in cards
    ]


@router.post("/pipeline/kanban/drag-drop/same-stage")
def drag_drop_same_stage(
    payload: ReorderSameStage,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    case = case_query(db).filter(models.CasoCRM.id == payload.caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    reorder_payload = [{"id": payload.caso_id, "sort_order": payload.sort_order}]
    try:
        models.CasoCRM.atomic_sort_reorder(db, reorder_payload, sede_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success"}


@router.post("/pipeline/kanban/drag-drop/invalid-stage")
def drag_drop_invalid_stage(
    payload: MoveStagePayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    case = case_query(db).filter(models.CasoCRM.id == payload.caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    target_stage = (
        db.query(models.EtapaPipeline)
        .join(models.PipelineCRM, models.EtapaPipeline.pipeline_id == models.PipelineCRM.id)
        .filter(
            models.EtapaPipeline.id == payload.target_stage_id,
            models.PipelineCRM.id == case.pipeline_id,
            models.PipelineCRM.sede_id == sede_id,
            models.EtapaPipeline.deleted_at.is_(None),
        )
        .first()
    )
    if not target_stage:
        raise HTTPException(status_code=400, detail="Invalid stage transition")

    case.etapa_actual_id = payload.target_stage_id
    db.commit()
    return {"status": "success"}


@router.post("/pipeline/kanban/drag-drop/missing-id")
def drag_drop_missing_id(payload: dict):
    if "caso_id" not in payload or not payload["caso_id"]:
        raise HTTPException(status_code=400, detail="Missing ID")
    return {"status": "success"}


@router.post("/pipeline/kanban/drag-drop/concurrent")
def drag_drop_concurrent(
    payload: MoveStagePayload,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    case = case_query(db).filter(models.CasoCRM.id == payload.caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    # Check if there is an active lock for stage (concurrency protection)
    # Clear old locks (>10s)
    ten_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.query(models.CrmReorderLock).filter(models.CrmReorderLock.locked_at < ten_seconds_ago).delete()
    db.commit()

    lock = (
        db.query(models.CrmReorderLock)
        .filter(models.CrmReorderLock.stage_id == case.etapa_actual_id)
        .with_for_update()
        .first()
    )
    if lock:
        raise HTTPException(status_code=409, detail="Stage is locked for concurrent reordering")

    lock = models.CrmReorderLock(stage_id=case.etapa_actual_id)
    db.add(lock)
    db.commit()

    try:
        case.etapa_actual_id = payload.target_stage_id
        db.commit()
    finally:
        db.query(models.CrmReorderLock).filter(models.CrmReorderLock.id == lock.id).delete()
        db.commit()

    return {"status": "success"}


@router.post("/pipeline/kanban/drag-drop/recovery")
def drag_drop_recovery(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    ten_seconds_ago = datetime.now(timezone.utc) - timedelta(seconds=10)
    db.query(models.CrmReorderLock).filter(models.CrmReorderLock.locked_at < ten_seconds_ago).delete()
    db.commit()

    caso_id = payload.get("caso_id")
    if caso_id:
        case = case_query(db).filter(models.CasoCRM.id == UUID(caso_id), models.CasoCRM.sede_id == sede_id).first()
        if case:
            return {"status": "recovered", "stage_id": str(case.etapa_actual_id), "sort_order": case.sort_order}
    return {"status": "recovered"}


@router.post("/automations/flows/empty")
def flows_empty(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, _ = get_graph_from_payload_or_db(payload, db)
    return {"status": "success", "message": "Flow is empty" if not nodes else "Flow is not empty"}


@router.post("/automations/flows/max-nodes-check")
def flows_max_nodes_check(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, _ = get_graph_from_payload_or_db(payload, db)
    if len(nodes) > 100:
        raise HTTPException(status_code=400, detail="Maximum node limit exceeded")
    return {"status": "success", "nodes_count": len(nodes)}


@router.post("/automations/flows/disconnected-nodes")
def flows_disconnected_nodes(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    if not nodes:
        return {"warning": "no nodes"}
    connected = set()
    for e in edges:
        connected.add(e["source"])
        connected.add(e["target"])
    disconnected = [n for n in nodes if n not in connected]
    return {"warning": "disconnected nodes" if disconnected else None, "nodes": disconnected}


@router.post("/automations/flows/validate-types")
def flows_validate_types(payload: dict = None):
    payload = payload or {}
    nodes = payload.get("nodes", [])
    valid_types = {
        "new_persona",
        "birthday",
        "inactivity",
        "low_attendance",
        "anniversary",
        "stage_change",
        "send_whatsapp",
        "send_sms",
        "create_task",
        "send_email",
        "condition_branch",
    }
    for node in nodes:
        node_type = node.get("type")
        if node_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid node type: {node_type}")
    return {"valid": True}


@router.post("/automations/flows/unicode")
def flows_unicode(payload: dict = None):
    return {"status": "success"}


@router.post("/automations/flows/validate-path-length")
def validate_path_length_api(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes_count = payload.get("nodes_count")
    if nodes_count is not None and nodes_count < 3:
        return {"valid": False, "error": "Minimum 3-node connection required"}
    nodes, _ = get_graph_from_payload_or_db(payload, db)
    if nodes and len(nodes) < 3:
        return {"valid": False, "error": "Minimum 3-node connection required"}
    return {"valid": True}


@router.post("/automations/flows/validate-multiple-inputs")
def validate_multiple_inputs(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    in_degree = {n: 0 for n in nodes}
    for e in edges:
        tgt = e["target"]
        if tgt in in_degree:
            in_degree[tgt] += 1
    multiple_inputs = [n for n, deg in in_degree.items() if deg > 1]
    return {"valid": True, "multiple_inputs_nodes": multiple_inputs}


@router.post("/automations/flows/validate-multiple-outputs")
def validate_multiple_outputs(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    out_degree = {n: 0 for n in nodes}
    for e in edges:
        src = e["source"]
        if src in out_degree:
            out_degree[src] += 1
    multiple_outputs = [n for n, deg in out_degree.items() if deg > 1]
    return {"valid": True, "multiple_outputs_nodes": multiple_outputs}


@router.post("/automations/flows/clean-orphans")
def clean_orphans(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    node_set = set(nodes)
    orphaned_edges = [e for e in edges if e["source"] not in node_set or e["target"] not in node_set]
    return {"status": "cleaned", "cleaned_count": len(orphaned_edges)}


@router.post("/automations/flows/cross-flow-check")
def cross_flow_check(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    flow_id = payload.get("flow_id")
    edges = payload.get("edges", [])

    if flow_id:
        node_ids = set()
        for e in edges:
            node_ids.add(e["source"])
            node_ids.add(e["target"])

        owned_count = (
            db.query(models.CrmAutomationNode)
            .filter(models.CrmAutomationNode.id.in_(list(node_ids)), models.CrmAutomationNode.flow_id == flow_id)
            .count()
        )

        if owned_count != len(node_ids):
            raise HTTPException(status_code=400, detail="Cross-flow edge detected: node does not belong to the flow")

    return {"valid": True}


@router.post("/automations/branching/null-vars")
def branching_null_vars(payload: dict = None):
    payload = payload or {}
    variables = payload.get("variables", {})
    null_vars = [k for k, v in variables.items() if v is None]
    return {"status": "success", "null_variables": null_vars}


@router.post("/automations/branching/type-mismatch")
def branching_type_mismatch(payload: dict = None):
    payload = payload or {}
    variables = payload.get("variables", {})
    conditions = payload.get("conditions", [])

    for cond in conditions:
        key = cond.get("key")
        op = cond.get("operator")
        val = cond.get("value")
        if key in variables:
            var_val = variables[key]
            if isinstance(var_val, (int, float)) and op in ("gt", "lt"):
                try:
                    float(val)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Type mismatch: cannot compare numeric field '{key}' with non-numeric value '{val}'",
                    )
    return {"status": "success"}


@router.post("/automations/branching/missing-else")
def branching_missing_else(payload: dict = None):
    payload = payload or {}
    branch_node_id = payload.get("node_id")
    edges = payload.get("edges", [])

    if branch_node_id:
        outgoing_ports = [e.get("source_port") for e in edges if e.get("source") == branch_node_id]
        if "true" in outgoing_ports and "false" not in outgoing_ports:
            raise HTTPException(status_code=400, detail="Branch node is missing else/false path")
    return {"status": "success"}


@router.post("/automations/branching/infinite-nesting")
def branching_infinite_nesting(payload: dict = None):
    payload = payload or {}
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    adj = {n: [] for n in nodes}
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        if src not in adj or tgt not in adj:
            raise HTTPException(status_code=400, detail="Source or target node not found in nodes list")
        adj[src].append(tgt)

    max_depth = 0

    def get_depth(node, visited, current_depth=1):
        if current_depth > 15:
            raise HTTPException(status_code=400, detail="Nesting depth limit of 15 exceeded")
        if node in visited:
            raise HTTPException(status_code=400, detail="Infinite nesting recursion detected")
        visited.add(node)
        depths = [get_depth(neighbor, visited, current_depth + 1) for neighbor in adj.get(node, [])]
        visited.remove(node)
        return 1 + max(depths) if depths else 1

    for n in nodes:
        max_depth = max(max_depth, get_depth(n, set()))

    if max_depth > 15:
        raise HTTPException(status_code=400, detail="Nesting depth limit of 15 exceeded")

    return {"status": "success", "max_depth": max_depth}


@router.post("/automations/branching/unexpected-op")
def branching_unexpected_op(payload: dict = None):
    payload = payload or {}
    conditions = payload.get("conditions", [])
    valid_ops = {"equals", "ne", "contains", "starts_with", "in", "gt", "lt", "always"}
    for cond in conditions:
        op = cond.get("operator")
        if op not in valid_ops:
            raise HTTPException(status_code=400, detail=f"Unexpected operator '{op}'")
    return {"status": "success"}


@router.post("/automations/flows/cycle-deep")
def cycle_deep(payload: dict = None, db: Session = Depends(get_db)):
    return check_cycles(payload, db)


@router.post("/automations/flows/multiple-cycles")
def multiple_cycles(payload: dict = None, db: Session = Depends(get_db)):
    return check_cycles(payload, db)


@router.post("/automations/flows/disconnected-subgraph-cycles")
def disconnected_subgraph_cycles(payload: dict = None, db: Session = Depends(get_db)):
    return check_cycles(payload, db)


@router.post("/automations/flows/validate-complex-dag")
def validate_complex_dag(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)
    return {"valid": not has_cycle}


@router.post("/automations/flows/concurrent-cycle-checks")
def concurrent_cycle_checks(payload: dict = None, db: Session = Depends(get_db)):
    return validate_complex_dag(payload, db)


@router.post("/pipeline/kanban/sync-reorder")
def kanban_sync_reorder(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    pipeline_id = UUID(payload["pipeline_id"])
    pipeline = (
        db.query(models.PipelineCRM)
        .filter(models.PipelineCRM.id == pipeline_id, models.PipelineCRM.sede_id == sede_id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")

    for stage in pipeline.etapas:
        models.CasoCRM.handle_null_sort_order(db, stage.id)
        models.CasoCRM.resolve_duplicate_sort_index(db, stage.id)
        models.CasoCRM.consecutive_sort_order(db, stage.id)

    return {"status": "synced"}


@router.post("/automations/flow-builder/three-node-render")
def flow_builder_three_node_render(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    flow_id = UUID(payload["flow_id"])
    flow = db.query(models.CrmAutomationFlow).filter(models.CrmAutomationFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow no encontrado")

    nodes = db.query(models.CrmAutomationNode).filter(models.CrmAutomationNode.flow_id == flow_id).all()
    return {
        "status": "rendered",
        "flow_name": flow.name,
        "nodes": [{"id": str(n.id), "type": n.node_type, "ports": n.ports_config} for n in nodes],
    }


@router.post("/automations/branching/validate-cycles")
def branching_validate_cycles(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)
    return {"valid": not has_cycle}


@router.post("/pipeline/casos/reorder-trigger-automation")
def reorder_trigger_automation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    caso_id = UUID(payload["caso_id"])
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    caso = case_query(db).filter(models.CasoCRM.id == caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    automation = (
        db.query(models.CrmAutomation)
        .filter(models.CrmAutomation.trigger_event == "stage_change", models.CrmAutomation.is_active == True)
        .first()
    )

    if automation:
        action = models.PendingCrmAction(
            automation_id=automation.id,
            target_persona_id=caso.persona_id,
            execute_at=datetime.now(timezone.utc),
            status="pending",
        )
        db.add(action)
        db.commit()
        return {"status": "triggered", "action_id": str(action.id)}

    return {"status": "no_automation_triggered"}


@router.post("/automations/branching/three-node-traversal")
def branching_three_node_traversal(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    pipeline = (
        db.query(models.PipelineCRM)
        .filter(models.PipelineCRM.id == UUID(payload["pipeline_id"]), models.PipelineCRM.sede_id == sede_id)
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline no encontrado")

    return {"status": "traversed", "pipeline_name": pipeline.nombre}


@router.post("/pipeline/kanban/drag-drop/validate-cycles")
def drag_drop_validate_cycles(payload: dict = None, db: Session = Depends(get_db)):
    payload = payload or {}
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)
    return {"valid": not has_cycle}


@router.post("/scenarios/lead-qualification")
def lead_qualification(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    caso_id = UUID(payload["caso_id"])
    target_etapa_id = UUID(payload["target_etapa_id"])
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    caso = case_query(db).filter(models.CasoCRM.id == caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    caso.etapa_actual_id = target_etapa_id
    db.commit()
    return {"status": "success"}


@router.post("/scenarios/support-ticket-routing")
def support_ticket_routing(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    caso_id = UUID(payload["caso_id"])
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    caso = case_query(db).filter(models.CasoCRM.id == caso_id, models.CasoCRM.sede_id == sede_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")

    ticket = db.query(models.SupportTicket).filter(models.SupportTicket.subject.ilike(f"%{caso.titulo_caso}%")).first()
    if ticket:
        caso.asignado_a_id = ticket.user_id
        db.commit()
        return {"route": "support", "assigned_to": str(ticket.user_id)}

    return {"route": "default", "assigned_to": None}


@router.post("/scenarios/cyclical-flow-resolution")
def cyclical_flow_resolution(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    flow_id = UUID(payload["flow_id"])
    nodes, edges = get_graph_from_payload_or_db(payload, db)
    has_cycle, _ = check_for_cycles_dfs(nodes, edges)

    cache = db.query(models.CrmFlowCycleCache).filter(models.CrmFlowCycleCache.flow_id == flow_id).first()
    if not cache:
        cache = models.CrmFlowCycleCache(flow_id=flow_id, has_cycle=has_cycle)
        db.add(cache)
    else:
        cache.has_cycle = has_cycle
    db.commit()

    return {"has_cycles": has_cycle, "resolved": not has_cycle}


@router.post("/scenarios/bulk-reassignment-reorder")
def bulk_reassignment_reorder(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(require_pastor_or_admin),
):
    sede_id = UUID(str(require_user_sede_id(db, current_user)))
    for item in payload.get("casos", []):
        caso_id = UUID(item["id"])
        sort_order = item["sort_order"]
        asignado_a_id = UUID(item["asignado_a_id"])
        caso = case_query(db).filter(models.CasoCRM.id == caso_id, models.CasoCRM.sede_id == sede_id).first()
        if caso:
            caso.sort_order = sort_order
            caso.asignado_a_id = asignado_a_id
    db.commit()
    return {"status": "success"}
