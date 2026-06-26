# Estandares de Desarrollo CCF

**Actualizado:** 2026-06-26

Este documento resume las reglas tecnicas. La fuente completa es `REGLAS.md`.

## Backend y Datos

- Usar UUID para entidades transaccionales expuestas por API.
- Usar `personas.id` para representar personas.
- Usar `auth_users.id` para autenticacion v3, alineado al UUID de `personas.id`.
- Filtrar por `sede_id` en consultas ministeriales, pastorales y administrativas.
- Usar `DateTime(timezone=True)` para marcas persistidas.
- Usar soft delete o estados para entidades protegidas.
- Usar `JSON` cuando el modelo deba correr tambien en SQLite de pruebas.

## Frontend

- Usar `apiFetch` para llamadas a backend de plataforma.
- Usar componentes del sistema existente antes de crear variantes.
- Usar texto visible en espanol pastoral y administrativo consistente con el dominio.
- No crear pantallas espejo para sostener rutas antiguas.

## Migraciones

- Cada migracion debe tener una intencion.
- Toda migracion de datos debe preservar integridad referencial.
- No recrear columnas retiradas para resolver errores de runtime.
- Validar con `alembic upgrade head` antes de desplegar.

## Checklist

- [ ] La identidad de personas usa UUID.
- [ ] No se agregan identidades enteras para personas.
- [ ] `sede_id` esta aplicado donde corresponde.
- [ ] No hay borrado fisico en entidades protegidas.
- [ ] Las fechas persistidas son timezone-aware.
- [ ] La prueba proporcional fue ejecutada y registrada.
