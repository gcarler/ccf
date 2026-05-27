from backend.models_shared import *
from sqlalchemy.dialects.postgresql import UUID

from backend.models_shared import _utcnow


# 2. ACADEMY & FORUM
class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
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
    created_at = Column(DateTime, default=_utcnow)
    lessons = relationship("Lesson", back_populates="course")
    enrollments = relationship("Enrollment", back_populates="course")
    prerequisites = relationship(
        "CoursePrerequisite",
        foreign_keys="CoursePrerequisite.course_id",
        back_populates="course",
    )


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    prerequisite_course_id = Column(
        Integer, ForeignKey("courses.id"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "course_id", "prerequisite_course_id", name="uq_course_prerequisite"
        ),
    )

    course = relationship(
        "Course", foreign_keys=[course_id], back_populates="prerequisites"
    )
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id])


class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
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
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    progress_percent = Column(Numeric(5, 2), default=0)
    last_position_seconds = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress"),
    )


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    course_id = Column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True
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
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(
        Integer, ForeignKey("assessments.id"), nullable=False, index=True
    )
    question_text = Column(Text, nullable=False)
    question_type = Column(String(20), default="multiple_choice")
    points = Column(Integer, default=10)

    assessment = relationship("Assessment", back_populates="questions")
    options = relationship("AssessmentOption", back_populates="question")


class AssessmentOption(Base):
    __tablename__ = "assessment_options"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer, ForeignKey("assessment_questions.id"), nullable=False, index=True
    )
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("AssessmentQuestion", back_populates="options")


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(
        Integer, ForeignKey("enrollments.id"), nullable=False, index=True
    )
    assessment_id = Column(
        Integer, ForeignKey("assessments.id"), nullable=False, index=True
    )
    score = Column(Numeric(5, 2), default=0)
    passed = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    answers = relationship(
        "AssessmentAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(
        Integer,
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(Integer, ForeignKey("assessment_questions.id"), nullable=False)
    selected_option_id = Column(
        Integer, ForeignKey("assessment_options.id"), nullable=True
    )
    text_response = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Numeric(5, 2), default=0)

    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("AssessmentQuestion")
    selected_option = relationship("AssessmentOption")


class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    title = Column(String(200), nullable=False)
    file_url = Column(String(500), nullable=False)
    resource_type = Column(String(50), nullable=True)

    lesson = relationship("Lesson", back_populates="resources")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(
        Integer, ForeignKey("enrollments.id"), nullable=False, index=True
    )
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False, index=True)
    file_url = Column(String(500), nullable=False)
    comment = Column(Text, nullable=True)
    grade = Column(Numeric(5, 2), nullable=True)
    teacher_feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class FormalActa(Base):
    __tablename__ = "formal_actas"
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    closed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="closed")  # closed, archived
    min_grade_required = Column(Numeric(5, 2), default=70)
    min_attendance_required = Column(Numeric(5, 2), default=75)
    created_at = Column(DateTime, default=_utcnow)


