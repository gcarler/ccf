# Checklist Editorial — Sitio Público Editable desde el CMS

> **Para quién:** equipo editorial (no desarrolladores). Este checklist indica qué textos e imágenes del sitio público **se editan desde el CMS** y **dónde**.
> **Estado:** verificado el 2026-08-13 contra el código y el entorno de staging.

## 0. Resumen ejecutivo

**Todo el contenido editorial del sitio público se edita desde el CMS.** No hay que tocar código para cambiar textos, imágenes o enlaces de las páginas públicas.

El sitio se edita desde **`/plataforma/cms`** (módulo CMS de la plataforma). Las herramientas principales:

| Herramienta | Ruta | Para qué sirve |
|---|---|---|
| **Builder** | `/plataforma/cms/builder?site=ccf&page=<slug>` | Editar las secciones de cada página (hero, formularios, labels) |
| **Páginas** | `/plataforma/cms/pages` | Ver/crear/publicar páginas completas |
| **Media** | `/plataforma/cms/media` | Subir y gestionar imágenes (biblioteca CMS) |
| **Menús** | `/plataforma/cms/menus` | Editar la navegación (header y menú móvil) |
| **Temas** | `/plataforma/cms/themes` | Colores, logo, eslogan, CTAs y textos del header |
| **Logo & Branding** | `/plataforma/cms/branding` | Logo y nombre del sitio |
| **Posts / Blog** | `/plataforma/cms/posts` | Crear y aprobar artículos del blog |
| **Testimonios** | `/plataforma/cms/testimonials` | Aprobar y gestionar testimonios |
| **Equipo Pastoral** | `/plataforma/cms/pastoral-team` | Gestionar el equipo de pastores |

> **¿Cómo publicar?** En el Builder, el botón **"Guardar"** es la acción de publicar (guardar + publicar en un solo paso). Los cambios aparecen en el sitio público casi de inmediato. Solo editores con rol **Gestor o Administrador** pueden publicar; los Editores guardan borradores.

---

## 1. Páginas públicas y sus elementos editables

### 🏠 `/` (Inicio) — Builder `page=home`
- [ ] **Hero**: eyebrow, título (3 partes), descripción, botones + enlaces, imagen de fondo, slides/galería (desde la biblioteca Media).
- [ ] **Bento "Bienvenidos a Casa"**: título, descripción, tarjeta destacada (imagen, título, descripción, CTA, enlace) y mini-tarjetas.
- [ ] **Actividades**: eyebrow, título, texto "Ver calendario →" **y su enlace** (`activities_view_all_href`), mensaje de estado vacío.
- [ ] **Newsletter**: eyebrow, título, descripción, placeholder, texto del botón, estado "Enviando..." y mensajes de éxito/error (toasts).

### 🙏 `/nosotros` (Quiénes Somos) — Builder `page=about`
- [ ] **Hero**: eyebrow, título (2 partes), descripción.
- [ ] **Estadísticas** (4 números + etiquetas).
- [ ] **Visión y Misión** (títulos + textos).
- [ ] **Fundadores**: nombre, rol e **imágenes** de los 2 pastores principales.
- [ ] **Valores** (6 tarjetas: número, título, descripción).
- [ ] **Cita** (texto + autor + subtítulo).
- [ ] **CTA final** (título + descripción + botones).

### 👥 `/pastores` — Builder `page=pastors`
- [ ] **Hero y labels**: badge, título, descripción, "Cargando...", estado vacío, texto del botón de tarjeta, "Pastor Principal".
- [ ] **Tarjetas del equipo**: se gestionan desde **Equipo Pastoral** (`/plataforma/cms/pastoral-team`).
- [ ] **Detalle `/pastores/[slug]`**: labels del `detail_template` (rol, cita, historia, CTAs).

### 📅 `/eventos` — Builder `page=events`
- [ ] **Hero**: eyebrow, título, descripción.
- [ ] **Labels del calendario**: "HOY", "Próximo en 48 horas", "Destacado", "Reservar lugar", filtros, "Sincronizar Calendario", notificaciones.
- [ ] **Nombres de los meses** (`month_names`, 12) y etiquetas de vista: Semanal / Mensual / Anual.
- [ ] Los **eventos en sí** se crean en la agenda de la plataforma (módulo Agenda / Evangelismo); el CMS decide si se muestran.

