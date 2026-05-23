from backend.models_shared import *
from backend.models_shared import _utcnow


# 3. CRM & CHAT
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(String(100), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow, index=True)


class ConsolidationPipeline(Base):
    __tablename__ = "consolidation_pipeline"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    source = Column(String(100), nullable=True)
    stage = Column(String(20), default="new", index=True)
    notes = Column(Text, nullable=True)

    assigned_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    pastor = relationship("User", back_populates="assigned_leads")


class AgendaEvent(Base):
    __tablename__ = "agenda_events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=True, index=True)
    location = Column(String(200), nullable=True)
    is_all_day = Column(Boolean, default=True, index=True)
    created_by_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class CrmEvent(Base):
    __tablename__ = "crm_events"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime, nullable=True, index=True)
    event_type = Column(String(20), default="PERMANENT", index=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    day_of_week = Column(Integer, nullable=True)
    month_day = Column(String(10), nullable=True)
    location = Column(String(200), nullable=True)
    status = Column(String(20), default="SCHEDULED", index=True)
    cancellation_reason = Column(Text, nullable=True)
    target_audience = Column(String(50), default="ALL")
    target_role_id = Column(Integer, ForeignKey("role_definitions.id"), nullable=True)
    target_role_ids = Column(JSON, nullable=True)
    target_member_ids = Column(JSON, nullable=True)
    fixed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    attendances = relationship("EventAttendance", back_populates="event")
    assignments = relationship("EventAssignment", back_populates="event")


class EventAssignment(Base):
    __tablename__ = "event_assignments"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("crm_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(Date, nullable=False, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=False, index=True)  # e.g. MC, PREACHER, OFFERING
    created_at = Column(DateTime, default=_utcnow)

    event = relationship("CrmEvent", back_populates="assignments")
    member = relationship("Member")


class EventAttendance(Base):
    __tablename__ = "event_attendances"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "session_date", "member_id", name="uq_event_attendance"
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(
        Integer,
        ForeignKey("crm_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_date = Column(
        Date, nullable=False, index=True, default=lambda: _utcnow().date()
    )
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), default="present", index=True)
    role_at_event = Column(String(30), default="attendee", index=True)
    source = Column(String(30), default="manual", index=True)
    check_in_at = Column(DateTime, nullable=True, index=True)
    check_out_at = Column(DateTime, nullable=True, index=True)
    notes = Column(Text, nullable=True)
    scanned_at = Column(DateTime, default=_utcnow, index=True)
    attended = Column(Boolean, default=True)

    event = relationship("CrmEvent", back_populates="attendances")
    member = relationship("Member")


class CounselingTicket(Base):
    __tablename__ = "counseling_tickets"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subject = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(
        String(50), default="open", index=True
    )  # open, in_progress, resolved
    priority_level = Column(
        String(20), default="NORMAL", index=True
    )  # URGENT, HIGH, NORMAL
    sentiment_score = Column(Float, nullable=True)  # -1.0 to 1.0
    sentiment_label = Column(String(20), nullable=True)  # POSITIVE, NEUTRAL, NEGATIVE
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member")
    pastor = relationship("User")


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"
    id = Column(Integer, primary_key=True, index=True)
    requester_name = Column(String(200), nullable=False, index=True)
    request_text = Column(Text, nullable=False)
    category = Column(String(50), default="General")
    is_public = Column(Boolean, default=False, index=True)
    source = Column(String(50), default="crm", index=True)  # web, crm, evangelism
    status = Column(
        String(50), default="pending", index=True
    )  # pending, praying, answered
    created_at = Column(DateTime, default=_utcnow, index=True)


class Ministry(Base):
    __tablename__ = "ministries"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(Integer, ForeignKey("members.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    members = relationship(
        "Member",
        secondary="member_ministries",
        back_populates="ministries",
        overlaps="member,members,ministries,ministry",
    )


class Member(Base):
    __tablename__ = "members"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    email = Column(String(100), nullable=True, index=True)
    phone = Column(String(20), nullable=True, index=True)
    church_role = Column(String(50), default="Miembro", index=True)
    is_baptized = Column(Boolean, default=False, index=True)
    spiritual_status = Column(
        String(50), default="Nuevo", index=True
    )  # Nuevo, Creyente, DiscÃ­pulo, Servidor

    # --- New Management Fields ---
    talents = Column(Text, nullable=True)  # Habilidades (MÃºsica, Tech, Cocina, etc)
    spiritual_gifts = Column(
        Text, nullable=True
    )  # Dones (Liderazgo, Misericordia, etc)
    pastoral_notes = Column(Text, nullable=True)  # Notas internas para el pastor

    created_at = Column(DateTime, default=_utcnow, index=True)

    user = relationship("User", backref=backref("member_profile", uselist=False))
    family = relationship("Family", back_populates="members")
    ministries = relationship(
        "Ministry",
        secondary="member_ministries",
        back_populates="members",
        overlaps="member,members,ministries,ministry",
    )
    donations = relationship("Donation", back_populates="member")
    tasks = relationship("CrmTask", back_populates="member")
    event_attendances = relationship(
        "EventAttendance", back_populates="member", cascade="all, delete-orphan"
    )
    volunteer_shifts = relationship(
        "VolunteerShift", back_populates="member", cascade="all, delete-orphan"
    )
    communication_logs = relationship(
        "CommunicationLog", back_populates="member", cascade="all, delete-orphan"
    )
    positions = relationship(
        "MemberPosition", back_populates="member", cascade="all, delete-orphan"
    )
    consolidation_cases = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.member_id",
        back_populates="member",
        cascade="all, delete-orphan",
    )
    consolidated_cases_as_pastor = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.assigned_pastor_id",
        back_populates="assigned_pastor",
    )
    consolidated_cases_as_leader = relationship(
        "ConsolidationCase",
        foreign_keys="ConsolidationCase.assigned_leader_id",
        back_populates="assigned_leader",
    )
    consolidation_assignments_sent = relationship(
        "ConsolidationAssignment",
        foreign_keys="ConsolidationAssignment.assigned_by_member_id",
        back_populates="assigned_by_member",
    )
    consolidation_assignments_received = relationship(
        "ConsolidationAssignment",
        foreign_keys="ConsolidationAssignment.assigned_to_member_id",
        back_populates="assigned_to_member",
    )
    consolidation_interactions = relationship(
        "ConsolidationInteraction",
        foreign_keys="ConsolidationInteraction.performed_by_member_id",
        back_populates="performed_by_member",
    )


