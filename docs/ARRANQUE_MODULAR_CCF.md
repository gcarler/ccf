# Arranque Modular — CCF

> **Objetivo:** dar una entrada operativa uniforme por modulo para que cualquier agente o sesión nueva arranque con el contexto correcto, sin mezclar owners ni saltarse el smoke canónico.

## 1. Regla de uso

Antes de editar código:

1. identificar el modulo visible para el usuario
2. leer su handover canónico
3. correr su smoke canónico o el de plataforma si el owner real es compartido
4. revisar el backlog vivo por IDs `PARCIAL-*` y `PEND-*`

Si el cambio toca auth, permisos, `personas.id`, `sede_id`, `apiFetch`, layouts, AG Grid o componentes UI base, el owner deja de ser el modulo visible y pasa a plataforma compartida.

## 2. Arranque por modulo

### CRM

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_CRM.md
cat /root/ccf/docs/CRM_API_CONTRACTS.md
cat /root/ccf/docs/CRM_RBAC_MATRIX.md
cat /root/ccf/docs/CRM_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_CRM_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CRM.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_crm_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:crm
npm run test:e2e:crm:deep
```

Ruta mínima:

- `/plataforma/crm/personas`

### Academy

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_ACADEMY.md
cat /root/ccf/docs/ACADEMY_API_CONTRACTS.md
cat /root/ccf/docs/ACADEMY_RBAC_MATRIX.md
cat /root/ccf/docs/ACADEMY_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_ACADEMY_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_ACADEMY.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_academy_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:academy
npm run test:e2e:academy:deep
```

Ruta mínima:

- `/plataforma/academy`

### CMS

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_CMS.md
cat /root/ccf/docs/CMS_API_CONTRACTS.md
cat /root/ccf/docs/CMS_RBAC_MATRIX.md
cat /root/ccf/docs/CMS_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_CMS_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_CMS.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:cms
npm run test:e2e:cms:deep
```

Ruta mínima:

- `/plataforma/cms`

### Messaging / Community

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_MESSAGING_COMMUNITY.md
cat /root/ccf/docs/MESSAGING_COMMUNITY_API_CONTRACTS.md
cat /root/ccf/docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md
cat /root/ccf/docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_MESSAGING_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_MESSAGING_COMMUNITY.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_messaging_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:messaging
npm run test:e2e:messaging:deep
```

Ruta mínima:

- `/plataforma/inbox/messages`

### Agenda / Calendar

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_AGENDA.md
cat /root/ccf/docs/AGENDA_API_CONTRACTS.md
cat /root/ccf/docs/SYSTEM_CALENDAR_CONTRACT.md
cat /root/ccf/docs/AGENDA_RBAC_MATRIX.md
cat /root/ccf/docs/AGENDA_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_AGENDA_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_AGENDA.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_agenda_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:agenda
npm run test:e2e:agenda:deep
```

Ruta mínima:

- `/plataforma/calendar`

### Evangelismo

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_EVANGELISMO.md
cat /root/ccf/docs/EVANGELISMO_API_CONTRACTS.md
cat /root/ccf/docs/EVANGELISMO_RBAC_MATRIX.md
cat /root/ccf/docs/EVANGELISMO_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_EVANGELISMO_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE '^\d+\. \*\*.*\[(PARCIAL|PEND)-|^\| `(PARCIAL|PEND)-' /root/ccf/docs/ESTADO_EVANGELISMO.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Smoke frontend:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
cd /root/ccf/frontend
npm run test:e2e:evangelism
npm run test:e2e:evangelism:deep
```

Ruta mínima:

- `/plataforma/evangelism`

### Proyectos

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_PROYECTOS.md
cat /root/ccf/docs/PROJECTS_API_CONTRACTS.md
cat /root/ccf/docs/PROJECTS_RBAC_MATRIX.md
cat /root/ccf/docs/PROJECTS_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_PROYECTOS_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_PROYECTOS.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_projects_quality.py
```

Smoke frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:projects
npm run test:e2e:projects:detail
```

Ruta mínima:

- `/plataforma/projects`

### Plataforma compartida

Leer primero:

```bash
cat /root/ccf/docs/ESTADO_PLATAFORMA_COMPARTIDA.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RBAC_API_UI.md
cat /root/ccf/docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md
cat /root/ccf/docs/PLATAFORMA_UI_BASE_PROTEGIDA.md
cat /root/ccf/docs/PLATAFORMA_MATRIZ_MODULAR.md
cat /root/ccf/docs/PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md
cat /root/ccf/docs/PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md
```

Backlog vivo:

```bash
grep -nE "PARCIAL-|PEND-" /root/ccf/docs/ESTADO_PLATAFORMA_COMPARTIDA.md
```

Smoke canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_platform_quality.py
```

Smoke frontend / rutas críticas:

```bash
cd /root/ccf/frontend
npm run build
npm run test:e2e:platform
```

Ruta mínima:

- `/plataforma`

## 3. Verificación de entorno base

Antes de cualquier trabajo nuevo:

```bash
cd /root/ccf
git status --short
python3 --version && node --version
```

Versiones verificadas en este host el **2026-07-16**:

- Python: **3.12.3**
- Node: **v24.15.0**

## 4. Relación con el plan modular

- Este documento no reemplaza los handovers `ESTADO_*`.
- Este documento sí cierra la necesidad operativa de una entrada uniforme por modulo.
- La profundización de contratos, gates y suites sigue viviendo en cada modulo y en `docs/PLAN_ARQUITECTURA_MODULAR_CCF.md`.
