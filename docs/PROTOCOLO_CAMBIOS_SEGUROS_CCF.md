# Protocolo de Cambios Seguros CCF

**Actualizado:** 2026-06-26
**Estado:** documento operativo vigente

Este protocolo protege la plataforma mientras se mantiene una arquitectura canonica: personas por UUID, Auth v3, Academy en tablas `academy_*` y aislamiento por sede.

## Autoridad

1. `REGLAS.md`
2. `docs/ESTADO_ARQUITECTURA_CCF.md`
3. `AGENTS_FRONTEND.md`
4. `docs/ESTANDARES_DESARROLLO.md`

Si dos documentos contradicen estos contratos, se corrige el documento antes de cambiar codigo.

## Contratos No Negociables

- `personas.id` es la identidad de personas en todo el sistema.
- `auth_users.id` debe corresponder al UUID de la persona.
- No se recrean columnas inversas entre personas y autenticacion.
- Toda lectura o escritura pastoral, ministerial o administrativa debe respetar `sede_id`.
- Las fechas persistidas usan `DateTime(timezone=True)` o equivalente UTC.
- Los borrados de entidades protegidas se hacen por estado o `deleted_at`.
- Las APIs nuevas no aceptan identidades enteras para representar personas.

## Flujo de Cambio

1. Ejecutar `git status --short`.
2. Leer el modelo, schema, CRUD y endpoint afectados.
3. Clasificar el cambio:
   - docs/configuracion;
   - frontend;
   - backend/API;
   - datos/migracion.
4. Editar la capa minima que posee el problema.
5. Verificar antes de ampliar el alcance.
6. Registrar comandos ejecutados y riesgo residual.

## Reglas de Edicion

- No revertir cambios locales de otro agente.
- No usar `git reset --hard` ni restauraciones globales.
- No mezclar frontend, backend y migraciones si no son inseparables.
- No crear wrappers o aliases para sostener nombres antiguos.
- Si una ruta historica no tiene consumidor vivo, se elimina en vez de duplicarla.
- Si una migracion de datos es necesaria, debe tener `upgrade`, `downgrade` y una prueba proporcional.

## Verificacion Minima

Solo docs:

```bash
rg -n "archivo_o_referencia_eliminada" docs REGLAS.md PLAN_DE_TRABAJO.md
```

Backend/API:

```bash
source venv/bin/activate
python -m py_compile backend/app.py
python -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_smoke.py
```

Migraciones:

```bash
source venv/bin/activate
alembic upgrade head
```

Frontend:

```bash
cd frontend
npm run typecheck
```

Runtime:

```bash
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:3000/plataforma
```

## Cierre

Un cambio queda cerrado cuando el diff propio esta acotado, las pruebas proporcionales pasan y no quedan referencias activas al contrato retirado.
