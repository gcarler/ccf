# Auditoría Forense Integral: Módulo CMS Publicaciones y Aniversario (posts) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Inicial)  
**Módulo Auditado:** `cms` (Suite de Publicaciones, Noticias Eclesiales, Artículos de Aniversario, Moderación de Comentarios y Anuncios Pastorales)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-CMS-POSTS-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre la **Suite de Publicaciones, Noticias y Artículos de Aniversario del Módulo CMS (`posts`)** de la Plataforma CCF, cubriendo la infraestructura frontend en Next.js 15, su vinculación con el Kernel de Personas (`Axioma 1`), la consistencia cronológica en UTC y soft-deletes (`Axioma 2`), el aislamiento multi-tenant por sede y alcance global (`Axioma 3`), la prohibición de modales centrados (`AlertDialog` = 0 / uso de Drawers y SidePanel), la conformidad con los tokens semánticos CSS del Design System CCF y las pruebas backend:
- **Estructura Operativa y Vistas Auditadas (3 Vistas Canónicas — 1,537 Líneas):**
  1. `frontend/src/app/plataforma/cms/posts/page.tsx` (1,058 líneas): Centro editorial integral de artículos, noticias y aniversarios con conmutador de vistas (grid, list, table, board, kanban), filtros taxonómicos (categorías y etiquetas) y edición lateral en `SidePanel`.
  2. `frontend/src/app/plataforma/cms/comments/page.tsx` (265 líneas): Panel de moderación y auditoría de comentarios comunitarios sobre publicaciones pastorales.
  3. `frontend/src/app/plataforma/cms/announcements/new/page.tsx` (214 líneas): Formulario guiado de redacción y programación de anuncios prioritarios.
- **Integración con Modelos y Backend:**
  - Cliente canónico `@/lib/cms/v2` que centraliza todas las mutaciones y consultas a través de `apiFetch()`.
  - Enlace canónico de autores, editores y moderadores hacia `personas.id` (`auth_users.id`).
  - Cobertura backend con pruebas de contratos y comentarios celulares/editoriales (`tests/test_cms_v2_post_comments.py`, `tests/backend/api/test_cms_v2.py`).
- **Documentación Canónica:**
  - `docs/CMS_API_CONTRACTS.md`, `docs/CMS_QA_CHECKLIST.md` y `docs/CMS_RBAC_MATRIX.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. Toda publicación o moderación referencia al autor canónico en `personas.id`. Cero tablas paralelas de seres humanos.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Timestamps de programación (`published_at`), creación y comentarios en UTC (`datetime.now(timezone.utc)`). Baja lógica implementada con archivado (`status='archived'`) y `deleted_at`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. Publicaciones de alcance ministerial global (`sede_id` NULL) para aniversarios institucionales y segmentadas por `sede_id` para sedes locales.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0, `Dialog` = 0). Las operaciones editoriales y de confirmación operan en paneles laterales deslizantes (`SidePanel`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-CMS-POSTS-01**. Se detectan **160 selectores `dark:`** y **11 clases Tailwind hardcodeadas** en las 3 vistas:
   - `frontend/src/app/plataforma/cms/posts/page.tsx` (1,058 líneas): 137 selectores `dark:`, 0 clases TW.
   - `frontend/src/app/plataforma/cms/comments/page.tsx` (265 líneas): 2 selectores `dark:`, 11 clases TW.
   - `frontend/src/app/plataforma/cms/announcements/new/page.tsx` (214 líneas): 21 selectores `dark:`, 0 clases TW.
6. **Regla Frontend 3 (Cliente HTTP y Rutas Canónicas — 100%):** 100% `apiFetch()` a través del cliente `@/lib/cms/v2`. Rutas prefijadas canónicamente con `/plataforma/cms/...`.
7. **Compilación y Pruebas Backend (100%):** Cobertura en suite de tests backend y balance sintáctico estricto en frontend (`curlies=0, parens=0, brackets=0`).
8. **Estado Documental (100%):** Documentación técnica y contratos editoriales sincronizados con los estándares de plataforma.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Autores y editores mapean a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Programación en UTC; baja lógica con archivado y `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Contenido global institucional (`sede_id` NULL) y territorial. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers/Wizards | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Uso exclusivo de `SidePanel`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-CMS-POSTS-01.** 160 selectores `dark:` y 11 clases TW hardcodeadas. | 15% | **60/100** | 🟡 **REQUIERE FASE 1** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; rutas canónicas `/plataforma/...` | **Cumplimiento pleno (100%).** 100% `apiFetch()` vía `@/lib/cms/v2`. Rutas `/plataforma/cms/...`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** Cobertura backend de CMS y balance sintáctico estricto en frontend. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Documentación editorial y contratos de API sincronizados. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** La suite editorial CMS Publicaciones y Aniversario (`posts`) presenta una arquitectura robusta, con soporte multi-vista, edición en `SidePanel` (0 modales centrados) y consumo canónico mediante `apiFetch()`. Se detecta el hallazgo **H-CMS-POSTS-01** (160 selectores `dark:` y 11 clases Tailwind hardcodeadas) en sus 3 vistas. Se aprueba condicionado a su remediación técnica inmediata.

