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
const data = await apiFetch<Member[]>("/crm/members/", { token, cache: "no-store" });
  setMembers(data);
} catch (error) {
  if (error instanceof ApiError && error.status === 401) {
    logout();
    return;
  }
  addToast("No pudimos cargar los miembros", "error");
}
```

Con esto podemos mantener un único punto de configuración para cabeceras, autenticación y reintentos futuros.

## Hooks de contenido reutilizable

Cuando necesites leer bloques gestionados por el CMS (`/content/<clave>`), usa los hooks de `src/hooks/useContent.ts` para estandarizar el parseo del campo `content` y compartir estados de carga.

```ts
import { useContentBlock, useContentBlocks } from "@/hooks/useContent";

const { data: hero, loading } = useContentBlock("home_hero");
const { data: sections } = useContentBlocks([
  "home_academy_card",
  "home_giving_card",
]);
```

- Ambos hooks devuelven `{ data, loading, error, refresh }`.
- El campo `data.content` se parsea automáticamente (si trae JSON) y se mezcla en la respuesta. Si necesitas el string original para editar, usa `hero?.raw_content`.
- `useContentBlocks` acepta un array de claves y construye un diccionario `{ [key]: block | null }`.
- Usa estos hooks en vez de repetir `fetch('/content/...')` seguido de `JSON.parse` en cada página.