class ForumComment(Base):
    __tablename__ = "forum_comments"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("forum_threads.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    personas = relationship("Persona", back_populates="family")


class CellGroup(Base):
    __tablename__ = "cell_groups"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, nullable=True, index=True)
    name = Column(String(100), nullable=False)
    zone = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    leader_name = Column(String(100), nullable=True)
    members_count = Column(Integer, default=0)
    capacity = Column(Integer, default=15)
    day_of_week = Column(String(20), nullable=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    status = Column(String(20), default="Activo", index=True)

    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=True, index=True)

    evangelism_strategy_id = Column(
        String(50),
        ForeignKey("estrategias_evangelismo.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    leader_persona_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    assistant_persona_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )
    host_persona_id = Column(
        UUID(as_uuid=True), ForeignKey("personas.id", ondelete="SET NULL"), nullable=True
    )

    schedule = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    leader = relationship("Persona", foreign_keys=[leader_persona_id])
    assistant = relationship("Persona", foreign_keys=[assistant_persona_id])
    host = relationship("Persona", foreign_keys=[host_persona_id])

    base_attendees = relationship(
        "CellGroupMember", back_populates="cell_group", cascade="all, delete-orphan"
    )


class CellGroupMember(Base):
    __tablename__ = "cell_group_members"
    id = Column(Integer, primary_key=True, index=True)
    cell_group_id = Column(
        Integer,
        ForeignKey("cell_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), default="asistente")

    rol_personalizado_id = Column(
        Integer,
        ForeignKey("estrategia_roles_personalizados.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    fecha_ingreso = Column(DateTime, default=_utcnow)
    activo = Column(Boolean, default=True, index=True)

    cell_group = relationship("CellGroup", back_populates="base_attendees")
    persona = relationship("Persona")


class CellGroupSession(Base):
    """A single weekly/monthly reporting session for a Faro en Casa house."""

    __tablename__ = "cell_group_sessions"
    __table_args__ = (
        UniqueConstraint(
            "cell_group_id", "season_id", "session_date", name="uq_cell_session"
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    cell_group_id = Column(
        Integer,
        ForeignKey("cell_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id = Column(
        Integer,
        ForeignKey("campaign_seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(Date, nullable=False, index=True)
    report_deadline = Column(DateTime, nullable=True)
    status = Column(String(20), default="Realizada")  # Realizada | Cancelada
    topic = Column(String(255), nullable=True)
    offering_amount = Column(Numeric(12, 2), nullable=True)
    report_notes = Column(Text, nullable=True)
    novelty_type = Column(String(50), nullable=True)
    novelty_detail = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    reported_by_persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    cell_group = relationship("CellGroup")
    season = relationship("CampaignSeason", foreign_keys=[season_id])
    reported_by_persona = relationship("Persona")


class CellGroupAttendance(Base):
    """Attendance record of a member at a Faro en Casa session."""

    __tablename__ = "cell_group_attendance"
    __table_args__ = (
        UniqueConstraint("session_id", "persona_id", name="uq_faro_attendance"),
    )
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(
        Integer,
        ForeignKey("cell_group_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    persona_id = Column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attended = Column(Boolean, default=True)
    absence_reason = Column(String(50), nullable=True, index=True)
    absence_reason_detail = Column(Text, nullable=True)
    scanned_at = Column(DateTime, default=_utcnow, index=True)
    status = Column(String(20), default="present")  # present | absent | first_time
    notes = Column(Text, nullable=True)

    # --- Nuevos campos (refactor evangelismo) ---
    estado = Column(String(20), default="ASISTIO", index=True)  # EstadoAsistenciaEnum
    es_primera_vez = Column(Boolean, default=False, index=True)
    requiere_seguimiento = Column(Boolean, default=False, index=True)
    motivo_excusa_id = Column(
        Integer,
        ForeignKey("motivos_excusa.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detalle_excusa = Column(String, nullable=True)

    session = relationship("CellGroupSession")
    persona = relationship("Persona")


class CampaignSeason(Base):
    """Represents an evangelistic campaign season (e.g. 'Faro en Casa 2026')."""

    __tablename__ = "campaign_seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    periodicity = Column(
        String(20), default="SEMANAL", nullable=False
    )  # SEMANAL | MENSUAL
    status = Column(String(20), default="Activa", index=True)  # Activa | Finalizada
    created_at = Column(DateTime, default=_utcnow)


class ConsolidationPipeline(Base):
    """Pipeline leads table (legacy). Referenced by multiple modules."""

    __tablename__ = "consolidation_pipeline"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    source = Column(String(100), nullable=True)
    landing_page = Column(String(500), nullable=True)
    campaign = Column(String(200), nullable=True, index=True)
    stage = Column(String(20), default="new", index=True)
    notes = Column(Text, nullable=True)
    assigned_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_user_course"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    status = Column(String(20), default="active")  # active, completed, dropped
    progress_percent = Column(Float, default=0)
    final_grade = Column(Float, nullable=True)
    attendance_percent = Column(Float, default=0)
    lessons_completed = Column(JSON, nullable=True, default=list)
    approved = Column(Boolean, default=False)
    acta_closed = Column(Boolean, default=False)
    certificate_issued = Column(Boolean, default=False)
    certificate_code = Column(String(64), nullable=True)
    access_window_end = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


class AcademyActivityLog(Base):
    __tablename__ = "academy_activity_logs"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(
        String(50), nullable=False, index=True
    )  # enrollment, completion, drop, certificate
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    modality = Column(String(20), nullable=True)  # formal, no_formal
    value = Column(Numeric(10, 2), default=1.0)
    created_at = Column(DateTime, default=_utcnow, index=True)


class ForumThread(Base):
    __tablename__ = "forum_threads"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CourseAttendance(Base):
    __tablename__ = "course_attendance"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(
        Integer,
        ForeignKey("enrollments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(DateTime, default=_utcnow, index=True)
    status = Column(String(20), default="present")  # present, absent, justified
    recorded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    enrollment = relationship("Enrollment")


class Certificate(Base):
    __tablename__ = "certificates"
    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(
        Integer, ForeignKey("enrollments.id"), nullable=False, index=True
    )
    certificate_code = Column(String(64), unique=True, nullable=False, index=True)
    issued_at = Column(DateTime, default=_utcnow)

    enrollment = relationship("Enrollment")
