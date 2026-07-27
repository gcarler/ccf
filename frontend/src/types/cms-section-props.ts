/**
 * Section props contracts — mirror of backend Pydantic schemas.
 *
 * Source of truth: ``backend/schemas/cms_v2_sections.py`` (SECTION_PROPS_SCHEMAS).
 * The backend persists ``props_json`` after running ``validate_section_props()``,
 * which uses Pydantic with ``extra="ignore"`` (drops unknown keys) and
 * ``model_dump(exclude_unset=True)`` (only emits keys the admin set). Every
 * Pydantic field has a default, so emitted props are partial — all fields
 * here are optional unless the row was authored otherwise.
 *
 * Why a separate module: the discriminated union needs ~44 interfaces and a
 * union type, none of which fit cleanly inside ``cms-v2.ts`` next to the
 * ``CmsSection`` core shape. Keeping the contracts in their own file also
 * lets the public renderer import only the prop interface it needs for a
 * given sub-component, instead of pulling the whole union.
 *
 * Why ``extra="ignore"``-style permissiveness on the TS side: the backend
 * already strips unknown keys, but a row authored before a schema existed
 * can still carry fields the schema now forbids — those bypass the strip
 * on read. Keeping every field optional means clients degrade gracefully
 * to the renderer's fallback defaults rather than type-erroring at runtime.
 *
 * BN: cada interfaz toma el nombre ``<Type>Props`` en ``snake_case`` (igual
 * que el backend) para que el intercambio de claves en revisiones sea
 * trivial; el renderer normaliza a ``camelCase`` únicamente cuando hay un
 * motivo de alias presentacional (p. ej. Hero.divide~titleLead).
 */

// ─── Shared item shapes ---------------------------------------------------------------

export interface ButtonItem {
  label?: string;
  href?: string;
  variant?: "primary" | "outline" | "ghost" | string;
  size?: "sm" | "md" | "lg" | string;
  icon?: string | null;
}

export interface TocItem {
  label?: string;
  href?: string;
}

export interface CollapsibleItem {
  question?: string;
  answer?: string;
}

export interface SocialLinkItem {
  platform?: string;
  url?: string;
  label?: string;
}

export interface CalendarItem {
  title?: string;
  date?: string | null;
  time?: string | null;
  location?: string | null;
}

export interface ContentBlock {
  type?: "text" | "image" | "video" | "quote" | "divider" | "spacer" | "list" | string;
  content?: string | null;
  image_url?: string | null;
  alt?: string | null;
  caption?: string | null;
  text?: string | null;
  author?: string | null;
  height?: string | null;
}

export interface HeroSlideItem {
  src?: string | null;
  url?: string | null;
  alt?: string | null;
  title?: string | null;
  caption?: string | null;
  href?: string | null;
  status?: string | null;
}

export interface CardItem {
  title?: string | null;
  body?: string | null;
  href?: string | null;
  icon?: string | null;
}

export interface GalleryItem {
  url?: string | null;
  alt?: string | null;
  caption?: string | null;
}

export interface FaqItem {
  q?: string | null;
  a?: string | null;
}

export interface TestimonialItemPublic {
  author?: string | null;
  role?: string | null;
  content?: string | null;
  stars?: number;
}

export interface StatItem {
  value?: string | null;
  label?: string | null;
}

export interface TeamMemberItem {
  name?: string | null;
  role?: string | null;
  image?: string | null;
  bio?: string | null;
}

export interface PricingItem {
  name?: string | null;
  price?: string | null;
  features?: string | null;
  btn?: string | null;
  btn_href?: string | null;
}

export interface TimelineEntryItem {
  year?: string | null;
  title?: string | null;
  body?: string | null;
}

export interface IconGridItem {
  icon?: string | null;
  title?: string | null;
  body?: string | null;
}

export interface CivicConvocatoriaItem {
  title?: string | null;
  description?: string | null;
  status?: string | null;
  deadline?: string | null;
  category?: string | null;
  href?: string | null;
}

export interface CivicQuickLinkItem {
  icon?: string | null;
  label?: string | null;
  href?: string | null;
  description?: string | null;
  color?: string | null;
}

export interface CivicFileDownloadItem {
  name?: string | null;
  file_url?: string | null;
  format?: string | null;
  size_label?: string | null;
  description?: string | null;
}

