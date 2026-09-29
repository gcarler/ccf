# Puente de agentes CCF

## Fuente de verdad

El registro operativo es `.bridge/bridge.sqlite3`. Cada ticket conserva su dueño,
revisor, revisiones, entrega, dictamen y eventos. Los JSON anteriores en `.bridge/`
se importan una sola vez y permanecen intactos como respaldo. El archivo
`.bridge/codex_submission.txt` es histórico; escribir allí no registra una entrega.

El ejecutable canónico es `python3 scripts/ccf_agent_bridge.py`. Las rutas locales
antiguas `scripts/ccf_bridge.py` y `scripts/ccf_tmux_daemon.py` actúan como
adaptadores en el host actual, pero no son la fuente de verdad.

## Responsables y estados

Cada ticket tiene tres roles distintos: coordinador (`coordinator`), desarrollador
(`owner`) y auditor (`reviewer`). El coordinador asigna y cierra; el desarrollador
entrega; el auditor verifica. La asignación fija el HEAD base del worktree.
Backend y frontend pueden tener tickets diferentes, con dependencia explícita y
worktrees separados. Solo se permite una tarea activa por desarrollador.
Dos tareas activas tampoco pueden compartir la misma raíz de worktree.
Los destinatarios tmux configurados actualmente son `agy`, `agy2`, `codex` y
`freebuff`; un agente nuevo necesita registrar su comando de panel antes de
recibir asignaciones.

`ASSIGNED → WORKING → AWAITING_AUDIT → APPROVED → DONE`

Si la auditoría falla: `AWAITING_AUDIT → REVISION_REQUIRED → AWAITING_AUDIT`.
`CANCELLED` cierra un ticket duplicado o abandonado con motivo registrado.
`approve` nunca crea la siguiente tarea. `close` da el cierre terminal.

## Uso

```bash
python3 scripts/ccf_agent_bridge.py assign --id TKT-123 --module academy \
  --title "Vista de cohorte" --desc "Implementar la vista aprobada" \
  --actor agy --owner agy2 --reviewer codex --worktree /root/ccf \
  --criteria "tsc limpio;contrato API validado"
```

El daemon deja el evento en `SENT` después de que tmux acepta el texto. El agente
ejecuta el comando `ack` incluido en el mensaje; entonces pasa a `ACKED` y la
tarea a `WORKING`. `SENT` no significa que el modelo haya leído el mensaje.
El ID del evento aparece en la salida de `assign` y en el aviso recibido.

```bash
python3 scripts/ccf_agent_bridge.py ack --event <EVENT_ID_ASIGNACION> --actor agy2
python3 scripts/ccf_agent_bridge.py submit --id TKT-123 --actor agy2 \
  --commit <SHA_COMPLETO_DE_40_CARACTERES> --files frontend/src/app/plataforma/academy/page.tsx \
  --check "tsc PASS" --notes "Vista implementada y verificada"
python3 scripts/ccf_agent_bridge.py ack --event <EVENT_ID_ENTREGA> --actor codex
python3 scripts/ccf_agent_bridge.py approve --id TKT-123 --actor codex \
  --score 100 --evidence "SHA revisado; tests y contrato comprobados"
python3 scripts/ccf_agent_bridge.py ack --event <EVENT_ID_DICTAMEN> --actor agy2
python3 scripts/ccf_agent_bridge.py close --id TKT-123 --actor agy \
  --reason "Integrado en la rama acordada"
```

El auditor confirma con `ack` la recepción de cada revisión antes de aprobar o
rechazar. Una revisión rechazada se reentrega bajo el mismo ID con un SHA nuevo.
El coordinador solo cierra en `DONE` después del ACK del dictamen aprobado por
parte del desarrollador.
`submit` exige ID, actor, commit que sea el HEAD actual y descendiente del HEAD
base, archivos cambiados por ese commit y al menos un check. El bridge valida
SHA y rutas; no puede
probar que el resultado del check declarado sea auténtico. El auditor debe
ejecutar sus propias verificaciones antes de aprobar.

## Operación y recuperación

```bash
python3 scripts/ccf_agent_bridge.py status
python3 scripts/ccf_agent_bridge.py get-task --id TKT-123
python3 scripts/ccf_agent_bridge.py get-submission --id TKT-123
python3 scripts/ccf_agent_bridge.py get-history --id TKT-123
python3 scripts/ccf_agent_bridge.py pause --actor agy
python3 scripts/ccf_agent_bridge.py resume --actor agy
python3 scripts/ccf_agent_bridge.py retry --event <EVENT_ID> --actor agy
python3 scripts/ccf_agent_bridge.py daemon --interval 1
```

El daemon es transporte, no autoridad. Un envío fallido queda `FAILED` y se
reintenta explícitamente; un envío interrumpido en `SENDING` se recupera
automáticamente tras 60 segundos. Cada intento tiene un token de propiedad:
un dispatcher anterior no puede registrar el resultado de un intento nuevo.
El transporte es *al menos una vez*: tras una caída puede llegar un aviso
duplicado, pero comparte ID y el ACK es idempotente. Un envío sin ACK queda
visible en `status`. Si el ACK llega mientras el daemon aún registra el envío,
se acepta sin perder la transición. El dispatcher solo entrega a paneles cuyo
proceso activo corresponde al agente esperado; si volvió a un shell, deja el
evento en `FAILED`. Los mensajes se normalizan a una línea de comentario de
shell y no incluyen notas ni hallazgos completos. El envío
directo de archivos a `.bridge/events/` ya no pertenece al flujo canónico.
Los cambios de estado usan transacciones SQLite. `get-history` y las últimas
operaciones de `status` conservan ACK, pausas, reintentos, expiraciones de lease
y resultados de cada envío con actor y fecha. Para revertir el despliegue,
se puede detener el daemon nuevo y consultar los JSON heredados, que no se
sobrescriben; las tareas creadas después de la migración solo existen en SQLite.

El campo `--actor` identifica al agente dentro del flujo local, pero no es una
autenticación criptográfica. Tres nombres distintos impiden mezclas accidentales
de rol; **no impiden la suplantación por un proceso con acceso al mismo usuario
del sistema y a la base SQLite**. La aprobación de seguridad fuerte requeriría
usuarios de sistema separados o un servicio autenticado con secretos aislados.
`agy` es además el operador de la pausa global; ese privilegio no se hereda
automáticamente de ser coordinador de un ticket. Las dependencias se conservan
en `get-task` y solo se asigna si ya están en `DONE`.
Los tickets anteriores a esta versión conservan su cierre histórico por el
revisor y no tienen HEAD base; los nuevos aplican las reglas reforzadas.

No incluir datos personales, credenciales, secretos ni información pastoral en
títulos, descripciones, notas o hallazgos. SQLite conserva estos registros sin
purga automática; su respaldo y retención deben gestionarse como datos
operativos sensibles. El directorio canónico `.bridge` y la base se restringen
a `0700` y `0600`; un directorio alternativo ya existente conserva sus permisos
y debe revisarse antes de usarlo.