---

## 4. Inventario Detallado de las Vistas Frontend de CMS Posts

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/cms/posts/page.tsx` | 1,058 | **0** | **137** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-POSTS-01) |
| 2 | `frontend/src/app/plataforma/cms/comments/page.tsx` | 265 | **11** | **2** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-POSTS-01) |
| 3 | `frontend/src/app/plataforma/cms/announcements/new/page.tsx` | 214 | **0** | **21** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-CMS-POSTS-01) |
| **TOTAL** | **3 Vistas Canónicas** | **1,537** | **11** | **160** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en Fases Atómicas

Para subsanar el Hallazgo **H-CMS-POSTS-01**, se establece la siguiente fase atómica de remediación:

### Fase 1: Remediación de Tokens Semánticos en Suite CMS Publicaciones (`TKT-CMS-POSTS-REMEDIATION-01`)
- **Archivos a intervenir (3 archivos — 1,537 líneas):**
  1. `frontend/src/app/plataforma/cms/posts/page.tsx` (0 TW / 137 `dark:`)
  2. `frontend/src/app/plataforma/cms/comments/page.tsx` (11 TW / 2 `dark:`)
  3. `frontend/src/app/plataforma/cms/announcements/new/page.tsx` (0 TW / 21 `dark:`)
- **Acciones específicas:**
  - Sustituir clases Tailwind hardcodeadas por variables semánticas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--primary-foreground))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`, `hsl(var(--destructive))`, `hsl(var(--warning))` y `hsl(var(--success))`.
  - Erradicar 160 selectores `dark:` redundantes.
  - Preservar el editor enriquecido (`RichEditor`), el conmutador de vistas (`ViewSwitcher`), los Drawers (`SidePanel`), 0 modales centrados (`AlertDialog` = 0) y el balance sintáctico estricto (`c:0 p:0 b:0`).
  - Preservar las rutas canónicas `/plataforma/cms/...`.
- **Total incidencias a erradicar:** 11 clases TW / 160 selectores `dark:`.
- **Commit atómico:** `feat(cms): Remediación de Tokens Semánticos en Publicaciones y Aniversario (H-CMS-POSTS-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-CMS-POSTS-FINAL-CERTIFICATION`)
- Validar la erradicación total de clases Tailwind no semánticas (0 residuales) en las 3 vistas.
- Actualizar `AUDITORIA_FORENSE_CMS_POSTS_2026-09-24.md` con la nota certificada de **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final sin observaciones pendientes.
- **Commit atómico:** `docs(cms): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final de Publicaciones CMS`.

---

## 6. Certificación Final y Despliegue Proyectados (`TKT-CMS-POSTS-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Se ejecutará el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh` (swap atómico `.next-build` $\rightarrow$ `.next` y verificación HTTP en servicio).
2. Se verificará en vivo la respuesta HTTP 200 OK y latencia en milisegundos en las rutas canónicas del módulo:
   - `/plataforma/cms/posts`
   - `/plataforma/cms/comments`
   - `/plataforma/cms/announcements/new`
3. Se registrará la telemetría en vivo en las Secciones 6 y 7 de la auditoría y se emitirá el commit atómico `feat(cms): Despliegue Staging y Verificación en Vivo de Publicaciones CMS`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo CMS Publicaciones y Aniversario (`posts`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-CMS-POSTS-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
