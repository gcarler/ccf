# flake8: noqa: F401
# Barrel re-export file — all imports intentionally unused here

# Identity & auth
# CMS
from backend.models_cms import CmsMediaItem  # noqa: F401
from backend.models_cms import (  # noqa: F401
    Announcement, CmsMenu, CmsMenuItem, CmsPage, CmsPageView,
    CmsPageVersion, CmsPublishLog, CmsSection,
    CmsSite, CmsTheme, ContentMetric,
    ContentPublication, MediaAsset,
    PageContent,
    PageContentVersion, SavedView, Testimonial)
# CRM / Pastoral
from backend.models_crm import (
    ChatMessage,
    CrmAutomation, CrmEvent,
    ColombianDepartment,
    CommunicationLog, CommunityBoardCard,
    Conversation, ConversationParticipant, Family,
    CounselingTicket, Donation, DonationCategory, EventAssignment,
    EventAttendance, Fund, PersonaMinistryAssignment,
    PersonaPosition, PersonaRoleLink, Ministry, Position,
    Persona, PrayerRequest, RoleDefinition, SpiritualMilestone, SupportTicket,
    VolunteerShift, VolunteerSkill, persona_volunteer_skills)

# Projects (canonical)
from backend.models_projects import (
    Project, ProjectActivityLog, ProjectAttachment, ProjectComment,
    ProjectDocument, ProjectInboxState, ProjectMilestone, ProjectPhase,
    ProjectTask, ProjectWhiteboard, TaskSupply)

# Agent identity models (canonical person)
from backend.models_agents import (
    Agent, AgentActivity, AgentAuth, AgentContact, AgentFamily,
    AgentInsight, AgentJourney, AgentPermission, AgentRole, AgentTask)

# Governance / Identity / Ops
from backend.models_governance import AdminAuditLog, AutomationRule
from backend.models_identity import Notification, User
from backend.models_identity import (
    Badge, Level, RefreshToken, ResetToken, Role, UserBadge,
    UserReminder, UserUIPreference, VerificationToken)
from backend.models_ops import ChurchLocation, SocialChannel, SystemVariable

# Evangelismo — Schema canónico definitivo
from backend.models_evangelism import (
    RolEnGrupoEnum, EstadoAsistenciaEnum, TipoSeguimientoEnum,
    FrecuenciaEnum, EstadoSesionEnum,
    Sede, CampaignSeason, CategoriaEstrategia, LogAuditoria, MotivoExcusa,
    EstrategiaEvangelismo, RolPersonalizadoEstrategia,
    GrupoEvangelismo, ParticipanteGrupo, SesionGrupo, Asistencia,
    RegistroSeguimiento, HistorialEmbudo,
    )

# Kernel — Identity, Permissions & Multi-agent Contracts
from backend.models_kernel import (  # noqa: F401
    ActivityStatus, MinistryOffice, ChurchRole,
    PersonaMinistry, PersonaRoleAssignment, PersonaRoleHistory)

# Auth v3 — RBAC, MFA, forensics, and gamification
from backend.models_auth import (
    HistorialContrasena, LogSeguridad, Medalla, MedallaUsuario,
    NivelGamificado, NotificacionUsuario, PreferenciaUI,
    RecordatorioUsuario, RolPlataforma, TokenResetContrasena,
    TokenSesion, TokenVerificacionEmail, Usuario, UsuarioRolModulo)

# Agenda — Calendario Unificado, Recursos, Participantes
from backend.models_agenda import (
    EventoAgenda, ParticipanteEvento, RecursoFisico, ReservaRecurso,
)

# Academy — single canonical model tree
from backend.models_academy_core import (
    AcademyActivityLog, Assessment, AssessmentAnswer, AssessmentAttempt,
    AssessmentOption, AssessmentQuestion, AssignmentSubmission, Certificate,
    Course, CourseAttendance, CoursePrerequisite, Enrollment, FormalActa,
    FormalActaEntry, ForumComment, ForumThread, Lesson, LessonProgress, Resource,
)

# CRM pipeline, cases, interactions and follow-up tasks
from backend.models_crm_pipeline import (
    CasoCRM, EtapaPipeline, InteraccionCRM, PipelineCRM, TareaCRM,
)

# Biblioteca de Recursos CRM — PlantillaMensaje vive aquí (versión normalizada)
from backend.models_crm import (  # noqa: F401
    CanalEnvio, CategoriaRecurso, EstadoEnvioPlantilla,
    BitacoraEnvioPlantilla, PlantillaMensaje, RecursoAdjunto,
)

# Conversation Memory
from backend.models_conversation import AgentConversation, AgentMessage

# Knowledge Base
from backend.models_knowledge_base import AgentKnowledgeBase

# Enterprise CMS — Audit Trail, Permissions, Notifications, Webhooks, Custom Types, Search, Sessions
from backend.models_enterprise import (  # noqa: F401
    AuditLog, ContentPermission, CmsNotification, Webhook, WebhookDelivery,
    CmsCustomType, CmsCustomEntry, CmsCustomEntryVersion, CmsGlossaryTerm,
    SearchIndex, SearchPromotion, UserSession, MediaFolder,
    MediaFileVersion, CmsRedirect, BrokenLinkCheck,
)
