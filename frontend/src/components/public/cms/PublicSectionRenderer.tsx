"use client";

import { CmsSection } from "@/types/cms-v2";

// ── Section components ──────────────────────────────────────────────────────
// All section components are extracted into grouped files under ``./sections``.
// This file is now a thin dispatch table (~60 lines).
import {
  HeroSection,
  VideoHeroSection,
  RichTextSection,
  RichTextColumnsSection,
  CardsSection,
  CtaBannerSection,
  GallerySection,
  FaqSection,
  EmbedSection,
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
} from "./sections";
// Shared type-cast helper for the dispatch switch.
import { asTyped } from "./sections/shared";

export default function PublicSectionRenderer({ section }: { section: CmsSection }) {
  switch (section.type) {
    case "hero":             return <HeroSection section={asTyped<"hero">(section)} />;
    case "video_hero":       return <VideoHeroSection section={asTyped<"video_hero">(section)} />;
    case "rich_text":        return <RichTextSection section={asTyped<"rich_text">(section)} />;
    case "rich_text_columns":return <RichTextColumnsSection section={asTyped<"rich_text_columns">(section)} />;
    case "cards":            return <CardsSection section={asTyped<"cards">(section)} />;
    case "cta_banner":       return <CtaBannerSection section={asTyped<"cta_banner">(section)} />;
    case "gallery":          return <GallerySection section={asTyped<"gallery">(section)} />;
    case "faq":              return <FaqSection section={asTyped<"faq">(section)} />;
    case "embed":            return <EmbedSection section={asTyped<"embed">(section)} />;
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
    // New 11
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
    // Civic blocks
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
    default:                       return <RichTextSection section={asTyped<"rich_text">(section)} />;
  }
}
