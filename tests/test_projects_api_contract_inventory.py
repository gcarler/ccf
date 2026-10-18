"""Regression tests for the Projects OpenAPI security inventory."""

from __future__ import annotations

import pytest

from scripts import audit_projects_api_contracts


def test_inventory_refuses_operations_without_authenticated_actor_dependency(monkeypatch):
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/private"): "NO current_user dependency"},
    )

    with pytest.raises(ValueError, match="authenticated current_user dependency"):
        audit_projects_api_contracts.render_inventory(
            {"paths": {"/api/projects/private": {"get": {"operationId": "private"}}}}
        )


def test_inventory_accepts_an_explicit_permission_guard(monkeypatch):
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/private"): "projects:read"},
    )

    inventory = audit_projects_api_contracts.render_inventory(
        {"paths": {"/api/projects/private": {"get": {"operationId": "private"}}}}
    )

    assert "`projects:read`" in inventory


# ── summarize_projects_guard_coverage (pure helper) ───────────────────────────


def test_guard_summary_reports_full_coverage(monkeypatch):
    """Todas las operaciones con guard válido → 0 sin autenticar y 100% cubierto."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {
            ("GET", "/api/projects/items"): "projects:read",
            ("POST", "/api/projects/items"): "projects:create",
        },
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                "/api/projects/items": {
                    "get": {"operationId": "list"},
                    "post": {"operationId": "create"},
                }
            }
        }
    )

    assert summary["total_operations"] == 2
    assert summary["authenticated_operations"] == 2
    assert summary["unauthenticated_operations"] == 0
    assert summary["missing_guard_mappings"] == 0
    assert summary["coverage_pct"] == 100.0
    assert summary["guard_distribution"] == {"projects:create": 1, "projects:read": 1}
    assert summary["is_fully_guarded"] is True


def test_guard_summary_counts_unauthenticated_operations(monkeypatch):
    """Operación con guard 'NO current_user dependency' → no cubierta."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/open"): "NO current_user dependency"},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {"paths": {"/api/projects/open": {"get": {"operationId": "open"}}}}
    )

    assert summary["total_operations"] == 1
    assert summary["authenticated_operations"] == 0
    assert summary["unauthenticated_operations"] == 1
    assert summary["missing_guard_mappings"] == 0
    assert summary["coverage_pct"] == 0.0
    assert summary["guard_distribution"] == {"NO current_user dependency": 1}
    assert summary["is_fully_guarded"] is False


def test_guard_summary_counts_missing_guard_mappings(monkeypatch):
    """Operación OpenAPI sin entrada en declared_guards() → missing mapping."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {("GET", "/api/projects/items"): "projects:read"},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                "/api/projects/items": {"get": {"operationId": "list"}},
                "/api/projects/orphan": {"delete": {"operationId": "orphan"}},
            }
        }
    )

    assert summary["total_operations"] == 2
    assert summary["authenticated_operations"] == 1
    assert summary["missing_guard_mappings"] == 1
    # La operación sin mapeo no entra en la distribución ni en coverage
    assert summary["coverage_pct"] == 50.0
    assert summary["guard_distribution"] == {"projects:read": 1}
    assert summary["is_fully_guarded"] is False


def test_guard_summary_empty_openapi(monkeypatch):
    """OpenAPI vacío (0 operaciones) → coverage 100.0 y is_fully_guarded False."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {},
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage({"paths": {}})

    assert summary == {
        "total_operations": 0,
        "authenticated_operations": 0,
        "unauthenticated_operations": 0,
        "missing_guard_mappings": 0,
        "coverage_pct": 100.0,
        "guard_distribution": {},
        "is_fully_guarded": False,
    }


def test_guard_summary_orders_guard_distribution_alphabetically(monkeypatch):
    """La distribución agrupa por guard y sale ordenada alfabéticamente."""
    monkeypatch.setattr(
        audit_projects_api_contracts,
        "declared_guards",
        lambda: {
            ("GET", "/api/projects/a"): "projects:read",
            ("GET", "/api/projects/b"): "projects:admin",
            ("GET", "/api/projects/c"): "projects:read",
            ("GET", "/api/projects/d"): "projects:edit",
        },
    )

    summary = audit_projects_api_contracts.summarize_projects_guard_coverage(
        {
            "paths": {
                f"/api/projects/{key}": {"get": {"operationId": f"op{key}"}} for key in "abcd"
            }
        }
    )

    assert summary["total_operations"] == 4
    assert summary["authenticated_operations"] == 4
    assert list(summary["guard_distribution"].items()) == [
        ("projects:admin", 1),
        ("projects:edit", 1),
        ("projects:read", 2),
    ]
    assert summary["coverage_pct"] == 100.0
    assert summary["is_fully_guarded"] is True


# ── summarize_projects_http_method_footprint (pure helper) ────────────────────