export interface LocationItem {
  name?: string;
  address?: string;
  city?: string;
  phone?: string;
  schedule?: string;
  embed_url?: string;
  lat?: number | null;
  lng?: number | null;
  is_main?: boolean;
}

export interface CourseItem {
  id?: string;
  title?: string;
  description?: string;
  instructor?: string;
  modality?: string;
  lessons?: number;
  image_url?: string | null;
  cta_label?: string;
}

export interface BookItem {
  id?: string;
  title?: string;
  author?: string;
  price?: string;
  description?: string;
  image_url?: string | null;
}

export interface TestimonialItem {
  author?: string;
  role?: string;
  content?: string;
  image_url?: string | null;
  stars?: number;
}

export interface PolicySectionItem {
  id?: string;
  title?: string;
  content?: string;
}

export interface FooterLinkGroup {
  title?: string;
  links?: SocialLinkItem[];
}

export interface MobileMenuItem {
  label?: string;
  href?: string;
  icon?: string;
}

// ─── 44 section-type props interfaces ------------------------------------------------
//
// Naming: the exported interface MUST be ``<PascalCaseType>Props`` where
// ``PascalCaseType`` is the section type with the first letter capitalised
// (e.g. ``hero`` → ``Hero``, ``image_text`` → ``ImageText``,
// ``civic_hero_search`` → ``CivicHeroSearch``). The props map at the bottom
// of this file relies on this convention.

export interface HeroProps {
  title?: string;
  title_lead?: string;
  title_accent?: string;
  title_tail?: string;
  description?: string;
  body?: string;
  eyebrow?: string;
  primary_cta?: string;
  primary_cta_href?: string;
  secondary_cta?: string;
  secondary_cta_href?: string;
  cta_label?: string;
  cta_href?: string;
  bg_image?: string;
  image_url?: string;
  image_alt?: string;
  slides?: HeroSlideItem[] | HeroSlideItem[];
  items?: HeroSlideItem[];
}

export interface VideoHeroProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  video_url?: string;
}

export interface RichTextProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
}

export interface RichTextColumnsProps {
  title?: string;
  body?: string;
  body_2?: string;
}

export interface CardsProps {
  title?: string;
  body?: string;
  items?: CardItem[];
}

export interface CtaBannerProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  cta_label_2?: string;
  cta_href_2?: string;
}

export interface GalleryProps {
  title?: string;
  body?: string;
  image_url?: string;
  image_alt?: string;
  items?: GalleryItem[];
}

export interface FaqProps {
  title?: string;
  items?: FaqItem[];
}

export interface EmbedProps {
  title?: string;
  body?: string;
  embed_url?: string;
}

export interface TestimonialsProps {
  title?: string;
  items?: TestimonialItemPublic[];
}

export interface StatsProps {
  title?: string;
  items?: StatItem[];
}

export interface TeamProps {
  title?: string;
  items?: TeamMemberItem[];
}

export interface CountdownProps {
  title?: string;
  target_date?: string;
  body?: string;
}

export interface PricingProps {
  title?: string;
  items?: PricingItem[];
}

export interface ImageTextProps {
  title?: string;
  body?: string;
  image_url?: string;
  image_alt?: string;
  cta_label?: string;
  cta_href?: string;
  image_side?: string;
}

export interface TimelineProps {
  title?: string;
  items?: TimelineEntryItem[];
}

export interface IconGridProps {
  title?: string;
  body?: string;
  items?: IconGridItem[];
}

export interface NewsletterProps {
  title?: string;
  body?: string;
  cta_label?: string;
  action_url?: string;
}

export interface ButtonProps {
  buttons?: ButtonItem[];
  align?: string;
  gap?: string;
}

export interface TocProps {
  title?: string;
  items?: TocItem[];
  style?: string;
}

export interface DividerProps {
  style?: string;
  color?: string;
  thickness?: string;
  margin_top?: string;
  margin_bottom?: string;
  width?: string;
}

export interface CollapsibleProps {
  title?: string;
  default_open?: boolean;
  content_html?: string;
  bg_color?: string;
  border?: boolean;
}

