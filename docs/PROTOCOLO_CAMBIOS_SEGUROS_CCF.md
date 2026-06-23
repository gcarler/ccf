# Protocolo de Cambios Seguros CCF

**Fecha:** 2026-06-04  
**Estado:** Documento operativo vigente  
**Objetivo:** Permitir corregir la plataforma a la luz de `REGLAS.md`, `docs/ESTANDARES_DESARROLLO.md` y `AGENTS_FRONTEND.md` sin tumbar funcionalidad existente.
**Capa operativa de agentes:** `docs/AGENTES_OPERATIVOS_CCF.md`

---

## 1. Principio Rector

La plataforma CCF tiene reglas arquitectonicas correctas, pero tambien tiene deuda compat activa. Por lo tanto:

> Ninguna regla ideal se corrige de forma masiva si el cambio requiere migraciones, renombrados amplios, cambios de identidad, cambios de rutas o reescrituras de auth/RBAC.

Este documento existe por una razon operativa concreta: la plataforma ya se ha caido varias veces al aplicar correcciones amplias que parecian alineadas con las reglas, pero que tocaron contratos vivos sin puntos de control suficientes. Desde ahora el trabajo se hace por desarrollo puntuado: un cambio pequeno, una verificacion, un registro, y solo despues el siguiente cambio.

Si no se puede demostrar que la plataforma sigue levantando despues de un punto, no se continua con el siguiente.

Antes de tocar codigo se debe clasificar cada hallazgo como:

| Categoria | Significado | Accion permitida |
|---|---|---|
| Bloqueante operativo | Rompe seguridad, sede_id, login, build, arranque o datos | Corregir en microcambio con pruebas |
| Correccion segura | Cambio local sin migracion ni contrato externo | Corregir con prueba enfocada |
| Deuda conocida | Incumple regla ideal pero esta acoplado a DB/API/UI compat | Documentar, no tocar sin plan |
| Compat protegido | Existe para compatibilidad activa | No renombrar ni eliminar |
| Contradiccion documental | Reglas/documentos se contradicen | Corregir documento o test antes del codigo |

---

## 2. Orden de Autoridad de Documentos

Mientras no se consoliden los manuales, usar este orden:

1. `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md` para decidir como cambiar sin romper.
2. `REGLAS.md` como fuente principal de arquitectura backend/DB.
3. `AGENTS_FRONTEND.md` como complemento frontend.
4. `docs/ESTANDARES_DESARROLLO.md` como referencia historica, no como fuente bloqueante si contradice los anteriores.

Si dos documentos discrepan, no corregir codigo todavia. Primero registrar la contradiccion y proponer una decision canonica.

---

## 3. No Tocar Sin Plan de Migracion

Estas areas no deben modificarse como "fix rapido":

- PK `Integer` a UUID en tablas existentes.
- FKs compat a `users.id`.
- Columnas compat en `personas` como `church_role`, `membership_type`, `user_id`.
- Rutas existentes `members`, `academy`, `evangelism`, `projects`.
- Alias compat como `Member = Persona`, `CellGroup = GrupoEvangelismo`.
- Auth v1/v2/v3, refresh tokens, cookies o `sessionStorage`.
- `backend/models.py` como barrel de compatibilidad.
- Migraciones Alembic que cambien tipos de PK/FK.
- Eliminacion de tablas, columnas o relaciones compat.

Estas areas solo se tocan con:

1. Inventario de dependencias.
2. Migracion reversible o plan de rollback.
3. Tests antes/despues.
4. Smoke test funcional.
5. Aprobacion explicita.

---

## 4. Cambios Permitidos Como Microfix

Se pueden corregir en cambios pequenos y aislados:

- Consultas internas que claramente olvidan filtrar por `sede_id`, siempre que el usuario autenticado ya tenga sede disponible.
- Endpoints que aceptan `sede_id` del cliente y pueden reemplazarlo por `require_user_sede_id()` o helper equivalente sin cambiar contrato publico critico.
- `fetch()` directo en frontend cuando puede reemplazarse por `apiFetch()` sin alterar flujo.
- Textos visibles de UI que digan "miembro" cuando la pantalla se refiere a personas del Kernel.
- Uso accidental de `indigo`, `violet`, `purple` en UI.
- `datetime.utcnow()` en codigo nuevo o local, reemplazable por `datetime.now(timezone.utc)`.
- `db.delete()` en una tabla que ya tenga `deleted_at` o estado activo/inactivo y donde el cambio sea local.

Cada microfix debe tener una sola intencion. No mezclar frontend, backend y migraciones en el mismo cambio salvo que sea estrictamente necesario.

---

## 5. Contradicciones Actuales a Resolver Antes de Corregir Codigo

