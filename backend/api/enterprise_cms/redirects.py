"""Redirects + resolve — CRUD de ``CmsRedirect`` y resolución por matching
(exact > wildcard > regex) con prioridad por ``priority DESC``.

Sub-router movido desde ``backend/api/enterprise_cms.py`` (split del
monolito, deuda estructural 🟠#4, 2026-08-05). Conserva el docstring de
``resolve_redirect`` y ``_format_match`` vinculados a
``AUDITORIA_FORENSE_CMS.md F-04 (cerrado)``.
"""

from __future__ import annotations

import fnmatch
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.enterprise_cms.__common import _log_audit, require_cms_manage, require_cms_read
from backend.core.database import get_db
from backend.models_enterprise import CmsRedirect
from backend.models_identity import User

router = APIRouter()


class RedirectCreate(BaseModel):
    site_key: str
    from_path: str
    to_path: str
    status_code: int = 301
    # Tipo de matching + prioridad (AUDITORIA_FORENSE_CMS.md F-04 cerrado).
    # exact: match literal (default, back-compat).
    # wildcard: glob con * y ? via fnmatch.
    # regex: Python re.search contra el path pedido.
    match_type: str = "exact"
    priority: int = 0


@router.post("/redirects")
def create_redirect(
    body: RedirectCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    # Validar match_type y regex-pattern antes de persistir
    # (AUDITORIA_FORENSE_CMS.md F-04 cerrado).
    mt = (body.match_type or "exact").strip().lower()
    if mt not in ("exact", "wildcard", "regex"):
        raise HTTPException(422, "match_type must be one of: exact, wildcard, regex")
    if mt == "regex":
        # Compila el patron para fallar temprano (422) si el regex es invalido
        try:
            re.compile(body.from_path)
        except re.error as exc:
            raise HTTPException(422, f"Invalid regex pattern: {exc}") from exc

    redir = CmsRedirect(
        site_key=body.site_key,
        from_path=body.from_path,
        to_path=body.to_path,
        status_code=body.status_code,
        match_type=mt,
        priority=int(body.priority),
        created_by_persona_id=getattr(user, "persona_id", None),
    )
    db.add(redir)
    _log_audit(
        db,
        user,
        "redirect.create",
        "redirect",
        str(redir.id),
        site_key=body.site_key,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"id": str(redir.id), "status": "created"}


@router.get("/redirects")
def list_redirects(
    site_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    redirs = (
        db.query(CmsRedirect)
        .filter(
            CmsRedirect.site_key == site_key,
            CmsRedirect.is_active == True,
        )
        .order_by(CmsRedirect.from_path)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "from_path": r.from_path,
            "to_path": r.to_path,
            "status_code": r.status_code,
            "hit_count": r.hit_count,
            "match_type": r.match_type,
            "priority": r.priority,
        }
        for r in redirs
    ]


@router.delete("/redirects/{redirect_id}")
def delete_redirect(
    redirect_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_manage),
):
    redir = db.query(CmsRedirect).filter(CmsRedirect.id == redirect_id).first()
    if not redir:
        raise HTTPException(404, "Redirect not found")
    redir.is_active = False
    db.commit()
    return {"status": "deactivated"}


# ── AUDITORIA_FORENSE_CMS.md F-04 (cerrado): resolve redirect by incoming path ────
# Helper que aplica matching por prioridad: exact > wildcard > regex,
# dentro de cada tipo por priority DESC y luego por longitud de from_path
# DESC (más específico primero).  Usado por el endpoint GET /resolve-redirect
# y testeable directamente sin HTTP stack.


def resolve_redirect(db: Session, *, site_key: str, path: str) -> dict | None:
    """AUDITORIA_FORENSE_CMS.md F-04 (cerrado): resuelve el mejor redirect
    activo para ``path`` bajo ``site_key``.

    Aplica prioridad: exact > wildcard > regex.  Dentro de cada tipo,
    recorre por ``priority DESC`` y luego por ``len(from_path) DESC``
    (más específico primero).  Retorna un dict con ``id``, ``to_path``
    (con ``$1``/``$2`` reemplazados por los grupos capturados para
    regex/wildcard) y ``status_code``.  Retorna ``None`` si no hay match.

    En caso de regex inválido en runtime (guardado sin validación previa),
    se salta ese redirect de forma defensiva (no raise) — validación
    debe ocurrir en ``create_redirect``.
    """
    redirs = (
        db.query(CmsRedirect)
        .filter(
            CmsRedirect.site_key == site_key,
            CmsRedirect.is_active.is_(True),
        )
        .order_by(CmsRedirect.priority.desc(), CmsRedirect.from_path.desc())
        .all()
    )
    # Bucketing por match_type para aplicar prioridad exact > wildcard > regex
    buckets: dict[str, list[CmsRedirect]] = {"exact": [], "wildcard": [], "regex": []}
    for r in redirs:
        mt = (r.match_type or "exact").strip().lower()
        if mt in buckets:
            buckets[mt].append(r)

    for mt in ("exact", "wildcard", "regex"):
        for r in buckets[mt]:
            if mt == "exact":
                if r.from_path == path:
                    return _format_match(r, path, None)
            elif mt == "wildcard":
                # fnmatch: * matches everything except separator path "/", /
                # para soporte más preciso usamos posixmatch=False (default).
                if fnmatch.fnmatch(path, r.from_path):
                    return _format_match(r, path, None)
            elif mt == "regex":
                try:
                    m = re.search(r.from_path, path)
                except re.error:
                    continue  # Defensivo: regex inválido guardado sin validación
                if m:
                    return _format_match(r, path, m)
    return None


def _format_match(r: CmsRedirect, path: str, m: re.Match | None) -> dict:
    """Aplica sustitución de grupos ``$1``/``$2`` en ``to_path`` para
    regex, y ``$1``/``$2``.../``$N`` usando los grupos capturados.
    Para wildcard/exact retorna ``to_path`` literal.
    """
    to_path = r.to_path
    if m is not None and "$" in to_path:
        # Sustituye $0 (full match), $1, $2, ... $N con los grupos
        groups = m.groups() or ()
        expanded = [m.group(0)] + list(groups)
        for i, val in enumerate(expanded):
            to_path = to_path.replace(f"${i}", val or "")
    return {
        "id": str(r.id),
        "from_path": r.from_path,
        "to_path": to_path,
        "status_code": r.status_code,
        "match_type": r.match_type,
        "priority": r.priority,
    }


@router.get("/resolve-redirect")
def resolve_redirect_endpoint(
    site_key: str = Query(..., description="Site key del tenant"),
    path: str = Query(..., description="Path incoming a resolver"),
    db: Session = Depends(get_db),
    user: User = Depends(require_cms_read),
):
    """AUDITORIA_FORENSE_CMS.md F-04 (cerrado): resuelve un redirect para
    un path entrante aplicando matching por prioridad
    (exact > wildcard > regex).  Retorna el redirect matcheado con
    ``to_path`` ya reemplazado (para wildcard/regex con grupos de captura
    ``$1`` etc.) o ``404`` si no hay match.

    El ``hit_count`` del redirect matcheado se incrementa (best-effort).
    """
    match = resolve_redirect(db, site_key=site_key, path=path)
    if match is None:
        raise HTTPException(404, "No redirect matches the given path")
    # Best-effort hit count
    try:
        match_row = db.query(CmsRedirect).filter(CmsRedirect.id == match["id"]).first()
        if match_row:
            match_row.hit_count = (match_row.hit_count or 0) + 1
            db.commit()
    except Exception:
        db.rollback()
    return match
