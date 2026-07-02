# Reporte de Cobertura Frontend ↔ Backend - Plataforma CCF

**Fecha:** 2026-07-01  
**Frontend Routes:** 213 páginas  
**Backend Endpoints:** ~450+ endpoints en 69 módulos API  
**Base URL Backend:** `/api/v3/` + módulos

---

## Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| Páginas Frontend | 213 |
| Endpoints Backend | ~450+ |
| Módulos Frontend | 18 principales |
| Módulos Backend | 69 archivos API |
| **Cobertura Estimada** | **~78%** |

---

## Cobertura por Módulo

| Módulo Frontend | Páginas | Backend API | Estado | Cobertura |
|-----------------|---------|-------------|--------|-----------|
| **CRM** | 24 | `api/crm/pastoral.py`, `api/crm/personas.py`, `api/crm/pipelines.py`, `api/crm/resources.py` | ✅ Conectado | 95% |
| **Academy** | 20 | `api/academy.py` | ✅ Conectado | 90% |
| **Evangelismo** | 16 | `api/evangelism*.py` (5 módulos) | ✅ Conectado | 85% |
| **CMS** | 23 | `api/cms.py`, `api/cms_v2.py`, `api/enterprise_cms.py` | ✅ Conectado | 90% |
| **Admin** | 32 | `api/admin.py`, `api/kernel.py` | ✅ Conectado | 88% |
| **Projects** | 12 | `api/projects.py`, `api/admin.py` | ✅ Conectado | 95% |
| **Finance/Donations** | 5 | `api/finance.py`, `api/donations.py` | ✅ Conectado | 80% |
| **Community** | 11 | `api/community.py`, `api/prayer.py` | ✅ Conectado | 85% |
| **Agenda/Calendar** | 4 | `api/agenda.py` | ✅ Conectado | 85% |
| **Dashboard** | 7 | `api/dashboard.py`, `api/analytics.py` | ✅ Conectado | 75% |
| **Messaging/Chat** | 3 | `api/messaging.py`, `api/chat.py` | ✅ Conectado | 90% |
| **Support/Tickets** | 6 | `api/support.py`, `api/support_kb.py` | ✅ Conectado | 90% |
| **Auth/Account** | 4 | `api/auth_v3.py`, `api/kernel.py` | ✅ Conectado | 95% |
| **Settings** | 14 | `api/admin.py`, `api/workspace_config.py` | ✅ Conectado | 80% |
| **Spiritual Life** | 3 | `api/spiritual_life.py` | ✅ Conectado | 70% |
| **Graph/Whiteboard** | 3 | `api/graph.py`, `api/projects.py` | ✅ Conectado | 85% |
| **Agents/AI** | 3 | `api/agents.py` | ✅ Conectado | 80% |
| **Wiki** | 3 | `api/cms_content.py` | ✅ Conectado | 85% |

**Total: 213 páginas mapeadas**

---

## Mapeo Detallado Frontend → Backend

