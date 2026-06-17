"""Migrate CMS primary keys from Integer to UUID safely.

Revision ID: 20260616_0001
Revises: 20260614_kb_source_id_text
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0001"
down_revision = "20260614_kb_source_id_text"
branch_labels = None
depends_on = None


PK_TABLES = [
    "cms_sites",
    "cms_themes",
    "cms_menus",
    "cms_menu_items",
    "cms_pages",
    "cms_page_versions",
    "cms_sections",
    "cms_publish_logs",
    "cms_page_views",
    "cms_media_items",
    "testimonials",
    "announcements",
    "page_contents",
    "page_content_versions",
    "content_publications",
    "content_metrics",
    "media_assets",
]


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _has_table(table: str) -> bool:
    return table in set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> dict[str, dict]:
    return {c["name"]: c for c in sa.inspect(op.get_bind()).get_columns(table)}


def _has_column(table: str, column: str) -> bool:
    return column in _columns(table)


def _column_is_uuid(table: str, column: str) -> bool:
    col = _columns(table).get(column)
    if not col:
        return False
    return str(col["type"]).upper() == "UUID"


def _pk_constraint_name(table: str) -> str | None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT con.conname "
            "FROM pg_catalog.pg_constraint con "
            "JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid "
            "WHERE con.contype = 'p' AND rel.relname = :table"
        ),
        {"table": table},
    ).fetchall()
    return rows[0][0] if rows else None


def _fk_name(table: str, column: str) -> str | None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT con.conname "
            "FROM pg_catalog.pg_constraint con "
            "JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_catalog.pg_attribute att ON att.attrelid = con.conrelid "
            "  AND att.attnum = ANY(con.conkey) "
            "WHERE con.contype = 'f' "
            "  AND rel.relname = :table "
            "  AND att.attname = :column "
            "ORDER BY con.conname"
        ),
        {"table": table, "column": column},
    ).fetchall()
    return rows[0][0] if rows else None


def _drop_fk(table: str, column: str) -> None:
    fk = _fk_name(table, column)
    if fk:
        op.execute(f"ALTER TABLE {_quote(table)} DROP CONSTRAINT IF EXISTS {_quote(fk)}")


def _drop_index(table: str, column: str) -> None:
    rows = op.get_bind().execute(
        sa.text(
            "SELECT i.indexrelid::regclass::text "
            "FROM pg_catalog.pg_index i "
            "JOIN pg_catalog.pg_class rel ON rel.oid = i.indrelid "
            "WHERE rel.relname = :table "
            "  AND i.indisprimary = false "
            "  AND i.indisunique = false "
            "  AND array_length(i.indkey, 1) = 1 "
            "  AND i.indkey[0] = ("
            "    SELECT att.attnum "
            "    FROM pg_catalog.pg_attribute att "
            "    WHERE att.attrelid = rel.oid AND att.attname = :column"
            "  )"
        ),
        {"table": table, "column": column},
    ).fetchall()
    for row in rows:
        op.execute(f"DROP INDEX IF EXISTS {row[0]}")


def _drop_constraint_if_exists(table: str, constraint: str) -> None:
    op.execute(
        f"ALTER TABLE {_quote(table)} DROP CONSTRAINT IF EXISTS {_quote(constraint)}"
    )


def _add_uuid_ids() -> None:
    for table in PK_TABLES:
        if not _has_table(table) or _column_is_uuid(table, "id"):
            continue
        if not _has_column(table, "uuid_id"):
            op.execute(
                f"ALTER TABLE {_quote(table)} "
                "ADD COLUMN uuid_id UUID NOT NULL DEFAULT gen_random_uuid()"
            )


def _replace_fk_column(
    child_table: str,
    child_fk: str,
    parent_table: str,
    *,
    nullable: bool = False,
) -> None:
    if not _has_table(child_table) or not _has_table(parent_table):
        return
    if not _has_column(child_table, child_fk) or _column_is_uuid(child_table, child_fk):
        return
    if not _has_column(parent_table, "uuid_id"):
        return

    new_col = f"uuid_{child_fk}"
    if not _has_column(child_table, new_col):
        op.execute(f"ALTER TABLE {_quote(child_table)} ADD COLUMN {_quote(new_col)} UUID")

    op.execute(
        f"UPDATE {_quote(child_table)} child "
        f"SET {_quote(new_col)} = parent.uuid_id "
        f"FROM {_quote(parent_table)} parent "
        f"WHERE child.{_quote(child_fk)} = parent.id"
    )
    if nullable:
        missing_condition = f"{_quote(child_fk)} IS NOT NULL AND {_quote(new_col)} IS NULL"
    else:
        missing_condition = f"{_quote(new_col)} IS NULL"
    missing = op.get_bind().execute(
        sa.text(
            f"SELECT count(*) FROM {_quote(child_table)} WHERE {missing_condition}"
        )
    ).scalar()
    if missing:
        raise RuntimeError(
            f"Cannot migrate {child_table}.{child_fk}: {missing} rows did not map"
        )

    _drop_fk(child_table, child_fk)
    _drop_index(child_table, child_fk)
    op.execute(f"ALTER TABLE {_quote(child_table)} DROP COLUMN {_quote(child_fk)}")
    op.execute(
        f"ALTER TABLE {_quote(child_table)} "
        f"RENAME COLUMN {_quote(new_col)} TO {_quote(child_fk)}"
    )
    if not nullable:
        op.execute(
            f"ALTER TABLE {_quote(child_table)} "
            f"ALTER COLUMN {_quote(child_fk)} SET NOT NULL"
        )


def _replace_self_parent_id() -> None:
    table = "cms_menu_items"
    if not _has_table(table):
        return
    if not _has_column(table, "parent_id") or _column_is_uuid(table, "parent_id"):
        return
    if not _has_column(table, "uuid_id"):
        return

    if not _has_column(table, "uuid_parent_id"):
        op.execute("ALTER TABLE cms_menu_items ADD COLUMN uuid_parent_id UUID")
    op.execute(
        "UPDATE cms_menu_items child "
        "SET uuid_parent_id = parent.uuid_id "
        "FROM cms_menu_items parent "
        "WHERE child.parent_id = parent.id"
    )
    missing = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM cms_menu_items "
            "WHERE parent_id IS NOT NULL AND uuid_parent_id IS NULL"
        )
    ).scalar()
    if missing:
        raise RuntimeError(
            f"Cannot migrate cms_menu_items.parent_id: {missing} rows did not map"
        )
    _drop_fk(table, "parent_id")
    _drop_index(table, "parent_id")
    op.execute("ALTER TABLE cms_menu_items DROP COLUMN parent_id")
    op.execute("ALTER TABLE cms_menu_items RENAME COLUMN uuid_parent_id TO parent_id")


def _replace_published_version_id() -> None:
    table = "cms_pages"
    if not _has_table(table) or not _has_table("cms_page_versions"):
        return
    if not _has_column(table, "published_version_id"):
        return
    if _column_is_uuid(table, "published_version_id"):
        return
    if not _has_column("cms_page_versions", "uuid_id"):
        return

    if not _has_column(table, "uuid_published_version_id"):
        op.execute("ALTER TABLE cms_pages ADD COLUMN uuid_published_version_id UUID")
    op.execute(
        "UPDATE cms_pages page "
        "SET uuid_published_version_id = version.uuid_id "
        "FROM cms_page_versions version "
        "WHERE page.published_version_id = version.id"
    )
    missing = op.get_bind().execute(
        sa.text(
            "SELECT count(*) FROM cms_pages "
            "WHERE published_version_id IS NOT NULL "
            "AND uuid_published_version_id IS NULL"
        )
    ).scalar()
    if missing:
        raise RuntimeError(
            f"Cannot migrate cms_pages.published_version_id: {missing} rows did not map"
        )
    _drop_fk(table, "published_version_id")
    _drop_index(table, "published_version_id")
    op.execute("DROP INDEX IF EXISTS ix_cms_pages_published_version_id")
    op.execute("ALTER TABLE cms_pages DROP COLUMN published_version_id")
    op.execute(
        "ALTER TABLE cms_pages "
        "RENAME COLUMN uuid_published_version_id TO published_version_id"
    )


def _promote_uuid_id(table: str) -> None:
    if not _has_table(table) or _column_is_uuid(table, "id"):
        return
    if not _has_column(table, "uuid_id"):
        raise RuntimeError(f"Cannot promote {table}.id: uuid_id is missing")

    pk_name = _pk_constraint_name(table)
    if pk_name:
        op.execute(f"ALTER TABLE {_quote(table)} DROP CONSTRAINT IF EXISTS {_quote(pk_name)}")
    op.execute(f"ALTER TABLE {_quote(table)} DROP COLUMN id")
    op.execute(f"ALTER TABLE {_quote(table)} RENAME COLUMN uuid_id TO id")
    op.execute(f"ALTER TABLE {_quote(table)} ADD PRIMARY KEY (id)")
    op.execute(f"ALTER TABLE {_quote(table)} ALTER COLUMN id SET DEFAULT gen_random_uuid()")


def _add_fk(
    child_table: str,
    child_fk: str,
    parent_table: str,
    *,
    nullable: bool = False,
    on_delete: str = "CASCADE",
    constraint_name: str | None = None,
) -> None:
    if not _has_table(child_table) or not _has_table(parent_table):
        return
    if not _has_column(child_table, child_fk):
        return
    if not _column_is_uuid(child_table, child_fk):
        return
    if not nullable:
        op.execute(
            f"ALTER TABLE {_quote(child_table)} "
            f"ALTER COLUMN {_quote(child_fk)} SET NOT NULL"
        )
    name = constraint_name or f"fk_{child_table}_{child_fk}"
    _drop_fk(child_table, child_fk)
    _drop_constraint_if_exists(child_table, name)
    op.execute(
        f"ALTER TABLE {_quote(child_table)} ADD CONSTRAINT {_quote(name)} "
        f"FOREIGN KEY ({_quote(child_fk)}) REFERENCES {_quote(parent_table)}(id) "
        f"ON DELETE {on_delete}"
    )
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {_quote(f'ix_{child_table}_{child_fk}')} "
        f"ON {_quote(child_table)} ({_quote(child_fk)})"
    )


def _alter_column_to_text(table: str, column: str) -> None:
    if _has_table(table) and _has_column(table, column):
        op.execute(
            f"ALTER TABLE {_quote(table)} ALTER COLUMN {_quote(column)} "
            "TYPE VARCHAR(120)"
        )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    _add_uuid_ids()

    _replace_fk_column("cms_themes", "site_id", "cms_sites")
    _replace_fk_column("cms_menus", "site_id", "cms_sites")
    _replace_fk_column("cms_pages", "site_id", "cms_sites")
    _replace_fk_column("cms_publish_logs", "site_id", "cms_sites")
    _replace_fk_column("cms_menu_items", "menu_id", "cms_menus")
    _replace_self_parent_id()
    _replace_fk_column("cms_page_versions", "page_id", "cms_pages")
    _replace_published_version_id()
    _replace_fk_column("cms_sections", "page_id", "cms_pages")
    _replace_fk_column("cms_page_views", "page_id", "cms_pages")
    _replace_fk_column("cms_publish_logs", "page_id", "cms_pages", nullable=True)

    for table in PK_TABLES:
        _promote_uuid_id(table)

    _add_fk("cms_themes", "site_id", "cms_sites")
    _add_fk("cms_menus", "site_id", "cms_sites")
    _add_fk("cms_pages", "site_id", "cms_sites")
    _add_fk("cms_publish_logs", "site_id", "cms_sites")
    _add_fk("cms_menu_items", "menu_id", "cms_menus")
    _add_fk(
        "cms_menu_items",
        "parent_id",
        "cms_menu_items",
        nullable=True,
        constraint_name="fk_cms_menu_items_parent_id",
    )
    _add_fk(
        "cms_page_versions",
        "page_id",
        "cms_pages",
        constraint_name="fk_cms_page_versions_page_id",
    )
    _add_fk(
        "cms_pages",
        "published_version_id",
        "cms_page_versions",
        nullable=True,
        on_delete="SET NULL",
        constraint_name="fk_cms_pages_published_version_id",
    )
    _add_fk("cms_sections", "page_id", "cms_pages")
    _add_fk("cms_page_views", "page_id", "cms_pages")
    _add_fk("cms_publish_logs", "page_id", "cms_pages", nullable=True)

    if _has_table("cms_menus") and _has_column("cms_menus", "site_id"):
        _drop_constraint_if_exists("cms_menus", "uq_cms_menu_site_key")
        op.create_unique_constraint(
            "uq_cms_menu_site_key", "cms_menus", ["site_id", "menu_key"]
        )
    if _has_table("cms_pages") and _has_column("cms_pages", "site_id"):
        _drop_constraint_if_exists("cms_pages", "uq_cms_page_site_slug")
        op.create_unique_constraint(
            "uq_cms_page_site_slug", "cms_pages", ["site_id", "slug"]
        )
    if _has_table("cms_page_versions") and _has_column("cms_page_versions", "page_id"):
        _drop_constraint_if_exists("cms_page_versions", "uq_cms_page_version_number")
        op.create_unique_constraint(
            "uq_cms_page_version_number",
            "cms_page_versions",
            ["page_id", "version_number"],
        )

    _alter_column_to_text("cms_publish_logs", "entity_id")
    _alter_column_to_text("content_metrics", "ref_id")


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade not supported for CMS UUID PK migration. Restore from backup "
        "if integer primary keys must be recovered."
    )
