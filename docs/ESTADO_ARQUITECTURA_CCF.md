# Estado Arquitectonico CCF

**Fecha:** 2026-06-26
**Contrato vigente:** plataforma v3 con Kernel de Personas.

## Contrato Principal

- `personas.id` es el identificador canonico de toda persona.
- `auth_users.id` usa el mismo UUID para acceso a plataforma.
- Los roles de plataforma viven en Auth v3.
- Los roles ministeriales y pastorales viven alrededor de `personas`.
- Academy activa es `academy_core`.
- Auth activa es `auth_v3`.

## Base de Datos

Estado verificado en produccion:

- No existen columnas inversas entre personas y autenticacion.
- Las personas importadas viven en `personas`.
- Los accesos viven en `auth_users`.
- El administrador `gscarlosernesto@gmail.com` existe con rol `ADMINISTRADOR`.

## Reglas de Continuidad

- No reintroducir tablas paralelas de personas.
- No crear rutas nuevas con identidad entera para personas.
- No sostener scripts manuales de migracion historica en el repo.
- No mantener documentos que declaren pendientes ya retirados.

## Gate de Arquitectura

Antes de declarar una limpieza como terminada:

```bash
rg -n "ForeignKey\\(\"users\\.id\"\\)|personas\\.user_id|models\\.Persona|models_personas|backend\\.auth" backend docs scripts REGLAS.md
source venv/bin/activate
python -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_smoke.py
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:3000/plataforma
```
