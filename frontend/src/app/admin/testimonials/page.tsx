"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ImageIcon, MessageCircle, ShieldCheck } from "lucide-react";

export default function AdminTestimonialsPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/cms/testimonials");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center bg-slate-950/20 p-8">
      <div className="max-w-xl rounded-[2rem] border border-white/10 bg-slate-900/70 p-8 text-white shadow-2xl">
        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">CMS</p>
        <h1 className="mt-3 text-2xl font-black uppercase tracking-tight">Moderacion de testimonios movida al CMS</h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Este acceso redirige al flujo real para gestionar texto, aprobacion, archivo, imagenes, videos y podcasts sin paneles duplicados.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Link href="/cms/testimonials" className="rounded-2xl border border-white/10 p-4 text-xs font-black uppercase tracking-widest text-slate-200 hover:border-primary">
            <MessageCircle size={16} className="mb-2 text-primary" /> Testimonios
          </Link>
          <Link href="/cms/media" className="rounded-2xl border border-white/10 p-4 text-xs font-black uppercase tracking-widest text-slate-200 hover:border-primary">
            <ImageIcon size={16} className="mb-2 text-primary" /> Biblioteca media
          </Link>
        </div>
        <div className="mt-5 flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400">
          <ShieldCheck size={14} className="text-emerald-400" /> Fuente unica del CMS
        </div>
      </div>
    </div>
  );
}
