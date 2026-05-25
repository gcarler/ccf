# CMS v2 — Plan de Expansión de Bloques de Contenido

**Fecha:** 2026-05-25  
**Objetivo:** Agregar 11 nuevos tipos de sección al CMS v2  
**Arquitectura:** CMS v2 (secciones con `props_json` — sin migraciones BD)

---

## Cómo funciona (resumen)

Cada sección se define en **4 archivos** sin tocar la BD:

1. **Backend allowlist** → `backend/api/cms_v2.py` (`ALLOWED_SECTION_TYPES`)
2. **Builder registro** → `frontend/src/app/plataforma/cms/builder/page.tsx` (`SECTION_TYPES`, labels, colores)
3. **Renderer componente** → `frontend/src/components/public/cms/PublicSectionRenderer.tsx` (nuevo componente + case en el switch)
4. **(Opcional) Plantilla** → `SECTION_TEMPLATES` en el builder para preload

El campo `props_json` es JSON libre — cada tipo de sección lee las claves que necesita.

---

## Secciones existentes (19)

`hero`, `video_hero`, `rich_text`, `rich_text_columns`, `cards`, `cta_banner`, `gallery`, `faq`, `embed`, `testimonials`, `stats`, `team`, `countdown`, `pricing`, `image_text`, `timeline`, `icon_grid`, `newsletter`, `popup_banner`

---

## Nuevas secciones (11)

### 1. `button` — Botones

**Props:**
```json
{
  "buttons": [
    { "label": "Suscribirme", "href": "/boletin", "variant": "primary", "size": "lg", "icon": "arrow-right" },
    { "label": "Ver más", "href": "/cursos", "variant": "outline", "size": "md" }
  ],
  "align": "center",
  "gap": "4"
}
```

**UI:** Fila de botones con variantes (primary/outline/ghost), tamaños (sm/md/lg), iconos opcionales. Responsive: wrap en móvil.

---

### 2. `toc` — Índice / Tabla de Contenidos

**Props:**
```json
{
  "title": "En esta página",
  "items": [
    { "label": "Introducción", "href": "#intro" },
    { "label": "Capítulo 1", "href": "#cap1" },
    { "label": "Capítulo 2", "href": "#cap2" }
  ],
  "style": "numbered"
}
```

**UI:** Índice lateral o central con items enlazados. Variantes: numbered (lista ordenada), bulleted, minimal. Scrollspy opcional (resalta sección activa).

---

### 3. `divider` — Divisor / Separador

**Props:**
```json
{
  "style": "solid",
  "color": "primary",
  "thickness": "2",
  "margin_top": "8",
  "margin_bottom": "8",
  "width": "full"
}
```

**Estilos:** `solid`, `dashed`, `dotted`, `gradient`, `decorative` (con icono central: ✦, ❖, ☩).

---

### 4. `collapsible` — Grupo Ocultable

**Props:**
```json
{
  "title": "Información adicional",
  "default_open": false,
  "icon": "chevron",
  "content_html": "<p>Contenido que se puede ocultar...</p>",
  "bg_color": "surface",
  "border": true
}
```

**UI:** Sección con header clickeable que expande/colapsa. Animación suave. Soporta HTML enriquecido en el contenido.

---

### 5. `social_links` — Redes Sociales

**Props:**
```json
{
  "title": "Síguenos",
  "links": [
    { "platform": "facebook", "url": "https://facebook.com/ccf", "label": "Facebook" },
    { "platform": "instagram", "url": "https://instagram.com/ccf", "label": "Instagram" },
    { "platform": "youtube", "url": "https://youtube.com/@ccf", "label": "YouTube" },
    { "platform": "tiktok", "url": "https://tiktok.com/@ccf", "label": "TikTok" },
    { "platform": "whatsapp", "url": "https://wa.me/573001234567", "label": "WhatsApp" }
  ],
  "layout": "row",
  "show_labels": true,
  "icon_size": "24"
}
```

**Plataformas soportadas:** facebook, instagram, youtube, tiktok, twitter/x, whatsapp, telegram, linkedin, spotify, apple-podcasts.

**Layouts:** `row` (fila), `grid` (rejilla), `stack` (vertical).

---

### 6. `spacer` — Marcador de Posición / Espaciador

**Props:**
```json
{
  "height": "32",
  "bg_color": "transparent",
  "label": "Espacio de contenido"
}
```

**UI:** Espacio vacío configurable. Útil para respiración visual entre secciones. Alturas predefinidas: 16, 24, 32, 48, 64, 96, 128px. Modo "placeholder" muestra texto guía en modo builder.

---

### 7. `calendar` — Calendario de Eventos

**Props:**
```json
{
  "title": "Próximos Eventos",
  "source": "api",
  "api_endpoint": "/public/events",
  "view": "month",
  "max_events": 10,
  "show_time": true,
  "show_location": true
}
```

**UI:** Calendario interactivo con eventos. Vista month/list. Si `source: "api"`, carga eventos del backend. Si `source: "manual"`, usa items[].

