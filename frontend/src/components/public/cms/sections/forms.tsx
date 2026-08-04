"use client";

import { CmsSection } from "@/types/cms-v2";
import type { ContactFormProps, PrayerFormProps } from "@/types/cms-section-props";
import { useState } from "react";
import { apiFetch, extractErrorMessage } from "@/lib/http";
import { asProps, val } from "./shared";

export function ContactFormSection({ section }: { section: CmsSection<"contact_form"> }) {
  const props: ContactFormProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Hablemos de Tu Caminar");
  const subtitle = val(p, "subtitle", "");
  const actionUrl = val(p, "action_url", "/public/contact");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    // Honeypot: bots that fill this field are treated as successful but never
    // reach the CRM. The field is intentionally invisible to normal users.
    if (String(form.get("website") || "").trim()) {
      setStatus("success");
      return;
    }

    const fullName = String(form.get("full_name") || "").trim();
    const email = String(form.get("email") || "").trim();
    const phone = String(form.get("phone") || "").trim();
    const notes = String(form.get("notes") || "").trim();
    if (fullName.length < 2 || notes.length < 2) return;

    setStatus("submitting");
    setError(null);
    try {
      // CMS action_url is constrained to an internal relative endpoint. This
      // prevents an editor typo/config value from turning the public form into
      // an arbitrary third-party data exfiltration surface.
      const endpoint = ["/public/contact"].includes(actionUrl) ? actionUrl : "/public/contact";
      await apiFetch(endpoint, {
        method: "POST",
        body: {
          full_name: fullName,
          email: email || undefined,
          phone: phone || undefined,
          notes: notes || undefined,
          source: "cms-contact",
        },
        silent: true,
      });
      setStatus("success");
      formElement.reset();
    } catch (submissionError) {
      setStatus("error");
      setError(extractErrorMessage(submissionError, "No se pudo enviar el mensaje."));
    }
  };

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      {status === "success" ? (
        <p className="mt-6 font-bold" role="status" aria-live="polite" style={{ color: "var(--site-on-surface)" }}>{val(p, "success_message", "Gracias. Te contactaremos pronto.")}</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4 max-w-xl">
          <div>
            <label htmlFor="cms-contact-full-name" className="sr-only">{val(p, "name_label", "Nombre completo")}</label>
            <input id="cms-contact-full-name" name="full_name" required minLength={2} maxLength={160} type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} autoComplete="name" className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <div>
            <label htmlFor="cms-contact-email" className="sr-only">Correo electrónico</label>
            <input id="cms-contact-email" name="email" type="email" maxLength={255} placeholder="tu@email.com (opcional)" autoComplete="email" className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <div>
            <label htmlFor="cms-contact-phone" className="sr-only">{val(p, "phone_label", "WhatsApp")}</label>
            <input id="cms-contact-phone" name="phone" type="tel" maxLength={40} placeholder={val(p, "phone_placeholder", "+57 300...")} autoComplete="tel" className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <div>
            <label htmlFor="cms-contact-notes" className="sr-only">{val(p, "message_label", "¿En qué podemos ayudarte?")}</label>
            <textarea id="cms-contact-notes" name="notes" required minLength={2} maxLength={5000} rows={4} placeholder={val(p, "message_placeholder", "Cuéntanos un poco sobre ti...")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
          {status === "error" && <p role="alert" aria-live="assertive" className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>}
          <button type="submit" disabled={status === "submitting"} className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white disabled:opacity-60" style={{ background: "var(--site-cta-gradient)" }}>
            {status === "submitting" ? "Enviando..." : val(p, "submit_label", "Enviar mensaje y conectar")}
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
  const actionUrl = val(p, "action_url", "/crm/prayer-requests/public");
  const category = val(p, "category", "General");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    if (String(form.get("website") || "").trim()) {
      setStatus("success");
      return;
    }

    const requesterName = String(form.get("requester_name") || "").trim();
    const requestText = String(form.get("request_text") || "").trim();
    if (requesterName.length < 2 || requestText.length < 2) return;

    setStatus("submitting");
    setError(null);
    try {
      const endpoint = ["/crm/prayer-requests/public"].includes(actionUrl)
        ? actionUrl
        : "/crm/prayer-requests/public";
      await apiFetch(endpoint, {
        method: "POST",
        body: {
          requester_name: requesterName,
          request_text: requestText,
          category,
        },
        silent: true,
      });
      setStatus("success");
      formElement.reset();
    } catch (submissionError) {
      setStatus("error");
      setError(extractErrorMessage(submissionError, "No se pudo enviar la petición."));
    }
  };

  return (
    <section className="ccf-section-panel p-7 md:p-12 lg:p-14" style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      {status === "success" ? (
        <p className="mt-6 font-bold" role="status" aria-live="polite" style={{ color: "var(--site-on-surface)" }}>{val(p, "success_message", "Tu petición ha sido enviada.")}</p>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6 space-y-4 max-w-xl">
          <div>
            <label htmlFor="cms-prayer-name" className="sr-only">{val(p, "name_label", "Nombre")}</label>
            <input id="cms-prayer-name" name="requester_name" required minLength={2} maxLength={160} type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} autoComplete="name" className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <div>
            <label htmlFor="cms-prayer-request" className="sr-only">{val(p, "request_label", "Petición de oración")}</label>
            <textarea id="cms-prayer-request" name="request_text" required minLength={2} maxLength={5000} rows={4} placeholder={val(p, "request_placeholder", "Comparte tu necesidad...")} className="w-full rounded-xl px-4 py-3 text-sm border" style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }} />
          </div>
          <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
          {status === "error" && <p role="alert" aria-live="assertive" className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>}
          <button type="submit" disabled={status === "submitting"} className="inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white disabled:opacity-60" style={{ background: "var(--site-cta-gradient)" }}>
            {status === "submitting" ? "Enviando..." : val(p, "submit_label", "Enviar al equipo pastoral")}
          </button>
        </form>
      )}
    </section>
  );
}

// ─── Course Grid (config-only shell; data comes from academy API) ──────────────
