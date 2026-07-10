"""Test that all CRUD functions are properly exported.

Prevents regressions where new functions are added to crud modules
but not exported in __init__.py, causing AttributeError at runtime.
"""
import importlib
import inspect

import pytest


# SQLAlchemy symbols that appear in dir() but aren't CRUD functions
_SKIP_NAMES = {"func", "or_", "and_", "not_", "true", "false", "null", "literal_column"}


def _get_crud_functions(module_name: str) -> list[str]:
    """Get all public function names from a crud module, excluding imports."""
    module = importlib.import_module(module_name)
    funcs = []
    for name in dir(module):
        if name.startswith("_") or name in _SKIP_NAMES:
            continue
        obj = getattr(module, name)
        if inspect.isfunction(obj) and obj.__module__ == module_name:
            funcs.append(name)
    return funcs


def test_cms_crud_exports():
    """All public functions in crud.cms must be accessible via crud.*."""
    from backend import crud

    missing = [name for name in _get_crud_functions("backend.crud.cms") if not hasattr(crud, name)]
    assert not missing, (
        f"Functions in crud.cms not exported in crud.__init__: {missing}. "
        "Add them to backend/crud/__init__.py."
    )


def test_crm_crud_exports():
    """All public functions in crud.crm must be accessible via crud.*."""
    from backend import crud

    missing = [name for name in _get_crud_functions("backend.crud.crm") if not hasattr(crud, name)]
    assert not missing, (
        f"Functions in crud.crm not exported in crud.__init__: {missing}. "
        "Add them to backend/crud/__init__.py."
    )
