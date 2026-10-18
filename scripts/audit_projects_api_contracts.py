#!/usr/bin/env python3
"""Generate/check the Projects router inventory from the application's OpenAPI."""

from __future__ import annotations

import argparse
import difflib
import sys
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


if __name__ == "__main__":
    raise SystemExit(main())
