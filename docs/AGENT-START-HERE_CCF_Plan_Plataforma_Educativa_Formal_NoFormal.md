# Plan de Trabajo CCF - Plataforma Educativa (Formal y No Formal)

## Estado general
- Estado actual: En ejecucion (MVP tecnico activo)
- Fecha de inicio: 2026-03-05
- Horizonte: 16 semanas (referencial, sin cronograma rigido)
- Meta: Lanzar una plataforma unica con rutas academicas para cursos formales y no formales
- Modalidad de ejecucion: Flujo continuo, sin horarios fijos

## Lo ya realizado
- Plan macro de 6 fases definido
- Diferenciacion inicial de alcance entre modalidad formal y no formal
- Backlog inicial por modulos creado
- KPIs de exito iniciales definidos
- API con cursos formales y no formales implementada
- API de inscripciones y seguimiento basico implementada
- Frontend con catalogo por modalidad y vista de mis cursos implementado

## Fases y tareas ejecutables

### Fase 1 - Descubrimiento y definicion (Semanas 1-2)
Estado: En curso

Tareas:
- [ ] Levantar requerimientos con direccion academica, coordinacion, docentes y soporte
- [ ] Definir reglas de negocio de cursos formales (cohortes, prerrequisitos, actas, notas, certificacion)
- [ ] Definir reglas de negocio de cursos no formales (oferta continua, autoinscripcion, badges, microcertificados)
- [ ] Documentar procesos as-is y to-be (admision, matricula, pagos, evaluacion, certificacion)
- [ ] Acordar KPIs base y metas trimestrales

Criterio de terminado:
- Documento de alcance firmado por responsables academicos y operativos

### Fase 2 - Diseno funcional y UX/UI (Semanas 3-4)
Estado: Pendiente

Tareas:
- [ ] Definir arquitectura funcional por modulos (Portal, LMS, Gestion academica, Pagos, Comunicaciones, Reportes)
- [ ] Disenar flujos por perfil (aspirante, estudiante, docente, coordinador, admin)
- [ ] Prototipar flujo de formal (admision a certificacion oficial)
- [ ] Prototipar flujo de no formal (catalogo a microcertificado)
- [ ] Validar criterios de aceptacion por modulo

Criterio de terminado:
- Prototipos navegables aprobados y backlog refinado

### Fase 3 - Arquitectura tecnica e integraciones (Semanas 5-6)
Estado: Pendiente

Tareas:
- [ ] Definir stack y arquitectura de despliegue
- [ ] Definir modelo de datos unificado con extensiones por modalidad
- [ ] Definir integraciones (pagos, correo/WhatsApp, videoconferencia, certificados, BI)
- [ ] Definir seguridad, auditoria, backups y trazabilidad
- [ ] Definir ambientes dev, qa, prod y estrategia CI/CD

Criterio de terminado:
- Blueprint tecnico aprobado y contratos API definidos

### Fase 4 - Construccion MVP (Semanas 7-10)
Estado: En curso

Tareas:
- [x] Implementar autenticacion y roles (base)
- [x] Implementar catalogo e inscripcion
- [x] Implementar aula virtual y progreso (base)
- [x] Implementar evaluaciones y certificacion (base MVP)
- [ ] Completar reglas avanzadas de evaluacion/certificacion
- [x] Implementar panel de administracion (moderacion de testimonios)
- [x] Cargar contenidos iniciales para formal y no formal

Criterio de terminado:
- MVP funcional desplegado en QA con pruebas base aprobadas

### Fase 5 - Piloto y ajustes (Semanas 11-13)
Estado: Pendiente

Tareas:
- [ ] Ejecutar piloto con 1 programa formal y 2-3 cursos no formales
- [ ] Medir conversion, abandono, avance, finalizacion y satisfaccion
- [ ] Corregir incidencias y mejorar UX
- [ ] Afinar comunicaciones automaticas y reportes academicos

Criterio de terminado:
- Informe de piloto y version candidata a produccion

### Fase 6 - Lanzamiento y escalamiento (Semanas 14-16)
Estado: Pendiente

Tareas:
- [ ] Despliegue productivo gradual
- [ ] Capacitacion por rol y mesa de ayuda
- [ ] Activar tableros ejecutivos y academicos
- [ ] Ejecutar plan de soporte de 90 dias

Criterio de terminado:
- Plataforma en produccion con KPIs operativos activos

## Tablero de seguimiento

