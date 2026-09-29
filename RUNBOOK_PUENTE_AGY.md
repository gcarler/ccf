# Runbook del Puente de Agentes CCF

El protocolo vigente está en [docs/PUENTE_AGENTES_CCF.md](docs/PUENTE_AGENTES_CCF.md).
Este archivo se conserva para los operadores que usaban el runbook anterior.

El puente mantiene una tarea por desarrollador en `.bridge/bridge.sqlite3`.
La entrega requiere ID de ticket, SHA completo, archivos y verificaciones.
El auditor independiente confirma cada entrega antes de dictaminar; `approve`
no asigna otra tarea y `close` termina el ciclo en `DONE`.

Comando de estado:

```bash
python3 scripts/ccf_agent_bridge.py status
```

Los archivos `.bridge/state.json`, `.bridge/current_task.json` y
`.bridge/codex_submission.txt` son históricos. Las sesiones locales que siguen
ejecutando `scripts/ccf_bridge.py` llegan al mismo registro SQLite mediante
el adaptador de compatibilidad.