### 🎥 `/predicas` — Builder `page=sermons`
- [ ] **Hero y labels**: eyebrow, títulos, descripción, búsqueda, estados vacíos, "Ver canal", "Copiar", "Compartir".
- [ ] **Miniaturas de YouTube**: se pueden reemplazar con imágenes de la biblioteca CMS por video (editor guiado "Miniaturas de prédicas" dentro del builder, sección `feed`). Si la imagen del CMS falla, se usa la miniatura original de YouTube.

### 📚 `/cursos` — Builder `page=courses`
- [ ] **Hero**: eyebrow, título, descripción.
- [ ] **Labels**: librería (título, descripción, vacío), cursos (título, descripción), newsletter (CTA, placeholder, toasts), wishlist.
- [ ] Los **cursos y libros** se gestionan desde el módulo Academia; el CMS controla qué se publica.
- [ ] **Detalle `/cursos/[id]`**: labels del `detail_template` (inscripción, syllabus, instructor, toasts).

### 📍 `/sedes` — Builder `page=locations`
- [ ] **Hero**: título, placeholder de búsqueda, mapa embebido, badge "Principal", "Cómo llegar", estados vacíos.
- [ ] **Sedes** (lista con nombre, dirección, teléfono, horarios): editable en el bloque `locations_feed`.

### 📬 `/boletin` — Builder `page=newsletter`
- [ ] **Hero del boletín**: subtítulo, título, descripción, texto del botón, mensajes de éxito/error, placeholder del email, "Enviando...".

### 💬 `/testimonios` — Builder `page=testimonials`
- [ ] **Hero y labels**: búsqueda, "Cargando...", vacío, "Compartir mi historia", "Leer más".
- [ ] Los **testimonios** se aprueban desde `/plataforma/cms/testimonials`.
- [ ] **Detalle `/testimonios/[id]`**: labels del `detail_template` ("Volver a testimonios", "Testimonio no encontrado", formulario de oración, compartir).

### ✍️ `/blog` — Builder `page=blog`
- [ ] **Hero y labels**: búsqueda, vacío, **"Leer más"**.
- [ ] Los **artículos** se crean en `/plataforma/cms/posts`.
- [ ] **Detalle `/blog/[slug]`**: el contenido del post viene del módulo Posts; los comentarios son funcionales (sus placeholders no son editables — ver §3).
- [ ] **Categorías `/categoria/[slug]` y etiquetas `/etiqueta/[slug]`**: labels del `archive_template` ("Volver al blog", estados vacíos, "Leer más").

### ✉️ `/contacto` — Builder `page=contact` (espejo español `contacto`)
- [ ] **Hero**: eyebrow, título (2 partes), descripción.
- [ ] **Formulario de contacto** (`contact_form`): título, subtítulo, labels y placeholders de nombre/email/WhatsApp/mensaje, texto del botón, mensaje de éxito, botón "Enviar otro mensaje". Los envíos llegan al CRM.

### ✝️ `/conocer-a-jesus` — Builder `page=discover`
- [ ] **Hero**: eyebrow, título, descripción, CTA.
- [ ] **Feed**: título intro, párrafos, beneficios, pasos, oración, formulario de contacto (labels) e información de contacto.

### 🔒 `/privacy` — Builder `page=privacy`
- [ ] **Política de privacidad**: fecha de actualización, resumen y secciones (títulos y contenidos).

---

## 2. Elementos globales (presentes en todas las páginas)

### 🧭 Header / Navegación
- [ ] **Menú principal**: `/plataforma/cms/menus` (items, submenús, visibilidad, orden).
- [ ] **Menú móvil**: `/plataforma/cms/menus` (menú `mobile`, incluye ícono por item).
- [ ] **Logo e imagen**: `/plataforma/cms/branding` o Temas → Branding (`--site-logo-url`, `--site-logo-name`).
- [ ] **CTA "Quiero conocer a Jesús"** (texto + enlace): Temas → Branding (`--site-header-cta-label/href`).
- [ ] **Eslogan junto al logo** ("Comunidad cristiana"): Temas → Branding (`--site-brand-tagline`).
- [ ] **Tooltips**: "Nuestras Sedes" y "Cambiar tema": Temas → Branding (`--site-header-location-title`, `--site-header-theme-title`).
- [ ] **Encabezado del dropdown** ("Explorar") y del **menú móvil** ("Menu principal"): Temas → Branding.
- [ ] **Aria-labels del menú móvil** ("Abrir menu" / "Cerrar menu"): Temas → Branding (`--site-header-open-menu-label`, `--site-header-close-menu-label`).