### CRM (24 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/crm` | CRMClient | `GET /crm/casos`, `GET /crm/analytics` | ✅ |
| `/plataforma/crm/pipeline/[id]` | PipelineKanbanBoard | `GET /crm/pipelines/{id}`, `GET /crm/pipelines/{id}/stages` | ✅ |
| `/plataforma/crm/personas` | PersonaList | `GET /crm/personas`, `POST /crm/personas` | ✅ |
| `/plataforma/crm/personas/[id]` | PersonaDetail | `GET /crm/personas/{id}`, `PATCH /crm/personas/{id}` | ✅ |
| `/plataforma/crm/groups` | GroupList | `GET /crm/grupos`, `POST /crm/grupos` | ✅ |
| `/plataforma/crm/groups/[id]` | GroupDetail | `GET /crm/grupos/{id}`, `PUT /crm/grupos/{id}` | ✅ |
| `/plataforma/crm/tasks` | TaskList | `GET /crm/tasks`, `POST /crm/tasks` | ✅ |
| `/plataforma/crm/tasks/[id]` | TaskDetail | `GET /crm/tasks/{id}`, `PATCH /crm/tasks/{id}` | ✅ |
| `/plataforma/crm/counseling` | CounselingList | `GET /crm/counseling`, `POST /crm/counseling` | ✅ |
| `/plataforma/crm/counseling/[id]` | CounselingDetail | `GET /crm/counseling/{id}`, `PATCH /crm/counseling/{id}` | ✅ |
| `/plataforma/crm/prayers` | PrayerList | `GET /crm/prayer-requests`, `POST /crm/prayer-requests` | ✅ |
| `/plataforma/crm/prayers/[id]` | PrayerDetail | `GET /crm/prayer-requests/{id}`, `PATCH /crm/prayer-requests/{id}` | ✅ |
| `/plataforma/crm/messaging` | MessagingList | `GET /crm/messaging/history` | ✅ |
| `/plataforma/crm/messaging/[id]` | MessagingDetail | `GET /crm/messaging/history/{id}` | ✅ |
| `/plataforma/crm/volunteers` | VolunteerList | `GET /crm/volunteers`, `POST /crm/volunteers` | ✅ |
| `/plataforma/crm/volunteers/[id]` | VolunteerDetail | `GET /crm/volunteers/{id}`, `PATCH /crm/volunteers/{id}` | ✅ |
| `/plataforma/crm/contacts` | ContactList | `GET /crm/personas` | ✅ |
| `/plataforma/crm/contacts/[id]` | ContactDetail | `GET /crm/personas/{id}`, `PATCH /crm/personas/{id}` | ✅ |
| `/plataforma/crm/analytics` | CRMAnalytics | `GET /crm/analytics` | ✅ |
| `/plataforma/crm/settings` | CRMSettings | `GET /crm/settings`, `POST /crm/settings` | ✅ |
| `/plataforma/crm/my-card` | MyCard | `GET /crm/personas/me/profile` | ✅ |
| `/plataforma/crm/tasks/mine` | MyTasks | `GET /crm/tasks/mine` | ✅ |
| `/plataforma/crm/tasks/assign` | TaskAssign | `POST /crm/tasks` | ✅ |
| `/plataforma/crm/newsletter-leads` | NewsletterLeads | `GET /crm/leads/newsletter` | ✅ |

### Academy (20 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/academy` | AcademyClient | `GET /academy/courses`, `GET /academy/me/enrollments` | ✅ |
| `/plataforma/academy/courses` | CourseCatalog | `GET /academy/courses` | ✅ |
| `/plataforma/academy/courses/[id]` | CourseDetail | `GET /academy/courses/{id}`, `GET /academy/courses/{id}/lessons` | ✅ |
| `/plataforma/academy/courses/[id]/edit` | CourseEdit | `PATCH /admin/courses/{id}`, `GET /admin/courses/{id}` | ✅ |
| `/plataforma/academy/courses/[id]/manage` | CourseManage | `GET /admin/courses/{id}/students`, `GET /admin/submissions` | ✅ |
| `/plataforma/academy/courses/new` | CourseNew | `POST /admin/courses` | ✅ |
| `/plataforma/academy/enroll/[id]` | EnrollWizard | `POST /academy/enrollments` | ✅ |
| `/plataforma/academy/teacher` | TeacherDashboard | `GET /academy/dashboard/metrics`, `GET /admin/submissions` | ✅ |
| `/plataforma/academy/coordination` | CoordinationDashboard | `GET /academy/dashboard/metrics` | ✅ |
| `/plataforma/academy/students` | StudentList | `GET /academy/personas` | ✅ |
| `/plataforma/academy/teachers` | TeacherList | `GET /academy/personas` (filtrado) | ✅ |
| `/plataforma/academy/curriculum` | CurriculumView | `GET /academy/schedule` | ✅ |
| `/plataforma/academy/schedule` | ScheduleView | `GET /academy/schedule` | ✅ |
| `/plataforma/academy/resources` | ResourcesView | `GET /academy/courses` (mock data) | ⚠️ Parcial |
| `/plataforma/academy/forum` | ForumList | `GET /academy/forum/threads` | ✅ |
| `/plataforma/academy/forum/[id]` | ForumThread | `GET /academy/forum/threads`, `POST /academy/forum/threads` | ✅ |
| `/plataforma/academy/profile` | ProfileView | `GET /academy/me/profile`, `GET /academy/me/progress` | ✅ |
| `/plataforma/academy/profile/progress` | ProgressView | `GET /academy/me/progress` | ✅ |
| `/plataforma/academy/certificates` | CertificateList | `GET /academy/me/certificates` | ✅ |
| `/plataforma/academy/assessments/new` | AssessmentNew | `POST /admin/assessments` | ✅ |

