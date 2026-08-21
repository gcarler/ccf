"""Paridad RBAC entre REST y las superficies MCP privadas.

Regresión del Hallazgo 1: los allowances por rol que ``require_permission``
(REST) concede a roles de plataforma sin permisos granulares explícitos
(pastor/coordinador/docente en academy/projects/wiki, etc.) deben aplicar
también en ``require_mcp_permission`` vía la matriz compartida
``role_allows_permission``.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.core.permissions import PERMISSIONS, create_access_token, require_permission
from backend.models_auth import RolPlataforma, UsuarioRolModulo
from tests.conftest import TestingSessionLocal, seed_user_with_role


def _user_with_module_role(db_session, role_name, modulo, permisos, email):
    """Crea un usuario sin permisos granulares en su rol base y un grant modular."""
    user, _persona, _sede = seed_user_with_role(db_session, role_name=role_name, email=email, permisos={})
    module_role = RolPlataforma(
        id=uuid.uuid4(),
        nombre=f"{role_name}-{modulo}-{uuid.uuid4().hex[:8]}",
        permisos=permisos,
    )
    db_session.add(module_role)
    db_session.flush()
    db_session.add(UsuarioRolModulo(user_id=user.id, modulo=modulo, rol_id=module_role.id))
    db_session.commit()
    return user


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


class TestMcpRestParityGranularPermissions:
    """Paridad REST vs MCP para usuarios con permisos granulares (UsuarioRolModulo).

    Ambas superficies deben resolver los grants modulares desde la misma fuente
    de verdad (get_user_effective_permissions): la jerarquía (manage→edit→read)
    y las denegaciones deben coincidir permiso por permiso.
    """

    @staticmethod
    def _rest_allows(check, request, user, db):
        try:
            asyncio.run(check(request, current_user=user, db=db))
            return True
        except HTTPException as exc:
            if exc.status_code == 403:
                return False
            raise

    @staticmethod
    def _mcp_allows(db, user, permission):
        from backend.mcp_auth import require_mcp_permission

        try:
            require_mcp_permission(db, user, permission)
            return True
        except PermissionError:
            return False

    def _assert_full_parity(self, db_session, user):
        request = SimpleNamespace(state=SimpleNamespace())
        for permission in PERMISSIONS:
            rest = self._rest_allows(require_permission(permission), request, user, db_session)
            mcp = self._mcp_allows(db_session, user, permission)
            assert rest == mcp, f"Paridad rota para {permission}: REST={rest} MCP={mcp}"

    def test_miembro_with_granular_crm_grants(self, db_session):
        user = _user_with_module_role(
            db_session, "miembro", "crm", {"crm:read": "allow", "crm:edit": "allow"}, "miembro-crm@test.com"
        )
        self._assert_full_parity(db_session, user)
        # El grant granular es el que decide en CRM (miembro no tiene allowance).
        assert self._mcp_allows(db_session, user, "crm:read") is True
        assert self._mcp_allows(db_session, user, "crm:edit") is True
        assert self._mcp_allows(db_session, user, "crm:manage") is False

    def test_custom_role_with_granular_finance_manage(self, db_session):
        user = _user_with_module_role(
            db_session, "tesorero", "finance", {"finance:manage": "allow"}, "tesorero@test.com"
        )
        self._assert_full_parity(db_session, user)
        # manage implica read/edit por jerarquía en ambas fronteras.
        assert self._mcp_allows(db_session, user, "finance:read") is True
        assert self._mcp_allows(db_session, user, "finance:edit") is True
        assert self._mcp_allows(db_session, user, "finance:manage") is True
        assert self._mcp_allows(db_session, user, "cms:edit") is False

    def test_soft_deleted_module_role_revokes_grant_in_both(self, db_session):
        user = _user_with_module_role(
            db_session, "miembro", "crm", {"crm:manage": "allow"}, "miembro-crm-del@test.com"
        )
        assert self._mcp_allows(db_session, user, "crm:manage") is True

        db_session.query(UsuarioRolModulo).filter(UsuarioRolModulo.user_id == user.id).update(
            {UsuarioRolModulo.deleted_at: datetime.now(timezone.utc)}
        )
        db_session.commit()

        self._assert_full_parity(db_session, user)
        assert self._mcp_allows(db_session, user, "crm:manage") is False
