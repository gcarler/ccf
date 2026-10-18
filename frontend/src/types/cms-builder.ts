/**
 * Contratos canónicos del CMS Builder (Puck — @puckeditor/core 0.22).
 *
 * Fuente de las shapes: destructuración del render de cada bloque en
 * `src/app/plataforma/cms/builder/page.tsx` y del DTO del backend `cms/v2`
 * (`CmsSection` en `@/types/cms-v2`). Mantener sincronizado cualquier
 * cambio de schema de props con `backend/schemas/cms_v2_sections.py` y
 * `src/types/cms-section-props.ts` (mirror Pydantic del renderer público).
 */
import type { ComponentDataOptionalId } from "@puckeditor/core";
import type { ReactNode } from "react";
import type { CmsSection } from "@/types/cms-v2";

export type { FieldProps } from "@puckeditor/core";

// ─── Editor (Puck Data) ────────────────────────────────────────────────

/** Una sección renderizable del editor: { type, props: {..., id?, section_key?} }. */
export type PuckSectionData = ComponentDataOptionalId<
  Record<string, string | string[] | number | boolean>
>;

/** Datos raíz serializados de Puck usados por el builder (load / change / save). */
export interface PuckData {
  content: PuckSectionData[];
}

// ─── Base de datos (DTO cms/v2) ───────────────────────────────────────

/** DTO canónico de una sección persistida en la base de datos. */
export type DbSection = CmsSection;

// ─── Renders de bloques ───────────────────────────────────────────────

/** Destructuración del render de la raíz de Puck. */
export interface PuckRootRenderProps {
  children?: ReactNode;
  [key: string]: unknown;
}

/** Render del bloque Hero (CTA único + imagen de fondo). */
export interface HeroRenderProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  bg_image?: string;
  [key: string]: unknown;
}

/** Render de un bloque "banner" de CTA único. */
export interface BannerRenderProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  [key: string]: unknown;
}

/** Render de un bloque con doble CTA. */
export interface DoubleCtaRenderProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  cta_label_2?: string;
  cta_href_2?: string;
  [key: string]: unknown;
}

/** Props de un render de bloque con título/descripción opcionales y lista tipada. */
export interface ListSectionRenderProps<I extends object> {
  title?: string;
  body?: string;
  items?: I[] & Record<string, unknown>;
  [key: string]: unknown;
}

// ─── Ítems de bloques de lista ────────────────────────────────────────

/** Item del bloque FAQ (Preguntas frecuentes). */
export interface FaqItem {
  q?: string;
  a?: string;
}

/** Item de bloque con autor/testimonio (bloque "testimonials"). */
export interface AuthorItem {
  author?: string;
  role?: string;
  content?: string;
  stars?: number;
}

/** Item de bloque con par valor/etiqueta (bloque "stats" y opciones). */
export interface OptionItem {
  value?: string;
  label?: string;
}

/** Item del bloque de Galería (imagen; alias histórico CarouselItem). */
export interface CarouselItem {
  url?: string;
  alt?: string;
  caption?: string;
}
/** Alias del ítem de galería para usos tipo carrusel. */
export type GalleryItem = CarouselItem;

/** Item del bloque de Tarjetas. */
export interface CardItem {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  image_url?: string;
}

// ─── MediaPicker ──────────────────────────────────────────────────────

/** Item del selector de medios (galería de URLs del CMS). */
export interface MediaItem {
  id?: string;
  url?: string;
  name?: string;
  thumbnail_url?: string;
  mime_type?: string;
  size?: number;
  created_at?: string;
  [key: string]: string | number | undefined | null;
}
