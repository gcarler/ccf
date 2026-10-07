import sqlalchemy as sa
"""Canonical Academy models backed exclusively by ``academy_*`` tables."""

import uuid as _uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, synonym

from backend.core.database import Base
from backend.models_shared import _utcnow


class Course(Base):
    __tablename__ = "academy_courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    code = Column(String(50), nullable=False, unique=True)
    slug = Column(String(200), nullable=True, unique=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    tag = Column(String(100), nullable=True)
    cta_text = Column(String(100), nullable=True)
    syllabus = Column(JSON, nullable=True)
    instructor_name = Column(String(200), nullable=True)
    modality = Column(String(50), nullable=False, index=True)
    otorga_rol_iglesia = Column(String(50), nullable=True)
    is_published = Column(Boolean, default=False, nullable=False)
    is_self_paced = Column(Boolean, default=False, nullable=False)
    duration_hours = Column(Integer, nullable=False, default=0)
    cohort_name = Column(String(100), nullable=True)
    certificate_type = Column(String(50), nullable=True)
    xp_per_lesson = Column(Integer, default=10, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    image_url = Column(String(255), nullable=True)
    access_level = Column(String(20), nullable=False, default="persona", server_default="persona")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")
    prerequisites = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course",
    )


class CoursePrerequisite(Base):
    __tablename__ = "academy_course_prerequisites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)
    prerequisite_course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("course_id", "prerequisite_course_id", name="uq_course_prerequisite"),)

    course = relationship("Course", foreign_keys=[course_id], back_populates="prerequisites")
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id])


class Lesson(Base):
    __tablename__ = "academy_lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="video", nullable=False)
    media_url = Column(String(255), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    duration_minutes = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    course = relationship("Course", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson")
    assessments = relationship("Assessment", back_populates="lesson")


class LessonProgress(Base):
    __tablename__ = "academy_lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False, index=True)
    progress_percent = Column(Numeric(5, 2), default=0)
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    last_position_seconds = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("persona_id", "lesson_id", name="uq_lesson_progress_persona_lesson"),)


class Assessment(Base):
    __tablename__ = "academy_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    max_score = Column(Float, nullable=False, default=100)
    passing_score = Column(Float, nullable=False, default=70)
    weight = Column(Numeric(5, 2), default=1.0)
    is_published = Column(Boolean, default=False, nullable=False)
    max_attempts = Column(Integer, nullable=True, default=3)
    cooldown_minutes = Column(Integer, nullable=True, default=60)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    min_score = synonym("passing_score")
    lesson = relationship("Lesson", back_populates="assessments")
    course = relationship("Course")
    questions = relationship("AssessmentQuestion", back_populates="assessment")


class AssessmentQuestion(Base):
    __tablename__ = "academy_assessment_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessments.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice", nullable=False)
    points = Column(Integer, default=1, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question")


class AssessmentOption(Base):
    __tablename__ = "academy_assessment_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    question_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessment_questions.id"), nullable=False, index=True)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)

    question = relationship("AssessmentQuestion", back_populates="options")


class Enrollment(Base):
    __tablename__ = "academy_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)
    cohort_name = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    progress_percent = Column(Float, default=0.0, nullable=False)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0.0, nullable=False)
    lessons_completed = Column(JSON, nullable=True, default=list)
    approved = Column(Boolean, default=False, nullable=False)
    acta_closed = Column(Boolean, default=False, nullable=False)
    certificate_issued = Column(Boolean, default=False, nullable=False)
    certificate_code = Column(String(64), nullable=True)
    access_window_end = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    persona = relationship("Persona")
    course = relationship("Course", back_populates="enrollments")

    __table_args__ = (UniqueConstraint("persona_id", "course_id", name="uq_enrollment_persona_course"),)


class AssessmentAttempt(Base):
    __tablename__ = "academy_assessment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessments.id"), nullable=False, index=True)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    created_at = synonym("submitted_at")
    assessment = relationship("Assessment")
    enrollment = relationship("Enrollment")
    answers = relationship("AssessmentAnswer", back_populates="attempt")


class AssessmentAnswer(Base):
    __tablename__ = "academy_assessment_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("academy_assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessment_questions.id"), nullable=False)
    selected_option_id = Column(UUID(as_uuid=True), ForeignKey("academy_assessment_options.id"), nullable=True)
    text_response = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Numeric(5, 2), default=0)

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("AssessmentQuestion")
    selected_option = relationship("AssessmentOption")


