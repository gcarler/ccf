# Cliente HTTP centralizado

Este frontend ahora utiliza un wrapper ligero sobre `fetch` para estandarizar llamadas al backend. El helper vive en `src/lib/http.ts` y expone `apiFetch` y la clase `ApiError`.

## Variables de entorno

- `NEXT_PUBLIC_API_URL`: URL base disponible en el navegador.
- `API_BASE_URL`: fallback para entornos de servidor/renderizado si no existe la variable pública.

Si ninguna está definida se usa `http://localhost:8000`.

## apiFetch

```ts
import { apiFetch } from "@/lib/http";

const courses = await apiFetch<Course[]>("/courses/", {
  token,              // opcional, añade Authorization Bearer
  method: "POST",     // por defecto GET
  body: { ... },       // se serializa como JSON (usa FormData para uploads)
  query: { page: 1 },  // se convierte en parámetros de URL
  cache: "no-store",  // pasa directamente a fetch
});
```

- Siempre añade `Accept: application/json`.
- Cuando `body` no es `FormData`, define `Content-Type: application/json` y hace `JSON.stringify`.
- Si la respuesta no es `ok`, lanza `ApiError` con `status` y `detail` (el JSON parseado si existe).

## Guías rápidas

- Prefiere `apiFetch` sobre `fetch(apiUrl())` para garantizar manejo consistente de errores y autenticación.
- Aporta `token` cuando la API lo exige. Obténlo desde `AuthContext` (`const { token } = useAuth();`).
- Usa `cache: "no-store"` en vistas con datos dinámicos (dashboards, listados admin, etc.).
- Atrapa `ApiError` para mostrar mensajes específicos (`error.detail?.message`).

Ejemplo básico con manejo de errores:

```ts
try {
const data = await apiFetch<Persona[]>("/crm/personas/", { token, cache: "no-store" });
  setPersonas(data);
} catch (error) {
  if (error instanceof ApiError && error.status === 401) {
    logout();
    return;
  }
  addToast("No pudimos cargar las personas", "error");
}
```

Con esto podemos mantener un único punto de configuración para cabeceras, autenticación y reintentos futuros.

## Hooks de contenido reutilizable

El CMS legacy basado en bloques `/cms/content/<clave>` fue retirado. Para contenido público usa el CMS v2 (`useCmsV2Page`) y para documentos colaborativos usa `useWikiDocument`.

```ts
import { useCmsV2Page } from "@/hooks/useCmsV2Page";

const page = useCmsV2Page("inicio");
const hero = page?.blocks?.hero;
```
