# flake8: noqa: F401
# Barrel re-export file — all imports intentionally unused here

# Identity & auth
# CMS
# Academy — single canonical model tree
from backend.models_academy_core import (
    AcademyActivityLog,
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentOption,
    AssessmentQuestion,
    AssignmentSubmission,
    Certificate,
    Course,
    CourseAttendance,
    CoursePrerequisite,
    Enrollment,
    FormalActa,
    FormalActaEntry,
    ForumComment,
    ForumThread,
    Lesson,
    LessonProgress,
    Resource,
)

# Agenda — Calendario Unificado, Recursos, Participantes
from backend.models_agenda import (
    EventoAgenda,
    ParticipanteEvento,
    RecursoFisico,
    ReservaRecurso,
)

# Agent identity models (canonical person)
from backend.models_agents import (
    Agent,
    AgentActivity,
    AgentAuth,
    AgentContact,
    AgentFamily,
    AgentInsight,
    AgentJourney,
    AgentPermission,
    AgentRole,
    AgentTask,
)

# Auth v3 — RBAC, MFA, forensics, and gamification
from backend.models_auth import (
    HistorialContrasena,
    LogSeguridad,
    Medalla,
    MedallaUsuario,
    NivelGamificado,
    NotificacionUsuario,
    PreferenciaUI,
    RecordatorioUsuario,
    RolPlataforma,
    TokenResetContrasena,
    TokenSesion,
    TokenVerificacionEmail,
    Usuario,
    UsuarioRolModulo,
)
from backend.models_cms import (  # noqa: F401
    Announcement,
    CmsCategory,
    CmsMediaItem,  # noqa: F401
    CmsMenu,
    CmsMenuItem,
    CmsPage,
    CmsPageVersion,
    CmsPageView,
    CmsPost,
    CmsPostCategory,
    CmsPostTag,
    CmsPublishLog,
    CmsSection,
    CmsSectionType,
    CmsSeoSnapshot,
    CmsSite,
    CmsTag,
    CmsTheme,
    SavedView,
    Testimonial,
)

# Conversation Memory
from backend.models_conversation import AgentConversation, AgentMessage

# CRM / Pastoral
# Biblioteca de Recursos CRM — PlantillaMensaje vive aquí (versión normalizada)
from backend.models_crm import (  # noqa: F401
    BitacoraEnvioPlantilla,
    CanalEnvio,
    CategoriaRecurso,
    ChatMessage,
    ColombianDepartment,
    CommunicationLog,
    CommunityBoardCard,
    Conversation,
    ConversationParticipant,
    CounselingTicket,
    CrmAutomation,
    CrmAutomationEdge,
    CrmAutomationFlow,
    CrmAutomationNode,
    CrmEvent,
    CrmFlowBranch,
    CrmFlowCanvasConfig,
    CrmFlowCycleCache,
    Donation,
    DonationCategory,
    EstadoEnvioPlantilla,
    EventAssignment,
    EventAttendance,
    Family,
    Fund,
    Ministry,
    PendingCrmAction,
    Persona,
    PersonaMentorship,
    PersonaMinistryAssignment,
    PersonaPosition,
    PersonaRoleLink,
    PlantillaMensaje,
    Position,
    PrayerRequest,
    RecursoAdjunto,
    RoleDefinition,
    SpiritualMilestone,
    SupportTicket,
    VolunteerShift,
    VolunteerSkill,
    persona_volunteer_skills,
)

# CRM pipeline, cases, interactions and follow-up tasks
from backend.models_crm_pipeline import (
    CasoCRM,
    CrmDragDropEvent,
    CrmReorderLock,
    EtapaPipeline,
    InteraccionCRM,
    PipelineCRM,
    TareaCRM,
)

# Enterprise CMS — Audit Trail, Permissions, Notifications, Webhooks, Custom Types, Search, Sessions
from backend.models_enterprise import (  # noqa: F401
    AuditLog,
    BrokenLinkCheck,
    CmsCustomEntry,
    CmsCustomEntryVersion,
    CmsCustomType,
    CmsGlossaryTerm,
    CmsNotification,
    CmsRedirect,
    ContentPermission,
    MediaFileVersion,
    MediaFolder,
    SearchIndex,
    SearchPromotion,
    UserSession,
    Webhook,
    WebhookDelivery,
)

# Evangelismo — Schema canónico definitivo
from backend.models_evangelism import (
    Asistencia,
    CampaignSeason,
    CategoriaEstrategia,
    EstadoAsistenciaEnum,
    EstadoSesionEnum,
    EstrategiaEvangelismo,
    FrecuenciaEnum,
    GrupoEvangelismo,
    HistorialEmbudo,
    LogAuditoria,
    MotivoExcusa,
    ParticipanteGrupo,
    RegistroSeguimiento,
    RolEnGrupoEnum,
    RolPersonalizadoEstrategia,
    Sede,
    SesionGrupo,
    TipoSeguimientoEnum,
)

# Finance Suite — Contabilidad, Facturación, Gastos, Documentos, Firma
from backend.models_finance_suite import (
    AccountingEntry,
    AccountingEntryLine,
    BankAccount,
    BankReconciliation,
    BankTransaction,
    ChartOfAccount,
    Document,
    DocumentTag,
    DocumentTagLink,
    ExpenseItem,
    ExpenseReceipt,
    ExpenseReport,
    FinancialStatement,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    ReconciliationLine,
    SalesOrder,
    SalesOrderItem,
    SignRequest,
    SignSigner,
    TaxConfiguration,
)

# Governance / Identity / Ops
from backend.models_governance import AdminAuditLog, AutomationRule
from backend.models_identity import (
    Badge,
    Level,
    Notification,
    RefreshToken,
    ResetToken,
    Role,
    User,
    UserBadge,
    UserReminder,
    UserUIPreference,
    VerificationToken,
)

# Kernel — Identity, Permissions & Multi-agent Contracts
from backend.models_kernel import (  # noqa: F401
    ActivityStatus,
    ChurchRole,
    MinistryOffice,
    PersonaMinistry,
    PersonaRoleAssignment,
    PersonaRoleHistory,
)

# Knowledge Base
from backend.models_knowledge_base import AgentKnowledgeBase
from backend.models_ops import ChurchLocation, SocialChannel, SystemVariable

# Projects (canonical)
from backend.models_projects import (
    Project,
    ProjectActivityLog,
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
from backend.models_wiki import WikiPage  # noqa: F401
