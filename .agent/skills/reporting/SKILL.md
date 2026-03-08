---
name: reporting-engine
description: Nodo especializado en la generación de documentos y reportes estructurados a partir de datos académicos y de comunidad.
---

# Reporting Engine Skill

Este skill permite al agente generar reportes técnicos y operativos para la toma de decisiones.

## Capacidades Principales
- **Reporte de Progreso Académico:** Genera archivos (PDF/CSV) con el estado de inscripciones, notas y asistencia por curso.
- **Reporte de Impacto Social:** Estructura datos de participación familiar a partir del CRM.
- **Trazabilidad de Comunicación:** Consolida logs de mensajes para auditorías de soporte.

## Conectividad de Malla (Mesh)
- **Inputs:** Requiere `enrollment_data` o `member_data` de los nodos LMS/CRM.
- **Outputs:** Provee `structured_report_file` listo para consumo por el nodo de Estrategia o descarga por el usuario.
