# Auditoría Forense Integral — Módulo CMS Páginas, Builder y SEO (pages)
**Plataforma Comunidad Cristiana Fe (CCF)**  
**Fecha:** 24 de Septiembre de 2026  
**Identificador de Auditoría:** `TKT-AUDIT-CMS-PAGES-01`  
**Módulo:** `cms` (Suite Páginas, Editor Visual Builder, Versiones, Testimonios, SEO y Redirecciones)  
**Auditor Responsable:** `agy` (Auditor Forense de Arquitectura de Plataforma)  
**Ingeniero de Desarrollo:** `agy2` (Pair Programmer / Implementador Dev)  
**Rama de Integración:** `integration/cms-aniversario-to-main`  
**Estado:** **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)**

---

## 1. Resumen Ejecutivo y Alcance

La presente auditoría forense evalúa de manera exhaustiva y canónica el núcleo editorial de gestión de contenidos públicos de la Plataforma CCF. Esta suite abarca el motor de publicación de páginas (`pages`), el editor visual Drag & Drop con componentes dinámicos (`builder`), el visor y comparador visual de diferencias entre revisiones (`versions`, `VersionsDiffView.tsx`, `FieldDiff.tsx`), el gestor y vista de detalle de testimonios ministeriales (`testimonials`), el subsistema de optimización en motores de búsqueda (`seo-audit`), el gestor de enlaces rotos (`broken-links`), el router de redirecciones canónicas (`redirects`), el checklist de preparación operativa (`readiness`), el monitor multi-sitio (`sites`) y el visor interactivo de previsualización (`preview`).

La inspección cubre los contratos de backend de páginas y builder en `/api/cms/v2/pages` y `/api/cms/v2/builder`, el aislamiento multi-tenant por `sede_id`, la observancia del Axioma 1 (Kernel de personas para autores y editores) y la revisión línea por línea de las **13 vistas canónicas frontend** en Next.js 15 + React 19 que totalizan **5,338 líneas de código**:
1. `frontend/src/app/plataforma/cms/pages/[slug]/versions/VersionsDiffView.tsx` (509 líneas)
2. `frontend/src/app/plataforma/cms/pages/[slug]/versions/FieldDiff.tsx` (205 líneas)
3. `frontend/src/app/plataforma/cms/pages/[slug]/versions/page.tsx` (491 líneas)
4. `frontend/src/app/plataforma/cms/pages/[slug]/page.tsx` (192 líneas)
5. `frontend/src/app/plataforma/cms/builder/page.tsx` (1,276 líneas)
6. `frontend/src/app/plataforma/cms/preview/page.tsx` (187 líneas)
7. `frontend/src/app/plataforma/cms/sites/page.tsx` (118 líneas)
8. `frontend/src/app/plataforma/cms/testimonials/page.tsx` (937 líneas)
9. `frontend/src/app/plataforma/cms/testimonials/[slug]/page.tsx` (252 líneas)
10. `frontend/src/app/plataforma/cms/seo-audit/page.tsx` (607 líneas)
11. `frontend/src/app/plataforma/cms/redirects/page.tsx` (214 líneas)
12. `frontend/src/app/plataforma/cms/readiness/page.tsx` (275 líneas)
13. `frontend/src/app/plataforma/cms/broken-links/page.tsx` (75 líneas)

---

## 2. Hallazgos Forenses Detectados

### [H-CMS-PAGES-01] Presencia de Selectores `dark:` Redundantes y Clases Tailwind Hardcodeadas No Semánticas
- **Severidad:** Media (Deuda técnica visual / Violación de Regla 2 de Frontend).
- **Archivos Afectados (Telemetría Canónica agy — 5,338 líneas en 13 vistas):**
  - `frontend/src/app/plataforma/cms/pages/[slug]/versions/VersionsDiffView.tsx` (509 l): **55** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/pages/[slug]/versions/FieldDiff.tsx` (205 l): **18** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/pages/[slug]/versions/page.tsx` (491 l): **4** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/pages/[slug]/page.tsx` (192 l): **13** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/builder/page.tsx` (1,276 l): **5** selectores `dark:`, **18** clases TW hardcodeadas.
  - `frontend/src/app/plataforma/cms/preview/page.tsx` (187 l): **16** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/sites/page.tsx` (118 l): **10** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/testimonials/page.tsx` (937 l): **9** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/testimonials/[slug]/page.tsx` (252 l): **9** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/seo-audit/page.tsx` (607 l): **52** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/redirects/page.tsx` (214 l): **36** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/readiness/page.tsx` (275 l): **40** selectores `dark:`, **0** TW.
  - `frontend/src/app/plataforma/cms/broken-links/page.tsx` (75 l): **0** selectores `dark:`, **6** clases TW hardcodeadas.