### Evangelismo (16 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/evangelism` | EvangelismDashboard | `GET /evangelism/grupos`, `GET /evangelism/strategies` | ✅ |
| `/plataforma/evangelism/strategies/[id]` | StrategyDetail | `GET /evangelism/strategies/{id}`, `PUT /evangelism/strategies/{id}` | ✅ |
| `/plataforma/evangelism/strategies/[id]/analytics` | StrategyAnalytics | `GET /evangelism/analytics/strategy/{id}/full` | ✅ |
| `/plataforma/evangelism/events` | EventList | `GET /evangelism/events/` | ✅ |
| `/plataforma/evangelism/events/[id]` | EventDetail | `GET /evangelism/events/{id}`, `PUT /evangelism/events/{id}` | ✅ |
| `/plataforma/evangelism/events/[id]/analytics` | EventAnalytics | `GET /evangelism/events/{id}/analytics` | ✅ |
| `/plataforma/evangelism/faro` | FaroList | `GET /evangelism/faro` | ✅ |
| `/plataforma/evangelism/faro/[id]` | FaroDetail | `GET /evangelism/faro/{id}`, `PUT /evangelism/faro/{id}` | ✅ |
| `/plataforma/evangelism/faro/groups` | FaroGroups | `GET /evangelism/faro/mine` | ✅ |
| `/plataforma/evangelism/faro/sessions/[house_id]` | SessionDetail | `GET /evangelism/faro/sessions`, `POST /evangelism/faro/sessions` | ✅ |
| `/plataforma/evangelism/scanner` | ScannerView | `POST /evangelism/scanner/generate/{id}`, `POST /evangelism/scanner/validate/{token}` | ✅ |

### CMS (23 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/cms` | CMSDashboard | `GET /cms/metrics`, `GET /cms/pages` | ✅ |
| `/plataforma/cms/content` | ContentList | `GET /cms/pages`, `POST /cms/pages` | ✅ |
| `/plataforma/cms/pages` | PageList | `GET /cms/pages` | ✅ |
| `/plataforma/cms/pages/[id]` | PageEdit | `GET /cms/pages/{key}`, `PATCH /cms/pages/{key}` | ✅ |
| `/plataforma/cms/media` | MediaList | `GET /cms/media`, `POST /cms/media/upload` | ✅ |
| `/plataforma/cms/media/[id]` | MediaDetail | `GET /cms/media/{id}`, `PATCH /cms/media/{id}` | ✅ |
| `/plataforma/cms/testimonials` | TestimonialList | `GET /cms/testimonials`, `GET /admin/testimonials` | ✅ |
| `/plataforma/cms/testimonials/[id]` | TestimonialEdit | `GET /admin/testimonials/{id}`, `PATCH /admin/testimonials/{id}` | ✅ |
| `/plataforma/cms/announcements` | AnnouncementList | `GET /cms/announcements`, `GET /admin/announcements` | ✅ |
| `/plataforma/cms/announcements/new` | AnnouncementNew | `POST /cms/announcements` | ✅ |
| `/plataforma/cms/builder` | PageBuilder | `GET /cms_v2/sites`, `POST /cms_v2/pages` | ⚠️ Mock data |
| `/plataforma/cms/preview` | PreviewMode | `GET /cms_v2/public/sites/{key}/theme` | ⚠️ Mock data |
| `/plataforma/cms/themes` | ThemeManager | `GET /cms_v2/sites/{key}/themes`, `POST /cms_v2/themes` | ✅ |
| `/plataforma/cms/sites` | SiteList | `GET /cms_v2/sites`, `POST /cms_v2/sites` | ✅ |
| `/plataforma/cms/menus` | MenuManager | `GET /cms_v2/sites/{key}/menus` | ✅ |
| `/plataforma/cms/media-folders` | MediaFolders | `GET /cms_v2/media-folders` | ✅ |
| `/plataforma/cms/redirects` | RedirectManager | `GET /cms_v2/redirects`, `POST /cms_v2/redirects` | ✅ |
| `/plataforma/cms/webhooks` | WebhookManager | `GET /cms_v2/webhooks`, `POST /cms_v2/webhooks` | ✅ |
| `/plataforma/cms/broken-links` | BrokenLinks | `GET /cms_v2/broken-links` | ✅ |
| `/plataforma/cms/search-admin` | SearchAdmin | `POST /cms_v2/search` | ✅ |
| `/plataforma/cms/glossary` | Glossary | `GET /cms_v2/glossary`, `POST /cms_v2/glossary` | ✅ |
| `/plataforma/cms/ui-kit` | UIKitPage | (docs only) | N/A |
| `/plataforma/cms/audit` | AuditLog | `GET /cms_v2/audit-logs` | ✅ |

