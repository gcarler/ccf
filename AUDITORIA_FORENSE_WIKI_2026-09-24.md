# Auditoría Forense Integral: Módulo Wiki y Base de Conocimientos Eclesial (Artículos, Categorías y Documentación) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `wiki` (Base de Conocimientos Eclesial, Artículos Ministeriales, Categorías, Versionado Histórico y Documentación de Plataforma)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-WIKI-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Wiki y Base de Conocimientos (`wiki`)** de la Plataforma CCF, cubriendo la totalidad de sus capas estructurales, operativas y documentales:
- **Backend y Endpoints Transversales:** `backend/api/wiki.py` (274 líneas con endpoints de listado, obtención, creación, snapshotting, versionado y soft delete), `backend/crud/wiki.py` (279 líneas de lógica transaccional de páginas y versiones históricas), `backend/models_wiki.py` (41 líneas con los modelos `WikiPage` y `WikiPageVersion`) y `backend/schemas/wiki.py`.
- **Frontend y Vistas Operativas:** Los 4 archivos canónicos del módulo en `frontend/src/app/plataforma/wiki/` y `frontend/src/components/wiki/`:
  1. `frontend/src/app/plataforma/wiki/page.tsx` (Hub Central de la Wiki y Directorio de Categorías)
  2. `frontend/src/app/plataforma/wiki/docs/page.tsx` (Directorio General de Documentación)
  3. `frontend/src/app/plataforma/wiki/docs/[page_key]/page.tsx` (Visor y Editor de Artículo Específico)
  4. `frontend/src/components/wiki/WikiEditor.tsx` (Editor Enriquecido de Documentos Markdown)
- **Suites de Pruebas y Aseguramiento:** `tests/test_wiki.py`, `tests/test_wiki_gap.py`, `tests/test_projects_wiki_slash_commands.py` (48 pruebas automatizadas cubriendo versionado, búsquedas, aislamiento multi-tenant y edge cases).
- **Documentación Canónica:** `docs/wiki/MODULO_WIKI.md`, `docs/wiki/PLAN_DE_TRABAJO_WIKI.md`, `docs/WIKI_API_CONTRACTS.md`, `docs/WIKI_QA_CHECKLIST.md`, `docs/WIKI_RBAC_MATRIX.md`, `docs/ESTADO_WIKI.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento riguroso. En `backend/models_wiki.py`:
   - `WikiPage.author_id` refiere obligatoriamente a `personas.id` (`ForeignKey("personas.id")`).
   - `WikiPageVersion.created_by_persona_id` refiere a `personas.id` (`ForeignKey("personas.id")`).
   - Cero tablas paralelas de personas. Atribución estricta al actor canónico UUID.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento estricto. Columnas de timestamp `created_at`, `updated_at`, `deleted_at` usan `DateTime(timezone=True)`. Backend opera con `datetime.now(timezone.utc)` y `_utcnow`. Prohibición absoluta de `datetime.utcnow()` respetada al 100% (0 ocurrencias). Preservación de registros mediante soft-delete (`deleted_at.is_(None)`).
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** La función `_resolve_sede(db, current_user)` en `backend/api/wiki.py` extrae `sede_id` del token del usuario (`get_user_sede_id(db, current_user.id)`). Restricción de unicidad canónica `uq_wiki_pages_key_sede` en `("page_key", "sede_id")`. Las páginas con `sede_id = None` corresponden a documentación global de plataforma accesible ministerialmente.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` o modals en viewport center) en los 4 archivos de frontend. La navegación y edición de artículos se ejecuta mediante rutas dedicadas y paneles laterales.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 65%):** **Hallazgo H-WIKI-01**. Se identifican **23 clases Tailwind hardcodeadas** (`bg-white`, `border-white`, `text-white`, `bg-slate-900`, `text-slate-700`, `border-gray-200`) y **36 selectores `dark:`** a lo largo de los 4 archivos de frontend del módulo Wiki.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** Los 4 archivos auditados utilizan exclusivamente `apiFetch()` de `@/lib/http`. Cero llamadas a `fetch()` crudo.
7. **Regla Frontend 4 (Rutas Canónicas — 100%):** Cero rutas sin prefijo `/plataforma/...`. Navegación unificada bajo `/plataforma/wiki`, `/plataforma/wiki/docs` y `/plataforma/wiki/docs/[page_key]`.
8. **Compilación y Pruebas Backend (100%):** Suite de 48 pruebas unitarias y de integración backend (`test_wiki.py`, `test_wiki_gap.py`, `test_projects_wiki_slash_commands.py`). Balance sintáctico estricto en los 4 archivos de frontend (`curlies=0, parens=0, brackets=0`).

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `WikiPage.author_id` y `WikiPageVersion.created_by_persona_id` enlazan a `personas.id`. Cero tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps con `DateTime(timezone=True)`. Backend en UTC estricto. Cero llamadas a `datetime.utcnow()`. Soft-delete activo en `deleted_at`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** `_resolve_sede` inyecta sede del token. Restricción `uq_wiki_pages_key_sede`. Documentos globales justificados. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 4 archivos auditados. 0 modales centrados (`AlertDialog` = 0, Modales = 0). Experiencia fluida de lectura y edición. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (65%). Hallazgo H-WIKI-01.** 23 clases Tailwind hardcodeadas y 36 selectores `dark:` en los 4 archivos de Wiki. | 15% | **65/100** | 🟡 **REQUIERE FASES 1 Y 2** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 4 archivos verificados. Cero llamadas a `fetch()` crudo. 100% de consultas internas utilizan `apiFetch`. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y esquemas Pydantic | **Cumplimiento pleno (100%).** 48 tests automatizados en 3 suites dedicadas (`test_wiki.py`, `test_wiki_gap.py`, `test_projects_wiki_slash_commands.py`). | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, esquemas Pydantic y documentación sincronizada en `docs/wiki/` y `docs/WIKI_*.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (65 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.75 + 10.0 + 10.0 + 5.0 = \mathbf{89.75 / 100} \approx \mathbf{89.8 / 100}$$

**Calificación Inicial:** **Grado A (89.8 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Wiki y Base de Conocimientos Eclesial exhibe una arquitectura de datos sólida con versionado histórico snapshot, enlaces directos a `personas.id` (Axioma 1), UTC estricto con `DateTime(timezone=True)` (Axioma 2), y aislamiento multi-tenant por sede con soporte global (Axioma 3). En la interfaz de usuario no existen modales centrados (100% conformes), pero se detecta el hallazgo **H-WIKI-01** (23 clases Tailwind hardcodeadas y 36 selectores `dark:` en los 4 archivos). Se aprueba condicionado a su remediación estructurada en dos fases atómicas.

---

## 4. Inventario Detallado de los 4 Archivos de Frontend de Wiki

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/wiki/page.tsx` | 253 | 11 | 16 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WIKI-01) |
| 2 | `frontend/src/app/plataforma/wiki/docs/page.tsx` | 27 | 0 | 1 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-WIKI-01) |
| 3 | `frontend/src/app/plataforma/wiki/docs/[page_key]/page.tsx` | 226 | 10 | 15 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-WIKI-01) |
| 4 | `frontend/src/components/wiki/WikiEditor.tsx` | 159 | 2 | 4 | 0 | `c:0 p:0 b:0` | 🔴 Requiere Fase 2 (H-WIKI-01) |
| **TOTAL** | **4 Archivos Auditados** | **665** | **23** | **36** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la erradicación del 100% del Hallazgo **H-WIKI-01**, se establece el siguiente plan de remediación en dos fases atómicas:

