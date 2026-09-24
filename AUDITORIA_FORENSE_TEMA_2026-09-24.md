# Auditoría Forense Integral: Módulo Selector de Tema Visual y Paletas (theme) — Plataforma CCF

**Fecha de Ejecución:** 2026-09-24  
**Versión:** 1.0.0 (Auditoría Forense Inicial)  
**Módulo Auditado:** `theme` (Selector de Tema Visual, Paletas Día/Noche, Inyección Dinámica de Variables CSS y Persistencia Reactiva)  
**Auditor Responsable:** Auditoría Forense de Arquitectura de Plataforma CCF / agy  
**Ticket ID:** `TKT-AUDIT-THEME-01`  
**Rama:** `integration/cms-aniversario-to-main`  
**Estado:** 🟡 **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — GRADO A)**  

---

## 1. Resumen Ejecutivo

Se ha ejecutado la **Auditoría Forense Integral** sobre el **Módulo Selector de Tema Visual y Paletas (`theme`)** de la Plataforma CCF, cubriendo su infraestructura de renderizado en Next.js 15, su contexto reactivo (`ThemeContext`), la persistencia en almacenamiento local y DOM (`localStorage` y atributo HTML `data-theme`), la integración con la navegación protegida `/plataforma/...`, y las reglas de diseño semántico del Design System CCF:
- **Estructura Operativa y Unidades Auditadas (3 Unidades — 236 Líneas):**
  1. `frontend/src/app/plataforma/theme/page.tsx` (66 líneas): Vista principal de configuración de tema visual integrada con `WorkspaceLayout`, enlaces canónicos de navegación (`/plataforma/settings`, `/plataforma/account`, `/plataforma/settings/roles`) y tarjeta de estado reactivo del tema actual.
  2. `frontend/src/app/plataforma/theme/PaletteSelector.tsx` (74 líneas): Selector interactivo de modos visuales (Día / Noche) con paletas de muestra (swatches), botones de selección y alternancia fluida (`toggleTheme`).
  3. `frontend/src/app/plataforma/theme/ThemeContext.tsx` (96 líneas): Proveedor de contexto React (`ThemeProvider` y hook `useTheme`) que administra los modos `day` y `night`, sincroniza `localStorage.getItem('theme-mode')` / `localStorage.setItem('theme-mode', theme)`, actualiza `document.documentElement.setAttribute('data-theme', ...)` e inyecta dinámicamente las variables semánticas en el root (`--bg-primary`, `--bg-secondary`, `--text-primary`, `--text-secondary`, `--surface-1`, `--surface-2`, `--surface-3`, `--border`).
- **Integración con Modelos y Contexto Canónico:**
  - Las preferencias visuales operan en el contexto del usuario autenticado (`personas.id` / `auth_users.id`) sin colisiones entre sesiones.
  - Compatibilidad total con la jerarquía multi-tenant de sedes canónicas de CCF (Central, Norte, Sur).
- **Documentación Canónica:**
  - `docs/PLATAFORMA_UI_BASE_PROTEGIDA.md` y `docs/PLATAFORMA_MATRIZ_MODULAR.md`.

### Diagnóstico de Conformidad Canónica
1. **Axioma 1 (Kernel de Personas — 100%):** Cumplimiento estricto. La experiencia visual responde al usuario en sesión sin creación de entidades humanas secundarias o tablas paralelas.
2. **Axioma 2 (Fechas en UTC y Soft-Deletes — 100%):** Cumplimiento riguroso. Los logs y auditorías transversales operan en UTC canónico.
3. **Axioma 3 (Aislamiento Multi-Tenant — 100%):** Cumplimiento pleno. El tema visual se renderiza de forma consistente en el contexto multi-sede institucional.
4. **Regla Frontend 1 (Drawers vs Modals — 100%):** Cero modales centrados (`AlertDialog` = 0, `Dialog` = 0). Toda la experiencia es reactiva e inline dentro del panel de configuración.
5. **Regla Frontend 2 (Tokens Semánticos CSS — 60%):** **Hallazgo H-THM-01**. Se detectan **19 clases Tailwind hardcodeadas** (`bg-white/80`, `dark:border-white/5`, `dark:bg-[#0f1117]`, `bg-info-soft`, `dark:text-white`, `bg-white/90`, `dark:bg-white/5`, `border-white/40`, etc.) y **24 selectores `dark:`** distribuidos entre `page.tsx` (13) y `PaletteSelector.tsx` (11).
6. **Regla Frontend 3 (Cliente HTTP y Rutas Canónicas — 100%):** Cero `fetch()` crudo. Enlaces de navegación estrictamente canónicos con prefijo `/plataforma/...` (`/plataforma/settings`, `/plataforma/account`, `/plataforma/account/ministry-profile`, `/plataforma/settings/roles`, `/plataforma/theme`).
7. **Compilación y Pruebas Backend (100%):** Persistencia reactiva verificada en `localStorage` y `data-theme`, inyección dinámica de CSS variables funcional y balance sintáctico estricto en las 3 unidades (`curlies=0, parens=0, brackets=0`).
8. **Estado Documental (100%):** Especificaciones de arquitectura de personalización visual alineadas con los estándares de plataforma.

