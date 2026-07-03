"use client";

import React, { useMemo } from "react";
import {
  Bell,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Clock,
  Globe,
  Heart,
  Mail,
  MapPin,
  Menu,
  MessageCircle,
  Play,
  Search,
  Share2,
  Star,
  User,
  Users,
  X,
} from "lucide-react";

interface Props {
  tokens: Record<string, string>;
}

export default function ThemePreview({ tokens }: Props) {
  const css = useMemo(() => {
    const style: React.CSSProperties = {};
    Object.entries(tokens).forEach(([k, v]) => {
      (style as Record<string, string>)[k] = v;
    });
    return style;
  }, [tokens]);

  const t = (key: string, fallback: string) => tokens[key] || fallback;

  return (
    <div
      className="rounded-xl overflow-hidden border"
      style={{
        ...css,
        background: t("--site-background", "#001134"),
        color: t("--site-on-background", "#d9e2ff"),
        borderColor: t("--site-outline-variant", "#424750"),
      }}
    >
      {/* ── Mock Navbar ── */}
      <nav
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{
          background: t("--site-navbar-bg", "rgba(0,13,42,0.6)"),
          backdropFilter: "blur(20px)",
          borderColor: t("--site-navbar-border", "rgba(165,200,255,0.08)"),
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
            style={{
              background: t("--site-primary", "#a5c8ff"),
              color: t("--site-on-primary", "#00315e"),
            }}
          >
            CCF
          </div>
          <span className="text-sm font-semibold hidden sm:inline">Iglesia</span>
        </div>
        <div className="hidden md:flex items-center gap-4 text-xs font-medium opacity-70">
          <span>Inicio</span>
          <span>Nosotros</span>
          <span>Eventos</span>
          <span>Contacto</span>
        </div>
        <div className="flex items-center gap-2">
          <Search size={14} className="opacity-60" />
          <Menu size={14} className="opacity-60 md:hidden" />
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section className="relative px-6 py-10 sm:py-14 text-center overflow-hidden">
        {/* Decorative glows */}
        <div
          className="absolute top-0 left-1/4 w-64 h-64 rounded-full blur-3xl opacity-40 pointer-events-none"
          style={{ background: t("--site-glow-subtle", "rgba(165,200,255,0.08)") }}
        />
        <div
          className="absolute bottom-0 right-1/4 w-48 h-48 rounded-full blur-3xl opacity-30 pointer-events-none"
          style={{ background: t("--site-glow-intense", "rgba(165,200,255,0.3)") }}
        />

        <div className="relative z-10 max-w-lg mx-auto space-y-4">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
            style={{
              background: t("--site-hero-badge-bg", "rgba(165,200,255,0.05)"),
              border: `1px solid ${t("--site-hero-badge-border", "rgba(165,200,255,0.3)")}`,
              color: t("--site-hero-badge-color", "rgba(165,200,255,0.9)"),
            }}
          >
            <Star size={10} />
            Bienvenidos
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold leading-tight" style={{ color: t("--site-on-hero", "#ffffff") }}>
            Una comunidad de <span style={{ color: t("--site-primary", "#a5c8ff") }}>fe y esperanza</span>
          </h1>
          <p className="text-sm leading-relaxed opacity-70 max-w-sm mx-auto">
            Este es un preview en tiempo real de cómo se verán los colores, tipografía y componentes en tu sitio público.
          </p>
          <div className="flex items-center justify-center gap-3 pt-2">
            <button
              className="px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all hover:scale-105 active:scale-95"
              style={{
                background: t("--site-hero-cta-gradient", "linear-gradient(135deg,#018abd 0%,#2c609d 100%)"),
                boxShadow: t("--site-hero-cta-shadow", "0 8px 32px rgba(1,138,189,0.4)"),
                color: "#ffffff",
              }}
            >
              <Play size={12} fill="currentColor" />
              Ver sermón
            </button>
            <button
              className="px-5 py-2.5 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all hover:scale-105 active:scale-95"
              style={{
                background: t("--site-hero-bg-light", "rgba(255,255,255,0.08)"),
                border: `1px solid ${t("--site-hero-border-light", "rgba(255,255,255,0.15)")}`,
                color: t("--site-on-hero", "#ffffff"),
              }}
            >
              <Calendar size={12} />
              Eventos
            </button>
          </div>
        </div>
      </section>

      {/* ── Stats Row ── */}
      <div className="grid grid-cols-3 gap-px" style={{ background: t("--site-outline-variant", "#424750") }}>
        {[
          { icon: Users, label: "Miembros", value: "1,240" },
          { icon: Globe, label: "Países", value: "12" },
          { icon: Heart, label: "Donaciones", value: "$8.5K" },
        ].map((stat, i) => (
          <div
            key={i}
            className="flex flex-col items-center justify-center py-4 text-center"
            style={{ background: t("--site-surface-container-low", "#001944") }}
          >
            <stat.icon size={16} style={{ color: t("--site-primary", "#a5c8ff") }} className="mb-1" />
            <p className="text-sm font-bold">{stat.value}</p>
            <p className="text-[10px] uppercase tracking-wider opacity-60">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* ── Content Cards ── */}
      <div className="px-4 py-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider">Próximos eventos</h2>
          <span className="text-[10px] font-semibold uppercase tracking-wider opacity-50 flex items-center gap-1 cursor-pointer hover:opacity-80 transition-opacity">
            Ver todo <ChevronRight size={10} />
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            {
              title: "Culto de Jóvenes",
              date: "Vie, 18 Jul",
              time: "7:00 PM",
              location: "Auditorio Principal",
              tag: "Worship",
              highlight: false,
            },
            {
              title: "Conferencia Familiar",
              date: "Sáb, 19 Jul",
              time: "9:00 AM",
              location: "Centro de Convenciones",
              tag: "Especial",
              highlight: true,
            },
          ].map((evt, i) => (
            <div
              key={i}
              className="rounded-xl p-4 transition-all duration-300 hover:-translate-y-0.5"
              style={{
                background: evt.highlight
                  ? t("--site-primary-container", "#004581")
                  : t("--site-surface-container", "#021d4a"),
                border: `1px solid ${evt.highlight ? t("--site-primary", "#a5c8ff") : t("--site-outline-variant", "#424750")}`,
                boxShadow: evt.highlight ? `0 12px 32px ${t("--site-card-highlight", "rgba(165,200,255,0.15)")}` : "none",
              }}
            >
              <div className="flex items-start justify-between mb-3">
                <span
                  className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                  style={{
                    background: t("--site-hero-badge-bg", "rgba(165,200,255,0.05)"),
                    color: t("--site-primary", "#a5c8ff"),
                  }}
                >
                  {evt.tag}
                </span>
                {evt.highlight && <Heart size={12} style={{ color: t("--site-primary", "#a5c8ff") }} />}
              </div>
              <h3 className="text-sm font-bold mb-2">{evt.title}</h3>
              <div className="space-y-1.5 text-[11px] opacity-70">
                <div className="flex items-center gap-1.5">
                  <Calendar size={10} /> {evt.date}
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock size={10} /> {evt.time}
                </div>
                <div className="flex items-center gap-1.5">
                  <MapPin size={10} /> {evt.location}
                </div>
              </div>
              <button
                className="mt-3 w-full py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all hover:opacity-90"
                style={{
                  background: t("--site-cta-gradient", "linear-gradient(to right,#004581,#018abd,#004581)"),
                  boxShadow: t("--site-cta-shadow", "0 4px 20px rgba(1,138,189,0.5)"),
                  color: "#ffffff",
                }}
              >
                Registrarme
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* ── Testimonial Card (Glassmorphism) ── */}
      <div className="px-4 pb-6">
        <div
          className="rounded-xl p-5 relative overflow-hidden"
          style={{
            background: t("--site-glass-bg", "rgba(29,51,97,0.4)"),
            backdropFilter: "blur(20px)",
            border: `1px solid ${t("--site-glass-border", "rgba(165,200,255,0.1)")}`,
          }}
        >
          <div
            className="absolute -top-8 -right-8 w-24 h-24 rounded-full blur-2xl opacity-30 pointer-events-none"
            style={{ background: t("--site-primary", "#a5c8ff") }}
          />
          <MessageCircle
            size={28}
            style={{ color: t("--site-primary", "#a5c8ff") }}
            className="opacity-30 mb-3"
          />
          <p className="text-sm leading-relaxed opacity-90 italic relative z-10">
            "Este tema se ve increíble. La glassmorphism y los glows le dan un toque moderno y profesional a toda la plataforma."
          </p>
          <div className="flex items-center gap-3 mt-4 pt-4 border-t" style={{ borderColor: t("--site-outline-variant", "#424750") }}>
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold"
              style={{
                background: t("--site-primary", "#a5c8ff"),
                color: t("--site-on-primary", "#00315e"),
              }}
            >
              JD
            </div>
            <div>
              <p className="text-xs font-bold">Juan Díaz</p>
              <p className="text-[10px] opacity-60">Miembro desde 2023</p>
            </div>
            <div className="ml-auto flex gap-0.5">
              {[1, 2, 3, 4, 5].map((s) => (
                <Star key={s} size={10} fill={t("--site-primary", "#a5c8ff")} style={{ color: t("--site-primary", "#a5c8ff") }} />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Form Elements ── */}
      <div className="px-4 pb-6 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-wider">Formulario de contacto</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wider opacity-70">Nombre</label>
            <input
              readOnly
              value="María González"
              className="w-full px-3 py-2 rounded-lg text-xs outline-none transition-all"
              style={{
                background: t("--site-surface-container-high", "#1d3361"),
                border: `1px solid ${t("--site-outline-variant", "#424750")}`,
                color: t("--site-on-surface", "#d9e2ff"),
              }}
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wider opacity-70">Email</label>
            <input
              readOnly
              value="maria@email.com"
              className="w-full px-3 py-2 rounded-lg text-xs outline-none transition-all"
              style={{
                background: t("--site-surface-container-high", "#1d3361"),
                border: `1px solid ${t("--site-outline-variant", "#424750")}`,
                color: t("--site-on-surface", "#d9e2ff"),
              }}
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <label className="text-[10px] font-semibold uppercase tracking-wider opacity-70">Mensaje</label>
          <textarea
            readOnly
            rows={2}
            value="Me encantaría ser parte del equipo de voluntarios..."
            className="w-full px-3 py-2 rounded-lg text-xs outline-none resize-none transition-all"
            style={{
              background: t("--site-surface-container-high", "#1d3361"),
              border: `1px solid ${t("--site-outline-variant", "#424750")}`,
              color: t("--site-on-surface", "#d9e2ff"),
            }}
          />
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked
            readOnly
            className="w-4 h-4 rounded cursor-default"
            style={{
              accentColor: t("--site-primary", "#a5c8ff"),
            }}
          />
          <span className="text-[11px] opacity-70">Acepto recibir noticias y eventos</span>
        </div>
        <button
          className="w-full py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all hover:scale-[1.01] active:scale-[0.99]"
          style={{
            background: t("--site-cta-gradient", "linear-gradient(to right,#004581,#018abd,#004581)"),
            boxShadow: t("--site-cta-shadow", "0 4px 20px rgba(1,138,189,0.5)"),
            color: "#ffffff",
          }}
        >
          Enviar mensaje
        </button>
      </div>

      {/* ── Alerts & Badges ── */}
      <div className="px-4 pb-6 space-y-2">
        <h2 className="text-sm font-bold uppercase tracking-wider">Estados y alertas</h2>
        <div className="flex flex-wrap gap-2">
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{
              background: t("--site-primary-container", "#004581"),
              color: t("--site-primary", "#a5c8ff"),
            }}
          >
            <CheckCircle2 size={10} /> Confirmado
          </span>
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{
              background: t("--site-surface-container-high", "#1d3361"),
              color: t("--site-on-surface-variant", "#c2c6d1"),
            }}
          >
            <Clock size={10} /> Pendiente
          </span>
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{
              background: `${t("--site-error", "#ffb4ab")}20`,
              color: t("--site-error", "#ffb4ab"),
              border: `1px solid ${t("--site-error", "#ffb4ab")}40`,
            }}
          >
            <X size={10} /> Cancelado
          </span>
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
            style={{
              background: t("--site-hero-badge-bg", "rgba(165,200,255,0.05)"),
              border: `1px solid ${t("--site-hero-badge-border", "rgba(165,200,255,0.3)")}`,
              color: t("--site-hero-badge-color", "rgba(165,200,255,0.9)"),
            }}
          >
            <Bell size={10} /> Notificación
          </span>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer
        className="px-4 py-5 border-t text-center"
        style={{
          background: t("--site-surface-container-lowest", "#000d2a"),
          borderColor: t("--site-outline-variant", "#424750"),
        }}
      >
        <div className="flex items-center justify-center gap-4 mb-3">
          {[Mail, Share2, Globe, User].map((Icon, i) => (
            <div
              key={i}
              className="w-8 h-8 rounded-lg flex items-center justify-center transition-all hover:scale-110 cursor-pointer"
              style={{
                background: t("--site-surface-container", "#021d4a"),
                color: t("--site-on-surface-variant", "#c2c6d1"),
              }}
            >
              <Icon size={13} />
            </div>
          ))}
        </div>
        <p className="text-[10px] opacity-50 uppercase tracking-wider">
          Preview generado en tiempo real
        </p>
      </footer>
    </div>
  );
}
