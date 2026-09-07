# Reglas Mandatorias de Arquitectura y Desarrollo — Plataforma CCF

Toda interacción, modificación de código, migración, diseño UI y operación Git dentro de este repositorio DEBE acatar estrictamente las siguientes reglas canónicas (fuente de verdad: `AGENTS_RULES_CCF.md` y `REGLAS.md`).

---

## 1. Reglas de Git, Commits y Push
- **PROHIBIDO `--no-verify`**: Jamás saltarse los hooks con `--no-verify` en `git commit` o `git push`. Los gates del `pre-push` son obligatorios.
- **Push seguro**: Utilizar validación de rama o `scripts/push_branch.sh origin <rama>`.
- **Commits atómicos y convencionales**: Prefijos obligatorios `feat(cms):`, `fix(cms):`, `docs(cms):`, `refactor(cms):`. Un solo hallazgo/unidad temática por commit.
- **Evidencia y verificación**: Confirmar SHA remoto tras el push.

---

## 2. Reglas de Frontend (Next.js 15 + React 19 + TypeScript)
- **Drawers, NO Modals**: Todos los flujos de creación, edición o detalle (create/edit/view) DEBEN usar paneles laterales deslizantes (**Drawers / SidePanel / RightPanel**). Prohibido usar `AlertDialog` o modals centrados.
- **Tokens Semánticos**: Usar exclusivamente variables CSS del Design System: `hsl(var(--primary))`, `hsl(var(--surface-1))`, `hsl(var(--surface-2))`, `hsl(var(--destructive))`, `hsl(var(--border))`, etc. **PROHIBIDO** usar colores hardcodeados de Tailwind (`bg-blue-500`, `text-gray-400`, `bg-red-600`, etc.).
- **Peticiones HTTP**: Toda llamada al backend de plataforma debe usar `apiFetch` (`@/lib/http`). Prohibido usar `fetch()` crudo para APIs internas.
- **Rutas de navegación**: Toda ruta interna del aplicativo debe llevar el prefijo `/plataforma/...`.
- **Clases condicionales**: Usar `clsx` o helpers consistentes, no template strings desordenados.
- **TypeScript estricto**: Cero `any` injustificado. Compilación limpia sin errores (`tsc --noEmit`).
- **Estados de UI**: Siempre proveer estados de carga (`Skeleton`/`Loader`), estados vacíos (`EmptyState`) y notificaciones mediante `toast` (sonner).

---

## 3. Reglas de Backend (FastAPI + SQLAlchemy + Python 3.12)
- **Fechas en UTC**: Usar `datetime.now(timezone.utc)`. **PROHIBIDO** `datetime.utcnow()` (deprecado en Python 3.12).
- **Actor UUID obligatorio**: Toda mutación (create/update/delete) exige el actor canónico UUID (`current_user.id`). Si falta responde 401; si no tiene sede en entidades con tenant responde 409.
- **Aislamiento Multi-Tenant (Axioma 3)**: `sede_id` debe obtenerse del usuario autenticado (`get_user_sede_id()`), NUNCA del cliente. Las entidades con sede NULL representan alcance global ministerial (`Model.sede_id.is_(None) | (Model.sede_id == sede_id)`).
- **Inyección de DB**: Usar dependencias FastAPI `db: Session = Depends(get_db)`.
- **Permisos y Guards**: Proteger endpoints con `require_module_access` y permisos canónicos.
- **Soft Deletes**: Prohibido hard delete en entidades protegidas. Usar `deleted_at`, `estado`, `is_active`.
- **Columnas Timezone**: Columnas de fecha con `DateTime(timezone=True)`.

---

## 4. Reglas de Base de Datos (PostgreSQL + Kernel de Personas)
- **Axioma 1 (Kernel de Personas)**: `personas.id` es la única identidad canónica para seres humanos en toda la plataforma. Prohibido crear tablas paralelas de personas. `auth_users.id` comparte el mismo UUID.
- **Claves Primarias UUIDv4**: Toda tabla transaccional expone PK UUIDv4 (`id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`).
- **Inmutabilidad de Migraciones**: Las migraciones cerradas y mergeadas a `main` son inmutables. Nunca se editan; cualquier corrección requiere una nueva migración reversible (`upgrade()` y `downgrade()`).
- **Cero scripts temporales**: Prohibido mantener archivos `_tmp_*` o `_scratch_*` en `scripts/`.

---

## 5. Protocolo Operativo y Despliegues
- **Deploy seguro**: Siempre usar `bash scripts/deploy_frontend.sh` para builds de frontend (swap atómico `.next-build` -> `.next`).
- **Verificación en Vivo**: Comprobar códigos HTTP 200 en las rutas afectadas tras cada despliegue.