### Hecho
- Definido plan marco 16 semanas
- Definidas rutas formal y no formal
- Definidos modulos principales y KPIs iniciales
- Backend MVP con entidades `courses`, `lessons`, `enrollments`
- Datos semilla: cursos formal/no formal y usuarios demo
- Frontend MVP con catalogo por modalidad e inscripcion

### En curso
- Fase 1: Levantamiento y consolidacion de requerimientos
- Fase 4: Construccion MVP

### Pendiente
- Fases 2, 3, 5 y 6

## Plan de ejecucion inmediato (proximos 14 dias)
- [x] Crear matriz de requerimientos por modalidad y por rol (v0 en `docs/2026-03-05_Matriz_Requerimientos_Rol_Modalidad_v0.md`)
- [x] Crear matriz de procesos academicos y administrativos (v0 en `docs/2026-03-05_Matriz_Procesos_Academicos_Administrativos_v0.md`)
- [x] Crear catalogo de reglas de negocio (formal/no formal) (v0 en `docs/2026-03-05_Catalogo_Reglas_Negocio_v0.md`)
- [x] Crear backlog priorizado MVP con esfuerzo estimado (v0 en `docs/2026-03-05_Backlog_MVP_Priorizado_v0.md`)
- [x] Definir RACI y esquema de coordinacion operativa libre (v0 en `docs/2026-03-05_RACI_y_Calendario_Comite_v0.md`)

## Backlog priorizado por modulo
- Academico formal: cohortes, periodos, prerrequisitos, rubricas, actas, certificados oficiales
- Academico no formal: catalogo dinamico, bundles, microcredenciales, certificados automaticos
- Operacion: CRM educativo, notificaciones omnicanal, mesa de ayuda
- Gobierno: roles, permisos, bitacora, proteccion de datos
- BI: embudo comercial, retencion, desempeno docente, progreso, ingresos

## KPI objetivo (primeros 3 meses post lanzamiento)
- Conversion no formal mayor a 20%
- Finalizacion mayor a 70% en no formal guiado
- Finalizacion mayor a 80% en formal por cohorte
- NPS mayor a 50
- Primer contacto de soporte menor a 24h
- Disponibilidad mayor a 99.5%

## Historial de actualizaciones
- 2026-03-05: Se crea documento maestro AGENT-START-HERE con estado inicial de ejecucion
- 2026-03-05: Se implementa MVP tecnico inicial (backend + frontend) para rutas formal y no formal

## Avance técnico implementado en código

### Hitos MVP (Completados 2026-03-05)
- [x] **MVP-001: Seguridad Avanzada:** Registro público restringido a rol 'estudiante', endpoints protegidos por roles (admin/staff) y `ProtectedRoute` en frontend.
- [x] **MVP-002: Evaluaciones Dinámicas:** Sistema de intentos de evaluación con guardado de notas, cálculo de aprobación y persistencia en inscripciones.
- [x] **MVP-003: Certificación Digital:** Generación automática de certificados tras aprobación; Modal de visualización e impresión en el portal del estudiante.
- [x] **MVP-004: Gestión de Prerrequisitos:** Validación automática de cursos previos para la Ruta Formal antes de permitir nuevas inscripciones.
- [x] **MVP-005: Interfaz Administrativa:** Panel admin con Sidebar unificado para Moderación, Temas y la nueva gestión de Actas.
- [x] **MVP-006: Automatización de Actas:** Proceso de cierre de curso formal que califica y certifica masivamente según criterios de nota y asistencia.
- [x] **MVP-007: Asistencia Automática:** Registro de actividad diaria (Check-in) al ingresar a la academia, con actualización de porcentaje de asistencia.
- [x] **MVP-008: Material del Docente:** Capacidad de adjuntar archivos (PDF, DOC, Multimedia) a las lecciones.
- [x] **MVP-009: Entrega de Trabajos:** Espacio para que el estudiante suba sus evidencias y tareas por lección.

Backend (`backend/main.py`, `backend/models.py`, `backend/crud.py`, `backend/schemas.py`):
- Gestión de seguridad robusta (JWT + Roles).
- Lógica de Cierre de Actas y Certificación Masiva.
- Endpoints para intentos de evaluación y validación de prerrequisitos.

Frontend (`frontend/src/app/page.tsx`, `frontend/src/components/MyEnrollments.tsx`, `frontend/src/app/admin/layout.tsx`):
- Sidebar administrativo y protección de rutas.
- Modal de Certificados con funcionalidad de impresión.
- Gestión de Actas para personal administrativo.

