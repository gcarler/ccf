# Arquitectura objetivo — Monolito modular estricto CCF

**Estado:** vigente como arquitectura objetivo
**Primera versión:** 2026-08-31
**Rama de trabajo:** `feature/platform-architecture-20260831`

## 1. Decisión arquitectónica

CCF continuará como un único despliegue y una única base de datos, organizado
como un monolito modular estricto. Cada módulo tendrá límites de código,
ownership y contratos verificables. La extracción a microservicios queda
pospuesta hasta que exista una necesidad operativa medible y un contrato de
integración estable.

Esta decisión reduce el riesgo sobre el núcleo compartido (`Persona`, auth,
sedes y permisos) y permite corregir la deuda histórica sin duplicar identidad
ni consistencia transaccional.

## 2. Núcleo de plataforma

El núcleo es la única zona que puede ser consumida por todos los módulos:

- identidad canónica: `personas.id` y `auth_users.id`;
- autenticación, roles y permisos;
- resolución de `sede_id` y tenancy;
- configuración, observabilidad, errores y límites de tasa;
- cliente HTTP frontend (`apiFetch`) y design system;
- contratos de eventos internos y utilidades puras aprobadas.

El núcleo no contiene reglas de negocio específicas de CRM, Academia, CMS,
Evangelismo o Mensajería.

## 3. Módulos propietarios

Cada módulo es dueño de sus casos de uso, endpoints, schemas, servicios,
modelos y pantallas. Las tablas compartidas de identidad no cambian de dueño.

| Módulo | Backend propietario | Frontend propietario | Contrato público |
|---|---|---|---|
| CRM | `backend/api/crm`, `backend/crud/crm_`, servicios CRM, modelos CRM | `frontend/src/app/plataforma/crm`, `components/crm` | `/api/crm` |
| Academia | `backend/api/academy`, `models_academy_core.py` | `frontend/src/app/plataforma/academy` | `/api/academy` |
| CMS | `backend/api/cms*`, `backend/crud/cms`, modelos CMS | `frontend/src/app/plataforma/cms` | `/api/cms*` |
| Evangelismo | `backend/api/evangelism*`, servicios evangelismo | `frontend/src/app/plataforma/evangelism` | `/api/evangelism` |
| Mensajería | `backend/api/messaging`, `backend/api/chat`, servicios messaging | `frontend/src/app/plataforma/messages`, `components/messaging` | `/api/messaging`, `/api/chat` |
| Agenda | `backend/api/agenda`, modelos agenda | `frontend/src/app/plataforma/agenda` | `/api/agenda` |
| Proyectos | `backend/api/projects`, modelos projects | `frontend/src/app/plataforma/projects` | `/api/projects` |
| Finanzas | `backend/api/finance*`, modelos finance | `frontend/src/app/plataforma/contabilidad`, `finance` | `/api/finance*` |
| Vida espiritual | `backend/api/spiritual_life`, modelos propios | rutas espirituales | `/api/spiritual-life` |
| Soporte | `backend/api/support*` | rutas support | `/api/support` |

La tabla define ownership de código, no una autorización para que un módulo
lea internamente los archivos de otro.

## 4. Reglas de dependencia

Se permiten únicamente estas dependencias:

```text
Frontend del módulo
        ↓ apiFetch + tipos/contratos públicos
API del módulo
        ↓ servicios de dominio del mismo módulo
CRUD/repositorios del módulo
        ↓ modelos y tablas propietarias + núcleo aprobado
Base de datos
```

Reglas obligatorias:

1. Un módulo no importa `api`, `crud`, `schemas`, `models` o componentes
   internos de otro módulo.
2. Un módulo no ejecuta SQL sobre tablas propietarias de otro módulo.
3. El acceso a `Persona`, auth y sede se hace mediante contratos del núcleo o
   adaptadores aprobados; no se crean identidades paralelas.
4. Las relaciones entre módulos se expresan con UUID, consultas de lectura
   mediante adaptadores o eventos internos, nunca con imports circulares.
5. Los routers solo orquestan autenticación, validación, autorización y
   servicios; las reglas de negocio no se duplican en el frontend.
6. El frontend consume el contrato REST del módulo mediante `apiFetch`; no
   importa tipos privados ni conoce tablas.
7. Un puente entre módulos debe vivir en `backend/integrations/<owner>/` o en
   un contrato de eventos del núcleo, tener un owner único y pruebas propias.
8. Las funciones compartidas deben ser puras o pertenecer explícitamente al
   núcleo; no se añade lógica de negocio a un helper “shared” por comodidad.
9. Las transacciones que cruzan módulos deben tener un servicio orquestador
   explícito y una única política de rollback; no se permiten commits internos
   ocultos.
10. Toda mutación respeta actor UUID, sede, soft delete y timestamps UTC.

## 5. Comunicación entre módulos

### Lecturas

- Preferir un adaptador de lectura estable del núcleo o del módulo propietario.
- El adaptador devuelve DTOs inmutables, no entidades SQLAlchemy.
- La lectura cross-module debe declarar su owner y su contrato.

### Escrituras

- El módulo propietario procesa la mutación.
- El módulo consumidor solicita la operación mediante un servicio o evento
  interno definido, no manipulando la tabla ajena.
