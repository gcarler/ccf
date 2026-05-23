# Identity & auth
# Academy / LMS
from backend.models_academy import AcademyActivityLog  # noqa: F401
from backend.models_academy import (
    Assessment,
    AssessmentAttempt,
    AssessmentOption,
    AssessmentQuestion,
    AssignmentSubmission,
    Certificate,
    Course,
    CourseAttendance,
    CoursePrerequisite,
    Enrollment,
    Family,
    FaroSeason,
    FormalActa,
    ForumComment,
    ForumThread,
    GloryHouse,
    GloryHouseAttendance,
    GloryHouseMember,
    GloryHouseSession,
    Lesson,
    LessonProgress,
    Resource,
)
from backend.models_agents import AgentInsight, AgentTask  # noqa: F401

# Assets / Agents / Governance / Ops
from backend.models_assets import AssetItem, InventoryItem, MaintenanceLog  # noqa: F401

# CMS
from backend.models_cms import CmsMediaItem  # noqa: F401
from backend.models_cms import (
    Announcement,
    CmsMenu,
    CmsMenuItem,
    CmsPage,
    CmsPageVersion,
    CmsPublishLog,
    CmsSection,
    CmsSite,
    CmsTheme,
    ContentMetric,
    ContentPublication,
    MediaAsset,
    NewsletterSubscription,
    PageContent,
    PageContentVersion,
    Testimonial,
)

# CRM / Pastoral
from backend.models_crm import ChatMessage  # noqa: F401
from backend.models_crm import (
    AgendaEvent,
    CommunicationLog,
    CommunityBoardCard,
    ConsolidationAssignment,
    ConsolidationCase,
    ConsolidationFollowUpTask,
    ConsolidationInteraction,
    ConsolidationPipeline,
    CounselingTicket,
    CrmAutomation,
    CrmEvent,
    CrmTask,
    Donation,
    DonationCategory,
    EventAssignment,
    EventAttendance,
    Fund,
    Member,
    MemberMinistry,
    MemberPosition,
    MemberRole,
    Ministry,
    PastoralCallLog,
    Position,
    PrayerRequest,
    RoleDefinition,
    SpiritualMilestone,
    SupportTicket,
    VolunteerShift,
    VolunteerSkill,
    member_volunteer_skills,
)
from backend.models_governance import AdminAuditLog, AutomationRule  # noqa: F401
from backend.models_identity import Notification  # noqa: F401
from backend.models_identity import (
    Badge,
    Level,
    RefreshToken,
    ResetToken,
    Role,
    User,
    UserBadge,
    UserReminder,
    UserUIPreference,
    VerificationToken,
)
from backend.models_ops import SocialChannel  # noqa: F401
from backend.models_ops import ChurchLocation, SystemVariable

# Projects
from backend.models_projects import ProjectActivityLog  # noqa: F401
from backend.models_projects import (
    Project,
    ProjectAttachment,
    ProjectComment,
    ProjectDocument,
    ProjectInboxState,
    ProjectMilestone,
    ProjectPhase,
    ProjectTask,
    ProjectWhiteboard,
    TaskSupply,
)
