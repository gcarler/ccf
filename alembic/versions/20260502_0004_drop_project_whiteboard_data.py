"""drop project whiteboard data column

Revision ID: 20260502_0004
Revises: 20260502_0003
Create Date: 2026-05-02 16:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260502_0004"
down_revision = "20260502_0003"
branch_labels = None
depends_on = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _drop_sqlite_project_triggers(bind) -> None:
    for trigger_name in (
        "after_project_insert_search",
        "after_project_update_search",
        "log_task_creation",
        "log_task_priority_change",
        "log_task_status_change",
        "update_project_progress_on_task_insert",
        "update_project_progress_on_task_update",
    ):
        bind.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger_name}"))


def _create_sqlite_project_triggers(bind) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS after_project_insert_search AFTER INSERT ON projects BEGIN
              INSERT INTO projects_search_idx(rowid, title, description) VALUES (new.id, NEW.title, NEW.description);
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS after_project_update_search AFTER UPDATE ON projects BEGIN
              INSERT INTO projects_search_idx(projects_search_idx, rowid, title, description) VALUES('delete', old.id, old.title, old.description);
              INSERT INTO projects_search_idx(rowid, title, description) VALUES (new.id, NEW.title, NEW.description);
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS log_task_creation
            AFTER INSERT ON project_tasks
            BEGIN
                INSERT INTO project_activity_logs (project_id, action_type, description)
                VALUES (NEW.project_id, 'task_created', 'Nueva tarea: ' || NEW.title);
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS log_task_priority_change
            AFTER UPDATE OF priority ON project_tasks
            BEGIN
                INSERT INTO project_activity_logs (project_id, action_type, description)
                VALUES (NEW.project_id, 'priority_changed', 'Tarea ' || NEW.title || ' cambio prioridad a ' || NEW.priority);
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS log_task_status_change
            AFTER UPDATE OF status ON project_tasks
            BEGIN
                INSERT INTO project_activity_logs (project_id, action_type, description)
                VALUES (NEW.project_id, 'status_changed', 'Tarea ' || NEW.title || ' cambio a ' || NEW.status);
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS update_project_progress_on_task_insert
            AFTER INSERT ON project_tasks
            BEGIN
                UPDATE projects
                SET progress_percent = (
                    SELECT CAST(COUNT(CASE WHEN status = 'done' THEN 1 END) * 100.0 / COUNT(*) AS INTEGER)
                    FROM project_tasks
                    WHERE project_id = NEW.project_id
                )
                WHERE id = NEW.project_id;
            END
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TRIGGER IF NOT EXISTS update_project_progress_on_task_update
            AFTER UPDATE OF status ON project_tasks
            BEGIN
                UPDATE projects
                SET progress_percent = (
                    SELECT CAST(COUNT(CASE WHEN status = 'done' THEN 1 END) * 100.0 / COUNT(*) AS INTEGER)
                    FROM project_tasks
                    WHERE project_id = NEW.project_id
                )
                WHERE id = NEW.project_id;
            END
            """
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("projects") and _has_column(inspector, "projects", "whiteboard_data"):
        bind.execute(sa.text("DROP TABLE IF EXISTS _alembic_tmp_projects"))
        if bind.dialect.name == "sqlite":
            _drop_sqlite_project_triggers(bind)
        with op.batch_alter_table("projects") as batch_op:
            batch_op.drop_column("whiteboard_data")
        if bind.dialect.name == "sqlite":
            _create_sqlite_project_triggers(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("projects") and not _has_column(inspector, "projects", "whiteboard_data"):
        bind.execute(sa.text("DROP TABLE IF EXISTS _alembic_tmp_projects"))
        if bind.dialect.name == "sqlite":
            _drop_sqlite_project_triggers(bind)
        with op.batch_alter_table("projects") as batch_op:
            batch_op.add_column(sa.Column("whiteboard_data", sa.Text(), nullable=True))
        if bind.dialect.name == "sqlite":
            _create_sqlite_project_triggers(bind)
