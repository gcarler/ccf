from backend.models_shared import *
from backend.models_shared import _utcnow
import uuid as _uuid

# 2. ACADEMY & FORUM
class Course(Base):
    __tablename__ = "courses"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    code = Column(String(20), unique=True, index=True, nullable=False)
    title = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    modality = Column(String(20), nullable=False, index=True)
    is_published = Column(Boolean, default=True)
    is_self_paced = Column(Boolean, default=True)
    duration_hours = Column(Integer, default=0)
    cohort_name = Column(String(100), nullable=True)
    certificate_type = Column(String(50), default="ParticipaciÃ³n")
    xp_per_lesson = Column(Integer, default=10)
    image_url = Column(String(500), nullable=True)
    instructor_name = Column(String(200), nullable=True)
    sede_id = Column(UUID(as_uuid=True), ForeignKey("sedes.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")
    prerequisites = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course",
    )

class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    prerequisite_course_id = Column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "course_id", "prerequisite_course_id", name="uq_course_prerequisite_pair"
        ),
    )

    course = relationship(
        "Course", foreign_keys=[course_id], back_populates="prerequisites"
    )
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id])

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="video")  # video, pdf, quiz
    media_url = Column(String(255), nullable=True)
    order_index = Column(Integer, default=0)
    duration_minutes = Column(Integer, default=0)
    course = relationship("Course", back_populates="lessons")
    resources = relationship("Resource", back_populates="lesson")
    assessments = relationship("Assessment", back_populates="lesson")

class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, index=True)
    progress_percent = Column(Numeric(5, 2), default=0)
    last_position_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("persona_id", "lesson_id", name="uq_persona_lesson_progress"),
    )

class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, index=True)
    course_id = Column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True, index=True
    )  # Direct course relation
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    min_score = Column(Numeric(5, 2), default=70)
    weight = Column(Numeric(5, 2), default=1.0)

    lesson = relationship("Lesson", back_populates="assessments")
    course = relationship("Course")  # New relationship
    questions = relationship("AssessmentQuestion", back_populates="assessment")

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")
    points = Column(Integer, default=10)

    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question")

class AssessmentOption(Base):
    __tablename__ = "assessment_options"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    question_id = Column(
        UUID(as_uuid=True), ForeignKey("assessment_questions.id"), nullable=False, index=True
    )
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("AssessmentQuestion", back_populates="options")

class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    assessment_id = Column(
        UUID(as_uuid=True), ForeignKey("assessments.id"), nullable=False, index=True
    )
    score = Column(Numeric(5, 2), default=0)
    passed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

    answers = relationship(
        "AssessmentAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )

class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    attempt_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(UUID(as_uuid=True), ForeignKey("assessment_questions.id"), nullable=False)
    selected_option_id = Column(
        UUID(as_uuid=True), ForeignKey("assessment_options.id"), nullable=True
    )
    text_response = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Numeric(5, 2), default=0)

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("AssessmentQuestion")
    selected_option = relationship("AssessmentOption")

class Resource(Base):
    __tablename__ = "resources"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=False)
    resource_type = Column(String(50), nullable=True)

    lesson = relationship("Lesson", back_populates="resources")

class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, index=True)
    file_url = Column(String(500), nullable=False)
    comment = Column(Text, nullable=True)
    grade = Column(Numeric(5, 2), nullable=True)
    teacher_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class FormalActa(Base):
    __tablename__ = "formal_actas"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    closed_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    status = Column(String(20), default="closed")  # closed, archived
    min_grade_required = Column(Numeric(5, 2), default=70)
    min_attendance_required = Column(Numeric(5, 2), default=75)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class ForumComment(Base):
    __tablename__ = "forum_comments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("forum_threads.id"), nullable=False)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class Family(Base):
    __tablename__ = "families"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    personas = relationship("Persona", back_populates="family")

class CampaignSeason(Base):
    """Represents an evangelistic campaign season (e.g. 'Temporada 2026')."""

    __tablename__ = "campaign_seasons"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    periodicity = Column(
        String(20), default="SEMANAL", nullable=False
    )  # SEMANAL | MENSUAL
    status = Column(String(20), default="Activa", index=True)  # Activa | Finalizada
    created_at = Column(DateTime(timezone=True), default=_utcnow)

class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("persona_id", "course_id", name="uq_persona_course"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True, index=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String(20), default="active")  # active, completed, dropped
    progress_percent = Column(Float, default=0)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0)
    lessons_completed = Column(JSON, nullable=True, default=list)
    approved = Column(Boolean, default=False)
    acta_closed = Column(Boolean, default=False)
    certificate_issued = Column(Boolean, default=False)
    certificate_code = Column(String(64), nullable=True)
    access_window_end = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)
    persona = relationship("Persona")
    course = relationship("Course", back_populates="enrollments")

class AcademyActivityLog(Base):
    __tablename__ = "academy_activity_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    event_type = Column(
        String(50), nullable=False, index=True
    )  # enrollment, completion, drop, certificate
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=True)
    persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)
    modality = Column(String(20), nullable=True)  # formal, no_formal
    value = Column(Numeric(10, 2), default=1.0)
    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)

class ForumThread(Base):
    __tablename__ = "forum_threads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    title = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    author_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

class CourseAttendance(Base):
    __tablename__ = "course_attendance"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(DateTime(timezone=True), default=_utcnow, index=True)
    status = Column(String(20), default="present")  # present, absent, justified
    recorded_by_persona_id = Column(UUID(as_uuid=True), ForeignKey("personas.id"), nullable=True)

    enrollment = relationship("Enrollment")

class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4)
    enrollment_id = Column(
        UUID(as_uuid=True), ForeignKey("enrollments.id"), nullable=False, index=True
    )
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime(timezone=True), default=_utcnow)

    enrollment = relationship("Enrollment")
