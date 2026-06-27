"""Canonical Academy models backed exclusively by ``academy_*`` tables."""

import uuid as _uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
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
    prerequisite_course_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_courses.id"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("course_id", "prerequisite_course_id", name="uq_course_prerequisite"),
    )

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

    __table_args__ = (
        UniqueConstraint("persona_id", "lesson_id", name="uq_lesson_progress_persona_lesson"),
    )


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
    assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_assessments.id"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), default="multiple_choice", nullable=False)
    points = Column(Integer, default=1, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question")


class AssessmentOption(Base):
    __tablename__ = "academy_assessment_options"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_assessment_questions.id"), nullable=False, index=True
    )
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

    __table_args__ = (
        UniqueConstraint("persona_id", "course_id", name="uq_enrollment_persona_course"),
    )


class AssessmentAttempt(Base):
    __tablename__ = "academy_assessment_attempts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_assessments.id"), nullable=False, index=True
    )
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True
    )
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
    question_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_assessment_questions.id"), nullable=False
    )
    selected_option_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_assessment_options.id"), nullable=True
    )
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
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True
    )
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("academy_lessons.id"), nullable=False, index=True)
    file_url = Column("seaweed_fid", String(500), nullable=False)
    comment = Column(Text, nullable=True)
    teacher_feedback = Column(Text, nullable=True)
    grade = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)


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
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False, index=True
    )
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
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("academy_enrollments.id"), nullable=False
    )
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
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)
