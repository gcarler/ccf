# Identity & auth
# Academy / LMS
from backend.models_academy import AcademyActivityLog  # noqa: F401
from backend.models_academy import (Assessment, AssessmentAttempt,
                                    AssessmentOption, AssessmentQuestion,
                                    AssignmentSubmission, Certificate, Course,
                                    CourseAttendance, CoursePrerequisite,
                                    Enrollment, Family, FaroSeason, FormalActa,
                                    ForumComment, ForumThread, GloryHouse,
                                    GloryHouseAttendance, GloryHouseMember,
                                    GloryHouseSession, Lesson, LessonProgress,
                                    Resource)

# Assets / Agents / Governance / Ops
from backend.models_assets import (AssetItem, InventoryItem,  # noqa: F401
                                   MaintenanceLog)
# CMS
from backend.models_cms import CmsMediaItem  # noqa: F401
from backend.models_cms import (Announcement, CmsMenu, CmsMenuItem, CmsPage,
                                CmsPageVersion, CmsPublishLog, CmsSection,
                                CmsSite, CmsTheme, ContentMetric,
                                ContentPublication, MediaAsset,
                                NewsletterSubscription, PageContent,
                                PageContentVersion, Testimonial)
# CRM / Pastoral
from backend.models_crm import ChatMessage  # noqa: F401
from backend.models_crm import (AgendaEvent, ColombianCity,
                                ColombianDepartment,
                                CommunicationLog, CommunityBoardCard,
                                ConsolidationAssignment, ConsolidationCase,
                                ConsolidationFollowUpTask,
                                ConsolidationInteraction,
                                ConsolidationPipeline, CounselingTicket,
                                CrmAutomation, CrmEvent, CrmTask, Donation,
                                DonationCategory, EventAssignment,
                                EventAttendance, EvangelismStrategy, Fund, Member,
                                MemberMinistry, MemberPosition,
                                MemberRole, Ministry,
                                PastoralCallLog, Position, PrayerRequest,
                                RoleDefinition, SpiritualMilestone,
                                SupportTicket, VolunteerShift, VolunteerSkill,
                                member_volunteer_skills)
from backend.models_governance import (AdminAuditLog,  # noqa: F401
                                       AutomationRule)
from backend.models_identity import Notification  # noqa: F401
from backend.models_identity import (Badge, Level, RefreshToken, ResetToken,
                                     Role, User, UserBadge, UserReminder,
                                     UserUIPreference, VerificationToken)
from backend.models_ops import SocialChannel  # noqa: F401
from backend.models_ops import ChurchLocation, SystemVariable
# Projects
from backend.models_projects import ProjectActivityLog  # noqa: F401
from backend.models_projects import (Project, ProjectAttachment,
                                     ProjectComment, ProjectDocument,
                                     ProjectInboxState, ProjectMilestone,
                                     ProjectPhase, ProjectTask,
                                     ProjectWhiteboard, TaskSupply)

# Agent identity models (canonical person)
from backend.models_agents import (Agent, AgentAuth, AgentContact, AgentRole,
    AgentActivity, AgentFamily, AgentJourney, AgentPermission, AgentTask,
    AgentInsight)

# Kernel — Protocolo de Identidad y Roles
from backend.models_kernel import (ActivityStatus, MinistryOffice, ChurchRole,
    PlatformRole)  # noqa: F401
from backend.models_kernel import (UserMinistry, UserRoleAssignment,
    UserRoleHistory, PlatformRoleDefinition, UserPlatformRole)  # noqa: F401

# Knowledge Base
from backend.services.knowledge_base import AgentKnowledgeBase  # noqa: F401

# Conversation Memory
from backend.services.conversation_memory import (  # noqa: F401
    AgentConversation, AgentMessage,
)
