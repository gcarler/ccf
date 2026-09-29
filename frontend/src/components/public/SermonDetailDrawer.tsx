"use client";

import React, { useEffect, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Play,
  Calendar,
  Eye,
  Youtube,
  MessageCircle,
  Copy,
  Check,
  ExternalLink,
  BookOpen,
  User,
  Sparkles,
} from "lucide-react";
import Image from "next/image";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";

export interface YTVideo {
  id: string;
  title: string;
  description: string;
  published_at: string;
  view_count: number;
  thumbnail_hq: string;
  thumbnail_mq: string;
  url: string;
  embed_url: string;
}

interface SermonDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  video: YTVideo | null;
  allVideos?: YTVideo[];
  onSelectVideo?: (video: YTVideo) => void;
  shareWhatsappLabel?: string;
  copyLinkLabel?: string;
  copiedLabel?: string;
  viewOnYoutubeLabel?: string;
}

/* Limpia la descripción: remueve enlaces y banners de redes sociales */
function cleanDescription(raw: string) {
  const cutMarkers = [
    "¡NO OLVIDES",
    "REDES SOCIALES",
    "Instagram:",
    "Facebook:",
    "Visita nuestra página",
    "Suscríbete",
  ];
  let s = raw ?? "";
  for (const m of cutMarkers) {
    const i = s.indexOf(m);
    if (i > 0) s = s.substring(0, i);
  }
  return s.trim();
}

/* Extrae el nombre del predicador */
export function extractPreacherName(title: string): string {
  const parts = title.split("|").map((p) => p.trim());
  if (parts.length > 1) {
    for (const part of [...parts].reverse()) {
      if (/(ap\.?|ps\.?|pastor|pastora|profeta|ev\.?|obispo)/i.test(part)) {
        return normalizePreacherTitle(part);
      }
    }
    const last = parts[parts.length - 1];
    if (!/^(parte|part|\d+)/i.test(last)) {
      return normalizePreacherTitle(last);
    }
  }
  return "Comunidad Cristiana El Faro";
}

function normalizePreacherTitle(raw: string): string {
  let s = raw.replace(/\s+/g, " ").trim();
  s = s.replace(/^Ps\s+/i, "Ps. ");
  s = s.replace(/^Ap\s+/i, "Ap. ");
  return s;
}

/* Detecta citas bíblicas en título o descripción */
function extractBibleVerse(text: string): string | null {
  const regex =
    /\b(?:1|2|3)?\s*(?:Génesis|Éxodo|Levítico|Números|Deuteronomio|Josué|Jueces|Rut|Samuel|Reyes|Crónicas|Esdras|Nehemías|Ester|Job|Salmos?|Proverbios|Eclesiastés|Cantares|Isaías|Jeremías|Lamentaciones|Ezequiel|Daniel|Oseas|Joel|Amós|Abdías|Jonás|Miqueas|Nahúm|Habacuc|Sofonías|Hageo|Zacarías|Malaquías|Mateo|Marcos|Lucas|Juan|Hechos|Romanos|Corintios|Gálatas|Efesios|Filipenses|Colosenses|Tesalonicenses|Timoteo|Tito|Filemón|Hebreos|Santiago|Pedro|Judas|Apocalipsis)\s+\d+(?::\d+(?:-\d+)?)?\b/i;
  const match = regex.exec(text);
  return match ? match[0] : null;
}

function formatViewsCount(n: number) {
  if (!n) return "";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return `${n}`;
}