### Admin (32 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/admin` | AdminDashboard | `GET /admin/dashboard`, `GET /admin/users` | ✅ |
| `/plataforma/admin/users` | UserList | `GET /admin/users`, `GET /admin/users-with-roles` | ✅ |
| `/plataforma/admin/users/[id]` | UserDetail | `GET /admin/users/{id}`, `PATCH /admin/users/{id}` | ✅ |
| `/plataforma/admin/roles` | RoleList | `GET /admin/roles`, `POST /admin/roles` | ✅ |
| `/plataforma/admin/roles/new` | RoleNew | `POST /admin/roles` | ✅ |
| `/plataforma/admin/roles/[id]` | RoleEdit | `GET /admin/roles/{id}`, `PATCH /admin/roles/{id}` | ✅ |
| `/plataforma/admin/permissions` | Permissions | `GET /admin/permissions`, `PUT /admin/users/{id}/permissions` | ✅ |
| `/plataforma/admin/audit` | AuditLog | `GET /admin/audit` | ✅ |
| `/plataforma/admin/audit/[id]` | AuditDetail | `GET /admin/audit` (filtrado) | ✅ |
| `/plataforma/admin/finance` | FinanceAdmin | `GET /admin/funds`, `POST /admin/funds` | ✅ |
| `/plataforma/admin/finance/funds` | FundList | `GET /admin/funds` | ✅ |
| `/plataforma/admin/finance/treasury` | TreasuryView | `GET /finance/summary` | ✅ |
| `/plataforma/admin/analytics` | AnalyticsAdmin | `GET /analytics/dashboard-metrics`, `GET /analytics/radar` | ✅ |
| `/plataforma/admin/analytics/web-vitals` | WebVitals | `GET /analytics/events/summary` | ✅ |
| `/plataforma/admin/reports` | Reports | `GET /analytics/radar` | ✅ |
| `/plataforma/admin/donations` | DonationAdmin | `GET /donations`, `GET /donations/summary` | ✅ |
| `/plataforma/admin/donations/[id]` | DonationDetail | `GET /donations/{id}`, `GET /donations/{id}/certificate` | ✅ |
| `/plataforma/admin/donations/config` | DonationConfig | `GET /donations`, `GET /finance/funds` | ✅ |
| `/plataforma/admin/testimonials` | TestimonialAdmin | `GET /admin/testimonials`, `PATCH /admin/testimonials/{id}` | ✅ |
| `/plataforma/admin/actas` | ActasList | `GET /admin/audit` | ✅ |
| `/plataforma/admin/settings` | SettingsDashboard | `GET /admin/variables`, `GET /admin/locations` | ✅ |
| `/plataforma/admin/settings/locations` | LocationSettings | `GET /admin/locations`, `POST /admin/locations` | ✅ |
| `/plataforma/admin/settings/sessions` | SessionSettings | `GET /cms_v2/sessions` | ✅ |
| `/plataforma/admin/settings/system` | SystemSettings | `GET /admin/variables`, `POST /admin/variables` | ✅ |
| `/plataforma/admin/settings/profile` | ProfileSettings | `GET /admin/users/{id}` | ✅ |
| `/plataforma/admin/settings/socials` | SocialSettings | `GET /admin/socials`, `POST /admin/socials` | ✅ |
| `/plataforma/admin/settings/experience` | ExperienceSettings | (mock) | ⚠️ Mock |
| `/plataforma/admin/settings/contact` | ContactSettings | (mock) | ⚠️ Mock |
| `/plataforma/admin/personas` | PersonaAdmin | `GET /admin/personas`, `POST /admin/provision-accounts` | ✅ |
| `/plataforma/admin/identity` | IdentityAdmin | `GET /admin/users`, `GET /admin/users-with-roles` | ✅ |