**Props alternativos (modo manual):**
```json
{
  "title": "Calendario",
  "source": "manual",
  "items": [
    { "date": "2026-06-01", "title": "Reunión de líderes", "time": "19:00", "location": "Sede Norte" }
  ]
}
```

---

### 8. `map` — Mapa Interactivo

**Props:**
```json
{
  "title": "Encuéntranos",
  "provider": "google",
  "embed_url": "https://www.google.com/maps/embed?pb=...",
  "address": "Cra 15 #85-30, Bogotá",
  "lat": 4.6727,
  "lng": -74.0547,
  "zoom": 15,
  "height": "400",
  "show_directions_link": true
}
```

**Providers:** `google` (iframe embed), `openstreetmap` (iframe), `custom` (imagen estática con pin).

---

### 9. `document_upload` — Cargar Documentos

**Props:**
```json
{
  "title": "Subir Documento",
  "description": "Adjunta tu documento para revisión",
  "accepted_types": ".pdf,.doc,.docx,.jpg,.png",
  "max_size_mb": 10,
  "upload_endpoint": "/api/public/documents",
  "success_message": "Documento enviado correctamente",
  "show_file_list": true
}
```

**UI:** Drop zone con drag & drop. Muestra archivos seleccionados, barra de progreso, mensajes de éxito/error. Integración con SeaweedFS existente.

---

### 10. `content_blocks` — Bloques de Contenido Mixto

**Props:**
```json
{
  "layout": "grid",
  "columns": "3",
  "blocks": [
    {
      "type": "text",
      "content": "<h3>Misión</h3><p>Nuestra misión es...</p>"
    },
    {
      "type": "image",
      "image_url": "/img/mision.jpg",
      "alt": "Nuestra misión",
      "caption": "Equipo CCF 2026"
    },
    {
      "type": "video",
      "video_url": "https://youtube.com/embed/...",
      "aspect_ratio": "16:9"
    },
    {
      "type": "quote",
      "text": "La fe mueve montañas",
      "author": "Pastor Histar"
    }
  ]
}
```

**Sub-block types:** `text`, `image`, `video`, `quote`, `divider`, `spacer`, `list`. Layouts: `grid`, `masonry`, `flex`, `stack`.

---

### 11. `accordion` — Acordeón (expansión de FAQ)

**Props:**
```json
{
  "title": "Preguntas Frecuentes",
  "subtitle": "Todo lo que necesitas saber",
  "items": [
    { "question": "¿Cómo me inscribo?", "answer": "Puedes inscribirte...", "default_open": false },
    { "question": "¿Es gratuito?", "answer": "Sí, todos los servicios...", "default_open": false }
  ],
  "style": "bordered",
  "open_multiple": false
}
```

**Nota:** Similar a `faq` existente pero con más estilos y opciones de diseño.

---

## Plan de implementación por fases

### Fase 1 — Simples (sin estado, sin APIs)
| Sección | Esfuerzo | Archivos |
|---------|----------|----------|
| `divider` | 15 min | 4 archivos |
| `spacer` | 10 min | 4 archivos |
| `button` | 30 min | 4 archivos |

### Fase 2 — Interactivas (estado React)
| Sección | Esfuerzo | Archivos |
|---------|----------|----------|
| `collapsible` | 45 min | 4 archivos |
| `social_links` | 30 min | 4 archivos |
| `toc` | 45 min | 4 archivos |
| `accordion` | 30 min | 4 archivos |

### Fase 3 — Externas (APIs/embeds)
| Sección | Esfuerzo | Archivos |
|---------|----------|----------|
| `calendar` | 60 min | 4 archivos + API endpoint |
| `map` | 30 min | 4 archivos |
| `document_upload` | 90 min | 4 archivos + backend endpoint |
| `content_blocks` | 60 min | 4 archivos |

**Total estimado:** ~7 horas de desarrollo

---

## Estructura de archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `backend/api/cms_v2.py` | Agregar 11 tipos a `ALLOWED_SECTION_TYPES` |
| `backend/api/public.py` | Endpoint `/public/documents` para uploads (si no existe) |
| `frontend/src/app/plataforma/cms/builder/page.tsx` | Registrar 11 tipos en SECTION_TYPES, labels, colores, previews |
| `frontend/src/components/public/cms/PublicSectionRenderer.tsx` | 11 nuevos componentes + 11 cases en switch |
| `frontend/src/lib/cms/v2.ts` | (Opcional) helper para document upload |

---

## Consideraciones de diseño

1. **Consistencia visual:** Todos los componentes usan `--faro-*` CSS variables
2. **Responsive:** Mobile-first, breakpoint lg para layouts multi-columna
3. **Accesibilidad:** ARIA labels en componentes interactivos, focus visible
4. **Performance:** Lazy load de embeds (map, video), IntersectionObserver
5. **Dark mode:** Todos los componentes soportan dark con `dark:` clases
6. **Builder UX:** Cada tipo tiene preview visual, color de badge, descripción
