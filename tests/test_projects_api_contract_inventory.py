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


# ─── summarize_projects_request_body_schema_hygiene (pure helper) ────────────


def test_request_body_schema_hygiene_clean_and_real_fastapi_schema():
    """requestBody con content-type soportado y schema tipado (y schema real de FastAPI) -> HYGIENIC_REQUEST_BODY_CONTRACTS."""
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
            "/api/projects/{project_id}/upload": {
                "post": {
                    "requestBody": {
                        "content": {
                            "multipart/form-data": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            },
        }
    }

    res = audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
        openapi
    )
    assert res == {
        "operations_with_request_body": 2,
        "empty_content_operations": [],
        "unsupported_media_types": [],
        "untyped_request_body_schemas": [],
        "is_request_body_hygienic": True,
        "request_body_posture": "HYGIENIC_REQUEST_BODY_CONTRACTS",
    }

    real_res = (
        audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
            None
        )
    )
    assert real_res["operations_with_request_body"] > 0
    assert real_res["empty_content_operations"] == []
    assert real_res["unsupported_media_types"] == []
    assert real_res["untyped_request_body_schemas"] == []
    assert real_res["is_request_body_hygienic"] is True
    assert real_res["request_body_posture"] == "HYGIENIC_REQUEST_BODY_CONTRACTS"


def test_request_body_schema_hygiene_empty_content():
    """requestBody con content vacío -> EMPTY_REQUEST_BODY_CONTENT."""
    openapi = {
        "paths": {
            "/api/projects": {
                "post": {
                    "requestBody": {"required": True, "content": {}},
                }
            }
        }
    }

    res = audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
        openapi
    )
    assert res == {
        "operations_with_request_body": 1,
        "empty_content_operations": ["POST /api/projects"],
        "unsupported_media_types": [],
        "untyped_request_body_schemas": [],
        "is_request_body_hygienic": False,
        "request_body_posture": "EMPTY_REQUEST_BODY_CONTENT",
    }


def test_request_body_schema_hygiene_untyped_and_unsupported_media_type():
    """requestBody sin schema tipado o con MIME no soportado -> UNTYPED_REQUEST_BODY_SCHEMA / UNSUPPORTED_REQUEST_BODY_MEDIA_TYPE."""
    untyped_openapi = {
        "paths": {
            "/api/projects": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {}}
                        }
                    }
                }
            }
        }
    }
    res_untyped = (
        audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
            untyped_openapi
        )
    )
    assert res_untyped == {
        "operations_with_request_body": 1,
        "empty_content_operations": [],
        "unsupported_media_types": [],
        "untyped_request_body_schemas": ["POST /api/projects:application/json"],
        "is_request_body_hygienic": False,
        "request_body_posture": "UNTYPED_REQUEST_BODY_SCHEMA",
    }

    unsupported_openapi = {
        "paths": {
            "/api/projects/raw": {
                "put": {
                    "requestBody": {
                        "content": {
                            "text/plain": {"schema": {"type": "string"}}
                        }
                    }
                }
            }
        }
    }
    res_unsupported = (
        audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
            unsupported_openapi
        )
    )
    assert res_unsupported == {
        "operations_with_request_body": 1,
        "empty_content_operations": [],
        "unsupported_media_types": ["PUT /api/projects/raw:text/plain"],
        "untyped_request_body_schemas": [],
        "is_request_body_hygienic": False,
        "request_body_posture": "UNSUPPORTED_REQUEST_BODY_MEDIA_TYPE",
    }


def test_request_body_schema_hygiene_no_request_bodies():
    """Esquema sin requestBody en /api/projects -> NO_REQUEST_BODIES_DEFINED."""
    expected = {
        "operations_with_request_body": 0,
        "empty_content_operations": [],
        "unsupported_media_types": [],
        "untyped_request_body_schemas": [],
        "is_request_body_hygienic": False,
        "request_body_posture": "NO_REQUEST_BODIES_DEFINED",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
            {}
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_request_body_schema_hygiene(
            {
                "paths": {
                    "/api/projects": {"get": {"operationId": "list_projects"}},
                    "/api/projects/action": {"post": {"requestBody": {}}},
                }
            }
        )
        == expected
    )


def test_json_response_schema_hygiene_hygienic():
    """Esquema sintético con respuestas 200/201 tipadas ($ref, array con items, object con properties) -> HYGIENIC_JSON_RESPONSE_CONTRACTS."""
    schema = {
        "paths": {
            "/api/projects": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/ProjectOut"
                                        },
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProjectOut"
                                    }
                                }
                            }
                        }
                    }
                },
            },
            "/api/projects/summary": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "total": {"type": "integer"}
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/projects/export": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "text/csv": {"schema": {"type": "string"}}
                            }
                        }
                    }
                }
            },
            "/api/other": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {"application/json": {"schema": {}}}
                        }
                    }
                }
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
        schema
    )
    assert res == {
        "json_success_responses_count": 3,
        "ref_backed_responses_count": 1,
        "empty_json_response_schemas": [],
        "untyped_json_response_schemas": [],
        "is_json_response_hygienic": True,
        "response_schema_posture": "HYGIENIC_JSON_RESPONSE_CONTRACTS",
    }

    real_res = (
        audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
            None
        )
    )
    assert real_res["json_success_responses_count"] > 0
    assert real_res["ref_backed_responses_count"] > 0
    assert real_res["untyped_json_response_schemas"] == []


def test_json_response_schema_hygiene_empty_schema():
    """Respuesta 200 con schema vacío ({} o None) -> EMPTY_JSON_RESPONSE_SCHEMA."""
    schema = {
        "paths": {
            "/api/projects/ping": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {"application/json": {"schema": {}}}
                        }
                    }
                },
                "post": {
                    "responses": {
                        "201": {
                            "content": {"application/json": {}}
                        }
                    }
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
        schema
    )
    assert res == {
        "json_success_responses_count": 2,
        "ref_backed_responses_count": 0,
        "empty_json_response_schemas": [
            "GET /api/projects/ping:200",
            "POST /api/projects/ping:201",
        ],
        "untyped_json_response_schemas": [],
        "is_json_response_hygienic": False,
        "response_schema_posture": "EMPTY_JSON_RESPONSE_SCHEMA",
    }


def test_json_response_schema_hygiene_untyped_schema():
    """Respuesta 200 con schema sin claves estructurales ($ref, type, anyOf, oneOf, allOf) -> UNTYPED_JSON_RESPONSE_SCHEMA."""
    schema = {
        "paths": {
            "/api/projects/raw": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"title": "RawPayload"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {"description": "Created payload"}
                                }
                            }
                        }
                    }
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
        schema
    )
    assert res == {
        "json_success_responses_count": 2,
        "ref_backed_responses_count": 0,
        "empty_json_response_schemas": [],
        "untyped_json_response_schemas": [
            "GET /api/projects/raw:200",
            "POST /api/projects/raw:201",
        ],
        "is_json_response_hygienic": False,
        "response_schema_posture": "UNTYPED_JSON_RESPONSE_SCHEMA",
    }


def test_json_response_schema_hygiene_no_responses():
    """Esquema sin respuestas JSON 200/201 en /api/projects -> NO_JSON_SUCCESS_RESPONSES."""
    expected = {
        "json_success_responses_count": 0,
        "ref_backed_responses_count": 0,
        "empty_json_response_schemas": [],
        "untyped_json_response_schemas": [],
        "is_json_response_hygienic": False,
        "response_schema_posture": "NO_JSON_SUCCESS_RESPONSES",
    }
    assert (
        audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
            {}
        )
        == expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_json_response_schema_hygiene(
            {
                "paths": {
                    "/api/projects/delete": {
                        "delete": {
                            "responses": {"204": {"description": "No Content"}}
                        }
                    }
                }
            }
        )
        == expected
    )


