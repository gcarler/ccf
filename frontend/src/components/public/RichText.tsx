"use client";

import React from "react";
import { sanitizeCmsHtml } from "@/lib/cms/sanitize";

/**
 * RichText — pro typography for CMS content.
 *
 * Accepts raw HTML from the CMS and renders it with beautiful, consistent
 * typography: headings, lists, blockquotes, links, inline code, bold/italic,
 * horizontal rules, and more.
 *
 * Usage:
 *   <RichText html={cmsContent} />
 *   <RichText html={section.body} className="mt-4" />
 */

interface RichTextProps {
    html: string;
    className?: string;
    as?: "div" | "article" | "section";
}

const RICH_TEXT_CSS = `
    .ccf-rich-text {
        /* ── Base typography ── */
        line-height: 1.7;
        font-size: 1rem;
        color: inherit;
    }

    /* ── Headings ── */
    .ccf-rich-text h1 {
        font-size: clamp(1.5rem, 2.5vw, 2rem);
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 2rem 0 0.75rem;
        line-height: 1.2;
    }
    .ccf-rich-text h2 {
        font-size: clamp(1.25rem, 2vw, 1.5rem);
        font-weight: 700;
        letter-spacing: -0.01em;
        margin: 1.75rem 0 0.5rem;
        line-height: 1.3;
    }
    .ccf-rich-text h3 {
        font-size: clamp(1.125rem, 1.5vw, 1.25rem);
        font-weight: 700;
        margin: 1.5rem 0 0.5rem;
        line-height: 1.4;
    }
    .ccf-rich-text h4,
    .ccf-rich-text h5,
    .ccf-rich-text h6 {
        font-size: 1.125rem;
        font-weight: 600;
        margin: 1.25rem 0 0.5rem;
    }

    /* ── Paragraphs ── */
    .ccf-rich-text p {
        margin: 0.75rem 0;
    }
    .ccf-rich-text p:first-child { margin-top: 0; }
    .ccf-rich-text p:last-child { margin-bottom: 0; }

    /* ── Links ── */
    .ccf-rich-text a {
        color: var(--site-primary, #6366f1);
        text-decoration: underline;
        text-decoration-color: var(--site-primary, #6366f1);
        text-decoration-thickness: 2px;
        text-underline-offset: 2px;
        transition: opacity 0.2s;
    }
    .ccf-rich-text a:hover { opacity: 0.75; }

    /* ── Bold & Italic ── */
    .ccf-rich-text strong,
    .ccf-rich-text b {
        font-weight: 700;
    }
    .ccf-rich-text em,
    .ccf-rich-text i {
        font-style: italic;
    }

    /* ── Lists ── */
    .ccf-rich-text ul,
    .ccf-rich-text ol {
        margin: 1rem 0;
        padding-left: 1.5rem;
    }
    .ccf-rich-text ul { list-style-type: disc; }
    .ccf-rich-text ol { list-style-type: decimal; }
    .ccf-rich-text ul ul,
    .ccf-rich-text ol ul { list-style-type: circle; }
    .ccf-rich-text li {
        margin: 0.5rem 0;
        padding-left: 0.25rem;
    }
    .ccf-rich-text li::marker {
        color: var(--site-primary, #6366f1);
    }

    /* ── Blockquotes ── */
    .ccf-rich-text blockquote {
        margin: 1.5rem 0;
        padding: 1rem 1.25rem;
        border-left: 4px solid var(--site-primary, #6366f1);
        background: rgba(99, 102, 241, 0.05);
        border-radius: 0 0.5rem 0.5rem 0;
        font-style: italic;
        color: inherit;
        opacity: 0.85;
    }
    .ccf-rich-text blockquote p { margin: 0.25rem 0; }

    /* ── Code ── */
    .ccf-rich-text code {
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
        font-size: 0.875em;
        padding: 0.15em 0.4em;
        border-radius: 0.375rem;
        background: rgba(0, 0, 0, 0.06);
        color: #e11d48;
    }
    .dark .ccf-rich-text code {
        background: rgba(255, 255, 255, 0.08);
        color: #fb7185;
    }
    .ccf-rich-text pre {
        margin: 1.5rem 0;
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        background: #1e293b;
        color: #e2e8f0;
        overflow-x: auto;
        font-size: 0.875rem;
        line-height: 1.6;
    }
    .ccf-rich-text pre code {
        background: none;
        color: inherit;
        padding: 0;
        font-size: inherit;
    }

    /* ── Horizontal rule ── */
    .ccf-rich-text hr {
        margin: 2rem 0;
        border: none;
        border-top: 2px solid var(--site-outline-variant, rgba(0,0,0,0.1));
    }

    /* ── Images ── */
    .ccf-rich-text img {
        max-width: 100%;
        height: auto;
        border-radius: 0.75rem;
        margin: 1.5rem 0;
    }

    /* ── Tables ── */
    .ccf-rich-text table {
        width: 100%;
        border-collapse: collapse;
        margin: 1.5rem 0;
        font-size: 0.875rem;
    }
    .ccf-rich-text th,
    .ccf-rich-text td {
        padding: 0.75rem 1rem;
        border: 1px solid var(--site-outline-variant, rgba(0,0,0,0.1));
        text-align: left;
    }
    .ccf-rich-text th {
        font-weight: 700;
        background: rgba(99, 102, 241, 0.05);
    }

    /* ── First heading flush ── */
    .ccf-rich-text > h1:first-child,
    .ccf-rich-text > h2:first-child,
    .ccf-rich-text > h3:first-child {
        margin-top: 0;
    }
`;

export default function RichText({ html, className = "", as: Tag = "div" }: RichTextProps) {
    if (!html) return null;
    const safeHtml = sanitizeCmsHtml(html);

    return (
        <>
            <style>{RICH_TEXT_CSS}</style>
            <Tag
                className={`ccf-rich-text ${className}`}
                dangerouslySetInnerHTML={{ __html: safeHtml }}
            />
        </>
    );
}
