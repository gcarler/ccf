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


# ─── summarize_projects_schema_reference_density (pure helper) ────────────────


def test_schema_reference_density_strongly_typed_contracts():
    """>= 80% de respuestas tipadas y sin mutaciones huérfanas -> STRONGLY_TYPED_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProjectList"}
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
                    "responses": {"204": {"description": "No Content"}},
                },
                "get": {
                    "operationId": "get_project",
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
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_schema_reference_density(openapi)

    assert res == {
        "total_operations": 5,
        "typed_request_body_count": 2,
        "typed_response_count": 4,
        "untyped_mutation_routes": [],
        "unique_schemas_referenced": [
            "ProjectCreate",
            "ProjectList",
            "ProjectRead",
            "ProjectUpdate",
        ],
        "response_typing_coverage_pct": 80.0,
        "contract_posture": "STRONGLY_TYPED_CONTRACTS",
    }


def test_schema_reference_density_untyped_mutations_detected():
    """POST/PUT/PATCH sin schema_refs en requestBody ni en responses -> UNTYPED_MUTATIONS_DETECTED."""
    openapi = {
        "paths": {
            "/api/projects/{project_id}/archive": {
                "post": {
                    "operationId": "archive_project",
                    "responses": {"200": {"description": "Archived"}},
                },
            },
            "/api/projects/{project_id}": {
                "put": {
                    "operationId": "replace_project",
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
                "get": {
                    "operationId": "get_project",
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
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_schema_reference_density(openapi)

    assert res["total_operations"] == 3
    assert res["typed_request_body_count"] == 0
    assert res["typed_response_count"] == 1
    assert res["untyped_mutation_routes"] == [
        "POST /api/projects/{project_id}/archive",
        "PUT /api/projects/{project_id}",
    ]
    assert res["unique_schemas_referenced"] == ["ProjectRead"]
    assert res["response_typing_coverage_pct"] == 33.33
    assert res["contract_posture"] == "UNTYPED_MUTATIONS_DETECTED"


def test_schema_reference_density_partial_response_typing():
    """Mutaciones tipadas por requestBody pero < 80% de respuestas tipadas -> PARTIAL_RESPONSE_TYPING."""
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
                    "responses": {"201": {"description": "Created"}},
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_schema_reference_density(openapi)

    assert res == {
        "total_operations": 2,
        "typed_request_body_count": 1,
        "typed_response_count": 1,
        "untyped_mutation_routes": [],
        "unique_schemas_referenced": ["ProjectCreate", "ProjectRead"],
        "response_typing_coverage_pct": 50.0,
        "contract_posture": "PARTIAL_RESPONSE_TYPING",
    }


def test_schema_reference_density_empty_openapi():
    """OpenAPI vacío o sin rutas bajo /api/projects -> EMPTY_OPENAPI_INVENTORY."""
    expected = {
        "total_operations": 0,
        "typed_request_body_count": 0,
        "typed_response_count": 0,
        "untyped_mutation_routes": [],
        "unique_schemas_referenced": [],
        "response_typing_coverage_pct": 0.0,
        "contract_posture": "EMPTY_OPENAPI_INVENTORY",
    }
    assert audit_projects_api_contracts.summarize_projects_schema_reference_density({}) == expected
    assert audit_projects_api_contracts.summarize_projects_schema_reference_density(None) == expected
    assert (
        audit_projects_api_contracts.summarize_projects_schema_reference_density(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "list_crm"}}}}
        )
        == expected
    )


# ─── summarize_projects_error_response_coverage (pure helper) ─────────────────


def test_error_response_coverage_comprehensive():
    """100% con 2xx y >= 80% con 4xx/422 -> COMPREHENSIVE_STATUS_COVERAGE."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "create_project",
                    "responses": {
                        "201": {"description": "Created"},
                        "422": {"description": "Validation Error"},
                    },
                },
            },
            "/api/projects/{project_id}": {
                "get": {
                    "operationId": "get_project",
                    "responses": {
                        "200": {"description": "OK"},
                        "404": {"description": "Not Found"},
                    },
                },
                "patch": {
                    "operationId": "update_project",
                    "responses": {
                        "200": {"description": "OK"},
                        "422": {"description": "Validation Error"},
                    },
                },
                "delete": {
                    "operationId": "delete_project",
                    "responses": {
                        "204": {"description": "No Content"},
                        "403": {"description": "Forbidden"},
                    },
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_coverage(openapi)

    assert res == {
        "total_operations": 5,
        "has_2xx_success_count": 5,
        "has_4xx_or_422_count": 4,
        "missing_success_status_routes": [],
        "missing_error_status_routes": ["GET /api/projects"],
        "error_coverage_pct": 80.0,
        "status_posture": "COMPREHENSIVE_STATUS_COVERAGE",
    }


def test_error_response_coverage_missing_success_contract():
    """Operaciones sin ningún código 2xx -> MISSING_SUCCESS_CONTRACT (prioridad sobre error_coverage_pct)."""
    openapi = {
        "paths": {
            "/api/projects/{project_id}/export": {
                "get": {
                    "operationId": "export_project",
                    "responses": {"422": {"description": "Validation Error"}},
                }
            },
            "/api/projects": {
                "post": {
                    "operationId": "create_project",
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Bad Request"},
                    },
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_coverage(openapi)

    assert res == {
        "total_operations": 2,
        "has_2xx_success_count": 1,
        "has_4xx_or_422_count": 2,
        "missing_success_status_routes": ["GET /api/projects/{project_id}/export"],
        "missing_error_status_routes": [],
        "error_coverage_pct": 100.0,
        "status_posture": "MISSING_SUCCESS_CONTRACT",
    }


def test_error_response_coverage_partial_error_documentation():
    """Todas las rutas tienen 2xx pero < 80% tienen códigos 4xx -> PARTIAL_ERROR_DOCUMENTATION."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "create_project",
                    "responses": {
                        "201": {"description": "Created"},
                        "422": {"description": "Validation Error"},
                    },
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_coverage(openapi)

    assert res == {
        "total_operations": 2,
        "has_2xx_success_count": 2,
        "has_4xx_or_422_count": 1,
        "missing_success_status_routes": [],
        "missing_error_status_routes": ["GET /api/projects"],
        "error_coverage_pct": 50.0,
        "status_posture": "PARTIAL_ERROR_DOCUMENTATION",
    }


def test_error_response_coverage_empty_openapi():
    """OpenAPI vacío o sin rutas bajo /api/projects -> EMPTY_OPENAPI_INVENTORY."""
    expected = {
        "total_operations": 0,
        "has_2xx_success_count": 0,
        "has_4xx_or_422_count": 0,
        "missing_success_status_routes": [],
        "missing_error_status_routes": [],
        "error_coverage_pct": 0.0,
        "status_posture": "EMPTY_OPENAPI_INVENTORY",
    }
    assert audit_projects_api_contracts.summarize_projects_error_response_coverage({}) == expected
    assert audit_projects_api_contracts.summarize_projects_error_response_coverage(None) == expected
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_coverage(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "list_crm"}}}}
        )
        == expected
    )


# ─── summarize_projects_operation_documentation_quality (pure helper) ─────────


def test_operation_documentation_quality_well_documented():
    """>= 80% con summary >= 5 chars y sin operationId duplicados -> WELL_DOCUMENTED_OPERATIONS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "summary": "List all projects",
                    "tags": ["Projects"],
                },
                "post": {
                    "operationId": "create_project",
                    "summary": "Create a new project",
                    "tags": ["Projects"],
                },
            },
            "/api/projects/{project_id}": {
                "get": {
                    "operationId": "get_project",
                    "summary": "Get project details",
                    "tags": ["Projects"],
                },
                "patch": {
                    "operationId": "update_project",
                    "summary": "Update project fields",
                },
                "delete": {
                    "operationId": "delete_project",
                    "summary": "Del",  # < 5 chars -> undocumented
                    "tags": ["Projects"],
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_documentation_quality(
        openapi
    )

    assert res == {
        "total_operations": 5,
        "has_summary_count": 4,
        "has_operation_id_count": 5,
        "has_tags_count": 4,
        "undocumented_routes": ["DELETE /api/projects/{project_id}"],
        "duplicate_operation_ids": [],
        "summary_coverage_pct": 80.0,
        "documentation_posture": "WELL_DOCUMENTED_OPERATIONS",
    }


def test_operation_documentation_quality_duplicate_operation_ids():
    """operationId repetidos en rutas /api/projects -> DUPLICATE_OPERATION_IDS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "project_op",
                    "summary": "List projects",
                    "tags": ["Projects"],
                },
                "post": {
                    "operationId": "project_op",
                    "summary": "Create project",
                    "tags": ["Projects"],
                },
            },
            "/api/projects/{project_id}": {
                "get": {
                    "operationId": "detail_op",
                    "summary": "Get project",
                },
                "delete": {
                    "operationId": "detail_op",
                    "summary": "Delete project",
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_documentation_quality(
        openapi
    )

    assert res == {
        "total_operations": 4,
        "has_summary_count": 4,
        "has_operation_id_count": 4,
        "has_tags_count": 2,
        "undocumented_routes": [],
        "duplicate_operation_ids": ["detail_op", "project_op"],
        "summary_coverage_pct": 100.0,
        "documentation_posture": "DUPLICATE_OPERATION_IDS",
    }


def test_operation_documentation_quality_incomplete_summaries():
    """< 80% con summary >= 5 chars y sin duplicados -> INCOMPLETE_OPERATION_SUMMARIES."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "operationId": "list_projects",
                    "summary": "List all projects",
                },
                "post": {
                    "operationId": "",
                    "summary": "   ",
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_documentation_quality(
        openapi
    )

    assert res == {
        "total_operations": 2,
        "has_summary_count": 1,
        "has_operation_id_count": 1,
        "has_tags_count": 0,
        "undocumented_routes": ["POST /api/projects"],
        "duplicate_operation_ids": [],
        "summary_coverage_pct": 50.0,
        "documentation_posture": "INCOMPLETE_OPERATION_SUMMARIES",
    }


def test_operation_documentation_quality_empty_openapi():
    """OpenAPI vacío o sin rutas bajo /api/projects -> EMPTY_OPENAPI_INVENTORY."""
    expected = {
        "total_operations": 0,
        "has_summary_count": 0,
        "has_operation_id_count": 0,
        "has_tags_count": 0,
        "undocumented_routes": [],
        "duplicate_operation_ids": [],
        "summary_coverage_pct": 0.0,
        "documentation_posture": "EMPTY_OPENAPI_INVENTORY",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_operation_documentation_quality({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_documentation_quality(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_documentation_quality(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "list_crm"}}}}
        )
        == expected
    )


# ─── summarize_projects_collection_pagination_coverage (pure helper) ──────────


def test_collection_pagination_coverage_bounded_contracts():
    """100% de colecciones GET con parámetros de paginación o filtro -> BOUNDED_COLLECTION_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "parameters": [
                        {"in": "query", "name": "limit"},
                        {"in": "query", "name": "offset"},
                    ]
                }
            },
            "/api/v1/projects/{project_id}/tasks": {
                "parameters": [{"in": "query", "name": "status"}],
                "get": {"operationId": "list_tasks"},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_collection_pagination_coverage(
        openapi
    )

    assert res == {
        "collection_get_count": 2,
        "paginated_or_filtered_count": 2,
        "unbounded_collection_ops": [],
        "coverage_pct": 100.0,
        "pagination_posture": "BOUNDED_COLLECTION_CONTRACTS",
    }


def test_collection_pagination_coverage_partial():
    """>= 50% de colecciones GET acotadas pero >= 1 sin acotar -> PARTIAL_PAGINATION_COVERAGE."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "parameters": [{"in": "query", "name": "page_size"}],
                }
            },
            "/api/projects/{project_id}/risks": {
                "get": {
                    "parameters": [{"in": "query", "name": "search"}],
                }
            },
            "/api/projects/{project_id}/stakeholders": {
                "get": {
                    "parameters": [{"in": "header", "name": "X-Trace"}],
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_collection_pagination_coverage(
        openapi
    )

    assert res == {
        "collection_get_count": 3,
        "paginated_or_filtered_count": 2,
        "unbounded_collection_ops": ["GET /api/projects/{project_id}/stakeholders"],
        "coverage_pct": 66.67,
        "pagination_posture": "PARTIAL_PAGINATION_COVERAGE",
    }


def test_collection_pagination_coverage_unbounded_risk_and_ignores_item_routes():
    """< 50% acotadas -> UNBOUNDED_COLLECTION_RISK e ignora rutas de detalle terminadas en '}'."""
    openapi = {
        "paths": {
            "/api/projects": {"get": {"operationId": "list_projects"}},
            "/api/projects/{project_id}": {"get": {"operationId": "get_project"}},
            "/api/projects/{project_id}/tasks/{task_id}/": {
                "get": {"operationId": "get_task"}
            },
            "/api/projects/{project_id}/expenses": {
                "get": {"operationId": "list_expenses"}
            },
            "/api/projects/{project_id}/wiki": {
                "get": {"parameters": [{"in": "query", "name": "q"}]}
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_collection_pagination_coverage(
        openapi
    )

    assert res == {
        "collection_get_count": 3,
        "paginated_or_filtered_count": 1,
        "unbounded_collection_ops": [
            "GET /api/projects",
            "GET /api/projects/{project_id}/expenses",
        ],
        "coverage_pct": 33.33,
        "pagination_posture": "UNBOUNDED_COLLECTION_RISK",
    }


def test_collection_pagination_coverage_empty_or_no_collections():
    """Esquema vacío, None o solo rutas detalle/POST -> NO_COLLECTION_OPERATIONS."""
    expected = {
        "collection_get_count": 0,
        "paginated_or_filtered_count": 0,
        "unbounded_collection_ops": [],
        "coverage_pct": 0.0,
        "pagination_posture": "NO_COLLECTION_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_collection_pagination_coverage(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_collection_pagination_coverage({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_collection_pagination_coverage(
            {
                "paths": {
                    "/api/projects/{project_id}": {"get": {"operationId": "get_one"}},
                    "/api/projects": {"post": {"operationId": "create_one"}},
                    "/api/crm/contacts": {"get": {"operationId": "list_crm"}},
                }
            }
        )
        == expected
    )


# ─── summarize_projects_path_parameter_uuid_typing (pure helper) ─────────────


def test_path_parameter_uuid_typing_strict_including_anyof_and_override():
    """100% de parámetros path id/*_id con format=='uuid' (directo, anyOf o override de op_spec) -> STRICT_UUID_PATH_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/projects/{project_id}/tasks/{id}": {
                "parameters": [
                    {
                        "in": "path",
                        "name": "project_id",
                        "schema": {"type": "string"},  # overridden in op_spec
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "project_id",
                            "schema": {"type": "string", "format": "uuid"},
                        },
                        {
                            "in": "path",
                            "name": "id",
                            "schema": {
                                "anyOf": [
                                    {"type": "string", "format": "uuid"},
                                    {"type": "null"},
                                ]
                            },
                        },
                        {
                            "in": "query",
                            "name": "phase_id",
                            "schema": {"type": "string"},  # query param ignored
                        },
                    ]
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing(
        openapi
    )

    assert res == {
        "id_path_param_count": 2,
        "uuid_typed_count": 2,
        "untyped_id_params": [],
        "uuid_typing_rate_pct": 100.0,
        "uuid_posture": "STRICT_UUID_PATH_CONTRACTS",
    }


def test_path_parameter_uuid_typing_partial():
    """>= 50% de parámetros id/*_id con format uuid pero >= 1 sin tipar -> PARTIAL_UUID_PATH_TYPING."""
    openapi = {
        "paths": {
            "/api/projects/{project_id}": {
                "get": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "project_id",
                            "schema": {"type": "string", "format": "uuid"},
                        }
                    ]
                },
                "delete": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "project_id",
                            "schema": {"type": "string"},
                        }
                    ]
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing(
        openapi
    )

    assert res == {
        "id_path_param_count": 2,
        "uuid_typed_count": 1,
        "untyped_id_params": ["DELETE /api/projects/{project_id}:project_id"],
        "uuid_typing_rate_pct": 50.0,
        "uuid_posture": "PARTIAL_UUID_PATH_TYPING",
    }


def test_path_parameter_uuid_typing_weak():
    """< 50% de parámetros id/*_id con format uuid -> WEAK_PATH_ID_TYPING."""
    openapi = {
        "paths": {
            "/api/projects/{project_id}/risks/{risk_id}": {
                "patch": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": "project_id",
                            "schema": {"type": "string"},
                        },
                        {
                            "in": "path",
                            "name": "risk_id",
                            "schema": {"type": "integer"},
                        },
                    ]
                }
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing(
        openapi
    )

    assert res == {
        "id_path_param_count": 2,
        "uuid_typed_count": 0,
        "untyped_id_params": [
            "PATCH /api/projects/{project_id}/risks/{risk_id}:project_id",
            "PATCH /api/projects/{project_id}/risks/{risk_id}:risk_id",
        ],
        "uuid_typing_rate_pct": 0.0,
        "uuid_posture": "WEAK_PATH_ID_TYPING",
    }


def test_path_parameter_uuid_typing_empty_or_no_id_params():
    """Esquema vacío, None o parámetros path que no son id/*_id -> NO_ID_PATH_PARAMETERS."""
    expected = {
        "id_path_param_count": 0,
        "uuid_typed_count": 0,
        "untyped_id_params": [],
        "uuid_typing_rate_pct": 0.0,
        "uuid_posture": "NO_ID_PATH_PARAMETERS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_typing(
            {
                "paths": {
                    "/api/projects/{slug}": {
                        "get": {
                            "parameters": [
                                {"in": "path", "name": "slug", "schema": {"type": "string"}}
                            ]
                        }
                    }
                }
            }
        )
        == expected
    )


# ─── summarize_projects_security_requirement_coverage (pure helper) ──────────


def test_security_requirement_coverage_enforced_via_root_and_operation():
    """100% de operaciones protegidas (heredando de root security o con security explícito) -> ENFORCED_SECURITY_CONTRACTS."""
    openapi = {
        "security": [{"BearerAuth": []}],
        "paths": {
            "/api/projects": {
                "get": {"operationId": "list_projects"},
                "post": {
                    "operationId": "create_project",
                    "security": [{"OAuth2PasswordBearer": ["projects:write"]}],
                },
            }
        },
    }

    res = audit_projects_api_contracts.summarize_projects_security_requirement_coverage(
        openapi
    )

    assert res == {
        "total_operations": 2,
        "secured_operations_count": 2,
        "unsecured_operations": [],
        "security_coverage_pct": 100.0,
        "security_posture": "ENFORCED_SECURITY_CONTRACTS",
    }


def test_security_requirement_coverage_partial_when_op_overrides_with_empty():
    """>= 50% protegidas pero una operación sobreescribe security=[] -> PARTIAL_SECURITY_COVERAGE."""
    openapi = {
        "security": [{"BearerAuth": []}],
        "paths": {
            "/api/projects": {
                "get": {"operationId": "list_projects"},
                "post": {"operationId": "create_project"},
            },
            "/api/projects/public-health": {
                "get": {
                    "operationId": "public_health",
                    "security": [],
                }
            },
        },
    }

    res = audit_projects_api_contracts.summarize_projects_security_requirement_coverage(
        openapi
    )

    assert res == {
        "total_operations": 3,
        "secured_operations_count": 2,
        "unsecured_operations": ["GET /api/projects/public-health"],
        "security_coverage_pct": 66.67,
        "security_posture": "PARTIAL_SECURITY_COVERAGE",
    }


def test_security_requirement_coverage_unprotected_exposure():
    """< 50% de operaciones protegidas -> UNPROTECTED_ENDPOINT_EXPOSURE."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {"operationId": "list_projects"},
                "post": {
                    "operationId": "create_project",
                    "security": [{}],  # empty dict does not count as valid security scheme
                },
            },
            "/api/projects/{project_id}": {
                "delete": {
                    "operationId": "delete_project",
                    "security": [{"BearerAuth": []}],
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_security_requirement_coverage(
        openapi
    )

    assert res == {
        "total_operations": 3,
        "secured_operations_count": 1,
        "unsecured_operations": ["GET /api/projects", "POST /api/projects"],
        "security_coverage_pct": 33.33,
        "security_posture": "UNPROTECTED_ENDPOINT_EXPOSURE",
    }


def test_security_requirement_coverage_empty_or_no_projects_operations():
    """Esquema vacío, None o sin operaciones bajo /projects -> NO_PROJECTS_OPERATIONS."""
    expected = {
        "total_operations": 0,
        "secured_operations_count": 0,
        "unsecured_operations": [],
        "security_coverage_pct": 0.0,
        "security_posture": "NO_PROJECTS_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_security_requirement_coverage(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_security_requirement_coverage({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_security_requirement_coverage(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "list_crm"}}}}
        )
        == expected
    )


# ─── summarize_projects_mutation_request_body_contracts (pure helper) ────────


def test_mutation_request_body_contracts_strict_typed():
    """100% de requestBody en POST/PUT/PATCH con schema tipado ($ref o properties/type) -> STRICT_TYPED_MUTATION_BODIES."""
    openapi = {
        "paths": {
            "/api/projects": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProjectCreate"}
                            }
                        }
                    }
                }
            },
            "/api/projects/{project_id}": {
                "patch": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"title": {"type": "string"}},
                                }
                            }
                        }
                    }
                },
                "post": {
                    # Action endpoint without requestBody does not penalize with_request_body_count
                    "operationId": "archive_project",
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts(
        openapi
    )

    assert res == {
        "mutation_operations_count": 3,
        "with_request_body_count": 2,
        "typed_request_body_count": 2,
        "untyped_request_body_ops": [],
        "typing_rate_pct": 100.0,
        "request_body_posture": "STRICT_TYPED_MUTATION_BODIES",
    }


def test_mutation_request_body_contracts_partial_typing():
    """>= 50% de requestBody tipados pero >= 1 con schema vacío -> PARTIAL_MUTATION_BODY_TYPING."""
    openapi = {
        "paths": {
            "/api/projects": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ProjectCreate"}
                            }
                        }
                    }
                }
            },
            "/api/projects/{project_id}": {
                "put": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {}}
                        }
                    }
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts(
        openapi
    )

    assert res == {
        "mutation_operations_count": 2,
        "with_request_body_count": 2,
        "typed_request_body_count": 1,
        "untyped_request_body_ops": ["PUT /api/projects/{project_id}"],
        "typing_rate_pct": 50.0,
        "request_body_posture": "PARTIAL_MUTATION_BODY_TYPING",
    }


def test_mutation_request_body_contracts_untyped_payload_risk():
    """< 50% de requestBody tipados -> UNTYPED_MUTATION_PAYLOAD_RISK."""
    openapi = {
        "paths": {
            "/api/projects": {
                "post": {"requestBody": {"content": {"application/json": {}}}},
            },
            "/api/projects/{project_id}/tasks": {
                "post": {"requestBody": {}},
                "patch": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"anyOf": [{"type": "object"}]}
                            }
                        }
                    }
                },
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts(
        openapi
    )

    assert res == {
        "mutation_operations_count": 3,
        "with_request_body_count": 3,
        "typed_request_body_count": 1,
        "untyped_request_body_ops": [
            "POST /api/projects",
            "POST /api/projects/{project_id}/tasks",
        ],
        "typing_rate_pct": 33.33,
        "request_body_posture": "UNTYPED_MUTATION_PAYLOAD_RISK",
    }


def test_mutation_request_body_contracts_empty_or_no_request_bodies():
    """Esquema vacío, None o mutaciones sin requestBody -> NO_MUTATION_OPERATIONS."""
    expected_zero = {
        "mutation_operations_count": 0,
        "with_request_body_count": 0,
        "typed_request_body_count": 0,
        "untyped_request_body_ops": [],
        "typing_rate_pct": 0.0,
        "request_body_posture": "NO_MUTATION_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts(None)
        == expected_zero
    )
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts({})
        == expected_zero
    )
    res_no_body = (
        audit_projects_api_contracts.summarize_projects_mutation_request_body_contracts(
            {
                "paths": {
                    "/api/projects/{project_id}/close": {
                        "post": {"operationId": "close_project"}
                    }
                }
            }
        )
    )
    assert res_no_body == {
        "mutation_operations_count": 1,
        "with_request_body_count": 0,
        "typed_request_body_count": 0,
        "untyped_request_body_ops": [],
        "typing_rate_pct": 0.0,
        "request_body_posture": "NO_MUTATION_OPERATIONS",
    }


# ─── summarize_projects_operation_deprecation_hygiene (pure helper) ──────────


def test_operation_deprecation_hygiene_clean_lifecycle():
    """<= 25% deprecados con guía de migración explícita -> CLEAN_OPERATION_LIFECYCLE."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {"summary": "List projects"},
                "post": {"summary": "Create project"},
            },
            "/api/projects/{project_id}": {
                "get": {"summary": "Get project"},
                "patch": {"summary": "Update project"},
            },
            "/api/projects/{project_id}/legacy-tasks": {
                "get": {
                    "deprecated": True,
                    "summary": "Legacy tasks list",
                    "description": "Deprecated: please use /api/projects/{project_id}/tasks instead.",
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 5,
        "deprecated_operations_count": 1,
        "undocumented_deprecated_ops": [],
        "deprecation_rate_pct": 20.0,
        "deprecation_posture": "CLEAN_OPERATION_LIFECYCLE",
    }


def test_operation_deprecation_hygiene_undocumented_deprecated():
    """Operación deprecada sin guía de migración/reemplazo -> UNDOCUMENTED_DEPRECATED_ENDPOINTS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {"summary": "List projects"},
            },
            "/api/projects/old-export": {
                "post": {
                    "deprecated": True,
                    "summary": "Old export endpoint",
                    "description": "No longer supported.",
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 2,
        "deprecated_operations_count": 1,
        "undocumented_deprecated_ops": ["POST /api/projects/old-export"],
        "deprecation_rate_pct": 50.0,
        "deprecation_posture": "UNDOCUMENTED_DEPRECATED_ENDPOINTS",
    }


def test_operation_deprecation_hygiene_excessive_deprecated_surface():
    """> 25% de operaciones deprecadas pero todas documentadas con guía -> EXCESSIVE_DEPRECATED_SURFACE."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {"summary": "List projects"},
                "post": {
                    "deprecated": True,
                    "description": "Reemplazado por /api/v2/projects.",
                },
            },
            "/api/projects/{project_id}": {
                "delete": {
                    "deprecated": True,
                    "summary": "Sunset scheduled; migrate to archive action.",
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 3,
        "deprecated_operations_count": 2,
        "undocumented_deprecated_ops": [],
        "deprecation_rate_pct": 66.67,
        "deprecation_posture": "EXCESSIVE_DEPRECATED_SURFACE",
    }


def test_operation_deprecation_hygiene_empty_or_no_projects_operations():
    """Esquema vacío, None o sin operaciones bajo /projects -> NO_PROJECTS_OPERATIONS."""
    expected = {
        "total_operations": 0,
        "deprecated_operations_count": 0,
        "undocumented_deprecated_ops": [],
        "deprecation_rate_pct": 0.0,
        "deprecation_posture": "NO_PROJECTS_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_deprecation_hygiene(
            {"paths": {"/api/crm/contacts": {"get": {"deprecated": True}}}}
        )
        == expected
    )


# ─── summarize_projects_error_response_contract_coverage (pure helper) ───────


def test_error_response_contract_coverage_complete():
    """Operaciones con cobertura completa de errores 4xx/404/422 -> COMPLETE_ERROR_RESPONSE_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "get": {"responses": {"200": {}, "401": {}}},
                "post": {"responses": {"201": {}, "422": {}}},
            },
            "/api/v1/projects/{project_id}": {
                "get": {"responses": {"200": {}, "404": {}}},
                "delete": {"responses": {"204": {}, "404": {}, "409": {}}},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
        openapi
    )

    assert res == {
        "total_projects_operations": 4,
        "documented_error_operations_count": 4,
        "missing_error_contract_operations": [],
        "error_contract_coverage_pct": 100.0,
        "is_error_contract_compliant": True,
        "error_contract_posture": "COMPLETE_ERROR_RESPONSE_CONTRACTS",
    }


def test_error_response_contract_coverage_missing_on_parameterized_route():
    """Ruta parametrizada '{project_id}' sin 404/422/default -> MISSING_ERROR_RESPONSE_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/v1/projects/{project_id}": {
                "get": {"responses": {"200": {}, "401": {}}},
                "patch": {"responses": {"200": {}, "422": {}}},
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
        openapi
    )

    assert res == {
        "total_projects_operations": 2,
        "documented_error_operations_count": 1,
        "missing_error_contract_operations": ["GET /api/v1/projects/{project_id}"],
        "error_contract_coverage_pct": 50.0,
        "is_error_contract_compliant": False,
        "error_contract_posture": "MISSING_ERROR_RESPONSE_CONTRACTS",
    }


def test_error_response_contract_coverage_missing_on_mutation():
    """Mutación POST/PATCH sin 400/409/422/default -> MISSING_ERROR_RESPONSE_CONTRACTS."""
    openapi = {
        "paths": {
            "/projects": {
                "post": {"responses": {"201": {}, "401": {}}},
            },
            "/projects/{project_id}/archive": {
                "patch": {"responses": {"200": {}, "404": {}}},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
        openapi
    )

    assert res == {
        "total_projects_operations": 2,
        "documented_error_operations_count": 0,
        "missing_error_contract_operations": [
            "PATCH /projects/{project_id}/archive",
            "POST /projects",
        ],
        "error_contract_coverage_pct": 0.0,
        "is_error_contract_compliant": False,
        "error_contract_posture": "MISSING_ERROR_RESPONSE_CONTRACTS",
    }


def test_error_response_contract_coverage_empty_or_none():
    """Esquema vacío, None o sin operaciones bajo /projects -> NO_PROJECTS_OPERATIONS."""
    expected = {
        "total_projects_operations": 0,
        "documented_error_operations_count": 0,
        "missing_error_contract_operations": [],
        "error_contract_coverage_pct": 100.0,
        "is_error_contract_compliant": True,
        "error_contract_posture": "NO_PROJECTS_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
            None
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
            {}
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_contract_coverage(
            {"paths": {"/api/crm/contacts": {"get": {"responses": {"200": {}}}}}}
        )
        == expected
    )


# ─── summarize_projects_mutation_success_status_hygiene (pure helper) ────────


def test_mutation_success_status_hygiene_clean_contracts():
    """POST/PATCH/DELETE con códigos 201/200/204 semánticamente válidos -> CLEAN_MUTATION_STATUS_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "get": {"responses": {"200": {}}},
                "post": {"responses": {"201": {}, "422": {}}},
            },
            "/api/v1/projects/{project_id}": {
                "patch": {"responses": {"200": {}, "404": {}}},
                "delete": {"responses": {"204": {}, "404": {}}},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
        openapi
    )

    assert res == {
        "total_mutation_operations": 3,
        "valid_mutation_operations_count": 3,
        "missing_success_status_operations": [],
        "semantic_status_mismatch_operations": [],
        "hygiene_rate_pct": 100.0,
        "is_mutation_status_compliant": True,
        "mutation_status_posture": "CLEAN_MUTATION_STATUS_CONTRACTS",
    }


def test_mutation_success_status_hygiene_missing_success_status():
    """Operación de mutación sin código 2xx -> MISSING_SUCCESS_STATUS_CONTRACT."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "post": {"responses": {"201": {}}},
            },
            "/api/v1/projects/{project_id}/archive": {
                "post": {"responses": {"400": {}, "422": {}}},
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
        openapi
    )

    assert res == {
        "total_mutation_operations": 2,
        "valid_mutation_operations_count": 1,
        "missing_success_status_operations": [
            "POST /api/v1/projects/{project_id}/archive"
        ],
        "semantic_status_mismatch_operations": [],
        "hygiene_rate_pct": 50.0,
        "is_mutation_status_compliant": False,
        "mutation_status_posture": "MISSING_SUCCESS_STATUS_CONTRACT",
    }


def test_mutation_success_status_hygiene_semantic_mismatch():
    """Operación DELETE o PATCH con código 201 inválido -> SEMANTIC_STATUS_CODE_MISMATCH."""
    openapi = {
        "paths": {
            "/api/v1/projects/{project_id}": {
                "patch": {"responses": {"201": {}}},
                "delete": {"responses": {"201": {}, "204": {}}},
                "put": {"responses": {"200": {}}},
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
        openapi
    )

    assert res == {
        "total_mutation_operations": 3,
        "valid_mutation_operations_count": 1,
        "missing_success_status_operations": [],
        "semantic_status_mismatch_operations": [
            "DELETE /api/v1/projects/{project_id}",
            "PATCH /api/v1/projects/{project_id}",
        ],
        "hygiene_rate_pct": 33.33,
        "is_mutation_status_compliant": False,
        "mutation_status_posture": "SEMANTIC_STATUS_CODE_MISMATCH",
    }


def test_mutation_success_status_hygiene_empty_or_no_mutations():
    """Esquema sin mutaciones o None -> NO_MUTATION_OPERATIONS."""
    expected = {
        "total_mutation_operations": 0,
        "valid_mutation_operations_count": 0,
        "missing_success_status_operations": [],
        "semantic_status_mismatch_operations": [],
        "hygiene_rate_pct": 100.0,
        "is_mutation_status_compliant": True,
        "mutation_status_posture": "NO_MUTATION_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
            None
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
            {}
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_success_status_hygiene(
            {"paths": {"/api/v1/projects": {"get": {"responses": {"200": {}}}}}}
        )
        == expected
    )


# ─── summarize_projects_operation_metadata_hygiene (pure helper) ─────────────


def test_operation_metadata_hygiene_clean_metadata():
    """Operaciones con operationId único, summary >= 5 chars y tags -> CLEAN_OPERATION_METADATA."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "get": {
                    "operationId": "list_projects",
                    "summary": "List all projects",
                    "tags": ["Projects"],
                },
                "post": {
                    "operationId": "create_project",
                    "description": "Create a new project record",
                    "tags": ["Projects"],
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 2,
        "missing_operation_id_ops": [],
        "duplicate_operation_ids": [],
        "missing_summary_ops": [],
        "untagged_ops": [],
        "is_metadata_hygiene_compliant": True,
        "metadata_hygiene_posture": "CLEAN_OPERATION_METADATA",
    }


def test_operation_metadata_hygiene_duplicate_or_missing_operation_id():
    """Operación sin operationId y dos con el mismo operationId -> DUPLICATE_OR_MISSING_OPERATION_ID."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "get": {
                    "operationId": "dup_op",
                    "summary": "List projects",
                    "tags": ["Projects"],
                },
                "post": {
                    "operationId": "dup_op",
                    "summary": "Create project",
                    "tags": ["Projects"],
                },
            },
            "/api/v1/projects/{project_id}": {
                "delete": {
                    "summary": "Delete project",
                    "tags": ["Projects"],
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 3,
        "missing_operation_id_ops": ["DELETE /api/v1/projects/{project_id}"],
        "duplicate_operation_ids": ["dup_op"],
        "missing_summary_ops": [],
        "untagged_ops": [],
        "is_metadata_hygiene_compliant": False,
        "metadata_hygiene_posture": "DUPLICATE_OR_MISSING_OPERATION_ID",
    }


def test_operation_metadata_hygiene_missing_summary_or_tags():
    """Operación con operationId único pero sin summary o sin tags -> MISSING_SUMMARY_OR_TAGS."""
    openapi = {
        "paths": {
            "/api/v1/projects": {
                "get": {
                    "operationId": "list_projects",
                    "summary": " get ",
                    "tags": [],
                },
                "post": {
                    "operationId": "create_project",
                    "summary": "Valid summary",
                },
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene(
        openapi
    )

    assert res == {
        "total_operations": 2,
        "missing_operation_id_ops": [],
        "duplicate_operation_ids": [],
        "missing_summary_ops": ["GET /api/v1/projects"],
        "untagged_ops": ["GET /api/v1/projects", "POST /api/v1/projects"],
        "is_metadata_hygiene_compliant": False,
        "metadata_hygiene_posture": "MISSING_SUMMARY_OR_TAGS",
    }


def test_operation_metadata_hygiene_empty_or_none():
    """Esquema vacío o None -> NO_PROJECTS_OPERATIONS."""
    expected = {
        "total_operations": 0,
        "missing_operation_id_ops": [],
        "duplicate_operation_ids": [],
        "missing_summary_ops": [],
        "untagged_ops": [],
        "is_metadata_hygiene_compliant": True,
        "metadata_hygiene_posture": "NO_PROJECTS_OPERATIONS",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene(None)
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene({})
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_operation_metadata_hygiene(
            {"paths": {"/api/crm/contacts": {"get": {"operationId": "list_crm"}}}}
        )
        == expected
    )


# ─── summarize_projects_query_parameter_schema_hygiene (pure helper) ─────────


def test_query_parameter_schema_hygiene_clean_and_real_fastapi_schema():
    """Parámetros query en snake_case con schema tipado (y schema real de FastAPI) -> HYGIENIC_QUERY_PARAMETER_CONTRACTS."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "parameters": [
                        {
                            "in": "query",
                            "name": "page_size",
                            "schema": {"type": "integer"},
                        },
                        {
                            "in": "query",
                            "name": "status_filter",
                            "schema": {
                                "anyOf": [{"type": "string"}, {"type": "null"}]
                            },
                        },
                    ]
                }
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
        openapi
    )
    assert res == {
        "total_query_parameters": 2,
        "operations_with_query_params": 1,
        "non_snake_case_query_params": [],
        "untyped_query_params": [],
        "is_query_contract_hygienic": True,
        "query_hygiene_posture": "HYGIENIC_QUERY_PARAMETER_CONTRACTS",
    }

    real_res = (
        audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
            None
        )
    )
    assert real_res["total_query_parameters"] > 0
    assert real_res["operations_with_query_params"] > 0
    assert real_res["non_snake_case_query_params"] == []
    assert real_res["untyped_query_params"] == []
    assert real_res["is_query_contract_hygienic"] is True
    assert real_res["query_hygiene_posture"] == "HYGIENIC_QUERY_PARAMETER_CONTRACTS"


def test_query_parameter_schema_hygiene_untyped_schema():
    """Parámetro query con schema vacío o sin type/anyOf/$ref -> UNTYPED_QUERY_PARAMETER_SCHEMA."""
    openapi = {
        "paths": {
            "/api/projects": {
                "get": {
                    "parameters": [
                        {"in": "query", "name": "filter_by", "schema": {}},
                        {
                            "in": "query",
                            "name": "limit",
                            "schema": {"type": "integer"},
                        },
                    ]
                }
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
        openapi
    )
    assert res == {
        "total_query_parameters": 2,
        "operations_with_query_params": 1,
        "non_snake_case_query_params": [],
        "untyped_query_params": ["GET /api/projects:filter_by"],
        "is_query_contract_hygienic": False,
        "query_hygiene_posture": "UNTYPED_QUERY_PARAMETER_SCHEMA",
    }


def test_query_parameter_schema_hygiene_non_snake_case():
    """Parámetro query en camelCase con schema válido -> NON_SNAKE_CASE_QUERY_PARAMETER."""
    openapi = {
        "paths": {
            "/api/projects/tasks": {
                "get": {
                    "parameters": [
                        {
                            "in": "query",
                            "name": "pageSize",
                            "schema": {"type": "integer"},
                        }
                    ]
                }
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
        openapi
    )
    assert res == {
        "total_query_parameters": 1,
        "operations_with_query_params": 1,
        "non_snake_case_query_params": ["GET /api/projects/tasks:pageSize"],
        "untyped_query_params": [],
        "is_query_contract_hygienic": False,
        "query_hygiene_posture": "NON_SNAKE_CASE_QUERY_PARAMETER",
    }


def test_query_parameter_schema_hygiene_no_query_parameters():
    """Esquema sin parámetros query en /api/projects -> NO_QUERY_PARAMETERS_DEFINED."""
    expected = {
        "total_query_parameters": 0,
        "operations_with_query_params": 0,
        "non_snake_case_query_params": [],
        "untyped_query_params": [],
        "is_query_contract_hygienic": False,
        "query_hygiene_posture": "NO_QUERY_PARAMETERS_DEFINED",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
            {}
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_query_parameter_schema_hygiene(
            {
                "paths": {
                    "/api/projects/{project_id}": {
                        "get": {
                            "parameters": [
                                {
                                    "in": "path",
                                    "name": "project_id",
                                    "schema": {"type": "string"},
                                }
                            ]
                        }
                    }
                }
            }
        )
        == expected
    )