export interface SocialLinksProps {
  title?: string;
  items?: SocialLinkItem[];
  layout?: string;
  show_labels?: boolean;
  icon_size?: string;
}

export interface SpacerProps {
  height?: string;
  bg_color?: string;
  label?: string;
}

export interface CalendarProps {
  title?: string;
  source?: string;
  api_endpoint?: string | null;
  view?: string;
  max_events?: number;
  show_time?: boolean;
  show_location?: boolean;
  items?: CalendarItem[];
}

export interface MapProps {
  title?: string;
  provider?: string;
  embed_url?: string;
  address?: string;
  lat?: number | null;
  lng?: number | null;
  zoom?: number;
  height?: string;
  show_directions_link?: boolean;
}

export interface DocumentUploadProps {
  title?: string;
  description?: string;
  accepted_types?: string;
  max_size_mb?: string;
  upload_endpoint?: string | null;
  success_message?: string;
  show_file_list?: boolean;
}

export interface ContentBlocksProps {
  layout?: string;
  columns?: string;
  items?: ContentBlock[];
}

export interface AccordionProps {
  title?: string;
  subtitle?: string;
  items?: CollapsibleItem[];
  style?: string;
  open_multiple?: boolean;
}

export interface PopupProps {
  title?: string;
  body?: string;
  cta_label?: string;
  cta_href?: string;
  delay_ms?: number;
  start_at?: string | null;
  end_at?: string | null;
  show_on_paths?: string[];
  hide_on_paths?: string[];
  dismiss_mode?: "local" | "session" | "none" | string;
  dismiss_days?: number;
  dismiss_key?: string;
}

export interface EventsCalendarProps {
  title?: string;
  subtitle?: string;
  show_filters?: boolean;
  filters?: string[];
  max_events?: number;
  show_ics_export?: boolean;
  empty_title?: string;
  empty_description?: string;
  featured_badge?: string;
  reserve_cta?: string;
}

export interface VideoGridProps {
  title?: string;
  subtitle?: string;
  channel_url?: string;
  channel_label?: string;
  max_videos?: number;
  search_placeholder?: string;
  empty_title?: string;
  empty_description?: string;
}

export interface LocationsListProps {
  title?: string;
  subtitle?: string;
  search_placeholder?: string;
  show_map?: boolean;
  locations?: LocationItem[];
}

export interface ContactFormProps {
  title?: string;
  subtitle?: string;
  name_label?: string;
  name_placeholder?: string;
  phone_label?: string;
  phone_placeholder?: string;
  message_label?: string;
  message_placeholder?: string;
  submit_label?: string;
  success_message?: string;
  action_url?: string;
}

export interface PrayerFormProps {
  title?: string;
  subtitle?: string;
  name_label?: string;
  name_placeholder?: string;
  request_label?: string;
  request_placeholder?: string;
  submit_label?: string;
  success_message?: string;
  action_url?: string;
}

export interface CourseGridProps {
  title?: string;
  subtitle?: string;
  courses_title?: string;
  courses_description?: string;
  featured_course_id?: string | null;
  show_free_only?: boolean;
  courses?: CourseItem[];
  empty_title?: string;
  empty_description?: string;
}

export interface BookShopProps {
  title?: string;
  subtitle?: string;
  books?: BookItem[];
  empty_message?: string;
}

export interface TestimonialsMasonryProps {
  title?: string;
  subtitle?: string;
  testimonials?: TestimonialItem[];
  cta_label?: string;
  cta_href?: string;
  empty_title?: string;
}

export interface PolicyDocumentProps {
  title?: string;
  last_update?: string;
  summary?: string;
  sections?: PolicySectionItem[];
}

export interface FooterConfigProps {
  brand_description?: string;
  location_label?: string;
  newsletter_label?: string;
  copyright?: string;
  copyright_url?: string;
  nav_groups?: FooterLinkGroup[];
  social_links?: SocialLinkItem[];
}

export interface MobileMenuConfigProps {
  items?: MobileMenuItem[];
}

export interface CivicHeroSearchProps {
  eyebrow?: string;
  title?: string;
  subtitle?: string;
  placeholder?: string;
  action_url?: string;
  background_image?: string;
  suggestions?: string[];
}

export interface CivicConvocatoriaCardsProps {
  title?: string;
  body?: string;
  items?: CivicConvocatoriaItem[];
}

