# Plan de Refinamiento Extremo (Polish to 100%)

Este plan detalla los hitos minuciosos para llevar la plataforma CCF desde un estado "funcional" a una experiencia de usuario de "clase mundial", comparable a las mejores herramientas SaaS (como ClickUp, Linear o Notion). 

El enfoque ya no es "hacer que funcione", sino "hacer que sea un placer usarlo".

## Hito 1: Data Grid Industrial (Tablas de Alto Rendimiento)
**Objetivo:** Transformar las tablas estáticas (CRM, Proyectos, Soporte) en Data Grids interactivos de alto rendimiento.

- [ ] **Migración a TanStack Table:** Implementar la lógica de `@tanstack/react-table` en las vistas principales.
- [ ] **Redimensionamiento de Columnas (Resizing):** Permitir a los usuarios arrastrar los bordes de las columnas para ajustar su ancho.
- [ ] **Ordenamiento Dinámico (Sorting):** Ordenar por fecha, alfabéticamente o por prioridad haciendo clic en los encabezados.
- [ ] **Filtros Avanzados en Línea:** Menús popover (Radix UI) en cada encabezado para filtrar por múltiples criterios sin recargar la página.
- [ ] **Fijación de Columnas (Pinning):** Congelar la columna de "Nombre/Título" a la izquierda en pantallas pequeñas.

## Hito 2: Ecosistema de Selectores Inteligentes
**Objetivo:** Eliminar los `select` nativos y reemplazarlos por componentes de búsqueda profunda con soporte para teclado.

- [ ] **Selector de Asignados (User Picker):** Dropdown con barra de búsqueda integrada y avatares para asignar tareas o tickets, utilizando `<Command>` (CMDK).
- [ ] **Selector de Fechas Pro (Date Picker):** Calendario interactivo flotante (usando librerías como `react-day-picker`) integrado con validación para fechas límite y eventos.
- [ ] **Selector de Etiquetas/Categorías (Tags):** Sistema de etiquetas con colores personalizables para el CRM y Soporte, permitiendo selección múltiple.

## Hito 3: Contexto Dinámico y Reducción de Carga Cognitiva
**Objetivo:** Anticiparse a la necesidad del usuario, mostrando información sin necesidad de clics adicionales.

- [ ] **Tarjetas de Contexto (Hover Cards):** Al pasar el ratón sobre el nombre de un miembro o tarea, mostrar un Popover con un resumen rápido sin abrir el Drawer.
- [ ] **Edición en Línea Avanzada:** Evolucionar el `InlineEdit` actual para soportar áreas de texto (descripciones largas) y guardado automático con indicador de "Guardando...".
- [ ] **Estados Vacíos Ilustrados (Empty States):** Reemplazar textos genéricos por gráficos amigables con llamadas a la acción claras cuando no hay datos.

## Hito 4: Accesibilidad Total (a11y) y Teclado
**Objetivo:** Permitir que los "power users" operen la plataforma sin tocar el ratón.

- [ ] **Navegación por Teclado:** Asegurar que todos los modales, dropdowns y botones sean accesibles mediante `Tab` y las flechas direccionales.
- [ ] **Expansión del Centro de Comando:** Añadir la capacidad de buscar *contenido específico* (ej. "Buscar miembro Juan Pérez") directamente desde `Ctrl+K`.
- [ ] **Soporte de Lectores de Pantalla:** Atributos `aria-*` correctos en todos los componentes interactivos creados con Radix UI.

## Hito 5: Rendimiento Percibido y Micro-interacciones
**Objetivo:** Que la interfaz se sienta "inmediata" sin importar la velocidad de la red.

- [ ] **Mutaciones Optimistas:** Actualizar la UI instantáneamente antes de que el servidor responda (y revertir si falla) en acciones críticas como marcar tareas completadas.
- [ ] **Carga Diferida (Lazy Loading):** Dividir el código de los componentes pesados (como los mapas o el editor de texto enriquecido) para que la aplicación cargue en milisegundos.
- [ ] **Sonido y Háptica Opcional:** Pequeños efectos de sonido (opcionales) al completar una tarea o cerrar un ticket, similar a la experiencia en videojuegos de productividad.
