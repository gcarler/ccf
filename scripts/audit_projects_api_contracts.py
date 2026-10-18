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
