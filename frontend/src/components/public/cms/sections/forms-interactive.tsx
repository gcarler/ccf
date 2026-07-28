"use client";

import { CmsSection } from "@/types/cms-v2";
import type { NewsletterProps, DocumentUploadProps } from "@/types/cms-section-props";
import { CheckCircle2, FileText, Send, Upload } from "lucide-react";
import React, { useState } from "react";
import { apiFetch } from "@/lib/http";
import { asProps, val } from "./shared";

export function NewsletterSection({ section }: { section: CmsSection<"newsletter"> }) {
  const props: NewsletterProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Mantente conectado");
  const body = val(p, "body", "");
  const btnLabel = val(p, "cta_label", "Suscribirse");
  const actionUrl = val(p, "action_url", "");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes("@")) return;
    setLoading(true);
    setSubmitError(null);
    try {
      if (actionUrl.trim()) {
        if (actionUrl.trim().startsWith("/")) {
          await apiFetch<void>(actionUrl.trim(), {
            method: "POST",
            body: { name, email },
            silent: true,
          });
        } else {
          const res = await fetch(actionUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email }),
          });
          if (!res.ok) throw new Error("Error al enviar");
        }
      }
      setSent(true);
    } catch {
      setSubmitError("No se pudo enviar. Intenta de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="ccf-section-panel p-8 md:p-14 lg:p-16 text-center"
      style={{ background: "linear-gradient(135deg, var(--site-primary-container), var(--site-surface-container))" }}
    >
      <h2 className="text-2xl md:text-3xl font-black tracking-tight" style={{ color: "var(--site-on-surface)" }}>{title}</h2>
      {body && <p className="mt-3 text-base max-w-xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>{body}</p>}
      {sent ? (
        <div className="mt-8 inline-flex items-center gap-3 rounded-xl px-6 py-4" style={{ background: "var(--site-surface-container)" }}>
          <span className="text-2xl">🎉</span>
          <p className="font-bold" style={{ color: "var(--site-on-surface)" }}>¡Gracias! Te mantendremos al tanto.</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-8 flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Tu nombre"
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))", color: "var(--site-on-surface)" }}
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="tu@email.com"
            required
            className="flex-1 rounded-xl px-4 py-3 text-sm border outline-none"
            style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))", color: "var(--site-on-surface)" }}
          />
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold text-white whitespace-nowrap disabled:opacity-60 transition-opacity hover:opacity-90"
            style={{ background: "var(--site-cta-gradient)" }}
          >
            <Send size={14} /> {loading ? "Enviando..." : btnLabel}
          </button>
        </form>
      )}
      {submitError && (
        <p className="mt-3 text-sm font-semibold text-[hsl(var(--destructive))]">{submitError}</p>
      )}
    </section>
  );
}

// ─── Document Upload ───────────────────────────────────────────────────────────

export function DocumentUploadSection({ section }: { section: CmsSection<"document_upload"> }) {
  const props: DocumentUploadProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "Subir Documento");
  const description = val(p, "description", "");
  const acceptedTypes = val(p, "accepted_types", ".pdf,.doc,.docx,.jpg,.png");
  const maxSize = parseInt(val(p, "max_size_mb", "10"));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > maxSize * 1024 * 1024) {
        setError(`El archivo excede ${maxSize}MB`);
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      await apiFetch<void>("/public/documents", { method: "POST", body: formData, silent: true });
      setUploaded(true);
    } catch (err: any) {
      setError(err.message || "Error al subir el documento");
    } finally {
      setUploading(false);
    }
  };

  if (uploaded) return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="rounded-lg p-6 text-center" style={{ background: "var(--site-primary-container)" }}>
        <CheckCircle2 size={48} className="mx-auto mb-3" style={{ color: "var(--site-primary)" }} />
        <p className="text-lg font-bold" style={{ color: "var(--site-on-primary)" }}>{val(p, "success_message", "Documento enviado correctamente")}</p>
      </div>
    </section>
  );

  return (
    <section className="py-8 md:py-12 px-3 md:px-6 lg:px-8 xl:px-12">
      <div className="max-w-xl mx-auto rounded-lg border-2 border-dashed p-8 text-center transition-all hover:border-site-primary/50" style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface-container)" }}>
        <FileText size={48} className="mx-auto mb-3 opacity-30" style={{ color: "var(--site-primary)" }} />
        <h3 className="text-lg font-bold mb-2" style={{ color: "var(--site-on-surface)" }}>{title}</h3>
        {description && <p className="text-sm mb-4" style={{ color: "var(--site-on-surface-variant)" }}>{description}</p>}
        {error && <p className="text-sm mb-3 text-[hsl(var(--destructive))] font-semibold">{error}</p>}
        <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold cursor-pointer hover:scale-105 transition-all" style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
          <Upload size={16} /> Seleccionar archivo
          <input type="file" accept={acceptedTypes} onChange={handleFile} className="hidden" />
        </label>
        {selectedFile && (
          <div className="mt-3 text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
            <span className="font-medium">{selectedFile.name}</span>
            <span className="mx-2 opacity-50">({(selectedFile.size / 1024).toFixed(0)}KB)</span>
            <button onClick={handleUpload} disabled={uploading} className="ml-3 px-3 py-1 rounded bg-[hsl(var(--success))] text-white text-xs font-semibold hover:bg-[hsl(var(--success)/0.8)] disabled:opacity-50">
              {uploading ? "Subiendo..." : "Enviar"}
            </button>
          </div>
        )}
        <p className="text-xs mt-3 opacity-50" style={{ color: "var(--site-on-surface-variant)" }}>Máx: {maxSize}MB · Tipos: {acceptedTypes}</p>
      </div>
    </section>
  );
}
