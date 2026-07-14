"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ImageIcon, MessageCircle, ShieldCheck } from "lucide-react";

export default function AdminTestimonialsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/plataforma/cms/testimonials");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center bg-[hsl(var(--bg-muted))]/20 p-4">
      <div className="max-w-xl rounded-lg border border-white/10 bg-[hsl(var(--bg-muted))]/70 p-4 text-white shadow-2xl">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-primary">CMS</p>
        <h1 className="mt-3 text-lg font-semibold uppercase tracking-tight">Moderacion de testimonios movida al CMS</h1>
        <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
          Este acceso redirige al flujo real para gestionar texto, aprobacion, archivo, imagenes, videos y podcasts sin paneles duplicados.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link href="/plataforma/cms/testimonials" className="rounded-lg border border-white/10 p-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-primary">
            <MessageCircle size={16} className="mb-2 text-primary" /> Testimonios
          </Link>
          <Link href="/plataforma/cms/media" className="rounded-lg border border-white/10 p-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-primary">
            <ImageIcon size={16} className="mb-2 text-primary" /> Biblioteca media
          </Link>
        </div>
        <div className="mt-5 flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
          <ShieldCheck size={14} className="text-emerald-400" /> Fuente unica del CMS
        </div>
      </div>
    </div>
  );
}