class CourseAttendance(Base):
    __tablename__ = "academy_course_attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("academy_enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="present")
    recorded_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)

    enrollment = relationship("Enrollment")


class AssignmentSubmission(Base):
    __tablename__ = "academy_assignment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False, index=True)
    file_url = Column("seaweed_fid", String(500), nullable=False)
    comment = Column(Text, nullable=True)
    teacher_feedback = Column(Text, nullable=True)
    grade = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    # ACAD-MED-003-FOLLOWUP (cierre): columna soft-delete habilita el archivado
    # controlado por ``delete_submission_admin`` sin romper la integridad
    # referencial. Los huerfanos en Seaweed se recuperan vía el evento
    # ``assignment_submission_archived`` en ``AcademyActivityLog.payload_json``.
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # ACAD-MED-003-FOLLOWUP: necesario para ``row.lesson.course_id`` en
    # ``delete_submission_admin`` y para cualquier caller que necesite el
    # scope sede sin JOIN explícito.
    lesson = relationship("Lesson")


class Resource(Base):
    __tablename__ = "academy_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=False)
    resource_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    lesson = relationship("Lesson", back_populates="resources")


class Certificate(Base):
    __tablename__ = "academy_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True)
    certificate_code = Column(String(100), nullable=False, unique=True, index=True)
    certificate_type = Column(String(50), nullable=True)
    issued_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    enrollment = relationship("Enrollment")


class FormalActa(Base):
    __tablename__ = "academy_formal_actas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True)
    cohort_name = Column(String(100), nullable=False, default="General")
    closed_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    min_grade = Column(Float, nullable=False, default=70)
    min_attendance = Column(Float, nullable=False, default=75)
    status = Column(String(50), default="closed", nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    entries = relationship("FormalActaEntry", back_populates="acta")


class FormalActaEntry(Base):
    __tablename__ = "academy_formal_acta_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    acta_id = Column(UUID(as_uuid=True), ForeignKey("academy_formal_actas.id"), nullable=False)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0.0, nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)

    acta = relationship("FormalActa", back_populates="entries")


class ForumThread(Base):
    __tablename__ = "academy_forum_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=True, index=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, default="general", index=True)
    content = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    # Soft-delete contract: archived threads remain available for audit while
    # excluded from all learner-facing reads.
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class ForumComment(Base):
    __tablename__ = "academy_forum_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("academy_forum_threads.id"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("academy_forum_comments.id"), nullable=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AcademyActivityLog(Base):
    __tablename__ = "academy_activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    modality = Column(String(20), nullable=True)
    value = Column(Numeric(10, 2), default=1.0)
    # ACAD-MED-003-FOLLOWUP: payload_json captura metadatos del evento
    # (file_url, lesson_id, enrollment_id, archived_at, archived_by_persona_id)
    # que no caben en String(20) modality. Job batch de purga de Seaweed
    # consultará por event_type="assignment_submission_archived" + payload_json.
    payload_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)