def test_http_method_footprint_mixed_read_and_mutation_with_schema_refs():
    """Audita mezcla de lectura/mutación, orden alfabético de métodos y conteo de esquemas únicos."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProjectRead"}
                                }
                            }
                        }
                    },
                },
                "post": {
                    "operationId": "create_project",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProjectCreate"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProjectRead"}
                                }
                            }
                        },
                        "422": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                                }
                            }
                        },
                    },
                },
            },
            "/api/projects/{project_id}": {
                "patch": {
                    "operationId": "update_project",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProjectUpdate"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProjectRead"}
                                }
                            }
                        }
                    },
                },
                "delete": {
                    "operationId": "delete_project",
                    "responses": {
                        "422": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ValidationError"}
                                }
                            }
                        }
                    },
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_http_method_footprint(openapi)
    assert res == {
        "total_operations": 4,
        "read_only_operations": 1,
        "mutation_operations": 3,
        "method_counts": {"DELETE": 1, "GET": 1, "PATCH": 1, "POST": 1},
        "unique_schema_refs_count": 3,
        "mutation_ratio_pct": 75.0,
    }
    assert list(res["method_counts"].keys()) == ["DELETE", "GET", "PATCH", "POST"]


def test_http_method_footprint_read_only_operations():
    """Solo operaciones de lectura (GET/HEAD/OPTIONS) -> mutation_operations=0, mutation_ratio_pct=0.0."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {"operationId": "list"},
                "head": {"operationId": "head_list"},
                "options": {"operationId": "options_list"},
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_http_method_footprint(openapi)
    assert res["total_operations"] == 3
    assert res["read_only_operations"] == 3
    assert res["mutation_operations"] == 0
    assert res["method_counts"] == {"GET": 1, "HEAD": 1, "OPTIONS": 1}
    assert res["mutation_ratio_pct"] == 0.0


def test_http_method_footprint_ignores_routes_outside_projects_prefix():
    """Rutas fuera de /api/projects no se contabilizan en la huella."""
    openapi = {
        "paths": {
            "/api/crm/contacts": {"get": {"operationId": "crm_list"}, "post": {"operationId": "crm_create"}},
            "/api/projects/tasks": {"get": {"operationId": "tasks_list"}},
        }
    }
    res = audit_projects_api_contracts.summarize_projects_http_method_footprint(openapi)
    assert res["total_operations"] == 1
    assert res["read_only_operations"] == 1
    assert res["mutation_operations"] == 0
    assert res["method_counts"] == {"GET": 1}


def test_http_method_footprint_empty_openapi():
    """OpenAPI vacío retorna todos los conteos en 0 y method_counts={}."""
    res = audit_projects_api_contracts.summarize_projects_http_method_footprint({})
    assert res == {
        "total_operations": 0,
        "read_only_operations": 0,
        "mutation_operations": 0,
        "method_counts": {},
        "unique_schema_refs_count": 0,
        "mutation_ratio_pct": 0.0,
    }


# ─── summarize_projects_route_path_complexity (pure helper) ────────────────────