### 🦶 Footer (página `footer` del CMS)
- [ ] **Descripción** de la marca.
- [ ] **Enlaces**: navegación, recursos y redes sociales (labels + hrefs + íconos).
- [ ] **Títulos de columnas**: Navegación / Recursos / Contáctanos.
- [ ] **Contacto**: email, "Cartagena, Colombia" (+ su enlace), "Boletín semanal" (+ su enlace).
- [ ] **Copyright**: empresa, URL y texto.
- [ ] **Enlace de privacidad**: label + enlace (`privacy_label`, `privacy_href`).

### 🎨 Apariencia (Temas)
- [ ] **Colores, gradientes, superficies y fuentes**: `/plataforma/cms/themes` (presets rápidos: Institucional, Moderno, Minimalista, Vibrante, Oscuro).
- [ ] El **preview en vivo** muestra los cambios antes de guardar.

---

## 3. Qué NO es editable desde el CMS (y por qué)

| Elemento | Razón |
|---|---|
| **Fallbacks** que solo aparecen si un campo queda vacío (hrefs del hero, textos alternativos de imágenes) | Comportamiento intencional de seguridad: el sitio siempre funciona aunque el editor no configure el valor. Configura el campo en el CMS y el fallback desaparece. |
| **Aria-labels funcionales**: "Compartir en Facebook/X/WhatsApp", "Anterior/Siguiente/Cerrar" de galerías, "Cerrar pop-up", "Limpiar búsqueda", breadcrumb | Etiquetas de accesibilidad estándar, no contenido editorial. |
| **Placeholders de los comentarios del blog** ("Tu nombre", "tu@email.com"...) | Microcopy funcional del formulario de comentarios. |
| **Datos de plataforma** (eventos, cursos, testimonios, prédicas, pastores) | Se editan en sus módulos (Agenda, Academia, CRM, Posts, Equipo Pastoral); el CMS decide si se publican. |
| **Nombre/email del sitio vía configuración** (`SITE_NAME`, `SITE_EMAIL`) | Constantes de despliegue por entorno; el email del footer ahora sí es editable desde `footer_config` → `contact.email`. |

---

## 4. Flujo de trabajo recomendado

1. **Cambiar un texto o imagen de una página** → Builder (`/plataforma/cms/builder?site=ccf&page=<slug>`) → seleccionar la sección → editar el JSON o usar los campos guiados → **Guardar** (publica).
2. **Cambiar una imagen** → subirla primero en **Media** → usarla desde el campo de imagen (la biblioteca CMS se integra en el editor).
3. **Cambiar navegación o footer** → **Menús** y página `footer`.
4. **Cambiar colores o textos del header** → **Temas** → Branding.
5. **Publicar contenido nuevo (post, testimonio)** → crearlo en su módulo y aprobarlo/publicarlo desde el CMS.

> ⚠️ Los roles: **Editor** puede editar y guardar borradores; **Gestor/Administrador** puede publicar. Sin publicación, los cambios no se ven en el sitio.

---

## 5. Referencia rápida: slug de página → ruta pública

| Página CMS (builder `page=`) | Ruta pública |
|---|---|
| `home` | `/` |
| `about` | `/nosotros` |
| `pastors` | `/pastores`, `/pastores/[slug]` |
| `events` | `/eventos` |
| `sermons` | `/predicas` |
| `courses` | `/cursos`, `/cursos/[id]` |
| `locations` | `/sedes` |
| `newsletter` | `/boletin` |
| `testimonials` | `/testimonios`, `/testimonios/[id]` |
| `blog` | `/blog`, `/blog/[slug]`, `/categoria/[slug]`, `/etiqueta/[slug]` |
| `contact` | `/contacto` |
| `discover` | `/conocer-a-jesus` |
| `privacy` | `/privacy` |
| `welcome` | `/welcome` |
| `footer` | global (todas las páginas) |
