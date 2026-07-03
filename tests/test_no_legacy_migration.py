from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "alembic"
    / "versions"
    / "20260701_0002_eradicate_runtime_legacy.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("no_runtime_legacy", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runtime_legacy_migration_cleans_and_hardens_sqlite():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    sa.Table(
        "sedes",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
    )
    sa.Table(
        "personas",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255)),
        sa.Column("sede_id", sa.String(36)),
        sa.Column("qr_token", sa.String(100)),
        sa.Column("fecha_bautismo", sa.Date),
    )
    for table, owner in (
        ("cms_media_items", "created_by_persona_id"),
        ("announcements", "created_by_persona_id"),
        ("testimonials", "author_persona_id"),
    ):
        sa.Table(
            table,
            metadata,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(owner, sa.String(36), nullable=True),
            sa.Column("sede_id", sa.String(36), nullable=True),
        )
    sa.Table(
        "communication_logs",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("outcome", sa.String(50)),
    )
    sa.Table(
        "project_tasks",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("labels", sa.JSON, nullable=True),
        sa.Column("priority", sa.String(20), nullable=True),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(sa.text("INSERT INTO sedes VALUES ('sede-a')"))
        connection.execute(
            sa.text(
                "INSERT INTO personas "
                "(id, email, sede_id, qr_token, fecha_bautismo) VALUES "
                "('persona-a', 'a@example.com', 'sede-a', :old_token, '2025-01-02')"
            ),
            {"old_token": "CCF-" + "MBR-OLD"},
        )
        for table, owner in (
            ("cms_media_items", "created_by_persona_id"),
            ("announcements", "created_by_persona_id"),
            ("testimonials", "author_persona_id"),
        ):
            connection.execute(
                sa.text(
                    f'INSERT INTO "{table}" (id, "{owner}", sede_id) '
                    "VALUES ('valid', 'persona-a', NULL), ('orphan', NULL, NULL)"
                )
            )
        connection.execute(
            sa.text(
                "INSERT INTO communication_logs VALUES "
                "('old', 'delivered'), ('new', 'sent_real')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO project_tasks (id, labels, priority) VALUES "
                "('scalar', '\"urgent\"', 'alta'), "
                "('empty', NULL, NULL), ('array', '[\"ready\"]', 'URGENTE')"
            )
        )

        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        for table in ("cms_media_items", "announcements", "testimonials"):
            rows = connection.execute(
                sa.text(f'SELECT id, sede_id FROM "{table}"')
            ).all()
            assert rows == [("valid", "sede-a")]
            columns = {item["name"]: item for item in sa.inspect(connection).get_columns(table)}
            assert columns["sede_id"]["nullable"] is False

        outcomes = connection.execute(
            sa.text("SELECT outcome FROM communication_logs ORDER BY id")
        ).scalars().all()
        assert outcomes == ["sent_real", "sent_real"]
        token = connection.execute(sa.text("SELECT qr_token FROM personas")).scalar_one()
        assert not token.startswith("CCF-" + "MBR-")
        persona_columns = {
            item["name"] for item in sa.inspect(connection).get_columns("personas")
        }
        assert "baptism_date" in persona_columns
        assert "fecha_bautismo" not in persona_columns
        labels = connection.execute(
            sa.text("SELECT labels FROM project_tasks ORDER BY id")
        ).scalars().all()
        assert [sa.JSON().result_processor(connection.dialect, None)(value) for value in labels] == [
            ["ready"],
            [],
            ["urgent"],
        ]
        project_columns = {
            item["name"]: item
            for item in sa.inspect(connection).get_columns("project_tasks")
        }
        assert project_columns["labels"]["nullable"] is False
        assert project_columns["priority"]["nullable"] is False
        priorities = connection.execute(
            sa.text("SELECT priority FROM project_tasks ORDER BY id")
        ).scalars().all()
        assert priorities == ["urgent", "medium", "high"]

        migration.downgrade()
        columns = {
            item["name"]: item
            for item in sa.inspect(connection).get_columns("testimonials")
        }
        assert columns["sede_id"]["nullable"] is True
        project_columns = {
            item["name"]: item
            for item in sa.inspect(connection).get_columns("project_tasks")
        }
        assert project_columns["labels"]["nullable"] is True
        assert project_columns["priority"]["nullable"] is True
        persona_columns = {
            item["name"] for item in sa.inspect(connection).get_columns("personas")
        }
        assert "fecha_bautismo" in persona_columns
        assert "baptism_date" not in persona_columns


def test_public_contact_tracker_writes_only_canonical_crm_fields(db_session):
    from backend.services.public_contact_tracking import ContactRecord, tracker
    from tests.conftest import seed_admin

    _, _, sede = seed_admin(db_session, email="public-owner@example.com")
    result = tracker.record_contact(
        db_session,
        ContactRecord(
            email="newsletter-contact@example.com",
            first_name="Contacto",
            last_name="Público",
            source="newsletter-web",
            landing_page="/inicio",
            sede_id=sede.id,
        ),
    )

    assert result.persona.sede_id == sede.id
    assert result.case.sede_id == sede.id
    from backend.models_crm_pipeline import CanalOrigenEnum

    assert result.case.origen_canal == CanalOrigenEnum.WEB_FORM
    assert result.case.origen_detalle_id == "newsletter-web"
    assert result.case.pipeline_id is not None
    assert result.case.etapa_actual_id is not None
    assert result.case.payload_web["landing_page"] == "/inicio"


def test_project_task_contract_rejects_scalar_labels_and_old_priorities():
    from backend.schemas.projects import ProjectTaskCreate

    with pytest.raises(ValidationError):
        ProjectTaskCreate(title="Inválida", labels="urgent")
    with pytest.raises(ValidationError):
        ProjectTaskCreate(title="Inválida", priority="normal")
