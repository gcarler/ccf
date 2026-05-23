# Plan de Trabajo: Optimización y Estabilización - Proyecto CCF

Este plan aborda los hallazgos de la auditoría técnica para transformar el proyecto de un estado de "parches evolutivos" a una arquitectura profesional y mantenible.

---

## Fase 1: Sincronización y Consolidación de Datos (Prioridad Alta)
**Objetivo:** Eliminar la fragmentación del esquema de la base de datos.

1.  **Auditoría de Esquema Real:**
    *   Ejecutar un script para extraer el DDL (Data Definition Language) actual de `ccf_v2.db`.
    *   Comparar este DDL con los scripts `add_col.py`, `alter_db.py` y `add_whiteboard.py`.
2.  **Consolidación de Migraciones:**
    *   Crear un archivo único de migración (`master_schema.sql`) que contenga el estado final deseado.
    *   Documentar las columnas "huérfanas" que no están en los modelos de Python.
3.  **Validación de Integridad:**
    *   Verificar que `fix_timestamps.sql` se haya aplicado correctamente a todos los registros.

## Fase 2: Centralización de Seguridad y API (Prioridad Media)
**Objetivo:** Asegurar que todos los endpoints sigan la misma lógica de permisos.

1.  **Revisión de Roles:**
    *   Analizar `add_roles_api.py` y unificar la lógica de validación de roles en un middleware o dependencia de FastAPI.
2.  **Auditoría de Endpoints:**
    *   Asegurar que los nuevos módulos (`analytics`, `whiteboard`) utilicen el sistema de auditoría definido en `audit_events.py`.

## Fase 3: Limpieza y Refactorización (Prioridad Media-Baja)
**Objetivo:** Mejorar la legibilidad y reducir el "ruido" en el repositorio.

1.  **Gestión de Logs:**
    *   Configurar un directorio `/logs` y mover archivos `.log` actuales.
    *   Configurar una política de rotación de logs.
2.  **Eliminación de Scripts Obsoletos:**
    *   Identificar qué scripts de `fix_*.py` ya no son necesarios tras la Fase 1 y moverlos a una carpeta `/legacy` o eliminarlos.

## Fase 4: Automatización de Pruebas (Validación)
**Objetivo:** Garantizar que los cambios no rompan la funcionalidad actual.

1.  **Tests de Integración:**
    *   Crear pruebas que validen la conexión API -> Base de Datos para los módulos críticos.
2.  **Validación de Qwen:**
    *   Usar Qwen para verificar que cada cambio cumple con las reglas de negocio de CCF.

---
**Próximo Paso Inmediato:** Realizar la "Auditoría de Esquema Real" (Fase 1.1) para saber exactamente qué tenemos en la base de datos.