class AcademyProgram(Base):
    __tablename__ = "academy_programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    program_type = Column(String(50), nullable=False, default="diplomado", index=True)
    level_name = Column(String(100), nullable=True)
    total_duration_type = Column(String(50), nullable=False, default="semestres")
    total_duration_units = Column(Integer, nullable=False, default=2)
    total_credits = Column(Integer, nullable=False, default=0)
    modality = Column(String(50), nullable=False, default="presencial")
    has_teachers = Column(Boolean, nullable=False, default=True)
    teachers_can_grade = Column(Boolean, nullable=False, default=True)
    min_passing_grade = Column(Float, nullable=False, default=70.0)
    grading_scale_max = Column(Float, nullable=False, default=100.0)
    min_attendance_percent = Column(Float, nullable=False, default=80.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    study_plans = relationship("AcademyStudyPlan", back_populates="program", cascade="all, delete-orphan")


class AcademyAcademicPeriod(Base):
    __tablename__ = "academy_academic_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    period_type = Column(String(50), nullable=False, default="semestral")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    enrollment_start_date = Column(Date, nullable=True)
    enrollment_end_date = Column(Date, nullable=True)
    grading_deadline = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default="open", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    offerings = relationship("AcademyPeriodOffering", back_populates="academic_period", cascade="all, delete-orphan")


class AcademyGradingScheme(Base):
    __tablename__ = "academy_grading_schemes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    scale_max = Column(Float, nullable=False, default=100.0)
    passing_grade = Column(Float, nullable=False, default=70.0)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    cuts = relationship("AcademyGradingSchemeCut", back_populates="scheme", cascade="all, delete-orphan", order_by="AcademyGradingSchemeCut.order_index")


class AcademyGradingSchemeCut(Base):
    __tablename__ = "academy_grading_scheme_cuts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    scheme_id = Column(UUID(as_uuid=True), ForeignKey("academy_grading_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    order_index = Column(Integer, nullable=False, default=1)
    weight_percent = Column(Float, nullable=False, default=30.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    scheme = relationship("AcademyGradingScheme", back_populates="cuts")


class AcademyStudyPlan(Base):
    __tablename__ = "academy_study_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("academy_programs.id", ondelete="CASCADE"), nullable=False, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    total_credits = Column(Integer, nullable=False, default=0)
    total_levels = Column(Integer, nullable=False, default=1)
    level_type = Column(String(50), nullable=False, default="semestre")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    program = relationship("AcademyProgram", back_populates="study_plans")
    subjects = relationship("AcademyStudyPlanSubject", back_populates="study_plan", cascade="all, delete-orphan", order_by="AcademyStudyPlanSubject.order_index")


class AcademyStudyPlanSubject(Base):
    __tablename__ = "academy_study_plan_subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    study_plan_id = Column(UUID(as_uuid=True), ForeignKey("academy_study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id", ondelete="SET NULL"), nullable=True, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    level_number = Column(Integer, nullable=False, default=1)
    credits = Column(Integer, nullable=False, default=3)
    weekly_hours_theory = Column(Integer, nullable=False, default=2)
    weekly_hours_practice = Column(Integer, nullable=False, default=2)
    weekly_hours_independent = Column(Integer, nullable=False, default=4)
    is_mandatory = Column(Boolean, nullable=False, default=True)
    default_grading_scheme_id = Column(UUID(as_uuid=True), ForeignKey("academy_grading_schemes.id", ondelete="SET NULL"), nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    prerequisite_codes = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    study_plan = relationship("AcademyStudyPlan", back_populates="subjects")
    course = relationship("Course")
    default_grading_scheme = relationship("AcademyGradingScheme")
    offerings = relationship("AcademyPeriodOffering", back_populates="subject")


class AcademyPeriodOffering(Base):
    __tablename__ = "academy_period_offerings"
    quota_enrolled = Column(Integer, nullable=False, default=0)

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    academic_period_id = Column(UUID(as_uuid=True), ForeignKey("academy_academic_periods.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("academy_study_plan_subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("academy_courses.id", ondelete="SET NULL"), nullable=True, index=True)
    docente_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True, index=True)
    grading_scheme_id = Column(UUID(as_uuid=True), ForeignKey("academy_grading_schemes.id", ondelete="RESTRICT"), nullable=False)
    group_name = Column(String(50), nullable=False, default="Grupo 01")
    quota_max = Column(Integer, nullable=False, default=40)
    status = Column(String(50), nullable=False, default="open", index=True)
    classroom = Column(String(100), nullable=True)
    schedule_summary = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    academic_period = relationship("AcademyAcademicPeriod", back_populates="offerings")
    subject = relationship("AcademyStudyPlanSubject", back_populates="offerings")
    course = relationship("Course")
    docente_persona = relationship("Persona", foreign_keys=[docente_persona_id])
    grading_scheme = relationship("AcademyGradingScheme")
    grades = relationship("AcademyStudentPeriodGrade", back_populates="offering", cascade="all, delete-orphan")
    records = relationship("AcademyStudentSubjectRecord", back_populates="offering", cascade="all, delete-orphan")


class AcademyStudentPeriodGrade(Base):
    __tablename__ = "academy_student_period_grades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    cut_id = Column(UUID(as_uuid=True), ForeignKey("academy_grading_scheme_cuts.id", ondelete="CASCADE"), nullable=False, index=True)
    grade_value = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    graded_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("offering_id", "persona_id", "cut_id", name="uq_offering_student_cut"),)

    offering = relationship("AcademyPeriodOffering", back_populates="grades")
    persona = relationship("Persona", foreign_keys=[persona_id])
    cut = relationship("AcademyGradingSchemeCut")
    graded_by_persona = relationship("Persona", foreign_keys=[graded_by_persona_id])


class AcademyStudentSubjectRecord(Base):
    __tablename__ = "academy_student_subject_records"
    is_locked = Column(Boolean, nullable=False, default=False)

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("academy_enrollments.id", ondelete="SET NULL"), nullable=True)
    credits_attempted = Column(Integer, nullable=False, default=0)
    credits_earned = Column(Integer, nullable=False, default=0)
    calculated_final_grade = Column(Float, nullable=True)
    final_grade_override = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    attendance_percent = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="enrolled", index=True)
    acta_number = Column(String(50), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    closed_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("offering_id", "persona_id", name="uq_offering_student_record"),)

    offering = relationship("AcademyPeriodOffering", back_populates="records")
    persona = relationship("Persona", foreign_keys=[persona_id])
    enrollment = relationship("Enrollment")
    closed_by_persona = relationship("Persona", foreign_keys=[closed_by_persona_id])

