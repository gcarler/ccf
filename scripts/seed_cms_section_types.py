"""Seed cms_section_types table with all supported section types.

Run this script to populate the cms_section_types table for existing
databases that were created before this migration.

Usage:
    python -m scripts.seed_cms_section_types
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.database import SessionLocal
from backend.models_cms import CmsSectionType

# All supported section types
SECTION_TYPES = [
    ("hero", "Hero banner with title, subtitle, and CTA"),
    ("video_hero", "Hero banner with background video"),
    ("rich_text", "Rich text content block"),
    ("rich_text_columns", "Multi-column rich text layout"),
    ("cards", "Grid of cards with images and descriptions"),
    ("cta_banner", "Call-to-action banner"),
    ("gallery", "Image gallery with lightbox"),
    ("faq", "Accordion-style FAQ section"),
    ("embed", "External content embed (YouTube, Maps, etc.)"),
    ("testimonials", "Customer testimonials carousel"),
    ("stats", "Statistics/numbers display"),
    ("team", "Team members display"),
    ("countdown", "Countdown timer"),
    ("pricing", "Pricing table"),
    ("image_text", "Side-by-side image and text"),
    ("timeline", "Timeline of events"),
    ("icon_grid", "Grid of icons with labels"),
    ("newsletter", "Newsletter signup form"),
    ("popup_banner", "Popup/modal banner"),
    ("button", "Standalone button component"),
    ("toc", "Table of contents"),
    ("divider", "Visual divider/separator"),
    ("collapsible", "Collapsible content section"),
    ("social_links", "Social media links"),
    ("spacer", "Vertical spacing element"),
    ("calendar", "Calendar widget"),
    ("map", "Map embed"),
    ("document_upload", "Document upload area"),
    ("content_blocks", "Reusable content blocks"),
    ("accordion", "Accordion component"),
]


def seed_section_types():
    """Insert all section types if they don't exist."""
    db = SessionLocal()
    try:
        existing = {row.name for row in db.query(CmsSectionType).all()}
        added = 0
        for name, description in SECTION_TYPES:
            if name not in existing:
                db.add(CmsSectionType(name=name, description=description, is_active=True))
                added += 1
        if added > 0:
            db.commit()
            print(f"Seeded {added} section types")
        else:
            print("All section types already exist")
    finally:
        db.close()


if __name__ == "__main__":
    seed_section_types()