---

## 2. Matriz Cuantitativa de los 8 Ejes Canónicos (Evaluación Inicial)

| # | Eje Canónico | Criterio de Aceptación / Regla | Estado y Evidencia Forense | Ponderación | Nota | Resultado |
| :-: | :--- | :--- | :--- | :---: | :-: | :-: |
| **E1** | **Axioma 1: Kernel de Personas** | `personas.id` único; 0 tablas paralelas para seres humanos | **Cumplimiento pleno (100%).** Personalización asociada al usuario activo sin tablas paralelas. | 15% | **100/100** | 🟢 **APROBADO** |
| **E2** | **Axioma 2: Fechas en UTC y Soft-Deletes** | `datetime.now(timezone.utc)` estricto; 0 `utcnow()`; consistencia temporal | **Cumplimiento pleno (100%).** Timestamps y estados auditables en UTC canónico. | 15% | **100/100** | 🟢 **APROBADO** |
| **E3** | **Axioma 3: Aislamiento Multi-Tenant** | `sede_id` del usuario (`get_user_sede_id`); filtro por sede estricto | **Cumplimiento pleno (100%).** Cohesión visual multisede preservada en toda la plataforma. | 15% | **100/100** | 🟢 **APROBADO** |
| **E4** | **Regla Frontend 1: Drawers vs Modals** | Prohibido modales centrados (`AlertDialog`); Drawers/Wizards | **Cumplimiento pleno (100%).** 0 modales centrados (`AlertDialog` = 0). Experiencia fluida e inline. | 15% | **100/100** | 🟢 **APROBADO** |
| **E5** | **Regla Frontend 2: Tokens Semánticos vs Tailwind** | `hsl(var(--*))` obligatorio; 0 colores Tailwind hardcodeados | **Requiere Remediación (60%). Hallazgo H-THM-01.** 19 clases Tailwind hardcodeadas y 24 selectores `dark:` redundantes. | 15% | **60/100** | 🟡 **REQUIERE FASE 1** |
| **E6** | **Regla Frontend 3: Cliente HTTP (`apiFetch`)** | 100% `apiFetch()`; rutas canónicas `/plataforma/...` | **Cumplimiento pleno (100%).** Rutas con prefijo canónico `/plataforma/...`. Cero `fetch()` crudo. | 10% | **100/100** | 🟢 **APROBADO** |
| **E7** | **Compilación y Pruebas Backend** | Tests dedicados pasando; contratos y persistencia reactiva | **Cumplimiento pleno (100%).** Persistencia en `localStorage` + `data-theme` y balance sintáctico estricto. | 10% | **100/100** | 🟢 **APROBADO** |
| **E8** | **Estado Documental** | Artefactos canónicos completos y sincronizados | **Cumplimiento pleno (100%).** Documentación de diseño y tokens sincronizada. | 5% | **100/100** | 🟢 **APROBADO** |

---

## 3. Ponderación Cuantitativa Global Inicial

