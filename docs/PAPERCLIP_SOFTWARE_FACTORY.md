# Paperclip Software Factory (PLE)

## Objetivo

Convertir la empresa `PLE` en una fabrica de software operando con flujo continuo:

`idea -> backlog -> build -> QA -> release -> soporte`

## Base ya configurada

- Paperclip instalado y operativo en `http://127.0.0.1:3100`
- Adapter local `codex` instalado y autenticado
- Empresa activa: `PLE`

## Backlog semilla creado

- `PLE-2` Fabrica de software: sistema operativo de entrega
- `PLE-3` Definir organigrama de agentes para software factory
- `PLE-4` Diseñar pipeline SDLC con quality gates
- `PLE-5` Implementar framework de estimacion y priorizacion
- `PLE-6` Crear playbooks de entrega y soporte
- `PLE-7` Crear tablero de metricas operativas

Nota: nombre y prefijo tecnico alineados en `PLE`.

## Estructura recomendada de agentes

- CEO: estrategia, priorizacion y presupuesto
- CTO: arquitectura, calidad tecnica y decisiones de stack
- Product Manager: discovery, alcance y criterios de aceptacion
- Tech Lead: diseno tecnico y coordinacion de entrega
- Backend Engineer: APIs, datos, seguridad
- Frontend Engineer: UX, accesibilidad, performance
- QA Engineer: pruebas funcionales/regresion/e2e
- DevOps Engineer: CI/CD, despliegues, observabilidad
- Support Engineer: incidentes, hotfix y postmortems

## Gates de calidad minimos

Por cada ticket de implementacion:

1. lint (critico) en verde
2. typecheck en verde
3. tests unitarios/integracion en verde
4. build en verde
5. escaneo de seguridad sin high/critical
6. evidencia de release en ticket

## KPIs operativos

- Lead time por ticket
- Cycle time por etapa
- Throughput semanal
- Defectos por release
- MTTR
- Rollback rate
- Cumplimiento SLA

## Arranque rapido diario

1. Ejecutar `iniciar-paperclip.bat`
2. Revisar tablero y estado de `PLE-2..PLE-7` (backlog de PLE)
3. Limitar WIP activo
4. Cerrar bloqueos primero
5. Publicar resumen diario (riesgos, avances, siguiente entrega)

## Arquitectura A/B (continuidad)

- Equipo A (principal): agentes con `codex_local` y modelos GPT
- Equipo B (respaldo): agentes espejo con `codex --oss --local-provider ollama`
- Regla de failover: si A falla por auth/rate limit/costo, reasignar ticket al agente B del mismo rol

## Asignacion sugerida por rol

- CEO / PM: A=`o3` | B=`qwen3:8b`
- CTO / Tech Lead: A=`gpt-5.4` | B=`qwen3:8b`
- Backend / Frontend / DevOps: A=`gpt-5.3-codex` | B=`qwen2.5-coder:7b`
- QA: A=`o4-mini` | B=`qwen2.5-coder:7b`
- Support: A=`gpt-5-mini` | B=`qwen3:8b`

## Modelos locales validados en esta maquina

- `qwen3:8b` (funciona con `codex --oss`)
- `qwen2.5-coder:7b` (funciona con `codex --oss`)
- `qwen3.5:cloud` (disponible sin descarga pesada, pero con alta demanda intermitente)

## Comandos utiles

Instalar modelos base de respaldo:

```bash
ollama pull qwen3:8b
ollama pull qwen2.5-coder:7b
```

Pruebas de humo de Codex OSS:

```bash
codex exec --oss --local-provider ollama -m qwen3:8b "Responde exactamente: OK"
codex exec --oss --local-provider ollama -m qwen2.5-coder:7b "Responde exactamente: OK"
```

## Playbook corto: si A falla -> usar B

Disparadores de failover a B:

- timeout/reintentos en proveedor A
- errores de cuota/rate limit
- errores de autenticacion

Comandos exactos por rol:

- CEO/PM (A: `o3` -> B: `qwen3:8b`)
```bash
codex exec -m o3 "<tarea_estrategia_o_prd>"
codex exec --oss --local-provider ollama -m qwen3:8b "<tarea_estrategia_o_prd>"
```

- CTO/Tech Lead (A: `gpt-5.4` -> B: `qwen3:8b`)
```bash
codex exec -m gpt-5.4 "<tarea_arquitectura_o_revision>"
codex exec --oss --local-provider ollama -m qwen3:8b "<tarea_arquitectura_o_revision>"
```

- Backend/Frontend/DevOps (A: `gpt-5.3-codex` -> B: `qwen2.5-coder:7b`)
```bash
codex exec -m gpt-5.3-codex "<tarea_coding>"
codex exec --oss --local-provider ollama -m qwen2.5-coder:7b "<tarea_coding>"
```

- QA (A: `o4-mini` -> B: `qwen2.5-coder:7b`)
```bash
codex exec -m o4-mini "<plan_pruebas_o_regresion>"
codex exec --oss --local-provider ollama -m qwen2.5-coder:7b "<plan_pruebas_o_regresion>"
```

- Support (A: `gpt-5-mini` -> B: `qwen3:8b`)
```bash
codex exec -m gpt-5-mini "<triage_o_respuesta_incidente>"
codex exec --oss --local-provider ollama -m qwen3:8b "<triage_o_respuesta_incidente>"
```

Nota operativa:

- `qwen3.5:cloud` se detecta disponible, pero en esta fecha no paso prueba por alta demanda del servicio.
