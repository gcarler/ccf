"use client";

import { useEffect, useState, useRef } from "react";
import { CmsSection, CmsAbTest } from "@/types/cms-v2";
import { recordCmsAbTestEvent } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";

// ── Section components ──────────────────────────────────────────────────────
import {
  HeroSection,
  VideoHeroSection,
  RichTextSection,
  RichTextColumnsSection,
  AboutSection,
  CardsSection,
  CtaBannerSection,
  GallerySection,
  FaqSection,
  EmbedSection,
  FeedSection,
  TestimonialsSection,
  StatsSection,
  TeamSection,
  CountdownSection,
  PricingSection,
  ImageTextSection,
  TimelineSection,
  IconGridSection,
  NewsletterSection,
  PopupBlock,
  ButtonSection,
  TocSection,
  DividerSection,
  CollapsibleSection,
  SocialLinksSection,
  SpacerSection,
  CalendarSection,
  MapSection,
  DocumentUploadSection,
  ContentBlocksSection,
  AccordionSection,
  CivicFileDownloadsSection,
  CivicDataTableSection,
  CivicAlertBannerSection,
  CivicConvocatoriaCardsSection,
  CivicHeroSearchSection,
  CivicQuickLinksSection,
  EventsCalendarSection,
  VideoGridSection,
  LocationsListSection,
  ContactFormSection,
  PrayerFormSection,
  CourseGridSection,
  BookShopSection,
  TestimonialsMasonrySection,
  PolicyDocumentSection,
  FooterConfigSection,
  MobileMenuConfigSection,
  AnimatedCounterSection,
  VideoEmbedSection,
  GalleryMasonrySection,
  MapEmbedSection,
} from "./sections";
// Shared type-cast helper for the dispatch switch.
import { asTyped } from "./sections/shared";

interface PublicSectionRendererProps {
  section: CmsSection;
  abTest?: CmsAbTest | null;
  sectionB?: CmsSection | null;
  siteKey?: string;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(?:^|; )" + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, "\\$1") + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : null;
}

function setCookie(name: string, value: string, days = 365) {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

export default function PublicSectionRenderer({
  section,
  abTest,
  sectionB,
  siteKey = SITE_KEY,
}: PublicSectionRendererProps) {
  const [variant, setVariant] = useState<"a" | "b">("a");
  const [visitorId, setVisitorId] = useState<string>("");
  const viewRecordedRef = useRef(false);
  const clickRecordedRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined" || !abTest || abTest.status !== "active") return;

    let vid = getCookie("ab_visitor_id") || getCookie("ccf_ab_visitor_id");
    if (!vid && typeof localStorage !== "undefined") {
      vid = localStorage.getItem("ab_visitor_id") || localStorage.getItem("ccf_ab_visitor_id");
    }
    if (!vid) {
      vid = "v_" + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
    }
    setCookie("ab_visitor_id", vid);
    setCookie("ccf_ab_visitor_id", vid);
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("ab_visitor_id", vid);
      localStorage.setItem("ccf_ab_visitor_id", vid);
    }
    setVisitorId(vid);

    let hash = 0;
    const key = vid + abTest.id;
    for (let i = 0; i < key.length; i++) {
      hash = (hash << 5) - hash + key.charCodeAt(i);
      hash |= 0;
    }
    const normalized = (Math.abs(hash) % 100) / 100;
    const resolvedVariant: "a" | "b" = normalized < (abTest.traffic_split ?? 0.5) ? "a" : "b";
    setVariant(resolvedVariant);

    if (!viewRecordedRef.current) {
      viewRecordedRef.current = true;
      recordCmsAbTestEvent(siteKey, abTest.id, {
        variant: resolvedVariant,
        event_type: "view",
        visitor_id: vid,
      }).catch(() => {});
    }
  }, [abTest, siteKey]);

  const handleContainerClick = () => {
    if (!abTest || abTest.status !== "active" || !visitorId || clickRecordedRef.current) return;
    clickRecordedRef.current = true;
    recordCmsAbTestEvent(siteKey, abTest.id, {
      variant,
      event_type: "click",
      visitor_id: visitorId,
    }).catch(() => {});
  };

  const targetSection = variant === "b" && sectionB ? sectionB : section;

  return (
    <div
      data-ab-test-id={abTest?.id}
      data-ab-variant={variant}
      onClick={handleContainerClick}
    >
      {renderSection(targetSection)}
    </div>
  );
}

