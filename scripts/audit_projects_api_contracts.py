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
