# Catalogo de Reglas de Negocio (v0)

## Contexto
- Proyecto: CCF Plataforma Educativa
- Fecha: 2026-03-05
- Estado: Borrador operativo

## Reglas modalidad formal
| ID | Dominio | Regla | Disparador | Entrada | Salida | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RN-FOR-001 | Inscripcion | La matricula exige prerrequisitos aprobados | Solicitud de matricula | Historial academico + plan | Aprobada/Rechazada | Coordinacion academica | Pendiente validacion |
| RN-FOR-002 | Evaluacion | La nota final se calcula por rubrica definida por curso | Cierre de evaluacion | Notas parciales + pesos | Nota final | Docente | Pendiente implementacion |
| RN-FOR-003 | Certificacion | Certificado oficial solo con plan completo y estado financiero al dia | Cierre de cohorte | Estado academico + financiero | Certificado emitido/no emitido | Registro academico | Pendiente |
| RN-FOR-004 | Asistencia | Minimo 80% asistencia para aprobar componente sincronico | Cierre de modulo | Registro asistencia | Cumple/No cumple | Coordinador | Pendiente |

## Reglas modalidad no formal
| ID | Dominio | Regla | Disparador | Entrada | Salida | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| RN-NF-001 | Inscripcion | Autoinscripcion habilitada en cursos abiertos con cupo | Click inscribirse | Cupo + pago | Inscripcion activa | Operaciones | Parcial (base) |
| RN-NF-002 | Progreso | Curso marcado como completo al llegar al umbral de avance definido | Actualizacion de progreso | % avance | Estado completado/no completado | Producto academico | En curso |
| RN-NF-003 | Certificacion | Microcertificado al completar curso y aprobar evaluacion final | Cierre de curso | Progreso + nota | Certificado simple | Producto academico | Pendiente |
| RN-NF-004 | Reingreso | Estudiante puede retomar curso dentro de ventana de acceso | Login a curso | Fecha de vigencia | Acceso permitido/denegado | Soporte academico | Pendiente |

## Reglas transversales
| ID | Dominio | Regla | Trazabilidad | Estado |
|---|---|---|---|---|
| RN-TR-001 | Seguridad | Toda accion admin queda en bitacora | Panel admin + backend | Pendiente |
| RN-TR-002 | Comunicaciones | Confirmaciones criticas se notifican por correo | Inscripcion, aprobacion, certificacion | Pendiente |
| RN-TR-003 | Datos | Identificadores de usuario y curso son unicos y auditables | DB y API | Parcial |

## Reglas listas para implementar primero
1. RN-FOR-001 (prerrequisitos)
2. RN-NF-003 (microcertificado)
3. RN-TR-001 (bitacora admin)
