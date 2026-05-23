"""seed cms_sites 'faro', cms_menus 'main', and view_user_workload

Revision ID: 20260522_0021
Revises: 20260522_0020
Create Date: 2026-05-22

Previously managed by _run_startup_migrations(). Now in Alembic
so that a fresh PostgreSQL deployment has all required data.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260522_0021"
down_revision = "20260522_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Seed cms_sites 'faro'
    sites_exists = sa.text(
        "SELECT 1 FROM cms_sites WHERE site_key = 'faro'"
    )
    result = conn.execute(sites_exists).fetchone()
    if not result:
        op.execute(sa.text(
            "INSERT INTO cms_sites (site_key, name, base_path, is_active, created_at, updated_at) "
            "VALUES ('faro', 'FARO', '/faro', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ))

    # Seed cms_menus 'main' for 'faro' site
    menus_exists = sa.text(
        "SELECT 1 FROM cms_menus m "
        "JOIN cms_sites s ON m.site_id = s.id "
        "WHERE s.site_key = 'faro' AND m.menu_key = 'main'"
    )
    result = conn.execute(menus_exists).fetchone()
    if not result:
        op.execute(sa.text(
            "INSERT INTO cms_menus (site_id, menu_key, name, is_active, created_at, updated_at) "
            "SELECT id, 'main', 'Menu principal', true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP "
            "FROM cms_sites WHERE site_key = 'faro'"
        ))

    # Create view_user_workload
    op.execute(sa.text("DROP VIEW IF EXISTS view_user_workload"))
    op.execute(sa.text(
        "CREATE VIEW view_user_workload AS "
        "SELECT "
        "u.id AS user_id, "
        "u.username AS full_name, "
        "u.username, "
        "COUNT(t.id) AS total_tasks, "
        "SUM(CASE WHEN t.status IN ('todo','in_progress','review') THEN 1 ELSE 0 END) AS open_tasks, "
        "SUM(CASE WHEN t.priority = 'urgent' AND t.status != 'done' THEN 1 ELSE 0 END) AS critical_tasks, "
        "SUM(CASE WHEN t.due_date < CURRENT_TIMESTAMP AND t.status != 'done' THEN 1 ELSE 0 END) AS overdue_tasks "
        "FROM users u "
        "LEFT JOIN project_tasks t ON t.assignee_id = u.id "
        "GROUP BY u.id, u.username"
    ))


def downgrade() -> None:
    op.execute(sa.text("DROP VIEW IF EXISTS view_user_workload"))
    # Note: downgrading seed data is intentionally not implemented
    # as removing seeded rows could break foreign key constraints