export default function SermonDetailDrawer({
  isOpen,
  onClose,
  video,
  allVideos = [],
  onSelectVideo,
  shareWhatsappLabel = "WhatsApp",
  copyLinkLabel = "Copiar link",
  copiedLabel = "¡Copiado!",
  viewOnYoutubeLabel = "Ver en YouTube",
}: SermonDetailDrawerProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !video) return null;

  const desc = cleanDescription(video.description);
  const preacher = extractPreacherName(video.title);
  const bibleVerse = extractBibleVerse(`${video.title} ${desc}`);

  // Mensajes relacionados del mismo predicador
  const relatedVideos = allVideos
    .filter((v) => v.id !== video.id)
    .filter((v) => {
      if (preacher === "Comunidad Cristiana El Faro") return true;
      return extractPreacherName(v.title).toLowerCase() === preacher.toLowerCase();
    })
    .slice(0, 5);

  const fallbackVideos =
    relatedVideos.length === 0
      ? allVideos.filter((v) => v.id !== video.id).slice(0, 5)
      : relatedVideos;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(video.url);
    setCopied(true);
    toast.success("Enlace del mensaje copiado al portapapeles");
    setTimeout(() => setCopied(false), 2500);
  };

  const handleShareWhatsApp = () => {
    const text = encodeURIComponent(
      `🎙️ Te comparto este mensaje de fe de Comunidad Cristiana El Faro:\n\n*${video.title}*\n${video.url}`
    );
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex justify-end"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sermon-drawer-title"
      >
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Sliding Panel */}
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 28, stiffness: 280 }}
          className="relative z-10 w-full sm:max-w-xl md:max-w-2xl h-full flex flex-col shadow-2xl overflow-hidden border-l"
          style={{
            background: "var(--site-surface, #ffffff)",
            borderColor: "var(--site-outline-variant, rgba(0,0,0,0.1))",
            color: "var(--site-on-surface, #1e1f21)",
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between p-4 sm:p-5 border-b shrink-0 bg-site-surface-container-lowest"
            style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="text-3xs font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full flex items-center gap-1.5 shrink-0"
                style={{
                  background: "var(--site-primary-container, rgba(37,99,235,0.12))",
                  color: "var(--site-primary, #2563eb)",
                }}
              >
                <User size={11} />
                <span className="truncate max-w-[200px] sm:max-w-[320px]">{preacher}</span>
              </span>

              {bibleVerse && (
                <span
                  className="hidden sm:inline-flex items-center gap-1 text-3xs font-semibold px-2 py-0.5 rounded-md truncate max-w-[180px]"
                  style={{
                    background: "var(--site-surface-container-high, #e2e8f0)",
                    color: "var(--site-on-surface-variant, #475569)",
                  }}
                >
                  <BookOpen size={10} />
                  <span className="truncate">{bibleVerse}</span>
                </span>
              )}
            </div>

            <button
              onClick={onClose}
              aria-label="Cerrar reproductor"
              className="p-2 rounded-xl transition-colors hover:scale-105"
              style={{
                background: "var(--site-surface-container, rgba(0,0,0,0.04))",
                color: "var(--site-on-surface-variant, #64748b)",
              }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 scrollbar-thin">
            {/* Reproductor Embebido 16:9 */}
            <div className="relative aspect-video rounded-2xl overflow-hidden bg-black shadow-lg border border-site-outline-variant/15">
              <iframe
                key={video.id}
                src={video.embed_url}
                title={video.title}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                className="w-full h-full border-0"
              />
            </div>

            {/* Título y Metadatos */}
            <div>
              <h2
                id="sermon-drawer-title"
                className="text-lg sm:text-xl font-black tracking-tight leading-snug text-site-on-surface mb-2"
              >
                {video.title}
              </h2>

              <div className="flex items-center gap-3 text-xs text-site-outline font-medium flex-wrap">
                <span className="flex items-center gap-1">
                  <Calendar size={13} className="text-site-primary" />
                  {formatDate(video.published_at, {
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                    fallback: "",
                  })}
                </span>

                {video.view_count > 0 && (
                  <span className="flex items-center gap-1">
                    <Eye size={13} className="text-site-primary" />
                    {formatViewsCount(video.view_count)} reproducciones
                  </span>
                )}

                {bibleVerse && (
                  <span className="sm:hidden inline-flex items-center gap-1 text-site-primary font-semibold">
                    <BookOpen size={11} /> {bibleVerse}
                  </span>
                )}
              </div>
            </div>

            {/* Acciones Rápidas */}
            <div
              className="p-3.5 rounded-2xl border flex items-center justify-between gap-2 flex-wrap"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                {/* WhatsApp */}
                <button
                  type="button"
                  onClick={handleShareWhatsApp}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold transition-all hover:bg-[hsl(var(--success)/0.15)] hover:border-[hsl(var(--success))] border shadow-2xs"
                  style={{
                    background: "hsl(var(--success) / 0.08)",
                    borderColor: "hsl(var(--success) / 0.35)",
                    color: "hsl(var(--success))",
                  }}
                >
                  <MessageCircle size={15} />
                  <span>{shareWhatsappLabel}</span>
                </button>

                {/* Copiar enlace */}
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold border transition-all hover:bg-site-surface-container"
                  style={{
                    borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                    color: copied ? "var(--site-primary, #2563eb)" : "var(--site-on-surface, #1e1f21)",
                  }}
                >
                  {copied ? (
                    <>
                      <Check size={14} className="text-[hsl(var(--success))]" />
                      <span>{copiedLabel}</span>
                    </>
                  ) : (
                    <>
                      <Copy size={14} />
                      <span>{copyLinkLabel}</span>
                    </>
                  )}
                </button>
              </div>

              {/* Ver en YouTube */}
              <a
                href={video.url}
                target="_blank"
                rel="noopener noreferrer"
                title={viewOnYoutubeLabel}
                className="flex items-center gap-1.5 py-2 px-3.5 rounded-xl text-xs font-bold text-white transition-opacity hover:opacity-90 shadow-2xs"
                style={{ background: "var(--site-cta-gradient, #2563eb)" }}
              >
                <Youtube size={15} />
                <span className="hidden sm:inline">{viewOnYoutubeLabel}</span>
                <ExternalLink size={12} className="opacity-80" />
              </a>
            </div>

            {/* Descripción Pastoral Limpia */}
            {desc && (
              <div
                className="p-4 rounded-2xl border space-y-1.5"
                style={{
                  background: "var(--site-surface-container-low, #f8f9fb)",
                  borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                }}
              >
                <span
                  className="text-3xs font-extrabold uppercase tracking-wider block"
                  style={{ color: "var(--site-primary, #2563eb)" }}
                >
                  Resumen de la Enseñanza
                </span>
                <p className="text-xs text-site-on-surface-variant leading-relaxed whitespace-pre-line">
                  {desc}
                </p>
              </div>
            )}

            {/* Carrusel / Lista de Más Mensajes de este Predicador */}
            {fallbackVideos.length > 0 && (
              <div className="pt-2 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <Sparkles size={14} style={{ color: "var(--site-primary, #2563eb)" }} />
                    <h3 className="text-xs font-extrabold uppercase tracking-wider text-site-on-surface">
                      {relatedVideos.length > 0
                        ? `Más mensajes de ${preacher}`
                        : "Otras prédicas recomendadas"}
                    </h3>
                  </div>
                  <span className="text-3xs font-bold text-site-outline">
                    {fallbackVideos.length} disponibles
                  </span>
                </div>

                <div className="space-y-2.5">
                  {fallbackVideos.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => onSelectVideo && onSelectVideo(item)}
                      className="group flex items-start gap-3 p-2.5 rounded-xl border border-site-outline-variant/15 hover:border-site-primary/40 hover:bg-site-surface-container transition-all cursor-pointer"
                      style={{ background: "var(--site-surface-container-lowest, #ffffff)" }}
                    >
                      <div className="relative w-24 aspect-video rounded-lg overflow-hidden bg-black shrink-0">
                        <Image
                          src={item.thumbnail_mq || item.thumbnail_hq}
                          alt={item.title}
                          fill
                          className="object-cover group-hover:scale-105 transition-transform duration-300"
                          sizes="96px"
                        />
                        <div className="absolute inset-0 bg-black/25 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <Play size={16} fill="white" className="text-white ml-0.5" />
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        <h4 className="font-bold text-xs text-site-on-surface group-hover:text-site-primary transition-colors line-clamp-2 leading-snug">
                          {item.title}
                        </h4>
                        <p className="text-3xs text-site-outline mt-1 flex items-center gap-1">
                          <Calendar size={9} />
                          {formatDate(item.published_at, { month: "short", day: "numeric" })}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
