"use client";

import React from "react";
import Link from "next/link";
import { CmsSection } from "@/types/cms-v2";

function val(props: Record<string, unknown>, key: string, fallback = "") {
  const value = props?.[key];
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

export default function PublicSectionRenderer({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Sin título");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "Explorar");
  const ctaHref = val(props, "cta_href", "/faro");

  if (section.type === "hero") {
    return (
      <section className="rounded-3xl p-10 md:p-16" style={{ background: "var(--faro-surface-container)" }}>
        <p className="text-[10px] font-black uppercase tracking-[0.35em]" style={{ color: "var(--faro-primary)" }}>Hero</p>
        <h1 className="mt-3 text-4xl md:text-6xl font-black tracking-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h1>
        <p className="mt-4 text-base md:text-lg max-w-3xl" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>
        <Link href={ctaHref} className="inline-flex mt-8 rounded-full px-6 py-3 text-xs font-black uppercase tracking-widest text-white" style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}>
          {ctaLabel}
        </Link>
      </section>
    );
  }

  if (section.type === "cta_banner") {
    return (
      <section className="rounded-3xl p-10" style={{ background: "var(--faro-primary-container)" }}>
        <h2 className="text-3xl font-black" style={{ color: "var(--faro-on-primary-container)" }}>{title}</h2>
        <p className="mt-3 max-w-2xl" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>
        <Link href={ctaHref} className="inline-flex mt-6 rounded-full px-5 py-2.5 text-[11px] font-black uppercase tracking-widest" style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}>
          {ctaLabel}
        </Link>
      </section>
    );
  }

  if (section.type === "cards") {
    const cardsRaw = Array.isArray(props.items) ? props.items : [
      { title: val(props, "card_1_title", "Conecta"), body: val(props, "card_1_body", "Únete a una comunidad de fe.") },
      { title: val(props, "card_2_title", "Crece"), body: val(props, "card_2_body", "Discipulado y formación práctica.") },
      { title: val(props, "card_3_title", "Sirve"), body: val(props, "card_3_body", "Impacta tu ciudad con propósito.") },
    ];
    const cards = cardsRaw.filter(Boolean).slice(0, 6) as Array<{ title?: string; body?: string }>;
    return (
      <section className="rounded-3xl p-8 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-3xl font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        {body && <p className="mt-3 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          {cards.map((card, index) => (
            <article key={index} className="rounded-2xl p-5" style={{ background: "var(--faro-surface-container)" }}>
              <h4 className="text-lg font-black" style={{ color: "var(--faro-on-surface)" }}>{card.title || `Tarjeta ${index + 1}`}</h4>
              <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{card.body || "Descripción"}</p>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "faq") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [
      { q: val(props, "q1", "¿Dónde están ubicados?"), a: val(props, "a1", "Estamos en múltiples sedes. Revisa la sección de sedes.") },
      { q: val(props, "q2", "¿Cómo me conecto?"), a: val(props, "a2", "Puedes visitarnos, escribirnos o unirte a un grupo pequeño.") },
    ];
    const items = itemsRaw.slice(0, 8) as Array<{ q?: string; a?: string }>;
    return (
      <section className="rounded-3xl p-8 md:p-10" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-3xl font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        <div className="mt-5 space-y-3">
          {items.map((item, index) => (
            <details key={index} className="rounded-2xl p-4" style={{ background: "var(--faro-surface-container)" }}>
              <summary className="cursor-pointer font-black" style={{ color: "var(--faro-on-surface)" }}>{item.q || `Pregunta ${index + 1}`}</summary>
              <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{item.a || "Respuesta pendiente"}</p>
            </details>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "gallery") {
    const imageUrl = val(props, "image_url", "https://images.unsplash.com/photo-1517457373958-b7bdd4587205?w=1200&q=80");
    return (
      <section className="rounded-3xl overflow-hidden" style={{ background: "var(--faro-surface-container-low)" }}>
        <div className="w-full h-[320px] bg-cover bg-center" style={{ backgroundImage: `url('${imageUrl}')` }} aria-label={title || "Gallery image"} />
        <div className="p-6">
          <h3 className="text-2xl font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
          {body && <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        </div>
      </section>
    );
  }

  if (section.type === "embed") {
    const embed = val(props, "embed_url", "");
    return (
      <section className="rounded-3xl p-8" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-2xl font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        {body && <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        {embed ? (
          <div className="mt-4 aspect-video rounded-2xl overflow-hidden" style={{ background: "var(--faro-surface-container)" }}>
            <iframe title={title} src={embed} className="w-full h-full border-0" allowFullScreen />
          </div>
        ) : (
          <p className="mt-4 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>Define `embed_url` para mostrar el contenido embebido.</p>
        )}
      </section>
    );
  }

  return (
    <section className="rounded-3xl p-8" style={{ background: "var(--faro-surface-container-low)" }}>
      <h3 className="text-2xl font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
      {body && <p className="mt-3 leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
      {ctaHref && <Link href={ctaHref} className="inline-flex mt-5 text-sm font-black uppercase tracking-widest" style={{ color: "var(--faro-primary)" }}>{ctaLabel}</Link>}
    </section>
  );
}
