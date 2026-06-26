# Estado de Trabajo - Plataforma CCF

**Actualizado:** 2026-06-26
**Estado operativo:** plataforma v3 en produccion con identidad canonica por `personas.id`.

Este documento reemplaza planes anteriores de saneamiento. La fuente vigente para cambios es:

1. `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`
2. `REGLAS.md`
3. `docs/ESTADO_ARQUITECTURA_CCF.md`

## Stack en Produccion

| Componente | Tecnologia |
|---|---|
| Backend | FastAPI + SQLAlchemy |
| Frontend | Next.js |
| Base de datos | PostgreSQL |
| Proxy | nginx |
| Deploy | VPS directo con PM2 |

## Contratos Canonicos

- La persona se identifica por UUID en `personas.id`.
- `auth_users.id` comparte UUID con `personas.id`.
- No se recrean columnas inversas entre personas y autenticacion.
- No se introducen tablas paralelas para miembros, estudiantes, lideres o usuarios ministeriales.
- La plataforma usa rutas v3 y modulos actuales registrados en `backend/app.py`.
- Academy activa es `academy_core`; Auth activa es `auth_v3`.
- Los datos pastorales y ministeriales se filtran por `sede_id`.

## Estado de Saneamiento

| Area | Estado |
|---|---|
| Base de datos de personas | Canonica en `personas` |
| Acceso plataforma | `auth_users.id == personas.id` |
| Rol administrador | Gestionado en roles v3 |
| Scripts de migracion historica manual | Retirados |
| Planes antiguos de retiro por lotes | Retirados |
| Documentacion rectora | Consolidada en protocolo actual |

## Comandos Clave

```bash
./startccf
./stopccf

source venv/bin/activate
alembic upgrade head
python -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py
```

## Regla de Cierre

Una entrega arquitectonica solo se considera cerrada cuando:

- el contrato canonico queda expresado en codigo, datos y documentacion;
- no queda una ruta alternativa antigua registrada como flujo vigente;
- las pruebas proporcionales pasan;
- la plataforma responde por HTTP despues del cambio.
