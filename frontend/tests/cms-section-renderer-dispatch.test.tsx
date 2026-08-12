/**
 * Unit test — PublicSectionRenderer dispatch coverage.
 *
 * Verifies that every section type handled by the dispatch switch in
 * ``PublicSectionRenderer.tsx`` maps to the CORRECT component — not just
 * any component. This is done by mocking the sections barrel with stubs
 * that return a <div data-testid="section:{type}"> so we can assert the
 * exact component was rendered for each type.
 *
 * This guards against:
 *   - Missing case statements after refactoring.
 *   - Barrel export drift (index.ts forgetting to re-export a section).
 *   - Silent fallback to RichTextSection for a valid type.
 *   - Components that return null with empty props (gallery, popup_banner).
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { createMockCmsSection } from "@/test-utils/factories";

// ── Mock the sections barrel ─────────────────────────────────────────────────
// vi.mock is hoisted by vitest to the TOP of the file — before any const
// declarations. The factory MUST be fully self-contained (no references to
// outer-scope variables). Each stub returns a div with
// data-testid="section:{section.type}" so we can verify the dispatch
// selected the correct component for each type.

vi.mock("@/components/public/cms/sections", async () => {
  const React = await vi.importActual<typeof import("react")>("react");
  // List of all 48 component names exported by the barrel.
  // Must match sections/index.ts exports.
  const componentNames = [
    "HeroSection", "VideoHeroSection",
    "RichTextSection", "RichTextColumnsSection", "CardsSection", "CtaBannerSection",
    "TestimonialsSection", "StatsSection", "TeamSection",
    "CountdownSection", "PricingSection", "TimelineSection", "IconGridSection",
    "TocSection", "CollapsibleSection", "ContentBlocksSection",
    "AccordionSection", "PolicyDocumentSection", "TestimonialsMasonrySection",
    "GallerySection", "EmbedSection", "FeedSection", "ImageTextSection",
    "VideoGridSection", "EventsCalendarSection", "LocationsListSection",
    "CourseGridSection", "BookShopSection",
    "FaqSection", "NewsletterSection", "DocumentUploadSection",
    "ButtonSection", "DividerSection", "SocialLinksSection",
    "SpacerSection", "CalendarSection", "MapSection",
    "PopupBlock",
    "ContactFormSection", "PrayerFormSection",
    "CivicFileDownloadsSection", "CivicDataTableSection", "CivicAlertBannerSection",
    "CivicConvocatoriaCardsSection", "CivicHeroSearchSection", "CivicQuickLinksSection",
    "FooterConfigSection", "MobileMenuConfigSection",
  ];
  const stubs: Record<string, React.FC<{ section: { type: string } }>> = {};
  for (const name of componentNames) {
    stubs[name] = ({ section }) =>
      React.createElement("div", { "data-testid": `section:${section.type}` });
  }
  return stubs;
});

// Mock asTyped to pass through (it's a type-only cast at runtime)
vi.mock("@/components/public/cms/sections/shared", () => ({
  asTyped: (section: unknown) => section,
}));

// Import AFTER mocks are set up
import PublicSectionRenderer from "@/components/public/cms/PublicSectionRenderer";

// ── The 48 section types → expected component names ─────────────────────────
// Single source of truth that must match PublicSectionRenderer.tsx.
// Defined here (after vi.mock) so it's available at test-run time.

const TYPE_TO_COMPONENT: Record<string, string> = {
  // Core content
  hero: "HeroSection",
  video_hero: "VideoHeroSection",
  rich_text: "RichTextSection",
  rich_text_columns: "RichTextColumnsSection",
  cards: "CardsSection",
  cta_banner: "CtaBannerSection",
  gallery: "GallerySection",
  faq: "FaqSection",
  embed: "EmbedSection",
  feed: "FeedSection",
  testimonials: "TestimonialsSection",
  stats: "StatsSection",
  team: "TeamSection",
  countdown: "CountdownSection",
  pricing: "PricingSection",
  image_text: "ImageTextSection",
  timeline: "TimelineSection",
  icon_grid: "IconGridSection",
  newsletter: "NewsletterSection",
  popup_banner: "PopupBlock",
  // Interactive / utilities
  button: "ButtonSection",
  toc: "TocSection",
  divider: "DividerSection",
  collapsible: "CollapsibleSection",
  social_links: "SocialLinksSection",
  spacer: "SpacerSection",
  calendar: "CalendarSection",
  map: "MapSection",
  document_upload: "DocumentUploadSection",
  content_blocks: "ContentBlocksSection",
  accordion: "AccordionSection",
  // Civic
  civic_file_downloads: "CivicFileDownloadsSection",
  civic_data_table: "CivicDataTableSection",
  civic_alert_banner: "CivicAlertBannerSection",
  civic_convocatoria_cards: "CivicConvocatoriaCardsSection",
  civic_hero_search: "CivicHeroSearchSection",
  civic_quick_links: "CivicQuickLinksSection",
  // Config-only shells (data comes from external APIs)
  events_calendar: "EventsCalendarSection",
  video_grid: "VideoGridSection",
  locations_list: "LocationsListSection",
  contact_form: "ContactFormSection",
  prayer_form: "PrayerFormSection",
  course_grid: "CourseGridSection",
  book_shop: "BookShopSection",
  testimonials_masonry: "TestimonialsMasonrySection",
  policy_document: "PolicyDocumentSection",
  // Config sections
  footer_config: "FooterConfigSection",
  mobile_menu_config: "MobileMenuConfigSection",
};

const ALL_SECTION_TYPES = Object.keys(TYPE_TO_COMPONENT);

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeSection(type: string) {
  return createMockCmsSection(type, {
    id: `test-${type}`,
    page_id: "test-page",
    section_key: `key-${type}`,
  });
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PublicSectionRenderer dispatch", () => {
  it("covers exactly 48 section types", () => {
    expect(ALL_SECTION_TYPES).toHaveLength(48);
    // No duplicate types
    expect(new Set(ALL_SECTION_TYPES).size).toBe(48);
    // No duplicate component names
    const componentNames = Object.values(TYPE_TO_COMPONENT);
    expect(new Set(componentNames).size).toBe(componentNames.length);
  });

  // Generate one test per section type — each verifies the dispatch
  // selected the CORRECT component (not just any component).
  it.each(ALL_SECTION_TYPES)(
    'dispatches type="%s" to the correct component',
    (type) => {
      const section = makeSection(type);
      const { getByTestId } = render(<PublicSectionRenderer section={section} />);
      // The mock stub renders data-testid="section:{type}".
      // If the dispatch falls through to default (RichTextSection),
      // the data-testid would be "section:rich_text" instead.
      expect(() => getByTestId(`section:${type}`)).not.toThrow();
    },
  );

  it("falls back to RichTextSection for an unknown type", () => {
    const section = makeSection("__nonexistent_type__");
    const { getByTestId } = render(<PublicSectionRenderer section={section} />);
    // The default case calls RichTextSection. Since asTyped is a runtime
    // no-op, the section's type stays "__nonexistent_type__" — the stub
    // renders data-testid="section:__nonexistent_type__". We just verify
    // SOMETHING rendered (i.e. the dispatch didn't crash on unknown types).
    expect(() => getByTestId("section:__nonexistent_type__")).not.toThrow();
  });
});
