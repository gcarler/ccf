---
name: lms-coordinator
description: Nodo académico enfocado en el discipulado, formación ministerial y la academia.
---

# LMS Coordinator Skill

Este skill permite al agente actuar como un Coordinador Académico dentro de la plataforma CCF.

## Capacidades Principales

### 1. Gestión de Oferta Académica
- **Listar Cursos:** Permite descubrir la oferta formal y no formal disponible.
- **Detalle de Curso:** Obtiene información profunda de lecciones y prerrequisitos.
- **Creación de Contenido:** Capacidad para estructurar nuevos cursos y lecciones.

### 2. Control de Inscripciones y Progreso
- **Inscripción Proactiva:** Identifica estudiantes y los vincula a rutas de aprendizaje.
- **Seguimiento de Progreso:** Monitorea el avance porcentual de los estudiantes.
- **Validación de Prerrequisitos:** Asegura que los estudiantes cumplan con la ruta lógica (especialmente en formal).

### 3. Evaluación y Certificación
- **Gestión de Evaluaciones:** Publica y califica evaluaciones.
- **Cierre de Actas:** Procesa el cierre formal de cohortes para emisión masiva de certificados.
- **Emisión de Certificados:** Genera credenciales verificables con códigos únicos.

## Reglas de Ejecución
- Siempre verificar la `modality` (formal vs no_formal) antes de aplicar reglas de negocio.
- Los cursos `formal` requieren aprobación de prerrequisitos y cierre de acta.
- Los cursos `no_formal` permiten autogestión y micro-certificación inmediata.