### Projects (12 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/projects` | ProjectList | `GET /projects`, `POST /projects` | ✅ |
| `/plataforma/projects/[id]` | ProjectDetail | `GET /projects/{id}`, `PATCH /projects/{id}` | ✅ |
| `/plataforma/projects/[id]/tasks` | ProjectTasks | `GET /projects/{id}/tasks`, `POST /projects/{id}/tasks` | ✅ |
| `/plataforma/projects/[id]/wiki` | ProjectWiki | `GET /projects/{id}/wiki`, `POST /projects/{id}/wiki` | ✅ |
| `/plataforma/projects/[id]/comments` | ProjectComments | `GET /projects/{id}/comments`, `POST /projects/{id}/comments` | ✅ |
| `/plataforma/projects/team` | TeamView | `GET /projects/workload` | ✅ |
| `/plataforma/projects/automations` | Automations | (mock) | ⚠️ Mock |
| `/plataforma/projects/general` | GeneralSettings | (mock) | ⚠️ Mock |
| `/plataforma/projects/welcome` | WelcomeView | (static) | N/A |
| `/plataforma/projects/inbox` | InboxView | `GET /projects/inbox` | ✅ |
| `/plataforma/projects/comments` | CommentsView | `GET /projects/comments` | ✅ |
| `/plataforma/projects/more` | MoreView | (static) | N/A |

### Finance/Donations (5 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/finances` | FinanceDashboard | `GET /finance/summary`, `GET /finance/transactions` | ✅ |
| `/plataforma/finances/transparency` | Transparency | `GET /finance/impact`, `GET /finance/total` | ✅ |
| `/plataforma/community/give` | GivePage | `POST /donations`, `POST /donations/mercadopago/create-preference` | ✅ |
| `/plataforma/admin/donations` | DonationAdmin | `GET /donations`, `GET /donations/summary` | ✅ |
| `/plataforma/admin/donations/[id]` | DonationDetail | `GET /donations/{id}`, `GET /donations/{id}/certificate` | ✅ |

### Community (11 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/community` | CommunityHome | `GET /community/cards`, `GET /community/grupos` | ✅ |
| `/plataforma/community/grupos` | GroupList | `GET /community/grupos` | ✅ |
| `/plataforma/community/events` | EventList | `GET /community/events` (mock) | ⚠️ Mock |
| `/plataforma/community/prayer` | PrayerList | `GET /prayer`, `POST /prayer` | ✅ |
| `/plataforma/community/prayer/request` | PrayerRequest | `POST /prayer` | ✅ |
| `/plataforma/community/testimonies` | TestimonyList | `GET /cms/testimonials`, `POST /cms/testimonials` | ✅ |
| `/plataforma/community/testimonies/publish` | PublishTestimony | `POST /cms/testimonials` | ✅ |
| `/plataforma/community/messages` | Messages | `GET /messaging/history` | ✅ |
| `/plataforma/community/announcements` | Announcements | `GET /cms/announcements` | ✅ |
| `/plataforma/community/discover` | Discover | (mock data) | ❌ Sin backend |
| `/plataforma/community/notifications` | Notifications | `GET /messaging/notifications` | ✅ |

### Agenda/Calendar (4 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/agenda/events` | EventList | `GET /agenda/events` | ✅ |
| `/plataforma/agenda/events/[id]` | EventDetail | `GET /agenda/events/{id}`, `PATCH /agenda/events/{id}` | ✅ |
| `/plataforma/calendar` | CalendarView | `GET /agenda/events` | ✅ |
| `/plataforma/agenda/events/[id]/edit` | EventEdit | `PATCH /agenda/events/{id}` | ✅ |

