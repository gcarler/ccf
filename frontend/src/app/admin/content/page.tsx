"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { FileText, ImageIcon, MessageCircle } from "lucide-react";

export default function AdminContent() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/cms/content");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center bg-slate-950/20 p-8">
      <div className="max-w-xl rounded-[2rem] border border-white/10 bg-slate-900/70 p-8 text-white shadow-2xl">
        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-primary">CMS</p>
        <h1 className="mt-3 text-2xl font-black uppercase tracking-tight">Gestion de contenidos movida al CMS visual</h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Este acceso redirige al editor real para evitar paneles duplicados o datos simulados.
        </p>
        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Link href="/cms/content" className="rounded-2xl border border-white/10 p-4 text-xs font-black uppercase tracking-widest text-slate-200 hover:border-primary">
            <FileText size={16} className="mb-2 text-primary" /> Contenido
          </Link>
          <Link href="/cms/media" className="rounded-2xl border border-white/10 p-4 text-xs font-black uppercase tracking-widest text-slate-200 hover:border-primary">
            <ImageIcon size={16} className="mb-2 text-primary" /> Media
          </Link>
          <Link href="/cms/testimonials" className="rounded-2xl border border-white/10 p-4 text-xs font-black uppercase tracking-widest text-slate-200 hover:border-primary">
            <MessageCircle size={16} className="mb-2 text-primary" /> Testimonios
          </Link>
        </div>
      </div>
    </div>
  );
}