- **Total Hallazgo:** **267** selectores `dark:` redundantes y **24** clases Tailwind hardcodeadas no semánticas.
- **Impacto:** Rompen la adaptabilidad del Design System corporativo CCF ante el cambio de temas claro/oscuro y las 10 paletas personalizadas. Deben unificarse utilizando exclusivamente tokens CSS semánticos `hsl(var(--*))`.

---

## 3. Evaluación de los 8 Ejes Canónicos de Arquitectura

| # | Eje de Evaluación | Ponderación | Puntaje Obtenido | Estado | Observaciones Forenses |
| :-: | :--- | :---: | :---: | :---: | :--- |
| **1** | **Axioma 1: Kernel de Personas** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Autores, editores de revisiones y creadores de testimonios vinculados a `personas.id` canónico vía `auth_users.id` y `actor_persona_id`. Cero tablas paralelas de personas. |
| **2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Campos temporales en UTC (`DateTime(timezone=True)`). Control de revisiones, snapshots inmutables y borrado lógico (`deleted_at`, `is_active`) en páginas y testimonios. |
| **3** | **Axioma 3: Aislamiento Multi-Tenant** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Filtro estricto por `sede_id` autenticado en backend y frontend. Capacidad de alcance ministerial global explícita para sitios institucionales (`sede_id.is_(None)`). |
| **4** | **Drawers vs Modales Centrados** | 15.0% | **15.0 / 15.0** | 🟢 CUMPLE | Cero modales centrados (`AlertDialog` = 0) en las 13 vistas. Implementación rigurosa de paneles laterales deslizantes (`SidePanel` / Drawers) para configuración, SEO y edición. |
| **5** | **Tokens Semánticos del Design System** | 15.0% | **9.0 / 15.0** | 🟡 OBSERVADO | **H-CMS-PAGES-01**: Se detectaron 267 selectores `dark:` y 24 clases Tailwind hardcodeadas que deben sustituirse por tokens HSL semánticos. |
| **6** | **Peticiones HTTP y Rutas Canónicas** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | 100% de llamadas HTTP a través de `apiFetch()` (`@/lib/http` y servicios canónicos). Navegación con prefijo canónico estricto `/plataforma/cms/...`. |
| **7** | **TypeScript Estricto y Balance Sintáctico** | 10.0% | **10.0 / 10.0** | 🟢 CUMPLE | Interfaces y contratos de props estrictos, tipado exhaustivo de bloques del builder y balance sintáctico perfecto (`c:0 p:0 b:0`) en los 13 archivos. |
| **8** | **Manejo de Estados de UI** | 5.0% | **5.0 / 5.0** | 🟢 CUMPLE | Estados de carga (`Skeleton` / `Loader`), estados vacíos (`EmptyState`) y feedback reactivo mediante notificaciones `toast` (sonner). |
| **TOTAL** | **Evaluación Global de Calidad** | **100.0%** | **89.0 / 100** | 🟡 **GRADO A** | **Aprobado Condicionado a Remediación Técnica (H-CMS-PAGES-01)** |

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** La suite CMS Páginas, Builder y SEO presenta una excelente arquitectura de composición visual, control de versiones e integridad multi-tenant con cero modales centrados. Se autoriza la ejecución inmediata del plan de remediación atómico para erradicar el hallazgo **H-CMS-PAGES-01**.

---

