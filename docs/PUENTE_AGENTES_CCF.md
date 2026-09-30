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
`enqueue` guarda tareas `QUEUED` sin reservar agente ni worktree; el daemon las
activa por prioridad/FIFO cuando sus dependencias estén `DONE` y el desarrollador
y el worktree estén libres. `assign` conserva la asignación inmediata.

La automatización cubre la cola, el enrutamiento de avisos, sus reintentos,
alertas de fallos, los respaldos y la recuperación del proceso. Un coordinador
todavía define la tarea, su dueño, auditor y criterios; el auditor ejecuta su
verificación y dicta. El puente no inventa requisitos, no puntúa la calidad,
no aprueba entregas ni integra o publica ramas por su cuenta. Esa separación
queda reflejada como transición y actor en el historial de cada ticket.

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
python3 scripts/ccf_agent_bridge.py health --json
python3 scripts/ccf_agent_bridge.py get-task --id TKT-123
python3 scripts/ccf_agent_bridge.py get-submission --id TKT-123
python3 scripts/ccf_agent_bridge.py get-history --id TKT-123
python3 scripts/ccf_agent_bridge.py pause --actor agy
python3 scripts/ccf_agent_bridge.py resume --actor agy
python3 scripts/ccf_agent_bridge.py retry --event <EVENT_ID> --actor agy
python3 scripts/ccf_agent_bridge.py daemon --interval 1
python3 scripts/ccf_agent_bridge.py enqueue --id TKT-124 --module academy \
  --title "Vista de resultados" --desc "Implementar la pantalla acordada" \
  --actor agy --owner agy2 --reviewer codex --worktree /root/ccf-academy \
  --depends-on TKT-123 --priority 20 --criteria "contrato API;tsc limpio"
```

El daemon tiene un heartbeat cada cinco segundos; `health --json` informa
`HEALTHY` o `DEGRADED` y devuelve un código distinto de cero si el proceso no
latea, hay errores de entrega, avisos agotados o ACK/leases vencidos. PM2
supervisa el proceso y lo reinicia si cae. El daemon es transporte y activador
de cola, no autoridad de auditoría. `SENT` significa que tmux aceptó el aviso,
no que el modelo lo leyó. Si no llega ACK en 120 segundos, se reenvía el mismo
evento; un ACK tardío sigue siendo válido e idempotente. Una entrega fallida
reintenta automáticamente con esperas de 5, 15, 45, 120 y 300 segundos, hasta
seis intentos. Al agotarse, el evento pasa a `DEAD` y se crea una sola alerta
`BRIDGE_ALERT` al coordinador; las alertas no se escalan recursivamente. El
coordinador puede inspeccionar y reintentar eventos `DEAD` con `retry`. El
coordinador, desarrollador y auditor deben ser nombres de agentes con un panel
tmux registrado. `daemon --once` ejecuta un ciclo manual y no escribe un
heartbeat que simule un servicio continuo. El daemon comprueba el respaldo al
iniciar y crea uno si el último tiene 24 horas o más; luego repite esa
comprobación cada 60 segundos. Conserva los 14 respaldos más
recientes en `.bridge/backups/` con permisos `0700`/`0600`; `health --json`
marca la base degradada si no existe un respaldo reciente. `backup` crea uno
manualmente y verifica `integrity_check`; la recuperación se prueba abriendo
la copia con SQLite Backup API antes de reanudar el dispatcher. Estas copias
permanecen en el mismo volumen del host: protegen frente a corrupción lógica,
pero no frente a pérdida del disco/host ni sustituyen la réplica externa del
respaldo de producción.
Una tarea activa sin transición durante siete días aparece en `stalled_tasks`,
degrada `health` y genera una sola alerta al coordinador para ese periodo de
inactividad; una transición posterior reinicia el plazo.

Un envío interrumpido en `SENDING` recupera automáticamente la entrega al
vencer el lease de 60 segundos. Cada intento tiene un token de propiedad:
un dispatcher anterior no puede registrar el resultado de un intento nuevo.
El transporte es *al menos una vez*: tras una caída puede llegar un aviso
duplicado, pero comparte ID y el ACK es idempotente. Un envío sin ACK queda
visible en `status`. Si el ACK llega mientras el daemon aún registra el envío,
se acepta sin perder la transición. El dispatcher solo entrega a paneles cuyo
proceso activo corresponde al agente esperado; si volvió a un shell, deja el
evento en `FAILED`. Los mensajes se normalizan a una línea de comentario de
shell y no incluyen notas ni hallazgos completos. El envío
directo de archivos a `.bridge/events/` ya no pertenece al flujo canónico.
Los cambios de estado usan transacciones SQLite. `get-history` presenta una
línea temporal cronológica unificada de transiciones de estado y operaciones
(ACK, pausas, reintentos, expiraciones de lease y resultados de cada envío),
con tipo de registro, actor y fecha. Los errores habituales de transporte se
redactan antes de persistirse o aparecer en logs; esto no sustituye la regla de
no enviar secretos ni datos sensibles en entradas o notas. Tras reintentar
manualmente un evento muerto, un nuevo agotamiento vuelve a generar una alerta
al coordinador. Para revertir el despliegue,
se puede detener el daemon nuevo y consultar los JSON heredados, que no se
sobrescriben; las tareas creadas después de la migración solo existen en SQLite.

El campo `--actor` identifica al agente dentro del flujo local, pero no es una
autenticación criptográfica. Tres nombres distintos impiden mezclas accidentales
de rol; **no impiden la suplantación por un proceso con acceso al mismo usuario
del sistema y a la base SQLite**. La aprobación de seguridad fuerte requeriría
usuarios de sistema separados o un servicio autenticado con secretos aislados.
`agy` es además el operador de la pausa global; ese privilegio no se hereda
automáticamente de ser coordinador de un ticket. Las dependencias se conservan
en `get-task`; `assign` exige que estén en `DONE`, y `enqueue` espera su
finalización. `status` expone cada tarea en cola y su razón de bloqueo para que
el orden de activación sea auditable.
Los tickets anteriores a esta versión conservan su cierre histórico por el
revisor y no tienen HEAD base; los nuevos aplican las reglas reforzadas.

No incluir datos personales, credenciales, secretos ni información pastoral en
títulos, descripciones, notas o hallazgos. SQLite conserva estos registros sin
purga automática; su respaldo y retención deben gestionarse como datos
operativos sensibles. El directorio canónico `.bridge` y la base se restringen
a `0700` y `0600`; un directorio alternativo ya existente conserva sus permisos
y debe revisarse antes de usarlo.