class AcademyStudentEnrollment(Base):
    __tablename__ = 'academy_student_enrollments'

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey('academy_period_offerings.id', ondelete='CASCADE'), nullable=False)
    persona_id = Column(UUID(as_uuid=True), ForeignKey('personas.id'), nullable=False)
    enrolled_by_persona_id = Column(UUID(as_uuid=True), ForeignKey('personas.id'), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), nullable=False, server_default=sa.func.now())
    status = Column(String(50), nullable=False, default='active')
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint('offering_id', 'persona_id', name='uq_academy_student_enrollments_offering_persona'),
    )

    # Relationships
    offering = relationship("AcademyPeriodOffering", backref="enrollments")
    persona = relationship("Persona", foreign_keys=[persona_id])
    enrolled_by = relationship("Persona", foreign_keys=[enrolled_by_persona_id])


class AcademySocraticSession(Base):
    __tablename__ = "academy_socratic_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    session_type = Column(String(50), nullable=False, default="tutor")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    offering = relationship("AcademyPeriodOffering")
    student = relationship("Persona", foreign_keys=[student_id])


class AcademyDefenseSession(Base):
    __tablename__ = "academy_defense_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=True, index=True)
    submission_id = Column(UUID(as_uuid=True), ForeignKey("academy_assignment_submissions.id", ondelete="SET NULL"), nullable=True, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")
    score = Column(Float, nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=300)
    questions = Column(JSON, nullable=True)
    answers = Column(JSON, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    offering = relationship("AcademyPeriodOffering")
    submission = relationship("AssignmentSubmission")
    student = relationship("Persona", foreign_keys=[student_id])


class AcademyKnowledgeNode(Base):
    __tablename__ = "academy_knowledge_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    node_type = Column(String(50), nullable=False, default="concept")  # 'concept', 'skill', 'competency'
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    offering = relationship("AcademyPeriodOffering")


class AcademyKnowledgeEdge(Base):
    __tablename__ = "academy_knowledge_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    source_node_id = Column(UUID(as_uuid=True), ForeignKey("academy_knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    target_node_id = Column(UUID(as_uuid=True), ForeignKey("academy_knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    edge_type = Column(String(50), nullable=False, default="requires")  # 'requires', 'leads_to', 'related'
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    source_node = relationship("AcademyKnowledgeNode", foreign_keys=[source_node_id])
    target_node = relationship("AcademyKnowledgeNode", foreign_keys=[target_node_id])


class AcademyStudentNodeProgress(Base):
    __tablename__ = "academy_student_node_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("academy_knowledge_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    mastery_score = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    attempts = Column(Integer, nullable=False, default=0)
    last_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("student_id", "node_id", name="uq_student_node_progress"),
    )

    student = relationship("Persona", foreign_keys=[student_id])
    node = relationship("AcademyKnowledgeNode", foreign_keys=[node_id])


class AcademyPortfolioEntry(Base):
    __tablename__ = "academy_portfolio_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_type = Column(String(50), nullable=False, default="project")  # 'project', 'defense', 'certification', 'grade'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence_url = Column(String(500), nullable=True)
    score = Column(Float, nullable=True)
    issued_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    credential_hash = Column(String(64), nullable=True, index=True)
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    student = relationship("Persona", foreign_keys=[student_id])
    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])


class AcademyWellnessSignal(Base):
    __tablename__ = "academy_wellness_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    signal_type = Column(String(50), nullable=False)  # 'engagement_drop', 'grade_risk', 'absence_pattern', 'stress_indicator'
    severity = Column(String(20), nullable=False, default="medium")  # 'low', 'medium', 'high', 'critical'
    detected_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    details = Column(JSON, nullable=True)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    student = relationship("Persona", foreign_keys=[student_id])
    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])
    resolved_by = relationship("Persona", foreign_keys=[resolved_by_id])


