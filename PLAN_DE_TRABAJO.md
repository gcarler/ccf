# Estado de Trabajo — Plataforma CCF

**Versión:** 3.1 (actualización 2026-06-10)
**Propósito:** Referencia rápida del estado actual del proyecto y las prioridades vigentes.

> Este documento reemplaza el plan de trabajo original (pre-v3.0). Los planes activos de
> arquitectura y saneamiento viven en `docs/`.

---

## Stack en Producción

| Componente | Tecnología |
|---|---|
| Backend | FastAPI + Python 3.12 (uvicorn, puerto 8000) |
| Frontend | Next.js 14 (puerto 3000) |
| Base de datos | PostgreSQL 15 (VPS localhost:5432, sin Docker) |
| Proxy | nginx (SSL Let's Encrypt, dominio elfarocc.tech) |
| Deploy | VPS directo: `git pull origin main` → `./startccf` |
| Dev local | SQLite (`ccf_dev.db`) vía `DATABASE_URL` en `.env` |

---

## Lo Que Está Terminado (v3.0 — 2026-06-02 al 2026-06-05)

- **Seguridad:** 8 hard deletes convertidos a soft delete; filtrado `sede_id` agregado a chat, graph y agents.
- **Migraciones Alembic:** 5 migraciones encadenadas (índices, soft delete, `sede_id`, tablas legacy, GIST).
- **Performance backend:** `selectinload()` en CRUDs de Academy, CRM y Proyectos.
- **Frontend:** 4 modales convertidos a Drawers; 2 805 colores hardcodeados → tokens semánticos HSL.
- **Tests:** Suite pasó de 77 passed / 36 failed / 110 errors → **224 passed, 0 failed**.
- **CI/CD:** Pipeline GitHub Actions (`.github/workflows/ci.yml` y `deploy.yml`).
- **Flujo evangelismo → CRM:** motor de proyección temporal + bridge automático `es_primera_vez`.
- **Deuda legacy frontend:** Admin y Academy ya no consumen `/api/auth/users` ni `/api/academy/users/{user_id}/...`; `UserSelect` migrado a UUID.
- **Backfill UUID:** Migraciones físicas para Academy, CRM, CMS y Agents/Governance creadas (`alembic/versions/20260605_*`).
- **Runbook de producción:** `docs/RUNBOOK_PRODUCCION.md`.
- **Quality gate:** pasa con `ENV=test DATABASE_URL=sqlite:///./ccf_dev.db python3 scripts/auditing/quality_gate.py`.

---

## Planes Activos

| Documento | Propósito |
|---|---|
| `docs/PLAN_SANEAMIENTO_DEUDA_LEGACY_CCF.md` | Plan maestro de 6 lotes para retirar deuda `users.id` / PK enteras |
| `docs/INVENTARIO_DEUDA_LEGACY_RESTANTE_20260605.md` | Inventario exacto de archivos y columnas legacy restantes |
| `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md` | Reglas de trabajo: microcambios, verificación, rollback |
| `docs/ARQUITECTURA_IMPECABLE_CCF.md` | Definición de "arquitectura a punto" + gate obligatorio |
| `docs/CIERRE_ARQUITECTURA_CCF.md` | Estado medido al 2026-06-05 + deuda arquitectónica restante |

---

## Próximos Pasos (Lotes Pendientes)

Según `docs/PLAN_SANEAMIENTO_DEUDA_LEGACY_CCF.md`:

| Lote | Meta | Estado |
|---|---|---|
| Lote 0 | Estabilizar `quality_gate.py` sin timeout | Parcial — pasa con flags de entorno |
| Lote 1 | Cierre superficie Admin/Auth legacy | ✅ Completado en 2026-06-05 |
| Lote 2 | Academy Persona UUID (enrollments/progress) | ✅ Backfill creado; validar en staging |
| Lote 3 | Selectores UUID (`PersonaSelect`) | En proceso |
| Lote 4 | FKs `users.id` por dominio (CRM, CMS, Agents) | Pendiente |
| Lote 5 | PK enteras en tablas transaccionales | Pendiente |
| Lote 6 | Retiro de contratos legacy confirmados sin consumidores | Pendiente |

---

## Comandos Clave

```bash
# Arrancar plataforma
./startccf

# Detener plataforma
./stopccf

# Quality gate local
ENV=test DATABASE_URL=sqlite:///./ccf_dev.db QUALITY_GATE_STEP_TIMEOUT=90 QUALITY_GATE_FRONTEND_TIMEOUT=240 \
  python3 scripts/auditing/quality_gate.py

# Tests de contratos y reglas
/root/ccf/venv/bin/python -m pytest -q -o addopts='' \
  tests/test_smoke.py tests/test_structural_contracts.py tests/test_reglas_plataforma.py

# Typecheck frontend
cd frontend && npm run typecheck

# Migraciones
alembic upgrade head
```

---

## Regla de Oro

> Antes de cualquier cambio: leer `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`.
> La fuente de arquitectura es `REGLAS.md`. El glosario de términos es `GLOSSARY.md`.