def test_route_path_complexity_flat_collection_routes():
    """Rutas planas (/api/v1/projects y /api/v1/projects/{id}) → flat_collection_routes."""
    openapi = {
        "paths": {
            "/api/v1/projects": {"get": {"operationId": "list_projects"}},
            "/api/v1/projects/{id}": {
                "get": {"operationId": "get_project"},
                "patch": {"operationId": "update_project"},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_route_path_complexity(openapi)

    assert res == {
        "total_project_paths": 2,
        "parameterized_routes_count": 1,
        "deep_nested_routes_count": 0,
        "max_segment_depth": 4,
        "max_path_params": 1,
        "hierarchy_status": "flat_collection_routes",
    }


def test_route_path_complexity_hierarchical_subresources():
    """Subrecursos jerárquicos (>= 2 parámetros) → hierarchical_subresources."""
    openapi = {
        "paths": {
            "/api/v1/projects": {"get": {"operationId": "list_projects"}},
            "/api/v1/projects/{id}/tasks/{task_id}": {
                "patch": {"operationId": "update_task"}
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_route_path_complexity(openapi)

    assert res == {
        "total_project_paths": 2,
        "parameterized_routes_count": 1,
        "deep_nested_routes_count": 1,
        "max_segment_depth": 6,
        "max_path_params": 2,
        "hierarchy_status": "hierarchical_subresources",
    }


def test_route_path_complexity_excessive_nesting():
    """>= 3 parámetros o >= 8 segmentos → excessive_nesting (precedencia sobre subrecursos)."""
    by_params = {
        "paths": {
            "/api/v1/projects/{id}/tasks/{task_id}/comments/{comment_id}": {
                "get": {"operationId": "get_comment"}
            }
        }
    }
    res_params = audit_projects_api_contracts.summarize_projects_route_path_complexity(
        by_params
    )
    assert res_params["max_path_params"] == 3
    assert res_params["hierarchy_status"] == "excessive_nesting"

    # Borde exacto por profundidad: 8 segmentos (>= 8) y solo 2 parámetros.
    by_depth = {
        "paths": {
            "/api/v1/projects/{id}/tasks/{task_id}/comments/all": {
                "get": {"operationId": "get_reply"}
            }
        }
    }
    res_depth = audit_projects_api_contracts.summarize_projects_route_path_complexity(
        by_depth
    )
    assert res_depth["max_segment_depth"] == 8
    assert res_depth["hierarchy_status"] == "excessive_nesting"


def test_route_path_complexity_empty_openapi_and_non_project_routes():
    """Esquema vacío, None, paths no-dict o sin rutas Projects → no_project_routes."""
    assert audit_projects_api_contracts.summarize_projects_route_path_complexity(None) == {
        "total_project_paths": 0,
        "parameterized_routes_count": 0,
        "deep_nested_routes_count": 0,
        "max_segment_depth": 0,
        "max_path_params": 0,
        "hierarchy_status": "no_project_routes",
    }
    assert audit_projects_api_contracts.summarize_projects_route_path_complexity({})[
        "hierarchy_status"
    ] == "no_project_routes"
    assert audit_projects_api_contracts.summarize_projects_route_path_complexity(
        {"paths": ["/api/v1/projects"]}
    )["hierarchy_status"] == "no_project_routes"
    res_non_project = (
        audit_projects_api_contracts.summarize_projects_route_path_complexity(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "crm_list"}}}}
        )
    )
    assert res_non_project["total_project_paths"] == 0
    assert res_non_project["hierarchy_status"] == "no_project_routes"


# ─── summarize_projects_subresource_domains (pure helper) ─────────────────────


def test_subresource_domains_comprehensive_modularity():
    """Al menos 5 dominios únicos de subrecurso -> COMPREHENSIVE_DOMAIN_MODULARITY."""
    inventory = [
        {"path": "/api/v1/projects"},
        {"path": "/api/v1/projects/{project_id}"},
        {"path": "/api/v1/projects/{project_id}/tasks"},
        {"path": "/api/v1/projects/{project_id}/tasks/{task_id}"},
        {"path": "/api/v1/projects/{project_id}/tasks/{task_id}/comments"},
        {"path": "/api/v1/projects/{project_id}/risks"},
        {"path": "/api/v1/projects/{project_id}/stakeholders"},
        {"path": "/api/v1/projects/{project_id}/evm/summary"},
    ]

    res = audit_projects_api_contracts.summarize_projects_subresource_domains(inventory)

    assert res == {
        "total_routes": 8,
        "unique_domains_count": 5,
        "domain_counts": {
            "evm": 1,
            "risks": 1,
            "root": 2,
            "stakeholders": 1,
            "tasks": 3,
        },
        "top_domain": "tasks",
        "posture": "COMPREHENSIVE_DOMAIN_MODULARITY",
    }


def test_subresource_domains_narrow_scope_and_alphabetical_tie_break():
    """Menos de 5 dominios -> NARROW_DOMAIN_SCOPE y desempate alfabético ascendente en top_domain."""
    inventory = [
        {"path": "/api/projects/{id}/Wiki/pages"},
        {"path": "/api/projects/{id}/wiki/{page_id}"},
        {"path": "/api/v1/projects/{id}/budget/expenses"},
        {"path": "/api/v1/projects/{id}/Budget/summary"},
        {"path": "/api/v1/projects/{id}/charter"},
    ]

    res = audit_projects_api_contracts.summarize_projects_subresource_domains(inventory)

    assert res == {
        "total_routes": 5,
        "unique_domains_count": 3,
        "domain_counts": {
            "budget": 2,
            "charter": 1,
            "wiki": 2,
        },
        "top_domain": "budget",
        "posture": "NARROW_DOMAIN_SCOPE",
    }


def test_subresource_domains_root_fallback_and_non_dict_filtering():
    """Ignora entradas no-dict y asigna 'root' cuando solo hay prefijos o parámetros."""
    inventory = [
        None,
        "invalid-entry",
        123,
        {"path": "/api/v1/projects"},
        {"path": "/api/v1/projects/{project_id}"},
        {"path": ""},
    ]

    res = audit_projects_api_contracts.summarize_projects_subresource_domains(inventory)  # type: ignore[arg-type]

    assert res == {
        "total_routes": 3,
        "unique_domains_count": 1,
        "domain_counts": {"root": 3},
        "top_domain": "root",
        "posture": "NARROW_DOMAIN_SCOPE",
    }


def test_subresource_domains_empty_inventory():
    """Inventario vacío o None -> EMPTY_INVENTORY y top_domain='none'."""
    expected = {
        "total_routes": 0,
        "unique_domains_count": 0,
        "domain_counts": {},
        "top_domain": "none",
        "posture": "EMPTY_INVENTORY",
    }
    assert audit_projects_api_contracts.summarize_projects_subresource_domains(None) == expected
    assert audit_projects_api_contracts.summarize_projects_subresource_domains([]) == expected
    assert (
        audit_projects_api_contracts.summarize_projects_subresource_domains(["not-a-dict"])  # type: ignore[list-item]
        == expected
    )