class AcademyWellnessAlert(Base):
    __tablename__ = "academy_wellness_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("academy_wellness_signals.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    signal = relationship("AcademyWellnessSignal", foreign_keys=[signal_id], backref="alerts")
    recipient = relationship("Persona", foreign_keys=[recipient_id])


class AcademyAchievement(Base):
    __tablename__ = "academy_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    code = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    achievement_type = Column(String(50), nullable=False, default="milestone")  # 'completion', 'excellence', 'defense', 'streak', 'milestone'
    points = Column(Integer, nullable=False, default=10)
    badge_icon = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)


class AcademyStudentAchievement(Base):
    __tablename__ = "academy_student_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("academy_achievements.id", ondelete="CASCADE"), nullable=False, index=True)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    earned_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    evidence = Column(JSON, nullable=True)
    credential_hash = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("student_id", "achievement_id", "offering_id", name="uq_student_achievement_offering"),
    )

    student = relationship("Persona", foreign_keys=[student_id])
    achievement = relationship("AcademyAchievement", foreign_keys=[achievement_id], backref="student_achievements")
    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])


class AcademyLeaderboard(Base):
    __tablename__ = "academy_leaderboard"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    period = Column(String(50), nullable=False, default="2026-Q3", index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    total_points = Column(Integer, nullable=False, default=0)
    rank = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("student_id", "period", "offering_id", name="uq_leaderboard_student_period_offering"),
    )

    student = relationship("Persona", foreign_keys=[student_id])
    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])


class AcademyStudyGroup(Base):
    __tablename__ = "academy_study_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_members = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])
    creator = relationship("Persona", foreign_keys=[created_by])
    members = relationship("AcademyStudyGroupMember", back_populates="group", cascade="all, delete-orphan")


class AcademyStudyGroupMember(Base):
    __tablename__ = "academy_study_group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("academy_study_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="member")  # 'leader', 'member'
    joined_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        UniqueConstraint("group_id", "student_id", name="uq_study_group_student"),
    )

    group = relationship("AcademyStudyGroup", foreign_keys=[group_id], back_populates="members")
    student = relationship("Persona", foreign_keys=[student_id])


class AcademyCalendarEvent(Base):
    """Eventos y compromisos en el calendario académico inteligente."""
    __tablename__ = "academy_calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    offering_id = Column(UUID(as_uuid=True), ForeignKey("academy_period_offerings.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=False)  # 'evaluation', 'assignment', 'socratic_defense', 'study_group', 'milestone'
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    offering = relationship("AcademyPeriodOffering", foreign_keys=[offering_id])
    creator = relationship("Persona", foreign_keys=[created_by])


class AcademyContentRecommendation(Base):
    """Recomendaciones personalizadas de contenido, tutoría y grupos de estudio."""
    __tablename__ = "academy_content_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    recommendation_type = Column(String(50), nullable=False)  # 'study_group', 'socratic_tutor', 'course', 'resource', 'learning_path', 'mentor'
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    score = Column(Float, nullable=False, default=1.0)
    target_url = Column(String(500), nullable=True)
    viewed = Column(Boolean, nullable=False, default=False)
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    student = relationship("Persona", foreign_keys=[student_id])


class AcademyMentorProfile(Base):
    """Perfil de mentor académico disponible para acompañamiento."""
    __tablename__ = "academy_mentor_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    mentor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, unique=True, index=True)
    bio = Column(Text, nullable=True)
    expertise = Column(JSON, nullable=True)  # List of areas e.g. ["Teología", "Consejería"]
    availability_summary = Column(String(255), nullable=True)
    max_mentees = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    mentor = relationship("Persona", foreign_keys=[mentor_persona_id])


class AcademyMentorshipRequest(Base):
    """Solicitudes y vinculaciones de mentoría personalizada entre estudiantes y mentores."""
    __tablename__ = "academy_mentorship_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    mentor_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    mentee_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending")  # 'pending', 'accepted', 'rejected', 'completed'
    message = Column(Text, nullable=True)
    response_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    mentor = relationship("Persona", foreign_keys=[mentor_persona_id])
    mentee = relationship("Persona", foreign_keys=[mentee_persona_id])

