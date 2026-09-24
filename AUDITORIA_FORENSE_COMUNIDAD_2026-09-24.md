# Auditoría Forense Integral: Módulo Comunidad (Vida Conectada, Anuncios, Grupos y Oración) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Integral Inicial y Plan de Remediación Canónica)  
**Módulo Auditado:** `community` (Vida Conectada, Tablero Comunitario, Grupos de Conexión, Muro de Oración, Testimonios, Eventos Comunitarios y Notificaciones)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-COMMUNITY-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN DE TOKENS SEMÁNTICOS (88.8 / 100 — GRADO B+)**  

---

## 1. Resumen Ejecutivo

Se ha completado la **Auditoría Forense Integral** sobre el **Módulo Comunidad (community)** de la Plataforma CCF, cubriendo la totalidad de sus capas de dominio:
- **Backend relacional y endpoints:** `backend/api/community.py`, `backend/crud/crm_/community.py`, `backend/models_crm.py` (`CommunityBoardCard`, `GrupoEvangelismo`).
- **Frontend y vistas operativas:** `frontend/src/app/plataforma/community/**` y `frontend/src/components/community/**` (16 archivos analizados).
- **Suites de pruebas y aseguramiento:** `tests/test_crm_crud_counseling_prayer_community.py`, `tests/test_community_coverage.py`.
- **Documentación canónica:** `docs/MESSAGING_COMMUNITY_API_CONTRACTS.md`, `docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md`, `docs/ESTADO_COMMUNITY.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento riguroso. Las identidades en grupos de conexión (`GrupoEvangelismo.lider_persona_id`), participantes, peticiones de oración (`PrayerRequest.persona_id`), testimonios y eventos comunitarios están firmemente acopladas al UUID canónico de `personas.id`. Cero tablas paralelas de seres humanos. Cero identidades desconectadas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento estricto. Columnas temporales con `DateTime(timezone=True)` utilizando `datetime.now(timezone.utc)` y `_utcnow`. Cero uso de `datetime.utcnow()` (deprecado). Eliminación destructiva prohibida: `delete_community_card` ejecuta baja lógica mediante `deleted_at = _utcnow()`, sin invocaciones a `db.delete()`.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** `sede_id` se atribuye server-side desde el JWT del actor autenticado mediante `get_user_sede_id(db, current_user.id)` en mutaciones (`POST /community/cards`, `POST /community/grupos`). Excepción canónica de diseño expresamente documentada para los endpoints públicos de atracción comunitaria (`GET /community/cards`, `GET /community/grupos`, `GET /community/events`), donde se exponen únicamente metadatos agregados no sensibles con serializadores estrictos.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** **0 modales centrados (`AlertDialog` o modals tradicionales)** detectados en los 16 archivos de frontend. Los flujos interactivos de detalle y acciones operativas implementan paneles laterales deslizantes (`grupos/page.tsx` con `DrawerState` / `SidePanel`).
5. **Regla Frontend 2 (Tokens Semánticos CSS — 25%):** **Hallazgo H-COMM-01**. Se detectaron **119 violaciones** de clases de color Tailwind hardcodeadas (`bg-white`, `text-slate-*`, `border-gray-*`, `zinc-*`, `blue-*`, etc.) y selectores `dark:` distribuidas en 11 archivos de frontend (de los 16 auditados). Requiere saneamiento sistemático por fases.
6. **Regla Frontend 3 (Cliente HTTP apiFetch — 100%):** 16 archivos analizados. Cero llamadas a `fetch()` crudo. 100% de peticiones internas utilizan el cliente estándar `@/lib/http` (`apiFetch`).
7. **Compilación y Pruebas Backend (100%):** Cobertura unitaria y de integración en `tests/test_crm_crud_counseling_prayer_community.py` y `tests/test_community_coverage.py` asegurando atribución de sede, auto-incremento de posición y exclusión de bajas lógicas.
8. **Estado Documental (100%):** Paquete documental canónico completo y sincronizado.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :-: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** `models_crm.py` y `models_counseling_prayer.py` referencian `personas.id` en líderes de grupos, autores de testimonios y peticionarios. Cero identidades duplicadas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; soft-delete universal | **Cumplimiento pleno (100%).** Timestamps con `DateTime(timezone=True)`. Bajas lógicas con `deleted_at`. 0 `db.delete(` destructivos en `crud/crm_/community.py`. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); mutaciones aisladas; global justificado | **Cumplimiento pleno (100%).** Atribución server-side de `sede_id` en mutaciones. Excepción canónica documentada para vistas públicas con serializador restringido no sensible. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers obligatorios | **Cumplimiento pleno (100%).** 16 archivos auditados. 0 modales centrados (`AlertDialog` o modals en viewport center). Flujos alineados con paneles laterales deslizantes (`SidePanel` / Drawers). | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **No conforme (25%). Hallazgo H-COMM-01.** Detección de 119 violaciones de clases de color hardcodeadas (`slate`, `gray`, `zinc`, `blue`, `white`, etc.) y selectores `dark:` en 11 archivos de frontend. Requiere remediación atómica. | 15% | **25/100** | 🔴 **REQUIERE REMEDIACIÓN** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; 0 `fetch()` crudo en llamadas internas | **Cumplimiento pleno (100%).** 16 archivos verificados. 0 llamadas a `fetch()` crudo. 100% de llamadas utilizan el cliente `@/lib/http` con interceptores canónicos. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y cobertura estructural | **Cumplimiento pleno (100%).** Suites dedicadas `test_crm_crud_counseling_prayer_community.py` y `test_community_coverage.py` asegurando integridad de datos. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Contratos, checklists y guías sincronizadas en `docs/MESSAGING_COMMUNITY_*.md` y `docs/ESTADO_COMMUNITY.md`. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (25 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 3.75 + 10.0 + 10.0 + 5.0 = \mathbf{88.75 / 100} \approx \mathbf{88.8 / 100}$$

**Calificación Inicial:** **Grado B+ (88.8 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo supera de forma impecable los axiomas de identidad, temporalidad y aislamiento multi-tenant, así como la regla de navegación sin modales centrados (0 `AlertDialog`) y uso exclusivo de `apiFetch()`. El único hallazgo adverso es **H-COMM-01** (Tokens Semánticos), con 119 violaciones concentradas en 11 archivos de frontend. Se emite aprobación condicionada y se ordena su remediación prioritaria en 2 fases atómicas.

---

## 4. Inventario Detallado del Hallazgo H-COMM-01 (119 Incidencias en 11 Archivos)

El escaneo estático automatizado sobre los directorios `frontend/src/app/plataforma/community` y `frontend/src/components/community` arrojó el siguiente desglose forense:

| # | Archivo Auditado | Violaciones Detectadas | Tipo de Infracción Principal | Estado |
| :-: | :--- | :---: | :--- | :-: |
| 1 | `frontend/src/app/plataforma/community/prayer/page.tsx` | 41 | Clases `bg-white`, `text-slate-*`, `border-gray-*`, `dark:*` | 🔴 Requiere Fase 1 |
| 2 | `frontend/src/app/plataforma/community/discover/page.tsx` | 31 | Clases `bg-slate-*`, `text-zinc-*`, `border-slate-*`, `dark:*` | 🔴 Requiere Fase 2 |
| 3 | `frontend/src/app/plataforma/community/page.tsx` | 15 | Clases `bg-white`, `text-slate-700`, `border-slate-200`, `dark:*` | 🔴 Requiere Fase 2 |
| 4 | `frontend/src/app/plataforma/community/give/page.tsx` | 9 | Clases `bg-white`, `text-slate-900`, `border-gray-100`, `dark:*` | 🔴 Requiere Fase 1 |
| 5 | `frontend/src/app/plataforma/community/testimonies/publish/page.tsx` | 6 | Formulario con `bg-white`, `border-gray-300`, `text-white`, `dark:*` | 🔴 Requiere Fase 2 |
| 6 | `frontend/src/app/plataforma/community/prayer/request/page.tsx` | 5 | Formulario con `bg-white`, `text-slate-600`, `dark:*` | 🔴 Requiere Fase 1 |
| 7 | `frontend/src/app/plataforma/community/grupos/page.tsx` | 4 | Clases `bg-white`, `border-gray-200`, `dark:*` | 🔴 Requiere Fase 2 |
| 8 | `frontend/src/app/plataforma/community/events/page.tsx` | 3 | Tarjetas con `text-slate-500`, `bg-gray-50`, `dark:*` | 🔴 Requiere Fase 2 |
| 9 | `frontend/src/app/plataforma/community/notifications/page.tsx` | 2 | Notificaciones con `border-gray-200`, `bg-white`, `dark:*` | 🔴 Requiere Fase 2 |
| 10 | `frontend/src/app/plataforma/community/testimonies/page.tsx` | 2 | Tarjetas con `bg-white`, `text-gray-700`, `dark:*` | 🔴 Requiere Fase 2 |
| 11 | `frontend/src/components/community/QuickCommentCard.tsx` | 1 | Componente con subcadena residual `dark:*` | 🔴 Requiere Fase 1 |
| 12 | `frontend/src/app/plataforma/community/layout.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 13 | `frontend/src/app/plataforma/community/announcements/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 14 | `frontend/src/app/plataforma/community/messages/page.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 15 | `frontend/src/components/community/ListRow.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| 16 | `frontend/src/components/community/ToolbarChip.tsx` | 0 | Conforme al Design System | 🟢 Conforme |
| **TOTAL** | **16 Archivos Auditados** | **119** | **Incidencias Totales a Erradicar** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación en Fases Atómicas

Para garantizar la eliminación total del Hallazgo **H-COMM-01** preservando la estabilidad sintáctica y funcional de Next.js 15 + React 19, se estructura el plan de trabajo en las siguientes fases temáticas:

### Fase 1: Muro de Oración, Donaciones y Componentes (`TKT-COMM-REMEDIATION-01`)
- **Archivos a intervenir (4 archivos):**
  1. `frontend/src/app/plataforma/community/prayer/page.tsx` (41 incidencias)
  2. `frontend/src/app/plataforma/community/prayer/request/page.tsx` (5 incidencias)
  3. `frontend/src/app/plataforma/community/give/page.tsx` (9 incidencias)
  4. `frontend/src/components/community/QuickCommentCard.tsx` (1 incidencia)
- **Total incidencias a erradicar:** 56 incidencias.
- **Commit atómico:** `feat(community): Remediación de Tokens Semánticos en Muro de Oración y Donaciones (H-COMM-01 Fase 1)`.

### Fase 2: Hub Central, Descubrimiento, Grupos, Testimonios y Eventos (`TKT-COMM-REMEDIATION-02`)
- **Archivos a intervenir (7 archivos):**
  1. `frontend/src/app/plataforma/community/discover/page.tsx` (31 incidencias)
  2. `frontend/src/app/plataforma/community/page.tsx` (15 incidencias)
  3. `frontend/src/app/plataforma/community/testimonies/publish/page.tsx` (6 incidencias)
  4. `frontend/src/app/plataforma/community/grupos/page.tsx` (4 incidencias)
  5. `frontend/src/app/plataforma/community/events/page.tsx` (3 incidencias)
  6. `frontend/src/app/plataforma/community/testimonies/page.tsx` (2 incidencias)
  7. `frontend/src/app/plataforma/community/notifications/page.tsx` (2 incidencias)
- **Total incidencias a erradicar:** 63 incidencias.
- **Commit atómico:** `feat(community): Remediación de Tokens Semánticos en Hub Central, Grupos y Testimonios (H-COMM-01 Fase 2)`.

---

## 6. Certificación Final y Despliegue Proyectados

Una vez ejecutadas las 2 fases de remediación:
1. Se emitirá el ticket `TKT-COMM-FINAL-CERTIFICATION` con actualización de nota a **100.0/100 Grado A+**.
2. Se validará la ausencia total de violaciones residuales (0 clases Tailwind hardcodeadas, 0 selectores `dark:`).
3. Se procederá con `TKT-COMM-DEPLOY-AND-VERIFY` ejecutando `bash scripts/deploy_frontend.sh` y verificando en vivo HTTP 200 OK en las rutas canónicas (`/plataforma/community`, `/plataforma/community/prayer`, `/plataforma/community/grupos`, `/plataforma/community/discover`, `/plataforma/community/give`, etc.).

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (88.8 / 100 — Grado B+)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-COMM-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
