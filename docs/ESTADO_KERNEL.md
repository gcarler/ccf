# Estado del Módulo Kernel

**Actualizado:** 2026-07-18

---

## Resumen

Módulo núcleo de identidad de la plataforma. Gestiona la relación entre `personas.id` y los temas visuales de la plataforma. Es la base sobre la que se construye el kernel de personas (Axioma 1).

| Métrica | Valor |
|---|---|
| Router | `backend/api/kernel.py` |
| CRUD | `backend/crud/kernel.py` |
| Modelos | `backend/models_kernel.py` |
| Schemas | `backend/schemas/identity.py` |
| Frontend | `frontend/src/app/plataforma/theme/` |
| Tests | Sin archivo de cobertura dedicado |

---

## Contrato canónico

- `personas.id` como única identidad canónica
- Temas visuales por sede/iglesia
- Configuración de identidad corporativa

---

## Backend

| Aspecto | Detalle |
|---|---|
| Router | `backend/api/kernel.py` |
| CRUD | `backend/crud/kernel.py` |
| Modelos | `backend/models_kernel.py` |
| Schemas | `backend/schemas/identity.py` |

---

## Issues conocidos

- 5 imports locales dentro de funciones
- Sin tests de cobertura dedicados
