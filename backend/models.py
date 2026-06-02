# flake8: noqa: F401
# Barrel re-export file — all imports intentionally unused here

# Identity & auth
# Academy / LMS (legacy — Course, Enrollment, Lesson still in use via api/academy.py)
from backend.models_academy import (
    AcademyActivityLog, Assessment, AssessmentAttempt, AssessmentOption,
    AssessmentQuestion, AssignmentSubmission, CampaignSeason, CellGroup,
    Certificate, Course, CourseAttendance, CoursePrerequisite, Enrollment,
    Family, FormalActa, ForumComment, ForumThread, Lesson, LessonProgress,
    Resource)
# CMS
from backend.models_cms import CmsMediaItem  # noqa: F401
from backend.models_cms import (  # noqa: F401
    Announcement, CmsMenu, CmsMenuItem, CmsPage,
    CmsPageVersion, CmsPublishLog, CmsSection,
    CmsSite, CmsTheme, ContentMetric,
    ContentPublication, MediaAsset,
    PageContent,
    PageContentVersion, Testimonial)
# Personas (reemplaza Persona — UUID PK)
from backend.models_personas import Persona
Member = Persona  # Backward compatibility alias for legacy tests and CRUDs
FaroSeason = CampaignSeason  # Backward compatibility alias for FaroSeason


# CRM / Pastoral
from backend.models_crm import (
    AgendaEvent, ChatMessage, ConsolidationAssignment,
    ConsolidationCase, ConsolidationInteraction, ConsolidationTask,  # legacy (use CasoCRM from models_crm_core)
    CrmAutomation, CrmEvent,
    ColombianDepartment,
    CommunicationLog, CommunityBoardCard,
    Conversation, ConversationParticipant,
    CounselingTicket, CrmTask, Donation, DonationCategory, EventAssignment,
    EventAttendance, EvangelismStrategy, Fund, MemberMinistry,
    MemberPosition, MemberRole, Ministry, PastoralCallLog, Position,
    PrayerRequest, RoleDefinition, SpiritualMilestone, SupportTicket,
    VolunteerShift, VolunteerSkill, member_volunteer_skills)

# Projects (legacy English design — used by crud/projects.py)
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
    Sede, CategoriaEstrategia, LogAuditoria, MotivoExcusa,
    EstrategiaEvangelismo, RolPersonalizadoEstrategia,
    GrupoEvangelismo, ParticipanteGrupo, SesionGrupo, Asistencia,
    RegistroSeguimiento, HistorialEmbudo,
    )

# Kernel — Identity, Permissions & Multi-agent Contracts
from backend.models_kernel import (  # noqa: F401
    ActivityStatus, MinistryOffice, ChurchRole, PlatformRole,
    PersonaMinistry, PersonaRoleAssignment, PersonaRoleHistory,
    PlatformRoleDefinition, PersonaPlatformRole)

# Auth 2.0 — RBAC, MFA, Forensics, Gamification
from backend.models_auth import (
    HistorialContrasena, LogSeguridad, Medalla, MedallaUsuario,
    NivelGamificado, NotificacionUsuario, PreferenciaUI,
    RecordatorioUsuario, RolPlataforma, TokenResetContrasena,
    TokenSesion, TokenVerificacionEmail, Usuario, UsuarioRolModulo)

# Project v2 — WBS, Critical Path & Digital Twins
from backend.models_proyectos import (
    ComentarioTarea, DependenciaTarea, DocumentoProyecto,
    EquipoProyecto, Proyecto, TareaProyecto)

# Agenda — Calendario Unificado, Recursos, Participantes
from backend.models_agenda import (
    EventoAgenda, ParticipanteEvento, RecursoFisico, ReservaRecurso,
)

# Academy 2.0 — Catálogo, Evaluaciones, Matrícula, Certificaciones
from backend.models_academy_core import (
    ActaEntrada, ActaFormal, AsistenciaClase, Certificado,
    ComentarioForo, Curso as AcademyCurso, EntregaTarea, Evaluacion,
    HiloForo, IntentoEvaluacion, Leccion as AcademyLeccion, Matricula,
    Opcion, Pregunta, PrerrequisitoCurso, ProgresoLeccion,
)

# CRM Core 2.0 — Pipeline, Casos, Interacciones
from backend.models_crm_core import (
    CasoCRM, EtapaPipeline, InteraccionCRM, PipelineCRM,
    PlantillaMensaje, TareaCRM,
)

# Conversation Memory
from backend.services.conversation_memory import (
    AgentConversation, AgentMessage,
)

# Knowledge Base
from backend.services.knowledge_base import AgentKnowledgeBase



CellGroup = GrupoEvangelismo
CellGroupMember = ParticipanteGrupo
CellGroupSession = SesionGrupo
CellGroupAttendance = Asistencia

