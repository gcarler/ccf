"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  ButtonProps,
  DividerProps,
  SocialLinksProps,
  SpacerProps,
  CalendarProps,
  MapProps,
} from "@/types/cms-section-props";
import { Calendar, ChevronRight, MapPin, Star } from "lucide-react";
import Link from "next/link";
import React from "react";
import { asItems, asProps, val } from "./shared";

export function ButtonSection({ section }: { section: CmsSection<"button"> }) {
  const props: ButtonProps = section.props_json ?? {};
  const p = asProps(props);
  const buttons = (Array.isArray(p.buttons) ? p.buttons : [{ label: "Click", href: "/" }]) as Array<{ label: string; href: string; variant?: string; size?: string; icon?: string }>;
  const align = val(p, "align", "center");
  const gapRaw = val(p, "gap", "4");
  const gapClass: Record<string, string> = { "2": "gap-2", "3": "gap-3", "4": "gap-6 md:gap-8", "6": "gap-6", "8": "gap-8" };
  const gap = gapClass[gapRaw] ?? "gap-6 md:gap-8";

  const sizeClasses: Record<string, string> = { sm: "text-xs px-3 py-1.5", md: "text-sm px-4 py-2", lg: "text-base px-6 py-3" };
  const variantBg: Record<string, string> = { primary: "var(--site-primary)", outline: "transparent", ghost: "transparent" };
  const variantBorder: Record<string, string> = { primary: "var(--site-primary)", outline: "var(--site-outline-variant)", ghost: "transparent" };
  const variantColor: Record<string, string> = { primary: "var(--site-on-primary)", outline: "var(--site-on-surface)", ghost: "var(--site-primary)" };

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className={`flex flex-wrap ${gap} ${align === "center" ? "justify-center" : align === "right" ? "justify-end" : "justify-start"}`}>
        {buttons.map((btn, i) => (
          <Link
            key={i}
            href={btn.href || "#"}
            className={`rounded-lg font-semibold transition-all hover:scale-105 ${sizeClasses[btn.size || "md"]}`}
            style={{
              background: variantBg[btn.variant || "primary"],
              border: `2px solid ${variantBorder[btn.variant || "primary"]}`,
              color: variantColor[btn.variant || "primary"],
            }}
          >
            {btn.label}
            {btn.icon && <ChevronRight size={16} className="inline ml-1" />}
          </Link>
        ))}
      </div>
    </section>
  );
}

// ─── Divider ───────────────────────────────────────────────────────────────────

export function DividerSection({ section }: { section: CmsSection<"divider"> }) {
  const props: DividerProps = section.props_json ?? {};
  const p = asProps(props);
  const style = val(p, "style", "solid");
  const marginYRaw = val(p, "margin_top", "8");
  const width = val(p, "width", "full");

  const styleClass = style === "dashed" ? "border-dashed" : style === "dotted" ? "border-dotted" : "border-solid";
  const widthClass = width === "full" ? "w-full" : width === "narrow" ? "w-1/3" : "w-2/3";
  const pyClass: Record<string, string> = { "4": "py-4", "6": "py-6", "8": "py-8", "12": "py-12", "16": "py-16" };
  const marginY = pyClass[marginYRaw] ?? "py-8";

  return (
    <section className={`${marginY} px-3 md:px-6 lg:px-8 xl:px-12`}>
      <hr className={`${styleClass} border-t-2 mx-auto ${widthClass}`} style={{ borderColor: "var(--site-outline-variant)" }} />
    </section>
  );
}

// ─── Social Links ──────────────────────────────────────────────────────────────

