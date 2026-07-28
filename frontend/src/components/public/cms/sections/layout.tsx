"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  TocProps,
  CollapsibleProps,
  ContentBlocksProps,
  AccordionProps,
  PolicyDocumentProps,
} from "@/types/cms-section-props";
import { AnimatePresence, motion } from "framer-motion";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { sanitizeCmsHtml } from "@/lib/cms/sanitize";
import { asItems, asProps, val } from "./shared";

export function TocSection({ section }: { section: CmsSection<"toc"> }) {
  const props: TocProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "En esta página");
  const items = asItems(p).filter(Boolean);
  return (
    <section className="py-6 md:py-8 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="max-w-2xl rounded-lg p-4 border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)" }}>
        <h3 className="text-sm font-bold uppercase tracking-wide mb-3" style={{ color: "var(--site-primary)" }}>{title}</h3>
        <nav>
          <ol className="space-y-2">
            {items.map((item, i) => (
              <li key={i}>
                <a href={val(item, "href", "#")} className="flex items-center gap-2 text-sm font-medium hover:underline" style={{ color: "var(--site-on-surface)" }}>
                  <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>{i + 1}</span>
                  {val(item, "label", `Sección ${i + 1}`)}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      </div>
    </section>
  );
}

// ─── Collapsible ───────────────────────────────────────────────────────────────

export function CollapsibleSection({ section }: { section: CmsSection<"collapsible"> }) {
  const props: CollapsibleProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Información");
  const defaultOpen = p.default_open === true;
  const contentHtml = sanitizeCmsHtml(val(p, "content_html", ""));
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="py-4 md:py-6 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)" }}>
        <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--site-on-surface)" }}>
          <span className="font-bold text-lg">{title}</span>
          <ChevronDown size={20} className={`transition-transform duration-300 ${open ? "rotate-180" : ""}`} />
        </button>
        <AnimatePresence>
          {open && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
              <div className="px-4 pb-4" style={{ color: "var(--site-on-surface-variant)" }} dangerouslySetInnerHTML={{ __html: contentHtml }} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}

// ─── Content Blocks ────────────────────────────────────────────────────────────

export function ContentBlocksSection({ section }: { section: CmsSection<"content_blocks"> }) {
  const props: ContentBlocksProps = section.props_json ?? {};
  const p = asProps(props);
  const columns = parseInt(val(p, "columns", "2"));
  const blocks = asItems(p).filter(Boolean);
  const colClass = columns === 3 ? "md:grid-cols-3" : columns === 4 ? "md:grid-cols-4" : "md:grid-cols-2";

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className={`grid grid-cols-1 ${colClass} gap-6`}>
        {blocks.map((block, i) => {
          const type = val(block, "type", "text");
          if (type === "text") return <div key={i} dangerouslySetInnerHTML={{ __html: sanitizeCmsHtml(val(block, "content", "")) }} />;
          if (type === "image") return (
            <div key={i} className="rounded-lg overflow-hidden">
              <OptimizedImage src={val(block, "image_url", "")} alt={val(block, "alt", "")} width={800} height={450} className="w-full h-auto" />
              {val(block, "caption") && <p className="text-xs mt-1 opacity-60 text-center">{val(block, "caption")}</p>}
            </div>
          );
          if (type === "quote") return (
            <blockquote key={i} className="p-4 rounded-lg border-l-4 italic" style={{ borderColor: "var(--site-primary)", background: "var(--site-surface-container)" }}>
              <p className="text-lg" style={{ color: "var(--site-on-surface)" }}>{val(block, "text", "")}</p>
              {val(block, "author") && <p className="text-sm mt-2 font-semibold" style={{ color: "var(--site-primary)" }}>— {val(block, "author")}</p>}
            </blockquote>
          );
          if (type === "divider") return <hr key={i} className="col-span-full" style={{ borderColor: "var(--site-outline-variant)" }} />;
          if (type === "spacer") return <div key={i} style={{ height: `${parseInt(val(block, "height", "32"))}px` }} />;
          return null;
        })}
      </div>
    </section>
  );
}

// ─── Accordion ─────────────────────────────────────────────────────────────────

export function AccordionSection({ section }: { section: CmsSection<"accordion"> }) {
  const props: AccordionProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const subtitle = val(p, "subtitle", "");
  const items = asItems(p).filter(Boolean);
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {title && <h3 className="text-lg font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h3>}
      {subtitle && <p className="text-sm mb-6" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="rounded-lg border overflow-hidden" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}>
            <button onClick={() => setOpenIdx(openIdx === i ? null : i)} className="w-full flex items-center justify-between p-4 text-left" style={{ color: "var(--site-on-surface)" }}>
              <span className="font-semibold">{val(item, "question", `Pregunta ${i + 1}`)}</span>
              <ChevronDown size={18} className={`transition-transform duration-300 ${openIdx === i ? "rotate-180" : ""}`} />
            </button>
            <AnimatePresence>
              {openIdx === i && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                  <div className="px-4 pb-4 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                    {val(item, "answer", "")}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Policy Document ───────────────────────────────────────────────────────────

export function PolicyDocumentSection({ section }: { section: CmsSection<"policy_document"> }) {
  const props: PolicyDocumentProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Política de Privacidad");
  const lastUpdate = val(p, "last_update", "");
  const summary = val(p, "summary", "");
  const items = asItems(p).slice(0, 50) as Array<{ id?: string; title?: string; content?: string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h1 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h1>}
      {lastUpdate && <p className="mt-2 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>Última actualización: {lastUpdate}</p>}
      {summary && <p className="mt-4 text-base leading-relaxed" style={{ color: "var(--site-on-surface)" }}>{summary}</p>}
      {items.length > 0 && (
        <div className="mt-8 space-y-6">
          {items.map((item, i) => (
            <div key={i} id={item.id || `section-${i}`} className="rounded-xl p-5" style={{ background: "var(--site-surface-container)" }}>
              <h2 className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{item.title || `Sección ${i + 1}`}</h2>
              <div className="mt-2 text-sm leading-relaxed whitespace-pre-line" style={{ color: "var(--site-on-surface-variant)" }}>{item.content}</div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
