"""Canonical fallback catalog for CMS section types.

The database catalog is authoritative at runtime. This immutable fallback is
used only when the catalog table cannot be queried (for example during a
partial migration or an unavailable database). Keeping it in one dependency-
free module prevents CMS v1 and v2 from silently accepting different blocks.
"""

from __future__ import annotations

FALLBACK_SECTION_TYPES = frozenset(
    {
        "hero",
        "video_hero",
        "rich_text",
        "rich_text_columns",
        "cards",
        "cta_banner",
        "gallery",
        "faq",
        "embed",
        "testimonials",
        "stats",
        "team",
        "countdown",
        "pricing",
        "image_text",
        "timeline",
        "icon_grid",
        "newsletter",
        "popup_banner",
        "button",
        "toc",
        "divider",
        "collapsible",
        "social_links",
        "spacer",
        "calendar",
        "map",
        "document_upload",
        "content_blocks",
        "accordion",
        "civic_hero_search",
        "civic_convocatoria_cards",
        "civic_quick_links",
        "civic_file_downloads",
        "civic_data_table",
        "civic_alert_banner",
        "animated_counter",
        "video_embed",
        "gallery_masonry",
        "map_embed",
    }
)
