# Runbook Operativo: Asistencia de Eventos vs Agenda General

Fecha: 2026-05-17  
Estado: Vigente

## 1. Objetivo

Evitar mezcla de dominios:
- **Evento con seguimiento**: pertenece a Evangelismo y sí registra asistencia.
- **Evento de agenda**: reunión general sin seguimiento de asistencia.

## 2. Regla de decisión

Crear en **Evangelismo > Eventos** cuando:
- Se necesita lista de presentes/ausentes.
- Se requiere audiencia esperada (toda iglesia, roles o manual).
- Se necesita trazabilidad histórica de asistencia.

Crear en **Agenda** cuando:
- Solo se necesita visibilidad de calendario.
- No hay control de asistencia.
- No se necesitan métricas de asistencia.

## 3. Flujo operativo: Evento con asistencia

1. Crear evento en `/evangelism/events`.
2. Definir audiencia:
- `ALL`: toda la iglesia.
- `ROLE`: uno o más roles.
- `MANUAL`: personas específicas.
3. Abrir drawer de asistencia por fecha de sesión.
4. Marcar presentes (manual o por scanner).
5. Guardar registro.

Controles activos:
- Eventos `CANCELLED` no permiten guardar asistencia.
- Guardar con `0` presentes requiere confirmación explícita.
- `attendance_date` se guarda como fecha plana (`YYYY-MM-DD`).

## 4. Flujo operativo: Agenda sin asistencia

1. Crear evento en `/agenda/events`.
2. Registrar título, fecha/hora, ubicación y descripción.
3. No usar módulos de Evangelismo para este caso.

## 5. Política de acceso

- Módulo Evangelismo: solo roles `admin` y `pastor`.
- Usuarios fuera de esos roles deben ver bloqueo de acceso y no ver enlaces de Evangelismo en sidebar.

## 6. Validaciones y QA

Backend:
- `pytest tests/test_crm_api.py -k evangelism -q`
- `python scripts/qa_evangelism_integrity.py`

Frontend:
- `npm run typecheck`
- `npm run lint:strict`

## 7. Fallas frecuentes y respuesta

1. “No puedo pasar asistencia”:
- Confirmar que el evento no esté `CANCELLED`.
- Confirmar rol del usuario (`admin/pastor`).

2. “Se guardaron ausentes por error”:
- Ocurre cuando se guarda con pocos o cero presentes.
- Reabrir sesión de fecha y corregir selección.

3. “Evento creado en módulo incorrecto”:
- Si necesita asistencia, migrar a Evangelismo recreando evento con audiencia correcta.
- Si no necesita asistencia, mantener en Agenda.
