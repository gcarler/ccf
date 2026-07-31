/**
 * Barrel file — re-exports all CMS section components from grouped modules.
 *
 * Import from here: `import { HeroSection, FaqSection } from "./sections"`.
 */

export { HeroSection, VideoHeroSection } from "./hero";
export {
  RichTextSection,
  RichTextColumnsSection,
  CardsSection,
  CtaBannerSection,
} from "./text";
export {
  TestimonialsSection,
  StatsSection,
  TeamSection,
  TestimonialsMasonrySection,
} from "./social-proof";
export {
  CountdownSection,
  PricingSection,
  TimelineSection,
  IconGridSection,
} from "./data";
export {
  TocSection,
  CollapsibleSection,
  ContentBlocksSection,
  AccordionSection,
  PolicyDocumentSection,
} from "./layout";
export {
  GallerySection,
  EmbedSection,
  ImageTextSection,
  VideoGridSection,
  EventsCalendarSection,
  LocationsListSection,
  CourseGridSection,
  BookShopSection,
} from "./media";
export { FaqSection } from "./faq";
export { NewsletterSection, DocumentUploadSection } from "./forms-interactive";
export {
  ButtonSection,
  DividerSection,
  SocialLinksSection,
  SpacerSection,
  CalendarSection,
  MapSection,
} from "./utilities";
export { PopupBlock } from "./popup";
export { ContactFormSection, PrayerFormSection } from "./forms";
export {
  CivicFileDownloadsSection,
  CivicDataTableSection,
  CivicAlertBannerSection,
} from "./civic-info";
export {
  CivicConvocatoriaCardsSection,
  CivicHeroSearchSection,
  CivicQuickLinksSection,
} from "./civic-engagement";
export { FooterConfigSection, MobileMenuConfigSection } from "./config";
export { AnimatedCounterSection } from "./AnimatedCounterSection";
export { VideoEmbedSection } from "./VideoEmbedSection";
export { GalleryMasonrySection } from "./GalleryMasonrySection";
export { MapEmbedSection } from "./MapEmbedSection";