export interface CivicQuickLinksProps {
  title?: string;
  body?: string;
  columns?: string;
  items?: CivicQuickLinkItem[];
}

export interface CivicFileDownloadsProps {
  title?: string;
  body?: string;
  items?: CivicFileDownloadItem[];
}

export interface CivicDataTableProps {
  title?: string;
  caption?: string;
  headers?: string[];
  rows?: string[][];
  highlight_first_col?: boolean;
  striped?: boolean;
  footer_note?: string;
}

export interface CivicAlertBannerProps {
  level?: string;
  title?: string;
  message?: string;
  cta_label?: string;
  cta_href?: string;
  dismissible?: boolean;
}

// ─── Catalog & union -----------------------------------------------------------------

/** Section type strings the CMS recognises (mirrors backend catalog). */
export type CmsSectionType =
  | "button"
  | "toc"
  | "divider"
  | "collapsible"
  | "social_links"
  | "spacer"
  | "calendar"
  | "map"
  | "document_upload"
  | "content_blocks"
  | "accordion"
  | "popup_banner"
  | "events_calendar"
  | "video_grid"
  | "locations_list"
  | "contact_form"
  | "prayer_form"
  | "course_grid"
  | "book_shop"
  | "testimonials_masonry"
  | "policy_document"
  | "footer_config"
  | "mobile_menu_config"
  | "hero"
  | "video_hero"
  | "rich_text"
  | "rich_text_columns"
  | "cards"
  | "cta_banner"
  | "gallery"
  | "faq"
  | "embed"
  | "testimonials"
  | "stats"
  | "team"
  | "countdown"
  | "pricing"
  | "image_text"
  | "timeline"
  | "icon_grid"
  | "newsletter"
  | "civic_hero_search"
  | "civic_convocatoria_cards"
  | "civic_quick_links"
  | "civic_file_downloads"
  | "civic_data_table"
  | "civic_alert_banner";

/**
 * Maps each section type string to its props interface.
 * Acts as the lookup table for the discriminated union below.
 * Keep alphabetised by section_type for parity with SECTION_PROPS_SCHEMAS.
 */
export interface CmsSectionTypeToProps {
  button: ButtonProps;
  toc: TocProps;
  divider: DividerProps;
  collapsible: CollapsibleProps;
  social_links: SocialLinksProps;
  spacer: SpacerProps;
  calendar: CalendarProps;
  map: MapProps;
  document_upload: DocumentUploadProps;
  content_blocks: ContentBlocksProps;
  accordion: AccordionProps;
  popup_banner: PopupProps;
  events_calendar: EventsCalendarProps;
  video_grid: VideoGridProps;
  locations_list: LocationsListProps;
  contact_form: ContactFormProps;
  prayer_form: PrayerFormProps;
  course_grid: CourseGridProps;
  book_shop: BookShopProps;
  testimonials_masonry: TestimonialsMasonryProps;
  policy_document: PolicyDocumentProps;
  footer_config: FooterConfigProps;
  mobile_menu_config: MobileMenuConfigProps;
  hero: HeroProps;
  video_hero: VideoHeroProps;
  rich_text: RichTextProps;
  rich_text_columns: RichTextColumnsProps;
  cards: CardsProps;
  cta_banner: CtaBannerProps;
  gallery: GalleryProps;
  faq: FaqProps;
  embed: EmbedProps;
  testimonials: TestimonialsProps;
  stats: StatsProps;
  team: TeamProps;
  countdown: CountdownProps;
  pricing: PricingProps;
  image_text: ImageTextProps;
  timeline: TimelineProps;
  icon_grid: IconGridProps;
  newsletter: NewsletterProps;
  civic_hero_search: CivicHeroSearchProps;
  civic_convocatoria_cards: CivicConvocatoriaCardsProps;
  civic_quick_links: CivicQuickLinksProps;
  civic_file_downloads: CivicFileDownloadsProps;
  civic_data_table: CivicDataTableProps;
  civic_alert_banner: CivicAlertBannerProps;
}