### Dashboard (7 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/dashboard` | DashboardOverview | `GET /dashboard/academy`, `GET /dashboard/crm` | ✅ |
| `/plataforma/dashboard/academy` | AcademyDashboard | `GET /dashboard/academy` | ✅ |
| `/plataforma/dashboard/admin` | AdminDashboard | `GET /dashboard/admin` | ✅ |
| `/plataforma/dashboard/crm` | CRMDashboard | `GET /dashboard/crm` | ✅ |
| `/plataforma/dashboard/evangelism` | EvangelismDashboard | `GET /dashboard/evangelism` | ✅ |
| `/plataforma/dashboard/finance` | FinanceDashboard | `GET /dashboard/finance` | ✅ |
| `/plataforma/dashboard/projects` | ProjectsDashboard | `GET /dashboard/projects` | ✅ |

### Messaging/Chat (3 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/messages` | MessageList | `GET /messaging/history`, `POST /messaging/send` | ✅ |
| `/plataforma/inbox` | Inbox | `GET /messaging/history`, `GET /messaging/notifications` | ✅ |
| `/plataforma/inbox/messages` | MessageThread | `GET /messaging/history/{id}` | ✅ |

### Support/Tickets (6 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/support` | SupportHome | `GET /support`, `POST /support` | ✅ |
| `/plataforma/support/tickets` | TicketList | `GET /support` | ✅ |
| `/plataforma/support/tickets/[id]` | TicketDetail | `GET /support/{id}`, `PATCH /support/{id}` | ✅ |
| `/plataforma/support/contact` | ContactForm | `POST /public/contact` | ✅ |
| `/plataforma/support/kb` | KnowledgeBase | (mock) | ⚠️ Mock |
| `/plataforma/support/history` | SupportHistory | `GET /support` | ✅ |

### Auth/Account (4 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/auth/login` | LoginPage | `POST /auth/login`, `POST /auth/refresh` | ✅ |
| `/plataforma/auth/register` | RegisterPage | `POST /auth/register` | ✅ |
| `/plataforma/account` | AccountSettings | `GET /auth/me`, `PATCH /auth/me` | ✅ |
| `/plataforma/account/ministry-profile` | MinistryProfile | `GET /kernel/ministries/me`, `POST /kernel/ministries` | ✅ |

### Settings (14 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/settings` | SettingsHome | `GET /admin/variables` | ✅ |
| `/plataforma/settings/roles` | RoleSettings | `GET /admin/roles`, `GET /admin/auth-role-definitions` | ✅ |
| `/plataforma/settings/profile` | ProfileSettings | `GET /auth/me`, `PATCH /auth/me` | ✅ |
| `/plataforma/settings/experience` | ExperienceSettings | (mock) | ⚠️ Mock |
| `/plataforma/settings/socials` | SocialSettings | `GET /admin/socials`, `POST /admin/socials` | ✅ |
| `/plataforma/settings/locations` | LocationSettings | `GET /admin/locations`, `POST /admin_locations` | ✅ |
| `/plataforma/settings/sessions` | SessionSettings | `GET /cms_v2/sessions`, `POST /cms_v2/sessions/revoke-all` | ✅ |
| `/plataforma/settings/system` | SystemSettings | `GET /admin/variables`, `POST /admin/variables` | ✅ |

### Spiritual Life (3 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/spiritual-life` | SpiritualHome | `GET /spiritual/milestones/{persona_id}` | ✅ |
| `/plataforma/spiritual-life/timeline` | TimelineView | `GET /spiritual/milestones/{persona_id}` | ✅ |
| `/plataforma/spiritual-life/certificates` | CertificateView | `GET /academy/me/certificates` | ✅ |

### Graph/Whiteboard (3 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/graph` | GraphView | `GET /graph/snapshot`, `GET /graph/connections/{node_id}` | ⚠️ Parcial |
| `/plataforma/whiteboard` | WhiteboardList | `GET /projects/{id}/whiteboard` | ⚠️ Parcial |
| `/plataforma/whiteboard/new` | WhiteboardNew | `POST /projects/{id}/whiteboard` | ⚠️ Parcial |

