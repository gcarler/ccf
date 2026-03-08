# Plantilla - Matriz de Requerimientos por Rol y Modalidad

## Objetivo
Consolidar requerimientos funcionales y no funcionales por rol y por modalidad (formal/no formal) para cerrar Fase 1.

## Alcance
- Modalidades: Formal, No formal
- Roles: Aspirante, Estudiante, Docente, Coordinador, Admin

## Metadatos
- Fecha de version:
- Responsable de version:
- Aprobadores:
- Estado: Borrador | En revision | Aprobado

## Criterios de priorizacion
- MoSCoW: Must, Should, Could, Won't (esta fase)
- Esfuerzo: S, M, L
- Riesgo: Bajo, Medio, Alto

## Matriz principal
| ID | Modalidad | Rol | Requerimiento | Tipo (Funcional/NF) | Prioridad | Esfuerzo | Riesgo | Dependencias | Criterio de aceptacion | Estado |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-001 | Formal | Estudiante | Ver plan de estudios por cohorte | Funcional | Must | M | Medio | Datos de cohortes | Puede consultar materias por periodo | Pendiente |
| REQ-002 | No formal | Aspirante | Autoinscripcion en cursos abiertos | Funcional | Must | S | Bajo | Pasarela de pagos | Puede inscribirse y recibir confirmacion | Pendiente |

## No funcionales transversales
| ID | Categoria | Requerimiento | Meta |
|---|---|---|---|
| NF-001 | Disponibilidad | Plataforma disponible en horario operativo | >= 99.5% |
| NF-002 | Soporte | Tiempo de primera respuesta | < 24h |
| NF-003 | Seguridad | Registro de auditoria por accion critica | 100% acciones criticas |

## Mapeo a modulos
| ID Requerimiento | Portal | LMS | Gestion academica | Pagos | Comunicaciones | Reportes |
|---|---|---|---|---|---|---|
| REQ-001 | X | X | X |  |  | X |
| REQ-002 | X |  |  | X | X | X |

## Riesgos y bloqueos
| ID | Riesgo/Bloqueo | Impacto | Mitigacion | Responsable | Fecha compromiso |
|---|---|---|---|---|---|
| R-001 | Integracion de pagos sin contrato final | Alto | Mock de proveedor y pruebas contractuales | Producto + Tech Lead | |

## Aprobacion
- Producto:
- Direccion academica:
- Operaciones:
- Tecnologia:
