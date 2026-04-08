"""cms v2 multisite foundation

Revision ID: 20260408_0001
Revises:
Create Date: 2026-04-08 00:01:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260408_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("cms_sites"):
        return

    op.create_table(
        "cms_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_path", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_path"),
        sa.UniqueConstraint("site_key"),
    )
    op.create_index(op.f("ix_cms_sites_id"), "cms_sites", ["id"], unique=False)
    op.create_index(op.f("ix_cms_sites_site_key"), "cms_sites", ["site_key"], unique=False)
    op.create_index(op.f("ix_cms_sites_base_path"), "cms_sites", ["base_path"], unique=False)
    op.create_index(op.f("ix_cms_sites_is_active"), "cms_sites", ["is_active"], unique=False)

    op.create_table(
        "cms_themes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("tokens_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["cms_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_themes_id"), "cms_themes", ["id"], unique=False)
    op.create_index(op.f("ix_cms_themes_site_id"), "cms_themes", ["site_id"], unique=False)
    op.create_index(op.f("ix_cms_themes_is_active"), "cms_themes", ["is_active"], unique=False)

    op.create_table(
        "cms_menus",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("menu_key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["cms_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "menu_key", name="uq_cms_menu_site_key"),
    )
    op.create_index(op.f("ix_cms_menus_id"), "cms_menus", ["id"], unique=False)
    op.create_index(op.f("ix_cms_menus_site_id"), "cms_menus", ["site_id"], unique=False)
    op.create_index(op.f("ix_cms_menus_menu_key"), "cms_menus", ["menu_key"], unique=False)
    op.create_index(op.f("ix_cms_menus_is_active"), "cms_menus", ["is_active"], unique=False)

    op.create_table(
        "cms_menu_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("menu_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("href", sa.String(length=255), nullable=False),
        sa.Column("target", sa.String(length=20), nullable=True),
        sa.Column("is_external", sa.Boolean(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["menu_id"], ["cms_menus.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["cms_menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_menu_items_id"), "cms_menu_items", ["id"], unique=False)
    op.create_index(op.f("ix_cms_menu_items_menu_id"), "cms_menu_items", ["menu_id"], unique=False)
    op.create_index(op.f("ix_cms_menu_items_parent_id"), "cms_menu_items", ["parent_id"], unique=False)

    op.create_table(
        "cms_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("seo_json", sa.JSON(), nullable=True),
        sa.Column("published_version_id", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["cms_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "slug", name="uq_cms_page_site_slug"),
    )
    op.create_index(op.f("ix_cms_pages_id"), "cms_pages", ["id"], unique=False)
    op.create_index(op.f("ix_cms_pages_site_id"), "cms_pages", ["site_id"], unique=False)
    op.create_index(op.f("ix_cms_pages_slug"), "cms_pages", ["slug"], unique=False)
    op.create_index(op.f("ix_cms_pages_status"), "cms_pages", ["status"], unique=False)

    op.create_table(
        "cms_page_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["cms_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("page_id", "version_number", name="uq_cms_page_version_number"),
    )
    op.create_index(op.f("ix_cms_page_versions_id"), "cms_page_versions", ["id"], unique=False)
    op.create_index(op.f("ix_cms_page_versions_page_id"), "cms_page_versions", ["page_id"], unique=False)

    op.create_foreign_key(
        "fk_cms_pages_published_version_id",
        "cms_pages",
        "cms_page_versions",
        ["published_version_id"],
        ["id"],
    )

    op.create_table(
        "cms_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("section_key", sa.String(length=120), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("props_json", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.Column("is_visible", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["cms_pages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_sections_id"), "cms_sections", ["id"], unique=False)
    op.create_index(op.f("ix_cms_sections_page_id"), "cms_sections", ["page_id"], unique=False)
    op.create_index(op.f("ix_cms_sections_section_key"), "cms_sections", ["section_key"], unique=False)
    op.create_index(op.f("ix_cms_sections_type"), "cms_sections", ["type"], unique=False)
    op.create_index(op.f("ix_cms_sections_is_visible"), "cms_sections", ["is_visible"], unique=False)

    op.create_table(
        "cms_publish_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=True),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["cms_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["cms_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cms_publish_logs_id"), "cms_publish_logs", ["id"], unique=False)
    op.create_index(op.f("ix_cms_publish_logs_site_id"), "cms_publish_logs", ["site_id"], unique=False)
    op.create_index(op.f("ix_cms_publish_logs_page_id"), "cms_publish_logs", ["page_id"], unique=False)
    op.create_index(op.f("ix_cms_publish_logs_entity_type"), "cms_publish_logs", ["entity_type"], unique=False)
    op.create_index(op.f("ix_cms_publish_logs_action"), "cms_publish_logs", ["action"], unique=False)
    op.create_index(op.f("ix_cms_publish_logs_created_at"), "cms_publish_logs", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("cms_sites"):
        return

    op.drop_index(op.f("ix_cms_publish_logs_created_at"), table_name="cms_publish_logs")
    op.drop_index(op.f("ix_cms_publish_logs_action"), table_name="cms_publish_logs")
    op.drop_index(op.f("ix_cms_publish_logs_entity_type"), table_name="cms_publish_logs")
    op.drop_index(op.f("ix_cms_publish_logs_page_id"), table_name="cms_publish_logs")
    op.drop_index(op.f("ix_cms_publish_logs_site_id"), table_name="cms_publish_logs")
    op.drop_index(op.f("ix_cms_publish_logs_id"), table_name="cms_publish_logs")
    op.drop_table("cms_publish_logs")

    op.drop_index(op.f("ix_cms_sections_is_visible"), table_name="cms_sections")
    op.drop_index(op.f("ix_cms_sections_type"), table_name="cms_sections")
    op.drop_index(op.f("ix_cms_sections_section_key"), table_name="cms_sections")
    op.drop_index(op.f("ix_cms_sections_page_id"), table_name="cms_sections")
    op.drop_index(op.f("ix_cms_sections_id"), table_name="cms_sections")
    op.drop_table("cms_sections")

    op.drop_constraint("fk_cms_pages_published_version_id", "cms_pages", type_="foreignkey")
    op.drop_index(op.f("ix_cms_page_versions_page_id"), table_name="cms_page_versions")
    op.drop_index(op.f("ix_cms_page_versions_id"), table_name="cms_page_versions")
    op.drop_table("cms_page_versions")

    op.drop_index(op.f("ix_cms_pages_status"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_slug"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_site_id"), table_name="cms_pages")
    op.drop_index(op.f("ix_cms_pages_id"), table_name="cms_pages")
    op.drop_table("cms_pages")

    op.drop_index(op.f("ix_cms_menu_items_parent_id"), table_name="cms_menu_items")
    op.drop_index(op.f("ix_cms_menu_items_menu_id"), table_name="cms_menu_items")
    op.drop_index(op.f("ix_cms_menu_items_id"), table_name="cms_menu_items")
    op.drop_table("cms_menu_items")

    op.drop_index(op.f("ix_cms_menus_is_active"), table_name="cms_menus")
    op.drop_index(op.f("ix_cms_menus_menu_key"), table_name="cms_menus")
    op.drop_index(op.f("ix_cms_menus_site_id"), table_name="cms_menus")
    op.drop_index(op.f("ix_cms_menus_id"), table_name="cms_menus")
    op.drop_table("cms_menus")

    op.drop_index(op.f("ix_cms_themes_is_active"), table_name="cms_themes")
    op.drop_index(op.f("ix_cms_themes_site_id"), table_name="cms_themes")
    op.drop_index(op.f("ix_cms_themes_id"), table_name="cms_themes")
    op.drop_table("cms_themes")

    op.drop_index(op.f("ix_cms_sites_is_active"), table_name="cms_sites")
    op.drop_index(op.f("ix_cms_sites_base_path"), table_name="cms_sites")
    op.drop_index(op.f("ix_cms_sites_site_key"), table_name="cms_sites")
    op.drop_index(op.f("ix_cms_sites_id"), table_name="cms_sites")
    op.drop_table("cms_sites")
