"""Academy: Programs, study plans, credits, and grading schemes.

Revision ID: 20260927_0012_academy_programs_credits_grading_schemes
Revises: 20260926_0011_event_registrations_registration_number
Create Date: 2026-09-27 13:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260927_0012_academy_programs_credits_grading_schemes"
down_revision: Union[str, None] = "20260926_0011_event_registrations_registration_number"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. academy_programs
    op.create_table(
        "academy_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(50), nullable=False, default="diplomado", index=True),
        sa.Column("level_name", sa.String(100), nullable=True),
        sa.Column("total_duration_type", sa.String(50), nullable=False, default="semestres"),
        sa.Column("total_duration_units", sa.Integer(), nullable=False, default=2),
        sa.Column("total_credits", sa.Integer(), nullable=False, default=0),
        sa.Column("modality", sa.String(50), nullable=False, default="presencial"),
        sa.Column("has_teachers", sa.Boolean(), nullable=False, default=True),
        sa.Column("teachers_can_grade", sa.Boolean(), nullable=False, default=True),
        sa.Column("min_passing_grade", sa.Float(), nullable=False, default=70.0),
        sa.Column("grading_scale_max", sa.Float(), nullable=False, default=100.0),
        sa.Column("min_attendance_percent", sa.Float(), nullable=False, default=80.0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 2. academy_academic_periods
    op.create_table(
        "academy_academic_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("period_type", sa.String(50), nullable=False, default="semestral"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("enrollment_start_date", sa.Date(), nullable=True),
        sa.Column("enrollment_end_date", sa.Date(), nullable=True),
        sa.Column("grading_deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, default="open", index=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 3. academy_grading_schemes
    op.create_table(
        "academy_grading_schemes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scale_max", sa.Float(), nullable=False, default=100.0),
        sa.Column("passing_grade", sa.Float(), nullable=False, default=70.0),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 4. academy_grading_scheme_cuts
    op.create_table(
        "academy_grading_scheme_cuts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_grading_schemes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, default=1),
        sa.Column("weight_percent", sa.Float(), nullable=False, default=30.0),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 5. academy_study_plans
    op.create_table(
        "academy_study_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("program_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_programs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("total_credits", sa.Integer(), nullable=False, default=0),
        sa.Column("total_levels", sa.Integer(), nullable=False, default=1),
        sa.Column("level_type", sa.String(50), nullable=False, default="semestre"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 6. academy_study_plan_subjects
    op.create_table(
        "academy_study_plan_subjects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("study_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_study_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_courses.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("level_number", sa.Integer(), nullable=False, default=1),
        sa.Column("credits", sa.Integer(), nullable=False, default=3),
        sa.Column("weekly_hours_theory", sa.Integer(), nullable=False, default=2),
        sa.Column("weekly_hours_practice", sa.Integer(), nullable=False, default=2),
        sa.Column("weekly_hours_independent", sa.Integer(), nullable=False, default=4),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, default=True),
        sa.Column("default_grading_scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_grading_schemes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, default=0),
        sa.Column("prerequisite_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 7. academy_period_offerings
    op.create_table(
        "academy_period_offerings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("sede_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("academic_period_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_academic_periods.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_study_plan_subjects.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_courses.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("docente_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("grading_scheme_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_grading_schemes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("group_name", sa.String(50), nullable=False, default="Grupo 01"),
        sa.Column("quota_max", sa.Integer(), nullable=False, default=40),
        sa.Column("status", sa.String(50), nullable=False, default="open", index=True),
        sa.Column("classroom", sa.String(100), nullable=True),
        sa.Column("schedule_summary", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, index=True),
    )

    # 8. academy_student_period_grades
    op.create_table(
        "academy_student_period_grades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("offering_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("cut_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_grading_scheme_cuts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("grade_value", sa.Float(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("graded_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("offering_id", "persona_id", "cut_id", name="uq_offering_student_cut"),
    )

    # 9. academy_student_subject_records
    op.create_table(
        "academy_student_subject_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("offering_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("enrollment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("academy_enrollments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("credits_attempted", sa.Integer(), nullable=False, default=0),
        sa.Column("credits_earned", sa.Integer(), nullable=False, default=0),
        sa.Column("calculated_final_grade", sa.Float(), nullable=True),
        sa.Column("final_grade_override", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, default=False),
        sa.Column("attendance_percent", sa.Float(), nullable=False, default=0.0),
        sa.Column("status", sa.String(50), nullable=False, default="enrolled", index=True),
        sa.Column("acta_number", sa.String(50), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_persona_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("personas.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("offering_id", "persona_id", name="uq_offering_student_record"),
    )

    # Seed initial default grading scheme (30% - 30% - 40%)
    scheme_id = uuid.uuid4()
    op.execute(
        sa.text(f"""
        INSERT INTO academy_grading_schemes (id, name, description, scale_max, passing_grade, is_default, is_active, created_at, updated_at)
        VALUES ('{scheme_id}', 'Esquema Semestral Canónico (30% - 30% - 40%)', 'Tres cortes de evaluación regular con pesos 30%, 30% y 40% examen/proyecto final.', 100.0, 70.0, true, true, NOW(), NOW());
        
        INSERT INTO academy_grading_scheme_cuts (id, scheme_id, name, order_index, weight_percent, description, created_at, updated_at)
        VALUES 
        ('{uuid.uuid4()}', '{scheme_id}', 'Primer Corte (30%)', 1, 30.0, 'Evaluación parcial y talleres primer tercio', NOW(), NOW()),
        ('{uuid.uuid4()}', '{scheme_id}', 'Segundo Corte (30%)', 2, 30.0, 'Evaluación parcial y actividades segundo tercio', NOW(), NOW()),
        ('{uuid.uuid4()}', '{scheme_id}', 'Tercer Corte / Final (40%)', 3, 40.0, 'Examen final y entrega de proyecto consolidado', NOW(), NOW());
        """)
    )


def downgrade() -> None:
    op.drop_table("academy_student_subject_records")
    op.drop_table("academy_student_period_grades")
    op.drop_table("academy_period_offerings")
    op.drop_table("academy_study_plan_subjects")
    op.drop_table("academy_study_plans")
    op.drop_table("academy_grading_scheme_cuts")
    op.drop_table("academy_grading_schemes")
    op.drop_table("academy_academic_periods")
    op.drop_table("academy_programs")
