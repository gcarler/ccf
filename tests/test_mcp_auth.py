"""Paridad RBAC entre REST y las superficies MCP privadas.

Regresión del Hallazgo 1: los allowances por rol que ``require_permission``
(REST) concede a roles de plataforma sin permisos granulares explícitos
(pastor/coordinador/docente en academy/projects/wiki, etc.) deben aplicar
también en ``require_mcp_permission`` vía la matriz compartida
``role_allows_permission``.
"""

from __future__ import annotations

import asyncio

import pytest

from backend.core.permissions import create_access_token
from tests.conftest import TestingSessionLocal, seed_user_with_role


class TestMcpRoleMatrixParity:
    @pytest.mark.parametrize(
        "role_name, permission, expected",
        [
            # pastor: acceso pastoral total (CRM, evangelismo, academia,
            # proyectos, wiki) pero no CMS.
            ("PASTOR", "academy:read", True),
            ("PASTOR", "academy:edit", True),
            ("PASTOR", "academy:manage", True),
            ("PASTOR", "projects:manage", True),
            ("PASTOR", "wiki:edit", True),
            ("PASTOR", "crm:manage", True),
            ("PASTOR", "evangelism:manage", True),
            ("PASTOR", "cms:manage", False),
            ("PASTOR", "finance:read", False),
            # coordinador: lee/edita/gestiona academia y proyectos, lee/edita
            # evangelismo (no manage), wiki de lectura, sin CMS/finanzas.
            ("COORDINADOR", "academy:read", True),
            ("COORDINADOR", "academy:edit", True),
            ("COORDINADOR", "academy:manage", True),
            ("COORDINADOR", "projects:read", True),
            ("COORDINADOR", "wiki:read", True),
            ("COORDINADOR", "evangelism:read", True),
            ("COORDINADOR", "evangelism:manage", False),
            ("COORDINADOR", "crm:manage", False),
            ("COORDINADOR", "cms:manage", False),
            # docente: academia read/edit (no manage), proyectos, wiki.
            ("DOCENTE", "academy:read", True),
            ("DOCENTE", "academy:edit", True),
            ("DOCENTE", "academy:manage", False),
            ("DOCENTE", "projects:read", True),
            ("DOCENTE", "wiki:edit", True),
            ("DOCENTE", "evangelism:read", False),
            ("DOCENTE", "finance:read", False),
        ],
    )
    def test_require_mcp_permission_matches_rest_role_matrix(
        self, db_session, role_name, permission, expected
    ):
        from backend.mcp_auth import require_mcp_permission

        user, _persona, _sede = seed_user_with_role(
            db_session,
            role_name=role_name,
            email=f"{role_name.lower()}-{permission.replace(':', '-')}@test.com",
        )
        if expected:
            require_mcp_permission(db_session, user, permission)  # no debe lanzar
        else:
            with pytest.raises(PermissionError, match="Permisos insuficientes"):
                require_mcp_permission(db_session, user, permission)

    def test_effective_scopes_include_role_based_permissions(self, db_session):
        from backend.mcp_auth import _effective_user_scopes

        user, _persona, _sede = seed_user_with_role(
            db_session, role_name="PASTOR", email="pastor-scopes@test.com"
        )
        scopes = _effective_user_scopes(db_session, user)
        assert "academy:edit" in scopes
        assert "projects:manage" in scopes
        assert "wiki:edit" in scopes
        assert "crm:manage" in scopes
        assert "cms:manage" not in scopes
        assert "finance:read" not in scopes

    def test_verify_token_scopes_include_role_based_permissions(self, db_session, monkeypatch):
        import backend.mcp_auth as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)

        user, _persona, _sede = seed_user_with_role(
            db_session, role_name="COORDINADOR", email="coordinador-token@test.com"
        )
        token = create_access_token({"sub": str(user.id)})
        access_token = asyncio.run(module.CcfJwtTokenVerifier().verify_token(token))

        assert access_token is not None
        assert "academy:read" in access_token.scopes
        assert "evangelism:edit" in access_token.scopes
        assert "cms:manage" not in access_token.scopes
        assert "crm:manage" not in access_token.scopes
