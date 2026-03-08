# CCF Fase 1 - Matriz de Requerimientos y Reglas de Negocio

## Requerimientos por modalidad

| ID | Modalidad | Tipo | Requerimiento | Prioridad | Estado |
| --- | --- | --- | --- | --- | --- |
| FRM-001 | Formal | Funcional | Gestion de cohortes por periodo academico | Alta | En curso |
| FRM-002 | Formal | Funcional | Control de prerrequisitos para matricula | Alta | Pendiente |
| FRM-003 | Formal | Funcional | Registro de notas finales y actas | Alta | Pendiente |
| NFM-001 | No formal | Funcional | Autoinscripcion desde catalogo publico | Alta | Implementado MVP |
| NFM-002 | No formal | Funcional | Cursos de avance autonomo por lecciones | Alta | Implementado base |
| NFM-003 | No formal | Funcional | Emision automatica de microcertificados | Media | Pendiente |

## Requerimientos por rol

| Rol | Necesidad clave | Modalidad | Estado |
| --- | --- | --- | --- |
| Aspirante | Ver oferta y requisitos | Ambas | Pendiente |
| Estudiante | Inscripcion y seguimiento de progreso | Ambas | Implementado MVP |
| Docente | Gestion de contenidos y evaluaciones | Ambas | Pendiente |
| Coordinador | Control academico y reportes | Principalmente formal | Pendiente |
| Administrador | Configuracion global y permisos | Ambas | Pendiente |

## Reglas de negocio iniciales

### Formal
- RN-F-01: Un estudiante no puede matricularse si no cumple prerrequisitos definidos
- RN-F-02: La aprobacion depende de nota minima y asistencia segun reglamento
- RN-F-03: El certificado oficial solo se genera tras cierre de acta

### No formal
- RN-NF-01: La autoinscripcion queda activa al confirmar pago o beca aprobada
- RN-NF-02: El certificado se emite al completar el 100% y aprobar evaluacion final
- RN-NF-03: Los cursos pueden abrir/cerrar por demanda sin cohorte fija

## Riesgos detectados en Fase 1
- Ambiguedad normativa para certificados oficiales en ciertos programas
- Diferencias de proceso entre coordinaciones academicas
- Dependencia de proveedores externos (pagos/mensajeria)

## Acciones inmediatas (Semana 1)
- [ ] Validar RN-F-01 a RN-F-03 con coordinacion academica
- [ ] Validar RN-NF-01 a RN-NF-03 con unidad de educacion continua
- [ ] Confirmar politica de certificacion y firma
- [ ] Priorizar requerimientos FRM/NFM para MVP

## Evidencia de ejecucion tecnica
- API de cursos por modalidad y API de inscripcion disponibles
- Frontend con catalogo para formal/no formal y vista de cursos inscritos
- Dashboard tecnico inicial con metricas de cursos e inscripciones
