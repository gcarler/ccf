"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  User,
  Quote,
  BookOpen,
  Sparkles,
  MessageCircle,
  Share2,
  Copy,
  Check,
  ExternalLink,
  ChevronRight,
  Instagram,
  Facebook,
  Twitter,
  Heart,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { toast } from "sonner";
import { sanitizeCmsHtml } from "@/lib/cms/sanitize";

export interface PastorItem {
  id?: string | number;
  slug: string;
  name: string;
  role?: string;
  photo_url?: string;
  image?: string;
  bio_short?: string;
  bio_full?: string;
  story?: string;
  motto?: string;
  campus?: string;
  social_instagram?: string;
  social_facebook?: string;
  social_twitter?: string;
  is_main_pastor?: boolean;
  isMain?: boolean;
}

interface PastorDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  pastor: PastorItem | null;
}

function plainText(value: string | undefined): string {
  return (value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatSocialUrl(
  url: string | undefined | null,
  platform: "instagram" | "facebook" | "twitter"
): string | null {
  if (!url || !url.trim()) return null;
  const clean = url.trim();
  const isHandle = clean.startsWith("@") || (!clean.includes("/") && !clean.includes("."));
  if (isHandle) {
    const handle = clean.startsWith("@") ? clean.substring(1) : clean;
    if (platform === "instagram") return `https://instagram.com/${handle}`;
    if (platform === "facebook") return `https://facebook.com/${handle}`;
    if (platform === "twitter") return `https://x.com/${handle}`;
  }
  if (!/^https?:\/\//i.test(clean)) {
    return `https://${clean}`;
  }
  return clean;
}

export default function PastorDetailDrawer({
  isOpen,
  onClose,
  pastor,
}: PastorDetailDrawerProps) {
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

  if (!isOpen || !pastor) return null;

  const isMain = Boolean(pastor.is_main_pastor || pastor.isMain);
  const imageUrl = pastor.photo_url || pastor.image || "";
  const roleName = pastor.role || "Pastor de Comunidad Cristiana El Faro";
  const shortBio = plainText(pastor.bio_short || pastor.story || "");
  const fullBioHtml = pastor.bio_full || pastor.bio_short || pastor.story || "";

  const instagramUrl = formatSocialUrl(pastor.social_instagram, "instagram");
  const facebookUrl = formatSocialUrl(pastor.social_facebook, "facebook");
  const twitterUrl = formatSocialUrl(pastor.social_twitter, "twitter");

  const profileUrl = typeof window !== "undefined"
    ? `${window.location.origin}/pastores/${pastor.slug}`
    : `https://ccf.org/pastores/${pastor.slug}`;

  const handleCopyProfile = async () => {
    await navigator.clipboard.writeText(profileUrl);
    setCopied(true);
    toast.success("Enlace del perfil pastoral copiado al portapapeles");
    setTimeout(() => setCopied(false), 2500);
  };

  const handleWhatsApp = () => {
    const firstName = pastor.name.split(" ")[0];
    const text = encodeURIComponent(
      `¡Hola! Quisiera conectar con el ministerio del Pastor ${firstName} en Comunidad Cristiana El Faro.`
    );
    window.open(`https://wa.me/573008123456?text=${text}`, "_blank");
  };

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex justify-end"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pastor-drawer-title"
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
          className="relative z-10 w-full sm:max-w-lg md:max-w-xl h-full flex flex-col shadow-2xl overflow-hidden border-l"
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
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className="text-3xs font-extrabold uppercase tracking-wider px-2.5 py-1 rounded-full flex items-center gap-1"
                style={{
                  background: isMain
                    ? "var(--site-primary, #2563eb)"
                    : "var(--site-primary-container, rgba(37,99,235,0.12))",
                  color: isMain ? "#ffffff" : "var(--site-primary, #2563eb)",
                }}
              >
                {isMain && <Sparkles size={10} />}
                <span>{roleName}</span>
              </span>

              {isMain && (
                <span
                  className="text-3xs font-bold px-2 py-0.5 rounded-md"
                  style={{
                    background: "rgba(245, 158, 11, 0.15)",
                    color: "#d97706",
                  }}
                >
                  Principal
                </span>
              )}
            </div>

            <button
              onClick={onClose}
              aria-label="Cerrar panel pastoral"
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
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 scrollbar-thin">
            {/* Foto del Pastor */}
            <div className="relative aspect-[4/3] sm:aspect-[16/10] w-full rounded-2xl overflow-hidden shadow-md border border-site-outline-variant/15 bg-site-surface-container">
              {imageUrl ? (
                <Image
                  src={imageUrl}
                  alt={pastor.name}
                  fill
                  className="object-cover object-top"
                  sizes="(max-width: 768px) 100vw, 560px"
                  priority
                />
              ) : (
                <div
                  className="w-full h-full flex flex-col items-center justify-center space-y-2"
                  style={{
                    background:
                      "linear-gradient(135deg, var(--site-primary-container, rgba(37,99,235,0.12)), var(--site-surface-container-high, #e2e8f0))",
                  }}
                >
                  <User size={52} className="opacity-40" style={{ color: "var(--site-primary, #2563eb)" }} />
                  <span className="text-xs font-semibold opacity-60">Comunidad Cristiana El Faro</span>
                </div>
              )}
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 50%, transparent 100%)",
                }}
              />
              <div className="absolute bottom-4 left-4 right-4 text-white">
                <h2 id="pastor-drawer-title" className="text-xl sm:text-2xl font-black tracking-tight leading-tight">
                  {pastor.name}
                </h2>
                <p className="text-xs text-white/90 font-bold uppercase tracking-wider mt-0.5" style={{ color: "var(--site-primary-light, #93c5fd)" }}>
                  {roleName}
                </p>
              </div>
            </div>

            {/* Versículo / Cita Lema */}
            {shortBio && (
              <div
                className="p-4 sm:p-5 rounded-2xl border relative overflow-hidden space-y-2"
                style={{
                  background: "var(--site-surface-container-low, #f8f9fb)",
                  borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                }}
              >
                <Quote
                  size={32}
                  className="opacity-20 absolute top-3 right-3"
                  style={{ color: "var(--site-primary, #2563eb)" }}
                />
                <div className="flex items-center gap-1.5 text-3xs font-extrabold uppercase tracking-widest text-site-primary">
                  <BookOpen size={11} />
                  <span>Filosofía de Vida y Ministerio</span>
                </div>
                <p className="text-sm text-site-on-surface font-medium italic leading-relaxed">
                  &ldquo;{shortBio}&rdquo;
                </p>
              </div>
            )}

            {/* Trayectoria / Biografía Completa */}
            <div
              className="p-5 rounded-2xl border space-y-3"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <div className="flex items-center gap-2 border-b pb-2.5" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}>
                <User size={15} style={{ color: "var(--site-primary, #2563eb)" }} />
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-site-on-surface">
                  Biografía y Ministerio
                </h3>
              </div>

              <div
                className="text-xs sm:text-sm text-site-on-surface-variant leading-relaxed space-y-3"
                dangerouslySetInnerHTML={{ __html: sanitizeCmsHtml(fullBioHtml) }}
              />
            </div>

            {/* Redes Sociales del Pastor */}
            {(instagramUrl || facebookUrl || twitterUrl) && (
              <div
                className="p-4 rounded-2xl border flex items-center justify-between gap-3"
                style={{
                  background: "var(--site-surface-container-low, #f8f9fb)",
                  borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                }}
              >
                <span className="text-2xs font-extrabold uppercase tracking-wider text-site-on-surface-variant">
                  Conecta con el Pastor
                </span>
                <div className="flex items-center gap-2">
                  {instagramUrl && (
                    <a
                      href={instagramUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-8 h-8 rounded-xl border flex items-center justify-center transition-all hover:scale-110"
                      style={{
                        background: "var(--site-surface-container, #f1f5f9)",
                        borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                        color: "var(--site-primary, #2563eb)",
                      }}
                      title="Instagram"
                    >
                      <Instagram size={14} />
                    </a>
                  )}
                  {facebookUrl && (
                    <a
                      href={facebookUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-8 h-8 rounded-xl border flex items-center justify-center transition-all hover:scale-110"
                      style={{
                        background: "var(--site-surface-container, #f1f5f9)",
                        borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                        color: "var(--site-primary, #2563eb)",
                      }}
                      title="Facebook"
                    >
                      <Facebook size={14} />
                    </a>
                  )}
                  {twitterUrl && (
                    <a
                      href={twitterUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-8 h-8 rounded-xl border flex items-center justify-center transition-all hover:scale-110"
                      style={{
                        background: "var(--site-surface-container, #f1f5f9)",
                        borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                        color: "var(--site-primary, #2563eb)",
                      }}
                      title="X (Twitter)"
                    >
                      <Twitter size={14} />
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* Acciones de Contacto & Navegación */}
            <div className="pt-2 flex flex-col gap-3">
              {/* Botón WhatsApp Pastoral */}
              <button
                type="button"
                onClick={handleWhatsApp}
                className="w-full py-3 px-4 rounded-xl font-bold text-xs uppercase tracking-wider border shadow-sm transition-all flex items-center justify-center gap-2 hover:bg-emerald-50 hover:border-emerald-600"
                style={{
                  background: "rgba(16, 185, 129, 0.08)",
                  borderColor: "rgba(16, 185, 129, 0.35)",
                  color: "#059669",
                }}
              >
                <MessageCircle size={16} />
                <span>Escribir por WhatsApp Pastoral</span>
              </button>

              <div className="flex items-center gap-2">
                {/* Botón Compartir perfil */}
                <button
                  type="button"
                  onClick={handleCopyProfile}
                  className="flex-1 py-2.5 px-3 rounded-xl font-bold text-xs border transition-all flex items-center justify-center gap-1.5 hover:bg-site-surface-container"
                  style={{
                    borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                    color: copied ? "var(--site-primary, #2563eb)" : "var(--site-on-surface, #1e1f21)",
                  }}
                >
                  {copied ? (
                    <>
                      <Check size={14} className="text-emerald-600" />
                      <span>¡Enlace copiado!</span>
                    </>
                  ) : (
                    <>
                      <Share2 size={14} />
                      <span>Compartir perfil</span>
                    </>
                  )}
                </button>

                {/* Botón Ver perfil completo */}
                <Link
                  href={`/pastores/${pastor.slug}`}
                  onClick={onClose}
                  className="flex-1 py-2.5 px-3 rounded-xl font-bold text-xs text-white shadow-sm transition-opacity hover:opacity-95 flex items-center justify-center gap-1.5"
                  style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                >
                  <span>Ver perfil completo</span>
                  <ExternalLink size={13} className="opacity-80" />
                </Link>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="w-full py-2 px-4 rounded-xl font-bold text-3xs uppercase tracking-wider transition-colors hover:bg-black/5"
                style={{ color: "var(--site-on-surface-variant, #64748b)" }}
              >
                Cerrar Panel
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
