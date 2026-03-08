# Matriz de Requerimientos por Rol y Modalidad (v0)

## Contexto
- Proyecto: CCF Plataforma Educativa
- Fecha: 2026-03-05
- Estado: En revision interna

## Matriz
| ID | Modalidad | Rol | Requerimiento | Tipo | Prioridad | Esfuerzo | Dependencia | Criterio de aceptacion | Estado |
|---|---|---|---|---|---|---|---|---|---|
| REQ-001 | Ambas | Aspirante | Ver catalogo segmentado por modalidad | Funcional | Must | S | API de cursos | Lista separada formal/no formal visible | Hecho |
| REQ-002 | Ambas | Aspirante | Inscribirse a curso desde catalogo | Funcional | Must | S | API de enrollments | Inscripcion creada con confirmacion | Hecho |
| REQ-003 | Ambas | Estudiante | Ver cursos inscritos y progreso | Funcional | Must | S | API de enrollments | Vista de mis cursos con avance | Hecho |
| REQ-004 | Formal | Coordinador | Validar prerrequisitos antes de matricula | Funcional | Must | M | Reglas de negocio formal | Bloqueo de matricula sin prerrequisito | Pendiente |
| REQ-005 | Formal | Docente | Registrar calificacion por evaluacion | Funcional | Must | M | Modulo evaluaciones | Nota persistida por estudiante | Pendiente |
| REQ-006 | No formal | Estudiante | Completar curso autoformativo con seguimiento | Funcional | Should | S | Lecciones y progreso | Estado progreso actualizado | En curso |
| REQ-007 | No formal | Estudiante | Recibir microcertificado al finalizar | Funcional | Must | M | Modulo certificacion | Certificado descargable disponible | Pendiente |
| REQ-008 | Ambas | Admin | Gestionar testimonios desde panel | Funcional | Should | S | Panel admin | Alta/baja/moderacion de testimonios | Hecho |
| REQ-009 | Ambas | Admin | Gestionar roles y permisos | Funcional | Must | M | Autenticacion | Restriccion por rol aplicada | Pendiente |
| REQ-010 | Ambas | Operacion | Ver metricas de conversion y finalizacion | Funcional | Should | M | Endpoint dashboard | KPI visibles en tablero | En curso |
| REQ-011 | Ambas | Todos | Disponibilidad del servicio | No funcional | Must | M | Infraestructura | Disponibilidad >= 99.5% | Pendiente |
| REQ-012 | Ambas | Soporte | Tiempo de primera respuesta < 24h | No funcional | Should | S | Mesa de ayuda | SLA medido y reportado | Pendiente |

## Cobertura por modulo
| Modulo | Requerimientos vinculados |
|---|---|
| Portal | REQ-001, REQ-002 |
| LMS | REQ-003, REQ-005, REQ-006 |
| Gestion academica | REQ-004, REQ-007 |
| Gobierno (roles/permisos) | REQ-009 |
| Reportes | REQ-010, REQ-011, REQ-012 |

## Riesgos abiertos
| ID | Riesgo | Impacto | Mitigacion | Owner |
|---|---|---|---|---|
| R-001 | Reglas formales no cerradas con academia | Alto | Taller de validacion semanal | Producto |
| R-002 | Falta de roles implementados en backend/frontend | Alto | Priorizar MVP-001 en sprint actual | Tech Lead |
