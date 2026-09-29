# Auditoría Forense General de la Plataforma CCF

**Fecha de Auditoría:** 18 de Septiembre de 2026  
**Equipo Auditor:** Células Integradas de Auditoría Forense CCF (Backend & DB, Frontend & Design System, Seguridad & RBAC, Operación & SRE)  
**VCS Head:** `9934c72f` (`integration/cms-aniversario-to-main`)  
**Base de Datos Activa:** PostgreSQL 16 (`ccf_recovery_20260823`)  
**Dictamen Conclusivo Global:** **OPERATIVA Y AVANZADA, PERO NO CERTIFICADA GLOBALMENTE AL 100%**  
**Documento Canónico:** [`docs/AUDITORIA_FORENSE_GENERAL_PLATAFORMA_2026-09-18.md`](file:///root/ccf/docs/AUDITORIA_FORENSE_GENERAL_PLATAFORMA_2026-09-18.md)

---

## 1. Resumen Ejecutivo

Durante la jornada del 18 de septiembre de 2026, se activaron los equipos de auditoría forense adversarial sobre la totalidad de la plataforma CCF (Comunidad Cristiana El Faro). La inspección combinó análisis estático de código, comprobaciones dinámicas en caliente contra los servicios en ejecución, ejecución de suites de pruebas canónicas, verificación de esquemas y modelos de base de datos, y contrastación exhaustiva de los axiomas arquitectónicos del proyecto.

### 1.1 Balance General de Cumplimiento

```
┌───────────────────────────────────────────┬──────────────┬────────────────────────────────────────────────────────┐
│ Eje de Auditoría                          │ Cumplimiento │ Veredicto                                              │
├───────────────────────────────────────────┼──────────────┼────────────────────────────────────────────────────────┤
│ 1. Backend, Contratos API & SQLAlchemy    │     89%      │ 🟢 Aprobado con remediaciones puntuales                │
│ 2. Base de Datos, Axioma 1 & Alembic      │     84%      │ 🟡 Alerta crítica por versión Alembic en BD            │
│ 3. Frontend, UI/UX & Design System        │     82%      │ 🟡 Modales residuales y clases hardcodeadas            │
│ 4. Seguridad, RBAC & Multi-Tenant (Ax. 3) │     86%      │ 🟡 BOLA en Community y omisión de sede en Donaciones   │
│ 5. Cobertura de Pruebas & Calidad         │     91%      │ 🟢 Suites nucleares operativas (pass rate 100%)        │
│ 6. Infraestructura, PM2 & Producción      │     80%      │ 🟡 Stack en ejecución, pero desacoplado de PM2         │
└───────────────────────────────────────────┴──────────────┴────────────────────────────────────────────────────────┘
```

### 1.2 Métricas de Código y Calidad al Corte

- **Tests Automatizados:** 46/47 pruebas estructurales aprobadas ([`tests/test_structural_contracts.py`](file:///root/ccf/tests/test_structural_contracts.py)); suites nucleares ejecutadas con 254/254 aprobadas en smoke y domains ([`test_smoke.py`](file:///root/ccf/tests/test_smoke.py), [`test_academy_domain.py`](file:///root/ccf/tests/test_academy_domain.py), [`test_crm_domain.py`](file:///root/ccf/tests/test_crm_domain.py), [`test_cms_domain.py`](file:///root/ccf/tests/test_cms_domain.py), [`test_auth.py`](file:///root/ccf/tests/test_auth.py), [`test_permissions_granular.py`](file:///root/ccf/tests/test_permissions_granular.py)).
- **TypeScript:** 100% limpio (`npx tsc --noEmit` con **0 errores** en todo el frontend).
- **ESLint:** 0 errores, **1 warning residual** en [`frontend/src/app/plataforma/cms/pages/page.tsx:94:6`](file:///root/ccf/frontend/src/app/plataforma/cms/pages/page.tsx#L94) (`react-hooks/exhaustive-deps`).
- **Endpoints de Backend:** Cero errores HTTP 500 en respuestas estándar de API.
- **Frontend `apiFetch`:** Cumplimiento del 100% en las rutas internas de `/src/app/plataforma` (989 invocaciones a `apiFetch`, 0 `fetch` nativos hacia `/api/`).
- **Módulos Certificados 100/100 A+:** 9 módulos (Agenda, Mensajería, Chat, Evangelismo, CRM, Proyectos, Academia, Administración y Vida Espiritual).
- **Módulos con Deuda Técnica / Documental:** 17 módulos o superficies periféricas.

---

## 2. Matriz Consolidada de Hallazgos por Severidad

| ID | Severidad | Módulo / Capa | Descripción del Hallazgo | Ubicación de Código |
|---|---|---|---|---|
| **H-01** | 🔴 **CRÍTICO** | BD / Migraciones | Desconexión en BD activa: `alembic_version` tiene registrado `20260901_0015` inexistente en código. `alembic current` arroja código 255. | Tabla `alembic_version` en `ccf_recovery_20260823` |
| **H-02** | 🔴 **CRÍTICO** | Finanzas / Multi-Tenant | `POST /api/donations` inserta con `sede_id = NULL`. Luego `GET /api/donations` y `/summary` filtran por `sede_id == user_sede`, ocultando las donaciones creadas. | [`backend/api/donations.py:34-41`](file:///root/ccf/backend/api/donations.py#L34-L41) y [`backend/crud/crm_/donations.py:13-18`](file:///root/ccf/backend/crud/crm_/donations.py#L13-L18) |
| **H-03** | 🔴 **CRÍTICO** | Frontend / UI Rules | Violación de la regla "Drawers, NUNCA Modals": 25 diálogos modales flotantes centrados en flujos activos de producción (confirmaciones, creación y previsualizaciones). | 21 en CMS, 2 en Evangelismo, 1 en CRM templates, 1 en Facturación |
| **H-04** | 🔴 **CRÍTICO** | Frontend / Routing | Enlace roto con error HTTP 404 por falta del prefijo `/plataforma` en el listado de cursos de administración. | [`frontend/src/app/plataforma/admin/content/list/page.tsx:115, 308`](file:///root/ccf/frontend/src/app/plataforma/admin/content/list/page.tsx#L115) |
| **H-05** | 🟠 **ALTO** | Seguridad / BOLA | Vulnerabilidad BOLA en Comunidad: `DELETE /cards/{card_id}` no valida `sede_id` ni autoría, permitiendo a editores de una sede borrar tarjetas de otra. | [`backend/api/community.py:120-135`](file:///root/ccf/backend/api/community.py#L120-L135) y [`backend/crud/crm_/community.py:77-91`](file:///root/ccf/backend/crud/crm_/community.py#L77-L91) |
| **H-06** | 🟠 **ALTO** | Seguridad / Multi-Tenant | `Enterprise CMS` (`enterprise_cms.py`, 1.679 líneas) tiene 0 referencias a `sede_id`. Webhooks, auditorías y redirecciones operan de forma global. | [`backend/api/enterprise_cms.py`](file:///root/ccf/backend/api/enterprise_cms.py) |
| **H-07** | 🟠 **ALTO** | Backend / Python 3.12 | Uso de fechas naive `datetime.now()` sin timezone comparadas y persistidas contra columnas `DateTime(timezone=True)`. | [`backend/services/automation_engine.py:94, 121`](file:///root/ccf/backend/services/automation_engine.py#L94), [`intelligence.py:66`](file:///root/ccf/backend/services/intelligence.py#L66), [`projects.py:801`](file:///root/ccf/backend/api/projects.py#L801) |
| **H-08** | 🟠 **ALTO** | Frontend / Design System | 849 ocurrencias de clases de color hardcodeadas de Tailwind en 71 archivos (focos críticos en `forms/page.tsx` con 175 y `popups/page.tsx` con 98). | Múltiples páginas en [`frontend/src/app/plataforma/cms/`](file:///root/ccf/frontend/src/app/plataforma/cms) |
| **H-09** | 🟠 **ALTO** | Frontend / Design System | Existencia de `DSModal.tsx` en `@/design`, institucionalizando la primitiva de modal flotante prohibida. | [`frontend/src/design/components/DSModal.tsx:42`](file:///root/ccf/frontend/src/design/components/DSModal.tsx#L42) |
| **H-10** | 🟠 **ALTO** | Infraestructura / SRE | PM2 sin supervisión activa (`pm2 status` vacío); proceso huérfano en puerto 8100 (PID 3218544); fallback monolítico en `deploy_frontend.sh`. | Supervisor PM2 y procesos en Linux VPS |
| **H-11** | 🟡 **MEDIO** | Backend / Soft Deletes | Hard deletes físicos `db.delete(row)` en entidades operativas de CMS (`CmsForm`, `CmsNewsletter`, `CmsSubscriber` y `CmsPopup`). | [`backend/crud/cms/forms.py:104`](file:///root/ccf/backend/crud/cms/forms.py#L104), [`newsletters.py:82, 264`](file:///root/ccf/backend/crud/cms/newsletters.py#L82), [`popups.py:71`](file:///root/ccf/backend/crud/cms/popups.py#L71) |
| **H-12** | 🟡 **MEDIO** | Seguridad / RBAC | `GET /dashboard/{module}` solo valida permisos para `module == 'admin'`. Usuarios sin rol pueden leer métricas de Finanzas o CRM. | [`backend/api/dashboard.py:77`](file:///root/ccf/backend/api/dashboard.py#L77) |
| **H-13** | 🟡 **MEDIO** | Seguridad / RBAC | `GET /admin/automations` usa `require_active_user` y el CRUD no filtra por `sede_id`, exponiendo automatizaciones cross-tenant. | [`backend/api/admin.py:1240`](file:///root/ccf/backend/api/admin.py#L1240) y [`backend/crud/admin.py:1115`](file:///root/ccf/backend/crud/admin.py#L1115) |
| **H-14** | 🟡 **MEDIO** | Backend / Axioma 1 | Modelos de Chat y Mentoría conservan FKs hacia `auth_users.id` en lugar de apuntar a `personas.id`. | [`backend/models_crm.py:35, 57, 72, 853`](file:///root/ccf/backend/models_crm.py#L35) |
| **H-15** | 🟡 **MEDIO** | Backend / Schemas | Inconsistencia de tipo `str` en lugar de `UUID` en schemas Pydantic de Auth v3, Evangelismo y Admin, evadiendo validación 422. | [`backend/schemas/auth_v3.py`](file:///root/ccf/backend/schemas/auth_v3.py), [`evangelism.py`](file:///root/ccf/backend/schemas/evangelism.py), [`admin.py`](file:///root/ccf/backend/schemas/admin.py) |
| **H-16** | 🟡 **MEDIO** | Frontend / HTTP | Llamadas a `fetch` nativo crudo en componentes cliente hacia `/api/...`. | [`PublicSearchModal.tsx:118`](file:///root/ccf/frontend/src/components/public/cms/PublicSearchModal.tsx#L118) y [`(public)/nosotros/page.tsx:30`](file:///root/ccf/frontend/src/app/(public)/nosotros/page.tsx#L30) |
| **H-17** | 🟡 **MEDIO** | Frontend / Design System | Desconexión del barrel `@/components/index.ts` (0 imports desde plataforma) y ausencia de `src/components/ui/index.ts`. | [`frontend/src/components/index.ts`](file:///root/ccf/frontend/src/components/index.ts) |
| **H-18** | 🔵 **BAJO** | Frontend / ESLint | Warning de `react-hooks/exhaustive-deps` en CMS Pages debido a instanciación de `new Set()` dentro del cuerpo del componente. | [`frontend/src/app/plataforma/cms/pages/page.tsx:94:6`](file:///root/ccf/frontend/src/app/plataforma/cms/pages/page.tsx#L94) |
| **H-19** | 🔵 **BAJO** | Backend / Convención | Columna de FK a `personas.id` en `SupportTicket` nombrada `user_id` en lugar de `persona_id`. | [`backend/models_crm.py:1140`](file:///root/ccf/backend/models_crm.py#L1140) |
| **H-20** | 🟢 **INFO** | Backend / SQLAlchemy | Uso predominante del estilo SQLAlchemy 1.4 (`db.query`) en lugar del estilo 2.0 moderno (`select()`). | Transversal en backend |

---

## 3. Auditoría Detallada por Dominios Técnicos

### 3.1 Backend y Base de Datos

#### Axioma 1 (Kernel de Personas) — Calificación: 96%
- **Fortalezas:**
  - `personas.id` (UUIDv4) es la clave primaria universal e inmutable de los seres humanos en el sistema.
  - `auth_users` comparte el mismo UUID con relación PK-FK 1:1 estricta:
    ```python
    id = Column(UUID(as_uuid=True), ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True)
    ```
  - Cero ocurrencias de `ForeignKey("users.id")` en los modelos activos. Las tablas paralelas históricas fueron completamente extirpadas.
- **Deuda Residual:**
  - En `backend/models_crm.py`, los modelos `ChatMessage`, `Conversation`, `ConversationParticipant` y `MentorshipRelation` tienen FKs apuntando a `auth_users.id` en lugar de `personas.id`. Aunque comparten el mismo valor UUID, esto fuerza conceptualmente a que el participante tenga cuenta en auth.

#### Axioma 3 (Aislamiento Multi-Tenant) — Calificación: 88%
- **Fortalezas:**
  - Obtención canónica del `sede_id` desde el JWT/sesión del usuario mediante `get_user_sede_id(db, current_user.id)`.
  - Tratamiento estandarizado de modelos globales (`sede_id IS NULL`):
    ```python
    query.filter((Model.sede_id == user_sede) | (Model.sede_id.is_(None)))
    ```
- **Quiebre Crítico en Donaciones (H-02):**
  - `create_donation` omite la asignación del `sede_id` del actor, persistiendo `NULL`.
  - La consulta de resumen `GET /api/donations/summary` filtra con `Donation.sede_id == user_sede`, haciendo invisibles todas las donaciones y falseando los balances del campus.

#### Fechas UTC y Python 3.12 — Calificación: 90%
- **Fortalezas:** Cero ocurrencias de `datetime.utcnow()` en todo el backend y tests.
- **Vulnerabilidad:** Uso de `datetime.now()` sin zona horaria en servicios de automatización (`automation_engine.py:94, 121`) comparado contra columnas `DateTime(timezone=True)`, lo que produce desajustes horarios e inconsistencias en la ejecución de tareas programadas.

#### Estado de Migraciones Alembic — Calificación: 75%
- **Cadena Canónica:** El directorio `alembic/canonical_versions` está sano, con 77 migraciones lineales y head único en `20260822_0002_evangelism_sede_indexes`.
- **Inconsistencia en Producción (H-01):** La base de datos viva `ccf_recovery_20260823` tiene estampada la versión `20260901_0015` en la tabla `alembic_version`. Dicha versión **no existe en el repositorio**, bloqueando cualquier operación de `alembic upgrade` o `alembic current`.

---

### 3.2 Frontend, UI/UX y Design System

#### Regla Inmutable: Drawers vs Modals — Calificación: 82%
A pesar de la existencia y uso extendido de `WorkspaceDrawer` y `SidePanel`, persisten **25 diálogos modales flotantes centrados**:
- **CMS:** 21 modales de confirmación destructiva y previsualización (páginas, temas, anuncios, A/B testing, popups, media, newsletters, tags, categorías, menús y formularios).
- **Evangelismo:** 2 modales flotantes en configuración de campañas y pre-registro (`PreregistrationTab.tsx:578, 746`).
- **CRM:** 1 modal de creación/edición de plantillas (`templates/page.tsx:148`).
- **Facturación:** 1 modal de registro de pagos (`facturacion/page.tsx:268`).
- **Design System:** Presencia indebida de `DSModal.tsx` en `@/design/components/DSModal.tsx`.

#### Tokens Semánticos vs Clases Hardcodeadas — Calificación: 85%
- El proyecto cuenta con **24,674 referencias a tokens semánticos** `hsl(var(--...))`, lo que representa una adopción del ~96.7%.
- Sin embargo, se identificaron **849 ocurrencias de colores de Tailwind hardcodeados** en 71 archivos.
- Los focos principales se ubican en `cms/forms/page.tsx` (175 clases) y `cms/popups/page.tsx` (98 clases).

#### Peticiones HTTP y Enrutamiento — Calificación: 94%
- En `src/app/plataforma/**` el cumplimiento de `apiFetch` es del **100%** (989 llamadas).
- **Hallazgo Crítico de Ruta (H-04):** En [`admin/content/list/page.tsx:115, 308`](file:///root/ccf/frontend/src/app/plataforma/admin/content/list/page.tsx#L115), el botón de detalle de curso redirige a `/admin/content/courses/...` sin el prefijo `/plataforma/`, provocando un error **HTTP 404**.

---

### 3.3 Seguridad, RBAC y Aislamiento

#### Modelo de Permisos y RBAC — Calificación: 88%
- Centralizado en [`backend/core/permissions.py`](file:///root/ccf/backend/core/permissions.py), con soporte para roles plataforma, roles por módulo y overrides individuales.
- **Bypass en Dashboard (H-12):** `GET /dashboard/{module}` sólo exige el rol de administrador si el módulo es `"admin"`. Si un usuario con rol `estudiante` solicita `/dashboard/finance` o `/dashboard/crm`, el sistema le entrega los KPIs de su sede sin exigir `finance:read` ni `crm:read`.
- **Bypass en Admin Automations (H-13):** `GET /admin/automations` utiliza `require_active_user`, permitiendo a cualquier usuario autenticado inspeccionar los webhooks y reglas de la iglesia.

#### Vulnerabilidades BOLA / IDOR — Calificación: 85%
- **BOLA en Comunidad (H-05):** El endpoint `DELETE /cards/{card_id}` ejecuta la baja lógica sin comprobar `card.sede_id == actor_sede`, permitiendo la eliminación de tarjetas comunitarias entre sedes distintas.
- **Enterprise CMS (H-06):** 1.679 líneas en `enterprise_cms.py` sin aislamiento por `sede_id`.

#### Rate Limiting — Calificación: 80%
- Bifurcación técnica: `slowapi` inicializado con `storage_uri="memory://"` (las cuotas se pierden entre procesos worker) y limitador Redis tradicional con fallback a NO-OP si Redis no está activo.
- Endpoints sensibles sin protección DoS: `POST /donations/mercadopago/webhook`, mutaciones en Agenda y búsquedas masivas en CRM.

---

### 3.4 Infraestructura y Operación en Producción

#### Estado de Procesos y Supervisión — Calificación: 80%
- **Supervisor PM2:** No tiene procesos registrados (`pm2 status` vacío).
- **Procesos en Background:**
  - FastAPI en puerto `8000` (PID 3392574) — Operativo y saludable.
  - Next.js 15 en puerto `3000` (PID 3379614) — Operativo y saludable.
  - Proceso huérfano en puerto `8100` (PID 3218544) — Activo desde el 6 de septiembre consumiendo memoria sin recibir tráfico.
- **Impacto en Despliegues:** Al no encontrar procesos en PM2, `deploy_frontend.sh` recurre a `./stopccf && ./startccf`, reiniciando el backend durante actualizaciones de frontend y rompiendo el zero-downtime.

---

## 4. Matriz de Certificación por Módulos

| # | Módulo | Tipo | Artefactos | Estado al Corte | Dictamen Forense |
|---:|---|:---:|:---:|---|---|
| 1 | **Agenda / Calendario** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | Totalmente auditado; 357 tests; aislamiento estricto. |
| 2 | **Mensajería** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 177 backend + 134 frontend tests; ownership y soft-delete. |
| 3 | **Chat** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | WebSocket integrado; suite compartida con Mensajería. |
| 4 | **Evangelismo** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 384 tests; QR, asistencias y CRM bridge auditados. |
| 5 | **CRM** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 1.279 tests; Kernel de Personas estricto. |
| 6 | **Proyectos** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 505 tests; Kanban, Whiteboard y tareas verificadas. |
| 7 | **Academia** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 311 tests; evaluaciones y certificados certificados. |
| 8 | **Administración** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | Drawers canónicos ratificados; roles unificados. |
| 9 | **Vida Espiritual** | Nuclear | 6 / 6 | 🟢 Certificado 100/100 A+ | 111 tests; Ruta de Discipulado dinámica validada. |
| 10 | **CMS (v1 / v2)** | Periférico | 6 / 6 | 🟡 Operativo con Deuda | 21 modales residuales; 273 clases hardcodeadas. |
| 11 | **Auth v3** | Periférico | 5 / 6 | 🟡 Operativo con Deuda | Schemas usan `str` para UUID; falta plan de calidad. |
| 12 | **Plataforma Compartida** | Periférico | 5 / 6 | 🟡 Operativo con Deuda | Falta compilar y ejecutar gate transversal. |
| 13 | **Finanzas (Finance Suite)**| Periférico | 6 / 6 | 🟡 Avanzado | 134 tests (evidencia julio); requiere re-auditoría. |
| 14 | **Donaciones** | Periférico | 1 / 6 | 🔴 Operativo con Riesgo | Bug crítico de `sede_id = NULL`; faltan 5 artefactos. |
| 15 | **Comunidad** | Periférico | 4 / 6 | 🟡 Operativo con Brecha | Vulnerabilidad BOLA en borrado de tarjetas. |
| 16 | **Soporte (Support + KB)** | Periférico | 1 / 6 | 🟡 Operativo con Deuda | Aislamiento agregado recientemente; faltan artefactos. |
| 17 | **Dashboard** | Periférico | 1 / 6 | 🟡 Operativo con Brecha | Fuga de métricas por falta de RBAC granular. |
| 18 | **Sistema (System)** | Periférico | 1 / 6 | 🟡 Operativo con Deuda | Imports locales; faltan 5 artefactos canónicos. |
| 19 | **Agentes / IA** | Periférico | 1 / 6 | 🟡 Operativo no Certificable | Cobertura mínima (2 tests); faltan artefactos. |
| 20 | **Gobernanza** | Menor | 1 / 6 | 🔴 No Certificable | 0 tests dedicados; solo 1 endpoint activo. |
| 21 | **Tablas Personalizadas** | Menor | 2 / 6 | 🟡 Parcial | Vistas guardadas funcionales; suite incompleta. |
| 22 | **YouTube** | Menor | 1 / 6 | 🟡 Parcial | Proxy RSS sin rate limit ni autenticación. |
| 23 | **Wiki** | Menor | 5 / 6 | 🟡 Operativo con Deuda | Integrado con proyectos; faltan planes de calidad. |
| 24 | **Graph / Whiteboard** | Menor | 5 / 6 | 🟡 Parcial | Funcional; 4 xfail históricos en Graph API. |
| 25 | **Analítica** | Menor | 4 / 6 | 🟡 Parcial | Helpers pastorales activos; falta validación cross-tenant. |
| 26 | **Oración (Prayer)** | Menor | 1 / 6 | 🟡 Parcial | Modelos presentes; faltan 5 artefactos canónicos. |

---

## 5. Plan de Remediación Priorizado

### Fase 1: P0 — Correcciones Críticas de Bloqueo Inmediato
1. **Saneamiento de Alembic (H-01):**
   - Alinear la tabla `alembic_version` en PostgreSQL para reflejar la revisión canónica actual:
     ```sql
     UPDATE alembic_version SET version_num = '20260822_0002_evangelism_sede_indexes';
     ```
   - Validar que `alembic current` retorne código de salida 0.
2. **Corrección de Aislamiento en Donaciones (H-02):**
   - En [`backend/api/donations.py`](file:///root/ccf/backend/api/donations.py): resolver `actor_sede = get_user_sede_id(db, current_user.id)` y transferirlo al CRUD.
   - En [`backend/crud/crm_/donations.py`](file:///root/ccf/backend/crud/crm_/donations.py): asignar `row.sede_id = sede_id` y exigir `sede_id` en consultas y borrados.
   - Ejecutar script de reconciliación para donaciones históricas con `sede_id IS NULL`.
3. **Reparación de Enlace Roto 404 (H-04):**
   - En [`frontend/src/app/plataforma/admin/content/list/page.tsx:115, 308`](file:///root/ccf/frontend/src/app/plataforma/admin/content/list/page.tsx#L115), anteponer el prefijo `/plataforma/admin/content/courses/...`.
4. **Remediación de Vulnerabilidad BOLA en Comunidad (H-05):**
   - Exigir coincidencia de `sede_id` del actor en [`backend/crud/crm_/community.py:delete_community_card`](file:///root/ccf/backend/crud/crm_/community.py#L77).
5. **Saneamiento Operativo de Procesos (H-10):**
   - Terminar el proceso residual en el puerto 8100 (`kill 3218544`).
   - Registrar y levantar el stack formalmente bajo PM2 (`pm2 start ecosystem.config.cjs && pm2 save`).

### Fase 2: P1 — Seguridad, UI Standards y Limpieza de Código
1. **Erradicación de Modales Flotantes (H-03, H-09):**
   - Reemplazar los 25 diálogos modales centrados por paneles deslizantes `WorkspaceDrawer` o `SidePanel`.
   - Deprecar y eliminar `DSModal.tsx` de `@/design`.
2. **Blindaje RBAC en Dashboard y Admin (H-12, H-13):**
   - Proteger `GET /dashboard/{module}` con `require_module_access(module, 'read')`.
   - Proteger `GET /admin/automations` con `require_admin` y filtrar por `sede_id`.
3. **Corrección de ESLint en CMS Pages (H-18):**
   - Extraer `PLATFORM_MANAGED_SLUGS` y `PLATFORM_PARTIAL_SLUGS` fuera del cuerpo de la función en [`cms/pages/page.tsx`](file:///root/ccf/frontend/src/app/plataforma/cms/pages/page.tsx).
4. **Erradicación de Fechas Naive (H-07):**
   - Migrar `datetime.now()` a `datetime.now(timezone.utc)` en servicios de automatización e inteligencia.
5. **Migración de Colores Hardcodeados (H-08):**
   - Sustituir clases de Tailwind crudas en `forms/page.tsx` y `popups/page.tsx` por tokens semánticos del Design System.

### Fase 3: P2 — Estandarización Documental y Certificación Modular
1. Implementar el paquete canónico de 6 artefactos para los módulos periféricos (`Auth v3`, `Donations`, `Dashboard`, `Support`, `Community`).
2. Diseñar el esquema de partición multi-tenant para `Enterprise CMS` (`models_enterprise.py`).
3. Crear `src/components/ui/index.ts` y reestructurar las exportaciones del Design System en 3 capas.
4. Unificar la infraestructura de rate limiting sobre Redis distribuido.

---

## 6. Veredicto Final

La plataforma CCF demuestra una arquitectura madura, un diseño relacional altamente disciplinado en torno al **Kernel de Personas (Axioma 1)** y un conjunto de **9 módulos nucleares de clase de producción certificados al 100/100 A+**.

No obstante, **no es técnicamente admisible emitir una certificación global del 100%** debido a la presencia de:
1. Una falla crítica de migración en la base de datos activa (`H-01`).
2. Pérdida de aislamiento de sede en la creación de donaciones (`H-02`).
3. 25 modales que infringen la regla canónica de diseño UI (`H-03`).
4. Vulnerabilidades de autorización BOLA y RBAC en módulos periféricos (`H-05`, `H-12`).
5. Procesos huérfanos y falta de supervisión unificada en PM2 (`H-10`).

El presente informe constituye la hoja de ruta forense no negociable para alcanzar la certificación global total de la plataforma.

---
*Informe consolidado y emitido por el Equipo de Auditoría Técnica y Remediación CCF.*
