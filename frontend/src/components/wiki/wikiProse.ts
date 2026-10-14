/**
 * Estilos compartidos para el contenido rich-text de las wikis
 * (ProjectWikiEditor y UniversalWikiView).
 *
 * Regla del Design System: solo tokens semánticos `hsl(var(--*))`.
 * Los tokens cambian entre tema claro y oscuro, por lo que el contraste
 * se mantiene sin colores hardcodeados por tema.
 */
export const WIKI_PROSE_CLASS = 'wiki-prose';

export const WIKI_PROSE_CSS = `
    .wiki-prose { color: hsl(var(--foreground)); line-height: 1.7; }
    .wiki-prose > *:first-child { margin-top: 0; }

    /* ── Listas con numerales y viñetas visibles ── */
    .wiki-prose ul,
    .wiki-prose ol {
        margin: 1rem 0;
        padding-left: 1.625rem;
    }
    .wiki-prose ol { list-style-type: decimal; }
    .wiki-prose ul { list-style-type: disc; }
    .wiki-prose ol > li,
    .wiki-prose ul > li {
        display: list-item;
        margin: 0.375rem 0;
        padding-left: 0.25rem;
    }
    .wiki-prose ol > li::marker,
    .wiki-prose ul > li::marker {
        color: hsl(var(--text-secondary));
        font-weight: 700;
    }
    .wiki-prose ol ol { list-style-type: lower-alpha; }
    .wiki-prose ol ol ol { list-style-type: lower-roman; }
    .wiki-prose ul ul { list-style-type: circle; }
    .wiki-prose li > p { margin: 0; }

    /* ── Encabezados ── */
    .wiki-prose h1,
    .wiki-prose h2,
    .wiki-prose h3 {
        color: hsl(var(--foreground));
        font-weight: 800;
        line-height: 1.25;
        margin: 1.5rem 0 0.75rem;
        letter-spacing: -0.01em;
    }
    .wiki-prose h1 { font-size: 1.75rem; }
    .wiki-prose h2 { font-size: 1.375rem; }
    .wiki-prose h3 { font-size: 1.125rem; }

    /* ── Tipografía inline ── */
    .wiki-prose strong { font-weight: 700; color: hsl(var(--foreground)); }
    .wiki-prose em { font-style: italic; }
    .wiki-prose u { text-decoration: underline; text-underline-offset: 3px; }
    .wiki-prose code {
        font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, monospace;
        font-size: 0.875em;
        padding: 0.15em 0.4em;
        border-radius: 0.375rem;
        background: hsl(var(--surface-2));
        color: hsl(var(--destructive));
    }
    .wiki-prose pre {
        margin: 1rem 0;
        padding: 0.875rem 1rem;
        border-radius: 0.5rem;
        background: hsl(var(--surface-2));
        border: 1px solid hsl(var(--border));
        overflow-x: auto;
        font-size: 0.8125rem;
        line-height: 1.6;
    }
    .wiki-prose pre code { background: none; padding: 0; color: inherit; font-size: inherit; }

    /* ── Citas ── */
    .wiki-prose blockquote {
        margin: 1.25rem 0;
        padding: 0.75rem 1.25rem;
        border-left: 4px solid hsl(var(--primary));
        border-radius: 0 0.5rem 0.5rem 0;
        background: hsl(var(--surface-2));
        color: hsl(var(--text-primary));
        font-style: italic;
    }
    .wiki-prose blockquote p { margin: 0.25rem 0; }

    /* ── Separador e imágenes ── */
    .wiki-prose hr {
        margin: 1.75rem 0;
        border: none;
        border-top: 2px solid hsl(var(--border));
    }
    .wiki-prose img {
        max-width: 100%;
        height: auto;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border: 1px solid hsl(var(--border));
    }
`;
