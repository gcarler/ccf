import pytest
from backend.app import ROUTER_REGISTRY

CORE_MODULES = [
    "Academy",
    "projects",
    "crm",
    "agenda",
    "evangelism",
    "Finance Suite",
    "messaging",
    "admin",
    "surveys",
]

def test_router_registry_has_all_core_modules():
    assert len(ROUTER_REGISTRY) >= 30, f"Expected >=30 registered routers, got {len(ROUTER_REGISTRY)}"

    all_prefixes = [prefix for _, prefix, _ in ROUTER_REGISTRY]
    all_tags = []
    for _, _, tags in ROUTER_REGISTRY:
        if tags:
            all_tags.extend(tags)

    for mod in CORE_MODULES:
        has_tag = any(mod.lower() in t.lower() for t in all_tags)
        has_prefix = any(mod.lower() in p.lower() for p in all_prefixes)
        assert has_tag or has_prefix, f"Module {mod} must be present in ROUTER_REGISTRY"

def test_routers_have_active_routes():
    total_routes = sum(len(router.routes) for router, _, _ in ROUTER_REGISTRY)
    assert total_routes > 500, f"Expected >500 total routes across registry, got {total_routes}"

def test_kernel_personas_registered():
    kernel_entry = next((entry for entry in ROUTER_REGISTRY if entry[1] == "/api" and entry[2] == ["kernel"]), None)
    assert kernel_entry is not None, "Kernel router must be registered in ROUTER_REGISTRY"
    assert len(kernel_entry[0].routes) > 0, "Kernel router must have routes"
