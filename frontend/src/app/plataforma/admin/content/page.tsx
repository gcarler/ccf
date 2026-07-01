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
    <div className="flex h-full items-center justify-center bg-[hsl(var(--bg-muted))]/20 p-4">
      <div className="max-w-xl rounded-lg border border-white/10 bg-[hsl(var(--bg-muted))]/70 p-4 text-white shadow-2xl">
        <p className="text-[10px] font-semibold uppercase tracking-wide text-primary">CMS</p>
        <h1 className="mt-3 text-lg font-semibold uppercase tracking-tight">Gestion de contenidos movida al CMS visual</h1>
        <p className="mt-3 text-sm leading-relaxed text-[hsl(var(--text-secondary))]">
          Este acceso redirige al editor real para evitar paneles duplicados o datos simulados.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <Link href="/cms/content" className="rounded-lg border border-white/10 p-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-primary">
            <FileText size={16} className="mb-2 text-primary" /> Contenido
          </Link>
          <Link href="/cms/media" className="rounded-lg border border-white/10 p-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-primary">
            <ImageIcon size={16} className="mb-2 text-primary" /> Media
          </Link>
          <Link href="/cms/testimonials" className="rounded-lg border border-white/10 p-4 text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:border-primary">
            <MessageCircle size={16} className="mb-2 text-primary" /> Testimonios
          </Link>
        </div>
      </div>
    </div>
  );
}
