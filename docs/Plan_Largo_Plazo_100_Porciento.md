# Plan de Trabajo a Largo Plazo: Ruta hacia el 100% de CCF

Este documento establece la hoja de ruta estratégica para llevar la plataforma CCF desde su actual estado (MVP avanzado con UI de alto rendimiento tipo ClickUp) hasta un producto de nivel empresarial, 100% funcional, escalable y listo para producción masiva.

## Fase 1: Consolidación e Integración Real (Semanas 1-4)
**Objetivo:** Eliminar todos los datos falsos (mock data) de la interfaz y conectar el frontend 100% con el backend FastAPI.

1. **API de Proyectos y Tareas:**
   - Crear modelos SQLAlchemy y endpoints para Proyectos, Tareas, Comentarios y Asignaciones.
   - Integrar `InlineEdit` y `StatusPicker` con mutaciones (PUT/PATCH) reales hacia la API.
2. **CRM y Grupos de Vida Vivos:**
   - Sincronizar la tabla de miembros y casas de gloria con la base de datos real.
   - Implementar el registro de asistencia real desde el Drawer de Grupos.
3. **Bandeja de Entrada (Inbox) Dinámica:**
   - Crear sistema de notificaciones en el backend (websockets o polling optimizado).
   - Generar notificaciones reales al asignar tareas, cambiar estados o recibir mensajes de soporte.
4. **Soporte y Mesa de Ayuda:**
   - Conectar el formulario de soporte para que genere tickets reales en la base de datos y asigne a los agentes correspondientes.

## Fase 2: Robustez del LMS y Evaluaciones (Semanas 5-8)
**Objetivo:** Convertir la Academia en un LMS (Learning Management System) de grado universitario.

1. **Motor de Evaluaciones:**
   - Interfaz de creación de exámenes (opción múltiple, texto libre, carga de archivos) para profesores.
   - Calificación automática y manual con retroalimentación.
2. **Gestión de Contenido Multimedia:**
   - Integración con un CDN (ej. AWS S3, Cloudflare) para streaming seguro de videos y descarga de PDFs.
   - Seguimiento preciso del progreso de video (evitar que el usuario salte el video sin verlo).
3. **Certificaciones Avanzadas:**
   - Generación dinámica de PDFs con firmas digitales y códigos QR de validación.
   - Emisión de insignias (Micro-credenciales) para cursos no formales.

## Fase 3: Ecosistema de Agentes y Automatización (Semanas 9-12)
**Objetivo:** Dar vida a "Optimus Brain" y automatizar la carga administrativa de la iglesia.

1. **Agentes de IA Contextuales:**
   - Implementar el backend de IA usando LangChain/LlamaIndex para responder dudas pastorales, buscar en la base de conocimientos de la iglesia y resumir tareas.
2. **Automatizaciones de CRM:**
   - Flujos de trabajo automáticos: Si un visitante viene 3 veces, mover su estado a "Consolidación" y asignar una tarea al líder de su zona.
3. **Análisis Predictivo:**
   - Dashboards de predicción de deserción (identificar miembros que han dejado de asistir o estudiantes que no avanzan) para intervención temprana.

## Fase 4: Infraestructura, Escalabilidad y QA (Semanas 13-16)
**Objetivo:** Asegurar que la plataforma soporte miles de usuarios concurrentes sin fallos.

1. **Pruebas Exhaustivas (QA):**
   - Implementar pruebas End-to-End (E2E) con Playwright o Cypress para los flujos críticos (Inscripción, Pagos, Creación de Tareas).
   - Alcanzar >80% de cobertura de pruebas unitarias en backend.
2. **Infraestructura Cloud:**
   - Configurar despliegue en Kubernetes (K8s) o Docker Swarm para alta disponibilidad.
   - Configurar base de datos PostgreSQL con réplicas de lectura y copias de seguridad diarias automatizadas.
3. **Monitoreo y Alertas:**
   - Integrar Datadog/Grafana y Sentry para monitoreo de errores en tiempo real.

## Fase 5: Lanzamiento, Migración y Expansión (Semanas 17-20)
**Objetivo:** Despliegue a la congregación y expansión a dispositivos móviles.

1. **Migración de Datos Históricos:**
   - Importar historiales de miembros, estudiantes y donaciones desde sistemas antiguos (Excel, otros softwares).
2. **Lanzamiento Soft-Launch:**
   - Despliegue a un grupo de control (líderes y staff) durante 2 semanas.
3. **PWA / Aplicación Móvil:**
   - Optimizar la plataforma web para que sea instalable (Progressive Web App) con soporte offline parcial.
   - (Opcional) Iniciar desarrollo de app nativa en React Native/Flutter consumiendo la misma API.

---
**Criterio de Éxito Final (100%):** La plataforma opera de manera autónoma, gestionando la formación académica, las células de vida, las donaciones y el staff operativo en un solo lugar centralizado, seguro y escalable.
