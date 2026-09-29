"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Calendar, Clock, MapPin, Users, HeartHandshake, CheckCircle2, Download, Loader2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { apiFetch } from "@/lib/http";

export interface PublicMeetingEvent {
  id: string;
  nombre: string;
  slug?: string;
  typology?: string;
  categoria_pastoral?: string;
  descripcion?: string;
  dia_reunion?: string;
  hora_reunion?: string;
  next_datetime?: string;
  next_date?: string;
  imagen_url?: string;
  sede?: {
    id: string;
    nombre: string;
    ciudad: string;
  } | null;
  lugar?: string;
}

interface PublicEventRegisterDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  event: PublicMeetingEvent | null;
}

export default function PublicEventRegisterDrawer({
  isOpen,
  onClose,
  event,
}: PublicEventRegisterDrawerProps) {
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [telefono, setTelefono] = useState("");
  const [asistentesCount, setAsistentesCount] = useState(1);
  const [peticionOracion, setPeticionOracion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const nameInputRef = useRef<HTMLInputElement>(null);

  // Reset form when drawer opens with a new event
  useEffect(() => {
    if (isOpen) {
      setConfirmed(false);
      setNombre("");
      setEmail("");
      setTelefono("");
      setAsistentesCount(1);
      setPeticionOracion("");
      setTimeout(() => {
        nameInputRef.current?.focus();
      }, 150);
    }
  }, [isOpen, event?.id]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !event) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim()) {
      toast.error("Por favor ingresa tu nombre completo.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiFetch(`/evangelism/public/strategies/${event.id}/register`, {
        method: "POST",
        body: {
          nombre: nombre.trim(),
          email: email.trim() || undefined,
          telefono: telefono.trim() || undefined,
          asistentes_count: asistentesCount,
          peticion_oracion: peticionOracion.trim() || undefined,
        },
      });

      setConfirmed(true);
      toast.success("¡Tu asistencia ha sido confirmada con éxito! Te esperamos.");
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Error al registrar asistencia";
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDownloadSingleIcs = () => {
    const startIso = event.next_datetime ? new Date(event.next_datetime) : new Date();
    const endIso = new Date(startIso.getTime() + 90 * 60 * 1000); // 1.5 horas
    const formatDate = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

    const icsContent = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Comunidad Cristiana El Faro//Reunion Oficial//ES",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      "BEGIN:VEVENT",
      `UID:${event.id}-${Date.now()}@ccf.org`,
      `DTSTAMP:${formatDate(new Date())}`,
      `DTSTART:${formatDate(startIso)}`,
      `DTEND:${formatDate(endIso)}`,
      `SUMMARY:${event.nombre} - Comunidad Cristiana El Faro`,
      `DESCRIPTION:${event.descripcion || "Reunión de edificación y compañerismo en Comunidad Cristiana El Faro."}`,
      `LOCATION:${event.lugar || "Comunidad Cristiana El Faro"}`,
      "STATUS:CONFIRMED",
      "END:VEVENT",
      "END:VCALENDAR",
    ].join("\r\n");

    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${event.slug || "reunion"}-ccf.ics`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Evento agregado a tu archivo de calendario (.ics)");
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        />

        {/* Drawer Panel */}
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
            <div>
              <span
                className="text-xs font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full"
                style={{
                  background: "var(--site-primary-container, rgba(37,99,235,0.1))",
                  color: "var(--site-primary, #2563eb)",
                }}
              >
                {event.categoria_pastoral || "Reunión Pastoral"}
              </span>
              <h2 id="drawer-title" className="text-xl font-bold mt-1 tracking-tight">
                {confirmed ? "¡Te Esperamos!" : "Confirmar Asistencia"}
              </h2>
            </div>
            <button
              onClick={onClose}
              aria-label="Cerrar panel de asistencia"
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
            {/* Event Summary Card */}
            <div
              className="p-4 rounded-xl border space-y-3"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <h3 className="font-bold text-lg" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                {event.nombre}
              </h3>
              {event.descripcion && (
                <p className="text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                  {event.descripcion}
                </p>
              )}

              <div className="pt-2 border-t space-y-2 text-sm" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.06))" }}>
                {event.dia_reunion && (
                  <div className="flex items-center gap-2" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    <Calendar size={16} className="text-primary shrink-0" style={{ color: "var(--site-primary, #2563eb)" }} />
                    <span className="font-medium">
                      {event.dia_reunion} {event.hora_reunion ? `a las ${event.hora_reunion} hrs` : ""}
                    </span>
                  </div>
                )}
                {event.next_datetime && (
                  <div className="flex items-center gap-2" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    <Clock size={16} className="text-primary shrink-0" style={{ color: "var(--site-primary, #2563eb)" }} />
                    <span>
                      Próxima fecha:{" "}
                      <strong className="capitalize">
                        {new Date(event.next_datetime).toLocaleDateString("es-ES", {
                          weekday: "long",
                          day: "numeric",
                          month: "long",
                        })}
                      </strong>
                    </span>
                  </div>
                )}
                {event.lugar && (
                  <div className="flex items-center gap-2" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    <MapPin size={16} className="text-primary shrink-0" style={{ color: "var(--site-primary, #2563eb)" }} />
                    <span>
                      {event.lugar}{" "}
                      <Link
                        href="/sedes"
                        className="underline text-xs font-semibold ml-1"
                        style={{ color: "var(--site-primary, #2563eb)" }}
                        onClick={onClose}
                      >
                        Ver detalles de sedes
                      </Link>
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Form or Confirmation View */}
            {!confirmed ? (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1">
                  <label className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    Nombre completo *
                  </label>
                  <input
                    ref={nameInputRef}
                    type="text"
                    required
                    value={nombre}
                    onChange={(e) => setNombre(e.target.value)}
                    placeholder="Ej. Juan Pérez"
                    className="w-full px-4 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 transition-all"
                    style={{
                      background: "var(--site-surface-1, #ffffff)",
                      borderColor: "var(--site-outline-variant, #cbd5e1)",
                      color: "var(--site-on-surface, #1e1f21)",
                    }}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                      Teléfono / WhatsApp
                    </label>
                    <input
                      type="tel"
                      value={telefono}
                      onChange={(e) => setTelefono(e.target.value)}
                      placeholder="Ej. +52 81 1234 5678"
                      className="w-full px-4 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: "var(--site-surface-1, #ffffff)",
                        borderColor: "var(--site-outline-variant, #cbd5e1)",
                        color: "var(--site-on-surface, #1e1f21)",
                      }}
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                      Correo Electrónico
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="correo@ejemplo.com"
                      className="w-full px-4 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 transition-all"
                      style={{
                        background: "var(--site-surface-1, #ffffff)",
                        borderColor: "var(--site-outline-variant, #cbd5e1)",
                        color: "var(--site-on-surface, #1e1f21)",
                      }}
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold uppercase tracking-wider flex items-center justify-between" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    <span>Número de personas que asistirán</span>
                    <span className="font-semibold" style={{ color: "var(--site-primary, #2563eb)" }}>
                      {asistentesCount} {asistentesCount === 1 ? "asistente" : "asistentes"}
                    </span>
                  </label>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={1}
                      max={10}
                      value={asistentesCount}
                      onChange={(e) => setAsistentesCount(parseInt(e.target.value, 10))}
                      className="w-full accent-primary cursor-pointer"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                    <HeartHandshake size={14} style={{ color: "var(--site-primary, #2563eb)" }} />
                    <span>Petición de oración o mensaje pastoral (opcional)</span>
                  </label>
                  <textarea
                    rows={3}
                    value={peticionOracion}
                    onChange={(e) => setPeticionOracion(e.target.value)}
                    placeholder="Escribe aquí si tienes una petición especial de oración o alguna consulta..."
                    className="w-full px-4 py-2.5 rounded-lg border text-sm focus:outline-none focus:ring-2 transition-all resize-none"
                    style={{
                      background: "var(--site-surface-1, #ffffff)",
                      borderColor: "var(--site-outline-variant, #cbd5e1)",
                      color: "var(--site-on-surface, #1e1f21)",
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-3 px-4 rounded-xl font-bold text-sm tracking-wide shadow-md transition-all flex items-center justify-center gap-2 hover:opacity-95 disabled:opacity-50"
                  style={{
                    background: "var(--site-primary, #2563eb)",
                    color: "var(--site-on-primary, #ffffff)",
                  }}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      <span>Registrando asistencia...</span>
                    </>
                  ) : (
                    <span>Confirmar mi Asistencia</span>
                  )}
                </button>
              </form>
            ) : (
              <div className="text-center py-6 space-y-5">
                <div
                  className="w-16 h-16 mx-auto rounded-full flex items-center justify-center shadow-lg"
                  style={{
                    background: "var(--site-primary-container, rgba(37,99,235,0.15))",
                    color: "var(--site-primary, #2563eb)",
                  }}
                >
                  <CheckCircle2 size={36} />
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                    ¡Registro Confirmado!
                  </h3>
                  <p className="text-sm leading-relaxed max-w-sm mx-auto" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                    ¡Muchas gracias, <strong>{nombre}</strong>! Tu lugar para <strong>{event.nombre}</strong> ha sido
                    reservado con éxito. Nos llena de gozo poder recibirte.
                  </p>
                </div>

                <div className="pt-4 flex flex-col gap-3">
                  <button
                    onClick={handleDownloadSingleIcs}
                    className="w-full py-2.5 px-4 rounded-xl font-semibold text-sm border flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
                    style={{
                      borderColor: "var(--site-primary, #2563eb)",
                      color: "var(--site-primary, #2563eb)",
                      background: "var(--site-primary-container, rgba(37,99,235,0.06))",
                    }}
                  >
                    <Download size={16} />
                    <span>Guardar en mi Calendario (.ics)</span>
                  </button>

                  <button
                    onClick={onClose}
                    className="w-full py-2.5 px-4 rounded-xl font-bold text-sm transition-all hover:opacity-90"
                    style={{
                      background: "var(--site-surface-container-high, #e2e8f0)",
                      color: "var(--site-on-surface, #1e1f21)",
                    }}
                  >
                    Cerrar
                  </button>
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
