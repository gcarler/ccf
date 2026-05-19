# Identity & auth
from backend.models_identity import (  # noqa: F401
    Role,
    Level,
    User,
    Badge,
    UserBadge,
    UserUIPreference,
    Notification,
    UserReminder,
    RefreshToken,
)

# Academy / LMS
from backend.models_academy import (  # noqa: F401
    Course,
    CoursePrerequisite,
    Lesson,
    LessonProgress,
    Assessment,
    AssessmentQuestion,
    AssessmentOption,
    AssessmentAttempt,
    Resource,
    AssignmentSubmission,
    FormalActa,
    ForumComment,
    Family,
    GloryHouse,
    GloryHouseMember,
    FaroSeason,
    GloryHouseSession,
    GloryHouseAttendance,
    Enrollment,
    AcademyActivityLog,
    ForumThread,
    CourseAttendance,
    Certificate,
)

# CRM / Pastoral
from backend.models_crm import (  # noqa: F401
    ChatMessage,
    ConsolidationPipeline,
    AgendaEvent,
    CrmEvent,
    EventAssignment,
    EventAttendance,
    CounselingTicket,
    PrayerRequest,
    Ministry,
    Member,
    Position,
    MemberPosition,
    ConsolidationCase,
    ConsolidationAssignment,
    ConsolidationInteraction,
    ConsolidationFollowUpTask,
    Donation,
    DonationCategory,
    CrmTask,
    VolunteerShift,
    VolunteerSkill,
    CommunicationLog,
    CrmAutomation,
    RoleDefinition,
    MemberRole,
    MemberMinistry,
    Fund,
    PastoralCallLog,
    SpiritualMilestone,
    SupportTicket,
    CommunityBoardCard,
    member_volunteer_skills,
)

# Projects
from backend.models_projects import (  # noqa: F401
    Project,
    ProjectMilestone,
    ProjectActivityLog,
    ProjectWhiteboard,
    ProjectTask,
    ProjectAttachment,
    TaskSupply,
    ProjectComment,
    ProjectDocument,
    ProjectInboxState,
)

# Assets / Agents / Governance / Ops
from backend.models_assets import InventoryItem, AssetItem, MaintenanceLog  # noqa: F401
from backend.models_agents import AgentInsight, AgentTask  # noqa: F401
from backend.models_governance import AdminAuditLog, AutomationRule  # noqa: F401
from backend.models_ops import ChurchLocation, SocialChannel, SystemVariable  # noqa: F401

# CMS
from backend.models_cms import (  # noqa: F401
    PageContent,
    PageContentVersion,
    ContentPublication,
    ContentMetric,
    MediaAsset,
    CmsMediaItem,
    CmsSite,
    CmsTheme,
    CmsMenu,
    CmsMenuItem,
    CmsPage,
    CmsPageVersion,
    CmsSection,
    CmsPublishLog,
    Announcement,
    Testimonial,
    NewsletterSubscription,
)