class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    member_positions = relationship(
        "MemberPosition", back_populates="position", cascade="all, delete-orphan"
    )


class MemberPosition(Base):
    __tablename__ = "member_positions"
    __table_args__ = (
        UniqueConstraint(
            "member_id", "position_id", "start_date", name="uq_member_position_history"
        ),
    )
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position_id = Column(
        Integer,
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    start_date = Column(DateTime, nullable=True, index=True)
    end_date = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member", back_populates="positions")
    position = relationship("Position", back_populates="member_positions")


class ConsolidationCase(Base):
    __tablename__ = "consolidation_cases"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(String(20), default="new", index=True)
    status = Column(String(20), default="active", index=True)
    source = Column(String(100), nullable=True)
    last_contact_at = Column(DateTime, nullable=True, index=True)
    next_contact_at = Column(DateTime, nullable=True, index=True)
    assigned_pastor_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_leader_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, index=True)

    member = relationship(
        "Member", foreign_keys=[member_id], back_populates="consolidation_cases"
    )
    assigned_pastor = relationship(
        "Member",
        foreign_keys=[assigned_pastor_id],
        back_populates="consolidated_cases_as_pastor",
    )
    assigned_leader = relationship(
        "Member",
        foreign_keys=[assigned_leader_id],
        back_populates="consolidated_cases_as_leader",
    )
    assignments = relationship(
        "ConsolidationAssignment", back_populates="case", cascade="all, delete-orphan"
    )
    interactions = relationship(
        "ConsolidationInteraction", back_populates="case", cascade="all, delete-orphan"
    )
    follow_up_tasks = relationship(
        "ConsolidationFollowUpTask", back_populates="case", cascade="all, delete-orphan"
    )