### Fase 1: Hub Central de Wiki y Directorio de Documentos (`TKT-WIKI-REMEDIATION-01`)
- **Archivos a intervenir (2 archivos):**
  1. `frontend/src/app/plataforma/wiki/page.tsx` (11 clases TW + 16 `dark:`)
  2. `frontend/src/app/plataforma/wiki/docs/page.tsx` (0 clases TW + 1 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind (`bg-white`, `border-white`, `text-white`, `bg-slate-900`, `text-slate-700`, `border-gray-200`) por tokens semánticos: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` redundantes.
- **Total incidencias a erradicar:** 11 clases TW / 17 selectores `dark:`.
- **Commit atómico:** `feat(wiki): Remediación de Tokens Semánticos en Hub y Directorio de Wiki (H-WIKI-01 Fase 1)`.

### Fase 2: Visor y Editor de Artículos Wiki (`TKT-WIKI-REMEDIATION-02`)
- **Archivos a intervenir (2 archivos):**
  1. `frontend/src/app/plataforma/wiki/docs/[page_key]/page.tsx` (10 clases TW + 15 `dark:`)
  2. `frontend/src/components/wiki/WikiEditor.tsx` (2 clases TW + 4 `dark:`)
- **Acciones específicas:**
  - Sustituir colores hardcodeados de Tailwind por tokens semánticos del Design System: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--border))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))`.
  - Erradicar selectores `dark:` y bordes con opacidades no semánticas.
  - Preservar experiencia libre de modales centrados.
- **Total incidencias a erradicar:** 12 clases TW / 19 selectores `dark:`.
- **Commit atómico:** `feat(wiki): Remediación de Tokens Semánticos en Visor y Editor de Wiki (H-WIKI-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las Fases 1 y 2 de remediación:
1. Se emitirá el ticket `TKT-WIKI-FINAL-CERTIFICATION` elevando la nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de clases Tailwind no semánticas (0 residuales) en los 4 archivos.
3. Se procederá con `TKT-WIKI-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo respuesta HTTP 200 OK en las rutas canónicas del módulo:
   - `/plataforma/wiki`
   - `/plataforma/wiki/docs`

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.8 / 100 — Grado A)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-WIKI-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
