# Auditoría de completitud y consistencia — Academy

> **Fecha:** 2026-07-19  
> **Dictamen:** Academy **no está al 100%**. Requiere ejecutar y ampliar su
> plan de calidad antes de poder certificarse.

## Alcance y evidencia

- Backend: `backend/api/academy.py`, modelos, schemas y alcance por sede.
- Frontend: `frontend/src/app/plataforma/academy/**` y componentes Academy.
- Contratos: estado, matriz RBAC, contratos API y plan vigentes.
- Gates ejecutados: `scripts/test_academy_quality.py --backend-deep` (**9
  passed**) y `frontend npm run typecheck` (**verde**).
- El árbol contiene cambios locales de Academy sin commit; esta auditoría no
  los modifica ni los usa como prueba de un cierre publicado.

## Hallazgos de cierre

| ID | Pri. | Hallazgo verificable | Trabajo de cierre | Evidencia de aceptación |
|---|---:|---|---|---|
| `ACAD-AUD-001` | P0 | La UI de `forum/[id]` solicita `GET /forum/threads/{id}`, `GET /comments` y `POST /comments`, pero el router sólo expone listado, alta de hilo y `PATCH /resolve`. | Implementar contrato completo de detalle/comentarios con UUID, ownership, sede y soft delete; o retirar la ruta UI. | E2E crea hilo, abre detalle, agrega respuesta y bloquea acceso cross-sede. |
| `ACAD-AUD-002` | P0 | Sólo hay 9 pruebas backend dedicadas frente a más de 40 rutas Academy; no cubren matriz de rol/sede, admin, certificados ni foro detallado. | Crear matriz API por capacidad (`read/study/edit/manage`) y dos sedes; cada defecto se convierte en regresión. | Cobertura de rutas críticas y pruebas negativas reproducibles; el gate falla ante una fuga. |
| `ACAD-AUD-003` | P1 | La documentación declara pendientes los flujos admin, certificados, rutas duales y smoke profundo; no existe E2E para esos flujos. | Extender Playwright a certificados, curso canónico, coordinación, entregas y foro. | Smoke y deep E2E pasan con estudiante, editor y gestor. |
| `ACAD-AUD-004` | P1 | Persisten dos rutas de curso (`course/[id]` y `courses/[id]`) y dos fuentes de sidebar; el contrato de navegación no es único. | Decidir ruta canónica, mantener redirect compatible y centralizar navegación por capacidades. | Sin enlaces divergentes; lector no ve acciones de docencia/coordinación. |
| `ACAD-AUD-005` | P1 | Varias fronteras API del frontend siguen con `any`; typecheck no detecta drift de payload. | Definir DTOs Academy compartidos y tipar dashboard, cursos, foro, evaluación, certificados y admin. | Sin `any` en fronteras Academy críticas y typecheck/E2E verde. |
| `ACAD-AUD-006` | P2 | Recursos de lecciones están modelados, pero no tienen API propietaria; certificados y detalle de foro tienen UX incompleta. | Decidir explícitamente qué recursos son lectura embebida y qué requieren CRUD; completar o retirar controles sin implementación. | Contratos, UI y router coinciden sin 404 ni acciones inertes. |

## Consistencia documental

`ESTADO_ACADEMY.md` y `PLAN_ACADEMY_CALIDAD.md` ya reconocen buena parte de
la deuda (sidebar, rutas duplicadas, QR, catálogo y smoke). La auditoría añade
el defecto concreto de contrato Foro/UI (`ACAD-AUD-001`) y eleva la cobertura
de API/RBAC a condición P0. Por tanto **el plan existente es necesario pero
debe ampliarse**, no sustituirse por una declaración prematura de cierre.

## Orden de ejecución recomendado

1. Congelar y validar los cambios locales de Academy en un commit aislado.
2. Resolver `ACAD-AUD-001` y `ACAD-AUD-002` en backend y pruebas antes de
   cambiar UI masivamente.
3. Cerrar navegación/capacidades y rutas canónicas (`ACAD-AUD-004`).
4. Tipar fronteras y completar UX/E2E (`ACAD-AUD-003`, `005`, `006`).
5. Ejecutar gates profundos, documentación de contrato y cierre publicado.
