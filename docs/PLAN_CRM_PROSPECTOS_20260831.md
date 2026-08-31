# Plan integral — Creación de prospectos CRM

**Frente:** CRM  
**Rama de trabajo:** `feature/crm-prospectos-20260830`  
**Fecha:** 2026-08-31  
**Estado:** diagnóstico inicial

## Objetivo

Garantizar que un prospecto pueda registrarse desde el CRM de forma confiable, atómica y trazable: validar los datos, respetar la sede del usuario, evitar duplicados, crear o reutilizar la persona y generar su caso inicial en el pipeline sin estados parciales.

## Hallazgos confirmados

1. La pantalla Contactos llama a `/crm/personas/`, pero envía `source`, un campo rechazado por `PersonaCreate` (`extra="forbid"`).
2. El formulario permite dejar vacío el apellido, aunque `PersonaCreate` exige mínimo dos caracteres.
3. Contactos y Pipeline muestran casos CRM (`/crm/casos`), mientras Contactos solo crea una persona; por eso el registro puede no aparecer en el listado.
4. Pipeline envía datos de prospecto a `/crm/casos`, pero `CasoCreate` exige `persona_id` y rechaza `first_name`, `last_name`, `phone` y `spiritual_status`.
5. El backend ya contiene lógica para crear persona y caso juntos, pero el esquema no representa ese flujo.
6. El error de WebSocket observado pertenece al canal de mensajería y se auditará por separado; no se asumirá como causa del registro CRM.

## Alcance

Incluye Contactos, Pipeline, esquemas CRM, servicio de creación, endpoint de casos, deduplicación, aislamiento por sede, permisos y pruebas relacionadas. No incluye rediseño general del CRM ni cambios al módulo de Mensajería salvo la verificación de que no interfiera.

## Plan de ejecución

### Fase 1 — Línea base reproducible

- Reproducir los payloads actuales de Contactos y Pipeline.
- Registrar respuestas 4xx/5xx y validar el comportamiento con y sin autenticación.
- Revisar el contrato real de `PersonaCreate`, `CasoCreate`, `CasoCRM` y la función de creación de casos.
- Confirmar reglas de sede, deduplicación, auditoría y transacción.
- Separar formalmente el diagnóstico del WebSocket de mensajería.

**Salida:** caso reproducible y matriz de contratos actual/esperado.

### Fase 2 — Contrato único de prospecto

- Definir un payload explícito para registrar prospectos:
  - `persona_id` opcional para reutilizar una persona existente.
  - `first_name`, `last_name`, `phone`, `email` y `spiritual_status` para una persona nueva.
  - `source`, `stage`, `notes` y campaña como datos del caso.
- Definir respuesta con `persona`, `case` e indicador de reutilización.
- Mantener compatibilidad con el flujo existente que crea casos para una persona ya existente.
- Rechazar campos desconocidos y mensajes de validación claros.

**Salida:** contrato documentado y aprobado por pruebas de esquema.

### Fase 3 — Backend transaccional

- Hacer coherente `CasoCreate` con los dos modos soportados: persona existente o datos de persona nueva.
- Centralizar el caso de uso en un servicio CRM, evitando que Contactos y Pipeline implementen lógicas distintas.
- Resolver la sede exclusivamente desde el usuario autenticado o validar que la persona pertenezca a ella.
- Deduplicar por teléfono, móvil, correo o documento dentro de la misma sede, sin cruzar datos entre sedes.
- Crear persona y caso en una sola transacción; hacer `rollback` ante cualquier fallo.
- Traducir etapa, fuente y notas al modelo canónico del caso sin perder la información.
- Mantener auditoría, timestamps UTC, soft delete y compatibilidad con integraciones existentes.
- Cubrir correctamente el caso de persona existente para no duplicar personas ni generar casos involuntarios.

**Salida:** endpoint único probado con persistencia atómica.

### Fase 4 — Frontend CRM

- Cambiar Contactos y Pipeline al endpoint y payload únicos.
- Eliminar la llamada incorrecta a `/crm/personas/` para este flujo.
- Usar la ruta canónica sin slash final cuando corresponda al contrato.
- Validar nombre, apellido y datos de contacto antes de enviar.
- Mostrar el detalle real devuelto por el backend, incluyendo errores de validación y duplicados.
- Bloquear doble envío, conservar estados de carga y refrescar el pipeline después del alta.
- Verificar que la persona creada abra el caso correcto desde Contactos, Pipeline y detalle.

**Salida:** flujo visual consistente en ambas entradas del CRM.

### Fase 5 — Calidad y regresión

- Pruebas de esquema para persona nueva y persona existente.
- Pruebas API de creación exitosa, datos inválidos, duplicado, sede faltante y rollback.
- Pruebas RBAC para lectura, edición y ausencia de permisos.
- Pruebas de aislamiento entre sedes.
- Pruebas de que el listado devuelve el caso recién creado.
- Pruebas frontend del payload, manejo de error y refresco.
- Ejecutar lint, typecheck, pruebas backend, pruebas frontend y build según el protocolo del repositorio.
- Revisar seguridad y arquitectura antes de integrar.

**Criterio de aceptación:** un prospecto válido produce exactamente una persona y un caso CRM visible en el pipeline; ningún error deja registros parciales.

### Fase 6 — Integración por ramas

- Mantener todos los cambios en la rama CRM `feature/crm-prospectos-20260830`.
- Crear una rama temporal de integración basada en el `main` más reciente cuando los checks locales estén verdes.
- Ejecutar contrato de rama, guardrails, lint, pruebas y builds.
- Hacer commit exclusivo del CRM y push únicamente de la rama CRM.
- Integrar a `main` solo con checks exitosos; conservar separadas las ramas con conflictos.
- Archivar la rama temporal integrada bajo `archive/merged/` según el protocolo del repositorio.

### Fase 7 — Verificación en producción

- Desplegar después de la integración aprobada.
- Probar creación con datos reales controlados, duplicado y error de validación.
- Confirmar en base de datos la relación persona–caso y la sede.
- Confirmar visualmente Contactos, Pipeline y detalle.
- Revisar logs sin exponer datos sensibles.
- Mantener un procedimiento de reversión al commit anterior si la verificación falla.

## Riesgos y controles

| Riesgo | Control |
|---|---|
| Persona creada sin caso | Una sola transacción backend |
| Duplicados | Deduplicación scoped por sede y pruebas de concurrencia si aplica |
| Fuga entre sedes | Sede derivada del usuario y filtros en persona/caso |
| Contratos divergentes | Endpoint y servicio único |
| Regresión en evangelismo | Mantener compatibilidad del servicio existente y ejecutar su suite |
| Confusión con WebSocket | Tratar mensajería como diagnóstico independiente |
| Push desordenado | Rama CRM exclusiva y protocolo de integración |

## Estado actual

- Rama CRM creada desde `origin/main`.
- Diagnóstico inicial completado.
- Plan documentado.
- Sin cambios funcionales, commit ni push todavía.

## Próximo paso

Implementar la Fase 2 y la Fase 3 juntas, empezando por el contrato `CasoCreate` y el servicio transaccional, y después adaptar Contactos y Pipeline.