### 5.1 `apiFetch('/api/...')` vs `apiFetch('/...')`

`frontend/src/lib/api.ts` define `DEFAULT_API_URL = "/api"` y concatena el path. Por tanto el uso canonico debe ser:

```ts
apiFetch("/crm/personas")
```

No usar:

```ts
apiFetch("/api/crm/personas")
```

Excepcion: `fetch("/api/...")` directo solo en rutas publicas o endpoints Next internos donde no se use `apiFetch`, y debe justificarse.

### 5.2 JSON vs JSONB

Mientras los tests usen SQLite, la regla operativa es:

```python
Column(JSON)
```

No introducir `JSONB` nuevo en modelos. Si produccion requiere JSONB, debe hacerse con una decision explicita de arquitectura y tests adaptados.

### 5.3 Rutas ingles/espanol

El repo actual usa mayoritariamente:

- `/plataforma/academy`
- `/plataforma/evangelism`
- `/plataforma/projects`

No migrar rutas a `/academia`, `/evangelismo` o `/proyectos` sin plan de redireccion, navegacion y QA.

### 5.4 "Members" en codigo vs "personas" en UI

Regla inmediata:

- UI visible: usar "personas", "integrantes" o "participantes".
- Codigo compat: no renombrar rutas/variables/archivos `members` sin plan.

---

## 6. Protocolo Obligatorio Antes de Editar

Antes de cualquier cambio:

1. Ejecutar `git status --short`.
2. Identificar archivos con cambios ajenos.
3. No tocar archivos modificados por otro actor salvo que el cambio sea necesario y se lea cuidadosamente.
4. Declarar el alcance exacto del microcambio.
5. Confirmar si el cambio requiere migracion o toca contrato publico.

Si hay cambios locales en el mismo archivo, detenerse o pedir confirmacion antes de editar.

---

## 6.1 Punto Cero: Baseline de Plataforma

Antes de corregir codigo se debe capturar el estado real de arranque. El objetivo no es arreglar todo en este paso; es saber si se parte de una plataforma estable o de una plataforma ya rota.

Registrar:

- Rama actual.
- `git status --short`.
- Comandos ejecutados.
- Resultado exacto: PASS, FAIL o NO EJECUTADO.
- Error principal si falla.

Baseline minimo:

```bash
python3 -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py
```

Si el entorno usa un virtualenv especifico, usar el binario explicito del proyecto:

```bash
/root/ccf/venv/bin/python -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

Arranque local, cuando el cambio pueda afectar runtime:

```bash
./startccf
```

`./startccf` deja backend y frontend corriendo en segundo plano. Al terminar la verificacion manual o HTTP, cerrar con:

```bash
./stopccf
```

Verificacion HTTP minima:

```bash
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/api/system/health
```

Si el baseline falla antes de editar, el primer trabajo es clasificar el fallo como deuda preexistente o bloquear el cambio. No se deben mezclar correcciones nuevas con fallos de arranque no diagnosticados.

---

## 6.2 Desarrollo Puntuado

Todo cambio se divide en puntos. Cada punto debe poder revertirse sin arrastrar el resto.

| Punto | Nombre | Regla |
|---|---|---|
| P0 | Baseline | Medir estado antes de tocar codigo |
| P1 | Inventario | Leer archivos afectados y contratos relacionados |
| P2 | Microcambio | Editar solo lo necesario para una intencion |
| P3 | Verificacion local | Ejecutar prueba minima proporcional |
| P4 | Arranque | Confirmar que backend/frontend levantan si aplica |
| P5 | Registro | Documentar resultado, riesgo residual y siguiente punto |

No se permite pasar de P2 a otro cambio si P3 falla. Si P3 falla, hay solo tres opciones:

1. Corregir el fallo dentro del mismo alcance.
2. Revertir el microcambio.
3. Marcar BLOQUEADO y pedir decision.

No se permite acumular varios cambios rotos para "arreglarlos al final".

---

## 6.3 Reglas de Rollback

Cada punto debe tener salida clara.

Antes de editar:

```bash
git diff -- archivo_afectado
```

Despues de editar y antes de seguir:

```bash
git diff -- archivo_afectado
```

Si el cambio rompe build, typecheck, healthcheck o arranque, se debe identificar el archivo exacto y decidir:

- revertir solo el microcambio propio;
- ajustar dentro del mismo microcambio;
- dejar el cambio sin declarar terminado solo si el usuario aprueba continuar.

Prohibido usar comandos destructivos globales como `git reset --hard` o restaurar archivos completos con cambios ajenos.

---

## 6.4 Bitacora Obligatoria por Punto

Cada punto de trabajo debe dejar una entrada breve en la respuesta o en el documento de ejecucion del cambio:

```json
{
  "punto": "P2",
  "objetivo": "Reemplazar fetch directo por apiFetch en pantalla X",
  "archivos": ["frontend/src/..."],
  "contratos_revisados": ["apiFetch", "ruta backend"],
  "resultado": "PASS / FAIL / BLOQUEADO",
  "verificacion": "npm run typecheck",
  "rollback": "Revertir diff local del archivo X",
  "riesgo_residual": "Ninguno / descripcion"
}
```

Sin bitacora no hay cierre del punto.

---

## 7. Protocolo de Verificacion

Cada cambio debe cerrar con verificacion proporcional:

### Backend

Minimo:

```bash
python3 -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_reglas_plataforma.py
```

Para cambio de endpoint, agregar el test especifico del modulo.

### Frontend

Minimo para cambio local:

```bash
npm run typecheck
```

Si el cambio toca rutas, layout, auth o API client:

```bash
npm run build
```

### Plataforma en ejecucion

Si el cambio puede afectar uso real:

- Backend `/healthz`.
- Backend `/api/system/health`.
- Login o `/api/auth/me` segun el flujo afectado.
- Pagina principal del modulo afectado.
- Un request del endpoint modificado.

No declarar terminado si no se pudo verificar. Reportar explicitamente lo no verificado.

---

## 7.1 Matriz de Verificacion por Tipo de Cambio

| Tipo de cambio | Verificacion minima | Verificacion de arranque |
|---|---|---|
| Solo docs | No requiere build; revisar formato y enlaces | No aplica |
| Frontend UI local | `npm run typecheck` | `npm run build` si toca rutas/layout/API |
| Frontend API client | `npm run typecheck` + `npm run build` | Abrir ruta o hacer request afectado |
| Backend CRUD/API | `pytest` del modulo + `tests/test_smoke.py` | `/healthz` y endpoint afectado |
| Auth/RBAC/session | Tests auth + smoke + build frontend | Login o `/api/auth/me` |
| DB/modelos/migracion | Test estructural + migracion en entorno controlado | Health backend despues de migrar |
| Rutas publicas | Build frontend + smoke de rutas | HTTP 200 de rutas afectadas |

Si una verificacion no se puede ejecutar por sandbox, dependencias o entorno, se reporta como NO EJECUTADO con la razon exacta. No se reemplaza por suposiciones.

---

## 8. Orden Seguro de Correccion

Prioridad recomendada:

1. Corregir contradicciones documentales y tests de reglas que bloquean cambios seguros.
2. Corregir fugas obvias de `sede_id` en endpoints activos.
3. Corregir `apiFetch`/`fetch` directo en frontend, modulo por modulo.
4. Corregir textos visibles de UI.
5. Planificar deuda UUID/FK/compat en una migracion separada.

No hacer primero:

- Migraciones de PK/FK.
- Renombrados masivos.
- Reescritura de auth.
- Limpieza global de modelos compat.

---

## 9. Formato de Entrega de Cada Microcambio

Cada entrega debe reportar:

```json
{
  "auditoria_ccf": {
    "capa_evaluada": "DB / BACKEND / FRONTEND / DOCS",
    "archivo_o_endpoint": "ruta o endpoint",
    "categoria": "Bloqueante operativo / Correccion segura / Deuda conocida / Compat protegido / Contradiccion documental",
    "estado": "PASS / PENDIENTE / BLOQUEADO",
    "violacion_axioma": "Ninguna / Axioma 1 / Axioma 2 / Axioma 3",
    "cambio_realizado": "Resumen breve",
    "verificacion": "Comandos o pruebas ejecutadas",
    "riesgo_residual": "Lo que queda pendiente"
  }
}
```

---

## 10. Deuda Conocida Inicial

No corregir automaticamente estos hallazgos:

- Tablas nuevas o mixtas con PK `Integer` y FK a `personas.id`.
- `Persona.church_role`, `Persona.membership_type`, `Persona.user_id`.
- FKs a `users.id` en auditoria, CMS, agentes, auth compat y entidades historicas.
- Rutas y archivos `members`.
- Alias compat ingles/espanol en modelos y schemas.
- Tests que documentan `xfail` o deuda conocida.

Estas deudas deben pasar a un plan separado con migraciones, backfill, compatibilidad y rollback.

---

## 11. Regla de Cierre

Un cambio no esta terminado cuando "compila localmente". Esta terminado cuando:

1. El alcance prometido se cumplio.
2. No se tocaron archivos ajenos innecesariamente.
3. Las pruebas minimas pasan o se reporta por que no pudieron ejecutarse.
4. La plataforma queda en un estado igual o mas estable que antes.
5. El riesgo residual queda escrito.