- Si la operación necesita atomicidad entre dos dominios, se implementa un
  orquestador explícito en el núcleo o en el módulo dueño del caso de uso.

### Eventos internos

Los eventos son in-process durante esta etapa. Cada evento debe tener nombre,
payload versionado, actor, sede, idempotency key y owner. No se introduce un
broker externo hasta demostrar que el volumen o la disponibilidad lo exige.

## 6. Estructura objetivo del backend

La estructura final para cada módulo será:

```text
backend/modules/<modulo>/
├── api.py              # endpoints del módulo
├── contracts.py        # DTOs de entrada/salida y eventos públicos
├── service.py          # casos de uso y transacciones
├── repository.py       # acceso a persistencia propietaria
├── models.py           # solo si el módulo tiene modelos propios
└── tests/
```

La migración será gradual. Los paquetes históricos (`backend/api/crm`,
`backend/crud/crm_`, etc.) permanecen válidos hasta que cada unidad sea
extraída con pruebas y sin cambiar el contrato externo.

## 7. Estructura objetivo del frontend

```text
frontend/src/modules/<modulo>/
├── api.ts              # llamadas apiFetch y tipos públicos
├── components/         # componentes privados del módulo
├── hooks/              # estado y orquestación de pantalla
└── routes/             # composición de rutas existentes
```

Las rutas actuales bajo `/plataforma/<modulo>` se conservan. Primero se
encapsula el código; solo se cambia la ruta si existe una decisión explícita.

## 8. Fases de remediación

### Fase 0 — Baseline

- Inventariar imports cross-module, tablas consultadas y routers.
- Registrar excepciones existentes con owner, razón y fecha de expiración.
- Congelar contratos públicos y crear una línea base de pruebas.

### Fase 1 — Núcleo explícito

- Crear paquetes de contratos de identidad, auth, sedes, errores y eventos.
- Separar el barrel global `backend/models.py` de los imports internos nuevos.
- Prohibir imports internos de módulos desde el núcleo.

Entrega inicial: `backend/core/identity.py` concentra la resolución de
persona y sede para los consumidores nuevos. Los módulos propietarios deben
migrar sus imports en ramas separadas antes de retirar las excepciones del
registro de límites.

### Fase 2 — Encapsulación por módulo

- Mover casos de uso a servicios propietarios sin cambiar endpoints.
- Introducir repositorios/adaptadores para accesos cross-module existentes.
- Eliminar commits ocultos y lógica duplicada.

### Fase 3 — Guardrails ejecutables

- Validador de ownership de archivos y módulos.
- Validador de imports prohibidos y ciclos.
- Matriz de rutas ↔ owner ↔ contrato.
- Check CI que falle ante nuevas dependencias ilegales.
- Excepciones explícitas, pequeñas y con vencimiento.

### Fase 4 — Piloto CRM

- Encapsular creación de prospectos, casos y pipeline.
- Declarar formalmente el adaptador CRM–Evangelismo existente.
- Validar transacciones, sede, identidad y pruebas de costura.

### Fase 5 — Expansión

- Aplicar el patrón a CMS, Evangelismo, Academia y Mensajería.
- Resolver conflictos por módulo, nunca mediante un barrel global nuevo.
- Actualizar contratos y documentación después de cada unidad integrada.

## 9. Definition of Done arquitectónica

Un módulo se considera modularizado cuando:

- tiene owner y directorios definidos;
- sus endpoints llaman servicios propios;
- sus modelos propietarios no son importados por otros módulos;
- sus dependencias cross-module pasan por adaptadores o eventos declarados;
- no existen imports circulares ni commits ocultos;
- tiene pruebas de contrato, RBAC, sede y regresión;
- el guardrail de arquitectura pasa en CI;
- la rama propietaria y la integración respetan el protocolo CCF.

## 10. Excepciones iniciales a remediar

Estas excepciones se registran para ser aisladas, no para convertirse en
dependencias permanentes:

- `backend/models.py` como barrel global consumido por múltiples módulos;
- `backend/services/evangelism_crm_bridge.py`, puente compartido entre
  Evangelismo y CRM;
- `backend/api/crm/_shared.py`, que concentra serialización y scoping de varias
  superficies CRM;
- servicios genéricos en `backend/services/` con reglas de negocio mezcladas;
- componentes frontend compartidos que combinan datos de más de un módulo.

Cada excepción deberá migrarse mediante una unidad temática, con owner,
pruebas y fecha de revisión. No se hará un traslado masivo de carpetas.

## 11. Rollback

La transición es reversible por unidad:

- conservar rutas y contratos externos;
- extraer primero adaptadores, después mover consumidores;
- integrar un módulo por rama propietaria;
- revertir el commit de encapsulación si falla el gate;
- no editar migraciones históricas ni borrar código hasta contar con pruebas y
  una referencia archivada.

## Estado de esta decisión

- Arquitectura elegida: **monolito modular estricto**.
- Migración a microservicios: **pospuesta**.
- Primera entrega: mapa de límites y reglas objetivo.
- Próximo paso: inventario automático de imports y creación del primer guardrail
  ejecutable, sin alterar todavía el comportamiento de producción.
