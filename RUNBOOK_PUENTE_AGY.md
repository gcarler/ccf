# Runbook del Puente de Agentes CCF

El protocolo vigente está en [docs/PUENTE_AGENTES_CCF.md](docs/PUENTE_AGENTES_CCF.md).
Este archivo se conserva para los operadores que usaban el runbook anterior.

El puente mantiene una tarea por desarrollador en `.bridge/bridge.sqlite3`.
La entrega requiere ID de ticket, SHA completo, archivos y verificaciones.
El auditor independiente confirma cada entrega antes de dictaminar; el
coordinador, distinto del auditor y del desarrollador, asigna y cierra. `approve`
no asigna otra tarea y `close` termina el ciclo en `DONE`.

Comando de estado:

```bash
python3 scripts/ccf_agent_bridge.py status
python3 scripts/ccf_agent_bridge.py health --json
```

## Publicación y relevo del daemon

El proceso supervisado se declara como `ccf-agent-bridge` en
`ecosystem.config.cjs`; PM2 debe mantener exactamente una instancia. La
configuración versionada no se activa por editar el archivo. Primero hay que
integrar y verificar el código en `/root/ccf`, con los gates de Git normales.
No arrancar el proceso nuevo mientras el daemon heredado siga ejecutándose.

1. Consultar `status` y `health --json`; identificar tickets activos, eventos
   pendientes y las sesiones tmux de sus destinatarios. Pausar nuevas
   asignaciones con `pause --actor agy` durante el relevo. No cerrar ni
   cancelar tickets para despejar la cola.
2. Crear un respaldo consistente de `.bridge/bridge.sqlite3` usando la API
   SQLite de backup (no copiar solo el archivo en modo WAL). Guardar el
   respaldo fuera del checkout y comprobar que puede abrirse.
3. Detener el PID exacto del proceso heredado `ccf_tmux_daemon.py`; verificar
   con `pgrep -af` que no queda otro dispatcher. Arrancar únicamente el app
   nuevo: `pm2 start /root/ccf/ecosystem.config.cjs --only ccf-agent-bridge`.
   Consultar `pm2 list`, `pm2 logs ccf-agent-bridge --lines 30 --nostream` y
   `health --json`. Persistir con `pm2 save` solo tras comprobar estabilidad.
4. Reanudar con `resume --actor agy`. Probar un ticket de bajo riesgo hasta
   ACK, revisión y cierre antes de considerar concluida la migración.

Si falla el proceso nuevo, pausarlo o detenerlo antes de arrancar el adaptador
heredado. SQLite conserva tickets y eventos; no restaurar un respaldo sobre
trabajo posterior sin reconciliarlo. El transporte es *al menos una vez*, por
lo que un relevo entre envío y ACK puede repetir un aviso con el mismo ID.
La salud del proceso y la entrega de eventos son dimensiones diferentes:
PM2 reinicia caídas, mientras `health` expone retrasos, fallos y tickets
estancados que requieren intervención humana.

Los archivos `.bridge/state.json`, `.bridge/current_task.json` y
`.bridge/codex_submission.txt` son históricos. Las sesiones locales que siguen
ejecutando `scripts/ccf_bridge.py` llegan al mismo registro SQLite mediante
el adaptador de compatibilidad.
