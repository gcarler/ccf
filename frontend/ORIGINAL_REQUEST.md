# Original User Request

## Initial Request — 2026-07-31T20:32:28Z

<USER_REQUEST>
Finalizar y pulir la integración del editor visual Puck en Next.js para dejarlo 100% Pro, incorporando sincronización de variables CSS del tema del sitio, selector multimedia visual (MediaPicker), asistentes de redacción con Inteligencia Artificial, auto-guardado automático de cambios, y suite de pruebas E2E con Playwright antes de migrar la ruta principal.

Working directory: /root/ccf/frontend
Integrity mode: development

---

## Requisitos del Proyecto

### R1. Sincronización del Tema y Estilos CSS (Fase 1)
- Integrar las fuentes tipográficas del sistema (Outfit, Inter) y variables CSS personalizadas del tema de la sede (`--site-*`) en el lienzo del editor Puck.
- El canvas de Puck debe deshabilitar el aislamiento de iframe (`iframe={{ enabled: false }}`) para heredar los estilos globales de Tailwind y reaccionar dinámicamente a los colores del tema cargado (`var(--site-background)`).

### R2. Integración de Selector de Medios - MediaPicker (Fase 2)
- Integrar el componente React `MediaPicker` en los campos de tipo imagen del editor Puck (Hero `bg_image`, tarjetas `image_url` y elementos de la galería `url`).
- Al hacer clic en "Seleccionar Imagen", se debe desplegar el drawer del MediaPicker; al elegir una imagen del servidor (SeaweedFS), se debe actualizar el valor de la propiedad del bloque correspondiente.

### R3. Asistentes de Redacción con Inteligencia Artificial (Fase 3)
- Integrar campos de asistencia de IA (`AiTextInput`) en inputs y textareas de Puck (títulos y cuerpos de Hero, Rich Text y CTA Banner).
- Permitir ingresar un tema breve y llamar al endpoint `/system/ai/generate` para rellenar de forma automática los campos del bloque con textos sugeridos.

### R4. Catálogo de Bloques Complejos (Fase 4)
- Registrar y maquetar los componentes `gallery` (Galería) y `cards` (Tarjetas) con soporte de campos de listas dinámicas (tipo `array` en Puck) para añadir, reordenar y eliminar sub-elementos.

### R5. Auto-guardado Automático y Botón Manual de Guardado
- Implementar un mecanismo de guardado dual:
  1. **Auto-guardado automático:** Con debounce (por ejemplo, 2-5 segundos) que guarde los cambios en segundo plano mientras el usuario edita de forma transparente.
  2. **Botón de Guardar Manual:** Un botón de "Publicar" o "Guardar" visible en la cabecera del editor Puck que permita al usuario forzar una sincronización inmediata y manual con la base de datos en cualquier momento.

### R6. Suite de Pruebas E2E y Migración (Fase 5)
- Escribir una prueba automatizada con Playwright en `tests/e2e/cms/builder-puck-flow.spec.ts` que simule:
  1. Ingreso a `/plataforma/cms/builder-puck?site=ccf&page=home`.
  2. Adición y edición de una sección Hero con imagen seleccionada mediante el MediaPicker y texto generado con IA.
  3. Guardado automático exitoso y verificación de que se actualizó el contenido en base de datos.
- Reemplazar oficialmente la ruta `/plataforma/cms/builder/page.tsx` por la versión Puck una vez que todas las pruebas pasen en verde.

---

## Criterios de Aceptación

### Diseño y UX
- [ ] El editor visual Puck hereda correctamente el color de fondo `--site-background` en el canvas de edición.
- [ ] No es necesario copiar y pegar URLs para cambiar imágenes; el drawer de `MediaPicker` abre y actualiza el campo de imagen del bloque correspondiente.

### Guardado e Integración
- [ ] Los cambios se auto-guardan en segundo plano en base de datos automáticamente al modificar o mover bloques, Y existe además un botón manual de guardar/publicar en la cabecera que fuerza la sincronización síncrona inmediata.

### Inteligencia Artificial
- [ ] Los bloques principales (Hero, Rich Text, CTA Banner) muestran el input de redacción de IA y el botón "Redactar IA" genera textos del largo y tono adecuados sin errores de red.

### Pruebas y QA
- [ ] `npm run typecheck` en el frontend finaliza con 0 errores de compilación.
- [ ] `npm run lint` en el frontend finaliza con 0 errores y advertencias.
- [ ] La prueba E2E de Playwright en `tests/e2e/cms/builder-puck-flow.spec.ts` se ejecuta y pasa en verde.
- [ ] La ruta original `/plataforma/cms/builder` carga el nuevo editor Puck.
</USER_REQUEST>
