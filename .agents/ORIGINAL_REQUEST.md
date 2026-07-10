# Original User Request

## Initial Request — 2026-07-10T05:30:11Z

Implementar la evolución "Super Pro" del CRM de CCF integrando capacidades Enterprise: Pastoral Health Score, AI Copilot para Consejería y una Bandeja de Entrada Omnicanal.

Working directory: /root/ccf
Integrity mode: development

## Requirements

### R1. Pastoral Health Score (Scoring Espiritual)
Desarrollar un motor de análisis en el backend que calcule automáticamente un "Health Score" (0-100) y un estatus (EN_RIESGO, ESTABLE, COMPROMETIDO) para cada persona basado en su actividad reciente (asistencias, donaciones, grupos). El modelo `Persona` debe actualizarse para almacenar este score.

### R2. AI Copilot para Consejería Pastoral
Implementar un endpoint en el backend (`/api/crm/counseling/{id}/copilot-draft`) que lea el historial de un caso de consejería y genere sugerencias de respuesta automáticas usando la API de OpenAI (se asumirá que `OPENAI_API_KEY` estará en el `.env`). Integrar un botón en el frontend (`plataforma/crm/counseling/[id]`) para poblar el editor de texto con estas sugerencias.

### R3. Omnichannel Inbox (Bandeja Omnicanal)
Unificar en el frontend (perfil de la persona) los correos, SMS, mensajes de WhatsApp e hitos espirituales en un componente de línea de tiempo consolidado y continuo, tipo chat.

## Acceptance Criteria

### Backend & Analytics
- [ ] La base de datos tiene la migración aplicada con las nuevas columnas `health_score` y `health_status` en la tabla `personas`.
- [ ] Ejecutar el motor de scoring calcula correctamente los puntajes y actualiza la base de datos sin errores.
- [ ] El endpoint del AI Copilot recibe el ID del ticket y se comunica con la API de OpenAI utilizando la librería estándar, retornando el borrador. Se debe manejar el caso de llave faltante con gracia.

### Frontend
- [ ] La vista de consejería muestra el botón "Generar Respuesta con IA" y, al hacer clic, llena el cuadro de respuesta.
- [ ] La vista del perfil de la persona renderiza la línea de tiempo unificada mostrando un mix de distintos tipos de comunicación (`CommunicationLog`, `SpiritualMilestone`, etc.).
