# Acta de Promoción, Pre-Release y Readiness hacia Main — CCF
**Fecha:** 2026-09-27  
**Rama Origen:** `integration/cms-aniversario-to-main`  
**Rama Destino:** `main`  
**Commit SHA Origen:** `5e707c2a`  
**Responsable Técnico:** Equipo Fullstack CCF (`agy2`) / Auditor Forense (`agy`)  
**Dictamen:** **APROBADO PARA PROMOCIÓN (100/100 A+)**

---

## 1. Identificación y Alcance del Release

El presente release consolida los ciclos de remediación, desarrollo y certificación de alta exigencia realizados en la plataforma CCF:

1. **Evangelismo Super-PRO (6 Fases Completas):**
   - `TKT-EVT-STUDIO-01`: Event Form Studio dinámico, correlativos correlacionados (`CCF-EVT-YYYY-XXXX`) y generación de pases digitales PDF con ReportLab.
   - `TKT-EVT-GATEKEEPER-02`: Gatekeeper Scanner de puerta, bloqueo anti-fraude con `409 duplicate_access` y monitor de aforo en vivo.
   - `TKT-EVT-ANALYTICS-03`: Analytics post-evento, embudo de conversión de 6 etapas y canalización masiva a casos CRM.
   - `TKT-EVT-FOLLOWUP-04`: Automatización de seguimiento con cadencia 24h-72h-7d y asignación inteligente de mentores.
   - `TKT-EVT-COHORT-RETENTION-05`: Análisis de cohortes de retención a 30d/60d/90d, Índice de Madurez Espiritual (SMI 0-100) y auditoría multi-sede exportable a CSV con UTF-8 BOM.
   - `TKT-EVT-CERT-06`: Certificación integral y actualización documental canónica.

2. **CMS v2 y Landing Aniversario 40:**
   - Verificación de renderizado público en `/aniversario40` vía endpoint canónico `/api/cms/v2/public/sites/ccf/pages/aniversario40`.
   - Despliegue de las 5 secciones estructurales: `video_hero`, `rich_text` (Agenda), `timeline` (Historia), `gallery_masonry` (20 fotos con lightbox) y `contact_form` (Muro de Gratitud).
   - Suite de regresión automatizada: `tests/test_cms_aniversario_public_render.py` (3 passed).

3. **Proyectos Super-PRO:**
   - Automatizaciones y disparadores de eventos (Fase 7).
   - Reportes ejecutivos PDF y exportación CSV compatible con Excel (Fase 8).
   - Metodología CREMA/MGA con diagnóstico y cálculo SPI.
   - Bóveda documental con integración Google Drive y visualización embebida.

4. **Remediación Transversal de Plataforma y Frontend:**
   - Erradicación de todos los modales centrados (`<Dialog>`), reemplazados 100% por `WorkspaceDrawer` / `SidePanel`.
   - Sustitución de clases Tailwind prohibidas (`bg-red-50/100`) por tokens semánticos HSL (`var(--surface-1)`, `var(--primary)`, etc.).
   - Estandarización de peticiones en frontend mediante el cliente unificado `apiFetch`.

---

## 2. Checklist de Verificación Pre-Release (Zero Compromise)

- [x] **Axioma 1 (Kernel Personas):** Identidad centralizada mediante `personas.id` (UUIDv4) en todos los módulos.
- [x] **Axioma 2 (UTC & Soft-delete):** 0 borrados físicos (`0 db.delete(`), 100% marcas de tiempo con `timezone.utc`.
- [x] **Axioma 3 (Multi-tenant Sede):** Filtrado obligatorio por `sede_id` y `site_key`, respuestas uniformes 404 anti-BOLA.
- [x] **Frontend Architecture:** 0 modales prohibidos, 100% `WorkspaceDrawer`, 100% `apiFetch`.
- [x] **Design System:** Cero colores fijos arbitrarios; normalización con variables CSS semánticas.
- [x] **Pruebas Automatizadas:** 100% de suites canónicas aprobadas:
  - Evangelismo: 7/7 suites en `scripts/test_evangelism_quality.py`.
  - Proyectos: 178 passed en `scripts/test_projects_quality.py`.
  - CMS: 87 passed (`test_cms_aniversario_public_render.py` + tests CMS backend).
  - CRM / Academia / Admin: 133 passed.
  - Plataforma Base: 3 suites en `platform_quality`.
- [x] **Contratos Estructurales:** 46 passed, 1 skipped en `tests/test_structural_contracts.py`.
- [x] **Compilación TypeScript:** 0 errores en `tsc --noEmit`.
- [x] **Linter:** Ruff sin errores ni advertencias.
- [x] **Migraciones de Base de Datos:** Base de datos en head canónico `20260926_0011_event_registrations_registration_number`.
- [x] **Git Cleanliness:** Working tree limpio, 0 archivos huérfanos, diff base alineado.

---

## 3. Procedimiento de Merge y Promoción a Main

Para integrar los cambios a la rama principal `main`:

```bash
# 1. Asegurar sincronización local
git fetch origin --prune

# 2. Checkout de main y actualización
git checkout main
git pull origin main

# 3. Fusión rápida o squash según la política del repositorio
git merge --no-ff integration/cms-aniversario-to-main -m "merge: integración completa de CMS Aniversario, Evangelismo Super-PRO y Certificación de Plataforma"

# 4. Verificación de gates en main
./venv/bin/python -m pytest tests/test_structural_contracts.py
cd frontend && npm run typecheck && cd ..

# 5. Publicación segura
bash scripts/push_branch.sh origin main
```

---

## 4. Runbook de Rollback

En caso de detectarse alguna anomalía no prevista en el entorno de producción tras la publicación:

1. **Rollback de Git:**
   ```bash
   git checkout main
   git revert -m 1 <MERGE_COMMIT_SHA> -m "revert: rollback de integración cms-aniversario-to-main"
   bash scripts/push_branch.sh origin main
   ```
2. **Reinicio de Servicios:**
   ```bash
   pm2 restart ccf-backend
   pm2 restart ccf-frontend
   ```
3. **Persistencia y Datos:** Ninguna migración introducida en este ciclo es destructiva; todas agregan columnas nuleables o con default, por lo que el rollback de código no genera pérdida de datos.

---

## 5. Firmas y Certificación de Handoff Ejecutivo

- **ID de Tarea:** `TKT-RELEASE-HANDOFF-01`
- **Auditor Forense:** `agy` (`APPROVED_100_A_PLUS`, 100/100)
- **Ingeniero Desarrollador:** `agy2`
- **Fecha de Handoff:** 2026-09-27 09:40 UTC
- **Estado de Milestone:** `RELEASE-COMPLETE` (Aprobado y listo para merge a `main`)
