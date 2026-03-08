# Plantilla - Backlog MVP Priorizado

## Objetivo
Definir backlog MVP ejecutable, priorizado y con dependencias claras para acelerar Fase 4.

## Metadatos
- Fecha de corte:
- Responsable de producto:
- Responsable tecnico:
- Sprint actual:

## Criterios de priorizacion
- Valor de negocio: Alto, Medio, Bajo
- Esfuerzo: S, M, L
- Riesgo: Alto, Medio, Bajo
- Dependencias: Tecnicas, operativas, regulatorias

## Backlog priorizado (vista ejecutiva)
| Rank | ID | Epic/Modulo | Historia/Tarea | Modalidad | Prioridad (MoSCoW) | Valor | Esfuerzo | Riesgo | Dependencias | Responsable | Estado |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | MVP-001 | Gobierno | Autenticacion y roles base | Ambas | Must | Alto | M | Medio | Modelo de usuarios | Backend | Pendiente |
| 2 | MVP-002 | LMS | Evaluaciones basicas (intento, nota, aprobado) | Ambas | Must | Alto | M | Medio | Autenticacion y roles | Backend | Pendiente |
| 3 | MVP-003 | Certificacion | Certificado simple post-completitud | No formal | Must | Alto | S | Bajo | Evaluaciones basicas | Backend + Frontend | Pendiente |
| 4 | MVP-004 | Gestion academica | Reglas de prerrequisito en inscripcion formal | Formal | Should | Medio | M | Medio | Catalogo de reglas | Backend | Pendiente |
| 5 | MVP-005 | Reportes | Dashboard de avance por curso y cohorte | Ambas | Should | Medio | M | Bajo | Datos de progreso | Frontend | Pendiente |

## Detalle por item (Definition of Ready)
| ID | Descripcion funcional | Criterios de aceptacion | Datos necesarios | QA/Prueba | Definition of Done |
|---|---|---|---|---|---|
| MVP-001 | Login y autorizacion por rol | Cada rol accede solo a sus vistas/endpoints | Usuarios, roles, tokens | Prueba de accesos positivos/negativos | Codigo en QA + evidencia de pruebas |
| MVP-002 | Crear y resolver evaluacion | Se guarda nota y estado aprobado/reprobado | Preguntas, intentos, umbral | Casos de nota limite | Flujo end-to-end funcionando |

## Dependencias criticas
| ID | Depende de | Tipo | Riesgo si falla | Plan de contingencia |
|---|---|---|---|---|
| MVP-002 | MVP-001 | Tecnica | Alto | Feature flag temporal y pruebas unitarias |
| MVP-003 | MVP-002 | Tecnica | Medio | Emision manual temporal |

## Capacidad y compromiso semanal
| Semana | Capacidad equipo (pts) | Compromiso (pts) | Margen | Observaciones |
|---|---|---|---|---|
| W1 |  |  |  |  |

## Riesgos y decisiones
| Fecha | Riesgo/Decision | Impacto | Owner | Fecha limite |
|---|---|---|---|---|
|  |  |  |  |  |
