"use client";

import { CmsSection } from "@/types/cms-v2";
import type {
  CountdownProps,
  PricingProps,
  TimelineProps,
  IconGridProps,
} from "@/types/cms-section-props";
import Link from "next/link";
import { useEffect, useState } from "react";
import { asItems, asProps, val } from "./shared";

export function CountdownSection({ section }: { section: CmsSection<"countdown"> }) {
  const props: CountdownProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Próximo Evento");
  const targetDate = val(p, "target_date", "");
  const body = val(p, "body", "");

  const [timeLeft, setTimeLeft] = useState({ d: 0, h: 0, m: 0, s: 0, expired: false });

  useEffect(() => {
    if (!targetDate) return;
    const target = new Date(targetDate).getTime();

    const tick = () => {
      const now = Date.now();
      const diff = target - now;
      if (diff <= 0) {
        setTimeLeft({ d: 0, h: 0, m: 0, s: 0, expired: true });
        return;
      }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setTimeLeft({ d, h, m, s, expired: false });
    };

    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [targetDate]);

  const units = [
    { label: "DÍAS", value: timeLeft.d },
    { label: "HORAS", value: timeLeft.h },
    { label: "MIN", value: timeLeft.m },
    { label: "SEG", value: timeLeft.s },
  ];

  return (
    <section
      className="ccf-section-panel p-8 md:p-14 lg:p-16 text-center"
      style={{ background: "var(--site-cta-gradient)" }}
    >
      <h2 className="text-2xl md:text-3xl font-black text-white">{title}</h2>
      {body && <p className="mt-3 text-white/80 text-base">{body}</p>}
      {timeLeft.expired ? (
        <p className="mt-8 text-white text-xl font-bold">¡El evento ya comenzó!</p>
      ) : (
        <div className="mt-8 flex justify-center gap-3 md:gap-6">
          {units.map((unit) => (
            <div key={unit.label} className="flex flex-col items-center gap-2">
              <div
                className="size-16 md:size-20 rounded-xl flex items-center justify-center text-2xl md:text-3xl font-black text-white"
                style={{ background: "rgba(255,255,255,0.15)", backdropFilter: "blur(8px)" }}
              >
                {String(unit.value).padStart(2, "0")}
              </div>
              <span className="text-2xs font-bold uppercase tracking-widest text-white/70">{unit.label}</span>
            </div>
          ))}
        </div>
      )}
      {targetDate && !timeLeft.expired && (
        <p className="mt-6 text-white/60 text-xs">
          {new Date(targetDate).toLocaleDateString("es", { weekday: "long", year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" })}
        </p>
      )}
    </section>
  );
}

// ─── Pricing ───────────────────────────────────────────────────────────────────

export function PricingSection({ section }: { section: CmsSection<"pricing"> }) {
  const props: PricingProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Opciones");
  const items = asItems(p).slice(0, 4) as Array<{ name?: string; price?: string; features?: string; btn?: string; btn_href?: string; featured?: boolean | string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <h2 className="text-2xl md:text-3xl font-black tracking-tight text-center mb-10 md:mb-12" style={{ color: "var(--site-on-surface)" }}>
          {title}
        </h2>
      )}
      <div className={`grid grid-cols-1 gap-4 ${items.length >= 3 ? "md:grid-cols-3" : "md:grid-cols-2 max-w-2xl mx-auto"}`}>
        {items.map((item, i) => {
          const featured = item.featured === true || item.featured === "true" || item.featured === "1";
          return (
            <article
              key={i}
              className={`rounded-xl p-6 flex flex-col gap-4 relative ${featured ? "shadow-xl scale-[1.02]" : ""}`}
              style={{
                background: featured ? "var(--site-primary)" : "var(--site-surface-container)",
                border: featured ? "none" : "1px solid transparent",
              }}
            >
              {featured && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full px-4 py-1 text-2xs font-black uppercase tracking-widest bg-[hsl(var(--bg-primary))]" style={{ color: "var(--site-primary)" }}>
                  Recomendado
                </span>
              )}
              <div>
                <h3 className="text-lg font-black" style={{ color: featured ? "white" : "var(--site-on-surface)" }}>
                  {item.name || `Plan ${i + 1}`}
                </h3>
                <p className="text-3xl font-black mt-1" style={{ color: featured ? "white" : "var(--site-primary)" }}>
                  {item.price || "—"}
                </p>
              </div>
              <ul className="space-y-2 flex-1">
                {(item.features || "").split("\n").filter(Boolean).map((feat, fi) => (
                  <li key={fi} className="flex items-start gap-2 text-sm" style={{ color: featured ? "rgba(255,255,255,0.85)" : "var(--site-on-surface-variant)" }}>
                    <span className="mt-0.5 flex-shrink-0 font-black" style={{ color: featured ? "white" : "var(--site-primary)" }}>✓</span>
                    {feat}
                  </li>
                ))}
              </ul>
              {item.btn && (
                item.btn_href ? (
                  <Link
                    href={item.btn_href}
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest text-center block transition-opacity hover:opacity-90"
                    style={{ background: featured ? "var(--site-on-primary)" : "var(--site-primary)", color: featured ? "var(--site-primary)" : "var(--site-on-primary)" }}
                  >
                    {item.btn}
                  </Link>
                ) : (
                  <button
                    className="w-full py-3 rounded-full text-sm font-black uppercase tracking-widest transition-opacity hover:opacity-90"
                    style={{ background: featured ? "var(--site-on-primary)" : "var(--site-primary)", color: featured ? "var(--site-primary)" : "var(--site-on-primary)" }}
                  >
                    {item.btn}
                  </button>
                )
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}

// ─── Timeline ──────────────────────────────────────────────────────────────────

export function TimelineSection({ section }: { section: CmsSection<"timeline"> }) {
  const props: TimelineProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const items = asItems(p) as Array<{ year?: string; title?: string; body?: string }>;
  const fullBleed = Boolean(p.full_bleed);

  return (
    <section className={`ccf-section-panel p-7 md:p-12 lg:p-16 ${fullBleed ? "relative left-1/2 w-screen -translate-x-1/2 rounded-none" : ""}`} style={{ background: "var(--site-surface-container-low)" }}>
      {title && (
        <div className="mx-auto mb-12 max-w-2xl text-center md:mb-16">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.24em]" style={{ color: "var(--site-primary)" }}>Nuestra historia</p>
          <h2 className="text-3xl font-black tracking-tight md:text-5xl" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
        </div>
      )}
      <div className="relative mx-auto max-w-5xl">
        <div className="absolute bottom-0 left-5 top-0 w-px md:left-1/2" style={{ background: "color-mix(in srgb, var(--site-primary) 28%, transparent)" }} />
        <div className="space-y-10 md:space-y-14">
          {items.map((item, i) => (
            <div key={i} className="relative pl-16 md:grid md:grid-cols-2 md:gap-16 md:pl-0">
              <article className={`rounded-2xl border p-6 shadow-sm md:p-8 ${i % 2 === 1 ? "md:col-start-2" : ""}`} style={{ background: "var(--site-surface-container)", borderColor: "color-mix(in srgb, var(--site-outline-variant) 58%, transparent)" }}>
                <div className="mb-4 flex items-center gap-3">
                  <span className="text-sm font-black uppercase tracking-[0.16em]" style={{ color: "var(--site-primary)" }}>{item.year || String(i + 1)}</span>
                  <span className="h-px w-8" style={{ background: "var(--site-primary)", opacity: 0.35 }} />
                </div>
                {item.title && <h3 className="text-xl font-black leading-tight md:text-2xl" style={{ color: "var(--site-on-surface)" }}>{item.title}</h3>}
                {item.body && <p className="mt-4 max-w-prose text-base leading-8" style={{ color: "var(--site-on-surface-variant)" }}>{item.body}</p>}
              </article>
              <div className="absolute left-0 top-6 flex size-10 items-center justify-center rounded-full border-4 text-[10px] font-black text-white shadow-lg md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2" style={{ background: "var(--site-cta-gradient)", borderColor: "var(--site-surface-container-low)" }} aria-hidden="true">
                <span className="size-2 rounded-full bg-white" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── Icon Grid ─────────────────────────────────────────────────────────────────

export function IconGridSection({ section }: { section: CmsSection<"icon_grid"> }) {
  const props: IconGridProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const items = asItems(p).slice(0, 12) as Array<{ icon?: string; title?: string; body?: string }>;

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {(title || body) && (
        <div className="mb-8 text-center">
          {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
          {body && <p className="mt-3 text-base max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-6 md:gap-8">
        {items.map((item, i) => (
          <div key={i} className="rounded-xl p-5 flex flex-col items-center text-center gap-3" style={{ background: "var(--site-surface-container)" }}>
            {item.icon && <span className="text-4xl">{item.icon}</span>}
            <h3 className="font-black text-sm" style={{ color: "var(--site-on-surface)" }}>{item.title || `Item ${i + 1}`}</h3>
            {item.body && <p className="text-xs leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>{item.body}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}
