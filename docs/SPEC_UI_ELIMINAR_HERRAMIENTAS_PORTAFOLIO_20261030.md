# Especificación Canónica: Eliminación del Botón Herramientas del Encabezado del Portafolio

## 1. Contexto y Origen del Requerimiento
El usuario reportó un error de arquitectura y ubicación de UI en la vista de lista/portafolio de proyectos (`/plataforma/projects`):
* **Captura proporcionada por el usuario:** [captura_herramientas_portafolio.png](file:///root/ccf/docs/capturas_ui_proyectos_20261030/captura_herramientas_portafolio.png) (Google Drive: `https://drive.google.com/file/d/1PHvjtIjFUlsOoiC8p4IqzYhEXYTCzUpE/view?usp=sharing`).
* **Hallazgo:** En la barra superior de acciones (`ProjectsShell` -> `rightActions`), al lado de `+ NUEVO PROYECTO`, se encuentra un botón `🔧 HERRAMIENTAS` con un dropdown a la Matriz PMO.

---

## 2. Regla Mandatoria del Usuario (Innegociable)
> **"Ese botón está mal ubicado en esa parte de la plataforma porque las herramientas se gestionan al interior de cada proyecto. Recuerda que el menú de herramientas se despliega sólo en el sidebar derecho, no hace parte del Head ni del encabezado de la plataforma."**

---

## 3. Plan de Acción y Alcance Técnico

### A. Archivos Afectados
1. `frontend/src/app/plataforma/projects/ProjectsClient.tsx`:
   - Eliminar el bloque `<div ref={toolsMenuRef} className="relative">...<button>Herramientas</button>...</div>` en `rightActions` de `ProjectsShell`.
   - Eliminar el estado `toolsMenuOpen`, la referencia `toolsMenuRef` y el hook `useEffect` que escucha clicks fuera del menú y la tecla Escape.
   - Eliminar `showPMOPortfolio` y `<ProjectPMOPortfolioDrawer />` si no se invocan en esta vista de portafolio, o limpiar los imports huérfanos (`Wrench`, `BarChart3`, etc.).
   - Mantener intacto el botón `+ Nuevo Proyecto` y su funcionalidad.
2. `frontend/src/app/plataforma/projects/ProjectsClient.test.tsx`:
   - Adaptar o remover el test `it('abre la Matriz PMO CPI×SPI desde el menú Herramientas del portafolio')` para reflejar que dicho botón ya no existe en el encabezado general.
   - Verificar que todos los tests de la suite sigan pasando limpiamente.

---

## 4. Criterios de Aceptación Técnicos
1. **Header limpio:** En `/plataforma/projects`, la barra de acciones superior NO muestra el botón "Herramientas". Únicamente se muestra "+ Nuevo Proyecto" junto al buscador.
2. **Confinamiento de Herramientas:** Las herramientas (EVM, Gobernanza PMI, Matriz PMO, etc.) se gestionan exclusivamente al interior de cada proyecto en el sidebar derecho (`ProjectContextPanel`).
3. **TypeScript estricto:** Compilación limpia sin errores con `npx tsc --noEmit`.
4. **Tests Unitarios:** Suite de `ProjectsClient.test.tsx` y suites de proyectos pasando 100%.
5. **Git Protocol:**
   - Crear rama de trabajo: `integration/projects-ui-remove-portfolio-tools-20261030`.
   - Push seguro con `scripts/push_branch.sh origin integration/projects-ui-remove-portfolio-tools-20261030` estrictamente sin `--no-verify`.
   - Entrega mediante `ccf_agent_bridge.py submit`.