export function SocialLinksSection({ section }: { section: CmsSection<"social_links"> }) {
  const props: SocialLinksProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Síguenos");
  const links = asItems(p).filter(Boolean);
  const layout = val(p, "layout", "row");
  const showLabels = p.show_labels !== false;
  const iconSize = parseInt(val(p, "icon_size", "24"));

  const platformIcons: Record<string, React.ReactNode> = {
    facebook: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M18 2h-3a5 5 0 00-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 011-1h3z" /></svg>,
    instagram: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="5" /><circle cx="12" cy="12" r="5" /><circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" /></svg>,
    youtube: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M22.54 6.42a2.78 2.78 0 00-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 00-1.94 2A29 29 0 001 11.75a29 29 0 00.46 5.33A2.78 2.78 0 003.4 19.1c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 001.94-2 29 29 0 00.46-5.25 29 29 0 00-.46-5.43z" /><polygon points="9.75 15.02 15.5 11.75 9.75 8.48 9.75 15.02" fill="white" /></svg>,
    tiktok: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1v-3.5a6.37 6.37 0 00-.79-.05A6.34 6.34 0 003.15 15.2a6.34 6.34 0 0010.86 4.46V13a8.28 8.28 0 005.58 2.15V11.7a4.83 4.83 0 01-3.77-1.78V6.69h3.77z" /></svg>,
    whatsapp: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z" /><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2z" fill="none" stroke="currentColor" strokeWidth="1.5" /></svg>,
    twitter: <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>,
  };

  const containerClass = layout === "row" ? "flex flex-wrap gap-6 md:gap-8" : layout === "grid" ? "grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8" : "space-y-3";

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      <div className={containerClass}>
        {links.map((link, i) => {
          const platform = val(link, "platform", "").toLowerCase();
          const url = val(link, "url", "#");
          const label = val(link, "label", platform);
          return (
            <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-3 rounded-lg border transition-all hover:scale-105" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }}>
              <span style={{ color: "var(--site-primary)" }}>{platformIcons[platform] || <Star size={iconSize} />}</span>
              {showLabels && <span className="text-sm font-medium">{label}</span>}
            </a>
          );
        })}
      </div>
    </section>
  );
}

// ─── Spacer ────────────────────────────────────────────────────────────────────

export function SpacerSection({ section }: { section: CmsSection<"spacer"> }) {
  const props: SpacerProps = section.props_json ?? {};
  const p = asProps(props);
  const height = parseInt(val(p, "height", "32"));
  return <div style={{ height: `${height}px` }} />;
}

// ─── Calendar ──────────────────────────────────────────────────────────────────

export function CalendarSection({ section }: { section: CmsSection<"calendar"> }) {
  const props: CalendarProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Próximos Eventos");
  const items = asItems(p).filter(Boolean);
  const shouldShowTime = p.show_time !== false;
  const shouldShowLocation = p.show_location !== false;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-6" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      <div className="space-y-3">
        {items.length === 0 && <p className="text-sm opacity-60" style={{ color: "var(--site-on-surface-variant)" }}>No hay eventos configurados.</p>}
        {items.map((item, i) => (
          <div key={i} className="flex items-start gap-4 p-4 rounded-lg border" style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}>
            <div className="w-12 h-12 rounded-lg flex flex-col items-center justify-center shrink-0" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
              <Calendar size={18} />
            </div>
            <div className="flex-1">
              <p className="font-bold" style={{ color: "var(--site-on-surface)" }}>{val(item, "title", "Evento")}</p>
              <div className="flex flex-wrap gap-3 text-xs mt-1" style={{ color: "var(--site-on-surface-variant)" }}>
                {shouldShowTime && val(item, "date") && <span>{val(item, "date")}{val(item, "time") ? ` · ${val(item, "time")}` : ""}</span>}
                {shouldShowLocation && val(item, "location") && <span>{val(item, "location")}</span>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ─── Map ───────────────────────────────────────────────────────────────────────

export function MapSection({ section }: { section: CmsSection<"map"> }) {
  const props: MapProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Encuéntranos");
  const embedUrl = val(p, "embed_url", "");
  const address = val(p, "address", "");
  const height = parseInt(val(p, "height", "400"));
  const showDirections = p.show_directions_link !== false;

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <h3 className="text-lg font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
      {embedUrl ? (
        <div className="rounded-lg overflow-hidden border" style={{ borderColor: "var(--site-outline-variant)" }}>
          <iframe src={embedUrl} width="100%" height={height} style={{ border: 0 }} allowFullScreen loading="lazy" />
        </div>
      ) : (
        <div className="rounded-lg border p-8 text-center" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", height: `${height}px` }}>
          <MapPin size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--site-primary)" }} />
          <p className="text-lg font-medium mb-2" style={{ color: "var(--site-on-surface)" }}>{address || "Sin dirección configurada"}</p>
          {showDirections && address && (
            <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold" style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
              <MapPin size={16} /> Ver en Google Maps
            </a>
          )}
        </div>
      )}
    </section>
  );
}
