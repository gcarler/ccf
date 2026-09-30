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
2. Confirmar con `health --json` un respaldo reciente en `.bridge/backups/`.
   Si hace falta, `python3 scripts/ccf_agent_bridge.py backup` crea uno
   consistente mediante SQLite Backup API y comprueba `integrity_check`; no
   copiar solo el archivo principal cuando SQLite opera con WAL.
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

## Restauración manual de respaldo

La restauración es una operación de recuperación, no una reversión rutinaria:
puede descartar tareas o eventos posteriores al respaldo. Requiere aprobación
del operador responsable y reconciliar primero el trabajo posterior.

1. Pausar asignaciones (`pause --actor agy`) y detener tanto
   `ccf-agent-bridge` como el daemon heredado. Confirmar que no hay procesos del
   puente escribiendo en SQLite. No copiar ni reemplazar la base mientras haya
   un proceso activo.
2. Elegir explícitamente un archivo de `.bridge/backups/` y validar su
   integridad:

   ```bash
   python3 -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); print(c.execute("PRAGMA integrity_check").fetchone()[0]); c.close()' \
     .bridge/backups/<archivo-elegido.sqlite3>
   ```

   El resultado debe ser `ok`. Si no lo es, no restaurarlo.
3. Con todos los procesos detenidos, conservar la base actual con nombre
   fechado y revisar que no queden archivos `bridge.sqlite3-wal` o
   `bridge.sqlite3-shm`. Si queda un WAL, no continuar: reabrir/cerrar SQLite
   limpiamente o pedir asistencia para no perder transacciones confirmadas.
4. Instalar el respaldo validado como `.bridge/bridge.sqlite3`, con modo
   `0600`, y repetir `PRAGMA integrity_check` sobre esa ruta. Mantener la copia
   previa hasta verificar `health --json`, `status`, la cola y una entrega/ACK
   controlada. Solo entonces reanudar el servicio y las asignaciones.

La salud del proceso y la entrega de eventos son dimensiones diferentes:
PM2 reinicia caídas, mientras `health` expone retrasos, fallos y tickets
estancados que requieren intervención humana.

Los archivos `.bridge/state.json`, `.bridge/current_task.json` y
`.bridge/codex_submission.txt` son históricos. Las sesiones locales que siguen
ejecutando `scripts/ccf_bridge.py` llegan al mismo registro SQLite mediante
el adaptador de compatibilidad.
