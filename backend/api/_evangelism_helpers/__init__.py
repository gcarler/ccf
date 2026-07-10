"""Axioma 3 — Evangelismo scope helpers (package re-exports).

Re-exporta los símbolos de ``_shared.py`` para permitir
``from backend.api._evangelism_helpers import (...)`` estilo DRY.

NOTA sobre naming: este módulo existe como package (directorio) para
prevenir colisiones con archivos evangelismo existentes
(``backend/api/evangelism.py``, ``backend/api/evangelism_main/``, etc.).
"""

from backend.api._evangelism_helpers._shared import (
    _actor_sede_or_none_evangelismo,
    _get_scoped_grupo,
    _get_scoped_participante,
    _get_scoped_seguimiento,
    _get_scoped_sesion,
    _get_scoped_strategy,
    _scope_evangelism_grupos_by_user_sede,
    _scope_evangelism_strategies_by_user_sede,
    require_pastor_or_admin_with_sede,
)

__all__ = (
    "_actor_sede_or_none_evangelismo",
    "_get_scoped_grupo",
    "_get_scoped_participante",
    "_get_scoped_seguimiento",
    "_get_scoped_sesion",
    "_get_scoped_strategy",
    "_scope_evangelism_grupos_by_user_sede",
    "_scope_evangelism_strategies_by_user_sede",
    "require_pastor_or_admin_with_sede",
)
