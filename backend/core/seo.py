"""SEO utilities for the CMS: JSON-LD Schema.org, sitemap.xml, robots.txt.

This module is framework-agnostic and works with the CCF CMS models.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.core.config import get_settings


def _iso_date(value: Optional[datetime]) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _w3c_date(value: Optional[datetime]) -> str:
    if not value:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.strftime("%Y-%m-%d")


# ── JSON-LD Schema.org generators ──────────────────────────────────────────


def build_website_json_ld(
    site_name: str,
    site_url: str,
    search_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for WebSite schema (including Sitelinks Searchbox)."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": site_name,
        "url": site_url,
    }
    if search_url:
        data["potentialAction"] = {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": search_url},
            "query-input": "required name=search_term_string",
        }
    return data


def build_organization_json_ld(
    name: str,
    url: str,
    logo: Optional[str] = None,
    same_as: Optional[List[str]] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for Organization schema."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": name,
        "url": url,
    }
    if logo:
        data["logo"] = logo
    if same_as:
        data["sameAs"] = same_as
    if description:
        data["description"] = description
    return data


def build_webpage_json_ld(
    title: str,
    description: Optional[str] = None,
    url: str = "",
    image: Optional[str] = None,
    date_published: Optional[datetime] = None,
    date_modified: Optional[datetime] = None,
    author_name: Optional[str] = None,
    site_name: Optional[str] = None,
    breadcrumbs: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for WebPage schema (default for any CMS page)."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": url,
    }
    if description:
        data["description"] = description
    if image:
        data["image"] = image
    if date_published:
        data["datePublished"] = _iso_date(date_published)
    if date_modified:
        data["dateModified"] = _iso_date(date_modified)
    if author_name:
        data["author"] = {"@type": "Organization", "name": author_name}
    if site_name:
        data["publisher"] = {"@type": "Organization", "name": site_name}
    if breadcrumbs:
        data["breadcrumb"] = build_breadcrumb_list_json_ld(breadcrumbs, url)
    return data


def build_article_json_ld(
    title: str,
    description: Optional[str] = None,
    url: str = "",
    image: Optional[str] = None,
    date_published: Optional[datetime] = None,
    date_modified: Optional[datetime] = None,
    author_name: Optional[str] = None,
    site_name: Optional[str] = None,
    word_count: Optional[int] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for Article schema (for rich text / blog-like pages)."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "url": url,
    }
    if description:
        data["description"] = description
    if image:
        data["image"] = image
    if date_published:
        data["datePublished"] = _iso_date(date_published)
    if date_modified:
        data["dateModified"] = _iso_date(date_modified)
    if author_name:
        data["author"] = {"@type": "Organization", "name": author_name}
    if site_name:
        data["publisher"] = {"@type": "Organization", "name": site_name}
    if word_count:
        data["wordCount"] = word_count
    return data


def build_faq_page_json_ld(
    questions: List[Dict[str, str]],
    url: str = "",
    site_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for FAQPage schema.

    Args:
        questions: List of dicts with ``question`` and ``answer`` keys.
    """
    main_entity = []
    for item in questions:
        q = item.get("question", "")
        a = item.get("answer", "")
        if not q or not a:
            continue
        main_entity.append({
            "@type": "Question",
            "name": q,
            "acceptedAnswer": {
                "@type": "Answer",
                "text": a,
            },
        })
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }
    if url:
        data["url"] = url
    if site_name:
        data["publisher"] = {"@type": "Organization", "name": site_name}
    return data


