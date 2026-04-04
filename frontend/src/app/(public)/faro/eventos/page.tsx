"use client";

import React, { useState } from "react";
import Link from "next/link";
import { MapPin, Bell, Star, ChevronLeft, ChevronRight } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";

interface PublicEventItem {
    title?: string;
    date?: string;
    location?: string;
    excerpt?: string;
    category?: string;
    featured?: boolean;
}

const EVENT_IMGS = [
    "https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=600&q=80",
    "https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=600&q=80",
    "https://images.unsplash.com/photo-1447690709975-318628b14c57?w=600&q=80",
];

const CATEGORY_FILTERS = ["Todos", "Conferencias", "Grupos de Conexión", "Cursos & Talleres", "Especiales"];

export default function EventosPage() {
    const { data: heroContent } = useContentBlock("faro_events_hero");
    const { data: eventsContent } = useContentBlock(FARO_EVENTS_BLOCK_KEY);
    const [activeFilter, setActiveFilter] = useState("Todos");

    const heroEyebrow = heroContent?.eyebrow || "Calendario de Comunidad";
    const heroTitle = heroContent?.title || "Nuestra Agenda";
    const heroDescription =
        heroContent?.description ||
        "Espacios diseñados para el crecimiento, la conexión y la guía espiritual.";

    const parsedEvents = Array.isArray(eventsContent?.parsed)
        ? (eventsContent?.parsed as PublicEventItem[])
        : [];

    const featuredEvent = parsedEvents.find((e) => e.featured) ||
        parsedEvents[0] || {
            date: "24 DE JUNIO, 2025",
            title: "Noche de Iluminación: Adoración & Palabra",
            location: "Auditorio Central",
        };

    const upcomingEvent = parsedEvents[1] || {
        date: "12",
        title: "Cena de Jóvenes",
        location: "Sede Norte • 19:30 hrs",
    };

    const upcomingCards = [
        { img: EVENT_IMGS[0], tag: "Conferencia", month: "JUL", day: "05", title: "Liderazgo Radiante", desc: "Herramientas para guiar con propósito en un mundo cambiante." },
        { img: EVENT_IMGS[1], tag: "Música", month: "JUL", day: "12", title: "Festival FARO Sound", desc: "Tarde de música en vivo y comunidad al aire libre." },
        { img: EVENT_IMGS[2], tag: "Estudio", month: "AGO", day: "02", title: "Profundidad Teológica", desc: "Taller intensivo sobre los Salmos y su aplicación hoy." },
    ];

    const calendarDays = [
        { n: 26, prev: true }, { n: 27, prev: true }, { n: 28, prev: true },
        { n: 29, prev: true }, { n: 30, prev: true }, { n: 31, prev: true },
        ...Array.from({ length: 29 }, (_, i) => ({ n: i + 1, prev: false, event: [2, 5, 12, 24].includes(i + 1) })),
    ];

    return (
        <main className="pt-[88px] pb-20 px-6 md:px-12 max-w-7xl mx-auto">
            {/* ── HERO ──────────────────────────────── */}
            <header className="mb-14 pt-12 md:grid md:grid-cols-12 gap-8 items-end">
                <div className="md:col-span-8">
                    <span
                        className="text-xs font-black uppercase tracking-[0.25em] mb-4 block"
                        style={{ color: "var(--faro-secondary)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-black tracking-tighter leading-tight"
                        style={{
                            fontSize: "clamp(2.5rem, 6vw, 5rem)",
                            color: "var(--faro-on-surface)",
                        }}
                    >
                        {heroTitle}
                    </h1>
                </div>
                <div className="md:col-span-4 mt-6 md:mt-0">
                    <p style={{ color: "var(--faro-on-surface-variant)" }}>{heroDescription}</p>
                </div>
            </header>

            {/* ── EVENTO DESTACADO + FILTROS ─────────── */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
                {/* Featured */}
                <div
                    className="md:col-span-2 relative h-[440px] rounded-3xl overflow-hidden group"
                    style={{ background: "var(--faro-surface-container)" }}
                >
                    <img
                        src="https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=900&q=80"
                        alt="Gran Evento Destacado"
                        className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
                        style={{ opacity: 0.5 }}
                    />
                    <div
                        className="absolute inset-0"
                        style={{
                            background:
                                "linear-gradient(to top, var(--faro-surface-container-lowest) 0%, transparent 60%)",
                        }}
                    />
                    <div className="absolute bottom-0 p-8 w-full">
                        <div className="flex items-center gap-2 mb-4">
                            <span
                                className="px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase"
                                style={{
                                    background: "var(--faro-primary-container)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                Destacado
                            </span>
                            <span
                                className="text-xs font-bold"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                {featuredEvent.date}
                            </span>
                        </div>
                        <h2
                            className="text-3xl font-black mb-4"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            {featuredEvent.title}
                        </h2>
                        <div className="flex items-center gap-6">
                            <button
                                className="px-8 py-3 rounded-2xl font-black text-sm uppercase tracking-widest text-white transition-all hover:scale-105"
                                style={{
                                    background:
                                        "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                }}
                            >
                                Reservar Lugar
                            </button>
                            <span
                                className="flex items-center gap-2 text-sm font-bold"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                <MapPin size={16} /> {featuredEvent.location}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Filtros + próximo */}
                <div
                    className="rounded-3xl p-8 flex flex-col justify-between"
                    style={{ background: "var(--faro-surface-container-low)" }}
                >
                    <div>
                        <h3
                            className="text-xl font-black mb-6"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            Filtrar por tipo
                        </h3>
                        <div className="space-y-2">
                            {CATEGORY_FILTERS.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => setActiveFilter(cat)}
                                    className="w-full px-4 py-3 rounded-2xl flex items-center justify-between text-sm font-bold transition-all text-left"
                                    style={{
                                        background:
                                            activeFilter === cat
                                                ? "var(--faro-primary-container)"
                                                : "var(--faro-surface-container)",
                                        color:
                                            activeFilter === cat
                                                ? "var(--faro-primary)"
                                                : "var(--faro-on-surface-variant)",
                                    }}
                                >
                                    {cat}
                                    {activeFilter === cat && (
                                        <Star size={14} style={{ color: "var(--faro-primary)" }} />
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div
                        className="mt-6 pt-6"
                        style={{ borderTop: "1px solid var(--faro-outline-variant)" }}
                    >
                        <p
                            className="text-[10px] font-black uppercase tracking-[0.2em] mb-3"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Próximo en 48 horas
                        </p>
                        <div className="flex items-center gap-4">
                            <div
                                className="w-12 h-12 rounded-2xl flex items-center justify-center font-black text-lg shrink-0"
                                style={{
                                    background: "var(--faro-primary-container)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                {upcomingEvent.date}
                            </div>
                            <div>
                                <p
                                    className="text-sm font-black"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {upcomingEvent.title}
                                </p>
                                <p
                                    className="text-xs italic"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {upcomingEvent.location}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── TARJETAS DE EVENTOS ─────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-20">
                {upcomingCards.map(({ img, tag, month, day, title, desc }) => (
                    <article
                        key={title}
                        className="rounded-3xl overflow-hidden group transition-transform hover:-translate-y-1"
                        style={{ background: "var(--faro-surface-container-low)" }}
                    >
                        <div className="h-52 relative overflow-hidden">
                            <img
                                src={img}
                                alt={title}
                                className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                            />
                            <div
                                className="absolute top-4 right-4 p-3 rounded-2xl text-center min-w-[64px]"
                                style={{
                                    background: "rgba(0,13,42,0.8)",
                                    backdropFilter: "blur(12px)",
                                }}
                            >
                                <p
                                    className="text-[9px] font-black uppercase tracking-wider"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {month}
                                </p>
                                <p
                                    className="text-xl font-black"
                                    style={{ color: "var(--faro-primary)" }}
                                >
                                    {day}
                                </p>
                            </div>
                        </div>
                        <div className="p-7">
                            <span
                                className="text-[10px] font-black uppercase tracking-widest mb-2 block"
                                style={{ color: "var(--faro-secondary)" }}
                            >
                                {tag}
                            </span>
                            <h4
                                className="font-black text-lg mb-3 group-hover:opacity-80 transition-opacity"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                {title}
                            </h4>
                            <p
                                className="text-sm leading-relaxed line-clamp-2"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                {desc}
                            </p>
                        </div>
                    </article>
                ))}
            </div>

            {/* ── CALENDARIO ──────────────────────────── */}
            <section className="mb-20">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                    <div>
                        <h2
                            className="text-3xl font-black tracking-tight"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            Explora nuestro Calendario
                        </h2>
                        <p
                            className="text-sm mt-1"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Organiza tu tiempo con nuestras actividades comunitarias.
                        </p>
                    </div>
                    <div
                        className="inline-flex p-1 rounded-2xl"
                        style={{ background: "var(--faro-surface-container-high)" }}
                    >
                        {["Semanal", "Mensual", "Anual"].map((v) => (
                            <button
                                key={v}
                                className="px-6 py-2 rounded-2xl text-xs font-black tracking-widest uppercase transition-all"
                                style={
                                    v === "Mensual"
                                        ? {
                                            background: "var(--faro-primary)",
                                            color: "var(--faro-on-primary)",
                                        }
                                        : { color: "var(--faro-on-surface-variant)" }
                                }
                            >
                                {v}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                    {/* Calendar grid */}
                    <div
                        className="lg:col-span-8 rounded-3xl p-6 md:p-10"
                        style={{
                            background: "var(--faro-surface-container-low)",
                            border: "1px solid var(--faro-outline-variant)",
                        }}
                    >
                        <div className="flex items-center justify-between mb-8">
                            <div className="flex items-center gap-4">
                                <h3
                                    className="text-2xl font-black"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    Junio 2025
                                </h3>
                                <div className="flex gap-1">
                                    <button
                                        className="w-8 h-8 rounded-xl flex items-center justify-center transition-colors hover:scale-110"
                                        style={{
                                            background: "var(--faro-surface-container)",
                                            color: "var(--faro-on-surface)",
                                        }}
                                    >
                                        <ChevronLeft size={16} />
                                    </button>
                                    <button
                                        className="w-8 h-8 rounded-xl flex items-center justify-center transition-colors hover:scale-110"
                                        style={{
                                            background: "var(--faro-surface-container)",
                                            color: "var(--faro-on-surface)",
                                        }}
                                    >
                                        <ChevronRight size={16} />
                                    </button>
                                </div>
                            </div>
                            <button
                                className="text-xs font-black uppercase tracking-widest"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                HOY
                            </button>
                        </div>
                        {/* Day headers */}
                        <div className="grid grid-cols-7 gap-1 mb-2">
                            {["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"].map((d) => (
                                <div
                                    key={d}
                                    className="text-center py-2 text-[10px] font-black uppercase tracking-widest"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {d}
                                </div>
                            ))}
                        </div>
                        {/* Days */}
                        <div className="grid grid-cols-7 gap-1">
                            {calendarDays.map((day, i) => (
                                <div
                                    key={i}
                                    className="aspect-square p-1 flex flex-col items-center justify-between rounded-xl cursor-pointer transition-all hover:scale-105"
                                    style={
                                        day.n === 24 && !day.prev
                                            ? {
                                                background: "rgba(44,96,157,0.2)",
                                                border: "2px solid var(--faro-primary)",
                                            }
                                            : day.prev
                                            ? { opacity: 0.2 }
                                            : { background: "transparent" }
                                    }
                                >
                                    <span
                                        className="text-sm font-bold"
                                        style={{
                                            color:
                                                day.n === 24 && !day.prev
                                                    ? "var(--faro-primary)"
                                                    : "var(--faro-on-surface)",
                                        }}
                                    >
                                        {day.n}
                                    </span>
                                    {(day as any).event && (
                                        <div
                                            className="w-1.5 h-1.5 rounded-full"
                                            style={{ background: "var(--faro-primary)" }}
                                        />
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Sidebar upcoming */}
                    <div className="lg:col-span-4 space-y-5">
                        <div
                            className="rounded-3xl p-8"
                            style={{
                                background: "var(--faro-surface-container-low)",
                                border: "1px solid var(--faro-outline-variant)",
                            }}
                        >
                            <h3
                                className="text-xl font-black mb-6 flex items-center gap-2"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                <Star size={18} style={{ color: "var(--faro-primary)" }} />
                                Destacados
                            </h3>
                            <div className="space-y-5">
                                {[
                                    { tag: "Música • 12 JUN", title: "Festival FARO Sound", desc: "Música en vivo en Sede Jardín.", color: "var(--faro-secondary)" },
                                    { tag: "Especial • 24 JUN", title: "Noche de Iluminación", desc: "Adoración y Palabra profética.", color: "var(--faro-primary)" },
                                    { tag: "Semanal • Domingos", title: "Reuniones Generales", desc: "09:00, 11:00 y 18:00 hrs.", color: "var(--faro-on-surface-variant)" },
                                ].map(({ tag, title, desc, color }) => (
                                    <div key={title} className="flex gap-3 group cursor-pointer">
                                        <div
                                            className="w-2 shrink-0 rounded-full mt-1"
                                            style={{ background: color, minHeight: "12px" }}
                                        />
                                        <div>
                                            <p
                                                className="text-[10px] font-black uppercase tracking-widest mb-0.5"
                                                style={{ color }}
                                            >
                                                {tag}
                                            </p>
                                            <h4
                                                className="text-sm font-black group-hover:opacity-70 transition-opacity"
                                                style={{ color: "var(--faro-on-surface)" }}
                                            >
                                                {title}
                                            </h4>
                                            <p
                                                className="text-xs line-clamp-1"
                                                style={{ color: "var(--faro-on-surface-variant)" }}
                                            >
                                                {desc}
                                            </p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <button
                                className="w-full mt-8 py-3 rounded-2xl text-xs font-black uppercase tracking-widest border transition-all hover:scale-105"
                                style={{
                                    borderColor: "var(--faro-primary)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                Sincronizar Calendario
                            </button>
                        </div>

                        <div
                            className="rounded-3xl p-6 flex items-center gap-4"
                            style={{
                                background: "var(--faro-primary-container)",
                                border: "1px solid var(--faro-outline-variant)",
                            }}
                        >
                            <div
                                className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
                                style={{
                                    background: "var(--faro-primary)",
                                    color: "var(--faro-on-primary)",
                                }}
                            >
                                <Bell size={20} />
                            </div>
                            <div>
                                <h4
                                    className="font-black text-sm"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    ¿Quieres recordatorios?
                                </h4>
                                <p
                                    className="text-xs"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    Recibe avisos de tus eventos favoritos.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </main>
    );
}