function renderSection(section: CmsSection) {
  switch (section.type) {
    case "hero":             return <HeroSection section={asTyped<"hero">(section)} />;
    case "video_hero":       return <VideoHeroSection section={asTyped<"video_hero">(section)} />;
    case "rich_text":        return <RichTextSection section={asTyped<"rich_text">(section)} />;
    case "rich_text_columns":return <RichTextColumnsSection section={asTyped<"rich_text_columns">(section)} />;
    case "about":            return <AboutSection section={asTyped<"about">(section)} />;
    case "cards":            return <CardsSection section={asTyped<"cards">(section)} />;
    case "cta_banner":       return <CtaBannerSection section={asTyped<"cta_banner">(section)} />;
    case "gallery":          return <GallerySection section={asTyped<"gallery">(section)} />;
    case "faq":              return <FaqSection section={asTyped<"faq">(section)} />;
    case "embed":            return <EmbedSection section={asTyped<"embed">(section)} />;
    case "feed":             return <FeedSection section={asTyped<"feed">(section)} />;
    case "testimonials":     return <TestimonialsSection section={asTyped<"testimonials">(section)} />;
    case "stats":            return <StatsSection section={asTyped<"stats">(section)} />;
    case "team":             return <TeamSection section={asTyped<"team">(section)} />;
    case "countdown":        return <CountdownSection section={asTyped<"countdown">(section)} />;
    case "pricing":          return <PricingSection section={asTyped<"pricing">(section)} />;
    case "image_text":       return <ImageTextSection section={asTyped<"image_text">(section)} />;
    case "timeline":         return <TimelineSection section={asTyped<"timeline">(section)} />;
    case "icon_grid":        return <IconGridSection section={asTyped<"icon_grid">(section)} />;
    case "newsletter":       return <NewsletterSection section={asTyped<"newsletter">(section)} />;
    case "popup_banner":     return <PopupBlock section={asTyped<"popup_banner">(section)} />;
    case "button":           return <ButtonSection section={asTyped<"button">(section)} />;
    case "toc":              return <TocSection section={asTyped<"toc">(section)} />;
    case "divider":          return <DividerSection section={asTyped<"divider">(section)} />;
    case "collapsible":      return <CollapsibleSection section={asTyped<"collapsible">(section)} />;
    case "social_links":     return <SocialLinksSection section={asTyped<"social_links">(section)} />;
    case "spacer":           return <SpacerSection section={asTyped<"spacer">(section)} />;
    case "calendar":         return <CalendarSection section={asTyped<"calendar">(section)} />;
    case "map":              return <MapSection section={asTyped<"map">(section)} />;
    case "document_upload":  return <DocumentUploadSection section={asTyped<"document_upload">(section)} />;
    case "content_blocks":   return <ContentBlocksSection section={asTyped<"content_blocks">(section)} />;
    case "accordion":              return <AccordionSection section={asTyped<"accordion">(section)} />;
    case "civic_file_downloads":   return <CivicFileDownloadsSection section={asTyped<"civic_file_downloads">(section)} />;
    case "civic_data_table":       return <CivicDataTableSection section={asTyped<"civic_data_table">(section)} />;
    case "civic_alert_banner":     return <CivicAlertBannerSection section={asTyped<"civic_alert_banner">(section)} />;
    case "civic_convocatoria_cards": return <CivicConvocatoriaCardsSection section={asTyped<"civic_convocatoria_cards">(section)} />;
    case "civic_hero_search":      return <CivicHeroSearchSection section={asTyped<"civic_hero_search">(section)} />;
    case "civic_quick_links":      return <CivicQuickLinksSection section={asTyped<"civic_quick_links">(section)} />;
    case "events_calendar":        return <EventsCalendarSection section={asTyped<"events_calendar">(section)} />;
    case "video_grid":             return <VideoGridSection section={asTyped<"video_grid">(section)} />;
    case "locations_list":         return <LocationsListSection section={asTyped<"locations_list">(section)} />;
    case "contact_form":           return <ContactFormSection section={asTyped<"contact_form">(section)} />;
    case "prayer_form":            return <PrayerFormSection section={asTyped<"prayer_form">(section)} />;
    case "course_grid":            return <CourseGridSection section={asTyped<"course_grid">(section)} />;
    case "book_shop":              return <BookShopSection section={asTyped<"book_shop">(section)} />;
    case "testimonials_masonry":   return <TestimonialsMasonrySection section={asTyped<"testimonials_masonry">(section)} />;
    case "policy_document":        return <PolicyDocumentSection section={asTyped<"policy_document">(section)} />;
    case "footer_config":          return <FooterConfigSection section={asTyped<"footer_config">(section)} />;
    case "mobile_menu_config":     return <MobileMenuConfigSection section={asTyped<"mobile_menu_config">(section)} />;
    case "animated_counter":       return <AnimatedCounterSection section={asTyped<"animated_counter">(section)} />;
    case "video_embed":            return <VideoEmbedSection section={asTyped<"video_embed">(section)} />;
    case "gallery_masonry":        return <GalleryMasonrySection section={asTyped<"gallery_masonry">(section)} />;
    case "map_embed":              return <MapEmbedSection section={asTyped<"map_embed">(section)} />;
    default:                       return <UnsupportedSection type={section.type} />;
  }
}

function UnsupportedSection({ type }: { type: string }) {
  if (process.env.NODE_ENV !== "production") {
    console.warn(`[CMS] Tipo de sección sin renderer público: ${type}`);
  }
  return (
    <section
      aria-label="Sección no disponible"
      data-cms-unsupported-section={type}
      className="mx-auto my-6 max-w-6xl rounded-lg border border-dashed border-[hsl(var(--border))] p-6 text-center text-sm text-[hsl(var(--text-secondary))]"
    >
      Esta sección todavía no está disponible para publicación.
    </section>
  );
}
