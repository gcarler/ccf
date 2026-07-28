"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  CivicConvocatoriaCardsProps,
  CivicHeroSearchProps,
  CivicQuickLinksProps,
} from "@/types/cms-section-props";
import { Calendar, ChevronRight, Search } from "lucide-react";
import React, { useState } from "react";
import { asItems, asProps, val } from "./shared";

export function CivicConvocatoriaCardsSection({ section }: { section: CmsSection<"civic_convocatoria_cards"> }) {
  const props: CivicConvocatoriaCardsProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Convocatorias");
  const body = val(p, "body", "");
  const items = asItems(p) as Array<{
    title?: string; description?: string;
    status?: string; deadline?: string; category?: string; href?: string;
  }>;

  const statusMap: Record<string, { label: string; bg: string; text: string; dot: string }> = {
    abierta:  { label: "Abierta",      bg: "hsl(var(--success-muted))", text: "hsl(var(--success))", dot: "hsl(var(--success))" },
    cerrada:  { label: "Cerrada",      bg: "hsl(var(--destructive)/0.08)", text: "hsl(var(--destructive))", dot: "hsl(var(--destructive))" },
    proxima:  { label: "Próxima",      bg: "hsl(var(--info-muted))", text: "hsl(var(--info))", dot: "hsl(var(--info))" },
    revision: { label: "En revisión",  bg: "hsl(var(--warning-muted))", text: "hsl(var(--warning))", dot: "hsl(var(--warning))" },
  };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {(title || body) && (
        <div className="mb-10 md:mb-12">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-2 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8">
        {items.length === 0 && (
          <div className="col-span-full rounded-xl border-2 border-dashed p-12 text-center" style={{ borderColor: "var(--site-outline-variant)" }}>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>Agrega convocatorias usando el campo <strong>items</strong>.</p>
          </div>
        )}
        {items.map((item, i) => {
          const key = (item.status || "proxima").toLowerCase();
          const st = statusMap[key] || statusMap.proxima;
          return (
            <article
              key={i}
              className="rounded-xl border flex flex-col overflow-hidden transition-all hover:-translate-y-0.5 hover:shadow-md"
              style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
            >
              <div className="h-1.5" style={{ background: st.dot }} />
              <div className="flex-1 p-5 flex flex-col gap-3">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="font-black text-base leading-tight flex-1" style={{ color: "var(--site-on-surface)" }}>
                    {item.title || `Convocatoria ${i + 1}`}
                  </h3>
                  <span className="shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-bold" style={{ background: st.bg, color: st.text }}>
                    <span className="size-1.5 rounded-full" style={{ background: st.dot }} />
                    {st.label}
                  </span>
                </div>
                {item.category && (
                  <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>{item.category}</span>
                )}
                {item.description && (
                  <p className="text-sm leading-relaxed flex-1" style={{ color: "var(--site-on-surface-variant)" }}>{item.description}</p>
                )}
                {item.deadline && (
                  <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: key === "cerrada" ? "hsl(var(--destructive))" : "var(--site-on-surface-variant)" }}>
                    <Calendar size={12} /> Cierre: {item.deadline}
                  </div>
                )}
              </div>
              {item.href && (
                <div className="px-5 pb-5">
                  <a
                    href={item.href}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-bold transition-all hover:opacity-90"
                    style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                  >
                    Ver convocatoria <ChevronRight size={14} />
                  </a>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ─── Civic: Hero Search ───────────────────────────────────────────────────────

export function CivicHeroSearchSection({ section }: { section: CmsSection<"civic_hero_search"> }) {
  const props: CivicHeroSearchProps = section.props_json ?? {};
  const p = asProps(props);
  const eyebrow = val(p, "eyebrow", "");
  const title = val(p, "title", "¿Qué trámite buscas?");
  const subtitle = val(p, "subtitle", "Encuentra todo en un solo lugar.");
  const placeholder = val(p, "placeholder", "Buscar trámites, convocatorias, noticias...");
  const actionUrl = val(p, "action_url", "/buscar");
  const backgroundImage = val(p, "background_image", "");
  const suggestions = Array.isArray(p.suggestions) ? (p.suggestions as string[]) : [];
  const [query, setQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    window.location.href = `${actionUrl}?q=${encodeURIComponent(query.trim())}`;
  };

  return (
    <section
      className="relative flex flex-col items-center justify-center text-center px-4 py-16 md:py-24 overflow-hidden rounded-2xl"
      style={{
        background: backgroundImage
          ? `linear-gradient(rgba(0,0,0,0.55),rgba(0,0,0,0.6)),url('${backgroundImage}') center/cover no-repeat`
          : "var(--site-primary)",
      }}
    >
      {eyebrow && (
        <span className="text-[11px] font-black uppercase tracking-widest mb-3 px-3 py-1 rounded-full" style={{ background: "rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.9)" }}>
          {eyebrow}
        </span>
      )}
      <h1 className="text-3xl md:text-4xl lg:text-5xl font-black tracking-tight text-white drop-shadow-md max-w-3xl">
        {title}
      </h1>
      {subtitle && <p className="mt-4 text-base md:text-lg max-w-xl" style={{ color: "rgba(255,255,255,0.8)" }}>{subtitle}</p>}
      <form onSubmit={handleSearch} className="mt-8 w-full max-w-xl flex shadow-2xl rounded-2xl overflow-hidden">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label="Buscar trámites"
          className="flex-1 px-5 py-4 text-base outline-none bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
        />
        <button
          type="submit"
          className="px-6 py-4 font-black text-sm uppercase tracking-wide text-[hsl(var(--text-primary))] dark:text-white bg-[hsl(var(--bg-muted))] hover:bg-[hsl(var(--surface-2))] transition-colors flex items-center gap-2 whitespace-nowrap"
        >
          <Search size={16} /> Buscar
        </button>
      </form>
      {suggestions.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {suggestions.map((s, i) => (
            <button
              key={i}
              type="button"
              onClick={() => { window.location.href = `${actionUrl}?q=${encodeURIComponent(s)}`; }}
              className="text-xs font-semibold px-3 py-1 rounded-full transition-colors"
              style={{ background: "rgba(255,255,255,0.2)", color: "white" }}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Civic: Quick Links Grid ──────────────────────────────────────────────────

export function CivicQuickLinksSection({ section }: { section: CmsSection<"civic_quick_links"> }) {
  const props: CivicQuickLinksProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Accesos Rápidos");
  const body = val(p, "body", "");
  const columns = Math.max(2, Math.min(6, parseInt(val(p, "columns", "4"), 10)));
  const colClasses: Record<number, string> = {
    2: "grid-cols-2",
    3: "grid-cols-2 sm:grid-cols-3",
    4: "grid-cols-2 sm:grid-cols-2 md:grid-cols-4",
    5: "grid-cols-2 sm:grid-cols-3 md:grid-cols-5",
    6: "grid-cols-2 sm:grid-cols-3 md:grid-cols-6",
  };
  const items = asItems(p).slice(0, 12) as Array<{
    icon?: string; label?: string; href?: string; description?: string; color?: string;
  }>;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      {(title || body) && (
        <div className="mb-8 text-center">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-2 text-base max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className={`grid ${colClasses[columns] || colClasses[4]} gap-3`}>
        {items.map((item, i) => {
          const accent = item.color || "var(--site-primary)";
          return (
            <a
              key={i}
              href={item.href || "#"}
              className="group flex flex-col items-center text-center gap-3 p-5 rounded-2xl border transition-all hover:-translate-y-1 hover:shadow-lg focus-visible:ring-2 focus-visible:ring-offset-2"
              style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
            >
              <div
                className="size-14 rounded-2xl flex items-center justify-center text-3xl transition-transform group-hover:scale-110"
                style={{ background: `color-mix(in srgb, ${accent} 12%, transparent)`, color: accent }}
              >
                {item.icon || "🔗"}
              </div>
              <div>
                <p className="font-black text-sm leading-tight" style={{ color: "var(--site-on-surface)" }}>
                  {item.label || `Enlace ${i + 1}`}
                </p>
                {item.description && (
                  <p className="text-xs mt-1 leading-snug" style={{ color: "var(--site-on-surface-variant)" }}>
                    {item.description}
                  </p>
                )}
              </div>
            </a>
          );
        })}
        {items.length === 0 && (
          <div className="col-span-full rounded-xl border-2 border-dashed p-12 text-center" style={{ borderColor: "var(--site-outline-variant)" }}>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>Agrega enlaces usando el campo <strong>items</strong>.</p>
          </div>
        )}
      </div>
    </section>
  );
}
