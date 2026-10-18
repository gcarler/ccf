#!/usr/bin/env python3
"""Generate/check the Projects router inventory from the application's OpenAPI."""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUTPUT = ROOT / "docs" / "PROJECTS_API_ROUTE_INVENTORY.md"
PROJECT_PREFIX = "/api/projects"
PROJECTS_PREFIX = "/api/v1/projects"
HTTP_METHODS = {"delete", "get", "head", "options", "patch", "post", "put", "trace"}
IGNORED_SCHEMA_REFS = {"HTTPValidationError", "ValidationError"}


def schema_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            name = ref.rsplit("/", maxsplit=1)[-1]
            if name not in IGNORED_SCHEMA_REFS:
                refs.add(name)
        for child in value.values():
            refs.update(schema_refs(child))
    elif isinstance(value, list):
        for child in value:
            refs.update(schema_refs(child))
    return refs


def refs_cell(refs: set[str]) -> str:
    return ", ".join(f"`{name}`" for name in sorted(refs)) or "—"


def response_cell(responses: Any) -> str:
    if not isinstance(responses, dict):
        return "—"
    rows: list[str] = []
    for code, response in sorted(responses.items(), key=lambda item: item[0]):
        names = refs_cell(schema_refs(response))
        rows.append(f"`{code}` {names}")
    return "<br>".join(rows) or "—"