def build_event_json_ld(
    title: str,
    description: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    location_name: Optional[str] = None,
    location_address: Optional[str] = None,
    image: Optional[str] = None,
    url: str = "",
    site_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build JSON-LD for Event schema."""
    data: Dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": title,
        "url": url,
    }
    if description:
        data["description"] = description
    if start_date:
        data["startDate"] = start_date
    if end_date:
        data["endDate"] = end_date
    if image:
        data["image"] = image
    if location_name or location_address:
        data["location"] = {
            "@type": "Place",
            "name": location_name or "",
            "address": location_address or "",
        }
    if site_name:
        data["organizer"] = {"@type": "Organization", "name": site_name}
    return data


def build_breadcrumb_list_json_ld(
    items: List[Dict[str, str]],
    base_url: str = "",
) -> Dict[str, Any]:
    """Build JSON-LD for BreadcrumbList schema.

    Args:
        items: List of dicts with ``name`` and ``item`` (URL) keys.
        base_url: Base URL to prepend to relative paths.
    """
    item_list = []
    for i, item in enumerate(items):
        href = item.get("item", "")
        if href and not href.startswith(("http://", "https://")) and base_url:
            href = base_url.rstrip("/") + "/" + href.lstrip("/")
        entry: Dict[str, Any] = {
            "@type": "ListItem",
            "position": i + 1,
            "name": item.get("name", ""),
        }
        if href:
            entry["item"] = href
        item_list.append(entry)
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": item_list,
    }


def auto_json_ld_for_page(
    page,
    site,
    sections: Optional[List] = None,
    base_url: str = "",
    site_name: str = "",
) -> Optional[Dict[str, Any]]:
    """Automatically pick the best JSON-LD schema for a CMS page based on its sections.

    Inspects ``sections`` to decide between Article, FAQPage, Event, or WebPage.
    Falls back to WebPage if no specific signals are found.
    """
    if not page:
        return None

    title = getattr(page, "title", "")
    seo = getattr(page, "seo_json", None) or {}
    description = seo.get("meta_description") if isinstance(seo, dict) else None
    image = seo.get("meta_image") if isinstance(seo, dict) else None
    slug = getattr(page, "slug", "")
    url = f"{base_url.rstrip('/')}/{slug.lstrip('/')}"
    date_published = getattr(page, "created_at", None)
    date_modified = getattr(page, "updated_at", None)

    # Detect FAQ page
    faq_sections = []
    if sections:
        for section in sections:
            sec_type = getattr(section, "type", "")
            props = getattr(section, "props_json", None) or {}
            if sec_type == "faq" and isinstance(props, dict):
                items = props.get("items") or props.get("faqs") or []
                for item in items:
                    if isinstance(item, dict):
                        q = item.get("q") or item.get("question", "")
                        a = item.get("a") or item.get("answer", "")
                        if q and a:
                            faq_sections.append({"question": q, "answer": a})
    if faq_sections:
        return build_faq_page_json_ld(faq_sections, url=url, site_name=site_name)

    # Detect Article (rich_text heavy pages)
    has_article_signals = False
    if sections:
        for section in sections:
            if getattr(section, "type", "") in {"rich_text", "rich_text_columns"}:
                has_article_signals = True
                break
    if has_article_signals:
        word_count = 0
        if sections:
            for section in sections:
                props = getattr(section, "props_json", None) or {}
                if isinstance(props, dict) and isinstance(props.get("body"), str):
                    word_count += len(props["body"].split())
        return build_article_json_ld(
            title=title,
            description=description,
            url=url,
            image=image,
            date_published=date_published,
            date_modified=date_modified,
            author_name=site_name,
            site_name=site_name,
            word_count=word_count if word_count > 0 else None,
        )

    # Default: WebPage
    return build_webpage_json_ld(
        title=title,
        description=description,
        url=url,
        image=image,
        date_published=date_published,
        date_modified=date_modified,
        author_name=site_name,
        site_name=site_name,
    )


# ── Sitemap.xml generator ──────────────────────────────────────────────────


def build_sitemap_xml(
    pages,
    base_url: str,
    include_images: bool = False,
) -> str:
    """Build a sitemap.xml string from a list of CMS pages.

    Args:
        pages: Iterable of page-like objects with ``slug``, ``updated_at``,
            ``status``, and optionally ``seo_json`` attributes.
        base_url: The canonical base URL (e.g. ``https://example.com``).
        include_images: If True, also list Open Graph images as sitemap images.
    """
    urlset = ET.Element(
        "urlset",
        xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
    )
    # Add image namespace if needed
    if include_images:
        urlset.set(
            "xmlns:image",
            "http://www.google.com/schemas/sitemap-image/1.1",
        )

    ns_image = "http://www.google.com/schemas/sitemap-image/1.1"

    for page in pages:
        slug = getattr(page, "slug", "")
        status = getattr(page, "status", "")
        if status != "published":
            continue
        url_el = ET.SubElement(urlset, "url")
        loc = ET.SubElement(url_el, "loc")
        page_url = f"{base_url.rstrip('/')}/{slug.lstrip('/')}"
        loc.text = page_url

        lastmod = ET.SubElement(url_el, "lastmod")
        lastmod.text = _w3c_date(getattr(page, "updated_at", None))

        # Default priority based on depth
        depth = len([p for p in slug.split("/") if p])
        priority_val = max(0.1, 1.0 - (depth * 0.2))
        priority = ET.SubElement(url_el, "priority")
        priority.text = f"{priority_val:.1f}"

        changefreq = ET.SubElement(url_el, "changefreq")
        changefreq.text = "weekly"

        # Image sitemap
        if include_images:
            seo = getattr(page, "seo_json", None) or {}
            if isinstance(seo, dict):
                img_url = seo.get("meta_image")
                if img_url:
                    image_el = ET.SubElement(url_el, f"{{{ns_image}}}image")
                    image_loc = ET.SubElement(image_el, f"{{{ns_image}}}loc")
                    image_loc.text = str(img_url)

    # Pretty-print
    ET.indent(urlset, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(urlset, encoding="unicode")


# ── Robots.txt generator ───────────────────────────────────────────────────


def build_robots_txt(
    base_url: str,
    sitemap_url: Optional[str] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Build a robots.txt string.

    Args:
        base_url: The canonical base URL.
        sitemap_url: Full URL to the sitemap.xml.
        rules: List of dicts with keys ``user_agent`` (str) and
            ``allow``/``disallow`` (list of str).  Example::

                [{"user_agent": "*", "allow": ["/"], "disallow": ["/admin/"]}]
    """
    lines: List[str] = []
    default_rules = rules or [
        {"user_agent": "*", "allow": ["/"], "disallow": ["/plataforma/", "/api/"]},
    ]
    for rule in default_rules:
        ua = rule.get("user_agent", "*")
        lines.append(f"User-agent: {ua}")
        for path in rule.get("disallow", []):
            lines.append(f"Disallow: {path}")
        for path in rule.get("allow", []):
            lines.append(f"Allow: {path}")
        lines.append("")

    if sitemap_url:
        lines.append(f"Sitemap: {sitemap_url}")
    elif base_url:
        lines.append(f"Sitemap: {base_url.rstrip('/')}/sitemap.xml")

    return "\n".join(lines).strip() + "\n"
