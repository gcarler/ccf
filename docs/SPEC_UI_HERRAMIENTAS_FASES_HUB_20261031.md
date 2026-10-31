# Especificación Técnica Canónica: Unificación de la Herramienta "Fases" en el ProjectManagementHubDrawer y Contención Segura de Viewport

- **Fecha:** 2026-10-31
- **Ticket ID:** `TKT-PROJECTS-UI-PHASES-HUB-20261031-01`
- **Autor / Arquitectura:** `agy` (Lead Architecture & Coordination)
- **Agente Asignado:** `freebuff` (Frontend Developer & Refactoring Specialist)
- **Revisor / Auditor:** `agy`
- **Módulo:** `projects` (`frontend/src/app/plataforma/projects/[id]`, `frontend/src/components/projects`, `frontend/src/components/ui`)
- **Estado:** ESPECIFICACIÓN CANÓNICA APROBADA

---

## 1. Contexto y Requerimiento del Usuario

El usuario reportó un comportamiento inconsistente y problemático en la navegación de herramientas dentro del detalle de proyecto (`/plataforma/projects/[id]`):

> *"cuando ingresamos al menú de herramientas hay una opción que se llama “Fases” y comportamiento de esa herramienta fases es diferente al comportamiento de resto por qué el resto lo que hace es desplegar la herramienta hacia el lado derecho del menú de herramientas está por el contrario lo que hace es superponer o sea menú herramientas Entonces yo creo que todas deben tener el comportamiento igual o sea el comportamiento de Hacia dónde se despliega entonces me gusta que uno le da click a una herramienta y automáticamente se despliega otro Sí de bar derecho al lado derecho de donde está el menú de herramientas pero es fases no tiene ese comportamiento entonces creo que en eso tenemos que ser juiciosos y que nunca cuando se despliegue esa herramienta las opciones de manejarlas nunca queden ocultas de la pantalla porque si se sitúan si él decide llevar dos está abierto deben llegar hasta donde llega así de bardos si decide dos está ocultos deben llegar hasta donde llega el Side bar uno y si lleva dos y el uno están ocultos pues toda la pantalla nunca irse a tal lugar donde no se pueda ver o gestionar porque no hay manera entonces de minimizarla ni de cerrarlas entonces porfa revisa ese tema creo que lo puedes manejar con Freebuff"*

---

## 2. Diagnóstico y Causa Raíz

### 2.1 Aislamiento de "Fases" respecto al Hub de Herramientas
1. En `frontend/src/app/plataforma/projects/[id]/page.tsx`, la acción `phases` en `projectActions` ejecutaba `setShowPhaseManager(true)`, montando directamente un `<PhaseManagerDrawer>` superior fuera del `ProjectManagementHubDrawer`.
2. `PhaseManagerDrawer.tsx` envolvía todo su contenido en su propio `<RightPanel>` fijo e independiente con backdrop, superponiéndose sobre el `ProjectContextPanel` (sidebar derecho 1 de la pantalla) en lugar de acoplarse como una pestaña en el hub de herramientas (sidebar derecho 2).
3. A diferencia del resto de herramientas (Componentes EDT, WBS, Matriz PMO, Etiquetas, KPIs, Avance, Presupuesto, etc.), "Fases" carecía de:
   - Tira de pestañas unificada.
   - Botón de maximizar/minimizar (`Maximize2` / `Minimize2`).
   - Selector dropdown de herramientas.
   - Modo incrustado (`embedded`).

### 2.2 Desbordamiento y Confinamiento de Viewport (Sidebars S1 y S2)
1. `RightPanel.tsx` calculaba su redimensión y maximizado con un `reservedWidth` hardcodeado de `48 + effectiveOffset`, permitiendo que al expandirse hacia la izquierda pudiera cubrir los sidebars de navegación de la plataforma (S1: mini-sidebar principal de ~72px, y S2: sidebar expandido de proyecto de ~280px).
2. Cuando el panel se maximizaba (`maximized = true`), utilizaba la clase `w-screen max-w-none` (100vw), cubriendo indiscriminadamente S1 y S2, lo que provocaba que en ciertas resoluciones o configuraciones de zoom los controles de cierre, minimizado y gestión pudieran quedar desalineados o inaccesibles.

---

## 3. Solución Canónica y Requisitos de Implementación

### 3.1 Unificación de Fases en `ProjectManagementHubDrawer`
1. **Tipo Canónico `ProjectHubModuleKey`** (`frontend/src/components/projects/ProjectManagementHubDrawer.tsx`):
   - Agregar `'phases'` a la unión:
     ```typescript
     export type ProjectHubModuleKey =
       | 'phases'
       | 'components'
       | 'wbs'
       | 'pmo'
       ...
     ```
2. **Metadatos Canónicos `PROJECT_HUB_MODULE_META`**:
   - Registrar la entrada de Fases:
     ```typescript
     { key: 'phases', label: 'Fases', icon: Edit3 }
     ```
