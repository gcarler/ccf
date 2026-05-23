#!/usr/bin/env python3
"""
migrate_data.py
Transfers data from ccf_v2.db.bak to ccf_final.db.
Handles schema differences detected during audit:
  - projects.name -> projects.title
  - Extra/missing columns are handled per-table with explicit column mapping.
"""
import sqlite3
import json

SOURCE_DB = "/root/ccf/ccf_v2.db.bak"
TARGET_DB = "/root/ccf/ccf_final.db"

# Tables that exist in both source and target (with same name)
# Maps: source_table -> (target_table, column_mapping)
# column_mapping: dict of source_col -> target_col (None = skip source col)
# If a target column is not in the mapping, it gets NULL/default.
TABLE_MIGRATIONS = {
    "admin_audit_logs": {
        "target": "admin_audit_logs",
        "columns": {
            "id": "id",
            "actor_user_id": "actor_user_id",
            "action": "action",
            "resource_type": "resource_type",
            "resource_id": "resource_id",
            "metadata": "metadata",
            "created_at": "created_at",
        },
    },
    "agent_insights": {
        "target": "agent_insights",
        "columns": {
            "id": "id",
            "title": "title",
            "insight_type": "insight_type",
            "payload": "payload",
            "acknowledged": "acknowledged",
            "created_at": "created_at",
        },
    },
    "agent_tasks": {
        "target": "agent_tasks",
        "columns": {
            "id": "id",
            "title": "title",
            "description": "description",
            "status": "status",
            "priority": "priority",
            "source": "source",
            "created_at": "created_at",
            "updated_at": "updated_at",
        },
    },
    "badges": {
        "target": "badges",
        "columns": {
            "id": "id",
            "name": "name",
            "description": "description",
            "icon_key": "icon_key",
            "xp_reward": "xp_reward",
        },
    },
    "certificates": {
        "target": "certificates",
        "columns": {
            "id": "id",
            "enrollment_id": "enrollment_id",
            "certificate_code": "certificate_code",
            "issued_at": "issued_at",
        },
    },
    "chat_messages": {
        "target": "chat_messages",
        "columns": {
            "id": "id",
            "sender_id": "sender_id",
            "room_id": "room_id",
            "content": "content",
            "created_at": "created_at",
        },
    },
    "consolidation_pipeline": {
        "target": "consolidation_pipeline",
        "columns": {
            "id": "id",
            "first_name": "first_name",
            "last_name": "last_name",
            "phone": "phone",
            "stage": "stage",
            "assigned_pastor_id": "assigned_pastor_id",
            "created_at": "created_at",
            "updated_at": "updated_at",
        },
    },
    "courses": {
        "target": "courses",
        "columns": {
            "id": "id",
            "code": "code",
            "title": "title",
            "modality": "modality",
            "xp_per_lesson": "xp_per_lesson",
            "created_at": "created_at",
        },
    },
    "enrollments": {
        "target": "enrollments",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "course_id": "course_id",
            "status": "status",
            "progress_percent": "progress_percent",
            "lessons_completed": "lessons_completed",
        },
    },
    "forum_threads": {
        "target": "forum_threads",
        "columns": {
            "id": "id",
            "title": "title",
            "category": "category",
            "author_id": "author_id",
            "is_resolved": "is_resolved",
            "created_at": "created_at",
            "updated_at": "updated_at",
        },
    },
    "inventory_items": {
        "target": "inventory_items",
        "columns": {
            "id": "id",
            "name": "name",
            "category": "category",
            "stock": "stock",
            "status": "status",
        },
    },
    "lessons": {
        "target": "lessons",
        "columns": {
            "id": "id",
            "course_id": "course_id",
            "title": "title",
            "content": "content",
        },
    },
    "levels": {
        "target": "levels",
        "columns": {
            "id": "id",
            "title": "title",
            "min_xp": "min_xp",
            "icon_key": "icon_key",
        },
    },
    "members": {
        "target": "members",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "church_role": "church_role",
        },
    },
    "notifications": {
        "target": "notifications",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "title": "title",
            "content": "content",
            "is_read": "is_read",
            "created_at": "created_at",
        },
    },
    "refresh_tokens": {
        "target": "refresh_tokens",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "token": "token",
            "expires_at": "expires_at",
            "revoked": "revoked",
            "created_at": "created_at",
        },
    },
    "roles": {
        "target": "roles",
        "columns": {
            "role_id": "role_id",
            "name": "name",
            "permissions": "permissions",
        },
    },
    "user_badges": {
        "target": "user_badges",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "badge_id": "badge_id",
            "earned_at": "earned_at",
        },
    },
    "user_ui_preferences": {
        "target": "user_ui_preferences",
        "columns": {
            "id": "id",
            "user_id": "user_id",
            "settings": "settings",
            "updated_at": "updated_at",
        },
    },
    "users": {
        "target": "users",
        "columns": {
            "id": "id",
            "username": "username",
            "email": "email",
            "password_hash": "password_hash",
            "role_id": "role_id",
            "role": "role",
            "xp": "xp",
            "current_level_id": "current_level_id",
            "is_active": "is_active",
            "created_at": "created_at",
            "updated_at": "updated_at",
        },
    },
    # Special: projects.name -> projects.title
    "projects": {
        "target": "projects",
        "columns": {
            "id": "id",
            "name": "title",  # <-- THE KEY MAPPING
            "description": "description",
            "status": "status",
            "created_at": "created_at",
        },
    },
    "project_tasks": {
        "target": "project_tasks",
        "columns": {
            "id": "id",
            "project_id": "project_id",
            "title": "title",
            "description": "description",
            "status": "status",
            "priority": "priority",
            "assignee_id": "assignee_id",
            "start_date": "start_date",
            "due_date": "due_date",
            "labels": "labels",
        },
    },
}

