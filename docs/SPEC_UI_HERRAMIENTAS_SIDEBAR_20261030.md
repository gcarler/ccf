# Especificación Canónica: Unificación del Módulo de Herramientas Exclusivamente en el Sidebar Derecho

## 1. Contexto y Origen del Requerimiento
El usuario compartió capturas de pantalla de la interfaz en producción (`ministerioselfaro.org/plataforma/projects/...`) con errores críticos de layout, duplicidad de controles y desorden visual:
- Carpeta origen en Google Drive: `https://drive.google.com/drive/folders/1pexE4GdKlUcI0OVxWRL9ZAbvcxBXoHy2`
- Copias locales de las capturas disponibles en:
  - `docs/capturas_ui_proyectos_20261030/captura_20-49-53.png`
  - `docs/capturas_ui_proyectos_20261030/captura_20-52-03.png`
  - `docs/capturas_ui_proyectos_20261030/captura_20-52-40.png`

---

## 2. Regla Mandatoria del Usuario (Innegociable)
> **"Herramientas… EVM / CPI×SPI Gobernanza PMI- solo pueden estar en el modulo de herrameintas, y el modulo de herramientas no se puede duplicar y solo debe estar en el sidebar derecho."**

---

## 3. Análisis de Errores Detectados en las Capturas

### A. Botones y selector duplicados en el Control Bar superior (`captura_20-49-53.png`)
* **Ubicación:** `frontend/src/app/plataforma/projects/[id]/page.tsx` (líneas 895–934).
* **Problema:** En la barra superior de acciones (al lado de `Buscar en esta vista...` y `+ NUEVA ACTIVIDAD`), existen:
  1. `<select id="project-detail-tools-switcher">` ("Herramientas…")
  2. `<button data-testid="project-detail-quick-evm">` ("EVM / CPI×SPI")
  3. `<button data-testid="project-detail-quick-governance">` ("Gobernanza PMI")
* **Corrección:** **ELIMINAR** estos tres controles de la barra superior. Ningún acceso de herramientas o botones directos debe poblar el header general.

### B. Duplicidad de Hub de Herramientas y colisión de layout (`captura_20-52-03.png` y `captura_20-52-40.png`)
* **Ubicación:** `frontend/src/components/projects/ProjectManagementHubDrawer.tsx` y su invocación en `page.tsx` con `offsetRight={effectiveContextOffset}`.
* **Problema:**
  - Al hacer click en una herramienta, se abre un panel flotante central/horizontal gigante ("CENTRO DE GESTIÓN DEL PROYECTO") con pestañas superiores (`Componentes EDT`, `Matriz PMO`, `Etiquetas`, `KPIs`, `Avance`, `Riesgos`, etc.) desplazado hacia la izquierda por `offsetRight`.
  - Al mismo tiempo, el panel lateral derecho (`ProjectContextPanel`) permanece abierto mostrando la lista de herramientas en su pestaña "Herramientas".
  - Esto genera **dos paneles de herramientas compitiendo simultáneamente**, y en pantallas medianas o completas (`captura_20-52-40.png`), el contenido principal a la izquierda queda completamente **aplastado y con textos mutilados/cortados** ("RESO", "LETADAS ENTRE EL TOTAL...").
* **Corrección:**
  - El módulo de herramientas **NO se puede duplicar**.
  - Debe residir y desplegarse **ÚNICA Y EXCLUSIVAMENTE en el Sidebar Derecho** (Right Drawer).
  - Al seleccionar una herramienta (EVM, Gobernanza PMI, Avance, Matriz PMO, Componentes EDT, etc.) desde la pestaña `Herramientas` del sidebar derecho, la vista de la herramienta debe renderizarse dentro del Drawer derecho estándar (o abrir el Drawer propio de la herramienta en el lateral derecho cerrando/sustituyendo limpiamente el selector), **NUNCA** como un segundo panel flotante lateral que aplaste la vista principal de la pantalla.

---

## 4. Criterios de Aceptación Técnicos
1. **Header limpio:** Cero selectores "Herramientas…" ni botones "EVM / CPI×SPI" o "Gobernanza PMI" en el header/control bar de `page.tsx`.
2. **Sidebar Derecho Canónico:** Todas las herramientas (EVM, Gobernanza PMI, Avance, etc.) se acceden y visualizan exclusivamente a través del sidebar derecho.
3. **No duplicación:** No coexisten paneles paralelos de herramientas comprimiendo el ancho de la página principal.
4. **Reglas de UI / DS:**
   - Drawers laterales deslizantes, NO modals centrados ni alerts (`AGENTS_RULES_CCF.md`).
   - Tokens semánticos (`hsl(var(--surface-1))`, `hsl(var(--border))`, etc.). Cero colores hardcodeados de Tailwind.
5. **Calidad de Código y Tests:**
   - Compilación limpia sin errores TypeScript (`tsc --noEmit`).
   - Tests de vitest pasando (`npm run test:unit:run` o tests de proyectos afectados).
6. **Entrega Git:**
   - Rama: `integration/projects-tools-sidebar-20261030`
   - Push seguro mediante `bash scripts/push_branch.sh origin integration/projects-tools-sidebar-20261030` con todos los hooks y pre-push activos, **estrictamente sin `--no-verify`**.
