# Matriz de Procesos Academicos y Administrativos (v0)

## Contexto
- Proyecto: CCF Plataforma Educativa
- Fecha: 2026-03-05
- Estado: Borrador para validacion

## Leyenda
- As-Is: proceso actual
- To-Be: proceso objetivo en plataforma

## Procesos academicos
| ID | Proceso | Modalidad | As-Is (hoy) | To-Be (objetivo) | Entrada | Salida | KPI asociado | Owner |
|---|---|---|---|---|---|---|---|---|
| PA-001 | Admision | Formal | Registro manual en hojas y correo | Flujo digital con estado por etapa | Datos aspirante | Aspirante admitido/rechazado | Tiempo de admision | Coordinacion |
| PA-002 | Matricula | Formal | Validacion manual de prerrequisitos | Validacion automatica + excepcion manual | Historial + plan | Matricula activa | Tasa de errores matricula | Registro academico |
| PA-003 | Inscripcion | No formal | Registro web parcial sin trazabilidad completa | Autoinscripcion con confirmacion automatica | Curso + pago | Inscripcion activa | Conversion | Operaciones |
| PA-004 | Seguimiento de avance | Ambas | Seguimiento fragmentado por docente | Progreso centralizado por leccion/modulo | Eventos de uso | % avance por estudiante | Finalizacion | Docencia |
| PA-005 | Evaluacion | Ambas | Instrumentos mixtos no centralizados | Evaluacion en LMS con nota consolidada | Intentos + respuestas | Nota final | Aprobacion | Docente |
| PA-006 | Certificacion | Ambas | Emision semimanual | Emision automatica segun reglas | Estado final curso | Certificado | Tiempo de emision | Registro academico |

## Procesos administrativos
| ID | Proceso | As-Is (hoy) | To-Be (objetivo) | Entrada | Salida | KPI asociado | Owner |
|---|---|---|---|---|---|---|---|
| PM-001 | Pagos y conciliacion | Procesos separados por canal | Integracion de pagos y estado unico por estudiante | Transaccion | Estado financiero actualizado | Pagos exitosos | Finanzas |
| PM-002 | Soporte | Solicitudes por canales dispersos | Mesa de ayuda con SLA y categorias | Ticket | Respuesta y cierre | Primera respuesta < 24h | Soporte |
| PM-003 | Comunicaciones | Mensajes no estandarizados | Plantillas por evento critico (inscripcion, avance, certificacion) | Evento de negocio | Notificacion enviada y registrada | Entrega efectiva | Operaciones |
| PM-004 | Reporteria ejecutiva | Reportes manuales ad hoc | Dashboard recurrente por KPI clave | Datos consolidados | Tablero actualizado | Frecuencia y uso de reportes | Direccion |
| PM-005 | Gobierno de datos | Politicas parciales | Bitacora de acciones y trazabilidad por rol | Logs + eventos | Evidencia de auditoria | Cobertura de auditoria | Tecnologia |

## Brechas clave detectadas
1. Falta automatizar prerrequisitos y certificacion formal.
2. Falta segmentacion robusta por rol en frontend/backend.
3. Falta trazabilidad completa en soporte y comunicaciones.
