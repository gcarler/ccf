"use client";

import { CmsSection } from "@/types/cms-v2";
import type { ContactFormProps, PrayerFormProps } from "@/types/cms-section-props";
import { useState } from "react";
import { asProps, val } from "./shared";

export function ContactFormSection({ section }: { section: CmsSection<"contact_form"> }) {
  const props: ContactFormProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Hablemos de Tu Caminar");
  const subtitle = val(p, "subtitle", "");
  const [sent, setSent] = useState(false);

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      {sent ? (
        <p className="mt-6 font-bold" style={{ color: "var(--site-on-surface)" }}>{val(p, "success_message", "Gracias. Te contactaremos pronto.")}</p>
      ) : (
        <form
          onSubmit={(e) => { e.preventDefault(); setSent(true); }}
          className="mt-6 space-y-4 max-w-xl"
        >
          <input required type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          <input required type="tel" placeholder={val(p, "phone_placeholder", "+57 300...")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          <textarea required rows={4} placeholder={val(p, "message_placeholder", "Cuéntanos un poco sobre ti...")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          <button type="submit" className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
            {val(p, "submit_label", "Enviar mensaje y conectar")}
          </button>
        </form>
      )}
    </section>
  );
}

// ─── Prayer Form ───────────────────────────────────────────────────────────────

export function PrayerFormSection({ section }: { section: CmsSection<"prayer_form"> }) {
  const props: PrayerFormProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Pedir oración");
  const subtitle = val(p, "subtitle", "");
  const [sent, setSent] = useState(false);

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      {sent ? (
        <p className="mt-6 font-bold" style={{ color: "var(--site-on-surface)" }}>{val(p, "success_message", "Tu petición ha sido enviada.")}</p>
      ) : (
        <form onSubmit={(e) => { e.preventDefault(); setSent(true); }} className="mt-6 space-y-4 max-w-xl">
          <input required type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          <textarea required rows={4} placeholder={val(p, "request_placeholder", "Comparte tu necesidad...")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          <button type="submit" className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white" style={{ background: "var(--site-cta-gradient)" }}>
            {val(p, "submit_label", "Enviar al equipo pastoral")}
          </button>
        </form>
      )}
    </section>
  );
}

// ─── Course Grid (config-only shell; data comes from academy API) ──────────────