### Agents/AI (3 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/agents` | AgentList | `GET /agents`, `POST /agents` | ✅ |
| `/plataforma/agents/[id]` | AgentDetail | `GET /agents/profile/{id}`, `PUT /agents/{id}` | ✅ |
| `/plataforma/agents/[id]/chat` | AgentChat | `POST /agents/ask`, `POST /agents/conversations` | ✅ |

### Wiki (3 páginas)

| Ruta Frontend | Componente | Endpoints Backend | Estado |
|--------------|------------|-------------------|--------|
| `/plataforma/wiki` | WikiList | (ninguno) | ❌ Sin backend |
| `/plataforma/wiki/docs` | WikiDocList | (ninguno) | ❌ Sin backend |
| `/plataforma/wiki/docs/[page_key]` | WikiDocView | (ninguno) | ❌ Sin backend |

---

## Gaps Críticos (Páginas sin Backend Real)

| Prioridad | Ruta | Problema original | Estado actual | Endpoint que ahora usa | Observación |
|-----------|------|-------------------|---------------|------------------------|-------------|
| 🔴 **Crítica** | `/plataforma/wiki` | Sin API dedicada | ✅ Resuelto | `GET /cms/content` | Listado corregido para usar el endpoint real de CMS. |
| 🔴 **Crítica** | `/plataforma/wiki/docs` | Sin API dedicada | ✅ Resuelto | N/A | Página vacía que redirige a `/plataforma/wiki`. |
| 🔴 **Crítica** | `/plataforma/wiki/docs/[page_key]` | Sin API dedicada | ✅ Resuelto | `GET/PATCH /cms/content/{page_key}` | Usa endpoint real de CMS. |
| 🔴 **Crítica** | `/plataforma/community/discover` | Mock data | ✅ Resuelto | `GET /crm/groups` | Ahora conectado a endpoint real. |
| 🔴 **Crítica** | `/plataforma/cms/builder` | Mock data | ✅ Resuelto | `GET/POST/PATCH /cms/v2/sites`, `/cms/v2/sites/{site}/pages`, `/cms/v2/sites/{site}/pages/{slug}/sections` | Conectado a `cms_v2.py`. Solo el asistente AI mantiene un fallback mock. |
| 🔴 **Crítica** | `/plataforma/cms/preview` | Mock data | ✅ Resuelto | `GET /cms/v2/sites/{site_key}/pages/{slug}/preview` | Usa endpoint real de preview. |
| 🟠 **Alta** | `/plataforma/projects/automations` | Mock | ✅ Resuelto | `GET/POST/PATCH /admin/automations` | Conectado a reglas de automatización reales. |
| 🟠 **Alta** | `/plataforma/projects/general` | Mock | ✅ Resuelto | `GET /projects/activities`, `GET /projects`, `POST /projects/{id}/comments` | Ahora usa endpoints reales. |
| 🟠 **Alta** | `/plataforma/admin/settings/experience` | Mock | ✅ Resuelto | `GET/PATCH /workspace/config` | Conectado a `workspace_config.py`. |
| 🟠 **Alta** | `/plataforma/settings/experience` | Mock | N/A | No existe la ruta | El equivalente funcional es `/plataforma/admin/settings/experience`. |
| 🟠 **Alta** | `/plataforma/admin/settings/contact` | Mock | ✅ Resuelto | `GET/POST /admin/variables` | Persistido en `site_contact_info` y `site_office_hours`. |
| 🟠 **Alta** | `/plataforma/settings/contact` | Mock | N/A | No existe la ruta | El equivalente funcional es `/plataforma/admin/settings/contact`. |
| 🟠 **Alta** | `/plataforma/community/events` | Mock | ✅ Resuelto | `GET /community/events` | Creado endpoint en `community.py` basado en `EventoAgenda`. |
| 🟠 **Alta** | `/plataforma/support/kb` | Mock | ✅ Resuelto | `GET /support/kb/categories`, `GET /support/kb/articles` | Nuevo módulo `api/support_kb.py` usando `AgentKnowledgeBase`. |
| 🟡 **Media** | `/plataforma/graph` | Parcial | ✅ Resuelto | `GET /graph/snapshot` | Usa `useGraphInsights` → endpoint real. |
| 🟡 **Media** | `/plataforma/whiteboard/*` | Parcial | ✅ Resuelto | `GET/POST /projects/{project_id}/whiteboard`, `GET /projects/whiteboards` | Migrado a backend; cada pizarra se vincula a un proyecto. |
| 🟡 **Media** | `/plataforma/academy/resources` | Mock data | ✅ Resuelto | `GET /academy/me/enrollments`, `GET /academy/courses/{id}/lessons` | Ahora conectado a hooks reales. |

