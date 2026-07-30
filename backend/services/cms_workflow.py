"""
PageWorkflowService — Centralized page workflow logic (Fase 4.2).

Encapsulates all page status transitions, schedule auto-flip, version
snapshotting and rollback into a single service.  Endpoints call the
service instead of inlining CRUD calls + implicit status mutations.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from backend import crud, models
from backend.crud.cms import (
    create_cms_page_version,
    get_cms_page_version,
    restore_cms_page_version,
    transition_cms_page_status,
)

logger = logging.getLogger(__name__)

# ── Valid actions map ─────────────────────────────────────────────────────────

VALID_ACTIONS = frozenset({
    "submit_review",
    "approve",
    "publish",
    "archive",
    "revert_draft",
})

PUBLISHER_ACTIONS = frozenset({"approve", "publish", "archive"})

NON_TERMINAL_STATUSES = frozenset({"draft", "in_review", "approved"})


class PageWorkflowService:
    """Centralized workflow operations for CMS pages.

    Every public method accepts a ``db`` session and the domain objects
    directly — no FastAPI dependencies — so callers (endpoints, background
    workers, tests) share the same workflow contract.
    """

    def __init__(self, db: Session):
        self.db = db

    # ── Status transitions ─────────────────────────────────────────────────

    def transition(
        self,
        page: models.CmsPage,
        action: str,
        user_id: uuid.UUID | None,
        *,
        notes: str | None = None,
    ) -> models.CmsPage | None:
        """Apply a workflow action to a page and return the updated row.

        Returns ``None`` when the action is not recognised (caller
        translates to 422).  Publishes a version snapshot on ``publish``,
        then transitions the status and records a ``CmsPublishLog`` entry.
        """
        action = action.strip().lower()
        if action not in VALID_ACTIONS:
            return None

        result = transition_cms_page_status(
            self.db,
            page,
            action,
            user_id,
            notes=notes,
        )
        return result

    def requires_publisher_role(self, action: str) -> bool:
        """Return ``True`` if the action requires publisher (not just editor) role."""
        return action.strip().lower() in PUBLISHER_ACTIONS

    # ── Schedule auto-flip ─────────────────────────────────────────────────

    def apply_schedule(
        self,
        page: models.CmsPage,
        *,
        publish_at: object = None,
        user_id: uuid.UUID | None = None,
    ) -> models.CmsPage:
        """Auto-flip to ``scheduled`` status when ``publish_at`` is set.

        Called from ``patch_page`` after the CRUD has persisted timestamps.
        If ``publish_at`` is set and the page is in a non-terminal status
        (draft / in_review / approved), flip to ``scheduled`` so the cron
        scheduler picks it up. Otherwise leave status unchanged.
        """
        if publish_at is not None and page.status in NON_TERMINAL_STATUSES:
            page.status = "scheduled"
            page.updated_by_persona_id = (
                crud.cms.resolve_persona_uuid_for_user(self.db, user_id)
            )
            self.db.commit()
            self.db.refresh(page)
        return page

    # ── Rollback ───────────────────────────────────────────────────────────

    def rollback(
        self,
        page: models.CmsPage,
        version_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> models.CmsPage | None:
        """Restore a page to a previous version.

        Returns ``None`` when the version is not found (caller translates
        to 404).  On success the page status becomes ``draft`` and sections
        are replaced with the snapshot data.
        """
        version = get_cms_page_version(self.db, page.id, version_id)
        if not version:
            return None
        return restore_cms_page_version(self.db, page, version, user_id=user_id)

    # ── Version creation ───────────────────────────────────────────────────

    def create_version(
        self,
        page: models.CmsPage,
        user_id: uuid.UUID | None,
        *,
        notes: str | None = None,
    ) -> models.CmsPageVersion:
        """Snapshot the current page + sections into a new version row."""
        return create_cms_page_version(self.db, page, user_id, notes=notes)
