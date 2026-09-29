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

Cada ticket tiene exactamente un desarrollador (`owner`) y un auditor distinto
(`reviewer`). El orquestador asigna; el desarrollador entrega; el auditor verifica.
Backend y frontend pueden tener tickets diferentes, con dependencia explícita y
worktrees separados. Solo se permite una tarea activa por desarrollador.
Dos tareas activas tampoco pueden compartir la misma raíz de worktree.

`ASSIGNED → WORKING → AWAITING_AUDIT → APPROVED → DONE`

Si la auditoría falla: `AWAITING_AUDIT → REVISION_REQUIRED → AWAITING_AUDIT`.
`CANCELLED` cierra un ticket duplicado o abandonado con motivo registrado.
`approve` nunca crea la siguiente tarea. `close` da el cierre terminal.

## Uso

```bash
python3 scripts/ccf_agent_bridge.py assign --id TKT-123 --module academy \
  --title "Vista de cohorte" --desc "Implementar la vista aprobada" \
  --owner codex --reviewer agy --worktree /root/ccf \
  --criteria "tsc limpio;contrato API validado"
```

El daemon deja el evento en `SENT` después de que tmux acepta el texto. El agente
ejecuta el comando `ack` incluido en el mensaje; entonces pasa a `ACKED` y la
tarea a `WORKING`. `SENT` no significa que el modelo haya leído el mensaje.

```bash
python3 scripts/ccf_agent_bridge.py submit --id TKT-123 --actor codex \
  --commit <SHA_COMPLETO_DE_40_CARACTERES> --files frontend/src/app/plataforma/academy/page.tsx \
  --check "tsc PASS" --notes "Vista implementada y verificada"
python3 scripts/ccf_agent_bridge.py approve --id TKT-123 --actor agy \
  --score 100 --evidence "SHA revisado; tests y contrato comprobados"
python3 scripts/ccf_agent_bridge.py close --id TKT-123 --actor agy \
  --reason "Integrado en la rama acordada"
```

El auditor confirma con `ack` la recepción de cada revisión antes de aprobar o
rechazar. Una revisión rechazada se reentrega bajo el mismo ID con un SHA nuevo.
`submit` exige ID, actor, commit existente, lista de archivos y al menos un check.
El bridge registra la evidencia declarada; el auditor debe verificarla.

## Operación y recuperación

```bash
python3 scripts/ccf_agent_bridge.py status
python3 scripts/ccf_agent_bridge.py get-task --id TKT-123
python3 scripts/ccf_agent_bridge.py get-submission --id TKT-123
python3 scripts/ccf_agent_bridge.py pause --actor agy
python3 scripts/ccf_agent_bridge.py resume --actor agy
python3 scripts/ccf_agent_bridge.py retry --event <EVENT_ID>
python3 scripts/ccf_agent_bridge.py daemon --interval 1
```

El daemon es transporte, no autoridad. Un envío fallido queda `FAILED` y se
reintenta explícitamente; un envío sin ACK queda visible en `status`. El envío
directo de archivos a `.bridge/events/` ya no pertenece al flujo canónico.
Los cambios de estado usan transacciones SQLite. Para revertir el despliegue,
se puede detener el daemon nuevo y consultar los JSON heredados, que no se
sobrescriben; las tareas creadas después de la migración solo existen en SQLite.

El campo `--actor` identifica al agente dentro del flujo local, pero no es una
autenticación criptográfica. El control de acceso fuerte requeriría identidades
de proceso o credenciales separadas por agente.
