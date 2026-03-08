# Plantilla - Catalogo de Reglas de Negocio (Formal y No Formal)

## Objetivo
Documentar reglas de negocio versionadas para asegurar decisiones consistentes en backend, frontend y operacion.

## Metadatos
- Fecha de version:
- Responsable funcional:
- Responsable tecnico:
- Estado: Borrador | En revision | Aprobado

## Estructura de cada regla
| Campo | Descripcion |
|---|---|
| ID | Identificador unico (ej. RN-FOR-001) |
| Modalidad | Formal o No formal |
| Dominio | Inscripcion, Evaluacion, Certificacion, Pagos, etc |
| Regla | Definicion de la regla |
| Justificacion | Motivo de negocio/academico |
| Evento disparador | Cuándo aplica |
| Entradas | Datos requeridos |
| Salida esperada | Resultado de la regla |
| Excepciones | Casos especiales |
| Responsable | Quien decide cambios |
| Trazabilidad | Endpoint, pantalla, reporte afectado |

## Reglas modalidad formal
| ID | Dominio | Regla | Evento disparador | Entradas | Salida esperada | Excepciones | Responsable | Trazabilidad |
|---|---|---|---|---|---|---|---|---|
| RN-FOR-001 | Inscripcion | Un estudiante solo puede matricular materias con prerrequisitos aprobados | Solicitud de matricula | Historial academico, plan de estudios | Matricula aprobada/rechazada | Autorizacion manual de coordinacion | Coordinacion academica | `POST /enrollments/`, pantalla matricula |
| RN-FOR-002 | Certificacion | Se emite certificado oficial solo con plan completo aprobado | Cierre de cohorte | Notas finales, estado financiero | Certificado oficial emitido/no emitido | Pendiente administrativo con plazo definido | Registro academico | Modulo certificados, reporte cierre |

## Reglas modalidad no formal
| ID | Dominio | Regla | Evento disparador | Entradas | Salida esperada | Excepciones | Responsable | Trazabilidad |
|---|---|---|---|---|---|---|---|---|
| RN-NF-001 | Inscripcion | La autoinscripcion esta habilitada en cursos con cupo | Click en inscribirse | Cupo disponible, pago | Inscripcion activa | Becas/cupones especiales | Operaciones | `POST /enrollments/`, catalogo |
| RN-NF-002 | Certificacion | Se emite microcertificado al completar >= 80% y aprobar evaluacion final | Finalizacion de curso | Progreso, nota final | Microcertificado generado | Curso sin evaluacion final configurada | Producto academico | Panel estudiante, certificados |

## Reglas transversales
| ID | Dominio | Regla | Impacto |
|---|---|---|---|
| RN-TR-001 | Seguridad | Toda accion de admin debe quedar en bitacora | Auditoria y cumplimiento |
| RN-TR-002 | Comunicaciones | Confirmaciones criticas deben enviarse por correo y quedar registradas | Trazabilidad operativa |

## Control de cambios
| Fecha | ID regla | Cambio | Solicitante | Aprobador |
|---|---|---|---|---|
|  |  |  |  |  |
