import { getCmsMediaUrl } from "@/lib/cms/media";

export interface PublicHeroSlideInput {
  src?: string;
  url?: string;
  alt?: string;
  caption?: string;
  title?: string;
  href?: string;
  status?: string;
}

export interface NormalizedHeroProps {
  eyebrow: string;
  title?: string;
  titleLead: string;
  titleAccent: string;
  titleTail: string;
  description: string;
  primaryCta?: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  slides: Array<{
    src: string;
    alt: string;
    title?: string;
    caption?: string;
    href?: string;
  }>;
}

export interface NormalizedPopupProps {
  title: string;
  body: string;
  ctaLabel: string;
  ctaHref: string;
  delayMs: number;
  startAt: string;
  endAt: string;
  showOnPaths: string[];
  hideOnPaths: string[];
  dismissMode: "local" | "session" | "none";
  dismissDays: number;
  dismissKey: string;
}

export function cmsValue(props: Record<string, unknown>, key: string, fallback = ""): string {
  const value = props?.[key];
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

export function cmsStringList(props: Record<string, unknown>, key: string): string[] {
  const value = props?.[key];
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    return value
      .split(/[\n,]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return [];
}

export function cmsItems(props: Record<string, unknown>): Array<Record<string, unknown>> {
  return Array.isArray(props.items)
    ? (props.items as Array<Record<string, unknown>>).filter(
        (item) => Boolean(item) && (item as { status?: string }).status !== "archived",
      )
    : [];
}

export function parseCmsDateOrNull(value: string): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function parseCmsNonNegativeInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? Math.max(0, parsed) : fallback;
}

export function parseCmsPositiveInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? Math.max(1, parsed) : fallback;
}

export function matchesCmsPathRule(pathname: string, rule: string): boolean {
  const normalizedRule = rule.trim();
  if (!normalizedRule) return false;
  if (normalizedRule === "/") return true;
  if (normalizedRule.endsWith("*")) {
    return pathname.startsWith(normalizedRule.slice(0, -1));
  }
  return pathname === normalizedRule || pathname.startsWith(`${normalizedRule}/`);
}

export function shouldRenderCmsPopup(config: Pick<NormalizedPopupProps, "startAt" | "endAt" | "showOnPaths" | "hideOnPaths">, pathname: string, now = new Date()): boolean {
  const current = pathname || "/";
  if (config.showOnPaths.length > 0 && !config.showOnPaths.some((rule) => matchesCmsPathRule(current, rule))) {
    return false;
  }
  if (config.hideOnPaths.some((rule) => matchesCmsPathRule(current, rule))) {
    return false;
  }
  const startDate = parseCmsDateOrNull(config.startAt);
  const endDate = parseCmsDateOrNull(config.endAt);
  if (startDate && now < startDate) return false;
  if (endDate && now > endDate) return false;
  return true;
}

export function normalizeHeroProps(props: Record<string, unknown>): NormalizedHeroProps {
  const titleLead = cmsValue(props, "title_lead", "");
  const titleAccent = cmsValue(props, "title_accent", "");
  const titleTail = cmsValue(props, "title_tail", "");
  const title = cmsValue(props, "title", titleLead || titleAccent || titleTail ? "" : "Bienvenidos");
  const description = cmsValue(props, "description", cmsValue(props, "body", ""));
  const primaryLabel = cmsValue(props, "primary_cta", cmsValue(props, "cta_label", ""));
  const primaryHref = cmsValue(props, "primary_cta_href", cmsValue(props, "cta_href", "/")) || "/";
  const secondaryLabel = cmsValue(props, "secondary_cta", "");
  const secondaryHref = cmsValue(props, "secondary_cta_href", "/") || "/";
  const imageUrl = getCmsMediaUrl(cmsValue(props, "bg_image", cmsValue(props, "image_url", "")));
  const imageAlt = cmsValue(props, "image_alt", title);
  const rawSlides = Array.isArray(props.slides) ? (props.slides as PublicHeroSlideInput[]) : [];
  const slidesFromProps = rawSlides
    .map((item) => ({
      src: getCmsMediaUrl(String(item.src || item.url || "")),
      alt: String(item.alt || item.title || title),
      title: String(item.title || title),
      caption: String(item.caption || description || ""),
      href: typeof item.href === "string" ? item.href : undefined,
    }))
    .filter((slide) => slide.src);
  const itemSlides = (cmsItems(props) as PublicHeroSlideInput[])
    .filter((item) => item.url || item.src)
    .map((item) => ({
      src: getCmsMediaUrl(String(item.url || item.src || "")),
      alt: String(item.alt || item.title || title),
      title: String(item.title || title),
      caption: String(item.caption || description || ""),
      href: typeof item.href === "string" ? item.href : undefined,
    }));

  return {
    eyebrow: cmsValue(props, "eyebrow", ""),
    title: title || undefined,
    titleLead,
    titleAccent,
    titleTail,
    description,
    primaryCta: primaryLabel ? { label: primaryLabel, href: primaryHref } : undefined,
    secondaryCta: secondaryLabel ? { label: secondaryLabel, href: secondaryHref } : undefined,
    slides: [
      ...slidesFromProps,
      ...(imageUrl ? [{ src: imageUrl, alt: imageAlt, title, caption: description || undefined }] : []),
      ...itemSlides,
    ],
  };
}

export function normalizePopupProps(props: Record<string, unknown>, sectionId: string): NormalizedPopupProps {
  const rawDismissMode = cmsValue(props, "dismiss_mode", "local").toLowerCase();
  const dismissMode = rawDismissMode === "session" || rawDismissMode === "none" ? rawDismissMode : "local";

  return {
    title: cmsValue(props, "title", "Aviso Importante"),
    body: cmsValue(props, "body", ""),
    ctaLabel: cmsValue(props, "cta_label", "Ver Más"),
    ctaHref: cmsValue(props, "cta_href", "/"),
    delayMs: parseCmsNonNegativeInt(cmsValue(props, "delay_ms", "2000"), 2000),
    startAt: cmsValue(props, "start_at", ""),
    endAt: cmsValue(props, "end_at", ""),
    showOnPaths: cmsStringList(props, "show_on_paths"),
    hideOnPaths: cmsStringList(props, "hide_on_paths"),
    dismissMode,
    dismissDays: parseCmsPositiveInt(cmsValue(props, "dismiss_days", "30"), 30),
    dismissKey: cmsValue(props, "dismiss_key", "") || `cms_popup_${sectionId}`,
  };
}