class ConsolidationAssignment(Base):
    __tablename__ = "consolidation_assignments"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("consolidation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_by_member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_to_member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=True)
    priority = Column(String(20), default="normal", index=True)
    start_date = Column(DateTime, default=_utcnow, index=True)
    end_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="active", index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    case = relationship("ConsolidationCase", back_populates="assignments")
    assigned_by_member = relationship(
        "Member",
        foreign_keys=[assigned_by_member_id],
        back_populates="consolidation_assignments_sent",
    )
    assigned_to_member = relationship(
        "Member",
        foreign_keys=[assigned_to_member_id],
        back_populates="consolidation_assignments_received",
    )
    follow_up_tasks = relationship(
        "ConsolidationFollowUpTask",
        back_populates="assignment",
        cascade="all, delete-orphan",
    )


class ConsolidationInteraction(Base):
    __tablename__ = "consolidation_interactions"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("consolidation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    performed_by_member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    interaction_type = Column(String(50), nullable=False, index=True)
    interaction_date = Column(DateTime, default=_utcnow, index=True)
    result = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    next_action_date = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    case = relationship("ConsolidationCase", back_populates="interactions")
    performed_by_member = relationship(
        "Member",
        foreign_keys=[performed_by_member_id],
        back_populates="consolidation_interactions",
    )


class ConsolidationFollowUpTask(Base):
    __tablename__ = "consolidation_follow_up_tasks"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(
        Integer,
        ForeignKey("consolidation_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assignment_id = Column(
        Integer,
        ForeignKey("consolidation_assignments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True, index=True)
    status = Column(String(20), default="pending", index=True)
    completed_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    case = relationship("ConsolidationCase", back_populates="follow_up_tasks")
    assignment = relationship(
        "ConsolidationAssignment", back_populates="follow_up_tasks"
    )


class Donation(Base):
    __tablename__ = "donations"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    amount = Column(Float, nullable=False)
    donation_type = Column(String(50), default="Diezmo")  # Diezmo, Ofrenda, Especial
    status = Column(String(20), default="completed")
    reference_code = Column(String(100), nullable=True)
    payment_method = Column(String(50), default="Transferencia")
    fund_id = Column(Integer, nullable=True)
    person_id = Column(Integer, nullable=True)
    donor_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member", back_populates="donations")


class DonationCategory(Base):
    __tablename__ = "donation_categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    color_code = Column(String(50), default="blue")
    is_active = Column(Boolean, default=True)


class CrmTask(Base):
    __tablename__ = "crm_tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), default="Pastoral", nullable=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=True, index=True)
    lead_id = Column(
        Integer, ForeignKey("consolidation_pipeline.id"), nullable=True, index=True
    )
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    due_date = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    priority = Column(String(20), default="medium")
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member", back_populates="tasks")
    lead = relationship("ConsolidationPipeline")
    assignee = relationship("User")


class VolunteerShift(Base):
    __tablename__ = "volunteer_shifts"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, index=True)
    role_name = Column(String(100), nullable=False)
    team_name = Column(String(100), nullable=False)
    shift_start = Column(DateTime, nullable=False)
    shift_end = Column(DateTime, nullable=False)
    status = Column(String(20), default="confirmed")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    member = relationship("Member", back_populates="volunteer_shifts")


class VolunteerSkill(Base):
    __tablename__ = "volunteer_skills"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100))


member_volunteer_skills = Table(
    "member_volunteer_skills",
    Base.metadata,
    Column(
        "member_id",
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        Integer,
        ForeignKey("volunteer_skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class CommunicationLog(Base):
    __tablename__ = "communication_logs"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = Column(String(50), nullable=False, index=True)
    recipient_phone = Column(String(30), nullable=True)
    campaign_name = Column(String(120), nullable=True, index=True)
    content = Column(Text, nullable=False)
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    outcome = Column(String(50), default="sent", index=True)
    external_id = Column(String(120), nullable=True, index=True)
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    member = relationship("Member", back_populates="communication_logs")
    leader = relationship("User")


class SpiritualMilestone(Base):
    __tablename__ = "spiritual_milestones"
    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, nullable=False, index=True)
    type = Column(
        String(100), nullable=False, index=True
    )  # bautismo, membresia, ministerio, etc.
    event_date = Column(Date, nullable=False)
    minister_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow, index=True)

    minister = relationship("User")


class CrmAutomation(Base):
    __tablename__ = "crm_automations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)
    action_payload = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)


class RoleDefinition(Base):
    __tablename__ = "role_definitions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(50), default="blue")
    is_leadership = Column(Boolean, default=False, index=True)
    is_system_locked = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=_utcnow)


class MemberRole(Base):
    __tablename__ = "member_roles"
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role_id = Column(
        Integer,
        ForeignKey("role_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=_utcnow)

    member = relationship("Member")
    role = relationship("RoleDefinition")


class PastoralCallLog(Base):
    __tablename__ = "pastoral_call_logs"
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(
        Integer, ForeignKey("consolidation_pipeline.id"), nullable=False, index=True
    )
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    outcome = Column(String(120), nullable=False)
    notes = Column(Text, nullable=True)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


class MemberMinistry(Base):
    """Rich association between Member and Ministry with role and dates."""

    __tablename__ = "member_ministries"
    __table_args__ = (
        UniqueConstraint("member_id", "ministry_id", name="uq_member_ministry"),
    )
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(
        Integer,
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ministry_id = Column(
        Integer,
        ForeignKey("ministries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(50), nullable=True)  # e.g. Líder, Asistente, Coordinador
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    member = relationship("Member", overlaps="member,members,ministries,ministry")
    ministry = relationship("Ministry", overlaps="member,members,ministries,ministry")


class Fund(Base):
    __tablename__ = "funds"
    fund_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    current_balance = Column(Float, default=0.0)
    target_amount = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(20), default="open", index=True
    )  # open, in_progress, resolved, closed
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, onupdate=_utcnow)

    user = relationship("User")


class CommunityBoardCard(Base):
    __tablename__ = "community_board_cards"
    id = Column(Integer, primary_key=True, index=True)
    column_id = Column(String(50), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow, index=True)


class EvangelismStrategy(Base):
    __tablename__ = "evangelism_strategies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(String(100), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=_utcnow, index=True)
    updated_at = Column(DateTime, onupdate=_utcnow)