def test_security_scheme_hygiene_protected_operations():
    """Operaciones protegidas con esquemas definidos y respuestas 401/403 (is_hygienic=True)."""
    schema = {
        "security": [{"BearerAuth": []}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"},
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                },
            }
        },
        "paths": {
            "/api/projects": {
                "get": {
                    "security": [],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "201": {"description": "Created"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                    },
                },
            },
            "/projects/{project_id}": {
                "patch": {
                    "security": [{"BearerAuth": []}, {"ApiKeyAuth": []}],
                    "responses": {
                        "200": {"description": "Updated"},
                        "403": {"description": "Forbidden"},
                    },
                }
            },
            "/api/other": {
                "delete": {
                    "security": [],
                    "responses": {"204": {"description": "Deleted"}},
                }
            },
        },
    }
    res = audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
        schema
    )
    assert res == {
        "evaluated_operation_count": 3,
        "defined_security_schemes": ["ApiKeyAuth", "BearerAuth"],
        "has_global_security": True,
        "explicit_security_ops": [
            "POST /api/projects",
            "PATCH /projects/{project_id}",
        ],
        "public_override_ops": ["GET /api/projects"],
        "auth_error_documented_ops": [
            "POST /api/projects",
            "PATCH /projects/{project_id}",
        ],
        "unprotected_write_ops": [],
        "undefined_scheme_refs": [],
        "is_hygienic": True,
    }


def test_security_scheme_hygiene_unprotected_write_ops():
    """Detección de mutaciones con security=[] en unprotected_write_ops (is_hygienic=False)."""
    schema = {
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "paths": {
            "/api/projects": {
                "post": {
                    "security": [],
                    "responses": {"201": {"description": "Created"}},
                },
                "delete": {
                    "security": [],
                    "responses": {"204": {"description": "Deleted"}},
                },
            }
        },
    }
    res = audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
        schema
    )
    assert res["evaluated_operation_count"] == 2
    assert res["public_override_ops"] == [
        "POST /api/projects",
        "DELETE /api/projects",
    ]
    assert res["unprotected_write_ops"] == [
        "POST /api/projects",
        "DELETE /api/projects",
    ]
    assert res["is_hygienic"] is False


