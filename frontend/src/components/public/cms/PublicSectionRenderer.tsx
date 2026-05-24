"use client";

import React from "react";
import Link from "next/link";
import { CmsSection } from "@/types/cms-v2";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useState, useEffect } from "react";

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
  const ctaHref = val(props, "cta_href", "/");
  const imageUrl = val(props, "image_url", "");
  const imageAlt = val(props, "image_alt", title || "Imagen");


  if (section.type === "popup_banner") {
    return <PopupBlock section={section} />;
  }
  if (section.type === "hero") {
    if (imageUrl) {
      return (
        <section className="relative overflow-hidden rounded-lg min-h-[460px] flex items-end p-4 md:p-4">
          <img src={imageUrl} alt={imageAlt} className="absolute inset-0 h-full w-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/35 to-black/10" />
          <div className="relative z-10 max-w-4xl">
            <p className="text-[10px] font-bold uppercase tracking-wide text-white/75">Hero</p>
            <h1 className="mt-3 text-lg md:text-xl font-bold tracking-tight text-white">{title}</h1>
            <p className="mt-4 text-base md:text-lg max-w-3xl text-white/90">{body}</p>
            <Link href={ctaHref} className="inline-flex mt-3 rounded-full px-3 py-3 text-xs font-bold uppercase tracking-wide text-slate-950 bg-white hover:bg-slate-100 transition-colors">
              {ctaLabel}
            </Link>
          </div>
        </section>
      );
    }
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container)" }}>
        <p className="text-[10px] font-bold uppercase tracking-wide" style={{ color: "var(--faro-primary)" }}>Hero</p>
        <h1 className="mt-3 text-lg md:text-xl font-bold tracking-tight" style={{ color: "var(--faro-on-surface)" }}>{title}</h1>
        <p className="mt-4 text-base md:text-lg max-w-3xl" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>
        <Link href={ctaHref} className="inline-flex mt-3 rounded-full px-3 py-3 text-xs font-bold uppercase tracking-wide text-white" style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}>
          {ctaLabel}
        </Link>
      </section>
    );
  }

  if (section.type === "cta_banner") {
    return (
      <section className="rounded-lg p-4" style={{ background: "var(--faro-primary-container)" }}>
        <h2 className="text-xl font-bold" style={{ color: "var(--faro-on-primary-container)" }}>{title}</h2>
        <p className="mt-3 max-w-2xl" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>
        <Link href={ctaHref} className="inline-flex mt-3 rounded-full px-3 py-2.5 text-[11px] font-bold uppercase tracking-wide" style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}>
          {ctaLabel}
        </Link>
      </section>
    );
  }

  if (section.type === "cards") {
    const cardsRaw = Array.isArray(props.items) ? props.items : [];
    const cards = cardsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 6) as Array<{ title?: string; body?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        {body && <p className="mt-3 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-4">
          {cards.map((card, index) => (
            <article key={index} className="rounded-lg p-4" style={{ background: "var(--faro-surface-container)" }}>
              <h4 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{card.title || `Tarjeta ${index + 1}`}</h4>
              <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{card.body || "Descripción"}</p>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "faq") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [];
    const items = itemsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 8) as Array<{ q?: string; a?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        <div className="mt-5 space-y-3">
          {items.map((item, index) => (
            <details key={index} className="rounded-lg p-4" style={{ background: "var(--faro-surface-container)" }}>
              <summary className="cursor-pointer font-bold" style={{ color: "var(--faro-on-surface)" }}>{item.q || `Pregunta ${index + 1}`}</summary>
              <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{item.a || "Respuesta pendiente"}</p>
            </details>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "gallery") {
    return (
      <section className="rounded-lg overflow-hidden" style={{ background: "var(--faro-surface-container-low)" }}>
        {imageUrl && <img src={imageUrl} alt={imageAlt || "Gallery image"} className="w-full h-[320px] object-cover" />}
        <div className="p-4">
          <h3 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
          {body && <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        </div>
      </section>
    );
  }

  if (section.type === "embed") {
    const embed = val(props, "embed_url", "");
    return (
      <section className="rounded-lg p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        {body && <p className="mt-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
        {embed ? (
          <div className="mt-4 aspect-video rounded-lg overflow-hidden" style={{ background: "var(--faro-surface-container)" }}>
            <iframe title={title} src={embed} className="w-full h-full border-0" allowFullScreen />
          </div>
        ) : (
          <p className="mt-4 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>Define `embed_url` para mostrar el contenido embebido.</p>
        )}
      </section>
    );
  }

  if (section.type === "video_hero") {
    const videoUrl = val(props, "video_url", "");
    return (
      <section className="relative rounded-lg overflow-hidden min-h-48 flex items-center p-4 md:p-4">
        {videoUrl && (
          <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover">
            <source src={videoUrl} type="video/mp4" />
          </video>
        )}
        <div className="absolute inset-0 bg-black/50" />
        <div className="relative z-10 w-full max-w-4xl">
          <p className="text-[10px] font-bold uppercase tracking-wide text-white/70">Video Hero</p>
          <h1 className="mt-3 text-lg md:text-xl font-bold tracking-tight text-white">{title}</h1>
          <p className="mt-4 text-base md:text-lg text-white/90 max-w-3xl">{body}</p>
          {ctaHref && <Link href={ctaHref} className="inline-flex mt-3 rounded-full px-3 py-3 text-xs font-bold uppercase tracking-wide text-slate-900 bg-white hover:bg-slate-100 transition-colors">
            {ctaLabel}
          </Link>}
        </div>
      </section>
    );
  }

  if (section.type === "rich_text_columns") {
    const body2 = val(props, "body_2", "");
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
          <div className="leading-relaxed whitespace-pre-line" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</div>
          <div className="leading-relaxed whitespace-pre-line" style={{ color: "var(--faro-on-surface-variant)" }}>{body2 || body}</div>
        </div>
      </section>
    );
  }

  if (section.type === "testimonials") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [];
    const items = itemsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 4) as Array<{ author?: string; role?: string; content?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold text-center mb-3" style={{ color: "var(--faro-on-surface)" }}>{title || "Testimonios"}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((item, index) => (
            <article key={index} className="rounded-lg p-4" style={{ background: "var(--faro-surface-container)" }}>
              <p className="text-lg italic mb-3" style={{ color: "var(--faro-on-surface)" }}>&quot;{item.content}&quot;</p>
              <div className="flex items-center gap-3">
                <div className="size-10 rounded-full flex items-center justify-center font-bold text-white" style={{ background: "var(--faro-primary)" }}>
                  {(item.author || "A")[0]}
                </div>
                <div>
                  <p className="font-bold text-sm" style={{ color: "var(--faro-on-surface)" }}>{item.author}</p>
                  <p className="text-xs" style={{ color: "var(--faro-on-surface-variant)" }}>{item.role}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "stats") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [];
    const items = itemsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 4) as Array<{ value?: string; label?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4 text-center" style={{ background: "var(--faro-primary-container)" }}>
        <h3 className="text-xl font-bold mb-3" style={{ color: "var(--faro-on-primary-container)" }}>{title}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {items.map((item, index) => (
            <div key={index}>
              <p className="text-lg md:text-xl font-bold mb-2" style={{ color: "var(--faro-primary)" }}>{item.value}</p>
              <p className="text-sm font-bold uppercase tracking-wide" style={{ color: "var(--faro-on-primary-container)" }}>{item.label}</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "team") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [];
    const items = itemsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 8) as Array<{ name?: string; role?: string; image?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold text-center mb-3" style={{ color: "var(--faro-on-surface)" }}>{title || "Nuestro Equipo"}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
          {items.map((item, index) => (
            <div key={index} className="flex flex-col items-center">
              <div className="size-10 md:size-10 rounded-full mb-4 bg-cover bg-center" style={{ backgroundImage: item.image ? `url('${item.image}')` : undefined, background: item.image ? undefined : "var(--faro-surface-container-high)" }} />
              <p className="font-bold text-lg" style={{ color: "var(--faro-on-surface)" }}>{item.name}</p>
              <p className="text-sm mt-1" style={{ color: "var(--faro-primary)" }}>{item.role}</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (section.type === "countdown") {
    const targetDate = val(props, "target_date", "");
    return (
      <section className="rounded-lg p-4 text-center" style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}>
        <h3 className="text-xl font-bold text-white mb-3">{title || "Próximo Evento"}</h3>
        <div className="flex justify-center gap-3 md:gap-4">
          {["DÍAS", "HORAS", "MIN", "SEG"].map((unit) => (
            <div key={unit} className="flex flex-col items-center">
              <div className="size-8 md:size-10 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center mb-2">
                <span className="text-lg md:text-xl font-bold text-white">00</span>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wide text-white/80">{unit}</span>
            </div>
          ))}
        </div>
        {targetDate && <p className="mt-3 text-white/80 text-sm font-medium">Cuenta regresiva hasta: {new Date(targetDate).toLocaleDateString()}</p>}
      </section>
    );
  }

  if (section.type === "pricing") {
    const itemsRaw = Array.isArray(props.items) ? props.items : [];
    const items = itemsRaw
      .filter((item) => Boolean(item) && (item as { status?: string }).status !== "archived")
      .slice(0, 3) as Array<{ name?: string; price?: string; features?: string; btn?: string; status?: string }>;
    return (
      <section className="rounded-lg p-4 md:p-4" style={{ background: "var(--faro-surface-container-low)" }}>
        <h3 className="text-xl font-bold text-center mb-3" style={{ color: "var(--faro-on-surface)" }}>{title || "Opciones de Donación"}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map((item, index) => (
            <article key={index} className="rounded-lg p-4 md:p-4 flex flex-col" style={{ background: "var(--faro-surface-container)", border: index === 1 ? "2px solid var(--faro-primary)" : "none" }}>
              <h4 className="text-xl font-bold mb-2" style={{ color: "var(--faro-on-surface)" }}>{item.name}</h4>
              <p className="text-lg md:text-xl font-bold mb-3" style={{ color: "var(--faro-on-surface)" }}>{item.price}</p>
              <ul className="space-y-3 mb-3 flex-1">
                {(item.features || "").split("\n").map((feat, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                    <span style={{ color: "var(--faro-primary)" }}>✓</span> {feat}
                  </li>
                ))}
              </ul>
              <button className="w-full py-1.5 rounded-md font-bold uppercase tracking-wide text-xs transition-opacity hover:opacity-90" style={{ background: index === 1 ? "var(--faro-primary)" : "var(--faro-surface-container-highest)", color: index === 1 ? "var(--faro-on-primary)" : "var(--faro-on-surface)" }}>
                {item.btn || "Seleccionar"}
              </button>
            </article>
          ))}
        </div>
      </section>
    );
  }

  // Fallback (rich_text and default)
  return (
    <section className="rounded-lg p-4" style={{ background: "var(--faro-surface-container-low)" }}>
      <h3 className="text-lg font-bold" style={{ color: "var(--faro-on-surface)" }}>{title}</h3>
      {body && <p className="mt-3 leading-relaxed whitespace-pre-line" style={{ color: "var(--faro-on-surface-variant)" }}>{body}</p>}
      {ctaHref && <Link href={ctaHref} className="inline-flex mt-5 text-sm font-bold uppercase tracking-wide" style={{ color: "var(--faro-primary)" }}>{ctaLabel}</Link>}
    </section>
  );
}

function PopupBlock({ section }: { section: CmsSection }) {
  const props = section.props_json || {};
  const title = val(props, "title", "Aviso Importante");
  const body = val(props, "body", "");
  const ctaLabel = val(props, "cta_label", "Ver Más");
  const ctaHref = val(props, "cta_href", "/");
  const delayMs = parseInt(val(props, "delay_ms", "2000"), 10) || 2000;
  
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Logic to show popup once per session using sessionStorage
    const popupId = `faro_popup_${section.id}`;
    if (!sessionStorage.getItem(popupId)) {
      const timer = setTimeout(() => {
        setIsVisible(true);
      }, delayMs);
      return () => clearTimeout(timer);
    }
  }, [section.id, delayMs]);

  const handleClose = () => {
    setIsVisible(false);
    sessionStorage.setItem(`faro_popup_${section.id}`, "closed");
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-md bg-faro-surface-container rounded-lg p-4 shadow-2xl border border-faro-outline-variant/20"
            style={{
              background: "var(--faro-surface-container)",
              color: "var(--faro-on-surface)",
            }}
          >
            <button
              onClick={handleClose}
              className="absolute top-4 right-4 p-2 rounded-full hover:bg-faro-surface-container-high transition-colors"
            >
              <X size={20} />
            </button>

            <div className="text-center mt-2">
              <h2 className="text-lg font-bold mb-3">{title}</h2>
              <p className="text-sm mb-3" style={{ color: "var(--faro-on-surface-variant)" }}>
                {body}
              </p>

              <div className="flex flex-col gap-3">
                <Link
                  href={ctaHref}
                  onClick={handleClose}
                  className="w-full py-1.5 rounded-full text-xs font-bold uppercase tracking-wide text-white transition-transform hover:scale-[1.02]"
                  style={{ background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))" }}
                >
                  {ctaLabel}
                </Link>
                <button
                  onClick={handleClose}
                  className="w-full py-3 rounded-full text-xs font-bold uppercase tracking-wide hover:bg-faro-surface-container-high transition-colors"
                  style={{ color: "var(--faro-on-surface-variant)" }}
                >
                  No, gracias
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
