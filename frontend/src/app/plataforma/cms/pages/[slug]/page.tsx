"use client";

import React, { useEffect, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Layout, FileText, PenTool, ArrowRight, Globe, Clock, Layers } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import { DSCard } from '@/design';

interface PageData {
  id: string;
  slug: string;
  title: string;
  status: string;
  site_key?: string;
  updated_at?: string;
  sections_count?: number;
}

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  published:  { label: "Publicado",   color: "text-[hsl(var(--success))] bg-[hsl(var(--success-muted))] border-[hsl(var(--success)/0.25)]" },
  draft:      { label: "Borrador",    color: "text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] border-[hsl(var(--border))]" },
  in_review:  { label: "En Revisión", color: "text-[hsl(var(--warning))] bg-[hsl(var(--warning-muted))] border-[hsl(var(--warning)/0.25)]" },
  archived:   { label: "Archivado",   color: "text-[hsl(var(--destructive))] bg-[hsl(var(--destructive)/0.1)] border-[hsl(var(--destructive)/0.25)]" },
};

export default function CmsPageDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const id = params?.slug as string;

  const [page, setPage] = useState<PageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [countdown, setCountdown] = useState(3);

  useEffect(() => {
    if (!token || !id) return;
    const load = async () => {
      try {
        setLoading(true);
        const data = await apiFetch<PageData>(`/cms/pages/${id}`, { token }).catch(() => null);
        setPage(data ?? {
          id: id,
          slug: id,
          title: "Página",
          status: "draft",
          site_key: SITE_KEY,
        });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id, token]);

  // Auto-redirect countdown
  useEffect(() => {
    if (!page || loading) return;
    const siteKey = page.site_key || SITE_KEY;
    const slug = page.slug || id;

    if (countdown <= 0) {
      router.replace(`/plataforma/cms/builder?site=${siteKey}&page=${slug}`);
      return;
    }

    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, page, loading, router, id]);

  const handleGoNow = () => {
    if (!page) return;
    const siteKey = page.site_key || SITE_KEY;
    router.replace(`/plataforma/cms/builder?site=${siteKey}&page=${page.slug}`);
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3 bg-[hsl(var(--bg-primary))] ">
        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))]  flex items-center justify-center animate-pulse">
          <Layout size={28} strokeWidth={1} className="text-[hsl(var(--text-secondary))]" />
        </div>
        <div className="space-y-2 text-center">
          <div className="h-5 w-48 bg-[hsl(var(--surface-2))]  rounded-md animate-pulse mx-auto" />
          <div className="h-3 w-32 bg-[hsl(var(--surface-2))]  rounded-md animate-pulse mx-auto" />
        </div>
      </div>
    );
  }

  const status = STATUS_STYLES[page?.status ?? "draft"] ?? STATUS_STYLES["draft"];

  return (
    <div className="flex flex-col h-full items-center justify-center bg-[hsl(var(--bg-primary))]  p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg space-y-3 text-center"
      >
        {/* Icon */}
        <div className="flex justify-center">
          <div className="size-8 rounded-lg bg-gradient-to-br from-[hsl(var(--info))] to-[hsl(var(--info))] flex items-center justify-center shadow-2xl shadow-[hsl(var(--info)/30%)]">
            <PenTool size={32} className="text-[hsl(var(--primary-foreground))]" strokeWidth={1.5} />
          </div>
        </div>

        {/* Page info */}
        <div className="space-y-3">
          <div className="flex justify-center">
            <span className={clsx("px-3 py-1 rounded-full text-2xs font-semibold uppercase tracking-wide border", status.color)}>
              {status.label}
            </span>
          </div>
          <h1 className="text-xl font-semibold text-[hsl(var(--text-primary))] tracking-tight">
            {page?.title}
          </h1>
          <div className="flex items-center justify-center gap-4 text-xs font-bold text-[hsl(var(--text-secondary))]">
            <span className="flex items-center gap-1.5">
              <Globe size={11} /> {page?.site_key || SITE_KEY}
            </span>
            <span className="flex items-center gap-1.5">
              <FileText size={11} /> /{page?.slug}
            </span>
            {page?.sections_count !== undefined && (
              <span className="flex items-center gap-1.5">
                <Layers size={11} /> {page.sections_count} secciones
              </span>
            )}
            {page?.updated_at && (
              <span className="flex items-center gap-1.5">
                <Clock size={11} />
                {new Date(page.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>

        {/* Redirect card */}
        <DSCard className="space-y-5">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
              Redirigiendo al Builder
            </p>
            <p className="text-[hsl(var(--text-secondary))]  text-sm font-medium">
              Serás redirigido automáticamente al constructor visual donde podrás editar el contenido de esta página.
            </p>
          </div>

          {/* Countdown */}
          <div className="flex items-center justify-center">
            <div className="relative size-8">
              <svg className="size-8 -rotate-90" viewBox="0 0 56 56">
                <circle cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="4" className="text-[hsl(var(--border))]" />
                <circle
                  cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="4"
                  strokeDasharray={`${2 * Math.PI * 24}`}
                  strokeDashoffset={`${2 * Math.PI * 24 * (countdown / 3)}`}
                  className="text-[hsl(var(--primary))] transition-all duration-1000"
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xl font-semibold text-[hsl(var(--text-primary))]">
                {countdown}
              </span>
            </div>
          </div>

          {/* CTA button */}
          <button
            onClick={handleGoNow}
            className="w-full flex items-center justify-center gap-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg text-xs font-semibold uppercase tracking-wide shadow-xl shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all"
          >
            <PenTool size={16} />
            Abrir en el Builder ahora
            <ArrowRight size={16} />
          </button>

          <button
            onClick={() => router.push("/plataforma/cms/pages")}
            className="w-full py-2.5 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] text-2xs font-semibold uppercase tracking-wide transition-colors"
          >
            ← Volver a páginas
          </button>
        </DSCard>
      </motion.div>
    </div>
  );
}
