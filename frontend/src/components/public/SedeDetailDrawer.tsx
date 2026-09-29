"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  MapPin,
  Clock,
  User,
  Phone,
  Navigation,
  Copy,
  Check,
  Building2,
  Calendar,
  Sparkles,
  MessageCircle,
  ExternalLink,
  Baby,
} from "lucide-react";
import Image from "next/image";
import { toast } from "sonner";

export interface SedeDetailItem {
  id: string | number;
  name: string;
  address: string;
  city?: string;
  phone?: string;
  pastor?: string;
  pastor_name?: string;
  schedule?: string;
  midweek?: string;
  farokids_schedule?: string;
  image?: string;
  image_url?: string;
  mapsUrl?: string;
  maps_url?: string;
  mapEmbedUrl?: string;
  map_embed_url?: string;
  lat?: number | null;
  lng?: number | null;
  isMain?: boolean;
  is_main?: boolean;
  whatsapp?: string;
}

interface SedeDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sede: SedeDetailItem | null;
}

export default function SedeDetailDrawer({
  isOpen,
  onClose,
  sede,
}: SedeDetailDrawerProps) {
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

  if (!isOpen || !sede) return null;

  const pastorName = sede.pastor || sede.pastor_name || "";
  const imageUrl = sede.image || sede.image_url || "";
  const isMainSede = Boolean(sede.is_main || sede.isMain);
  const fullAddress = sede.address || "Dirección no especificada";

  const handleCopy = () => {
    if (!sede.address) return;
    navigator.clipboard.writeText(sede.address);
    setCopied(true);
    toast.success("Dirección copiada al portapapeles");
    setTimeout(() => setCopied(false), 2500);
  };

  // Format clean phone for WhatsApp
  const rawPhone = sede.phone || "+57 300 000 0000";
  const cleanPhone = rawPhone.replace(/[^\d]/g, "");
  const whatsappUrl = `https://wa.me/${cleanPhone}?text=${encodeURIComponent(
    `¡Hola! Quisiera más información sobre los servicios y reuniones de la ${sede.name}.`
  )}`;

  const googleMapsUrl =
    sede.mapsUrl ||
    sede.maps_url ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      [sede.name, sede.address, sede.city || "Colombia"].filter(Boolean).join(", ")
    )}`;

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex justify-end"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sede-drawer-title"
      >
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        />

        {/* Sliding Panel */}
        <motion.div
          initial={{ x: "100%" }}
          animate={{ x: 0 }}
          exit={{ x: "100%" }}
          transition={{ type: "spring", damping: 28, stiffness: 280 }}
          className="relative z-10 w-full sm:max-w-md md:max-w-lg h-full flex flex-col shadow-2xl overflow-hidden border-l"
          style={{
            background: "var(--site-surface-1, #ffffff)",
            borderColor: "var(--site-outline-variant, rgba(0,0,0,0.1))",
            color: "var(--site-on-surface, #1e1f21)",
          }}
        >
          {/* Header */}
          <div
            className="flex items-center justify-between p-5 border-b shrink-0"
            style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}
          >
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full"
                style={{
                  background: isMainSede
                    ? "var(--site-primary, #2563eb)"
                    : "var(--site-primary-container, rgba(37,99,235,0.1))",
                  color: isMainSede ? "#ffffff" : "var(--site-primary, #2563eb)",
                }}
              >
                {isMainSede ? "Sede Principal" : sede.city || "Sede Filial"}
              </span>
            </div>
            <button
              onClick={onClose}
              aria-label="Cerrar detalles de sede"
              className="p-2 rounded-lg transition-colors hover:scale-105"
              style={{
                background: "var(--site-surface-container, rgba(0,0,0,0.04))",
                color: "var(--site-on-surface-variant, #64748b)",
              }}
            >
              <X size={20} />
            </button>
          </div>

          {/* Body Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Foto de la Sede */}
            <div className="relative h-48 sm:h-56 w-full rounded-2xl overflow-hidden shadow-sm border border-site-outline-variant/10">
              {imageUrl ? (
                <Image
                  src={imageUrl}
                  alt={sede.name}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 480px"
                />
              ) : (
                <div
                  className="w-full h-full flex flex-col items-center justify-center space-y-2"
                  style={{
                    background:
                      "linear-gradient(135deg, var(--site-primary-container, rgba(37,99,235,0.12)), var(--site-surface-container-high, #e2e8f0))",
                  }}
                >
                  <Building2 size={44} className="opacity-40" style={{ color: "var(--site-primary, #2563eb)" }} />
                  <span className="text-xs font-semibold opacity-60">Comunidad Cristiana El Faro</span>
                </div>
              )}
              <div
                className="absolute inset-0"
                style={{
                  background:
                    "linear-gradient(to top, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.1) 50%, transparent 100%)",
                }}
              />
              <div className="absolute bottom-4 left-4 right-4 text-white">
                <h2 id="sede-drawer-title" className="text-xl sm:text-2xl font-black tracking-tight leading-tight">
                  {sede.name}
                </h2>
                {sede.city && (
                  <p className="text-xs text-white/90 font-medium flex items-center gap-1 mt-0.5">
                    <MapPin size={12} className="text-primary" /> {sede.city}, Colombia
                  </p>
                )}
              </div>
            </div>

            {/* Pastores a Cargo */}
            {pastorName && (
              <div
                className="p-4 rounded-xl border flex items-center gap-3.5"
                style={{
                  background: "var(--site-surface-container-low, #f8f9fb)",
                  borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                }}
              >
                <div
                  className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                  style={{
                    background: "var(--site-primary-container, rgba(37,99,235,0.15))",
                    color: "var(--site-primary, #2563eb)",
                  }}
                >
                  <User size={20} />
                </div>
                <div>
                  <span className="text-3xs font-extrabold uppercase tracking-wider block" style={{ color: "var(--site-primary, #2563eb)" }}>
                    Pastores a Cargo
                  </span>
                  <p className="text-sm font-bold mt-0.5" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                    {pastorName}
                  </p>
                </div>
              </div>
            )}

            {/* Horarios Detallados */}
            <div
              className="p-5 rounded-2xl border space-y-4"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <div className="flex items-center gap-2 border-b pb-2.5" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}>
                <Clock size={16} style={{ color: "var(--site-primary, #2563eb)" }} />
                <h3 className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                  Horarios de Cultos y Reuniones
                </h3>
              </div>

              <div className="space-y-3">
                {/* Culto Dominical */}
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg shrink-0 mt-0.5" style={{ background: "var(--site-primary-container, rgba(37,99,235,0.1))", color: "var(--site-primary, #2563eb)" }}>
                    <Calendar size={16} />
                  </div>
                  <div>
                    <span className="text-xs font-bold block" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                      Cultos Dominicales
                    </span>
                    <p className="text-xs mt-0.5" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                      {sede.schedule || "Domingos: 8:00 AM y 10:30 AM"}
                    </p>
                  </div>
                </div>

                {/* Culto Entre Semana */}
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg shrink-0 mt-0.5" style={{ background: "var(--site-surface-container-high, #e2e8f0)", color: "var(--site-on-surface, #1e1f21)" }}>
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <span className="text-xs font-bold block" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                      Reunión Entre Semana (Faros / Oración)
                    </span>
                    <p className="text-xs mt-0.5" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                      {sede.midweek || "Miércoles: 7:00 PM (Faros en Casa y Oración)"}
                    </p>
                  </div>
                </div>

                {/* FaroKids */}
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg shrink-0 mt-0.5" style={{ background: "rgba(245, 158, 11, 0.12)", color: "#d97706" }}>
                    <Baby size={16} />
                  </div>
                  <div>
                    <span className="text-xs font-bold block" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                      FaroKids (Ministerio Infantil)
                    </span>
                    <p className="text-xs mt-0.5" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                      {sede.farokids_schedule || "Disponible en todos los cultos dominicales (aulas por edades)"}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Dirección y Ubicación Física */}
            <div
              className="p-5 rounded-2xl border space-y-3"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-2xs font-extrabold uppercase tracking-wider" style={{ color: "var(--site-primary, #2563eb)" }}>
                  Dirección
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-lg border transition-all hover:bg-black/5"
                  style={{
                    borderColor: "var(--site-outline-variant, rgba(0,0,0,0.15))",
                    color: "var(--site-primary, #2563eb)",
                  }}
                >
                  {copied ? (
                    <>
                      <Check size={13} className="text-emerald-600" />
                      <span>Copiada</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copiar dirección</span>
                    </>
                  )}
                </button>
              </div>

              <p className="text-sm font-medium leading-relaxed" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                {fullAddress}
              </p>

              {sede.phone && (
                <div className="pt-2 border-t flex items-center gap-2 text-xs font-semibold" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.06))", color: "var(--site-on-surface-variant, #475569)" }}>
                  <Phone size={14} style={{ color: "var(--site-primary, #2563eb)" }} />
                  <a href={`tel:${sede.phone}`} className="hover:underline">
                    {sede.phone}
                  </a>
                </div>
              )}
            </div>

            {/* Botones de Acción Directa */}
            <div className="pt-2 flex flex-col gap-3">
              <a
                href={googleMapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-3 px-4 rounded-xl font-bold text-sm tracking-wide shadow-md transition-all flex items-center justify-center gap-2 hover:opacity-95 hover:scale-[1.01]"
                style={{
                  background: "var(--site-primary, #2563eb)",
                  color: "var(--site-on-primary, #ffffff)",
                }}
              >
                <Navigation size={16} />
                <span>Cómo Llegar (Google Maps)</span>
                <ExternalLink size={14} className="opacity-70 ml-0.5" />
              </a>

              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-3 px-4 rounded-xl font-bold text-sm tracking-wide border shadow-sm transition-all flex items-center justify-center gap-2 hover:bg-emerald-50 hover:border-emerald-600"
                style={{
                  background: "rgba(16, 185, 129, 0.08)",
                  borderColor: "rgba(16, 185, 129, 0.4)",
                  color: "#059669",
                }}
              >
                <MessageCircle size={17} />
                <span>Escribir por WhatsApp a esta Sede</span>
              </a>

              <button
                type="button"
                onClick={onClose}
                className="w-full py-2.5 px-4 rounded-xl font-bold text-xs uppercase tracking-wider transition-colors hover:bg-black/5"
                style={{
                  color: "var(--site-on-surface-variant, #64748b)",
                }}
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
