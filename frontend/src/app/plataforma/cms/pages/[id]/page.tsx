"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Layout, FileText, PenTool, ArrowRight, Globe, Clock, Layers } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";

interface PageData {
  id: number;
  slug: string;
  title: string;
  status: string;
  site_key?: string;
  updated_at?: string;
  sections_count?: number;
}

const STATUS_STYLES: Record<string, { label: string; color: string }> = {
  published:  { label: "Publicado",   color: "text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200" },
  draft:      { label: "Borrador",    color: "text-slate-500 bg-slate-100 dark:bg-white/5 border-slate-200" },
  in_review:  { label: "En Revisión", color: "text-amber-600 bg-amber-50 dark:bg-amber-900/20 border-amber-200" },
  archived:   { label: "Archivado",   color: "text-rose-500 bg-rose-50 dark:bg-rose-900/10 border-rose-200" },
};

export default function CmsPageDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const id = params?.id as string;

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
          id: Number(id),
          slug: id,
          title: "Página",
          status: "draft",
          site_key: "faro",
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
    const siteKey = page.site_key || "faro";
    const slug = page.slug || id;

    if (countdown <= 0) {
      router.replace(`/cms/builder?site=${siteKey}&page=${slug}`);
      return;
    }

    const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown, page, loading, router, id]);

  const handleGoNow = () => {
    if (!page) return;
    const siteKey = page.site_key || "faro";
    router.replace(`/cms/builder?site=${siteKey}&page=${page.slug}`);
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3 bg-white dark:bg-[#0d0e11]">
        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center animate-pulse">
          <Layout size={28} strokeWidth={1} className="text-slate-400" />
        </div>
        <div className="space-y-2 text-center">
          <div className="h-5 w-48 bg-slate-100 dark:bg-white/5 rounded-md animate-pulse mx-auto" />
          <div className="h-3 w-32 bg-slate-100 dark:bg-white/5 rounded-md animate-pulse mx-auto" />
        </div>
      </div>
    );
  }

  const status = STATUS_STYLES[page?.status ?? "draft"] ?? STATUS_STYLES["draft"];

  return (
    <div className="flex flex-col h-full items-center justify-center bg-white dark:bg-[#0d0e11] p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg space-y-3 text-center"
      >
        {/* Icon */}
        <div className="flex justify-center">
          <div className="size-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-2xl shadow-blue-500/30">
            <PenTool size={32} className="text-white" strokeWidth={1.5} />
          </div>
        </div>

        {/* Page info */}
        <div className="space-y-3">
          <div className="flex justify-center">
            <span className={clsx("px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide border", status.color)}>
              {status.label}
            </span>
          </div>
          <h1 className="text-xl font-semibold text-slate-900 dark:text-white tracking-tight">
            {page?.title}
          </h1>
          <div className="flex items-center justify-center gap-4 text-[11px] font-bold text-slate-400">
            <span className="flex items-center gap-1.5">
              <Globe size={11} /> {page?.site_key || "faro"}
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
        <div className="bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg p-3 space-y-5">
          <div className="space-y-1">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide">
              Redirigiendo al Builder
            </p>
            <p className="text-slate-600 dark:text-slate-300 text-sm font-medium">
              Serás redirigido automáticamente al constructor visual donde podrás editar el contenido de esta página.
            </p>
          </div>

          {/* Countdown */}
          <div className="flex items-center justify-center">
            <div className="relative size-8">
              <svg className="size-8 -rotate-90" viewBox="0 0 56 56">
                <circle cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="4" className="text-slate-200 dark:text-white/10" />
                <circle
                  cx="28" cy="28" r="24" fill="none" stroke="currentColor" strokeWidth="4"
                  strokeDasharray={`${2 * Math.PI * 24}`}
                  strokeDashoffset={`${2 * Math.PI * 24 * (countdown / 3)}`}
                  className="text-blue-600 transition-all duration-1000"
                  strokeLinecap="round"
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xl font-semibold text-slate-800 dark:text-white">
                {countdown}
              </span>
            </div>
          </div>

          {/* CTA button */}
          <button
            onClick={handleGoNow}
            className="w-full flex items-center justify-center gap-3 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"
          >
            <PenTool size={16} />
            Abrir en el Builder ahora
            <ArrowRight size={16} />
          </button>

          <button
            onClick={() => router.push("/cms/pages")}
            className="w-full py-2.5 text-slate-400 hover:text-slate-600 text-[10px] font-semibold uppercase tracking-wide transition-colors"
          >
            ← Volver a páginas
          </button>
        </div>
      </motion.div>
    </div>
  );
}