def route_inventory(openapi: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    operations: list[tuple[str, str, dict[str, Any]]] = []
    paths = openapi.get("paths", {})
    for path, path_item in paths.items():
        if path != PROJECT_PREFIX and not path.startswith(f"{PROJECT_PREFIX}/"):
            continue
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                operations.append((method.upper(), path, operation))
    return sorted(operations, key=lambda item: (item[1], item[0]))


def declared_guards() -> dict[tuple[str, str], str]:
    """Read authorization dependencies from the actual FastAPI route objects."""
    from fastapi.routing import APIRoute

    from backend.api.projects import router

    guards: dict[tuple[str, str], str] = {}
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        user_dependency = next(
            (dependency for dependency in route.dependant.dependencies if dependency.name == "current_user"),
            None,
        )
        guard = "NO current_user dependency"
        if user_dependency is not None and user_dependency.call is not None:
            call = user_dependency.call
            qualified_name = getattr(call, "__qualname__", getattr(call, "__name__", "unknown"))
            closure = dict(zip(call.__code__.co_freevars, call.__closure__ or ()))
            if "permission" in closure:
                guard = str(closure["permission"].cell_contents)
            elif "min_level" in closure:
                guard = f"project access: {closure['min_level'].cell_contents}"
            else:
                guard = qualified_name.rsplit(".", maxsplit=1)[-1]

        route_path = f"{PROJECT_PREFIX}{route.path}" if route.path else PROJECT_PREFIX
        for method in route.methods or set():
            key = (method.upper(), route_path)
            if key in guards:
                raise ValueError(f"Duplicate Projects route while collecting guards: {key}")
            guards[key] = guard
    return guards


UNAUTHENTICATED_GUARD = "NO current_user dependency"


def summarize_projects_guard_coverage(openapi: dict[str, Any]) -> dict[str, Any]:
    """Resumen puro de cobertura de guards de seguridad del router Projects.

    Inspecciona `route_inventory(openapi)` y `declared_guards()` y retorna:
    - `total_operations`: operaciones OpenAPI bajo /api/projects.
    - `authenticated_operations`: operaciones con guard válido (≠ NO current
      user dependency).
    - `unauthenticated_operations`: operaciones con guard
      'NO current_user dependency'.
    - `missing_guard_mappings`: operaciones OpenAPI sin entrada en el mapa
      de guards del router.
    - `coverage_pct`: 100.0 si no hay operaciones; si no, % autenticadas
      (2 decimales).
    - `guard_distribution`: conteos por nombre de guard (ordenados
      alfabéticamente por nombre).
    - `is_fully_guarded`: True sólo con > 0 operaciones, 0 sin autenticar
      y 0 sin mapeo de guard.
    """
    operations = route_inventory(openapi)
    guards = declared_guards()

    total_operations = len(operations)
    guard_distribution: dict[str, int] = {}
    authenticated = 0
    unauthenticated_operations = 0
    missing_guard_mappings = 0

    for method, path, _operation in operations:
        guard = guards.get((method, path))
        if guard is None:
            missing_guard_mappings += 1
            continue
        guard_distribution[guard] = guard_distribution.get(guard, 0) + 1
        if guard == UNAUTHENTICATED_GUARD:
            unauthenticated_operations += 1
        else:
            authenticated += 1

    coverage_pct = (
        100.0
        if total_operations == 0
        else round((authenticated / total_operations) * 100.0, 2)
    )

    return {
        "total_operations": total_operations,
        "authenticated_operations": authenticated,
        "unauthenticated_operations": unauthenticated_operations,
        "missing_guard_mappings": missing_guard_mappings,
        "coverage_pct": coverage_pct,
        "guard_distribution": {
            name: count for name, count in sorted(guard_distribution.items())
        },
        "is_fully_guarded": (
            total_operations > 0
            and unauthenticated_operations == 0
            and missing_guard_mappings == 0
        ),
    }


def summarize_projects_http_method_footprint(openapi: dict[str, Any]) -> dict[str, Any]:
    """Audita la superficie de lectura vs mutación y referencias de esquemas en las rutas /api/projects."""
    operations = route_inventory(openapi if isinstance(openapi, dict) else {})
    total_operations = len(operations)

    read_only_operations = 0
    mutation_operations = 0
    raw_method_counts: dict[str, int] = {}
    all_refs: set[str] = set()

    for method, _path, operation in operations:
        raw_method_counts[method] = raw_method_counts.get(method, 0) + 1
        if method in {"GET", "HEAD", "OPTIONS"}:
            read_only_operations += 1
        elif method in {"POST", "PUT", "PATCH", "DELETE"}:
            mutation_operations += 1
        all_refs.update(schema_refs(operation))

    method_counts = {
        method: count for method, count in sorted(raw_method_counts.items())
    }
    unique_schema_refs_count = len(all_refs)
    mutation_ratio_pct = (
        round((mutation_operations / total_operations) * 100.0, 2)
        if total_operations > 0
        else 0.0
    )

    return {
        "total_operations": total_operations,
        "read_only_operations": read_only_operations,
        "mutation_operations": mutation_operations,
        "method_counts": method_counts,
        "unique_schema_refs_count": unique_schema_refs_count,
        "mutation_ratio_pct": mutation_ratio_pct,
    }


def summarize_projects_route_path_complexity(
    openapi: dict[str, Any] | None,
) -> dict[str, Any]:
    """Analiza la complejidad jerárquica de las rutas Projects en un OpenAPI.

    Examina las rutas bajo ``PROJECTS_PREFIX`` ('/api/v1/projects') y retorna:
    - `total_project_paths`: rutas con prefijo Projects.
    - `parameterized_routes_count`: rutas con al menos un parámetro `{param}`.
    - `deep_nested_routes_count`: rutas con >= 2 parámetros o depth >= 6 segmentos.
    - `max_segment_depth`: profundidad máxima de segmentos (0 sin rutas).
    - `max_path_params`: máximo de parámetros por ruta (0 sin rutas).
    - `hierarchy_status`: 'no_project_routes' sin rutas Projects;
      'excessive_nesting' con >= 3 parámetros o >= 8 segmentos;
      'hierarchical_subresources' con >= 1 ruta deep-nested; y
      'flat_collection_routes' en cualquier otro caso.
    """
    paths = (openapi or {}).get("paths", {})
    if not isinstance(paths, dict):
        paths = {}

    matching_paths = [
        path
        for path in paths
        if isinstance(path, str) and path.startswith(PROJECTS_PREFIX)
    ]

    depths: list[int] = []
    param_counts: list[int] = []
    parameterized_routes_count = 0
    deep_nested_routes_count = 0

    for path in matching_paths:
        segments = [seg for seg in path.strip("/").split("/") if seg]
        segment_depth = len(segments)
        path_params_count = sum(
            1 for seg in segments if seg.startswith("{") and seg.endswith("}")
        )
        depths.append(segment_depth)
        param_counts.append(path_params_count)
        if path_params_count >= 1:
            parameterized_routes_count += 1
        if path_params_count >= 2 or segment_depth >= 6:
            deep_nested_routes_count += 1

    total_project_paths = len(matching_paths)
    max_segment_depth = max(depths, default=0)
    max_path_params = max(param_counts, default=0)

    if total_project_paths == 0:
        hierarchy_status = "no_project_routes"
    elif max_path_params >= 3 or max_segment_depth >= 8:
        hierarchy_status = "excessive_nesting"
    elif deep_nested_routes_count >= 1:
        hierarchy_status = "hierarchical_subresources"
    else:
        hierarchy_status = "flat_collection_routes"

    return {
        "total_project_paths": total_project_paths,
        "parameterized_routes_count": parameterized_routes_count,
        "deep_nested_routes_count": deep_nested_routes_count,
        "max_segment_depth": max_segment_depth,
        "max_path_params": max_path_params,
        "hierarchy_status": hierarchy_status,
    }


def summarize_projects_subresource_domains(
    inventory: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Agrupa un inventario de rutas de proyectos por dominio de subrecurso (PMBOK 8.2 / 10.2).

    Ignora entradas que no sean ``dict``. Para cada ruta ``path``, extrae los segmentos
    separados por ``'/'`` ignorando vacíos, ``'api'``, ``'v1'``, ``'projects'`` y
    parámetros ``'{...}'``, tomando el primer segmento restante en minúsculas como
    nombre de dominio (o ``'root'`` si no queda ningún segmento literal).
    """
    counts: dict[str, int] = {}
    total_routes = 0

    for item in inventory or []:
        if not isinstance(item, dict):
            continue
        total_routes += 1
        path = str(item.get("path") or "").strip()
        remaining = [
            seg.strip().lower()
            for seg in path.split("/")
            if seg.strip()
            and seg.strip().lower() not in {"api", "v1", "projects"}
            and not (seg.strip().startswith("{") and seg.strip().endswith("}"))
        ]
        domain = remaining[0] if remaining else "root"
        counts[domain] = counts.get(domain, 0) + 1

    domain_counts = dict(sorted(counts.items()))
    unique_domains_count = len(domain_counts)

    if total_routes == 0:
        top_domain = "none"
        posture = "EMPTY_INVENTORY"
    else:
        top_domain = min(domain_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if unique_domains_count >= 5:
            posture = "COMPREHENSIVE_DOMAIN_MODULARITY"
        else:
            posture = "NARROW_DOMAIN_SCOPE"

    return {
        "total_routes": total_routes,
        "unique_domains_count": unique_domains_count,
        "domain_counts": domain_counts,
        "top_domain": top_domain,
        "posture": posture,
    }


def summarize_projects_schema_reference_density(
    openapi: dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita la densidad de referencias de esquemas y tipado en rutas /api/projects."""
    safe_openapi = (
        openapi
        if isinstance(openapi, dict) and isinstance(openapi.get("paths", {}), dict)
        else {}
    )
    operations = route_inventory(safe_openapi)
    total_operations = len(operations)

    typed_request_body_count = 0
    typed_response_count = 0
    untyped_mutation_routes: list[str] = []
    all_refs: set[str] = set()

    for method, path, operation in operations:
        req_refs = schema_refs(operation.get("requestBody", {}))
        resp_refs = schema_refs(operation.get("responses", {}))
        if req_refs:
            typed_request_body_count += 1
        if resp_refs:
            typed_response_count += 1
        if method in {"POST", "PUT", "PATCH"} and not req_refs and not resp_refs:
            untyped_mutation_routes.append(f"{method} {path}")
        all_refs.update(schema_refs(operation))

    untyped_mutation_routes_sorted = sorted(untyped_mutation_routes)
    unique_schemas_referenced = sorted(all_refs)
    response_typing_coverage_pct = (
        round((typed_response_count / total_operations) * 100.0, 2)
        if total_operations > 0
        else 0.0
    )

    if total_operations == 0:
        contract_posture = "EMPTY_OPENAPI_INVENTORY"
    elif len(untyped_mutation_routes_sorted) > 0:
        contract_posture = "UNTYPED_MUTATIONS_DETECTED"
    elif response_typing_coverage_pct >= 80.0:
        contract_posture = "STRONGLY_TYPED_CONTRACTS"
    else:
        contract_posture = "PARTIAL_RESPONSE_TYPING"

    return {
        "total_operations": total_operations,
        "typed_request_body_count": typed_request_body_count,
        "typed_response_count": typed_response_count,
        "untyped_mutation_routes": untyped_mutation_routes_sorted,
        "unique_schemas_referenced": unique_schemas_referenced,
        "response_typing_coverage_pct": response_typing_coverage_pct,
        "contract_posture": contract_posture,
    }


def summarize_projects_error_response_coverage(
    openapi: dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita la cobertura de códigos de estado HTTP 2xx y 4xx en rutas /api/projects."""
    safe_openapi = (
        openapi
        if isinstance(openapi, dict) and isinstance(openapi.get("paths", {}), dict)
        else {}
    )
    operations = route_inventory(safe_openapi)
    total_operations = len(operations)

    has_2xx_success_count = 0
    has_4xx_or_422_count = 0
    missing_success_status_routes: list[str] = []
    missing_error_status_routes: list[str] = []

    for method, path, operation in operations:
        responses = operation.get("responses", {})
        codes = [str(k) for k in responses.keys()] if isinstance(responses, dict) else []
        has_2xx = any(c.startswith("2") for c in codes)
        has_4xx = any(c.startswith("4") for c in codes)
        if has_2xx:
            has_2xx_success_count += 1
        else:
            missing_success_status_routes.append(f"{method} {path}")
        if has_4xx:
            has_4xx_or_422_count += 1
        else:
            missing_error_status_routes.append(f"{method} {path}")

    missing_success_sorted = sorted(missing_success_status_routes)
    missing_error_sorted = sorted(missing_error_status_routes)
    error_coverage_pct = (
        round((has_4xx_or_422_count / total_operations) * 100.0, 2)
        if total_operations > 0
        else 0.0
    )

    if total_operations == 0:
        status_posture = "EMPTY_OPENAPI_INVENTORY"
    elif len(missing_success_sorted) > 0:
        status_posture = "MISSING_SUCCESS_CONTRACT"
    elif error_coverage_pct >= 80.0:
        status_posture = "COMPREHENSIVE_STATUS_COVERAGE"
    else:
        status_posture = "PARTIAL_ERROR_DOCUMENTATION"

    return {
        "total_operations": total_operations,
        "has_2xx_success_count": has_2xx_success_count,
        "has_4xx_or_422_count": has_4xx_or_422_count,
        "missing_success_status_routes": missing_success_sorted,
        "missing_error_status_routes": missing_error_sorted,
        "error_coverage_pct": error_coverage_pct,
        "status_posture": status_posture,
    }


def summarize_projects_operation_documentation_quality(
    openapi: dict[str, Any] | None,
) -> dict[str, Any]:
    """Audita la calidad documental (summary, operationId y tags) en rutas /api/projects."""
    safe_openapi = (
        openapi
        if isinstance(openapi, dict) and isinstance(openapi.get("paths", {}), dict)
        else {}
    )
    operations = route_inventory(safe_openapi)
    total_operations = len(operations)

    has_summary_count = 0
    has_operation_id_count = 0
    has_tags_count = 0
    undocumented_routes: list[str] = []
    op_id_counts: dict[str, int] = {}

    for method, path, operation in operations:
        summary_str = str(operation.get("summary") or "").strip()
        op_id_str = str(operation.get("operationId") or "").strip()

        if len(summary_str) >= 5:
            has_summary_count += 1
        else:
            undocumented_routes.append(f"{method} {path}")

        if len(op_id_str) > 0:
            has_operation_id_count += 1
            op_id_counts[op_id_str] = op_id_counts.get(op_id_str, 0) + 1

        if bool(operation.get("tags")):
            has_tags_count += 1

    undocumented_routes_sorted = sorted(undocumented_routes)
    duplicate_operation_ids = sorted(
        op_id for op_id, count in op_id_counts.items() if count > 1
    )
    summary_coverage_pct = (
        round((has_summary_count / total_operations) * 100.0, 2)
        if total_operations > 0
        else 0.0
    )

    if total_operations == 0:
        documentation_posture = "EMPTY_OPENAPI_INVENTORY"
    elif len(duplicate_operation_ids) > 0:
        documentation_posture = "DUPLICATE_OPERATION_IDS"
    elif summary_coverage_pct >= 80.0:
        documentation_posture = "WELL_DOCUMENTED_OPERATIONS"
    else:
        documentation_posture = "INCOMPLETE_OPERATION_SUMMARIES"

    return {
        "total_operations": total_operations,
        "has_summary_count": has_summary_count,
        "has_operation_id_count": has_operation_id_count,
        "has_tags_count": has_tags_count,
        "undocumented_routes": undocumented_routes_sorted,
        "duplicate_operation_ids": duplicate_operation_ids,
        "summary_coverage_pct": summary_coverage_pct,
        "documentation_posture": documentation_posture,
    }


PAGINATION_OR_FILTER_PARAMS = {
    "limit",
    "offset",
    "page",
    "page_size",
    "per_page",
    "skip",
    "cursor",
    "q",
    "search",
    "status",
    "phase",
    "phase_id",
}


def summarize_projects_collection_pagination_coverage(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la cobertura de paginación y filtrado query en endpoints GET de colección de proyectos."""
    empty_result: dict[str, Any] = {
        "collection_get_count": 0,
        "paginated_or_filtered_count": 0,
        "unbounded_collection_ops": [],
        "coverage_pct": 0.0,
        "pagination_posture": "NO_COLLECTION_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    collection_get_count = 0
    paginated_or_filtered_count = 0
    unbounded_collection_ops: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or "/projects" not in path:
            continue
        if not isinstance(path_item, dict):
            continue
        op_spec = path_item.get("get")
        if not isinstance(op_spec, dict):
            continue
        if path.rstrip("/").endswith("}"):
            continue

        collection_get_count += 1
        path_params = (
            path_item.get("parameters")
            if isinstance(path_item.get("parameters"), list)
            else []
        )
        op_params = (
            op_spec.get("parameters")
            if isinstance(op_spec.get("parameters"), list)
            else []
        )
        query_names = {
            str(param.get("name") or "").strip().lower()
            for param in (*path_params, *op_params)
            if isinstance(param, dict)
            and str(param.get("in") or "").strip().lower() == "query"
        }

        if query_names & PAGINATION_OR_FILTER_PARAMS:
            paginated_or_filtered_count += 1
        else:
            unbounded_collection_ops.append(f"GET {path}")

    if collection_get_count == 0:
        return empty_result

    coverage_pct = round(
        (paginated_or_filtered_count / collection_get_count) * 100.0, 2
    )
    if len(unbounded_collection_ops) == 0:
        pagination_posture = "BOUNDED_COLLECTION_CONTRACTS"
    elif coverage_pct >= 50.0:
        pagination_posture = "PARTIAL_PAGINATION_COVERAGE"
    else:
        pagination_posture = "UNBOUNDED_COLLECTION_RISK"

    return {
        "collection_get_count": collection_get_count,
        "paginated_or_filtered_count": paginated_or_filtered_count,
        "unbounded_collection_ops": unbounded_collection_ops,
        "coverage_pct": coverage_pct,
        "pagination_posture": pagination_posture,
    }


def summarize_projects_path_parameter_uuid_typing(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el tipado UUIDv4 de los parámetros de ruta id/*_id en operaciones de proyectos."""
    empty_result: dict[str, Any] = {
        "id_path_param_count": 0,
        "uuid_typed_count": 0,
        "untyped_id_params": [],
        "uuid_typing_rate_pct": 0.0,
        "uuid_posture": "NO_ID_PATH_PARAMETERS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    id_path_param_count = 0
    uuid_typed_count = 0
    untyped_id_params: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or "/projects" not in path:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete"):
            op_spec = path_item.get(method)
            if not isinstance(op_spec, dict):
                continue

            merged_params: dict[tuple[str, str], dict[str, Any]] = {}
            for src in (path_item.get("parameters"), op_spec.get("parameters")):
                if not isinstance(src, list):
                    continue
                for param in src:
                    if not isinstance(param, dict):
                        continue
                    p_in = str(param.get("in") or "").strip().lower()
                    p_name = str(param.get("name") or "").strip()
                    merged_params[(p_in, p_name)] = param

            for (p_in, p_name), param in merged_params.items():
                if p_in != "path":
                    continue
                name_lower = p_name.lower()
                if not (name_lower == "id" or name_lower.endswith("_id")):
                    continue

                id_path_param_count += 1
                schema = (
                    param.get("schema")
                    if isinstance(param.get("schema"), dict)
                    else {}
                )
                direct_uuid = str(schema.get("format") or "").strip().lower() == "uuid"
                any_of_list = (
                    schema.get("anyOf") if isinstance(schema.get("anyOf"), list) else []
                )
                one_of_list = (
                    schema.get("oneOf") if isinstance(schema.get("oneOf"), list) else []
                )
                composite_uuid = any(
                    isinstance(sub, dict)
                    and str(sub.get("format") or "").strip().lower() == "uuid"
                    for sub in (*any_of_list, *one_of_list)
                )

                if direct_uuid or composite_uuid:
                    uuid_typed_count += 1
                else:
                    untyped_id_params.append(f"{method.upper()} {path}:{p_name}")

    if id_path_param_count == 0:
        return empty_result

    uuid_typing_rate_pct = round(
        (uuid_typed_count / id_path_param_count) * 100.0, 2
    )
    if len(untyped_id_params) == 0:
        uuid_posture = "STRICT_UUID_PATH_CONTRACTS"
    elif uuid_typing_rate_pct >= 50.0:
        uuid_posture = "PARTIAL_UUID_PATH_TYPING"
    else:
        uuid_posture = "WEAK_PATH_ID_TYPING"

    return {
        "id_path_param_count": id_path_param_count,
        "uuid_typed_count": uuid_typed_count,
        "untyped_id_params": untyped_id_params,
        "uuid_typing_rate_pct": uuid_typing_rate_pct,
        "uuid_posture": uuid_posture,
    }


def summarize_projects_security_requirement_coverage(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la cobertura de requisitos de seguridad OpenAPI en operaciones de proyectos."""
    empty_result: dict[str, Any] = {
        "total_operations": 0,
        "secured_operations_count": 0,
        "unsecured_operations": [],
        "security_coverage_pct": 0.0,
        "security_posture": "NO_PROJECTS_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    has_root_sec = bool(
        isinstance(openapi_schema.get("security"), list)
        and any(
            isinstance(s, dict) and len(s) > 0 for s in openapi_schema["security"]
        )
    )

    total_operations = 0
    secured_operations_count = 0
    unsecured_operations: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or "/projects" not in path:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete"):
            op_spec = path_item.get(method)
            if not isinstance(op_spec, dict):
                continue

            total_operations += 1
            if "security" in op_spec:
                is_secured = bool(
                    isinstance(op_spec.get("security"), list)
                    and any(
                        isinstance(s, dict) and len(s) > 0
                        for s in op_spec["security"]
                    )
                )
            else:
                is_secured = has_root_sec

            if is_secured:
                secured_operations_count += 1
            else:
                unsecured_operations.append(f"{method.upper()} {path}")

    if total_operations == 0:
        return empty_result

    security_coverage_pct = round(
        (secured_operations_count / total_operations) * 100.0, 2
    )
    if len(unsecured_operations) == 0:
        security_posture = "ENFORCED_SECURITY_CONTRACTS"
    elif security_coverage_pct >= 50.0:
        security_posture = "PARTIAL_SECURITY_COVERAGE"
    else:
        security_posture = "UNPROTECTED_ENDPOINT_EXPOSURE"

    return {
        "total_operations": total_operations,
        "secured_operations_count": secured_operations_count,
        "unsecured_operations": unsecured_operations,
        "security_coverage_pct": security_coverage_pct,
        "security_posture": security_posture,
    }


TYPED_SCHEMA_KEYS = ("$ref", "properties", "allOf", "anyOf", "oneOf", "type")


def summarize_projects_mutation_request_body_contracts(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el tipado de esquemas en requestBody para operaciones de mutación (POST/PUT/PATCH) de proyectos."""
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return {
            "mutation_operations_count": 0,
            "with_request_body_count": 0,
            "typed_request_body_count": 0,
            "untyped_request_body_ops": [],
            "typing_rate_pct": 0.0,
            "request_body_posture": "NO_MUTATION_OPERATIONS",
        }

    mutation_operations_count = 0
    with_request_body_count = 0
    typed_request_body_count = 0
    untyped_request_body_ops: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or "/projects" not in path:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("post", "put", "patch"):
            op_spec = path_item.get(method)
            if not isinstance(op_spec, dict):
                continue

            mutation_operations_count += 1
            if "requestBody" not in op_spec:
                continue

            with_request_body_count += 1
            req_body = (
                op_spec.get("requestBody")
                if isinstance(op_spec.get("requestBody"), dict)
                else {}
            )
            content = (
                req_body.get("content")
                if isinstance(req_body.get("content"), dict)
                else {}
            )

            is_typed = False
            for media_obj in content.values():
                if not isinstance(media_obj, dict):
                    continue
                schema = media_obj.get("schema")
                if isinstance(schema, dict) and any(
                    bool(schema.get(k)) for k in TYPED_SCHEMA_KEYS
                ):
                    is_typed = True
                    break

            if is_typed:
                typed_request_body_count += 1
            else:
                untyped_request_body_ops.append(f"{method.upper()} {path}")

    if mutation_operations_count == 0 or with_request_body_count == 0:
        return {
            "mutation_operations_count": mutation_operations_count,
            "with_request_body_count": with_request_body_count,
            "typed_request_body_count": typed_request_body_count,
            "untyped_request_body_ops": untyped_request_body_ops,
            "typing_rate_pct": 0.0,
            "request_body_posture": "NO_MUTATION_OPERATIONS",
        }

    typing_rate_pct = round(
        (typed_request_body_count / with_request_body_count) * 100.0, 2
    )
    if len(untyped_request_body_ops) == 0:
        request_body_posture = "STRICT_TYPED_MUTATION_BODIES"
    elif typing_rate_pct >= 50.0:
        request_body_posture = "PARTIAL_MUTATION_BODY_TYPING"
    else:
        request_body_posture = "UNTYPED_MUTATION_PAYLOAD_RISK"

    return {
        "mutation_operations_count": mutation_operations_count,
        "with_request_body_count": with_request_body_count,
        "typed_request_body_count": typed_request_body_count,
        "untyped_request_body_ops": untyped_request_body_ops,
        "typing_rate_pct": typing_rate_pct,
        "request_body_posture": request_body_posture,
    }


DEPRECATION_MIGRATION_HINTS = (
    "use ",
    "replace",
    "migrat",
    "instead",
    "sunset",
    "reemplaz",
    "usar ",
)


def summarize_projects_operation_deprecation_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la higiene de ciclo de vida y guías de migración para operaciones deprecadas de proyectos."""
    empty_result: dict[str, Any] = {
        "total_operations": 0,
        "deprecated_operations_count": 0,
        "undocumented_deprecated_ops": [],
        "deprecation_rate_pct": 0.0,
        "deprecation_posture": "NO_PROJECTS_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    total_operations = 0
    deprecated_operations_count = 0
    undocumented_deprecated_ops: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or "/projects" not in path:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete"):
            op_spec = path_item.get(method)
            if not isinstance(op_spec, dict):
                continue

            total_operations += 1
            if op_spec.get("deprecated") is True:
                deprecated_operations_count += 1
                doc_text = f"{op_spec.get('summary') or ''} {op_spec.get('description') or ''}".lower()
                if not any(hint in doc_text for hint in DEPRECATION_MIGRATION_HINTS):
                    undocumented_deprecated_ops.append(f"{method.upper()} {path}")

    if total_operations == 0:
        return empty_result

    deprecation_rate_pct = round(
        (deprecated_operations_count / total_operations) * 100.0, 2
    )
    if len(undocumented_deprecated_ops) > 0:
        deprecation_posture = "UNDOCUMENTED_DEPRECATED_ENDPOINTS"
    elif deprecation_rate_pct > 25.0:
        deprecation_posture = "EXCESSIVE_DEPRECATED_SURFACE"
    else:
        deprecation_posture = "CLEAN_OPERATION_LIFECYCLE"

    return {
        "total_operations": total_operations,
        "deprecated_operations_count": deprecated_operations_count,
        "undocumented_deprecated_ops": undocumented_deprecated_ops,
        "deprecation_rate_pct": deprecation_rate_pct,
        "deprecation_posture": deprecation_posture,
    }


def summarize_projects_error_response_contract_coverage(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la cobertura de contratos de respuesta de error (4xx/404/409/422/default) en endpoints de proyectos (PMI §10.2)."""
    empty_result: dict[str, Any] = {
        "total_projects_operations": 0,
        "documented_error_operations_count": 0,
        "missing_error_contract_operations": [],
        "error_contract_coverage_pct": 100.0,
        "is_error_contract_compliant": True,
        "error_contract_posture": "NO_PROJECTS_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    total_projects_operations = 0
    documented_error_operations_count = 0
    missing_error_contract_operations: list[str] = []

    for path_str, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path_str, str) or "/projects" not in path_str:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete"):
            op_obj = path_item.get(method)
            if not isinstance(op_obj, dict):
                continue

            total_projects_operations += 1
            op_key = f"{method.upper()} {path_str}"
            responses = (
                op_obj.get("responses")
                if isinstance(op_obj.get("responses"), dict)
                else {}
            )
            status_keys = {str(k).strip().lower() for k in responses.keys()}

            has_any_error = bool(
                status_keys
                & {"400", "401", "403", "404", "409", "422", "500", "default"}
            ) or any(k.startswith("4") for k in status_keys)

            has_param_error = True
            if "{" in path_str:
                has_param_error = bool(status_keys & {"404", "422", "default"})

            has_mutation_error = True
            if method in {"post", "put", "patch", "delete"}:
                has_mutation_error = bool(
                    status_keys & {"400", "409", "422", "default"}
                )

            if has_any_error and has_param_error and has_mutation_error:
                documented_error_operations_count += 1
            else:
                missing_error_contract_operations.append(op_key)

    if total_projects_operations == 0:
        return empty_result

    missing_sorted = sorted(missing_error_contract_operations)
    error_contract_coverage_pct = round(
        (documented_error_operations_count / total_projects_operations) * 100.0, 2
    )
    is_error_contract_compliant = len(missing_sorted) == 0
    error_contract_posture = (
        "MISSING_ERROR_RESPONSE_CONTRACTS"
        if len(missing_sorted) > 0
        else "COMPLETE_ERROR_RESPONSE_CONTRACTS"
    )

    return {
        "total_projects_operations": total_projects_operations,
        "documented_error_operations_count": documented_error_operations_count,
        "missing_error_contract_operations": missing_sorted,
        "error_contract_coverage_pct": error_contract_coverage_pct,
        "is_error_contract_compliant": is_error_contract_compliant,
        "error_contract_posture": error_contract_posture,
    }


def summarize_projects_mutation_success_status_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la semántica de códigos HTTP de éxito (200/201/202/204) en operaciones de mutación de proyectos (PMI §4.6)."""
    empty_result: dict[str, Any] = {
        "total_mutation_operations": 0,
        "valid_mutation_operations_count": 0,
        "missing_success_status_operations": [],
        "semantic_status_mismatch_operations": [],
        "hygiene_rate_pct": 100.0,
        "is_mutation_status_compliant": True,
        "mutation_status_posture": "NO_MUTATION_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    total_mutation_operations = 0
    valid_mutation_operations_count = 0
    missing_success_status_operations: list[str] = []
    semantic_status_mismatch_operations: list[str] = []

    for path_str, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path_str, str) or "/projects" not in path_str:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("post", "put", "patch", "delete"):
            op_obj = path_item.get(method)
            if not isinstance(op_obj, dict):
                continue

            total_mutation_operations += 1
            op_key = f"{method.upper()} {path_str}"
            responses = (
                op_obj.get("responses")
                if isinstance(op_obj.get("responses"), dict)
                else {}
            )
            status_keys = {str(k).strip() for k in responses.keys()}
            success_keys = status_keys & {"200", "201", "202", "204"}

            if len(success_keys) == 0:
                missing_success_status_operations.append(op_key)
                continue

            is_mismatch = False
            if method == "delete" and (
                "201" in status_keys or not (status_keys & {"200", "202", "204"})
            ):
                is_mismatch = True
            elif method in {"put", "patch"} and not (
                status_keys & {"200", "202", "204"}
            ):
                is_mismatch = True

            if is_mismatch:
                semantic_status_mismatch_operations.append(op_key)
            else:
                valid_mutation_operations_count += 1

    if total_mutation_operations == 0:
        return empty_result

    missing_sorted = sorted(missing_success_status_operations)
    mismatch_sorted = sorted(semantic_status_mismatch_operations)
    hygiene_rate_pct = round(
        (valid_mutation_operations_count / total_mutation_operations) * 100.0, 2
    )
    is_mutation_status_compliant = (
        len(missing_sorted) == 0 and len(mismatch_sorted) == 0
    )

    if len(missing_sorted) > 0:
        mutation_status_posture = "MISSING_SUCCESS_STATUS_CONTRACT"
    elif len(mismatch_sorted) > 0:
        mutation_status_posture = "SEMANTIC_STATUS_CODE_MISMATCH"
    else:
        mutation_status_posture = "CLEAN_MUTATION_STATUS_CONTRACTS"

    return {
        "total_mutation_operations": total_mutation_operations,
        "valid_mutation_operations_count": valid_mutation_operations_count,
        "missing_success_status_operations": missing_sorted,
        "semantic_status_mismatch_operations": mismatch_sorted,
        "hygiene_rate_pct": hygiene_rate_pct,
        "is_mutation_status_compliant": is_mutation_status_compliant,
        "mutation_status_posture": mutation_status_posture,
    }


def summarize_projects_operation_metadata_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la unicidad de operationId y la higiene de summary/description y tags en endpoints de proyectos (PMI §10.2)."""
    empty_result: dict[str, Any] = {
        "total_operations": 0,
        "missing_operation_id_ops": [],
        "duplicate_operation_ids": [],
        "missing_summary_ops": [],
        "untagged_ops": [],
        "is_metadata_hygiene_compliant": True,
        "metadata_hygiene_posture": "NO_PROJECTS_OPERATIONS",
    }
    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return empty_result

    total_operations = 0
    missing_operation_id_ops: list[str] = []
    op_id_counts: dict[str, int] = {}
    missing_summary_ops: list[str] = []
    untagged_ops: list[str] = []

    for path_str, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path_str, str) or "/projects" not in path_str:
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete"):
            op_obj = path_item.get(method)
            if not isinstance(op_obj, dict):
                continue

            total_operations += 1
            op_key = f"{method.upper()} {path_str}"
            op_id = str(op_obj.get("operationId") or "").strip()
            summary = str(
                op_obj.get("summary") or op_obj.get("description") or ""
            ).strip()
            tags = op_obj.get("tags")

            if not op_id:
                missing_operation_id_ops.append(op_key)
            else:
                op_id_counts[op_id] = op_id_counts.get(op_id, 0) + 1

            if len(summary) < 5:
                missing_summary_ops.append(op_key)

            if (
                not isinstance(tags, list)
                or len([t for t in tags if str(t or "").strip()]) == 0
            ):
                untagged_ops.append(op_key)

    if total_operations == 0:
        return empty_result

    missing_op_id_sorted = sorted(missing_operation_id_ops)
    duplicate_operation_ids = sorted(
        [oid for oid, count in op_id_counts.items() if count > 1]
    )
    missing_summary_sorted = sorted(missing_summary_ops)
    untagged_sorted = sorted(untagged_ops)

    is_metadata_hygiene_compliant = (
        len(missing_op_id_sorted) == 0
        and len(duplicate_operation_ids) == 0
        and len(missing_summary_sorted) == 0
        and len(untagged_sorted) == 0
    )

    if len(missing_op_id_sorted) > 0 or len(duplicate_operation_ids) > 0:
        metadata_hygiene_posture = "DUPLICATE_OR_MISSING_OPERATION_ID"
    elif len(missing_summary_sorted) > 0 or len(untagged_sorted) > 0:
        metadata_hygiene_posture = "MISSING_SUMMARY_OR_TAGS"
    else:
        metadata_hygiene_posture = "CLEAN_OPERATION_METADATA"

    return {
        "total_operations": total_operations,
        "missing_operation_id_ops": missing_op_id_sorted,
        "duplicate_operation_ids": duplicate_operation_ids,
        "missing_summary_ops": missing_summary_sorted,
        "untagged_ops": untagged_sorted,
        "is_metadata_hygiene_compliant": is_metadata_hygiene_compliant,
        "metadata_hygiene_posture": metadata_hygiene_posture,
    }


_SNAKE_CASE_QUERY_PARAM_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def summarize_projects_query_parameter_schema_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el tipado de esquema y convención snake_case en parámetros query de endpoints /api/projects (PMI §10.2)."""
    if openapi_schema is None:
        from backend.app import app

        openapi_schema = app.openapi()

    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return {
            "total_query_parameters": 0,
            "operations_with_query_params": 0,
            "non_snake_case_query_params": [],
            "untyped_query_params": [],
            "is_query_contract_hygienic": False,
            "query_hygiene_posture": "NO_QUERY_PARAMETERS_DEFINED",
        }

    total_query_parameters = 0
    operations_with_query_params = 0
    non_snake_case_query_params: list[str] = []
    untyped_query_params: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or not path.startswith("/api/projects"):
            continue
        if not isinstance(path_item, dict):
            continue

        path_params = (
            path_item.get("parameters")
            if isinstance(path_item.get("parameters"), list)
            else []
        )

        for method in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
            op_spec = path_item.get(method)
            if not isinstance(op_spec, dict):
                continue

            op_params = (
                op_spec.get("parameters")
                if isinstance(op_spec.get("parameters"), list)
                else []
            )
            has_query_param = False
            for param in (*path_params, *op_params):
                if not isinstance(param, dict):
                    continue
                if param.get("in") != "query":
                    continue

                total_query_parameters += 1
                has_query_param = True
                name = str(param.get("name") or "")
                param_ref = f"{method.upper()} {path}:{name}"

                if not _SNAKE_CASE_QUERY_PARAM_RE.match(name):
                    non_snake_case_query_params.append(param_ref)

                schema = param.get("schema")
                has_valid_schema = (
                    isinstance(schema, dict)
                    and len(schema) > 0
                    and any(
                        bool(schema.get(k)) for k in ("type", "anyOf", "$ref")
                    )
                )
                if not has_valid_schema:
                    untyped_query_params.append(param_ref)

            if has_query_param:
                operations_with_query_params += 1

    if total_query_parameters == 0:
        query_hygiene_posture = "NO_QUERY_PARAMETERS_DEFINED"
    elif len(untyped_query_params) > 0:
        query_hygiene_posture = "UNTYPED_QUERY_PARAMETER_SCHEMA"
    elif len(non_snake_case_query_params) > 0:
        query_hygiene_posture = "NON_SNAKE_CASE_QUERY_PARAMETER"
    else:
        query_hygiene_posture = "HYGIENIC_QUERY_PARAMETER_CONTRACTS"

    is_query_contract_hygienic = (
        total_query_parameters > 0
        and len(non_snake_case_query_params) == 0
        and len(untyped_query_params) == 0
    )

    return {
        "total_query_parameters": total_query_parameters,
        "operations_with_query_params": operations_with_query_params,
        "non_snake_case_query_params": non_snake_case_query_params,
        "untyped_query_params": untyped_query_params,
        "is_query_contract_hygienic": is_query_contract_hygienic,
        "query_hygiene_posture": query_hygiene_posture,
    }


_SUPPORTED_REQUEST_BODY_MEDIA_TYPES = {
    "application/json",
    "multipart/form-data",
    "application/x-www-form-urlencoded",
}


def summarize_projects_request_body_schema_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el MIME content-type y tipado de esquema en requestBody de endpoints /api/projects (PMI §10.2)."""
    if openapi_schema is None:
        from backend.app import app

        openapi_schema = app.openapi()

    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return {
            "operations_with_request_body": 0,
            "empty_content_operations": [],
            "unsupported_media_types": [],
            "untyped_request_body_schemas": [],
            "is_request_body_hygienic": False,
            "request_body_posture": "NO_REQUEST_BODIES_DEFINED",
        }

    operations_with_request_body = 0
    empty_content_operations: list[str] = []
    unsupported_media_types: list[str] = []
    untyped_request_body_schemas: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or not path.startswith("/api/projects"):
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue

            req_body = op.get("requestBody")
            if not isinstance(req_body, dict) or len(req_body) == 0:
                continue

            operations_with_request_body += 1
            content = (
                req_body.get("content")
                if isinstance(req_body.get("content"), dict)
                else {}
            )
            if len(content) == 0:
                empty_content_operations.append(f"{method.upper()} {path}")
                continue

            for media_type, media_obj in content.items():
                media_ref = f"{method.upper()} {path}:{media_type}"
                if media_type not in _SUPPORTED_REQUEST_BODY_MEDIA_TYPES:
                    unsupported_media_types.append(media_ref)

                schema = (
                    media_obj.get("schema")
                    if isinstance(media_obj, dict)
                    else None
                )
                has_valid_schema = (
                    isinstance(schema, dict)
                    and len(schema) > 0
                    and any(
                        bool(schema.get(k))
                        for k in ("$ref", "type", "anyOf", "oneOf")
                    )
                )
                if not has_valid_schema:
                    untyped_request_body_schemas.append(media_ref)

    if operations_with_request_body == 0:
        request_body_posture = "NO_REQUEST_BODIES_DEFINED"
    elif len(empty_content_operations) > 0:
        request_body_posture = "EMPTY_REQUEST_BODY_CONTENT"
    elif len(untyped_request_body_schemas) > 0:
        request_body_posture = "UNTYPED_REQUEST_BODY_SCHEMA"
    elif len(unsupported_media_types) > 0:
        request_body_posture = "UNSUPPORTED_REQUEST_BODY_MEDIA_TYPE"
    else:
        request_body_posture = "HYGIENIC_REQUEST_BODY_CONTRACTS"

    is_request_body_hygienic = (
        operations_with_request_body > 0
        and len(empty_content_operations) == 0
        and len(unsupported_media_types) == 0
        and len(untyped_request_body_schemas) == 0
    )

    return {
        "operations_with_request_body": operations_with_request_body,
        "empty_content_operations": empty_content_operations,
        "unsupported_media_types": unsupported_media_types,
        "untyped_request_body_schemas": untyped_request_body_schemas,
        "is_request_body_hygienic": is_request_body_hygienic,
        "request_body_posture": request_body_posture,
    }


_STRUCTURAL_RESPONSE_SCHEMA_KEYS = ("$ref", "type", "anyOf", "oneOf", "allOf")


def summarize_projects_json_response_schema_hygiene(
    openapi_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el tipado estructural y referencias ($ref) en respuestas JSON 200/201 de endpoints /api/projects (PMI §10.2)."""
    if openapi_schema is None:
        from backend.app import app

        openapi_schema = app.openapi()

    if not isinstance(openapi_schema, dict) or not isinstance(
        openapi_schema.get("paths"), dict
    ):
        return {
            "json_success_responses_count": 0,
            "ref_backed_responses_count": 0,
            "empty_json_response_schemas": [],
            "untyped_json_response_schemas": [],
            "is_json_response_hygienic": False,
            "response_schema_posture": "NO_JSON_SUCCESS_RESPONSES",
        }

    json_success_responses_count = 0
    ref_backed_responses_count = 0
    empty_json_response_schemas: list[str] = []
    untyped_json_response_schemas: list[str] = []

    for path, path_item in sorted(openapi_schema["paths"].items()):
        if not isinstance(path, str) or not path.startswith("/api/projects"):
            continue
        if not isinstance(path_item, dict):
            continue

        for method in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
            op = path_item.get(method)
            if not isinstance(op, dict):
                continue

            responses = (
                op.get("responses")
                if isinstance(op.get("responses"), dict)
                else {}
            )
            for status_code in ("200", "201"):
                resp = responses.get(status_code)
                if not isinstance(resp, dict):
                    continue
                content = (
                    resp.get("content")
                    if isinstance(resp.get("content"), dict)
                    else {}
                )
                if "application/json" not in content:
                    continue

                json_success_responses_count += 1
                resp_ref = f"{method.upper()} {path}:{status_code}"
                json_media = content.get("application/json")
                schema = (
                    json_media.get("schema")
                    if isinstance(json_media, dict)
                    else None
                )

                if not isinstance(schema, dict) or len(schema) == 0:
                    empty_json_response_schemas.append(resp_ref)
                    continue

                if not any(
                    bool(schema.get(k))
                    for k in _STRUCTURAL_RESPONSE_SCHEMA_KEYS
                ):
                    untyped_json_response_schemas.append(resp_ref)

                if bool(schema.get("$ref")):
                    ref_backed_responses_count += 1

    if json_success_responses_count == 0:
        response_schema_posture = "NO_JSON_SUCCESS_RESPONSES"
    elif len(empty_json_response_schemas) > 0:
        response_schema_posture = "EMPTY_JSON_RESPONSE_SCHEMA"
    elif len(untyped_json_response_schemas) > 0:
        response_schema_posture = "UNTYPED_JSON_RESPONSE_SCHEMA"
    else:
        response_schema_posture = "HYGIENIC_JSON_RESPONSE_CONTRACTS"

    is_json_response_hygienic = (
        json_success_responses_count > 0
        and len(empty_json_response_schemas) == 0
        and len(untyped_json_response_schemas) == 0
    )

    return {
        "json_success_responses_count": json_success_responses_count,
        "ref_backed_responses_count": ref_backed_responses_count,
        "empty_json_response_schemas": empty_json_response_schemas,
        "untyped_json_response_schemas": untyped_json_response_schemas,
        "is_json_response_hygienic": is_json_response_hygienic,
        "response_schema_posture": response_schema_posture,
    }


def summarize_projects_security_scheme_hygiene(
    openapi_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la higiene de esquemas de seguridad y protección de mutaciones en endpoints /api/projects o /projects."""
    if not isinstance(openapi_schema, Mapping):
        return {
            "evaluated_operation_count": 0,
            "defined_security_schemes": [],
            "has_global_security": False,
            "explicit_security_ops": [],
            "public_override_ops": [],
            "auth_error_documented_ops": [],
            "unprotected_write_ops": [],
            "undefined_scheme_refs": [],
            "is_hygienic": True,
        }

    components = openapi_schema.get("components")
    sec_schemes = (
        components.get("securitySchemes")
        if isinstance(components, Mapping)
        and isinstance(components.get("securitySchemes"), Mapping)
        else {}
    )
    defined_security_schemes = sorted(str(k) for k in sec_schemes.keys())
    has_global_security = bool(openapi_schema.get("security"))

    evaluated_operation_count = 0
    explicit_security_ops: list[str] = []
    public_override_ops: list[str] = []
    auth_error_documented_ops: list[str] = []
    unprotected_write_ops: list[str] = []
    undefined_scheme_refs: list[str] = []

    paths = openapi_schema.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                evaluated_operation_count += 1
                op_key = f"{method.upper()} {path}"
                op_security = op.get("security")

                if isinstance(op_security, list) and len(op_security) > 0:
                    explicit_security_ops.append(op_key)
                if "security" in op and op_security == []:
                    public_override_ops.append(op_key)
                    if method in {"post", "put", "patch", "delete"}:
                        unprotected_write_ops.append(op_key)

                responses = (
                    op.get("responses")
                    if isinstance(op.get("responses"), Mapping)
                    else {}
                )
                resp_keys = {str(k) for k in responses.keys()}
                if "401" in resp_keys or "403" in resp_keys:
                    auth_error_documented_ops.append(op_key)

                for sec_req in (
                    op_security if isinstance(op_security, list) else []
                ):
                    if isinstance(sec_req, Mapping):
                        for scheme_name in sec_req.keys():
                            if (
                                len(defined_security_schemes) > 0
                                and str(scheme_name)
                                not in defined_security_schemes
                            ):
                                undefined_scheme_refs.append(
                                    f"{op_key}:{scheme_name}"
                                )

    is_hygienic = (
        len(unprotected_write_ops) == 0 and len(undefined_scheme_refs) == 0
    )

    return {
        "evaluated_operation_count": evaluated_operation_count,
        "defined_security_schemes": defined_security_schemes,
        "has_global_security": has_global_security,
        "explicit_security_ops": explicit_security_ops,
        "public_override_ops": public_override_ops,
        "auth_error_documented_ops": auth_error_documented_ops,
        "unprotected_write_ops": unprotected_write_ops,
        "undefined_scheme_refs": undefined_scheme_refs,
        "is_hygienic": is_hygienic,
    }


def summarize_projects_deprecation_and_sunset_hygiene(
    openapi_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la gobernanza de deprecación, fecha sunset (x-sunset) y guía de migración en endpoints /api/projects o /projects."""
    if not isinstance(openapi_schema, Mapping):
        return {
            "evaluated_operation_count": 0,
            "active_ops": [],
            "deprecated_ops": [],
            "deprecated_missing_sunset_ops": [],
            "deprecated_missing_migration_guide_ops": [],
            "inconsistent_sunset_on_active_ops": [],
            "is_hygienic": True,
        }

    evaluated_operation_count = 0
    active_ops: list[str] = []
    deprecated_ops: list[str] = []
    deprecated_missing_sunset_ops: list[str] = []
    deprecated_missing_migration_guide_ops: list[str] = []
    inconsistent_sunset_on_active_ops: list[str] = []

    paths = openapi_schema.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                evaluated_operation_count += 1
                op_key = f"{method.upper()} {path}"
                is_deprecated = bool(op.get("deprecated"))
                sunset_str = str(op.get("x-sunset") or "").strip()
                replacement_str = str(
                    op.get("x-replacement-path") or ""
                ).strip()
                desc_lower = str(op.get("description") or "").lower()

                if is_deprecated:
                    deprecated_ops.append(op_key)
                    if not sunset_str:
                        deprecated_missing_sunset_ops.append(op_key)
                    if not replacement_str and not any(
                        token in desc_lower
                        for token in ("use ", "replace", "migrat")
                    ):
                        deprecated_missing_migration_guide_ops.append(op_key)
                else:
                    active_ops.append(op_key)
                    if sunset_str:
                        inconsistent_sunset_on_active_ops.append(op_key)

    is_hygienic = (
        len(deprecated_missing_sunset_ops) == 0
        and len(deprecated_missing_migration_guide_ops) == 0
        and len(inconsistent_sunset_on_active_ops) == 0
    )

    return {
        "evaluated_operation_count": evaluated_operation_count,
        "active_ops": active_ops,
        "deprecated_ops": deprecated_ops,
        "deprecated_missing_sunset_ops": deprecated_missing_sunset_ops,
        "deprecated_missing_migration_guide_ops": deprecated_missing_migration_guide_ops,
        "inconsistent_sunset_on_active_ops": inconsistent_sunset_on_active_ops,
        "is_hygienic": is_hygienic,
    }


def summarize_projects_error_response_contract_hygiene(
    openapi_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la documentación de respuestas de error (4xx/5xx/default) en endpoints /api/projects o /projects."""
    if not isinstance(openapi_schema, Mapping):
        return {
            "evaluated_operation_count": 0,
            "ops_with_error_responses": [],
            "ops_missing_all_error_responses": [],
            "parameterized_ops_missing_404": [],
            "input_ops_missing_validation_error": [],
            "undescribed_error_responses": [],
            "is_hygienic": True,
        }

    evaluated_operation_count = 0
    ops_with_error_responses: list[str] = []
    ops_missing_all_error_responses: list[str] = []
    parameterized_ops_missing_404: list[str] = []
    input_ops_missing_validation_error: list[str] = []
    undescribed_error_responses: list[str] = []

    paths = openapi_schema.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                evaluated_operation_count += 1
                op_key = f"{method.upper()} {path}"
                raw_responses = (
                    op.get("responses")
                    if isinstance(op.get("responses"), Mapping)
                    else {}
                )
                responses = {str(k): v for k, v in raw_responses.items()}

                has_error = any(
                    code.startswith(("4", "5")) or code == "default"
                    for code in responses.keys()
                )
                if has_error:
                    ops_with_error_responses.append(op_key)
                else:
                    ops_missing_all_error_responses.append(op_key)

                if (
                    "{" in path
                    and "}" in path
                    and "404" not in responses
                    and "default" not in responses
                ):
                    parameterized_ops_missing_404.append(op_key)

                if (
                    (
                        isinstance(op.get("requestBody"), Mapping)
                        or bool(op.get("parameters"))
                    )
                    and "422" not in responses
                    and "400" not in responses
                    and "default" not in responses
                ):
                    input_ops_missing_validation_error.append(op_key)

                for code, resp_obj in responses.items():
                    if str(code).startswith(("4", "5")):
                        if (
                            isinstance(resp_obj, Mapping)
                            and not str(resp_obj.get("description") or "").strip()
                        ):
                            undescribed_error_responses.append(
                                f"{op_key}:{code}"
                            )

    is_hygienic = (
        len(ops_missing_all_error_responses) == 0
        and len(undescribed_error_responses) == 0
    )

    return {
        "evaluated_operation_count": evaluated_operation_count,
        "ops_with_error_responses": ops_with_error_responses,
        "ops_missing_all_error_responses": ops_missing_all_error_responses,
        "parameterized_ops_missing_404": parameterized_ops_missing_404,
        "input_ops_missing_validation_error": input_ops_missing_validation_error,
        "undescribed_error_responses": undescribed_error_responses,
        "is_hygienic": is_hygienic,
    }


def summarize_projects_mutation_idempotency_and_header_hygiene(
    openapi_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita encabezados de idempotencia, códigos 201/409 y tipado de headers de respuesta en mutaciones /api/projects o /projects."""
    if not isinstance(openapi_schema, Mapping):
        return {
            "evaluated_mutation_count": 0,
            "post_mutation_ops": [],
            "post_ops_with_201_created": [],
            "ops_with_idempotency_header": [],
            "ops_with_conflict_409_response": [],
            "malformed_header_param_ops": [],
            "untyped_response_headers": [],
            "is_hygienic": True,
        }

    evaluated_mutation_count = 0
    post_mutation_ops: list[str] = []
    post_ops_with_201_created: list[str] = []
    ops_with_idempotency_header: list[str] = []
    ops_with_conflict_409_response: list[str] = []
    malformed_header_param_ops: list[str] = []
    untyped_response_headers: list[str] = []

    paths = openapi_schema.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            for method in ("post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                evaluated_mutation_count += 1
                op_key = f"{method.upper()} {path}"
                raw_responses = (
                    op.get("responses")
                    if isinstance(op.get("responses"), Mapping)
                    else {}
                )
                responses = {str(k): v for k, v in raw_responses.items()}
                params = (
                    op.get("parameters")
                    if isinstance(op.get("parameters"), list)
                    else []
                )

                if method == "post":
                    post_mutation_ops.append(op_key)
                    if "201" in responses:
                        post_ops_with_201_created.append(op_key)

                has_malformed_header = False
                has_idempotency_header = False
                for param in params:
                    if (
                        isinstance(param, Mapping)
                        and str(param.get("in") or "").lower() == "header"
                    ):
                        hname = str(param.get("name") or "").strip()
                        if not hname:
                            has_malformed_header = True
                        elif hname.lower() in {
                            "idempotency-key",
                            "x-idempotency-key",
                            "x-request-id",
                        }:
                            has_idempotency_header = True

                if has_malformed_header:
                    malformed_header_param_ops.append(op_key)
                if has_idempotency_header:
                    ops_with_idempotency_header.append(op_key)

                if "409" in responses:
                    ops_with_conflict_409_response.append(op_key)

                for resp_obj in responses.values():
                    if isinstance(resp_obj, Mapping):
                        headers = resp_obj.get("headers")
                        if isinstance(headers, Mapping):
                            for header_name, header_obj in headers.items():
                                if not isinstance(header_obj, Mapping) or (
                                    "schema" not in header_obj
                                    and "$ref" not in header_obj
                                ):
                                    untyped_response_headers.append(
                                        f"{op_key}:{header_name}"
                                    )

    is_hygienic = (
        len(malformed_header_param_ops) == 0
        and len(untyped_response_headers) == 0
    )

    return {
        "evaluated_mutation_count": evaluated_mutation_count,
        "post_mutation_ops": post_mutation_ops,
        "post_ops_with_201_created": post_ops_with_201_created,
        "ops_with_idempotency_header": ops_with_idempotency_header,
        "ops_with_conflict_409_response": ops_with_conflict_409_response,
        "malformed_header_param_ops": malformed_header_param_ops,
        "untyped_response_headers": untyped_response_headers,
        "is_hygienic": is_hygienic,
    }


_CANONICAL_BINARY_EXPORT_TYPES = {
    "application/pdf",
    "text/csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}
_EXPORT_PATH_KEYWORDS = ("export", "pdf", "csv", "xlsx", "download", "report")


def summarize_projects_export_and_binary_response_hygiene(
    openapi_schema: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita las operaciones de exportación/reporte/descarga bajo /api/projects o /projects verificando media types y content-disposition."""
    if not isinstance(openapi_schema, Mapping):
        return {
            "evaluated_export_op_count": 0,
            "export_report_ops": [],
            "binary_stream_export_ops": [],
            "json_export_ops": [],
            "ops_with_content_disposition_header": [],
            "export_ops_missing_content_type": [],
            "mismatched_export_media_type_ops": [],
            "is_hygienic": True,
        }

    export_report_ops: list[str] = []
    binary_stream_export_ops: list[str] = []
    json_export_ops: list[str] = []
    ops_with_content_disposition_header: list[str] = []
    export_ops_missing_content_type: list[str] = []
    mismatched_export_media_type_ops: list[str] = []

    paths = openapi_schema.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            path_lower = path.lower()
            has_export_keyword = any(
                kw in path_lower for kw in _EXPORT_PATH_KEYWORDS
            )

            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                op_key = f"{method.upper()} {path}"
                raw_responses = (
                    op.get("responses")
                    if isinstance(op.get("responses"), Mapping)
                    else {}
                )
                media_types: set[str] = set()
                has_content_disposition = False

                for code, resp_obj in raw_responses.items():
                    if not str(code).startswith("2") or not isinstance(
                        resp_obj, Mapping
                    ):
                        continue
                    content = resp_obj.get("content")
                    if isinstance(content, Mapping):
                        for mtype in content.keys():
                            media_types.add(str(mtype))
                    headers = resp_obj.get("headers")
                    if isinstance(headers, Mapping):
                        if any(
                            str(h).strip().lower() == "content-disposition"
                            for h in headers.keys()
                        ):
                            has_content_disposition = True

                has_binary_type = bool(
                    media_types & _CANONICAL_BINARY_EXPORT_TYPES
                )
                if not (has_export_keyword or has_binary_type):
                    continue

                export_report_ops.append(op_key)
                if len(media_types) == 0:
                    export_ops_missing_content_type.append(op_key)
                if has_binary_type:
                    binary_stream_export_ops.append(op_key)
                if "application/json" in media_types:
                    json_export_ops.append(op_key)
                if has_content_disposition:
                    ops_with_content_disposition_header.append(op_key)
                if (
                    "pdf" in path_lower
                    and len(media_types) > 0
                    and not (
                        {
                            "application/pdf",
                            "application/octet-stream",
                            "application/json",
                        }
                        & media_types
                    )
                ):
                    mismatched_export_media_type_ops.append(op_key)

    is_hygienic = (
        len(export_ops_missing_content_type) == 0
        and len(mismatched_export_media_type_ops) == 0
    )

    return {
        "evaluated_export_op_count": len(export_report_ops),
        "export_report_ops": export_report_ops,
        "binary_stream_export_ops": binary_stream_export_ops,
        "json_export_ops": json_export_ops,
        "ops_with_content_disposition_header": ops_with_content_disposition_header,
        "export_ops_missing_content_type": export_ops_missing_content_type,
        "mismatched_export_media_type_ops": mismatched_export_media_type_ops,
        "is_hygienic": is_hygienic,
    }


_PATH_PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _is_valid_id_schema_node(node: Any) -> bool:
    if not isinstance(node, Mapping):
        return False
    enum_val = node.get("enum")
    has_enum = isinstance(enum_val, list) and len(enum_val) > 0
    return node.get("type") == "string" and (
        node.get("format") == "uuid"
        or bool(node.get("pattern"))
        or has_enum
    )


def _has_uuid_or_constrained_id_schema(schema: Any) -> bool:
    if not isinstance(schema, Mapping):
        return False
    if _is_valid_id_schema_node(schema):
        return True
    for composite_key in ("anyOf", "oneOf"):
        members = schema.get(composite_key)
        if isinstance(members, list) and any(
            _is_valid_id_schema_node(m) for m in members
        ):
            return True
    return False


def summarize_projects_path_parameter_uuid_hygiene(
    openapi: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita la declaración obligatoria y el esquema UUID/restringido de parámetros de ruta {param} en endpoints /api/projects o /projects."""
    if not isinstance(openapi, Mapping):
        return {
            "total_parameterized_operations": 0,
            "total_path_parameters": 0,
            "undeclared_or_optional_path_params": [],
            "untyped_id_path_params": [],
            "is_path_param_hygiene_clean": False,
        }

    total_parameterized_operations = 0
    total_path_parameters = 0
    undeclared_or_optional_path_params: list[str] = []
    untyped_id_path_params: list[str] = []

    paths = openapi.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if not isinstance(path_item, Mapping):
                continue

            placeholders = _PATH_PLACEHOLDER_RE.findall(path)
            if not placeholders:
                continue

            path_params = (
                path_item.get("parameters")
                if isinstance(path_item.get("parameters"), list)
                else []
            )

            for method in ("get", "post", "put", "patch", "delete"):
                op = path_item.get(method)
                if not isinstance(op, Mapping):
                    continue

                total_parameterized_operations += 1
                op_params = (
                    op.get("parameters")
                    if isinstance(op.get("parameters"), list)
                    else []
                )
                merged_params: dict[tuple[str, str], Mapping[str, Any]] = {}
                for p in (*path_params, *op_params):
                    if isinstance(p, Mapping):
                        p_name = str(p.get("name") or "")
                        p_in = str(p.get("in") or "")
                        if p_name and p_in:
                            merged_params[(p_name, p_in)] = p

                for placeholder in placeholders:
                    total_path_parameters += 1
                    param_ref = f"{method.upper()} {path}:{placeholder}"
                    param = merged_params.get((placeholder, "path"))

                    if param is None or param.get("required") is not True:
                        undeclared_or_optional_path_params.append(param_ref)

                    if param is not None and (
                        placeholder == "id" or placeholder.endswith("_id")
                    ):
                        if not _has_uuid_or_constrained_id_schema(
                            param.get("schema")
                        ):
                            untyped_id_path_params.append(param_ref)

    is_path_param_hygiene_clean = bool(
        total_parameterized_operations > 0
        and not undeclared_or_optional_path_params
        and not untyped_id_path_params
    )

    return {
        "total_parameterized_operations": total_parameterized_operations,
        "total_path_parameters": total_path_parameters,
        "undeclared_or_optional_path_params": undeclared_or_optional_path_params,
        "untyped_id_path_params": untyped_id_path_params,
        "is_path_param_hygiene_clean": is_path_param_hygiene_clean,
    }


def _resolve_schema_ref(
    schema: Any, openapi: Mapping[str, Any]
) -> Mapping[str, Any]:
    if not isinstance(schema, Mapping):
        return {}
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        name = ref.rsplit("/", maxsplit=1)[-1]
        components = openapi.get("components")
        schemas = (
            components.get("schemas")
            if isinstance(components, Mapping)
            and isinstance(components.get("schemas"), Mapping)
            else {}
        )
        target = schemas.get(name)
        if isinstance(target, Mapping):
            return target
    return schema


def _has_bounded_max_schema(schema: Any) -> bool:
    if not isinstance(schema, Mapping):
        return False
    if (
        schema.get("maximum") is not None
        or schema.get("exclusiveMaximum") is not None
    ):
        return True
    for composite_key in ("anyOf", "oneOf"):
        members = schema.get(composite_key)
        if isinstance(members, list) and any(
            isinstance(m, Mapping)
            and (
                m.get("maximum") is not None
                or m.get("exclusiveMaximum") is not None
            )
            for m in members
        ):
            return True
    return False


def summarize_projects_collection_pagination_hygiene(
    openapi: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita paginación, límite máximo acotado y envoltorio de respuesta en operaciones GET de colección bajo /api/projects o /projects."""
    if not isinstance(openapi, Mapping):
        return {
            "total_collection_get_operations": 0,
            "unpaginated_collection_operations": [],
            "unbounded_limit_operations": [],
            "bare_array_response_operations": [],
            "is_pagination_hygiene_clean": False,
        }

    total_collection_get_operations = 0
    unpaginated_collection_operations: list[str] = []
    unbounded_limit_operations: list[str] = []
    bare_array_response_operations: list[str] = []

    paths = openapi.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in sorted(paths.items()):
            if not isinstance(path, str) or not (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                continue
            if path.rstrip("/").endswith("}"):
                continue
            if not isinstance(path_item, Mapping):
                continue

            op = path_item.get("get")
            if not isinstance(op, Mapping):
                continue

            responses = (
                op.get("responses")
                if isinstance(op.get("responses"), Mapping)
                else {}
            )
            resp_200 = responses.get("200")
            if not isinstance(resp_200, Mapping):
                continue
            content = (
                resp_200.get("content")
                if isinstance(resp_200.get("content"), Mapping)
                else {}
            )
            json_media = content.get("application/json")
            if not isinstance(json_media, Mapping):
                continue

            resolved_schema = _resolve_schema_ref(
                json_media.get("schema"), openapi
            )
            if not resolved_schema:
                continue

            is_bare_array = resolved_schema.get("type") == "array"
            is_envelope_collection = False
            if (
                not is_bare_array
                and resolved_schema.get("type") in ("object", None)
                and isinstance(resolved_schema.get("properties"), Mapping)
            ):
                props = resolved_schema["properties"]
                for col_key in ("items", "results", "data"):
                    prop_schema = _resolve_schema_ref(
                        props.get(col_key), openapi
                    )
                    if prop_schema.get("type") == "array":
                        is_envelope_collection = True
                        break

            if not (is_bare_array or is_envelope_collection):
                continue

            total_collection_get_operations += 1
            op_key = f"GET {path}"

            path_params = (
                path_item.get("parameters")
                if isinstance(path_item.get("parameters"), list)
                else []
            )
            op_params = (
                op.get("parameters")
                if isinstance(op.get("parameters"), list)
                else []
            )
            query_params: dict[str, Mapping[str, Any]] = {}
            for p in (*path_params, *op_params):
                if isinstance(p, Mapping) and p.get("in") == "query":
                    p_name = str(p.get("name") or "")
                    if p_name:
                        query_params[p_name] = p

            qnames = set(query_params.keys())
            has_pagination_pair = (
                ({"limit", "offset"} <= qnames)
                or ({"page", "page_size"} <= qnames)
                or ({"skip", "limit"} <= qnames)
                or ({"cursor", "limit"} <= qnames)
            )
            if not has_pagination_pair:
                unpaginated_collection_operations.append(op_key)

            has_unbounded_limit = False
            for limit_key in ("limit", "page_size"):
                if limit_key in query_params:
                    param_obj = query_params[limit_key]
                    if not _has_bounded_max_schema(param_obj.get("schema")):
                        has_unbounded_limit = True
                        break
            if has_unbounded_limit:
                unbounded_limit_operations.append(op_key)

            if is_bare_array:
                bare_array_response_operations.append(op_key)

    is_pagination_hygiene_clean = bool(
        total_collection_get_operations > 0
        and not unpaginated_collection_operations
        and not unbounded_limit_operations
        and not bare_array_response_operations
    )

    return {
        "total_collection_get_operations": total_collection_get_operations,
        "unpaginated_collection_operations": unpaginated_collection_operations,
        "unbounded_limit_operations": unbounded_limit_operations,
        "bare_array_response_operations": bare_array_response_operations,
        "is_pagination_hygiene_clean": is_pagination_hygiene_clean,
    }


_NON_STRING_TEMPORAL_TYPES = {
    "integer",
    "number",
    "boolean",
    "array",
    "object",
}
_PROJECT_DOMAIN_SCHEMA_PREFIXES = (
    "Project",
    "Task",
    "Milestone",
    "Sprint",
    "Risk",
    "Issue",
    "Wbs",
    "WBS",
    "Evm",
    "EVM",
    "Charter",
    "Stakeholder",
    "ChangeRequest",
    "Ccb",
    "CCB",
    "Baseline",
    "Deliverable",
    "Phase",
    "Portfolio",
    "Program",
    "Kanban",
    "Gantt",
    "Wiki",
    "AnyDoc",
    "Procurement",
    "Quality",
    "Resource",
    "Retrospective",
    "Lesson",
)
_TEMPORAL_SUFFIXES = ("_at", "_date", "_timestamp", "_deadline")
_TEMPORAL_EXACT_NAMES = {
    "created_at",
    "updated_at",
    "deleted_at",
    "start_date",
    "end_date",
    "due_date",
    "target_date",
    "baseline_start_date",
    "baseline_end_date",
    "approved_at",
    "closed_at",
    "submitted_at",
}


def summarize_projects_datetime_and_temporal_field_hygiene(
    openapi: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita el formato ISO-8601 (date-time / date) de propiedades temporales (*_at, *_date, *_timestamp, *_deadline) en esquemas de proyectos."""
    if not isinstance(openapi, Mapping):
        return {
            "total_temporal_properties_inspected": 0,
            "unformatted_temporal_properties": [],
            "date_only_on_timestamp_properties": [],
            "is_temporal_hygiene_compliant": True,
            "total_temporal_fields": 0,
            "unformatted_datetime_fields": [],
            "unformatted_date_fields": [],
            "non_string_temporal_fields": [],
            "is_temporal_hygiene_clean": False,
        }

    referenced_schemas: set[str] = set()
    paths = openapi.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in paths.items():
            if isinstance(path, str) and (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                referenced_schemas.update(schema_refs(path_item))

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    total_temporal_fields = 0
    unformatted_datetime_fields: list[str] = []
    unformatted_date_fields: list[str] = []
    non_string_temporal_fields: list[str] = []
    unformatted_temporal_properties: list[str] = []
    date_only_on_timestamp_properties: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if (
            "project" not in s_name.lower()
            and not s_name.startswith(_PROJECT_DOMAIN_SCHEMA_PREFIXES)
            and s_name not in referenced_schemas
        ):
            continue
        if not isinstance(schema_obj, Mapping):
            continue
        props = schema_obj.get("properties")
        if not isinstance(props, Mapping):
            continue

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not (
                p_name.endswith(_TEMPORAL_SUFFIXES)
                or p_name in _TEMPORAL_EXACT_NAMES
            ):
                continue
            if not isinstance(prop_schema, Mapping):
                continue

            total_temporal_fields += 1
            field_ref = f"{s_name}.{p_name}"

            composite = prop_schema.get("anyOf") or prop_schema.get("oneOf")
            if isinstance(composite, list):
                raw_branches = [
                    b
                    for b in composite
                    if isinstance(b, Mapping) and b.get("type") != "null"
                ]
            else:
                raw_branches = [prop_schema]

            branches: list[Mapping[str, Any]] = []
            for rb in raw_branches:
                ref = rb.get("$ref")
                if isinstance(ref, str) and ref.startswith(
                    "#/components/schemas/"
                ):
                    ref_target = schemas.get(ref.split("/")[-1])
                    if isinstance(ref_target, Mapping):
                        branches.append(ref_target)
                        continue
                branches.append(rb)

            if any(
                b.get("type") in _NON_STRING_TEMPORAL_TYPES for b in branches
            ):
                non_string_temporal_fields.append(field_ref)

            has_any_iso_format = any(
                b.get("type") == "string"
                and b.get("format") in {"date-time", "date"}
                for b in branches
            )
            if not has_any_iso_format:
                unformatted_temporal_properties.append(field_ref)

            if p_name.endswith(("_at", "_timestamp")):
                if any(b.get("format") == "date" for b in branches):
                    date_only_on_timestamp_properties.append(field_ref)
                has_valid_dt = any(
                    b.get("type") == "string"
                    and b.get("format") == "date-time"
                    for b in branches
                )
                if not has_valid_dt:
                    unformatted_datetime_fields.append(field_ref)
            elif p_name.endswith(("_date", "_deadline")):
                has_valid_date = any(
                    b.get("type") == "string"
                    and b.get("format") in {"date", "date-time"}
                    for b in branches
                )
                if not has_valid_date:
                    unformatted_date_fields.append(field_ref)

    is_temporal_hygiene_clean = bool(
        total_temporal_fields > 0
        and not unformatted_datetime_fields
        and not unformatted_date_fields
        and not non_string_temporal_fields
    )
    unformatted_sorted = sorted(unformatted_temporal_properties)
    date_only_sorted = sorted(date_only_on_timestamp_properties)
    is_temporal_hygiene_compliant = bool(
        len(unformatted_sorted) == 0 and len(date_only_sorted) == 0
    )

    return {
        "total_temporal_properties_inspected": total_temporal_fields,
        "unformatted_temporal_properties": unformatted_sorted,
        "date_only_on_timestamp_properties": date_only_sorted,
        "is_temporal_hygiene_compliant": is_temporal_hygiene_compliant,
        "total_temporal_fields": total_temporal_fields,
        "unformatted_datetime_fields": unformatted_datetime_fields,
        "unformatted_date_fields": unformatted_date_fields,
        "non_string_temporal_fields": non_string_temporal_fields,
        "is_temporal_hygiene_clean": is_temporal_hygiene_clean,
    }


_PERCENTAGE_SUFFIXES = ("_pct", "_percentage")
_MONETARY_SUFFIXES = (
    "_cost",
    "_budget",
    "_amount",
    "_price",
    "_reserve",
    "_fee",
)
_COUNT_SUFFIXES = ("_count",)
_ALL_NUMERIC_DOMAIN_SUFFIXES = (
    _PERCENTAGE_SUFFIXES + _MONETARY_SUFFIXES + _COUNT_SUFFIXES
)


def _has_non_negative_lower_bound(branch: Mapping[str, Any]) -> bool:
    for key in ("minimum", "exclusiveMinimum"):
        val = branch.get(key)
        if (
            isinstance(val, (int, float))
            and not isinstance(val, bool)
            and val >= 0
        ):
            return True
    return False


def _has_both_bounds(branch: Mapping[str, Any]) -> bool:
    has_lower = any(
        isinstance(branch.get(k), (int, float))
        and not isinstance(branch.get(k), bool)
        for k in ("minimum", "exclusiveMinimum")
    )
    has_upper = any(
        isinstance(branch.get(k), (int, float))
        and not isinstance(branch.get(k), bool)
        for k in ("maximum", "exclusiveMaximum")
    )
    return has_lower and has_upper


def summarize_projects_numeric_bounds_and_currency_hygiene(
    openapi: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita cotas numéricas de dominio (porcentajes, montos monetarios y conteos) en esquemas de proyectos."""
    if not isinstance(openapi, Mapping):
        return {
            "total_numeric_domain_fields": 0,
            "unbounded_percentage_fields": [],
            "negative_allowed_monetary_fields": [],
            "non_integer_or_negative_count_fields": [],
            "is_numeric_bounds_hygiene_clean": False,
        }

    referenced_schemas: set[str] = set()
    paths = openapi.get("paths")
    if isinstance(paths, Mapping):
        for path, path_item in paths.items():
            if isinstance(path, str) and (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                referenced_schemas.update(schema_refs(path_item))

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    total_numeric_domain_fields = 0
    unbounded_percentage_fields: list[str] = []
    negative_allowed_monetary_fields: list[str] = []
    non_integer_or_negative_count_fields: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if (
            "project" not in s_name.lower()
            and s_name not in referenced_schemas
        ):
            continue
        if not isinstance(schema_obj, Mapping):
            continue
        props = schema_obj.get("properties")
        if not isinstance(props, Mapping):
            continue

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not p_name.endswith(_ALL_NUMERIC_DOMAIN_SUFFIXES):
                continue
            if not isinstance(prop_schema, Mapping):
                continue

            composite = prop_schema.get("anyOf") or prop_schema.get("oneOf")
            if isinstance(composite, list):
                non_null_branches = [
                    b
                    for b in composite
                    if isinstance(b, Mapping) and b.get("type") != "null"
                ]
            else:
                non_null_branches = [prop_schema]

            numeric_branches = [
                b
                for b in non_null_branches
                if b.get("type") in {"number", "integer"}
            ]
            if not numeric_branches:
                continue

            total_numeric_domain_fields += 1
            field_ref = f"{s_name}.{p_name}"

            if p_name.endswith(_PERCENTAGE_SUFFIXES):
                if not any(_has_both_bounds(b) for b in numeric_branches):
                    unbounded_percentage_fields.append(field_ref)
            elif p_name.endswith(_MONETARY_SUFFIXES):
                if not any(
                    _has_non_negative_lower_bound(b) for b in numeric_branches
                ):
                    negative_allowed_monetary_fields.append(field_ref)
            elif p_name.endswith(_COUNT_SUFFIXES):
                all_integer = all(
                    b.get("type") == "integer" for b in numeric_branches
                )
                has_non_neg = any(
                    _has_non_negative_lower_bound(b) for b in numeric_branches
                )
                if not (all_integer and has_non_neg):
                    non_integer_or_negative_count_fields.append(field_ref)

    is_numeric_bounds_hygiene_clean = bool(
        total_numeric_domain_fields > 0
        and not unbounded_percentage_fields
        and not negative_allowed_monetary_fields
        and not non_integer_or_negative_count_fields
    )

    return {
        "total_numeric_domain_fields": total_numeric_domain_fields,
        "unbounded_percentage_fields": unbounded_percentage_fields,
        "negative_allowed_monetary_fields": negative_allowed_monetary_fields,
        "non_integer_or_negative_count_fields": non_integer_or_negative_count_fields,
        "is_numeric_bounds_hygiene_clean": is_numeric_bounds_hygiene_clean,
    }


_CATEGORICAL_FIELD_TOKENS = (
    "status",
    "estado",
    "priority",
    "prioridad",
    "severity",
    "severidad",
    "health_status",
    "rag_status",
    "salience_class",
    "resolution_mode",
    "decision_status",
)


def _is_valid_enum_list(enum_val: Any) -> bool:
    if not isinstance(enum_val, list) or len(enum_val) == 0:
        return False
    seen: list[tuple[type, Any]] = []
    for item in enum_val:
        if isinstance(item, str) and not item.strip():
            return False
        key = (type(item), item)
        if key in seen:
            return False
        seen.append(key)
    return True


def _has_invalid_enum_in_node(node: Mapping[str, Any]) -> bool:
    if "enum" in node and not _is_valid_enum_list(node.get("enum")):
        return True
    for comp_key in ("anyOf", "oneOf", "allOf"):
        comp = node.get(comp_key)
        if isinstance(comp, list):
            for branch in comp:
                if (
                    isinstance(branch, Mapping)
                    and "enum" in branch
                    and not _is_valid_enum_list(branch.get("enum"))
                ):
                    return True
    return False


def _resolve_ref_schema(
    branch: Mapping[str, Any], schemas: Mapping[str, Any]
) -> Mapping[str, Any] | None:
    ref = branch.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        ref_name = ref.split("/")[-1]
        target = schemas.get(ref_name)
        if isinstance(target, Mapping):
            return target
    return None


def _branch_has_valid_enum(
    branch: Mapping[str, Any], schemas: Mapping[str, Any]
) -> bool:
    if "enum" in branch and _is_valid_enum_list(branch.get("enum")):
        return True
    resolved = _resolve_ref_schema(branch, schemas)
    if resolved is not None:
        if "enum" in resolved and _is_valid_enum_list(resolved.get("enum")):
            return True
        for comp_key in ("anyOf", "oneOf", "allOf"):
            comp = resolved.get(comp_key)
            if isinstance(comp, list):
                for sub in comp:
                    if (
                        isinstance(sub, Mapping)
                        and "enum" in sub
                        and _is_valid_enum_list(sub.get("enum"))
                    ):
                        return True
    return False


def _branch_is_string(
    branch: Mapping[str, Any], schemas: Mapping[str, Any]
) -> tuple[bool, bool]:
    """Retorna (has_string_type, has_string_constraint)."""
    targets: list[Mapping[str, Any]] = [branch]
    resolved = _resolve_ref_schema(branch, schemas)
    if resolved is not None:
        targets.append(resolved)
    has_str = False
    has_constraint = False
    for t in targets:
        if t.get("type") == "string":
            has_str = True
            if any(
                t.get(k) is not None
                for k in ("maxLength", "minLength", "pattern")
            ):
                has_constraint = True
    return has_str, has_constraint


def summarize_projects_enum_and_status_field_hygiene(
    openapi: Mapping[str, Any] | None = None,
    *,
    strict_enum: bool = False,
) -> dict[str, Any]:
    """Audita campos categóricos (status, priority, severity, etc.) y definiciones enum en components.schemas."""
    if not isinstance(openapi, Mapping):
        return {
            "total_categorical_fields": 0,
            "enum_backed_fields_count": 0,
            "constrained_string_fields_count": 0,
            "unconstrained_categorical_fields": [],
            "invalid_enum_definitions": [],
            "is_hygienic": True,
        }

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    referenced_schemas: set[str] = set()
    paths = openapi.get("paths")
    has_paths = isinstance(paths, Mapping) and len(paths) > 0
    if has_paths:
        for path, path_item in paths.items():
            if isinstance(path, str) and (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                referenced_schemas.update(schema_refs(path_item))

    total_categorical_fields = 0
    enum_backed_fields_count = 0
    constrained_string_fields_count = 0
    unconstrained_categorical_fields: list[str] = []
    invalid_enum_definitions: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if not isinstance(schema_obj, Mapping):
            continue
        if (
            has_paths
            and "project" not in s_name.lower()
            and s_name not in referenced_schemas
        ):
            continue

        if _has_invalid_enum_in_node(schema_obj):
            invalid_enum_definitions.append(s_name)

        props = schema_obj.get("properties")
        if not isinstance(props, Mapping):
            continue

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not isinstance(prop_schema, Mapping):
                continue

            field_ref = f"{s_name}.{p_name}"
            if _has_invalid_enum_in_node(prop_schema):
                invalid_enum_definitions.append(field_ref)

            p_lower = p_name.lower()
            if p_lower.startswith("by_") and prop_schema.get("type") == "object":
                continue
            is_categorical = p_lower in _CATEGORICAL_FIELD_TOKENS or any(
                p_lower.endswith(tok) for tok in _CATEGORICAL_FIELD_TOKENS
            )
            if not is_categorical:
                continue

            total_categorical_fields += 1

            composite = (
                prop_schema.get("anyOf")
                or prop_schema.get("oneOf")
                or prop_schema.get("allOf")
            )
            if isinstance(composite, list):
                non_null_branches = [
                    b
                    for b in composite
                    if isinstance(b, Mapping) and b.get("type") != "null"
                ]
            else:
                non_null_branches = [prop_schema]

            if not non_null_branches:
                unconstrained_categorical_fields.append(field_ref)
                continue

            is_enum_backed = any(
                _branch_has_valid_enum(b, schemas) for b in non_null_branches
            )
            if is_enum_backed:
                enum_backed_fields_count += 1
                continue

            branch_str_flags = [
                _branch_is_string(b, schemas) for b in non_null_branches
            ]
            is_ordinal_int = p_lower in {
                "severity",
                "severidad",
                "priority",
                "prioridad",
            } and all(b.get("type") == "integer" for b in non_null_branches)
            has_string_type = (
                any(f[0] for f in branch_str_flags)
                and all(
                    b.get("type")
                    not in {"integer", "number", "boolean", "array", "object"}
                    for b in non_null_branches
                )
            ) or (not strict_enum and is_ordinal_int)
            has_string_constraint = any(f[1] for f in branch_str_flags)

            if has_string_constraint or (not strict_enum and has_string_type):
                constrained_string_fields_count += 1

            if strict_enum or not has_string_type:
                unconstrained_categorical_fields.append(field_ref)

    is_hygienic = bool(
        len(unconstrained_categorical_fields) == 0
        and len(invalid_enum_definitions) == 0
    )

    return {
        "total_categorical_fields": total_categorical_fields,
        "enum_backed_fields_count": enum_backed_fields_count,
        "constrained_string_fields_count": constrained_string_fields_count,
        "unconstrained_categorical_fields": unconstrained_categorical_fields,
        "invalid_enum_definitions": invalid_enum_definitions,
        "is_hygienic": is_hygienic,
    }


_MUTATION_SCHEMA_SUFFIXES = (
    "create",
    "update",
    "upsert",
    "patch",
    "request",
    "input",
    "payload",
)
_EXCLUDED_STRING_FORMATS = {"uuid", "date", "date-time", "binary", "byte"}
_SHORT_STRING_FIELD_TOKENS = (
    "title",
    "titulo",
    "name",
    "nombre",
    "code",
    "codigo",
    "slug",
    "email",
    "phone",
    "telefono",
)


def summarize_projects_request_string_bounds_hygiene(
    openapi: Mapping[str, Any] | None = None,
    *,
    strict_short_field_bounds: bool = False,
    include_all_schemas: bool = False,
) -> dict[str, Any]:
    """Audita cotas maxLength/minLength/pattern en campos string de esquemas de mutación/entrada en OpenAPI."""
    if not isinstance(openapi, Mapping):
        return {
            "evaluated_schemas_count": 0,
            "total_string_fields": 0,
            "bounded_string_fields_count": 0,
            "unbounded_short_string_fields": [],
            "invalid_string_bounds": [],
            "is_hygienic": True,
        }

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    evaluated_schemas_count = 0
    total_string_fields = 0
    bounded_string_fields_count = 0
    unbounded_short_string_fields: list[str] = []
    invalid_string_bounds: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if not isinstance(schema_obj, Mapping):
            continue
        if not include_all_schemas and not s_name.lower().endswith(
            _MUTATION_SCHEMA_SUFFIXES
        ):
            continue

        evaluated_schemas_count += 1
        props = schema_obj.get("properties")
        if not isinstance(props, Mapping):
            continue

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not isinstance(prop_schema, Mapping):
                continue

            composite = (
                prop_schema.get("anyOf")
                or prop_schema.get("oneOf")
                or prop_schema.get("allOf")
            )
            if isinstance(composite, list):
                non_null_branches = [
                    b
                    for b in composite
                    if isinstance(b, Mapping) and b.get("type") != "null"
                ]
            else:
                non_null_branches = [prop_schema]

            if any(
                "enum" in b
                or (
                    _resolve_ref_schema(b, schemas) is not None
                    and "enum" in (_resolve_ref_schema(b, schemas) or {})
                )
                for b in non_null_branches
            ):
                continue

            string_branches = [
                b
                for b in non_null_branches
                if b.get("type") == "string"
                and str(b.get("format") or "").strip().lower()
                not in _EXCLUDED_STRING_FORMATS
            ]
            if not string_branches:
                continue

            total_string_fields += 1
            field_ref = f"{s_name}.{p_name}"

            has_invalid_bounds = False
            has_valid_bound = False
            has_any_short_constraint = False

            for b in string_branches:
                has_max = "maxLength" in b and b.get("maxLength") is not None
                has_min = "minLength" in b and b.get("minLength") is not None
                max_val = b.get("maxLength")
                min_val = b.get("minLength")

                max_ok = (
                    isinstance(max_val, (int, float))
                    and not isinstance(max_val, bool)
                    and max_val > 0
                )
                min_ok = (
                    isinstance(min_val, (int, float))
                    and not isinstance(min_val, bool)
                    and min_val >= 0
                )

                branch_invalid = False
                if has_max and not max_ok:
                    branch_invalid = True
                if has_min and not min_ok:
                    branch_invalid = True
                if has_max and has_min and max_ok and min_ok and min_val > max_val:
                    branch_invalid = True

                if branch_invalid:
                    has_invalid_bounds = True

                pat = b.get("pattern")
                has_pat = isinstance(pat, str) and bool(pat.strip())
                fmt = b.get("format")
                has_fmt = isinstance(fmt, str) and bool(fmt.strip())

                if (has_max and max_ok and not branch_invalid) or has_pat:
                    has_valid_bound = True
                if (has_max and max_ok and not branch_invalid) or has_pat or has_fmt:
                    has_any_short_constraint = True

            if has_invalid_bounds:
                invalid_string_bounds.append(field_ref)

            if has_valid_bound:
                bounded_string_fields_count += 1

            if strict_short_field_bounds:
                p_lower = p_name.lower()
                is_short_field = p_lower in _SHORT_STRING_FIELD_TOKENS or any(
                    p_lower.endswith(f"_{tok}") or p_lower.endswith(tok)
                    for tok in _SHORT_STRING_FIELD_TOKENS
                )
                if is_short_field and not has_any_short_constraint:
                    unbounded_short_string_fields.append(field_ref)

    is_hygienic = bool(
        len(unbounded_short_string_fields) == 0
        and len(invalid_string_bounds) == 0
    )

    return {
        "evaluated_schemas_count": evaluated_schemas_count,
        "total_string_fields": total_string_fields,
        "bounded_string_fields_count": bounded_string_fields_count,
        "unbounded_short_string_fields": unbounded_short_string_fields,
        "invalid_string_bounds": invalid_string_bounds,
        "is_hygienic": is_hygienic,
    }


_ARRAY_MUTATION_SCHEMA_SUFFIXES = (
    "create",
    "update",
    "upsert",
    "patch",
    "request",
    "input",
    "payload",
    "bulk",
    "batch",
)
_VALID_ITEMS_KEYS = ("type", "$ref", "anyOf", "oneOf", "allOf")


def summarize_projects_array_property_hygiene(
    openapi: Mapping[str, Any] | None = None,
    *,
    strict_request_max_items: bool = False,
    include_all_schemas: bool = False,
) -> dict[str, Any]:
    """Audita propiedades de tipo array (items, minItems, maxItems, uniqueItems) en esquemas OpenAPI."""
    if not isinstance(openapi, Mapping):
        return {
            "evaluated_schemas_count": 0,
            "total_array_fields": 0,
            "bounded_or_unique_arrays_count": 0,
            "missing_items_schema_fields": [],
            "invalid_array_bounds": [],
            "unbounded_request_array_fields": [],
            "is_hygienic": True,
        }

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    referenced_schemas: set[str] = set()
    paths = openapi.get("paths")
    has_paths = isinstance(paths, Mapping) and len(paths) > 0
    if has_paths:
        for path, path_item in paths.items():
            if isinstance(path, str) and (
                path.startswith("/api/projects") or path.startswith("/projects")
            ):
                referenced_schemas.update(schema_refs(path_item))

    evaluated_schemas_count = 0
    total_array_fields = 0
    bounded_or_unique_arrays_count = 0
    missing_items_schema_fields: list[str] = []
    invalid_array_bounds: list[str] = []
    unbounded_request_array_fields: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if not isinstance(schema_obj, Mapping):
            continue
        if (
            has_paths
            and not include_all_schemas
            and "project" not in s_name.lower()
            and s_name not in referenced_schemas
        ):
            continue
        if not include_all_schemas and not s_name.lower().endswith(
            _ARRAY_MUTATION_SCHEMA_SUFFIXES
        ):
            continue

        evaluated_schemas_count += 1
        props = schema_obj.get("properties")
        if not isinstance(props, Mapping):
            continue

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not isinstance(prop_schema, Mapping):
                continue

            composite = (
                prop_schema.get("anyOf")
                or prop_schema.get("oneOf")
                or prop_schema.get("allOf")
            )
            if isinstance(composite, list):
                non_null_branches = [
                    b
                    for b in composite
                    if isinstance(b, Mapping) and b.get("type") != "null"
                ]
            else:
                non_null_branches = [prop_schema]

            array_branches = [
                b for b in non_null_branches if b.get("type") == "array"
            ]
            if not array_branches:
                continue

            total_array_fields += 1
            field_ref = f"{s_name}.{p_name}"

            has_missing_items = False
            has_invalid_bounds = False
            has_valid_max_items = False
            has_unique_items = False

            for b in array_branches:
                items_obj = b.get("items")
                items_valid = (
                    isinstance(items_obj, Mapping)
                    and len(items_obj) > 0
                    and any(
                        items_obj.get(k) is not None for k in _VALID_ITEMS_KEYS
                    )
                )
                if not items_valid:
                    has_missing_items = True

                has_max = "maxItems" in b and b.get("maxItems") is not None
                has_min = "minItems" in b and b.get("minItems") is not None
                max_val = b.get("maxItems")
                min_val = b.get("minItems")

                max_ok = (
                    isinstance(max_val, (int, float))
                    and not isinstance(max_val, bool)
                    and max_val > 0
                )
                min_ok = (
                    isinstance(min_val, (int, float))
                    and not isinstance(min_val, bool)
                    and min_val >= 0
                )

                branch_invalid = False
                if has_max and not max_ok:
                    branch_invalid = True
                if has_min and not min_ok:
                    branch_invalid = True
                if (
                    has_max
                    and has_min
                    and max_ok
                    and min_ok
                    and min_val > max_val
                ):
                    branch_invalid = True

                if branch_invalid:
                    has_invalid_bounds = True

                if has_max and max_ok and not branch_invalid:
                    has_valid_max_items = True
                if b.get("uniqueItems") is True:
                    has_unique_items = True

            if has_missing_items:
                missing_items_schema_fields.append(field_ref)
            if has_invalid_bounds:
                invalid_array_bounds.append(field_ref)
            if has_valid_max_items or has_unique_items:
                bounded_or_unique_arrays_count += 1
            if strict_request_max_items and not has_valid_max_items:
                unbounded_request_array_fields.append(field_ref)

    is_hygienic = bool(
        len(missing_items_schema_fields) == 0
        and len(invalid_array_bounds) == 0
        and len(unbounded_request_array_fields) == 0
    )

    return {
        "evaluated_schemas_count": evaluated_schemas_count,
        "total_array_fields": total_array_fields,
        "bounded_or_unique_arrays_count": bounded_or_unique_arrays_count,
        "missing_items_schema_fields": missing_items_schema_fields,
        "invalid_array_bounds": invalid_array_bounds,
        "unbounded_request_array_fields": unbounded_request_array_fields,
        "is_hygienic": is_hygienic,
    }


def _is_branch_compatible_with_default(
    branch: Mapping[str, Any],
    default_val: Any,
    schemas: Mapping[str, Any],
) -> bool:
    resolved = _resolve_ref_schema(branch, schemas)
    if resolved is not None:
        return _is_schema_node_compatible_with_default(
            resolved, default_val, schemas
        )

    if isinstance(branch.get("enum"), list):
        if default_val not in branch["enum"]:
            return False

    if "const" in branch and default_val != branch.get("const"):
        return False

    b_type = branch.get("type")
    if b_type == "string":
        return isinstance(default_val, str)
    if b_type == "boolean":
        return isinstance(default_val, bool)
    if b_type == "integer":
        return isinstance(default_val, int) and not isinstance(default_val, bool)
    if b_type == "number":
        return isinstance(default_val, (int, float)) and not isinstance(
            default_val, bool
        )
    if b_type == "array":
        return isinstance(default_val, list)
    if b_type == "object":
        return isinstance(default_val, Mapping)
    return True


def _is_schema_node_compatible_with_default(
    node: Mapping[str, Any],
    default_val: Any,
    schemas: Mapping[str, Any],
) -> bool:
    composite = node.get("anyOf") or node.get("oneOf") or node.get("allOf")
    if isinstance(composite, list):
        non_null_branches = [
            b
            for b in composite
            if isinstance(b, Mapping) and b.get("type") != "null"
        ]
    else:
        non_null_branches = [node]

    if not non_null_branches:
        return False
    return any(
        _is_branch_compatible_with_default(b, default_val, schemas)
        for b in non_null_branches
    )


def summarize_projects_schema_required_and_default_hygiene(
    openapi: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Audita coherencia entre listas required, properties y valores default en components.schemas."""
    if not isinstance(openapi, Mapping):
        return {
            "evaluated_schemas_count": 0,
            "total_required_declarations": 0,
            "malformed_required_lists": [],
            "dangling_required_properties": [],
            "contradictory_required_null_defaults": [],
            "type_mismatched_defaults": [],
            "is_hygienic": True,
        }

    components = openapi.get("components")
    schemas = (
        components.get("schemas")
        if isinstance(components, Mapping)
        and isinstance(components.get("schemas"), Mapping)
        else {}
    )

    evaluated_schemas_count = 0
    total_required_declarations = 0
    malformed_required_lists: list[str] = []
    dangling_required_properties: list[str] = []
    contradictory_required_null_defaults: list[str] = []
    type_mismatched_defaults: list[str] = []

    for schema_name, schema_obj in sorted(schemas.items()):
        s_name = str(schema_name)
        if not isinstance(schema_obj, Mapping):
            continue

        props_raw = schema_obj.get("properties")
        has_props = isinstance(props_raw, Mapping)
        if not (has_props or schema_obj.get("type") == "object"):
            continue

        evaluated_schemas_count += 1
        props: Mapping[str, Any] = props_raw if has_props else {}

        if "required" in schema_obj:
            req_val = schema_obj.get("required")
            if not isinstance(req_val, list) or len(req_val) == 0:
                malformed_required_lists.append(s_name)
            else:
                seen_reqs: set[str] = set()
                is_malformed = False
                for item in req_val:
                    if not isinstance(item, str) or not item.strip():
                        is_malformed = True
                        continue
                    if item in seen_reqs:
                        is_malformed = True
                        continue
                    seen_reqs.add(item)
                    total_required_declarations += 1
                    req_ref = f"{s_name}.{item}"
                    if item not in props:
                        dangling_required_properties.append(req_ref)
                    else:
                        prop_def = props.get(item)
                        if (
                            isinstance(prop_def, Mapping)
                            and "default" in prop_def
                            and prop_def.get("default") is None
                        ):
                            contradictory_required_null_defaults.append(req_ref)
                if is_malformed:
                    malformed_required_lists.append(s_name)

        for prop_name, prop_schema in sorted(props.items()):
            p_name = str(prop_name)
            if not isinstance(prop_schema, Mapping):
                continue
            if "default" not in prop_schema or prop_schema.get("default") is None:
                continue

            default_val = prop_schema.get("default")
            if not _is_schema_node_compatible_with_default(
                prop_schema, default_val, schemas
            ):
                type_mismatched_defaults.append(f"{s_name}.{p_name}")

    is_hygienic = bool(
        len(malformed_required_lists) == 0
        and len(dangling_required_properties) == 0
        and len(contradictory_required_null_defaults) == 0
        and len(type_mismatched_defaults) == 0
    )

    return {
        "evaluated_schemas_count": evaluated_schemas_count,
        "total_required_declarations": total_required_declarations,
        "malformed_required_lists": malformed_required_lists,
        "dangling_required_properties": dangling_required_properties,
        "contradictory_required_null_defaults": contradictory_required_null_defaults,
        "type_mismatched_defaults": type_mismatched_defaults,
        "is_hygienic": is_hygienic,
    }


def _collect_non_null_branch_schemas(
    prop_schema: Mapping[str, Any],
    all_schemas: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    """Extrae ramas no nulas de un esquema de propiedad (incluyendo anyOf/oneOf y $ref)."""
    branches: list[Mapping[str, Any]] = []
    composite = prop_schema.get("anyOf") or prop_schema.get("oneOf")
    candidates = composite if isinstance(composite, list) else [prop_schema]
    for cand in candidates:
        if not isinstance(cand, Mapping):
            continue
        if cand.get("type") == "null":
            continue
        ref = cand.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            ref_name = ref.split("/")[-1]
            resolved = all_schemas.get(ref_name)
            if isinstance(resolved, Mapping):
                branches.append(resolved)
                continue
        branches.append(cand)
    return branches


def summarize_projects_uuid_and_identifier_field_hygiene(
    openapi_schema: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Audita la higiene de tipos y formato UUID en campos identificadores de esquemas OpenAPI de proyectos."""
    if openapi_schema is None:
        from backend.app import app

        schema_dict: Mapping[str, Any] = app.openapi()
    else:
        schema_dict = openapi_schema

    referenced_schemas: set[str] = set()
    paths = schema_dict.get("paths", {})
    if isinstance(paths, Mapping):
        for path, methods in paths.items():
            if not str(path).startswith(PROJECT_PREFIX) or not isinstance(methods, Mapping):
                continue
            for method, operation in methods.items():
                if str(method).lower() not in HTTP_METHODS or not isinstance(operation, Mapping):
                    continue
                for ref in schema_refs(operation):
                    referenced_schemas.add(ref)

    components = schema_dict.get("components", {})
    schemas = components.get("schemas", {}) if isinstance(components, Mapping) else {}

    if isinstance(schemas, Mapping) and referenced_schemas:
        queue = list(referenced_schemas)
        while queue:
            current = queue.pop()
            s_obj = schemas.get(current)
            if isinstance(s_obj, Mapping):
                for nested_ref in schema_refs(dict(s_obj)):
                    if nested_ref not in referenced_schemas:
                        referenced_schemas.add(nested_ref)
                        queue.append(nested_ref)

    total_identifier_properties_inspected = 0
    uuid_formatted_properties: list[str] = []
    plain_string_identifier_properties: list[str] = []
    non_string_identifier_properties: list[str] = []

    if isinstance(schemas, Mapping):
        for s_name in sorted(schemas.keys()):
            s_obj = schemas[s_name]
            if not isinstance(s_obj, Mapping):
                continue
            is_proj = (
                "project" in s_name.lower()
                or s_name.startswith(_PROJECT_DOMAIN_SCHEMA_PREFIXES)
                or s_name in referenced_schemas
            )
            if not is_proj:
                continue

            props = s_obj.get("properties", {})
            if not isinstance(props, Mapping):
                continue

            for prop_name in sorted(props.keys()):
                prop_schema = props[prop_name]
                if not isinstance(prop_schema, Mapping):
                    continue

                is_identifier = prop_name == "id" or prop_name.endswith(("_id", "_uuid"))
                if not is_identifier:
                    continue

                total_identifier_properties_inspected += 1
                qualified = f"{s_name}.{prop_name}"
                branches = _collect_non_null_branch_schemas(prop_schema, schemas)

                has_uuid_format = any(
                    b.get("type") == "string" and b.get("format") == "uuid"
                    for b in branches
                )
                has_string_type = any(b.get("type") == "string" for b in branches)

                if has_uuid_format:
                    uuid_formatted_properties.append(qualified)
                elif has_string_type:
                    plain_string_identifier_properties.append(qualified)
                else:
                    non_string_identifier_properties.append(qualified)

    return {
        "total_identifier_properties_inspected": total_identifier_properties_inspected,
        "uuid_formatted_properties": sorted(uuid_formatted_properties),
        "plain_string_identifier_properties": sorted(plain_string_identifier_properties),
        "non_string_identifier_properties": sorted(non_string_identifier_properties),
        "is_identifier_type_hygiene_compliant": len(non_string_identifier_properties) == 0,
    }


def summarize_projects_nullable_and_union_branch_hygiene(
    openapi_schema: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Audita la coherencia de ramas en uniones anyOf/oneOf de propiedades de esquemas OpenAPI de proyectos."""
    if openapi_schema is None:
        from backend.app import app

        schema_dict: Mapping[str, Any] = app.openapi()
    else:
        schema_dict = openapi_schema

    referenced_schemas: set[str] = set()
    paths = schema_dict.get("paths", {})
    if isinstance(paths, Mapping):
        for path, methods in paths.items():
            if not str(path).startswith(PROJECT_PREFIX) or not isinstance(methods, Mapping):
                continue
            for method, operation in methods.items():
                if str(method).lower() not in HTTP_METHODS or not isinstance(operation, Mapping):
                    continue
                for ref in schema_refs(operation):
                    referenced_schemas.add(ref)

    components = schema_dict.get("components", {})
    schemas = components.get("schemas", {}) if isinstance(components, Mapping) else {}

    if isinstance(schemas, Mapping) and referenced_schemas:
        queue = list(referenced_schemas)
        while queue:
            current = queue.pop()
            s_obj = schemas.get(current)
            if isinstance(s_obj, Mapping):
                for nested_ref in schema_refs(dict(s_obj)):
                    if nested_ref not in referenced_schemas:
                        referenced_schemas.add(nested_ref)
                        queue.append(nested_ref)

    total_properties_inspected = 0
    total_union_properties = 0
    degenerate_single_branch_unions: list[str] = []
    null_only_unions: list[str] = []
    duplicate_branch_unions: list[str] = []

    if isinstance(schemas, Mapping):
        for s_name in sorted(schemas.keys()):
            s_obj = schemas[s_name]
            if not isinstance(s_obj, Mapping):
                continue
            is_proj = (
                "project" in s_name.lower()
                or s_name.startswith(_PROJECT_DOMAIN_SCHEMA_PREFIXES)
                or s_name in referenced_schemas
            )
            if not is_proj:
                continue

            props = s_obj.get("properties", {})
            if not isinstance(props, Mapping):
                continue

            for prop_name in sorted(props.keys()):
                prop_schema = props[prop_name]
                if not isinstance(prop_schema, Mapping):
                    continue

                total_properties_inspected += 1
                branches = prop_schema.get("anyOf")
                if not isinstance(branches, list):
                    branches = prop_schema.get("oneOf")
                if not isinstance(branches, list):
                    continue

                total_union_properties += 1
                qualified = f"{s_name}.{prop_name}"

                if len(branches) < 2:
                    degenerate_single_branch_unions.append(qualified)

                non_null_count = sum(
                    1
                    for b in branches
                    if isinstance(b, Mapping) and b.get("type") != "null"
                )
                if non_null_count == 0:
                    null_only_unions.append(qualified)

                seen_serialized: set[str] = set()
                has_duplicate = False
                for b in branches:
                    if not isinstance(b, Mapping):
                        continue
                    serialized = json.dumps(dict(b), sort_keys=True)
                    if serialized in seen_serialized:
                        has_duplicate = True
                        break
                    seen_serialized.add(serialized)
                if has_duplicate:
                    duplicate_branch_unions.append(qualified)

    return {
        "total_properties_inspected": total_properties_inspected,
        "total_union_properties": total_union_properties,
        "degenerate_single_branch_unions": sorted(degenerate_single_branch_unions),
        "null_only_unions": sorted(null_only_unions),
        "duplicate_branch_unions": sorted(duplicate_branch_unions),
        "is_union_branch_hygiene_compliant": (
            len(degenerate_single_branch_unions) == 0
            and len(null_only_unions) == 0
            and len(duplicate_branch_unions) == 0
        ),
    }


_QUERY_FILTER_SORT_EXACT_NAMES = frozenset(
    {
        "sort",
        "order",
        "status",
        "state",
        "filter",
        "search",
        "q",
        "query",
        "sede_id",
    }
)
_QUERY_FILTER_SORT_SUFFIXES = ("_status", "_type", "_by", "_id")
_SEARCH_QUERY_PARAM_NAMES = frozenset({"search", "q", "query"})
_MUTATION_HTTP_METHODS = frozenset({"post", "put", "patch", "delete"})


def summarize_projects_query_filter_and_sort_parameter_hygiene(
    openapi_schema: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Audita la higiene de parámetros query de filtrado, ordenamiento, búsqueda y tenant en rutas de proyectos."""
    if openapi_schema is None:
        from backend.app import app

        schema_dict: Mapping[str, Any] = app.openapi()
    else:
        schema_dict = openapi_schema

    total_filter_sort_query_params = 0
    untyped_query_params: list[str] = []
    client_sede_id_mutation_query_params: list[str] = []
    invalid_search_bound_query_params: list[str] = []

    paths = schema_dict.get("paths", {}) if isinstance(schema_dict, Mapping) else {}
    if isinstance(paths, Mapping):
        for path in sorted(paths.keys()):
            path_str = str(path)
            if not path_str.startswith(("/api/projects", "/api/v1/projects", "/projects")):
                continue
            path_item = paths[path]
            if not isinstance(path_item, Mapping):
                continue

            path_params = (
                path_item.get("parameters")
                if isinstance(path_item.get("parameters"), list)
                else []
            )

            for method in ("get", "post", "put", "patch", "delete", "head", "options", "trace"):
                op_spec = path_item.get(method)
                if not isinstance(op_spec, Mapping):
                    continue

                op_params = (
                    op_spec.get("parameters")
                    if isinstance(op_spec.get("parameters"), list)
                    else []
                )

                for param in (*path_params, *op_params):
                    if not isinstance(param, Mapping) or param.get("in") != "query":
                        continue

                    name = str(param.get("name") or "").strip()
                    if not name:
                        continue

                    is_filter_sort = (
                        name in _QUERY_FILTER_SORT_EXACT_NAMES
                        or name.endswith(_QUERY_FILTER_SORT_SUFFIXES)
                    )
                    if not is_filter_sort:
                        continue

                    total_filter_sort_query_params += 1
                    param_ref = f"{method.upper()} {path_str}:{name}"

                    p_schema = param.get("schema")
                    has_type_info = (
                        isinstance(p_schema, Mapping)
                        and any(
                            bool(p_schema.get(k))
                            for k in ("type", "anyOf", "oneOf", "$ref")
                        )
                    )
                    if not has_type_info:
                        untyped_query_params.append(param_ref)

                    if name == "sede_id" and method in _MUTATION_HTTP_METHODS:
                        client_sede_id_mutation_query_params.append(param_ref)

                    if name in _SEARCH_QUERY_PARAM_NAMES and isinstance(p_schema, Mapping):
                        candidates: list[Mapping[str, Any]] = [p_schema]
                        for union_key in ("anyOf", "oneOf"):
                            branches = p_schema.get(union_key)
                            if isinstance(branches, list):
                                candidates.extend(
                                    b for b in branches if isinstance(b, Mapping)
                                )
                        has_invalid_bounds = False
                        for cand in candidates:
                            max_len = cand.get("maxLength")
                            min_len = cand.get("minLength")
                            if (
                                isinstance(max_len, (int, float))
                                and not isinstance(max_len, bool)
                                and max_len <= 0
                            ) or (
                                isinstance(min_len, (int, float))
                                and not isinstance(min_len, bool)
                                and min_len < 0
                            ):
                                has_invalid_bounds = True
                                break
                        if has_invalid_bounds:
                            invalid_search_bound_query_params.append(param_ref)

    return {
        "total_filter_sort_query_params": total_filter_sort_query_params,
        "untyped_query_params": sorted(untyped_query_params),
        "client_sede_id_mutation_query_params": sorted(client_sede_id_mutation_query_params),
        "invalid_search_bound_query_params": sorted(invalid_search_bound_query_params),
        "is_query_filter_sort_hygiene_compliant": (
            len(untyped_query_params) == 0
            and len(client_sede_id_mutation_query_params) == 0
            and len(invalid_search_bound_query_params) == 0
        ),
    }


_AUDITED_HTTP_STATUS_METHODS = ("get", "post", "put", "patch", "delete")


def summarize_projects_http_status_and_success_code_hygiene(
    openapi_schema: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Audita la semántica de códigos HTTP 2xx y respuestas 204/201 en operaciones de proyectos."""
    if openapi_schema is None:
        from backend.app import app

        schema_dict: Mapping[str, Any] = app.openapi()
    else:
        schema_dict = openapi_schema

    total_project_operations = 0
    missing_2xx_response_operations: list[str] = []
    body_on_204_no_content_operations: list[str] = []
    get_with_201_created_operations: list[str] = []

    paths = schema_dict.get("paths", {}) if isinstance(schema_dict, Mapping) else {}
    if isinstance(paths, Mapping):
        for path in sorted(paths.keys()):
            path_str = str(path)
            if not path_str.startswith(("/api/projects", "/api/v1/projects", "/projects")):
                continue
            path_item = paths[path]
            if not isinstance(path_item, Mapping):
                continue

            for method in _AUDITED_HTTP_STATUS_METHODS:
                op_spec = path_item.get(method)
                if not isinstance(op_spec, Mapping):
                    continue

                total_project_operations += 1
                op_ref = f"{method.upper()} {path_str}"
                responses = op_spec.get("responses")
                resp_map = responses if isinstance(responses, Mapping) else {}

                status_keys = {str(k) for k in resp_map.keys()}
                has_2xx = any(
                    len(code) == 3 and code.startswith("2") and code.isdigit()
                    for code in status_keys
                )
                if not has_2xx:
                    missing_2xx_response_operations.append(op_ref)

                resp_204 = resp_map.get("204") or resp_map.get(204)
                if isinstance(resp_204, Mapping):
                    content_204 = resp_204.get("content")
                    if isinstance(content_204, Mapping) and len(content_204) > 0:
                        body_on_204_no_content_operations.append(op_ref)

                if method == "get" and "201" in status_keys:
                    get_with_201_created_operations.append(op_ref)

    return {
        "total_project_operations": total_project_operations,
        "missing_2xx_response_operations": sorted(missing_2xx_response_operations),
        "body_on_204_no_content_operations": sorted(body_on_204_no_content_operations),
        "get_with_201_created_operations": sorted(get_with_201_created_operations),
        "is_http_status_hygiene_compliant": (
            len(missing_2xx_response_operations) == 0
            and len(body_on_204_no_content_operations) == 0
            and len(get_with_201_created_operations) == 0
        ),
    }


def render_inventory(openapi: dict[str, Any]) -> str:
    operations = route_inventory(openapi)
    guards = declared_guards()
    missing = [(method, path) for method, path, _ in operations if (method, path) not in guards]
    if missing:
        raise ValueError(f"OpenAPI operations missing router authorization mapping: {missing}")
    unauthenticated = [
        (method, path)
        for method, path, _ in operations
        if guards[(method, path)] == "NO current_user dependency"
    ]
    if unauthenticated:
        raise ValueError(
            "Projects operations must declare an authenticated current_user dependency: "
            f"{unauthenticated}"
        )
    lines = [
        "# Inventario OpenAPI — Projects",
        "",
        "> Generado desde `backend.app:app.openapi()` por `scripts/audit_projects_api_contracts.py`.",
        "> El guard declarado se extrae de la dependencia `current_user` del router; esto no prueba",
        "> el resultado por rol ni sustituye la matriz RBAC y sus tests.",
        "> los contratos de negocio en `PROJECTS_API_CONTRACTS.md`.",
        "",
        f"Operaciones únicas actuales: **{len(operations)}** bajo `{PROJECT_PREFIX}`.",
        "",
        "| Método | Ruta | Operation ID | Guard declarado | Entrada | Respuestas OpenAPI |",
        "|---|---|---|---|---|---|",
    ]

    for method, path, operation in operations:
        request_refs = schema_refs(operation.get("requestBody", {}))
        operation_id = str(operation.get("operationId", "—")).replace("|", "\\|")
        lines.append(
            f"| `{method}` | `{path}` | `{operation_id}` | `{guards[(method, path)]}` | "
            f"{refs_cell(request_refs)} | {response_cell(operation.get('responses'))} |"
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help=f"write {OUTPUT.relative_to(ROOT)}")
    mode.add_argument("--check", action="store_true", help="fail if the committed inventory is stale")
    args = parser.parse_args()

    from backend.app import app

    expected = render_inventory(app.openapi())
    if args.write:
        OUTPUT.write_text(expected, encoding="utf-8")
        print(f"Updated {OUTPUT.relative_to(ROOT)} ({len(route_inventory(app.openapi()))} operations).")
        return 0

    if args.check:
        actual = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if actual == expected:
            print(f"PASS: {OUTPUT.relative_to(ROOT)} matches OpenAPI.")
            return 0
        diff = difflib.unified_diff(
            actual.splitlines(), expected.splitlines(),
            fromfile=str(OUTPUT.relative_to(ROOT)), tofile="current OpenAPI",
            lineterm="",
        )
        print("\n".join(diff), file=sys.stderr)
        return 1

    print(expected, end="")
    return 0


__all__ = [name for name in globals() if not name.startswith("_")]


if __name__ == "__main__":
    raise SystemExit(main())
