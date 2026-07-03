"""Enterprise CMS tables — audit trail, permissions, notifications, webhooks,
custom post types, glossary, search, sessions, media folders, file versions,
redirects, broken link checks.

Revision ID: ent001
Revises: ffb57364a038
Create Date: 2026-06-20
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "ent001"
down_revision = "20260617_pastoral_profile"
branch_labels = None
depends_on = None


def _col_exists(conn, table, col):
    return conn.execute(sa.text(
        f"SELECT 1 FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}'"
    )).fetchone() is not None


def _table_exists(conn, table):
    return conn.execute(sa.text(
        f"SELECT 1 FROM information_schema.tables WHERE table_name='{table}'"
    )).fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Audit Trail ──────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_audit_logs"):
        op.create_table(
            "cms_audit_logs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("actor_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("actor_email", sa.String(255), nullable=True),
            sa.Column("actor_role", sa.String(80), nullable=True),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", sa.String(120), nullable=True),
            sa.Column("entity_slug", sa.String(200), nullable=True),
            sa.Column("site_key", sa.String(80), nullable=True),
            sa.Column("changes_json", postgresql.JSON, nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
            sa.Column("severity", sa.String(20), server_default="info"),
            sa.Column("session_id", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_audit_logs_action", "cms_audit_logs", ["action"])
        op.create_index("ix_cms_audit_logs_entity_type", "cms_audit_logs", ["entity_type"])
        op.create_index("ix_cms_audit_logs_entity_id", "cms_audit_logs", ["entity_id"])
        op.create_index("ix_cms_audit_logs_site_key", "cms_audit_logs", ["site_key"])
        op.create_index("ix_cms_audit_logs_severity", "cms_audit_logs", ["severity"])
        op.create_index("ix_cms_audit_logs_created_at", "cms_audit_logs", ["created_at"])

    # ── Content Permissions ──────────────────────────────────────────────
    if not _table_exists(conn, "cms_content_permissions"):
        op.create_table(
            "cms_content_permissions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", sa.String(120), nullable=False),
            sa.Column("permission_type", sa.String(30), nullable=False),
            sa.Column("grant_type", sa.String(30), nullable=False),
            sa.Column("grant_target", sa.String(120), nullable=False),
            sa.Column("is_denied", sa.Boolean, server_default="false"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_content_permissions_site_key", "cms_content_permissions", ["site_key"])
        op.create_index("ix_cms_content_permissions_entity_type", "cms_content_permissions", ["entity_type"])
        op.create_index("ix_cms_content_permissions_entity_id", "cms_content_permissions", ["entity_id"])
        op.create_index("ix_cms_content_permissions_grant_type", "cms_content_permissions", ["grant_type"])

    # ── Notifications ────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_notifications"):
        op.create_table(
            "cms_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("recipient_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=False),
            sa.Column("actor_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("notification_type", sa.String(60), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text, nullable=True),
            sa.Column("entity_type", sa.String(60), nullable=True),
            sa.Column("entity_id", sa.String(120), nullable=True),
            sa.Column("entity_slug", sa.String(200), nullable=True),
            sa.Column("site_key", sa.String(80), nullable=True),
            sa.Column("is_read", sa.Boolean, server_default="false"),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("action_url", sa.String(500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_notifications_recipient", "cms_notifications", ["recipient_persona_id"])
        op.create_index("ix_cms_notifications_type", "cms_notifications", ["notification_type"])
        op.create_index("ix_cms_notifications_unread", "cms_notifications", ["is_read"])
        op.create_index("ix_cms_notifications_created_at", "cms_notifications", ["created_at"])

    # ── Webhooks ─────────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_webhooks"):
        op.create_table(
            "cms_webhooks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("secret", sa.String(255), nullable=True),
            sa.Column("events", postgresql.JSON, server_default="[]"),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status_code", sa.Integer, nullable=True),
            sa.Column("failure_count", sa.Integer, server_default="0"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_webhooks_site_key", "cms_webhooks", ["site_key"])
        op.create_index("ix_cms_webhooks_active", "cms_webhooks", ["is_active"])

    if not _table_exists(conn, "cms_webhook_deliveries"):
        op.create_table(
            "cms_webhook_deliveries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("webhook_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cms_webhooks.id"), nullable=False),
            sa.Column("event", sa.String(80), nullable=False),
            sa.Column("payload_json", postgresql.JSON, nullable=True),
            sa.Column("response_status", sa.Integer, nullable=True),
            sa.Column("response_body", sa.Text, nullable=True),
            sa.Column("duration_ms", sa.Integer, nullable=True),
            sa.Column("success", sa.Boolean, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_webhook_deliveries_webhook", "cms_webhook_deliveries", ["webhook_id"])
        op.create_index("ix_cms_webhook_deliveries_event", "cms_webhook_deliveries", ["event"])
        op.create_index("ix_cms_webhook_deliveries_created_at", "cms_webhook_deliveries", ["created_at"])

    # ── Custom Post Types ────────────────────────────────────────────────
    if not _table_exists(conn, "cms_custom_types"):
        op.create_table(
            "cms_custom_types",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("type_key", sa.String(80), nullable=False),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("label_plural", sa.String(120), nullable=True),
            sa.Column("icon", sa.String(60), nullable=True),
            sa.Column("supports", postgresql.JSON, server_default="[]"),
            sa.Column("fields_schema", postgresql.JSON, server_default="{}"),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_custom_types_site_key", "cms_custom_types", ["site_key"])
        op.create_index("ix_cms_custom_types_type_key", "cms_custom_types", ["type_key"])

    if not _table_exists(conn, "cms_custom_entries"):
        op.create_table(
            "cms_custom_entries",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("type_key", sa.String(80), nullable=False),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("content_html", sa.Text, nullable=True),
            sa.Column("excerpt", sa.Text, nullable=True),
            sa.Column("fields_json", postgresql.JSON, server_default="{}"),
            sa.Column("status", sa.String(30), server_default="draft"),
            sa.Column("featured_image_url", sa.String(500), nullable=True),
            sa.Column("author_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("owner_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cms_custom_entries.id"), nullable=True),
            sa.Column("sort_order", sa.Integer, server_default="0"),
            sa.Column("view_count", sa.Integer, server_default="0"),
            sa.Column("locale", sa.String(10), nullable=True),
            sa.Column("seo_json", postgresql.JSON, server_default="{}"),
            sa.Column("version", sa.Integer, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_cms_custom_entries_site_key", "cms_custom_entries", ["site_key"])
        op.create_index("ix_cms_custom_entries_type_key", "cms_custom_entries", ["type_key"])
        op.create_index("ix_cms_custom_entries_slug", "cms_custom_entries", ["slug"])
        op.create_index("ix_cms_custom_entries_status", "cms_custom_entries", ["status"])
        op.create_index("ix_cms_custom_entries_parent", "cms_custom_entries", ["parent_id"])
        op.create_index("ix_cms_custom_entries_deleted", "cms_custom_entries", ["deleted_at"])

    if not _table_exists(conn, "cms_custom_entry_versions"):
        op.create_table(
            "cms_custom_entry_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cms_custom_entries.id"), nullable=False),
            sa.Column("version_number", sa.Integer, nullable=False),
            sa.Column("snapshot_json", postgresql.JSON, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_custom_entry_versions_entry", "cms_custom_entry_versions", ["entry_id"])

    # ── Glossary ─────────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_glossary_terms"):
        op.create_table(
            "cms_glossary_terms",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("term", sa.String(200), nullable=False),
            sa.Column("definition", sa.Text, nullable=False),
            sa.Column("aliases", postgresql.JSON, server_default="[]"),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("language", sa.String(10), server_default="es"),
            sa.Column("is_published", sa.Boolean, server_default="true"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_glossary_terms_site_key", "cms_glossary_terms", ["site_key"])
        op.create_index("ix_cms_glossary_terms_term", "cms_glossary_terms", ["term"])
        op.create_index("ix_cms_glossary_terms_category", "cms_glossary_terms", ["category"])

    # ── Search ───────────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_search_index"):
        op.create_table(
            "cms_search_index",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", sa.String(120), nullable=False),
            sa.Column("entity_slug", sa.String(200), nullable=True),
            sa.Column("title", sa.String(300), nullable=True),
            sa.Column("body_text", sa.Text, nullable=True),
            sa.Column("tags", postgresql.JSON, server_default="[]"),
            sa.Column("author_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("locale", sa.String(10), nullable=True),
            sa.Column("is_published", sa.Boolean, server_default="true"),
            sa.Column("boost_score", sa.Integer, server_default="0"),
            sa.Column("last_indexed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_search_index_site_key", "cms_search_index", ["site_key"])
        op.create_index("ix_cms_search_index_entity_type", "cms_search_index", ["entity_type"])
        op.create_index("ix_cms_search_index_published", "cms_search_index", ["is_published"])
        op.create_index("ix_cms_search_index_category", "cms_search_index", ["category"])

    if not _table_exists(conn, "cms_search_promotions"):
        op.create_table(
            "cms_search_promotions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("query_text", sa.String(200), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", sa.String(120), nullable=False),
            sa.Column("entity_slug", sa.String(200), nullable=True),
            sa.Column("title", sa.String(300), nullable=True),
            sa.Column("boost_score", sa.Integer, server_default="100"),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_search_promotions_site_key", "cms_search_promotions", ["site_key"])
        op.create_index("ix_cms_search_promotions_query", "cms_search_promotions", ["query_text"])

    # ── Sessions ─────────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_user_sessions"):
        op.create_table(
            "cms_user_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=False),
            sa.Column("session_token", sa.String(255), nullable=False),
            sa.Column("device_info", sa.String(500), nullable=True),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("browser", sa.String(100), nullable=True),
            sa.Column("os", sa.String(100), nullable=True),
            sa.Column("is_mobile", sa.Boolean, server_default="false"),
            sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_cms_user_sessions_persona", "cms_user_sessions", ["persona_id"])
        op.create_index("ix_cms_user_sessions_token", "cms_user_sessions", ["session_token"])
        op.create_index("ix_cms_user_sessions_active", "cms_user_sessions", ["is_active"])
        op.create_index("ix_cms_user_sessions_last_activity", "cms_user_sessions", ["last_activity_at"])

    # ── Media Folders ────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_media_folders"):
        op.create_table(
            "cms_media_folders",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(200), nullable=False),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cms_media_folders.id"), nullable=True),
            sa.Column("path", sa.String(500), nullable=False),
            sa.Column("sort_order", sa.Integer, server_default="0"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_media_folders_site_key", "cms_media_folders", ["site_key"])
        op.create_index("ix_cms_media_folders_slug", "cms_media_folders", ["slug"])
        op.create_index("ix_cms_media_folders_parent", "cms_media_folders", ["parent_id"])

    # ── File Versions ────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_media_file_versions"):
        op.create_table(
            "cms_media_file_versions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cms_media_items.id"), nullable=False),
            sa.Column("version_number", sa.Integer, nullable=False),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column("file_size", sa.Integer, server_default="0"),
            sa.Column("checksum", sa.String(64), nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_media_file_versions_item", "cms_media_file_versions", ["media_item_id"])

    # ── Redirects ────────────────────────────────────────────────────────
    if not _table_exists(conn, "cms_redirects"):
        op.create_table(
            "cms_redirects",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("from_path", sa.String(500), nullable=False),
            sa.Column("to_path", sa.String(500), nullable=False),
            sa.Column("status_code", sa.Integer, server_default="301"),
            sa.Column("is_active", sa.Boolean, server_default="true"),
            sa.Column("hit_count", sa.Integer, server_default="0"),
            sa.Column("created_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_redirects_site_key", "cms_redirects", ["site_key"])
        op.create_index("ix_cms_redirects_from_path", "cms_redirects", ["from_path"])
        op.create_index("ix_cms_redirects_active", "cms_redirects", ["is_active"])

    # ── Broken Link Check ────────────────────────────────────────────────
    if not _table_exists(conn, "cms_broken_link_checks"):
        op.create_table(
            "cms_broken_link_checks",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("site_key", sa.String(80), nullable=False),
            sa.Column("source_url", sa.String(500), nullable=False),
            sa.Column("source_entity_type", sa.String(60), nullable=True),
            sa.Column("source_entity_id", sa.String(120), nullable=True),
            sa.Column("target_url", sa.String(500), nullable=False),
            sa.Column("status_code", sa.Integer, nullable=True),
            sa.Column("error_message", sa.String(500), nullable=True),
            sa.Column("is_broken", sa.Boolean, server_default="true"),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_cms_broken_link_checks_site_key", "cms_broken_link_checks", ["site_key"])
        op.create_index("ix_cms_broken_link_checks_broken", "cms_broken_link_checks", ["is_broken"])
        op.create_index("ix_cms_broken_link_checks_checked_at", "cms_broken_link_checks", ["checked_at"])


def downgrade() -> None:
    tables = [
        "cms_broken_link_checks", "cms_redirects", "cms_media_file_versions",
        "cms_media_folders", "cms_user_sessions", "cms_search_promotions",
        "cms_search_index", "cms_glossary_terms", "cms_custom_entry_versions",
        "cms_custom_entries", "cms_custom_types", "cms_webhook_deliveries",
        "cms_webhooks", "cms_notifications", "cms_content_permissions",
        "cms_audit_logs",
    ]
    for t in tables:
        op.drop_table(t)
