"use client";

import { CmsSection } from "@/types/cms-v2";
import type { ContactFormProps, PrayerFormProps } from "@/types/cms-section-props";
import { useState } from "react";
import { apiFetch, extractErrorMessage } from "@/lib/http";
import { CheckCircle2, HeartHandshake, Loader2, Mail, MessageSquare, Phone, Send, User } from "lucide-react";
import { asProps, val } from "./shared";

const inputClass = "w-full rounded-xl px-4 py-3 text-sm border outline-none transition-all focus:ring-2 focus:ring-site-primary/25" +
  " [&::placeholder]:text-site-outline";

function inputStyle(): React.CSSProperties {
  return {
    background: "var(--site-surface)",
    borderColor: "var(--site-outline-variant)",
    color: "var(--site-on-surface)",
  };
}

function FieldLabel({ htmlFor, icon, children }: { htmlFor: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--site-on-surface)" }}>
      <span aria-hidden="true" className="text-site-primary">{icon}</span>
      {children}
    </label>
  );
}

function FormSuccess({ message, resetLabel, onReset }: { message: string; resetLabel: string; onReset: () => void }) {
  return (
    <div className="mt-8 flex flex-col items-center gap-4 rounded-2xl border p-8 text-center" style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface)" }}>
      <div className="flex size-14 items-center justify-center rounded-full" style={{ background: "var(--site-primary-container)" }}>
        <CheckCircle2 size={28} style={{ color: "var(--site-primary)" }} />
      </div>
      <p role="status" aria-live="polite" className="text-lg font-bold" style={{ color: "var(--site-on-surface)" }}>{message}</p>
      <button
        type="button"
        onClick={onReset}
        className="mt-1 rounded-full border px-5 py-2 text-xs font-bold uppercase tracking-widest transition-all hover:scale-105"
        style={{ borderColor: "var(--site-primary)", color: "var(--site-primary)" }}
      >
        {resetLabel}
      </button>
    </div>
  );
}

function SubmitButton({ submitting, label }: { submitting: boolean; label: string }) {
  return (
    <button
      type="submit"
      disabled={submitting}
      className="inline-flex w-full items-center justify-center gap-2 rounded-full px-6 py-3.5 text-sm font-bold uppercase tracking-widest text-white transition-all hover:scale-[1.02] active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
      style={{ background: "var(--site-cta-gradient)", boxShadow: "var(--site-cta-shadow)" }}
    >
      {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={15} />}
      {submitting ? "Enviando..." : label}
    </button>
  );
}

export function ContactFormSection({ section }: { section: CmsSection<"contact_form"> }) {
  const props: ContactFormProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Hablemos de Tu Caminar");
  const subtitle = val(p, "subtitle", "");
  const actionUrl = val(p, "action_url", "/public/contact");
  const resetLabel = val(p, "reset_label", "Enviar otro mensaje");
  const fullBleed = Boolean(p.full_bleed);
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
    <section className={`ccf-section-panel p-7 md:p-12 lg:p-14 ${fullBleed ? "relative left-1/2 w-screen -translate-x-1/2 rounded-none" : ""}`} style={{ background: "var(--site-surface-container-low)" }}>
      {title && <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>}
      {subtitle && <p className="mt-3 text-base" style={{ color: "var(--site-on-surface-variant)" }}>{subtitle}</p>}
      {status === "success" ? (
        <FormSuccess
          message={val(p, "success_message", "Gracias. Te contactaremos pronto.")}
          resetLabel={resetLabel}
          onReset={() => setStatus("idle")}
        />
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-5 max-w-xl">
          <div className="space-y-2">
            <FieldLabel htmlFor="cms-contact-full-name" icon={<User size={15} />}>{val(p, "name_label", "Nombre completo")}</FieldLabel>
            <input id="cms-contact-full-name" name="full_name" required minLength={2} maxLength={160} type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} autoComplete="name" className={inputClass} style={inputStyle()} />
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel htmlFor="cms-contact-email" icon={<Mail size={15} />}>{val(p, "email_label", "Correo electrónico")}</FieldLabel>
              <input id="cms-contact-email" name="email" type="email" maxLength={255} placeholder={val(p, "email_placeholder", "tu@email.com (opcional)")} autoComplete="email" className={inputClass} style={inputStyle()} />
            </div>
            <div className="space-y-2">
              <FieldLabel htmlFor="cms-contact-phone" icon={<Phone size={15} />}>{val(p, "phone_label", "WhatsApp")}</FieldLabel>
              <input id="cms-contact-phone" name="phone" type="tel" maxLength={40} placeholder={val(p, "phone_placeholder", "+57 300...")} autoComplete="tel" className={inputClass} style={inputStyle()} />
            </div>
          </div>
          <div className="space-y-2">
            <FieldLabel htmlFor="cms-contact-notes" icon={<MessageSquare size={15} />}>{val(p, "message_label", "¿En qué podemos ayudarte?")}</FieldLabel>
            <textarea id="cms-contact-notes" name="notes" required minLength={2} maxLength={5000} rows={4} placeholder={val(p, "message_placeholder", "Cuéntanos un poco sobre ti...")} className={inputClass} style={inputStyle()} />
          </div>
          <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
          {status === "error" && <p role="alert" aria-live="assertive" className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>}
          <SubmitButton submitting={status === "submitting"} label={val(p, "submit_label", "Enviar mensaje y conectar")} />
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
  const resetLabel = val(p, "reset_label", "Enviar otra petición");
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
        <FormSuccess
          message={val(p, "success_message", "Tu petición ha sido enviada.")}
          resetLabel={resetLabel}
          onReset={() => setStatus("idle")}
        />
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 space-y-5 max-w-xl">
          <div className="space-y-2">
            <FieldLabel htmlFor="cms-prayer-name" icon={<User size={15} />}>{val(p, "name_label", "Nombre")}</FieldLabel>
            <input id="cms-prayer-name" name="requester_name" required minLength={2} maxLength={160} type="text" placeholder={val(p, "name_placeholder", "Tu nombre")} autoComplete="name" className={inputClass} style={inputStyle()} />
          </div>
          <div className="space-y-2">
            <FieldLabel htmlFor="cms-prayer-request" icon={<HeartHandshake size={15} />}>{val(p, "request_label", "Petición de oración")}</FieldLabel>
            <textarea id="cms-prayer-request" name="request_text" required minLength={2} maxLength={5000} rows={4} placeholder={val(p, "request_placeholder", "Comparte tu necesidad...")} className={inputClass} style={inputStyle()} />
          </div>
          <input name="website" tabIndex={-1} autoComplete="off" aria-hidden="true" className="hidden" />
          {status === "error" && <p role="alert" aria-live="assertive" className="text-sm font-semibold text-[hsl(var(--destructive))]">{error}</p>}
          <SubmitButton submitting={status === "submitting"} label={val(p, "submit_label", "Enviar al equipo pastoral")} />
        </form>
      )}
    </section>
  );
}

// ─── Course Grid (config-only shell; data comes from academy API) ──────────────
