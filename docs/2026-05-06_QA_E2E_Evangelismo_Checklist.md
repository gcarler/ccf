# QA E2E Evangelismo (Eventos, Asistencia, Faro, Scanner)

Fecha: 6 de mayo de 2026

## 1) Eventos (Agenda)

### 1.1 Crear evento sin seguimiento (agenda general)
- Ir a `Evangelismo > Eventos`.
- Crear evento tipo reunión/agenda (sin necesidad de seguimiento ministerial especial).
- Seleccionar `Universo esperado: Toda la iglesia`.
- Guardar.
- Resultado esperado:
  - El evento aparece en listado.
  - No hay errores de validación.
  - Se puede abrir detalle del evento.

### 1.2 Crear evento con universo por roles
- Crear evento nuevo con `Universo esperado: Uno o varios roles`.
- Elegir al menos 1 rol.
- Guardar.
- Resultado esperado:
  - Se guarda sin error.
  - Badge/etiqueta de universo muestra rol(es) esperado(s).

### 1.3 Crear evento con selección manual
- Crear evento con `Universo esperado: Selección manual`.
- Elegir al menos 1 miembro.
- Guardar.
- Resultado esperado:
  - Se guarda sin error.
  - Conteo de personas esperadas coincide con selección.

### 1.4 Validaciones de creación
- Intentar guardar evento de roles sin roles seleccionados.
- Intentar guardar evento manual sin personas seleccionadas.
- Resultado esperado:
  - Muestra mensaje de validación.
  - No crea evento inválido.

### 1.5 Editar y eliminar evento
- Editar nombre/horarios/estado del evento.
- Guardar cambios.
- Eliminar un evento desde modal de confirmación.
- Resultado esperado:
  - Guardar deshabilita acciones mientras procesa.
  - Eliminar bloquea acciones del modal mientras procesa.
  - Lista se refresca correctamente.

## 2) Registro de asistencia por evento

### 2.1 Apertura y carga de sesión
- Abrir drawer de asistencia desde un evento.
- Cambiar fecha de sesión.
- Resultado esperado:
  - Carga asistencia previa de la fecha seleccionada.
  - Si no hay sesión previa, estado vacío controlado.

### 2.2 Marcación manual
- Usar búsqueda, filtro por rol y filtro de estado.
- Probar `Marcar filtrados` y `Limpiar filtrados`.
- Guardar registro.
- Resultado esperado:
  - Conteos se actualizan en UI.
  - Botón guardar se bloquea durante envío.
  - Toast de éxito con presentes/ausentes.

### 2.3 Modo escáner dentro de asistencia
- Abrir `Modo Escáner`.
- Probar token válido, inválido y repetido.
- Resultado esperado:
  - Válido: marca asistencia y limpia input.
  - Inválido: mensaje de error.
  - Repetido: mensaje informativo, sin duplicar.

## 3) Scanner de acceso (pantalla dedicada)

### 3.1 Flujo principal
- Ir a `Evangelismo > Escáner`.
- Ingresar token manual válido.
- Resultado esperado:
  - Muestra estado validado con miembro/rol.
  - Botón `Reiniciar` permite siguiente escaneo.

### 3.2 Manejo de error
- Ingresar token inválido.
- Resultado esperado:
  - Toast de error claro.
  - Vuelve a estado de escaneo.

## 4) Faro en Casa

### 4.1 Temporadas
- Crear temporada con datos completos.
- Intentar crear temporada sin campos requeridos.
- Resultado esperado:
  - Botón crear deshabilitado si formulario inválido.
  - Crea temporada cuando está completo.

### 4.2 Sesiones
- Registrar sesión semanal de una casa.
- Resultado esperado:
  - Botón registrar deshabilitado si faltan datos.
  - Crea sesión y refleja en listado/analítica.

### 4.3 Reporte semanal por casa
- Ir a detalle de casa Faro.
- Marcar presentes/ausentes, razones, notas.
- Guardar reporte.
- Resultado esperado:
  - Guarda correctamente.
  - Botón muestra estado de guardado.
  - Métricas y listas se actualizan.

## 5) Criterios de cierre

- No hay textos con mojibake (`Ã`, `Â`) en Eventos/Scanner.
- `npm run typecheck` pasa.
- Pruebas backend relevantes de evangelismo/eventos/asistencia pasan.
- Flujos críticos (crear evento, pasar asistencia, guardar reporte Faro, validar token) sin doble envío ni estados rotos.
