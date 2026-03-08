# Backlog MVP Priorizado (v0)

## Contexto
- Proyecto: CCF Plataforma Educativa
- Fecha: 2026-03-05
- Horizonte: Proximas 2 semanas

## Backlog
| Rank | ID | Modulo | Item | Prioridad | Valor | Esfuerzo | Dependencias | Owner sugerido | Estado |
|---|---|---|---|---|---|---|---|---|---|
| 1 | MVP-001 | Gobierno | Autenticacion y autorizacion por rol | Must | Alto | M | Modelo de usuarios | Backend | Pendiente |
| 2 | MVP-002 | LMS | Evaluaciones basicas (crear, responder, calificar) | Must | Alto | M | MVP-001 | Backend | Pendiente |
| 3 | MVP-003 | Certificacion | Emision de certificado simple por finalizacion | Must | Alto | S | MVP-002 | Backend + Frontend | Pendiente |
| 4 | MVP-004 | Gestion academica | Validacion de prerrequisitos en formal | Must | Alto | M | RN-FOR-001 | Backend | Pendiente |
| 5 | MVP-005 | Frontend | Vistas por rol (estudiante/docente/admin) | Should | Medio | M | MVP-001 | Frontend | Pendiente |
| 6 | MVP-006 | Reportes | Tablero de avance por modalidad y curso | Should | Medio | M | Eventos de progreso | Frontend + Backend | En curso |
| 7 | MVP-007 | Comunicaciones | Notificaciones de inscripcion/aprobacion | Should | Medio | S | Integracion correo | Backend | Pendiente |
| 8 | MVP-008 | Gobierno | Bitacora de acciones de administracion | Should | Medio | S | MVP-001 | Backend | Pendiente |

## Definition of Done minima
| ID | DoD |
|---|---|
| MVP-001 | Accesos bloqueados por rol en API y UI, pruebas positivas/negativas |
| MVP-002 | Nota final persistida y estado aprobado/reprobado visible |
| MVP-003 | Certificado visible para curso elegible en perfil estudiante |
| MVP-004 | Matricula formal rechazada con mensaje claro si no cumple prerrequisito |

## Plan de ejecucion libre (flujo continuo)
| Orden | Objetivo | Entregable |
|---|---|---|
| 1 | Cerrar reglas y criterios de aceptacion de MVP-001 a MVP-004 | Historias listas para desarrollo |
| 2 | Implementar MVP-001 backend | Endpoints protegidos por rol |
| 3 | Implementar MVP-005 frontend + pruebas acceso | UI segmentada por rol |
| 4 | Implementar MVP-002 | Flujo evaluacion base |
| 5 | Implementar MVP-003 y demo integrada | Flujo inscripcion -> progreso -> evaluacion -> certificado |

## Riesgos
| ID | Riesgo | Impacto | Mitigacion |
|---|---|---|---|
| RB-001 | Roles no definidos al detalle | Alto | Definir matriz de permisos por endpoint/pantalla antes de codificar |
| RB-002 | Certificacion depende de datos no capturados | Medio | Incluir campos minimos desde MVP-002 |
