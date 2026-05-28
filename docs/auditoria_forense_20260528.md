# INFORME DE AUDITORÍA FORENSE — Plataforma CCF
## Fecha: 2026-05-28 | Auditor: Senior DBA + Code Auditor

================================================================================
# CAPA A: KERNEL UNIFICADO DE PERSONAS (Fragmentación de Identidad)
================================================================================

## Violaciones CRÍTICAS (Integer → UUID)

### Modelos con Integer FK a users.id (debe ser persona_id UUID)
| Archivo | Línea | Columna | Severidad |
|---|---|---|---|
| models_crm.py | 17 | ChatMessage.sender_id | CRITICAL |
| models_crm.py | 31 | Conversation.last_sender_id | CRITICAL |
| models_crm.py | 44 | ConversationParticipant.user_id | CRITICAL |
| models_crm.py | 65 | AgendaEvent.created_by_user_id | CRITICAL |
| models_crm.py | 165 | CounselingTicket.pastor_id | CRITICAL |
| models_crm.py | 618 | CrmTask.assignee_id | CRITICAL |
| models_crm.py | 630 | CrmTask.created_by_id | CRITICAL |
| models_crm.py | 850 | EvangelismStrategy.owner_id | CRITICAL |
| models_academy.py | 65 | LessonProgress.user_id | CRITICAL |
| models_academy.py | 120 | Enrollment.user_id | CRITICAL |
| models_academy.py | 156 | CourseAttendance.user_id | CRITICAL |
| models_academy.py | 184 | Assignment.user_id | CRITICAL |
| models_academy.py | 215 | Resource.user_id | CRITICAL |
| models_academy.py | 248 | ForumThread.user_id | CRITICAL |
| models_academy.py | 270 | ForumComment.user_id | CRITICAL |

### Schemas con persona_id: int (debe ser str para UUID)
| Archivo | Línea | Schema | Severidad |
|---|---|---|---|
| schemas/crm.py | 98 | EventAttendanceBase.persona_id | HIGH |
| schemas/crm.py | 123 | EventAttendanceBase.event_id | HIGH |
| schemas/crm.py | 290 | Persona.id (ya corregido a str) | RESUELTO |
| schemas/crm.py | 800 | Family.id | HIGH |
| schemas/crm.py | 807 | CellGroupMember.id | MEDIUM |

================================================================================
# CAPA B: AISLAMIENTO MULTI-TENANT (sede_id)
================================================================================

## CRÍTICAS — Sin autenticación (público)
| Endpoint | Archivo:Línea | Exposición |
|---|---|---|
| GET /api/locations | admin.py:238 | Todas las ubicaciones de iglesia |
| GET /api/socials | admin.py:276 | Todos los canales sociales |
| GET /api/milestones | admin.py:528 | Todos los badges |
| GET /api/donation-categories | admin.py:590 | Todas las categorías |
| GET /api/automations | admin.py:626 | Todas las reglas de automatización |

## HIGH — Autenticado pero sin filtro sede_id
| Módulo | Endpoints afectados | Cantidad |
|---|---|---|
| CRM Core | list_plantillas, list_casos, list_interacciones, list_tareas | 4 |
| Academy Core | list_cursos, list_enrollments, list_threads, list_certificates | 4 |
| Evangelism | list_strategies, list_groups, list_seasons, list_sessions | 8+ |
| Proyectos | list_proyectos, list_tareas | 2 |
| Admin | list_roles, list_users | 2 |

## CUMPLEN — Filtran por sede_id
- GET /api/crm-core/pipelines (sede_id param)
- GET /api/agenda-core/recursos (sede_id param)
- GET /api/agenda-core/eventos (sede_id param)
- GET /api/crm/members (crud.get_user_sede_id)
- GET /api/crm/personas (crud.get_user_sede_id)

================================================================================
# CAPA C: TIMEZONES — DateTime(timezone=True)
================================================================================

## CUMPLE
- models_agenda.py — 9/9 DateTime con timezone=True ✅

## NO CUMPLEN (40+ columnas sin timezone=True)
| Archivo | Columnas afectadas | Severidad |
|---|---|---|
| models_proyectos.py | 6 DateTime sin tz | HIGH |
| models_crm_core.py | 5 DateTime sin tz (CasoCRM, InteraccionCRM) | HIGH |
| models_academy_core.py | 7 DateTime sin tz | HIGH |
| models_crm.py | 12+ DateTime sin tz | HIGH |
| models_evangelism.py | 6+ DateTime sin tz | HIGH |
| models_shared.py | _utcnow() elimina tzinfo (.replace(tzinfo=None)) | ROOT CAUSE |

================================================================================
# CAPA D: CONCURRENCIA Y COLISIONES (Race Conditions)
================================================================================

## CRÍTICAS
1. models_agenda.py — ReservaRecurso sin __table_args__ con ExcludeConstraint
2. crud/agenda_core.py:create_reserva — sin SELECT FOR UPDATE ni lock
3. api/agenda_core.py:create_reserva — sin verificación de disponibilidad

## PostgreSQL
- Extensión btree_gist: NO VERIFICADA (requiere acceso superuser)
- Constraint sin_colisiones_fisicas: NO EXISTE en la BD

================================================================================
# CAPA E: POLIMÓRFICO + SOFT DELETE
================================================================================

## CRÍTICAS
1. crud/agenda_core.py:list_eventos — NO filtra deleted_at IS NULL (bug inconsistente)
2. crud/agenda_core.py:get_evento — NO filtra deleted_at
3. api/crm/pastoral.py — delete_consolidation_case: HARD DELETE (sin soft-delete)
4. api/evangelism_grupos.py — delete_cell_group, delete_session: HARD DELETE
5. crud/academy_core.py — delete_curso, delete_leccion, delete_matricula: HARD DELETE

## POLIMÓRFICO (modulo_origen + entidad_origen_id)
- Infraestructura EXISTE en modelos_agenda.py pero NO SE USA
- Ningún módulo crea EventoAgenda al crear casos/enrollments/tareas
- Sin propagación de deleted_at entre dominios

================================================================================
# SCRIPTS DE REMEDIACIÓN PROPUESTOS
================================================================================