/**
 * Discriminated union of every section variant. The discriminant is
 * ``type``, narrowing ``props_json`` to the matching interface:
 *
 *   type T = Extract<CmsSectionDiscriminated, { type: "hero" }>;
 *   // -> { id: string; page_id: string; section_key: string; type: "hero";
 *   //      props_json: HeroProps; sort_order: number; is_visible: boolean;
 *   //      status: ...; created_at: string; updated_at: string }
 *
 * Consumers iterate ``CmsSectionDiscriminated[]`` and switch on
 * ``section.type`` -- once narrowed, ``section.props_json`` is statically
 * typed without runtime casts. Each variant carries the full ``CmsSection``
 * shape so existing APIs that read ``section.section_key`` or
 * ``section.id`` keep working.
 *
 * For sections whose ``type`` is a string not in the catalog (admin
 * experiments, future types), fall back to ``CmsSection`` (the generic
 * default with ``type: string`` and ``props_json: Record<string, unknown>``).
 */
type CmsSectionBase<T extends string, P> = {
  id: string;
  page_id: string;
  section_key: string;
  type: T;
  props_json: P;
  sort_order: number;
  is_visible: boolean;
  status: "active" | "archived" | string;
  created_at: string;
  updated_at: string;
};

export type CmsSectionDiscriminated =
  | CmsSectionBase<"hero", HeroProps>
  | CmsSectionBase<"video_hero", VideoHeroProps>
  | CmsSectionBase<"rich_text", RichTextProps>
  | CmsSectionBase<"rich_text_columns", RichTextColumnsProps>
  | CmsSectionBase<"cards", CardsProps>
  | CmsSectionBase<"cta_banner", CtaBannerProps>
  | CmsSectionBase<"gallery", GalleryProps>
  | CmsSectionBase<"faq", FaqProps>
  | CmsSectionBase<"embed", EmbedProps>
  | CmsSectionBase<"testimonials", TestimonialsProps>
  | CmsSectionBase<"stats", StatsProps>
  | CmsSectionBase<"team", TeamProps>
  | CmsSectionBase<"countdown", CountdownProps>
  | CmsSectionBase<"pricing", PricingProps>
  | CmsSectionBase<"image_text", ImageTextProps>
  | CmsSectionBase<"timeline", TimelineProps>
  | CmsSectionBase<"icon_grid", IconGridProps>
  | CmsSectionBase<"newsletter", NewsletterProps>
  | CmsSectionBase<"button", ButtonProps>
  | CmsSectionBase<"toc", TocProps>
  | CmsSectionBase<"divider", DividerProps>
  | CmsSectionBase<"collapsible", CollapsibleProps>
  | CmsSectionBase<"social_links", SocialLinksProps>
  | CmsSectionBase<"spacer", SpacerProps>
  | CmsSectionBase<"calendar", CalendarProps>
  | CmsSectionBase<"map", MapProps>
  | CmsSectionBase<"document_upload", DocumentUploadProps>
  | CmsSectionBase<"content_blocks", ContentBlocksProps>
  | CmsSectionBase<"accordion", AccordionProps>
  | CmsSectionBase<"popup_banner", PopupProps>
  | CmsSectionBase<"events_calendar", EventsCalendarProps>
  | CmsSectionBase<"video_grid", VideoGridProps>
  | CmsSectionBase<"locations_list", LocationsListProps>
  | CmsSectionBase<"contact_form", ContactFormProps>
  | CmsSectionBase<"prayer_form", PrayerFormProps>
  | CmsSectionBase<"course_grid", CourseGridProps>
  | CmsSectionBase<"book_shop", BookShopProps>
  | CmsSectionBase<"testimonials_masonry", TestimonialsMasonryProps>
  | CmsSectionBase<"policy_document", PolicyDocumentProps>
  | CmsSectionBase<"footer_config", FooterConfigProps>
  | CmsSectionBase<"mobile_menu_config", MobileMenuConfigProps>
  | CmsSectionBase<"civic_hero_search", CivicHeroSearchProps>
  | CmsSectionBase<"civic_convocatoria_cards", CivicConvocatoriaCardsProps>
  | CmsSectionBase<"civic_quick_links", CivicQuickLinksProps>
  | CmsSectionBase<"civic_file_downloads", CivicFileDownloadsProps>
  | CmsSectionBase<"civic_data_table", CivicDataTableProps>
  | CmsSectionBase<"civic_alert_banner", CivicAlertBannerProps>;
