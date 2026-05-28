# Identity & auth
# Academy / LMS (CellGroup models still used by evangelism)
from backend.models_academy import (  # noqa: F401
    CellGroup, CellGroupAttendance, CellGroupMember, CellGroupSession, Family)


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
    ColombianCity, ColombianDepartment,
    CommunicationLog, CommunityBoardCard,
    Conversation, ConversationParticipant,
    CounselingTicket, CrmTask, Donation, DonationCategory, EventAssignment,
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
# Projects (nuevo diseño)
from backend.models_proyectos import (  # noqa: F401
    ComentarioTarea, DependenciaTarea, DocumentoProyecto,
    EquipoProyecto, Proyecto, TareaProyecto)

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

# CRM Core 2.0 — Pipeline, Casos, Interacciones
from backend.models_crm_core import (  # noqa: F401
    CasoCRM, EtapaPipeline, InteraccionCRM, PipelineCRM,
    PlantillaMensaje, TareaCRM,
)

# Agenda — Calendario Unificado, Recursos, Participantes
from backend.models_agenda import (  # noqa: F401
    EventoAgenda, ParticipanteEvento, RecursoFisico, ReservaRecurso,
)

# Academy 2.0 — Catálogo, Evaluaciones, Matrícula, Certificaciones
from backend.models_academy_core import (  # noqa: F401
    ActaEntrada, ActaFormal, AsistenciaClase, Certificado,
    ComentarioForo, Curso as AcademyCurso, EntregaTarea, Evaluacion,
    HiloForo, IntentoEvaluacion, Leccion as AcademyLeccion, Matricula,
    Opcion, Pregunta, PrerrequisitoCurso, ProgresoLeccion,
)
