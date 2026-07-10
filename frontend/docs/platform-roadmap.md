# Plan de cierre de plataforma

Este documento resume lo que existe hoy y lo que falta en cada módulo para declarar la plataforma “lista”. Sirve como backlog maestro para organizar el trabajo.

## 1. Autenticación y seguridad
- **Implementado**: login/register básicos, contexto de sesión, protección de rutas, toasts.
- **Pendiente**:
  - Recuperación de contraseña, cambio de contraseña y verificación de correo.
  - Renovación automática del token y cierre de sesión por expiración.
  - Gestión de roles/permisos en UI (control de menús y vistas según rol).
  - Auditoría de logins y rate limiting (depende de backend).

## 2. Academia
- **Implementado**: catálogo de cursos, mis inscripciones, modal de certificados, wizard de enrolamiento (mock de pago), socket Mesh para calificaciones.
- **Pendiente**:
  - Conectar páginas estáticas (perfil, recursos, calendario, curriculum, foro, certificados globales) a endpoints reales o despublicarlas.
  - Integrar pagos reales en `academy/enroll/[id]` (pasarela o instrucciones claras).
  - Mejorar `useMeshSocket` (reconexión, manejo de errores) y estados de exámenes.
  - Añadir flujos de tareas/proyectos si backend lo soporta (subir tareas + feedback).

## 3. CRM completo
- **Implementado**: tablero general, pipeline, personas, tareas, mensajes, scanner, automations, grupos (catálogo), voluntarios (listado), eventos con asistencia, settings simples.
- **Pendiente**:
  - CRUD completo para grupos, voluntarios, contactos (alta/baja, asignaciones por rol, filtros, permisos).
  - Integrar counseling y automations con datos reales (hoy es mock sin validación).
  - Sincronizar CRM con academia (personas ↔ estudiantes) y con comunidad (peticiones/prayer).
  - Historial y métricas accionables (gráficos reales en dashboard, no valores fijos).

## 4. Comunidad (public-facing)
- **Implementado**: testimonios (envío + moderación), oración (solicitud), donaciones (UI), grupos/casas, eventos generales, soporte/donate content blocks.
- **Pendiente**:
  - Prayer request debe guardar y notificar (hoy sólo envía al backend sin confirmación admin).
  - Donaciones requiere pasarela real + recibo + conciliación (admin/finance espera `status`).
  - Formularios de soporte/donaciones necesitan validaciones fuertes y seguimiento (ticketing, emails).
  - Eventos públicos deberían ligar con CRM events o separar claramente.

## 5. Admin/CMS
- **Implementado**: dashboards base, testimonios admin, CMS (announcements/sermons/books), actas (cierre formal), submissions (calificaciones), settings.
- **Pendiente**:
  - Edición avanzada en CMS (preview, drag & drop, versionado) y permisos por rol.
  - Integrar CMS con todas las secciones públicas (algunos textos siguen quemados).
  - Admin finance debe mostrar datos reales (status, referencias de pago) y exportar.
  - Reportes/analytics requieren datos reales y filtros.

## 6. Infraestructura transversal
- **Implementado**: cliente `apiFetch`, hooks de contenido, contexto de auth/toast, Vitest básico.
- **Pendiente**:
  - Suite de pruebas ampliada (componentes, hooks clave, rutas API). Integrar a CI.
  - Linting estricto y formatos (Prettier/ESLint). Revisar vulnerabilidades de npm.
  - Documentación operativa: `.env` completos, flujos de despliegue, guías de contribución.
  - Observabilidad (logger, tracing en fetch, manejo centralizado de errores UI).

## Próximos pasos recomendados
1. **Autenticación**: implementar recuperación/verificación + roles. Bloquea mucho del resto.
2. **Academia**: cerrar páginas pendientes y pagos (mínimo instrucciones/links reales).
3. **CRM**: completar CRUD (grupos, voluntarios, contacts) y métricas.
4. **Comunidad/Donaciones**: integrar con pasarela y panel admin.
5. **CMS/Contenido**: garantizar que todo se edite desde admin y agregar permisos.
6. **Calidad**: ampliar pruebas y configurar CI antes del lanzamiento.

### Plan de ejecución sugerido

| Iteración | Objetivo | Historias clave | Dependencias |
|-----------|----------|-----------------|--------------|
| 1 | Endurecer Auth | Recuperar contraseña, verificación email, refresh token, guards por rol | requiere endpoints backend confirmados |
| 2 | Academia MVP | Integrar pagos (mock+pasarela), conectar páginas perfil/resources/schedule, mejorar MyEnrollments + Mesh | Iteración 1 completa (roles) |
| 3 | CRM completo | CRUD grupos/voluntarios/contactos, dashboards reales, automations+counseling conectados | Iteración 1 (roles) |
| 4 | Comunidad & Donaciones | Pasarela de pagos, prayer pipeline (admin), soporte con tickets | Iteraciones previas |
| 5 | CMS/Admin | Editor avanzado, finance real, reportes | Iteración 1 |
| 6 | Calidad & Observabilidad | Pruebas, CI/CD, logging, documentación final | todas las anteriores |

Cada iteración debería cerrarse con pruebas manuales + automáticas (Vitest/Playwright), checklist de roles, y despliegue en staging.