# Tables in source that have no corresponding target table (will be skipped)
SKIP_TABLES = [
    "alembic_version",
    "communication_logs",
    "content_metrics",
    "media_assets",
    "page_content_versions",
    "page_contents",
    "pastoral_call_logs",
    "task_supplies",
]


def get_source_columns(conn, table):
    """Return list of column names for a source table."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def get_target_columns(conn, table):
    """Return list of column names for a target table."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def migrate_table(src_conn, tgt_conn, table_name, cfg):
    """Migrate one table from source to target."""
    target_table = cfg["target"]
    col_map = cfg["columns"]

    # Build source SELECT columns (only those we map)
    src_cols = [sc for sc in col_map.keys()]
    src_cols_str = ", ".join(src_cols)

    # Build target INSERT columns
    tgt_cols = [tc for tc in col_map.values()]
    tgt_cols_str = ", ".join(tgt_cols)
    placeholders = ", ".join(["?" for _ in tgt_cols])

    # Fetch source data
    src_rows = src_conn.execute(f"SELECT {src_cols_str} FROM {table_name}").fetchall()
    if not src_rows:
        return 0

    # Insert into target
    insert_sql = f"INSERT INTO {target_table} ({tgt_cols_str}) VALUES ({placeholders})"
    tgt_conn.executemany(insert_sql, src_rows)
    return len(src_rows)


def main():
    src_conn = sqlite3.connect(SOURCE_DB)
    src_conn.row_factory = sqlite3.Row
    tgt_conn = sqlite3.connect(TARGET_DB)
    tgt_conn.execute("PRAGMA foreign_keys = OFF")  # Disable FK checks during migration

    results = {}
    total_rows = 0

    # Migrate mapped tables
    for src_table, cfg in sorted(TABLE_MIGRATIONS.items()):
        try:
            n = migrate_table(src_conn, tgt_conn, src_table, cfg)
            results[src_table] = n
            total_rows += n
            status = "OK"
        except Exception as e:
            results[src_table] = f"ERROR: {e}"
            status = "ERROR"

    # Skip tables that don't exist in target
    for skip in SKIP_TABLES:
        results[skip] = "SKIPPED (no target table)"

    tgt_conn.commit()
    tgt_conn.execute("PRAGMA foreign_keys = ON")
    tgt_conn.close()
    src_conn.close()

    # Report
    print("=" * 60)
    print("MIGRATION REPORT")
    print("=" * 60)
    for table, result in sorted(results.items()):
        if isinstance(result, int):
            print(f"  {table:35s} -> {result:>5d} rows migrated")
        else:
            print(f"  {table:35s} -> {result}")
    print("=" * 60)
    print(f"  TOTAL: {total_rows} rows migrated across all tables")
    print("=" * 60)


if __name__ == "__main__":
    main()