3. **Soporte `embedded` en `PhaseManagerDrawer.tsx`**:
   - Ampliar la interfaz `Props`:
     ```typescript
     interface Props {
       projectId: string;
       onClose: () => void;
       isOpen?: boolean;
       embedded?: boolean;
     }
     ```
   - Pasar `embedded={embedded}` y `isOpen={isOpen ?? true}` al `<RightPanel>` dentro de `PhaseManagerDrawer.tsx`.
   - Cuando `embedded` sea `true`, `RightPanel` ya se renderiza limpiamente como `<section className="flex min-h-0 min-w-0 flex-1 flex-col">`, integrándose sin duplicar cabeceras fijas, bordes externos ni listeners de redimensión.
4. **Página de Proyecto (`frontend/src/app/plataforma/projects/[id]/page.tsx`)**:
   - Actualizar `projectActions`:
     ```typescript
     { key: 'phases', label: 'Fases', icon: Edit3, onSelect: () => openHubModule('phases') },
     ```
   - Agregar el renderer en `moduleRenderers`:
     ```typescript
     phases: () => (
       <PhaseManagerDrawer
         embedded
         isOpen
         projectId={project?.id || id}
         onClose={() => closeHubModule('phases')}
       />
     ),
     ```
   - Eliminar el estado residual `showPhaseManager` y su renderizado aislado condicional `{showPhaseManager && <PhaseManagerDrawer ... />}`.

### 3.2 Confinamiento Dinámico y Clamping de Viewport en `RightPanel.tsx`
El comportamiento respecto a los sidebars izquierdos (`layers.S1` y `layers.S2`) debe cumplir estrictamente las tres reglas canónicas solicitadas por el usuario:
1. **Regla S2 Abierto:**
   - Si `layers.S2` está visible: el ancho máximo disponible del panel hacia la izquierda debe detenerse exactamente donde termina S2 (`viewportWidth - (s1Width + s2Width)`). No debe superponerse ni ocultar S2.
2. **Regla S2 Oculto / S1 Abierto:**
   - Si `layers.S2` está cerrado/oculto pero `layers.S1` está visible: el ancho máximo disponible debe detenerse donde termina S1 (`viewportWidth - s1Width`).
3. **Regla Ambos Ocultos:**
   - Si tanto S1 como S2 están ocultos: el ancho máximo puede ocupar toda la pantalla (`100vw`).
4. **Garantía de Controles Visibles:**
   - Ningún botón de cierre (`X`), botón de pantalla completa (`Maximize2`/`Minimize2`), pestaña ni botón de acción debe quedar fuera de la pantalla (`overflow-hidden`, padding seguro y contención en viewport garantizados en desktop y móvil).
   - En `RightPanel.tsx`, computar dinámicamente el `leftBoundary`:
     ```typescript
     // S1 ocupa ~72px en desktop cuando está visible; S2 ocupa el ancho configurado (default 280px)
     const s1Width = layers.S1 ? 72 : 0;
     const s2Width = layers.S2
       ? (typeof window !== 'undefined'
           ? (Number.parseInt(localStorage.getItem('s2Width') ?? '', 10) || 280)
           : 280)
       : 0;
     const leftBoundary = viewportWidth >= 1024
       ? (layers.S2 ? s1Width + s2Width : (layers.S1 ? s1Width : 0))
       : 0;
     const maxAvailableWidth = viewportWidth > 0
       ? Math.max(320, viewportWidth - leftBoundary - effectiveOffset)
       : undefined;
     ```
   - Actualizar `useResizablePanel` para que `reservedWidth` use `Math.max(48, leftBoundary + effectiveOffset)`.
   - Cuando `maximized` sea `true`, aplicar ancho `calc(100vw - ${leftBoundary + effectiveOffset}px)` en desktop (o `100vw` si `leftBoundary === 0`), garantizando que la barra de control permanezca accesible y visible.

---

## 4. Criterios de Aceptación

1. **Unificación Funcional:**
   - Hacer clic en "Fases" en el menú de herramientas de `ProjectContextPanel` abre la herramienta como pestaña dentro de `ProjectManagementHubDrawer` (sidebar derecho 2), exactamente igual que Componentes, EDT, Presupuesto, etc.
   - La pestaña de Fases se puede cerrar individualmente (botón `X` en la pestaña), minimizar, maximizar y alternar con otras pestañas abiertas.
2. **Confinamiento de Viewport:**
   - Con S1 y S2 abiertos, maximizar o redimensionar el hub hacia la izquierda se detiene en el límite derecho de S2, sin cubrirlo.
   - Con S2 oculto y S1 visible, el hub se detiene en el límite derecho de S1.
   - Con ambos ocultos, el hub puede extenderse a toda la pantalla.
   - Todos los botones de control (cerrar, minimizar/maximizar, tabs, acciones de fase) permanecen 100% visibles y operativos en cualquier resolución.
3. **Integridad de Código y Estilos:**
   - Cero tokens hardcodeados: usar únicamente tokens semánticos del Design System (`hsl(var(--...))`).
   - Cero errores de TypeScript (`npx tsc --noEmit`).
   - Todos los tests unitarios (`ProjectManagementHubDrawer.test.tsx`, `PhaseManagerDrawer.test.tsx`, `RightPanel.test.tsx`) pasan exitosamente.
4. **Protocolo Git:**
   - Commit semántico atómico: `fix(cms): unificar herramienta fases en project hub drawer con confinamiento de viewport`.
   - PROHIBIDO el uso de `--no-verify`. Todos los hooks de calidad (`pre-push`) deben ejecutarse limpiamente.