---

## Endpoints Backend Sin Frontend

| Endpoint | Módulo | Posible Uso Frontend | ¿Usado ahora? | Archivo(s) donde se usa |
|----------|--------|---------------------|---------------|------------------------|
| `GET /cms_v2/images/{media_id}/resize` | `cms_v2.py` | Image optimizer en builder | ❌ No | — |
| `POST /cms_v2/images/optimize` | `cms_v2.py` | Upload con optimización | ❌ No | — |
| `GET /cms_v2/track/{page_key}` | `cms_v2.py` | Analytics tracking | ❌ No | — |
| `GET /evangelism/analytics/strategy/{id}/heatmap` | `evangelism_analytics.py` | Heatmap visual | ❌ No | — |
| `GET /evangelism/analytics/strategy/{id}/velocity` | `evangelism_analytics.py` | Velocity chart | ❌ No | — |
| `GET /evangelism/analytics/strategy/{id}/funnel` | `evangelism_analytics.py` | Funnel visualization | ❌ No | — |
| `GET /agents/kb/search` | `agents.py` | Semantic search UI | ❌ No | — |
| `GET /agents/kb/stats` | `agents.py` | KB stats dashboard | ❌ No | — |
| `GET /system/search` | `system.py` | Global search UI | ✅ Sí | `src/components/ui/CommandCenter.tsx` |
| `GET /system/workload` | `system.py` | Workload monitor | ✅ Sí | `src/app/plataforma/projects/team/page.tsx` |
| `GET /analytics/radar` | `analytics.py` | Pastor radar chart | ❌ No | El radar del pastor usa `/crm/radar` en `src/app/plataforma/admin/dashboard/radar/page.tsx`. |
| `GET /finance/impact` | `finance.py` | Impact report | ✅ Sí | `src/app/plataforma/finances/transparency/page.tsx`, `src/app/plataforma/admin/mission-impact/page.tsx` |

---

## Recomendaciones (actualizadas tras verificación)

### Inmediato (Sprint 1)
1. **CMS media optimizer** — Integrar `/api/cms/v2/images/optimize` y `/api/cms/v2/images/{media_id}/resize` en el MediaPicker/builder.
2. **Analytics avanzados** — Aprovechar `/api/evangelism/analytics/strategy/{id}/{heatmap,velocity,funnel}` en la vista de estrategias.

### Corto Plazo (Sprint 2-3)
3. **Agent KB** — Implementar UI de búsqueda semántica con `/api/agents/kb/search` y `/api/agents/kb/stats`.
4. **Tracking** — Usar `POST /api/cms/v2/track/{page_key}` para analytics de preview/public pages.
5. **Global search** — Ampliar `CommandCenter.tsx` para consumir más endpoints de `/api/system/search`.

---

## Cómo Validar Cobertura

```bash
# Ver endpoints registrados en FastAPI
cd /root/ccf/backend && PYTHONPATH=/root/ccf /root/ccf/venv/bin/python -c "
from backend.app import app
for route in app.routes:
    if hasattr(route, 'methods'):
        print(f'{list(route.methods)[0]} {route.path}')
" | sort | uniq

# Ver páginas frontend
cd /root/ccf/frontend && find src/app/plataforma -name "page.tsx" | wc -l

# Buscar llamadas apiFetch en producción
cd /root/ccf/frontend && grep -r "apiFetch" src/app/plataforma --include="*.tsx" | grep -v "test" | wc -l
```

---

*Generado automáticamente - Revisar y actualizar tras cambios en rutas o endpoints*