## 4. Inventario Detallado de las Vistas Frontend de CMS Páginas, Builder y SEO

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `pages/[slug]/versions/VersionsDiffView.tsx` | 509 | **0** | **55** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 2 | `pages/[slug]/versions/FieldDiff.tsx` | 205 | **0** | **18** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 3 | `pages/[slug]/versions/page.tsx` | 491 | **0** | **4** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 4 | `pages/[slug]/page.tsx` | 192 | **0** | **13** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 5 | `builder/page.tsx` | 1,276 | **18** | **5** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 6 | `preview/page.tsx` | 187 | **0** | **16** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 7 | `sites/page.tsx` | 118 | **0** | **10** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 8 | `testimonials/page.tsx` | 937 | **0** | **9** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 9 | `testimonials/[slug]/page.tsx` | 252 | **0** | **9** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 10 | `seo-audit/page.tsx` | 607 | **0** | **52** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 11 | `redirects/page.tsx` | 214 | **0** | **36** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 12 | `readiness/page.tsx` | 275 | **0** | **40** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| 13 | `broken-links/page.tsx` | 75 | **6** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-PAGES-01) |
| **TOTAL** | **13 Vistas Canónicas** | **5,338** | **24 únicas** | **267** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en Fases Atómicas

Para resolver de manera definitiva el hallazgo **H-CMS-PAGES-01**, se implementará la siguiente secuencia canónica:

### Fase 1: Remediación de Tokens Semánticos en Suite CMS Páginas, Builder y SEO (`TKT-CMS-PAGES-REMEDIATION-01`)
- **Archivos a intervenir (13 archivos — 5,338 líneas):**
  1. `VersionsDiffView.tsx` (55 `dark:`)
  2. `FieldDiff.tsx` (18 `dark:`)
  3. `versions/page.tsx` (4 `dark:`)
  4. `pages/[slug]/page.tsx` (13 `dark:`)
  5. `builder/page.tsx` (5 `dark:`, 18 TW)
  6. `preview/page.tsx` (16 `dark:`)
  7. `sites/page.tsx` (10 `dark:`)
  8. `testimonials/page.tsx` (9 `dark:`)
  9. `testimonials/[slug]/page.tsx` (9 `dark:`)
  10. `seo-audit/page.tsx` (52 `dark:`)
  11. `redirects/page.tsx` (36 `dark:`)
  12. `readiness/page.tsx` (40 `dark:`)
  13. `broken-links/page.tsx` (6 TW)
- **Acciones específicas:**
  - Sustituir los 267 selectores `dark:` redundantes por variables del Design System CCF: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, etc.
  - Reemplazar las 24 clases Tailwind hardcodeadas por tokens semánticos equivalentes.
  - Mantener 0 modales centrados (100% SidePanel y Drawers).
  - Mantener 100% `apiFetch()` y balance sintáctico estricto (`c:0 p:0 b:0`).
- **Commit atómico:** `feat(cms): Remediación de Tokens Semánticos en Suite CMS Páginas, Builder y SEO (H-CMS-PAGES-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-CMS-PAGES-FINAL-CERTIFICATION`)
- Validar la erradicación del 100% de los 267 selectores `dark:` y las 24 clases Tailwind en las 13 vistas.
- Actualizar `AUDITORIA_FORENSE_CMS_PAGINAS_2026-09-24.md` elevando la calificación a **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final **APTO PARA STAGING**.
- **Commit atómico:** `docs(cms): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final de CMS Páginas, Builder y SEO`.

### Fase 3: Despliegue Staging y Verificación en Vivo (`TKT-CMS-PAGES-DEPLOY-AND-VERIFY`)
- Ejecutar despliegue seguro a staging con `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next`).
- Medir telemetría HTTP 200 OK y latencia en milisegundos en las rutas clave del módulo:
  - `/plataforma/cms/pages`
  - `/plataforma/cms/builder`
  - `/plataforma/cms/preview`
  - `/plataforma/cms/testimonials`
  - `/plataforma/cms/seo-audit`
  - `/plataforma/cms/redirects`
  - `/plataforma/cms/readiness`
  - `/plataforma/cms/broken-links`
- Registrar resultados en la auditoría y formalizar cierre.
- **Commit atómico:** `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Páginas, Builder y SEO`.

---

## 6. Certificación Final y Despliegue Proyectados (`TKT-CMS-PAGES-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Se ejecutará el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next` y verificación HTTP en servicio).
2. Se verificará en vivo la respuesta HTTP 200 OK y latencia en milisegundos en las rutas del módulo.
3. Se registrará la telemetría en vivo en las Secciones 6 y 7 de la auditoría y se emitirá el commit atómico `feat(cms): Despliegue Staging y Verificación en Vivo de CMS Páginas, Builder y SEO`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo CMS Páginas, Builder y SEO (`pages`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-CMS-PAGES-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
