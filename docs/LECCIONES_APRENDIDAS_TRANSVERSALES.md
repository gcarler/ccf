# Lecciones Aprendidas Transversales — Auditorías Forenses CCF

**Fecha:** 2026-08-09
**Módulos auditados:** Wiki (`feature/wiki-quality`, PR #9), Eventos (`feature/event-registration-quality`, PR #10 + commits producción)

---

## Resumen

| Métrica | Valor |
|---|---|
| Hallazgos corregidos (wiki) | 6 (W2-W6) |
| Hallazgos corregidos (eventos) | 13 (E1-E6, T2.1-T2.2, Q1-Q6) |
| Migraciones creadas | 1 (`20260809_0005_wiki_multi_tenant`) |
| Tests nuevos | 1 (`test_upsert_persona_email_priority_over_phone`) + 1 (`test_same_page_key_different_sedes`) |
| PRs merged a `main` | #9 (wiki), #10 (eventos) |
| Producción verificada | Wiki ✅, Eventos ✅ |

---

## Patrones anti repetidos y sus fixes

### 1. OR-ambiguity en lookups por múltiples claves débiles

**Afectó a**: `upsert_persona` (E6), `find_by_email_or_phone` (Q3)

**Problema**: `or_(email==.., phone==..).first()` retorna la primera fila no determinísticamente cuando dos registros distintos comparten partes del identificador (email de A, phone de B).

**Fix**: consultas SECUENCIALES con prioridad explícita (email > phone):

```python
# ANTI-patrón:
db.query(Persona).filter(or_(Persona.email == email, Persona.phone == phone)).first()

# Patrón correcto:
persona = None
if email:
    persona = db.query(Persona).filter(Persona.email == email).first()
if persona is None and phone:
    persona = db.query(Persona).filter(Persona.phone == phone).first()
```

**Rationale**: email es identificador personal fuerte (uno por persona); phone puede compartirse entre familiares. Email gana prioridad.

### 2. `except Exception` en I/O best-effort enmascara bugs

**Afectó a**: `_send_confirmation_email` (E4), `_send_verification_email` (E4), `_promote_first_waitlist` (Q2), `create_wiki_page` (W2)

**Problema**: capturar `Exception` genérica en operaciones de email push reduce cualquier error — incluidos `AttributeError`, `NameError`, `ImportError` de bugs de programación — a un `log.warning`, enmascarándolos como "éxito silencioso".

**Fix**: especificar familias de excepción de runtime:

```python
except (OSError, ConnectionError, RuntimeError) as exc:
    log.warning("Failed to send email: %s", exc)
```

- `OSError`: `SMTPException`, `SMTPConnectionError`, `socket.error`
- `ConnectionError`: fallos de red
- `RuntimeError`: fallos de formato de plantilla
- NO captura: `AttributeError`, `NameError`, `ImportError` (bugs de programación)

### 3. Multi-tenant unique constraints deben incluir sede_id

**Afectó a**: `WikiPage.page_key` (W3)

**Problema**: `page_key` con `unique=True` global — dos sedes no podían tener la misma `page_key`, violando el aislamiento multi-tenant.

**Fix**: `UniqueConstraint("page_key", "sede_id")` + migración. Regla transversal: cualquier columna "unique per sede" debe tener constraint compuesto, no `unique=True` standalone.

### 4. Páginas públicas deben respetar tema del sistema

**Afectó a**: rutas `/public/*` (T2.2)

**Problema**: el script inline en `layout.tsx` leía `localStorage('theme-mode')` (preferencia de la plataforma autenticada) en TODAS las rutas — un visitante en tema día veía el formulario en oscuro.

**Fix**: separar lógica por tipo de ruta:

```javascript
var isPublicRoute = window.location.pathname.indexOf('/public') === 0;
if (isPublicRoute) {
    // Rutas públicas: respetar sistema (prefers-color-scheme)
    effectiveTheme = prefersDark ? 'night' : 'day';
} else {
    // Rutas autenticadas: respetar localStorage (plataforma)
    effectiveTheme = theme === 'night' ? 'night' : 'day';
}
```

### 5. `AbortController` en forms públicos

**Afectó a**: `handleSubmit` (E3)

**Problema**: si el usuario navega fuera durante un POST en vuelo, el callback intenta actualizar estado de un componente desmontado (React warning "Can't perform a React state update on an unmounted component").

**Fix**: patrón estándar para todos los forms públicos no autenticados:

```typescript
const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (status === 'loading') return;  // guard de reentrada
    setStatus('loading');
    const controller = new AbortController();
    try {
        const data = await apiFetch('/...', { signal: controller.signal });
        setStatus('success');
    } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setStatus('error');
    }
};
```

### 6. QR container necesita `dark:bg-white`

**Afectó a**: QR display en `RegisterSuccess` (Q1)

**Problema**: `bg-white` hard-coded — el QR es módulos negros sobre fondo blanco, así que en tema oscuro el container negro hace el QR ilegible.

**Fix**: `bg-[hsl(var(--surface-1))] dark:bg-white` — el container se adaptó al tema pero preserva el fondo blanco del QR在各种 temas.

---

## Reglas de futuro para auditorías CCF

1. **Antes de codear un medio/bajo hallazgo**: grep por "subsumido por" en el tracker — puede estar ya mitigado por un crítico cerrado.
2. **En upserts por múltiples claves**: consultas secuenciales, no OR.
3. **En `try/except` alrededor de I/O**: especificar familias de excepción, no `Exception`.
4. **En unique constraints de tablas sede-scoped**: constraint compuesto con `sede_id`.
5. **En forms públicos**: `AbortController` + guard de reentrada + catch `AbortError`.
6. **En QR/QR code containers**: `dark:bg-white` para preservar contraste del QR.

---

## Build artifacts

- **Migración**: `alembic/canonical_versions/20260809_0005_wiki_multi_tenant_unique.py` — elimina unique global, crea compuesto `(page_key, sede_id)`
- **Tests nuevos**: `tests/test_event_registrations.py::test_upsert_persona_email_priority_over_phone`, `tests/test_wiki.py::test_same_page_key_different_sedes`
- **Docs**: `docs/AUDITORIA_FORENSE_WIKI.md`, `docs/AUDITORIA_FORENSE_EVENT_REGISTRATION.md`, `docs/LECCIONES_APRENDIDAS_TRANSVERSALES.md` (este archivo)