def test_security_scheme_hygiene_undefined_scheme_refs():
    """Detección de referencias a esquemas inexistentes en undefined_scheme_refs (is_hygienic=False)."""
    schema = {
        "components": {
            "securitySchemes": {
                "BearerAuth": {"type": "http", "scheme": "bearer"}
            }
        },
        "paths": {
            "/api/projects/tasks": {
                "get": {
                    "security": [{"GhostOAuth2": ["read:tasks"]}],
                    "responses": {"401": {"description": "Unauthorized"}},
                },
                "put": {
                    "security": [{"BearerAuth": [], "UnknownKey": []}],
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }
    res = audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
        schema
    )
    assert res["defined_security_schemes"] == ["BearerAuth"]
    assert res["undefined_scheme_refs"] == [
        "GET /api/projects/tasks:GhostOAuth2",
        "PUT /api/projects/tasks:UnknownKey",
    ]
    assert res["is_hygienic"] is False


def test_security_scheme_hygiene_empty_and_live_openapi():
    """Manejo de schema vacío/None y auditoría del esquema OpenAPI en vivo de la app FastAPI."""
    empty_expected = {
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
    assert (
        audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_security_scheme_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_operation_count"] > 0
    assert live_res["unprotected_write_ops"] == []
    assert live_res["undefined_scheme_refs"] == []
    assert live_res["is_hygienic"] is True


def test_deprecation_and_sunset_hygiene_compliant():
    """Endpoints activos y deprecados con x-sunset y guía de migración completos (is_hygienic=True)."""
    schema = {
        "paths": {
            "/api/projects": {
                "get": {
                    "summary": "List projects",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "deprecated": True,
                    "x-sunset": "2027-01-01",
                    "x-replacement-path": "/api/v2/projects",
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/projects/legacy": {
                "delete": {
                    "deprecated": True,
                    "x-sunset": "2026-12-31",
                    "description": "Deprecated endpoint: please migrate to /api/projects/{id}/archive.",
                    "responses": {"204": {"description": "Deleted"}},
                }
            },
            "/api/other": {
                "get": {
                    "deprecated": True,
                    "responses": {"200": {"description": "OK"}},
                }
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
        schema
    )
    assert res == {
        "evaluated_operation_count": 3,
        "active_ops": ["GET /api/projects"],
        "deprecated_ops": [
            "POST /api/projects",
            "DELETE /projects/legacy",
        ],
        "deprecated_missing_sunset_ops": [],
        "deprecated_missing_migration_guide_ops": [],
        "inconsistent_sunset_on_active_ops": [],
        "is_hygienic": True,
    }


def test_deprecation_and_sunset_hygiene_missing_sunset_or_migration():
    """Endpoints deprecados sin x-sunset o sin guía de migración (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/old-export": {
                "get": {
                    "deprecated": True,
                    "description": "Legacy CSV export endpoint.",
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "deprecated": True,
                    "x-sunset": "2027-06-30",
                    "description": "Legacy export trigger endpoint.",
                    "responses": {"200": {"description": "OK"}},
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
        schema
    )
    assert res["evaluated_operation_count"] == 2
    assert res["deprecated_ops"] == [
        "GET /api/projects/old-export",
        "POST /api/projects/old-export",
    ]
    assert res["deprecated_missing_sunset_ops"] == [
        "GET /api/projects/old-export"
    ]
    assert res["deprecated_missing_migration_guide_ops"] == [
        "GET /api/projects/old-export",
        "POST /api/projects/old-export",
    ]
    assert res["is_hygienic"] is False


def test_deprecation_and_sunset_hygiene_inconsistent_sunset_on_active():
    """Endpoints activos con x-sunset inconsistente (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/active-with-sunset": {
                "patch": {
                    "deprecated": False,
                    "x-sunset": "2027-03-01",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
        schema
    )
    assert res["active_ops"] == ["PATCH /api/projects/active-with-sunset"]
    assert res["inconsistent_sunset_on_active_ops"] == [
        "PATCH /api/projects/active-with-sunset"
    ]
    assert res["is_hygienic"] is False


def test_deprecation_and_sunset_hygiene_empty_and_live_openapi():
    """Esquema OpenAPI en vivo de la app FastAPI y manejo de schema vacío/None."""
    empty_expected = {
        "evaluated_operation_count": 0,
        "active_ops": [],
        "deprecated_ops": [],
        "deprecated_missing_sunset_ops": [],
        "deprecated_missing_migration_guide_ops": [],
        "inconsistent_sunset_on_active_ops": [],
        "is_hygienic": True,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_deprecation_and_sunset_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_operation_count"] > 0
    assert live_res["deprecated_missing_sunset_ops"] == []
    assert live_res["deprecated_missing_migration_guide_ops"] == []
    assert live_res["inconsistent_sunset_on_active_ops"] == []
    assert live_res["is_hygienic"] is True


def test_error_response_contract_hygiene_compliant():
    """Endpoints con errores 404/422 descritos (is_hygienic=True)."""
    schema = {
        "paths": {
            "/api/projects": {
                "post": {
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {
                        "201": {"description": "Created"},
                        "422": {"description": "Validation Error"},
                    },
                }
            },
            "/projects/{project_id}": {
                "get": {
                    "parameters": [{"name": "project_id", "in": "path"}],
                    "responses": {
                        "200": {"description": "OK"},
                        "404": {"description": "Not Found"},
                        "422": {"description": "Validation Error"},
                    },
                }
            },
            "/api/other": {
                "get": {
                    "responses": {"200": {"description": "OK"}}
                }
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
        schema
    )
    assert res == {
        "evaluated_operation_count": 2,
        "ops_with_error_responses": [
            "POST /api/projects",
            "GET /projects/{project_id}",
        ],
        "ops_missing_all_error_responses": [],
        "parameterized_ops_missing_404": [],
        "input_ops_missing_validation_error": [],
        "undescribed_error_responses": [],
        "is_hygienic": True,
    }


def test_error_response_contract_hygiene_missing_all_error_responses():
    """Endpoints sin ninguna respuesta de error (ops_missing_all_error_responses, is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/health": {
                "get": {
                    "responses": {"200": {"description": "Healthy"}}
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
        schema
    )
    assert res["evaluated_operation_count"] == 1
    assert res["ops_with_error_responses"] == []
    assert res["ops_missing_all_error_responses"] == [
        "GET /api/projects/health"
    ]
    assert res["is_hygienic"] is False


def test_error_response_contract_hygiene_missing_404_validation_and_undescribed():
    """Detección de parameterized_ops_missing_404, input_ops_missing_validation_error y undescribed_error_responses (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/{project_id}": {
                "patch": {
                    "parameters": [{"name": "project_id", "in": "path"}],
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {
                        "200": {"description": "Updated"},
                        "403": {"description": "   "},
                        "500": {"description": "Internal Server Error"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
        schema
    )
    assert res["ops_with_error_responses"] == [
        "PATCH /api/projects/{project_id}"
    ]
    assert res["parameterized_ops_missing_404"] == [
        "PATCH /api/projects/{project_id}"
    ]
    assert res["input_ops_missing_validation_error"] == [
        "PATCH /api/projects/{project_id}"
    ]
    assert res["undescribed_error_responses"] == [
        "PATCH /api/projects/{project_id}:403"
    ]
    assert res["is_hygienic"] is False


def test_error_response_contract_hygiene_empty_and_live_openapi():
    """Esquema OpenAPI en vivo de la app FastAPI y manejo de schema vacío/None."""
    empty_expected = {
        "evaluated_operation_count": 0,
        "ops_with_error_responses": [],
        "ops_missing_all_error_responses": [],
        "parameterized_ops_missing_404": [],
        "input_ops_missing_validation_error": [],
        "undescribed_error_responses": [],
        "is_hygienic": True,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_error_response_contract_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_operation_count"] > 0
    assert live_res["undescribed_error_responses"] == []


def test_mutation_idempotency_and_header_hygiene_compliant():
    """Mutaciones con headers de idempotencia, 201, 409 y response headers tipados (is_hygienic=True)."""
    schema = {
        "paths": {
            "/api/projects": {
                "get": {
                    "responses": {"200": {"description": "OK"}}
                },
                "post": {
                    "parameters": [
                        {
                            "name": "Idempotency-Key",
                            "in": "header",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "201": {
                            "description": "Created",
                            "headers": {
                                "X-RateLimit-Remaining": {
                                    "schema": {"type": "integer"}
                                },
                                "X-Request-Id": {
                                    "$ref": "#/components/headers/RequestId"
                                },
                            },
                        },
                        "409": {"description": "Conflict"},
                    },
                },
            },
            "/projects/{project_id}": {
                "patch": {
                    "parameters": [
                        {
                            "name": "X-Request-Id",
                            "in": "header",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"description": "Updated"},
                        "409": {"description": "Conflict"},
                    },
                }
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
        schema
    )
    assert res == {
        "evaluated_mutation_count": 2,
        "post_mutation_ops": ["POST /api/projects"],
        "post_ops_with_201_created": ["POST /api/projects"],
        "ops_with_idempotency_header": [
            "POST /api/projects",
            "PATCH /projects/{project_id}",
        ],
        "ops_with_conflict_409_response": [
            "POST /api/projects",
            "PATCH /projects/{project_id}",
        ],
        "malformed_header_param_ops": [],
        "untyped_response_headers": [],
        "is_hygienic": True,
    }


def test_mutation_idempotency_and_header_hygiene_malformed_header_param():
    """Detección de malformed_header_param_ops (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/tasks": {
                "post": {
                    "parameters": [
                        {
                            "name": "   ",
                            "in": "header",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"201": {"description": "Created"}},
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
        schema
    )
    assert res["evaluated_mutation_count"] == 1
    assert res["malformed_header_param_ops"] == ["POST /api/projects/tasks"]
    assert res["is_hygienic"] is False


def test_mutation_idempotency_and_header_hygiene_untyped_response_headers():
    """Detección de untyped_response_headers (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/tasks/{task_id}": {
                "put": {
                    "responses": {
                        "200": {
                            "description": "Updated",
                            "headers": {
                                "X-Retry-After": {"description": "Seconds"},
                                "X-Invalid": "not-a-dict",
                            },
                        }
                    }
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
        schema
    )
    assert res["untyped_response_headers"] == [
        "PUT /api/projects/tasks/{task_id}:X-Retry-After",
        "PUT /api/projects/tasks/{task_id}:X-Invalid",
    ]
    assert res["is_hygienic"] is False


def test_mutation_idempotency_and_header_hygiene_empty_and_live_openapi():
    """Esquema OpenAPI en vivo de la app FastAPI y manejo de schema vacío/None."""
    empty_expected = {
        "evaluated_mutation_count": 0,
        "post_mutation_ops": [],
        "post_ops_with_201_created": [],
        "ops_with_idempotency_header": [],
        "ops_with_conflict_409_response": [],
        "malformed_header_param_ops": [],
        "untyped_response_headers": [],
        "is_hygienic": True,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_mutation_idempotency_and_header_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_mutation_count"] > 0
    assert len(live_res["post_mutation_ops"]) > 0
    assert live_res["malformed_header_param_ops"] == []
    assert live_res["untyped_response_headers"] == []
    assert live_res["is_hygienic"] is True


def test_export_and_binary_response_hygiene_compliant():
    """Operaciones de exportación con binary/json media types y header Content-Disposition (is_hygienic=True)."""
    schema = {
        "paths": {
            "/api/projects/{project_id}/export.pdf": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "PDF Export",
                            "headers": {
                                "Content-Disposition": {
                                    "schema": {"type": "string"}
                                }
                            },
                            "content": {"application/pdf": {}},
                        }
                    }
                }
            },
            "/projects/{project_id}/report": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Executive Report JSON",
                            "content": {"application/json": {}},
                        }
                    }
                }
            },
            "/api/projects": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "List",
                            "content": {"application/json": {}},
                        }
                    }
                }
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
        schema
    )
    assert res == {
        "evaluated_export_op_count": 2,
        "export_report_ops": [
            "GET /api/projects/{project_id}/export.pdf",
            "GET /projects/{project_id}/report",
        ],
        "binary_stream_export_ops": [
            "GET /api/projects/{project_id}/export.pdf"
        ],
        "json_export_ops": ["GET /projects/{project_id}/report"],
        "ops_with_content_disposition_header": [
            "GET /api/projects/{project_id}/export.pdf"
        ],
        "export_ops_missing_content_type": [],
        "mismatched_export_media_type_ops": [],
        "is_hygienic": True,
    }


def test_export_and_binary_response_hygiene_missing_content_type():
    """Operación de exportación sin media types en respuestas 2xx -> export_ops_missing_content_type (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/download": {
                "get": {
                    "responses": {"200": {"description": "File stream"}}
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
        schema
    )
    assert res["evaluated_export_op_count"] == 1
    assert res["export_ops_missing_content_type"] == [
        "GET /api/projects/download"
    ]
    assert res["is_hygienic"] is False


def test_export_and_binary_response_hygiene_mismatched_pdf_media_type():
    """Operación con 'pdf' en el path pero media type incompatible (ej. text/csv) -> mismatched_export_media_type_ops (is_hygienic=False)."""
    schema = {
        "paths": {
            "/api/projects/report/pdf": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Wrong media type for PDF route",
                            "content": {"text/csv": {}},
                        }
                    }
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
        schema
    )
    assert res["mismatched_export_media_type_ops"] == [
        "GET /api/projects/report/pdf"
    ]
    assert res["is_hygienic"] is False


def test_export_and_binary_response_hygiene_empty_and_live_openapi():
    """Manejo de schema vacío/None y auditoría del esquema OpenAPI en vivo de la app FastAPI."""
    empty_expected = {
        "evaluated_export_op_count": 0,
        "export_report_ops": [],
        "binary_stream_export_ops": [],
        "json_export_ops": [],
        "ops_with_content_disposition_header": [],
        "export_ops_missing_content_type": [],
        "mismatched_export_media_type_ops": [],
        "is_hygienic": True,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_export_and_binary_response_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_export_op_count"] > 0
    assert live_res["export_ops_missing_content_type"] == []
    assert live_res["mismatched_export_media_type_ops"] == []
    assert live_res["is_hygienic"] is True


def test_path_parameter_uuid_hygiene_clean():
    """Parámetros de ruta declarados como required=True y con esquema UUID/pattern/enum válido -> is_path_param_hygiene_clean=True."""
    schema = {
        "paths": {
            "/api/projects/{project_id}/tasks/{id}": {
                "parameters": [
                    {
                        "name": "project_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "format": "uuid"},
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {
                                "anyOf": [
                                    {
                                        "type": "string",
                                        "pattern": "^[0-9a-f-]{36}$",
                                    }
                                ]
                            },
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            },
            "/projects/{slug}": {
                "get": {
                    "parameters": [
                        {
                            "name": "slug",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/projects": {
                "get": {"responses": {"200": {"description": "List"}}}
            },
        }
    }
    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
        schema
    )
    assert res == {
        "total_parameterized_operations": 2,
        "total_path_parameters": 3,
        "undeclared_or_optional_path_params": [],
        "untyped_id_path_params": [],
        "is_path_param_hygiene_clean": True,
    }


def test_path_parameter_uuid_hygiene_undeclared_or_optional():
    """Detecta placeholders de ruta no declarados o con required != True."""
    schema = {
        "paths": {
            "/api/projects/{project_id}/items/{item_id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "project_id",
                            "in": "path",
                            "required": False,
                            "schema": {"type": "string", "format": "uuid"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
        schema
    )
    assert res["total_parameterized_operations"] == 1
    assert res["total_path_parameters"] == 2
    assert res["undeclared_or_optional_path_params"] == [
        "GET /api/projects/{project_id}/items/{item_id}:project_id",
        "GET /api/projects/{project_id}/items/{item_id}:item_id",
    ]
    assert res["is_path_param_hygiene_clean"] is False


def test_path_parameter_uuid_hygiene_untyped_id_params():
    """Detecta parámetros *_id o id sin format=uuid, pattern ni enum sobre string."""
    schema = {
        "paths": {
            "/api/projects/{project_id}/tasks/{id}": {
                "delete": {
                    "parameters": [
                        {
                            "name": "project_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {"204": {"description": "Deleted"}},
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
        schema
    )
    assert res["undeclared_or_optional_path_params"] == []
    assert res["untyped_id_path_params"] == [
        "DELETE /api/projects/{project_id}/tasks/{id}:project_id",
        "DELETE /api/projects/{project_id}/tasks/{id}:id",
    ]
    assert res["is_path_param_hygiene_clean"] is False


def test_path_parameter_uuid_hygiene_empty_and_live_openapi():
    """Manejo de schema vacío/None y auditoría sobre el esquema OpenAPI real de la aplicación."""
    empty_expected = {
        "total_parameterized_operations": 0,
        "total_path_parameters": 0,
        "undeclared_or_optional_path_params": [],
        "untyped_id_path_params": [],
        "is_path_param_hygiene_clean": False,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_path_parameter_uuid_hygiene(
            app.openapi()
        )
    )
    assert live_res["total_parameterized_operations"] > 0
    assert live_res["total_path_parameters"] > 0
    assert live_res["undeclared_or_optional_path_params"] == []


def test_collection_pagination_hygiene_clean():
    """Operaciones GET de colección con envoltorio paginado, par de paginación y límite máximo acotado -> is_pagination_hygiene_clean=True."""
    schema = {
        "components": {
            "schemas": {
                "ProjectListEnvelope": {
                    "type": "object",
                    "properties": {
                        "items": {"type": "array", "items": {"type": "object"}},
                        "total": {"type": "integer"},
                    },
                }
            }
        },
        "paths": {
            "/api/projects": {
                "get": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {"type": "integer", "maximum": 100},
                        },
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer", "minimum": 0},
                        },
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProjectListEnvelope"
                                    }
                                }
                            }
                        }
                    },
                }
            },
            "/projects/{project_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array"}
                                }
                            }
                        }
                    }
                }
            },
        },
    }
    res = audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
        schema
    )
    assert res == {
        "total_collection_get_operations": 1,
        "unpaginated_collection_operations": [],
        "unbounded_limit_operations": [],
        "bare_array_response_operations": [],
        "is_pagination_hygiene_clean": True,
    }


def test_collection_pagination_hygiene_unpaginated_and_bare_array():
    """Detecta operaciones de colección sin par de paginación y con bare array directo."""
    schema = {
        "paths": {
            "/api/projects/tasks": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
        schema
    )
    assert res == {
        "total_collection_get_operations": 1,
        "unpaginated_collection_operations": ["GET /api/projects/tasks"],
        "unbounded_limit_operations": [],
        "bare_array_response_operations": ["GET /api/projects/tasks"],
        "is_pagination_hygiene_clean": False,
    }


def test_collection_pagination_hygiene_unbounded_limit():
    """Detecta parámetros limit o page_size sin maximum ni exclusiveMaximum."""
    schema = {
        "paths": {
            "/api/projects/risks": {
                "get": {
                    "parameters": [
                        {
                            "name": "page",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "page_size",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "results": {"type": "array"}
                                        },
                                    }
                                }
                            }
                        }
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
        schema
    )
    assert res["total_collection_get_operations"] == 1
    assert res["unpaginated_collection_operations"] == []
    assert res["unbounded_limit_operations"] == ["GET /api/projects/risks"]
    assert res["bare_array_response_operations"] == []
    assert res["is_pagination_hygiene_clean"] is False


def test_collection_pagination_hygiene_empty_and_live_openapi():
    """Manejo de schema vacío/None y auditoría sobre el esquema OpenAPI real de la aplicación."""
    empty_expected = {
        "total_collection_get_operations": 0,
        "unpaginated_collection_operations": [],
        "unbounded_limit_operations": [],
        "bare_array_response_operations": [],
        "is_pagination_hygiene_clean": False,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_collection_pagination_hygiene(
            app.openapi()
        )
    )
    assert live_res["total_collection_get_operations"] > 0


def test_datetime_and_temporal_field_hygiene_clean():
    """Propiedades *_at con format=date-time y *_date con format in {date, date-time} -> is_temporal_hygiene_clean=True."""
    schema = {
        "paths": {
            "/api/projects": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/MilestoneOut"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ProjectSummary": {
                    "type": "object",
                    "properties": {
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "start_date": {"type": "string", "format": "date"},
                    },
                },
                "MilestoneOut": {
                    "type": "object",
                    "properties": {
                        "due_date": {
                            "anyOf": [
                                {"type": "string", "format": "date-time"},
                                {"type": "null"},
                            ]
                        }
                    },
                },
                "UnrelatedAudit": {
                    "type": "object",
                    "properties": {
                        "logged_at": {"type": "integer"}
                    },
                },
            }
        },
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_fields"] == 3
    assert res["unformatted_datetime_fields"] == []
    assert res["unformatted_date_fields"] == []
    assert res["non_string_temporal_fields"] == []
    assert res["is_temporal_hygiene_clean"] is True
    assert res["total_temporal_properties_inspected"] == 3
    assert res["unformatted_temporal_properties"] == []
    assert res["date_only_on_timestamp_properties"] == []
    assert res["is_temporal_hygiene_compliant"] is True


def test_datetime_and_temporal_field_hygiene_unformatted_fields():
    """Detecta propiedades *_at sin format=date-time y *_date sin format in {date, date-time}."""
    schema = {
        "components": {
            "schemas": {
                "ProjectTaskInput": {
                    "type": "object",
                    "properties": {
                        "completed_at": {"type": "string"},
                        "target_date": {"type": "string", "format": "uuid"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_fields"] == 2
    assert res["unformatted_datetime_fields"] == [
        "ProjectTaskInput.completed_at"
    ]
    assert res["unformatted_date_fields"] == ["ProjectTaskInput.target_date"]
    assert res["non_string_temporal_fields"] == []
    assert res["is_temporal_hygiene_clean"] is False


def test_datetime_and_temporal_field_hygiene_non_string_fields():
    """Detecta campos temporales declarados como integer/number/boolean/array/object."""
    schema = {
        "components": {
            "schemas": {
                "ProjectBaseline": {
                    "type": "object",
                    "properties": {
                        "approved_at": {"type": "integer"},
                        "baseline_date": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "null"},
                            ]
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["non_string_temporal_fields"] == [
        "ProjectBaseline.approved_at",
        "ProjectBaseline.baseline_date",
    ]
    assert res["unformatted_datetime_fields"] == [
        "ProjectBaseline.approved_at"
    ]
    assert res["unformatted_date_fields"] == ["ProjectBaseline.baseline_date"]
    assert res["is_temporal_hygiene_clean"] is False


def test_datetime_and_temporal_field_hygiene_empty_and_live_openapi():
    """Manejo de schema vacío/None y auditoría sobre el esquema OpenAPI real de la aplicación."""
    for empty_in in (None, {}):
        res_empty = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
            empty_in
        )
        assert res_empty["total_temporal_fields"] == 0
        assert res_empty["unformatted_datetime_fields"] == []
        assert res_empty["unformatted_date_fields"] == []
        assert res_empty["non_string_temporal_fields"] == []
        assert res_empty["is_temporal_hygiene_clean"] is False

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
            app.openapi()
        )
    )
    assert live_res["total_temporal_fields"] > 0
    assert live_res["non_string_temporal_fields"] == []


def test_numeric_bounds_and_currency_hygiene_clean_schema():
    """Esquema limpio: porcentajes con min y max, montos no negativos y conteos enteros no negativos."""
    schema = {
        "paths": {
            "/api/projects/wbs": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/WbsRollupOut"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "ProjectFinancials": {
                    "type": "object",
                    "properties": {
                        "completion_pct": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 100.0,
                        },
                        "approved_budget": {
                            "type": "number",
                            "minimum": 0.0,
                        },
                        "management_reserve": {
                            "anyOf": [
                                {"type": "number", "exclusiveMinimum": 0},
                                {"type": "null"},
                            ]
                        },
                        "task_count": {
                            "type": "integer",
                            "minimum": 0,
                        },
                        "status_pct": {
                            "type": "string",
                        },
                    },
                },
                "WbsRollupOut": {
                    "type": "object",
                    "properties": {
                        "variance_percentage": {
                            "type": "number",
                            "exclusiveMinimum": -100.0,
                            "exclusiveMaximum": 100.0,
                        },
                        "actual_cost": {
                            "type": "number",
                            "minimum": 0,
                        },
                    },
                },
                "UnrelatedInvoice": {
                    "type": "object",
                    "properties": {
                        "total_amount": {"type": "number"},
                        "item_count": {"type": "number"},
                    },
                },
            }
        },
    }
    res = audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
        schema
    )
    assert res == {
        "total_numeric_domain_fields": 6,
        "unbounded_percentage_fields": [],
        "negative_allowed_monetary_fields": [],
        "non_integer_or_negative_count_fields": [],
        "is_numeric_bounds_hygiene_clean": True,
    }


def test_numeric_bounds_and_currency_hygiene_unbounded_percentage_and_monetary():
    """Detecta porcentajes sin cotas completas y montos monetarios que permiten negativos."""
    schema = {
        "components": {
            "schemas": {
                "ProjectBudgetUpdate": {
                    "type": "object",
                    "properties": {
                        "progress_pct": {"type": "number", "minimum": 0},
                        "margin_percentage": {"type": "number", "maximum": 100},
                        "planned_cost": {"type": "number"},
                        "contingency_reserve": {
                            "type": "number",
                            "minimum": -10.0,
                        },
                        "service_fee": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "null"},
                            ]
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
        schema
    )
    assert res["total_numeric_domain_fields"] == 5
    assert res["unbounded_percentage_fields"] == [
        "ProjectBudgetUpdate.margin_percentage",
        "ProjectBudgetUpdate.progress_pct",
    ]
    assert res["negative_allowed_monetary_fields"] == [
        "ProjectBudgetUpdate.contingency_reserve",
        "ProjectBudgetUpdate.planned_cost",
        "ProjectBudgetUpdate.service_fee",
    ]
    assert res["non_integer_or_negative_count_fields"] == []
    assert res["is_numeric_bounds_hygiene_clean"] is False


def test_numeric_bounds_and_currency_hygiene_invalid_count_fields():
    """Detecta conteos (*_count) declarados como number (no integer) o sin cota inferior >= 0."""
    schema = {
        "components": {
            "schemas": {
                "ProjectMetrics": {
                    "type": "object",
                    "properties": {
                        "defect_count": {"type": "number", "minimum": 0},
                        "milestone_count": {"type": "integer"},
                        "risk_count": {"type": "integer", "minimum": -1},
                        "valid_count": {"type": "integer", "minimum": 0},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
        schema
    )
    assert res["total_numeric_domain_fields"] == 4
    assert res["non_integer_or_negative_count_fields"] == [
        "ProjectMetrics.defect_count",
        "ProjectMetrics.milestone_count",
        "ProjectMetrics.risk_count",
    ]
    assert res["is_numeric_bounds_hygiene_clean"] is False


def test_numeric_bounds_and_currency_hygiene_empty_and_live_openapi():
    """Manejo de entrada vacía/None y verificación contra el esquema OpenAPI real."""
    empty_expected = {
        "total_numeric_domain_fields": 0,
        "unbounded_percentage_fields": [],
        "negative_allowed_monetary_fields": [],
        "non_integer_or_negative_count_fields": [],
        "is_numeric_bounds_hygiene_clean": False,
    }
    assert (
        audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
            None
        )
        == empty_expected
    )
    assert (
        audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
            {}
        )
        == empty_expected
    )

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_numeric_bounds_and_currency_hygiene(
            app.openapi()
        )
    )
    assert live_res["total_numeric_domain_fields"] >= 0
    assert isinstance(live_res["unbounded_percentage_fields"], list)
    assert isinstance(live_res["negative_allowed_monetary_fields"], list)
    assert isinstance(live_res["non_integer_or_negative_count_fields"], list)


def test_enum_and_status_field_hygiene_clean_and_live_schema():
    """Esquema sintético con enums válidos (directos y vía $ref) + esquema real de FastAPI con strict_enum=False."""
    schema = {
        "components": {
            "schemas": {
                "RagStatusEnum": {
                    "type": "string",
                    "enum": ["GREEN", "AMBER", "RED"],
                },
                "ProjectSummaryOut": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["DRAFT", "ACTIVE", "CLOSED"],
                        },
                        "rag_status": {
                            "$ref": "#/components/schemas/RagStatusEnum"
                        },
                        "priority": {
                            "type": "string",
                            "maxLength": 32,
                        },
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
        schema, strict_enum=False
    )
    assert res == {
        "total_categorical_fields": 3,
        "enum_backed_fields_count": 2,
        "constrained_string_fields_count": 1,
        "unconstrained_categorical_fields": [],
        "invalid_enum_definitions": [],
        "is_hygienic": True,
    }

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
            app.openapi(), strict_enum=False
        )
    )
    assert live_res["total_categorical_fields"] > 0
    assert live_res["unconstrained_categorical_fields"] == []
    assert live_res["invalid_enum_definitions"] == []
    assert live_res["is_hygienic"] is True


def test_enum_and_status_field_hygiene_strict_vs_non_strict_unconstrained():
    """Detecta campos categóricos sin enum cuando strict_enum=True o sin tipo válido cuando strict_enum=False."""
    schema = {
        "components": {
            "schemas": {
                "ProjectIssueInput": {
                    "type": "object",
                    "properties": {
                        "severity": {
                            "type": "string",
                            "enum": ["LOW", "HIGH"],
                        },
                        "priority": {"type": "string", "maxLength": 20},
                        "resolution_mode": {"type": "string"},
                        "health_status": {},
                        "decision_status": {"type": "integer"},
                    },
                }
            }
        }
    }
    res_relaxed = audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
        schema, strict_enum=False
    )
    assert res_relaxed["total_categorical_fields"] == 5
    assert res_relaxed["enum_backed_fields_count"] == 1
    assert res_relaxed["constrained_string_fields_count"] == 2
    assert res_relaxed["unconstrained_categorical_fields"] == [
        "ProjectIssueInput.decision_status",
        "ProjectIssueInput.health_status",
    ]
    assert res_relaxed["is_hygienic"] is False

    res_strict = audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
        schema, strict_enum=True
    )
    assert res_strict["total_categorical_fields"] == 5
    assert res_strict["enum_backed_fields_count"] == 1
    assert res_strict["constrained_string_fields_count"] == 1
    assert res_strict["unconstrained_categorical_fields"] == [
        "ProjectIssueInput.decision_status",
        "ProjectIssueInput.health_status",
        "ProjectIssueInput.priority",
        "ProjectIssueInput.resolution_mode",
    ]
    assert res_strict["is_hygienic"] is False


def test_enum_and_status_field_hygiene_invalid_enum_definitions():
    """Detecta definiciones enum inválidas (lista vacía, valores duplicados, string en blanco '   ')."""
    schema = {
        "components": {
            "schemas": {
                "EmptyLifecycleEnum": {
                    "type": "string",
                    "enum": [],
                },
                "ProjectRiskItem": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["OPEN", "OPEN"],
                        },
                        "severidad": {
                            "type": "string",
                            "enum": ["HIGH", "   "],
                        },
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
        schema, strict_enum=False
    )
    assert res["invalid_enum_definitions"] == [
        "EmptyLifecycleEnum",
        "ProjectRiskItem.severidad",
        "ProjectRiskItem.status",
    ]
    assert res["is_hygienic"] is False


def test_enum_and_status_field_hygiene_nullable_anyof_oneof_support():
    """Soporta propiedades nullable con anyOf/oneOf que referencian un enum válido."""
    schema = {
        "components": {
            "schemas": {
                "SalienceClassEnum": {
                    "type": "string",
                    "enum": ["DEFINITIVE", "DOMINANT", "DORMANT"],
                },
                "ProjectStakeholderOut": {
                    "type": "object",
                    "properties": {
                        "salience_class": {
                            "anyOf": [
                                {
                                    "$ref": "#/components/schemas/SalienceClassEnum"
                                },
                                {"type": "null"},
                            ]
                        },
                        "estado": {
                            "oneOf": [
                                {
                                    "type": "string",
                                    "enum": ["ACTIVO", "INACTIVO"],
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_enum_and_status_field_hygiene(
        schema, strict_enum=True
    )
    assert res == {
        "total_categorical_fields": 2,
        "enum_backed_fields_count": 2,
        "constrained_string_fields_count": 0,
        "unconstrained_categorical_fields": [],
        "invalid_enum_definitions": [],
        "is_hygienic": True,
    }


def test_request_string_bounds_hygiene_clean_and_live_schema():
    """Esquema sintético de mutación con maxLength válido + esquema real de FastAPI con strict_short_field_bounds=False."""
    schema = {
        "components": {
            "schemas": {
                "ProjectCreate": {
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 200,
                        },
                        "code": {
                            "type": "string",
                            "pattern": "^[A-Z0-9_-]{3,20}$",
                        },
                    },
                },
                "ProjectSummaryOut": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_request_string_bounds_hygiene(
        schema, strict_short_field_bounds=True
    )
    assert res == {
        "evaluated_schemas_count": 1,
        "total_string_fields": 2,
        "bounded_string_fields_count": 2,
        "unbounded_short_string_fields": [],
        "invalid_string_bounds": [],
        "is_hygienic": True,
    }

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_request_string_bounds_hygiene(
            app.openapi(), strict_short_field_bounds=False
        )
    )
    assert live_res["evaluated_schemas_count"] > 0
    assert live_res["total_string_fields"] > 0
    assert live_res["invalid_string_bounds"] == []
    assert live_res["unbounded_short_string_fields"] == []
    assert live_res["is_hygienic"] is True


def test_request_string_bounds_hygiene_strict_short_fields_unbounded():
    """Detecta campos cortos (title, name, code, slug) sin maxLength/pattern cuando strict_short_field_bounds=True."""
    schema = {
        "components": {
            "schemas": {
                "ProjectMilestoneUpdate": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "name": {"type": "string"},
                        "project_code": {"type": "string"},
                        "slug": {"type": "string"},
                        "contact_email": {
                            "type": "string",
                            "format": "email",
                        },
                        "description": {"type": "string"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_request_string_bounds_hygiene(
        schema, strict_short_field_bounds=True
    )
    assert res["evaluated_schemas_count"] == 1
    assert res["total_string_fields"] == 6
    assert res["bounded_string_fields_count"] == 0
    assert res["unbounded_short_string_fields"] == [
        "ProjectMilestoneUpdate.name",
        "ProjectMilestoneUpdate.project_code",
        "ProjectMilestoneUpdate.slug",
        "ProjectMilestoneUpdate.title",
    ]
    assert res["is_hygienic"] is False


def test_request_string_bounds_hygiene_invalid_string_bounds():
    """Detecta cotas inválidas (maxLength=0, minLength=-1, minLength > maxLength)."""
    schema = {
        "components": {
            "schemas": {
                "ProjectTaskInput": {
                    "type": "object",
                    "properties": {
                        "zero_max": {"type": "string", "maxLength": 0},
                        "negative_min": {"type": "string", "minLength": -1},
                        "inverted_bounds": {
                            "type": "string",
                            "minLength": 50,
                            "maxLength": 10,
                        },
                        "valid_title": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 120,
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_request_string_bounds_hygiene(
        schema, strict_short_field_bounds=False
    )
    assert res["total_string_fields"] == 4
    assert res["bounded_string_fields_count"] == 1
    assert res["invalid_string_bounds"] == [
        "ProjectTaskInput.inverted_bounds",
        "ProjectTaskInput.negative_min",
        "ProjectTaskInput.zero_max",
    ]
    assert res["is_hygienic"] is False


def test_request_string_bounds_hygiene_nullable_and_excluded_formats():
    """Soporta propiedades nullable con anyOf/oneOf y excluye campos uuid/date-time/enum."""
    schema = {
        "components": {
            "schemas": {
                "ProjectPatchPayload": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "format": "uuid"},
                        "due_at": {"type": "string", "format": "date-time"},
                        "status": {
                            "type": "string",
                            "enum": ["OPEN", "CLOSED"],
                        },
                        "title": {
                            "anyOf": [
                                {"type": "string", "maxLength": 150},
                                {"type": "null"},
                            ]
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_request_string_bounds_hygiene(
        schema, strict_short_field_bounds=True
    )
    assert res == {
        "evaluated_schemas_count": 1,
        "total_string_fields": 1,
        "bounded_string_fields_count": 1,
        "unbounded_short_string_fields": [],
        "invalid_string_bounds": [],
        "is_hygienic": True,
    }


def test_array_property_hygiene_clean_and_live_schema():
    """Esquema sintético con arrays acotados (maxItems, uniqueItems, items con $ref) + esquema real de FastAPI con strict_request_max_items=False."""
    schema = {
        "components": {
            "schemas": {
                "TaskBatchUpdate": {
                    "type": "object",
                    "properties": {
                        "task_ids": {
                            "type": "array",
                            "items": {"type": "string", "format": "uuid"},
                            "minItems": 1,
                            "maxItems": 100,
                            "uniqueItems": True,
                        },
                        "items": {
                            "type": "array",
                            "items": {
                                "$ref": "#/components/schemas/TaskPatchItem"
                            },
                            "maxItems": 50,
                        },
                    },
                },
                "ProjectSummaryOut": {
                    "type": "object",
                    "properties": {
                        "tags": {"type": "array", "items": {}},
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_array_property_hygiene(
        schema, strict_request_max_items=True
    )
    assert res == {
        "evaluated_schemas_count": 1,
        "total_array_fields": 2,
        "bounded_or_unique_arrays_count": 2,
        "missing_items_schema_fields": [],
        "invalid_array_bounds": [],
        "unbounded_request_array_fields": [],
        "is_hygienic": True,
    }

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_array_property_hygiene(
            app.openapi(), strict_request_max_items=False
        )
    )
    assert live_res["evaluated_schemas_count"] > 0
    assert live_res["total_array_fields"] > 0
    assert live_res["missing_items_schema_fields"] == []
    assert live_res["invalid_array_bounds"] == []
    assert live_res["unbounded_request_array_fields"] == []
    assert live_res["is_hygienic"] is True


def test_array_property_hygiene_strict_unbounded_request_arrays():
    """Detecta arrays sin maxItems cuando strict_request_max_items=True."""
    schema = {
        "components": {
            "schemas": {
                "ProjectBulkCreate": {
                    "type": "object",
                    "properties": {
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "uniqueItems": True,
                        },
                        "deliverables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 25,
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_array_property_hygiene(
        schema, strict_request_max_items=True
    )
    assert res["total_array_fields"] == 2
    assert res["bounded_or_unique_arrays_count"] == 2
    assert res["unbounded_request_array_fields"] == [
        "ProjectBulkCreate.tags"
    ]
    assert res["is_hygienic"] is False


def test_array_property_hygiene_missing_items_and_invalid_bounds():
    """Detecta items faltante/vacío y cotas inválidas (maxItems=0, minItems=-1, minItems > maxItems)."""
    schema = {
        "components": {
            "schemas": {
                "ProjectWbsInput": {
                    "type": "object",
                    "properties": {
                        "raw_list": {"type": "array", "items": {}},
                        "no_items_key": {"type": "array"},
                        "zero_max": {
                            "type": "array",
                            "items": {"type": "string"},
                            "maxItems": 0,
                        },
                        "neg_min": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": -1,
                        },
                        "inverted": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 10,
                            "maxItems": 5,
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_array_property_hygiene(
        schema, strict_request_max_items=False
    )
    assert res["total_array_fields"] == 5
    assert res["missing_items_schema_fields"] == [
        "ProjectWbsInput.no_items_key",
        "ProjectWbsInput.raw_list",
    ]
    assert res["invalid_array_bounds"] == [
        "ProjectWbsInput.inverted",
        "ProjectWbsInput.neg_min",
        "ProjectWbsInput.zero_max",
    ]
    assert res["is_hygienic"] is False


def test_array_property_hygiene_nullable_anyof_oneof_support():
    """Soporta propiedades array nullable con anyOf/oneOf."""
    schema = {
        "components": {
            "schemas": {
                "ProjectFilterRequest": {
                    "type": "object",
                    "properties": {
                        "assignee_ids": {
                            "anyOf": [
                                {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "format": "uuid",
                                    },
                                    "maxItems": 20,
                                },
                                {"type": "null"},
                            ]
                        },
                        "labels": {
                            "oneOf": [
                                {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "maxItems": 10,
                                },
                                {"type": "null"},
                            ]
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_array_property_hygiene(
        schema, strict_request_max_items=True
    )
    assert res == {
        "evaluated_schemas_count": 1,
        "total_array_fields": 2,
        "bounded_or_unique_arrays_count": 2,
        "missing_items_schema_fields": [],
        "invalid_array_bounds": [],
        "unbounded_request_array_fields": [],
        "is_hygienic": True,
    }


def test_schema_required_and_default_hygiene_clean_and_live_schema():
    """Esquema sintético íntegro + esquema real de FastAPI (is_hygienic=True)."""
    schema = {
        "components": {
            "schemas": {
                "ProjectCreate": {
                    "type": "object",
                    "required": ["title", "code"],
                    "properties": {
                        "title": {"type": "string"},
                        "code": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["DRAFT", "ACTIVE"],
                            "default": "DRAFT",
                        },
                        "is_active": {
                            "type": "boolean",
                            "default": True,
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_schema_required_and_default_hygiene(
        schema
    )
    assert res == {
        "evaluated_schemas_count": 1,
        "total_required_declarations": 2,
        "malformed_required_lists": [],
        "dangling_required_properties": [],
        "contradictory_required_null_defaults": [],
        "type_mismatched_defaults": [],
        "is_hygienic": True,
    }

    from backend.app import app

    live_res = (
        audit_projects_api_contracts.summarize_projects_schema_required_and_default_hygiene(
            app.openapi()
        )
    )
    assert live_res["evaluated_schemas_count"] > 0
    assert live_res["total_required_declarations"] > 0
    assert live_res["malformed_required_lists"] == []
    assert live_res["dangling_required_properties"] == []
    assert live_res["contradictory_required_null_defaults"] == []
    assert live_res["type_mismatched_defaults"] == []
    assert live_res["is_hygienic"] is True


def test_schema_required_and_default_hygiene_malformed_and_dangling_required():
    """Detecta required malformado (lista vacía, duplicados) y propiedades en required que no existen en properties."""
    schema = {
        "components": {
            "schemas": {
                "EmptyRequiredSchema": {
                    "type": "object",
                    "required": [],
                    "properties": {"name": {"type": "string"}},
                },
                "DuplicateAndDanglingSchema": {
                    "type": "object",
                    "required": ["title", "title", "ghost_field"],
                    "properties": {"title": {"type": "string"}},
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_schema_required_and_default_hygiene(
        schema
    )
    assert res["evaluated_schemas_count"] == 2
    assert res["malformed_required_lists"] == [
        "DuplicateAndDanglingSchema",
        "EmptyRequiredSchema",
    ]
    assert res["dangling_required_properties"] == [
        "DuplicateAndDanglingSchema.ghost_field"
    ]
    assert res["is_hygienic"] is False


def test_schema_required_and_default_hygiene_contradictory_required_null_defaults():
    """Detecta contradicción entre campo obligatorio en required y default: None explícito."""
    schema = {
        "components": {
            "schemas": {
                "ProjectBaselineCreate": {
                    "type": "object",
                    "required": ["project_id", "reason"],
                    "properties": {
                        "project_id": {"type": "string", "format": "uuid"},
                        "reason": {"type": "string", "default": None},
                        "notes": {"type": "string", "default": None},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_schema_required_and_default_hygiene(
        schema
    )
    assert res["contradictory_required_null_defaults"] == [
        "ProjectBaselineCreate.reason"
    ]
    assert res["is_hygienic"] is False


def test_schema_required_and_default_hygiene_type_mismatched_defaults_and_anyof():
    """Detecta defaults incompatibles con type o fuera de enum y soporta anyOf/oneOf."""
    schema = {
        "components": {
            "schemas": {
                "ProjectConfigPayload": {
                    "type": "object",
                    "properties": {
                        "bad_enum": {
                            "type": "string",
                            "enum": ["LOW", "HIGH"],
                            "default": "MEDIUM",
                        },
                        "bad_int_bool": {
                            "type": "integer",
                            "default": True,
                        },
                        "bad_str": {
                            "type": "string",
                            "default": 42,
                        },
                        "bad_array": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": "not-a-list",
                        },
                        "valid_nullable": {
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "null"},
                            ],
                            "default": 10,
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_schema_required_and_default_hygiene(
        schema
    )
    assert res["type_mismatched_defaults"] == [
        "ProjectConfigPayload.bad_array",
        "ProjectConfigPayload.bad_enum",
        "ProjectConfigPayload.bad_int_bool",
        "ProjectConfigPayload.bad_str",
    ]
    assert res["is_hygienic"] is False


def test_temporal_timestamp_format_hygiene_compliant_with_deadlines_and_refs():
    """Verifica campos *_at, *_timestamp, *_date y *_deadline válidos (incluyendo $ref y anyOf)."""
    schema = {
        "components": {
            "schemas": {
                "IsoTimestampDef": {
                    "type": "string",
                    "format": "date-time",
                },
                "ProjectTimelineOut": {
                    "type": "object",
                    "properties": {
                        "created_at": {
                            "type": "string",
                            "format": "date-time",
                        },
                        "sync_timestamp": {
                            "$ref": "#/components/schemas/IsoTimestampDef"
                        },
                        "submission_deadline": {
                            "anyOf": [
                                {"type": "string", "format": "date"},
                                {"type": "null"},
                            ]
                        },
                        "baseline_start_date": {
                            "type": "string",
                            "format": "date",
                        },
                    },
                },
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_properties_inspected"] == 4
    assert res["unformatted_temporal_properties"] == []
    assert res["date_only_on_timestamp_properties"] == []
    assert res["is_temporal_hygiene_compliant"] is True


def test_temporal_timestamp_format_hygiene_detects_date_only_on_timestamp_fields():
    """Detecta campos *_at y *_timestamp que declaran format='date' en vez de 'date-time'."""
    schema = {
        "components": {
            "schemas": {
                "TaskAuditRecord": {
                    "type": "object",
                    "properties": {
                        "approved_at": {"type": "string", "format": "date"},
                        "event_timestamp": {
                            "anyOf": [
                                {"type": "string", "format": "date"},
                                {"type": "null"},
                            ]
                        },
                        "due_date": {"type": "string", "format": "date"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_properties_inspected"] == 3
    assert res["unformatted_temporal_properties"] == []
    assert res["date_only_on_timestamp_properties"] == [
        "TaskAuditRecord.approved_at",
        "TaskAuditRecord.event_timestamp",
    ]
    assert res["is_temporal_hygiene_compliant"] is False


def test_temporal_timestamp_format_hygiene_detects_unformatted_properties():
    """Detecta propiedades temporales sin format ISO-8601 ('date-time' o 'date')."""
    schema = {
        "components": {
            "schemas": {
                "MilestoneScheduleInput": {
                    "type": "object",
                    "properties": {
                        "closed_at": {"type": "string"},
                        "gate_deadline": {"type": "string"},
                        "audit_timestamp": {"type": "integer"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_properties_inspected"] == 3
    assert res["unformatted_temporal_properties"] == [
        "MilestoneScheduleInput.audit_timestamp",
        "MilestoneScheduleInput.closed_at",
        "MilestoneScheduleInput.gate_deadline",
    ]
    assert res["is_temporal_hygiene_compliant"] is False


def test_temporal_timestamp_format_hygiene_ignores_non_project_schemas():
    """Ignora esquemas ajenos al dominio de proyectos y retorna cumplimiento limpio en esquema vacío."""
    schema = {
        "components": {
            "schemas": {
                "AuthSessionRecord": {
                    "type": "object",
                    "properties": {
                        "created_at": {"type": "string"},
                        "login_timestamp": {"type": "string", "format": "date"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_datetime_and_temporal_field_hygiene(
        schema
    )
    assert res["total_temporal_properties_inspected"] == 0
    assert res["unformatted_temporal_properties"] == []
    assert res["date_only_on_timestamp_properties"] == []
    assert res["is_temporal_hygiene_compliant"] is True


def test_uuid_and_identifier_format_hygiene_live_openapi():
    """Valida contra el esquema OpenAPI real que todos los identificadores de proyectos sean de tipo string."""
    res = audit_projects_api_contracts.summarize_projects_uuid_and_identifier_field_hygiene()
    assert res["total_identifier_properties_inspected"] > 0
    assert res["non_string_identifier_properties"] == []
    assert res["is_identifier_type_hygiene_compliant"] is True
    assert (
        len(res["uuid_formatted_properties"]) + len(res["plain_string_identifier_properties"])
        == res["total_identifier_properties_inspected"]
    )


def test_uuid_and_identifier_format_hygiene_classifies_uuid_vs_plain_string_including_anyof():
    """Clasifica propiedades con format=uuid frente a string plano, incluyendo uniones anyOf con null."""
    schema = {
        "components": {
            "schemas": {
                "ProjectTaskRead": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "format": "uuid"},
                        "parent_task_id": {
                            "anyOf": [
                                {"type": "string", "format": "uuid"},
                                {"type": "null"},
                            ]
                        },
                        "external_reference_id": {"type": "string"},
                        "assignee_uuid": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "null"},
                            ]
                        },
                        "title": {"type": "string"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_uuid_and_identifier_field_hygiene(
        schema
    )
    assert res["total_identifier_properties_inspected"] == 4
    assert res["uuid_formatted_properties"] == [
        "ProjectTaskRead.id",
        "ProjectTaskRead.parent_task_id",
    ]
    assert res["plain_string_identifier_properties"] == [
        "ProjectTaskRead.assignee_uuid",
        "ProjectTaskRead.external_reference_id",
    ]
    assert res["non_string_identifier_properties"] == []
    assert res["is_identifier_type_hygiene_compliant"] is True


def test_uuid_and_identifier_format_hygiene_detects_non_string_identifiers():
    """Detecta identificadores tipados como integer, number o boolean como incumplimiento de higiene."""
    schema = {
        "components": {
            "schemas": {
                "WbsNodeCreate": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "project_id": {
                            "anyOf": [
                                {"type": "number"},
                                {"type": "null"},
                            ]
                        },
                        "legacy_uuid": {"type": "boolean"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_uuid_and_identifier_field_hygiene(
        schema
    )
    assert res["total_identifier_properties_inspected"] == 3
    assert res["uuid_formatted_properties"] == []
    assert res["plain_string_identifier_properties"] == []
    assert res["non_string_identifier_properties"] == [
        "WbsNodeCreate.id",
        "WbsNodeCreate.legacy_uuid",
        "WbsNodeCreate.project_id",
    ]
    assert res["is_identifier_type_hygiene_compliant"] is False


def test_uuid_and_identifier_format_hygiene_ignores_non_project_schemas():
    """Ignora esquemas fuera del dominio de proyectos y retorna cumplimiento limpio."""
    schema = {
        "components": {
            "schemas": {
                "FinanceLedgerEntry": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "account_id": {"type": "number"},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_uuid_and_identifier_field_hygiene(
        schema
    )
    assert res["total_identifier_properties_inspected"] == 0
    assert res["uuid_formatted_properties"] == []
    assert res["plain_string_identifier_properties"] == []
    assert res["non_string_identifier_properties"] == []
    assert res["is_identifier_type_hygiene_compliant"] is True


def test_nullable_and_union_branch_hygiene_live_openapi():
    """Valida contra el esquema OpenAPI real que todas las uniones anyOf/oneOf sean coherentes."""
    res = audit_projects_api_contracts.summarize_projects_nullable_and_union_branch_hygiene()
    assert res["total_properties_inspected"] > 0
    assert res["total_union_properties"] > 0
    assert res["degenerate_single_branch_unions"] == []
    assert res["null_only_unions"] == []
    assert res["duplicate_branch_unions"] == []
    assert res["is_union_branch_hygiene_compliant"] is True


def test_nullable_and_union_branch_hygiene_detects_degenerate_and_null_only_unions():
    """Detecta uniones con menos de 2 ramas o compuestas únicamente por ramas null."""
    schema = {
        "components": {
            "schemas": {
                "ProjectRiskUpdate": {
                    "type": "object",
                    "properties": {
                        "single_branch_field": {
                            "anyOf": [{"type": "string"}],
                        },
                        "only_null_field": {
                            "oneOf": [{"type": "null"}, {"type": "null"}],
                        },
                        "valid_nullable_field": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_nullable_and_union_branch_hygiene(
        schema
    )
    assert res["total_properties_inspected"] == 3
    assert res["total_union_properties"] == 3
    assert res["degenerate_single_branch_unions"] == [
        "ProjectRiskUpdate.single_branch_field"
    ]
    assert res["null_only_unions"] == ["ProjectRiskUpdate.only_null_field"]
    assert res["duplicate_branch_unions"] == ["ProjectRiskUpdate.only_null_field"]
    assert res["is_union_branch_hygiene_compliant"] is False


def test_nullable_and_union_branch_hygiene_detects_duplicate_branches():
    """Detecta ramas duplicadas idénticas dentro de anyOf o oneOf."""
    schema = {
        "components": {
            "schemas": {
                "WbsNodePatch": {
                    "type": "object",
                    "properties": {
                        "duplicated_string_union": {
                            "anyOf": [
                                {"type": "string", "maxLength": 100},
                                {"maxLength": 100, "type": "string"},
                                {"type": "null"},
                            ]
                        },
                        "clean_polymorphic_union": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/ProjectTaskRead"},
                                {"$ref": "#/components/schemas/MilestoneScheduleInput"},
                            ]
                        },
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_nullable_and_union_branch_hygiene(
        schema
    )
    assert res["total_properties_inspected"] == 2
    assert res["total_union_properties"] == 2
    assert res["degenerate_single_branch_unions"] == []
    assert res["null_only_unions"] == []
    assert res["duplicate_branch_unions"] == ["WbsNodePatch.duplicated_string_union"]
    assert res["is_union_branch_hygiene_compliant"] is False


def test_nullable_and_union_branch_hygiene_ignores_non_project_schemas():
    """Ignora esquemas ajenos al dominio de proyectos y retorna cumplimiento limpio."""
    schema = {
        "components": {
            "schemas": {
                "ExternalAuthPayload": {
                    "type": "object",
                    "properties": {
                        "broken_union": {"anyOf": [{"type": "null"}]},
                    },
                }
            }
        }
    }
    res = audit_projects_api_contracts.summarize_projects_nullable_and_union_branch_hygiene(
        schema
    )
    assert res["total_properties_inspected"] == 0
    assert res["total_union_properties"] == 0
    assert res["degenerate_single_branch_unions"] == []
    assert res["null_only_unions"] == []
    assert res["duplicate_branch_unions"] == []
    assert res["is_union_branch_hygiene_compliant"] is True
