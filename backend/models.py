# Identity & auth
# Academy / LMS
from backend.models_academy import AcademyActivityLog  # noqa: F401
from backend.models_academy import (  # noqa: F401
    Assessment, AssessmentAttempt, AssessmentOption, AssessmentQuestion,
    AssignmentSubmission, Certificate, CellGroup, CellGroupAttendance,
    CellGroupMember, CellGroupSession, Course,
    CourseAttendance, CoursePrerequisite, Enrollment, Family, CampaignSeason,
    FormalActa, ForumComment, ForumThread, Lesson, LessonProgress, Resource)


# Assets / Agents / Governance / Ops
from backend.models_assets import (AssetItem, InventoryItem,  # noqa: F401
                                   MaintenanceLog)
# CMS
from backend.models_cms import CmsMediaItem  # noqa: F401
from backend.models_cms import (  # noqa: F401
    Announcement, CmsMenu, CmsMenuItem, CmsPage,
    CmsPageVersion, CmsPublishLog, CmsSection,
    CmsSite, CmsTheme, ContentMetric,
    ContentPublication, MediaAsset,
    NewsletterSubscription, PageContent,
    PageContentVersion, Testimonial)
# Personas (reemplaza Persona — UUID PK)
from backend.models_personas import Persona  # noqa: F401

# CRM / Pastoral
from backend.models_crm import ChatMessage  # noqa: F401
from backend.models_crm import (  # noqa: F401
    AgendaEvent, ColombianCity, ColombianDepartment,
    CommunicationLog, CommunityBoardCard,
    ConsolidationAssignment, ConsolidationCase,
    ConsolidationInteraction, ConsolidationTask,
    CounselingTicket, CrmAutomation,
    CrmEvent, CrmTask, Donation, DonationCategory, EventAssignment,
    EventAttendance, EvangelismStrategy, Fund, MemberMinistry,
    MemberPosition, MemberRole, Ministry, PastoralCallLog, Position,
    PrayerRequest, RoleDefinition, SpiritualMilestone, SupportTicket,
    VolunteerShift, VolunteerSkill, member_volunteer_skills)
from backend.models_governance import (AdminAuditLog,  # noqa: F401
                                       AutomationRule)
from backend.models_identity import Notification  # noqa: F401
from backend.models_identity import (  # noqa: F401
    Badge, Level, RefreshToken, ResetToken,
    Role, User, UserBadge, UserReminder,
    UserUIPreference, VerificationToken)
from backend.models_ops import SocialChannel  # noqa: F401
from backend.models_ops import ChurchLocation, SystemVariable  # noqa: F401
# Projects
from backend.models_projects import ProjectActivityLog  # noqa: F401
from backend.models_projects import (  # noqa: F401
    Project, ProjectAttachment, ProjectComment, ProjectDocument,
    ProjectInboxState, ProjectMilestone, ProjectPhase, ProjectTask,
    ProjectWhiteboard, TaskSupply)

# Agent identity models (canonical person)
from backend.models_agents import (  # noqa: F401
    Agent, AgentAuth, AgentContact, AgentRole,
    AgentActivity, AgentFamily, AgentJourney, AgentPermission, AgentTask,
    AgentInsight)

# Evangelismo — Schema canónico definitivo
from backend.models_evangelism import (  # noqa: F401
    RolEnGrupoEnum, EstadoAsistenciaEnum, TipoSeguimientoEnum,
    FrecuenciaEnum, EstadoSesionEnum,
    Sede, LogAuditoria, CategoriaEstrategia, MotivoExcusa,
    EstrategiaEvangelismo, RolPersonalizadoEstrategia, GrupoEvangelismo,
    ParticipanteGrupo, SesionGrupo, Asistencia, RegistroSeguimiento,
    HistorialEmbudo,
)

# Kernel — Protocolo de Identidad y Roles
from backend.models_kernel import (  # noqa: F401
    ActivityStatus, MinistryOffice, ChurchRole, PlatformRole,
    PersonaMinistry, PersonaRoleAssignment, PersonaRoleHistory,
    PlatformRoleDefinition, PersonaPlatformRole,
    UserMinistry, UserRoleAssignment, UserRoleHistory, UserPlatformRole)

# Knowledge Base
from backend.services.knowledge_base import AgentKnowledgeBase  # noqa: F401

# Conversation Memory
from backend.services.conversation_memory import (  # noqa: F401
    AgentConversation, AgentMessage,
)