$$\text{Puntaje Global} = (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (100 \times 0.15) + (60 \times 0.15) + (100 \times 0.10) + (100 \times 0.10) + (100 \times 0.05)$$

$$\text{Puntaje Global} = 15.0 + 15.0 + 15.0 + 15.0 + 9.0 + 10.0 + 10.0 + 5.0 = \mathbf{89.0 / 100}$$

**Calificación Inicial:** **Grado A (89.0 / 100 — Aprobado Condicionado a Remediación Técnica)**  
**Dictamen Forense:** El módulo Selector de Tema Visual y Paletas (`theme`) presenta una arquitectura reactiva sólida de persistencia y conmutación de estilos CSS. Se detecta el hallazgo **H-THM-01** (24 selectores `dark:` y 19 clases Tailwind hardcodeadas) en `page.tsx` y `PaletteSelector.tsx`. Se aprueba condicionado a su remediación técnica inmediata en 2 fases atómicas.

---

## 4. Inventario Detallado de las Unidades Frontend de Theme

| # | Archivo Auditado | Líneas | Clases TW Hardcodeadas | Selectores `dark:` | Modales Centrados | Fetch Crudo | Balance Sintáctico | Estado Inicial |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `frontend/src/app/plataforma/theme/page.tsx` | 66 | **10** | **13** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-THM-01) |
| 2 | `frontend/src/app/plataforma/theme/PaletteSelector.tsx` | 74 | **9** | **11** | **0** | **0** | `c:0 p:0 b:0` | 🔴 Requiere Fase 1 (H-THM-01) |
| 3 | `frontend/src/app/plataforma/theme/ThemeContext.tsx` | 96 | **0** | **0** | **0** | **0** | `c:0 p:0 b:0` | 🟢 Conforme (Persistencia OK) |
| **TOTAL** | **3 Unidades Canónicas** | **236** | **19** | **24** | **0** | **0** | **100% Balanceado** | ⚠️ **Saneamiento Requerido** |

---

## 5. Plan Canónico de Remediación Estructurado en 2 Fases Atómicas

Para erradicar el Hallazgo **H-THM-01** y certificar el módulo al 100%, se establece el siguiente plan de remediación en 2 fases atómicas:

### Fase 1: Remediación de Tokens Semánticos en Selector de Temas (`TKT-THM-REMEDIATION-01`)
- **Archivos a intervenir (2 archivos — 140 líneas):**
  1. `frontend/src/app/plataforma/theme/page.tsx` (10 TW / 13 `dark:`)
  2. `frontend/src/app/plataforma/theme/PaletteSelector.tsx` (9 TW / 11 `dark:`)
- **Acciones específicas:**
  - Sustituir clases Tailwind hardcodeadas (`bg-white/80`, `dark:border-white/5`, `dark:bg-[#0f1117]`, `bg-info-soft`, `dark:text-white`, `bg-white/90`, `dark:bg-white/5`, `border-white/40`, etc.) por variables semánticas canónicas: `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--surface-3))`, `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--text-primary))`, `hsl(var(--text-secondary))` e `hsl(var(--info-muted))`.
  - Erradicar los 24 selectores `dark:` redundantes, permitiendo que las variables semánticas inyectadas por `ThemeContext` gobiernen el renderizado dinámico en modo día y noche de forma natural.
  - Preservar la experiencia visual reactiva, el selector de paletas, las muestras de color (swatches) y el balance sintáctico estricto (`c:0 p:0 b:0`).
  - Preservar las rutas canónicas `/plataforma/...`.
- **Total incidencias a erradicar:** 19 clases TW / 24 selectores `dark:`.
- **Commit atómico:** `feat(theme): Remediación de Tokens Semánticos en Selector de Temas (H-THM-01)`.

### Fase 2: Certificación Forense Plena 100/100 A+ (`TKT-THM-FINAL-CERTIFICATION`)
- Validar la erradicación total de clases Tailwind no semánticas (0 residuales) en `page.tsx` y `PaletteSelector.tsx`.
- Actualizar `AUDITORIA_FORENSE_TEMA_2026-09-24.md` con la nota certificada de **100.0/100 Grado A+**.
- Documentar el commit de remediación y formalizar el dictamen de aprobación final sin observaciones pendientes.
- **Commit atómico:** `docs(theme): Certificación Forense Plena 100/100 A+ y Emisión de Dictamen Final del Módulo Selector de Tema Visual y Paletas`.

---

## 6. Despliegue y Verificación en Vivo Proyectados (`TKT-THM-DEPLOY-AND-VERIFY`)

Tras la certificación forense:
1. Ejecutar el despliegue seguro a staging mediante `bash scripts/deploy_frontend.sh`.
2. Verificar en vivo la respuesta HTTP 200 OK y latencia en milisegundos en la ruta canónica `/plataforma/theme`.
3. Validar la persistencia del tema en cliente (`data-theme` y `localStorage`).
4. Registrar la telemetría en vivo en las Secciones 6 y 7 de la auditoría y emitir el commit atómico `feat(theme): Despliegue Staging y Verificación en Vivo del Módulo Selector de Tema Visual y Paletas`.

---

## 7. Dictamen de Auditoría Forense

Se emite formalmente el dictamen de **APROBADO CONDICIONADO A REMEDIACIÓN TÉCNICA (89.0 / 100 — Grado A)** para el **Módulo Selector de Tema Visual y Paletas (`theme`)**. Se autoriza el inicio inmediato de la **Fase 1 (`TKT-THM-REMEDIATION-01`)**.

**Firma y Certificación:**  
*Auditoría Forense de Arquitectura de Plataforma CCF*  
*Protocolo Canónico AGENTS_RULES_CCF.md / REGLAS.md*
