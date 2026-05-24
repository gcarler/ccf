"use client";

import React, { useState, useMemo } from "react";

import Image from "next/image";
import { Bell, ChevronLeft, ChevronRight, MapPin, Star, CalendarDays } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { FARO_EVENTS_BLOCK_KEY } from "@/lib/cms/blocks";

interface PublicEventItem {
    title?: string;
    date?: string;
    location?: string;
    excerpt?: string;
    category?: string;
    featured?: boolean;
    status?: string;
    img?: string;
}

interface CalendarDay {
    n: number;
    prev: boolean;
    event?: boolean;
}

const CATEGORY_FILTERS = [
    "Todos",
    "Conferencias",
    "Grupos de Conexión",
    "Cursos & Talleres",
    "Especiales",
];

function formatMonthDay(date?: string) {
    if (!date) return { month: "", day: "" };
    const parts = date.trim().split(/\s+/);
    return {
        day: parts[0] ?? "",
        month: parts[2] ?? "",
    };
}

export default function EventosPage() {
    const { data: heroContent } = useContentBlock("faro_events_hero");
    const { data: eventsContent } = useContentBlock(FARO_EVENTS_BLOCK_KEY);
    const [activeFilter, setActiveFilter] = useState("Todos");
    const [reserveModal, setReserveModal] = useState<PublicEventItem | null>(null);
    const [calendarView, setCalendarView] = useState<"Semanal" | "Mensual" | "Anual">("Mensual");
    const [currentMonth, setCurrentMonth] = useState(5); // June (0-indexed)
    const [currentYear, setCurrentYear] = useState(2026);

    const heroEyebrow = heroContent?.eyebrow || "Calendario de Comunidad";
    const heroTitle = heroContent?.title || "Nuestra Agenda";
    const heroDescription =
        heroContent?.description ||
        "Espacios diseñados para el crecimiento, la conexión y la guía espiritual.";

    const parsedEvents = Array.isArray(eventsContent?.parsed)
        ? (eventsContent?.parsed as PublicEventItem[]).filter((event) => event.status !== "archived")
        : [];

    const filteredEvents = useMemo(() => {
        if (activeFilter === "Todos") return parsedEvents;
        return parsedEvents.filter((e) => e.category === activeFilter);
    }, [parsedEvents, activeFilter]);

    const featuredEvent = filteredEvents.find((event) => event.featured) || filteredEvents[0];
    const upcomingEvent = filteredEvents[1];
    const upcomingCards = filteredEvents;
    const hasEvents = filteredEvents.length > 0;

    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

    // Build dynamic calendar from events
    const eventDays = useMemo(() => {
        const days = new Set<number>();
        filteredEvents.forEach((e) => {
            if (e.date) {
                const match = e.date.match(/(\d{1,2})\s/);
                if (match) days.add(parseInt(match[1], 10));
            }
        });
        return days;
    }, [filteredEvents]);

    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const firstDayOfWeek = new Date(currentYear, currentMonth, 1).getDay();
    const prevMonthDays = new Date(currentYear, currentMonth, 0).getDate();

    const calendarDays: CalendarDay[] = [
        ...Array.from({ length: firstDayOfWeek }, (_, i) => ({
            n: prevMonthDays - firstDayOfWeek + i + 1,
            prev: true,
        })),
        ...Array.from({ length: daysInMonth }, (_, i) => ({
            n: i + 1,
            prev: false,
            event: eventDays.has(i + 1),
        })),
    ];

    return (
        <main className="pt-[88px] pb-4 px-3 md:px-4">
            <header className="mb-14 pt-12 md:grid md:grid-cols-12 gap-3 items-end">
                <div className="md:col-span-8">
                    <span
                        className="text-xs font-semibold uppercase tracking-wide mb-4 block"
                        style={{ color: "var(--faro-secondary)" }}
                    >
                        {heroEyebrow}
                    </span>
                    <h1
                        className="font-bold tracking-tighter leading-tight"
                        style={{
                            fontSize: "clamp(2.5rem, 6vw, 5rem)",
                            color: "var(--faro-on-surface)",
                        }}
                    >
                        {heroTitle}
                    </h1>
                </div>
                <div className="md:col-span-4 mt-3 md:mt-0">
                    <p style={{ color: "var(--faro-on-surface-variant)" }}>{heroDescription}</p>
                </div>
            </header>

            <section className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-16">
                <div
                    className="md:col-span-2 relative h-[440px] rounded-lg overflow-hidden group"
                    style={{ background: "var(--faro-surface-container)" }}
                >
                    {featuredEvent?.img ? (
                        <Image
                            src={featuredEvent.img}
                            alt={featuredEvent.title || "Evento destacado"}
                            fill
                            className="object-cover transition-transform duration-700 group-hover:scale-105"
                            style={{ opacity: 0.5 }}
                        />
                    ) : (
                        <div
                            className="absolute inset-0"
                            style={{
                                background:
                                    "linear-gradient(135deg, var(--faro-primary-container), var(--faro-surface-container-high))",
                            }}
                        />
                    )}
                    <div
                        className="absolute inset-0"
                        style={{
                            background:
                                "linear-gradient(to top, var(--faro-surface-container-lowest) 0%, transparent 60%)",
                        }}
                    />
                    {featuredEvent ? (
                        <div className="absolute bottom-0 p-4 w-full">
                            <div className="flex items-center gap-2 mb-4">
                                <span
                                    className="px-3 py-1 rounded-full font-semibold tracking-wide uppercase"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    Destacado
                                </span>
                                {featuredEvent.date ? (
                                    <span
                                        className="text-xs font-bold"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        {featuredEvent.date}
                                    </span>
                                ) : null}
                            </div>
                            <h2
                                className="text-xl font-bold mb-4"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                {featuredEvent.title || "Evento destacado"}
                            </h2>
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={() => {
                                        if (featuredEvent) {
                                            toast.success(`Reserva iniciada para "${featuredEvent.title}"`);
                                        }
                                    }}
                                    className="px-4 py-1.5 rounded-md font-black text-sm uppercase tracking-wide text-white transition-all hover:scale-105"
                                    style={{
                                        background:
                                            "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    }}
                                >
                                    Reservar lugar
                                </button>
                                {featuredEvent.location ? (
                                    <span
                                        className="flex items-center gap-2 text-sm font-bold"
                                        style={{ color: "var(--faro-primary)" }}
                                    >
                                        <MapPin size={16} /> {featuredEvent.location}
                                    </span>
                                ) : null}
                            </div>
                        </div>
                    ) : (
                        <div className="absolute inset-0 flex items-center justify-center p-4">
                            <div
                                className="max-w-md rounded-lg p-4 text-center"
                                style={{ background: "var(--faro-overlay-bg)", backdropFilter: "blur(12px)" }}
                            >
                                <p
                                    className="text-[10px] font-semibold uppercase tracking-wide mb-3"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    Sin eventos publicados
                                </p>
                                <h2
                                    className="text-xl font-bold mb-3"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    Esperando agenda desde el CMS
                                </h2>
                                <p
                                    className="text-sm"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    Cuando haya eventos reales publicados, apareceran aqui sin contenido simulado.
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                <div
                    className="rounded-lg p-4 flex flex-col justify-between"
                    style={{ background: "var(--faro-surface-container-low)" }}
                >
                    <div>
                        <h3
                            className="text-xl font-bold mb-3"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            Filtrar por tipo
                        </h3>
                        <div className="space-y-2">
                            {CATEGORY_FILTERS.map((cat) => (
                                <button
                                    key={cat}
                                    onClick={() => setActiveFilter(cat)}
                                    className="w-full px-4 py-1.5 rounded-md flex items-center justify-between text-sm font-bold transition-all text-left"
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
                                    {activeFilter === cat ? (
                                        <Star size={14} style={{ color: "var(--faro-primary)" }} />
                                    ) : null}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div
                        className="mt-3 pt-6"
                        style={{ borderTop: "1px solid var(--faro-outline-variant)" }}
                    >
                        <p
                            className="text-[10px] font-semibold uppercase tracking-wide mb-3"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Proximo en 48 horas
                        </p>
                        {upcomingEvent ? (
                            <div className="flex items-center gap-4">
                                <div
                                    className="w-12 h-8 rounded-lg flex items-center justify-center font-black text-lg shrink-0"
                                    style={{
                                        background: "var(--faro-primary-container)",
                                        color: "var(--faro-primary)",
                                    }}
                                >
                                    {upcomingEvent.date || "!"}
                                </div>
                                <div>
                                    <p
                                        className="text-sm font-semibold"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {upcomingEvent.title || "Proximo evento"}
                                    </p>
                                    <p
                                        className="text-xs italic"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        {upcomingEvent.location || "Sin ubicacion publicada"}
                                    </p>
                                </div>
                            </div>
                        ) : (
                            <p className="text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                                Sin eventos proximos publicados.
                            </p>
                        )}
                    </div>
                </div>
            </section>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-20">
                {hasEvents ? (
                    upcomingCards.map((event) => {
                        const { month, day } = formatMonthDay(event.date);
                        return (
                            <article
                                key={`${event.title || "event"}-${event.date || "date"}`}
                                className="rounded-lg overflow-hidden group transition-transform hover:-translate-y-1"
                                style={{ background: "var(--faro-surface-container-low)" }}
                            >
                                <div className="h-52 relative overflow-hidden">
                                    {event.img ? (
                                        <Image
                                            src={event.img}
                                            alt={event.title || "Evento"}
                                            fill
                                            className="object-cover transition-transform duration-500 group-hover:scale-110"
                                        />
                                    ) : (
                                        <div
                                            className="absolute inset-0"
                                            style={{
                                                background:
                                                    "linear-gradient(135deg, var(--faro-primary-container), var(--faro-surface-container-high))",
                                            }}
                                        />
                                    )}
                                    {month || day ? (
                                        <div
                                            className="absolute top-4 right-4 p-3 rounded-lg text-center min-w-[64px]"
                                            style={{
                                                background: "var(--faro-date-badge-bg)",
                                                backdropFilter: "blur(12px)",
                                            }}
                                        >
                                            {month ? (
                                                <p
                                                    className="text-[9px] font-semibold uppercase tracking-wider"
                                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                                >
                                                    {month}
                                                </p>
                                            ) : null}
                                            {day ? (
                                                <p
                                                    className="text-xl font-bold"
                                                    style={{ color: "var(--faro-primary)" }}
                                                >
                                                    {day}
                                                </p>
                                            ) : null}
                                        </div>
                                    ) : null}
                                </div>
                                <div className="p-7">
                                    <span
                                        className="text-[10px] font-semibold uppercase tracking-wide mb-2 block"
                                        style={{ color: "var(--faro-secondary)" }}
                                    >
                                        {event.category || "Evento"}
                                    </span>
                                    <h4
                                        className="font-black text-lg mb-3 group-hover:opacity-80 transition-opacity"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        {event.title || "Evento publicado"}
                                    </h4>
                                    <p
                                        className="text-sm leading-relaxed line-clamp-2"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        {event.excerpt || event.location || "Contenido real desde el CMS"}
                                    </p>
                                </div>
                            </article>
                        );
                    })
                ) : (
                    <div
                        className="md:col-span-3 rounded-lg p-4 text-center"
                        style={{ background: "var(--faro-surface-container-low)" }}
                    >
                        <p
                            className="text-[10px] font-semibold uppercase tracking-wide mb-3"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Sin eventos publicados
                        </p>
                        <h3
                            className="text-lg font-bold mb-2"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            El calendario aun no tiene contenido real
                        </h3>
                        <p className="text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                            Cuando el CMS publique eventos, apareceran aqui sin tarjetas inventadas.
                        </p>
                    </div>
                )}
            </div>

            <section className="mb-20">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-3 gap-4">
                    <div>
                        <h2
                            className="text-xl font-bold tracking-tight"
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
                        className="inline-flex p-1 rounded-lg"
                        style={{ background: "var(--faro-surface-container-high)" }}
                    >
                        {(["Semanal", "Mensual", "Anual"] as const).map((value) => (
                            <button
                                key={value}
                                onClick={() => setCalendarView(value)}
                                className="px-3 py-2 rounded-lg text-xs font-bold tracking-wide uppercase transition-all"
                                style={
                                    calendarView === value
                                        ? {
                                              background: "var(--faro-primary)",
                                              color: "var(--faro-on-primary)",
                                          }
                                        : { color: "var(--faro-on-surface-variant)" }
                                }
                            >
                                {value}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                    <div
                        className="lg:col-span-8 rounded-lg p-3 md:p-4"
                        style={{
                            background: "var(--faro-surface-container-low)",
                            border: "1px solid var(--faro-outline-variant)",
                        }}
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-4">
                                <h3
                                    className="text-lg font-bold"
                                    style={{ color: "var(--faro-on-surface)" }}
                                >
                                    {monthNames[currentMonth]} {currentYear}
                                </h3>
                                <div className="flex gap-1">
                                    <button
                                        onClick={() => {
                                            if (currentMonth === 0) { setCurrentMonth(11); setCurrentYear((y) => y - 1); }
                                            else setCurrentMonth((m) => m - 1);
                                        }}
                                        className="w-8 h-8 rounded-md flex items-center justify-center transition-colors hover:scale-110"
                                        style={{
                                            background: "var(--faro-surface-container)",
                                            color: "var(--faro-on-surface)",
                                        }}
                                    >
                                        <ChevronLeft size={16} />
                                    </button>
                                    <button
                                        onClick={() => {
                                            if (currentMonth === 11) { setCurrentMonth(0); setCurrentYear((y) => y + 1); }
                                            else setCurrentMonth((m) => m + 1);
                                        }}
                                        className="w-8 h-8 rounded-md flex items-center justify-center transition-colors hover:scale-110"
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
                                onClick={() => { setCurrentMonth(new Date().getMonth()); setCurrentYear(new Date().getFullYear()); }}
                                className="text-xs font-semibold uppercase tracking-wide"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                HOY
                            </button>
                        </div>

                        <div className="grid grid-cols-7 gap-1 mb-2">
                            {["Dom", "Lun", "Mar", "Mie", "Jue", "Vie", "Sab"].map((day) => (
                                <div
                                    key={day}
                                    className="text-center py-2 text-[10px] font-semibold uppercase tracking-wide"
                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                >
                                    {day}
                                </div>
                            ))}
                        </div>

                        <div className="grid grid-cols-7 gap-1">
                            {calendarDays.map((day, index) => (
                                <div
                                    key={index}
                                    className="aspect-square p-1 flex flex-col items-center justify-between rounded-md cursor-pointer transition-all hover:scale-105"
                                    style={
                                        day.n === 24 && !day.prev
                                            ? {
                                                  background: "var(--faro-card-highlight)",
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
                                    {day.event ? (
                                        <div
                                            className="w-1.5 h-1.5 rounded-full"
                                            style={{ background: "var(--faro-primary)" }}
                                        />
                                    ) : null}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="lg:col-span-4 space-y-5">
                        <div
                            className="rounded-lg p-4"
                            style={{
                                background: "var(--faro-surface-container-low)",
                                border: "1px solid var(--faro-outline-variant)",
                            }}
                        >
                            <h3
                                className="text-xl font-bold mb-3 flex items-center gap-2"
                                style={{ color: "var(--faro-on-surface)" }}
                            >
                                <Star size={18} style={{ color: "var(--faro-primary)" }} />
                                Destacados
                            </h3>
                            <div className="space-y-5">
                                {hasEvents ? (
                                    parsedEvents.slice(0, 3).map((event) => (
                                        <div
                                            key={`${event.title || "event"}-${event.date || "date"}`}
                                            className="flex gap-3 group cursor-pointer"
                                        >
                                            <div
                                                className="w-2 shrink-0 rounded-full mt-1"
                                                style={{ background: "var(--faro-primary)", minHeight: "12px" }}
                                            />
                                            <div>
                                                <p
                                                    className="text-[10px] font-semibold uppercase tracking-wide mb-0.5"
                                                    style={{ color: "var(--faro-primary)" }}
                                                >
                                                    {event.category || "Evento"}
                                                    {event.date ? ` • ${event.date}` : ""}
                                                </p>
                                                <h4
                                                    className="text-sm font-semibold group-hover:opacity-70 transition-opacity"
                                                    style={{ color: "var(--faro-on-surface)" }}
                                                >
                                                    {event.title || "Evento publicado"}
                                                </h4>
                                                <p
                                                    className="text-xs line-clamp-1"
                                                    style={{ color: "var(--faro-on-surface-variant)" }}
                                                >
                                                    {event.excerpt || event.location || "Contenido real desde el CMS"}
                                                </p>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <p className="text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                                        Sin destacados publicados todavia.
                                    </p>
                                )}
                            </div>
                            <button
                                onClick={() => {
                                    const ics = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//FARO//ES\n" +
                                        filteredEvents.map((e) => `BEGIN:VEVENT\nSUMMARY:${e.title || "Evento"}\nDESCRIPTION:${e.excerpt || ""}\nEND:VEVENT`).join("\n") +
                                        "\nEND:VCALENDAR";
                                    const blob = new Blob([ics], { type: "text/calendar" });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement("a");
                                    a.href = url; a.download = "faro-eventos.ics"; a.click();
                                    URL.revokeObjectURL(url);
                                    toast.success("Calendario descargado — impórtalo en Google Calendar o Outlook");
                                }}
                                className="w-full mt-3 py-1.5 rounded-md text-xs font-semibold uppercase tracking-wide border transition-all hover:scale-105"
                                style={{
                                    borderColor: "var(--faro-primary)",
                                    color: "var(--faro-primary)",
                                }}
                            >
                                Sincronizar Calendario
                            </button>
                        </div>

                        <div
                            onClick={() => toast.info("Notificaciones de eventos próximamente — te avisaremos")}
                            className="rounded-lg p-3 flex items-center gap-4 cursor-pointer transition-all hover:scale-[1.02]"
                            style={{
                                background: "var(--faro-primary-container)",
                                border: "1px solid var(--faro-outline-variant)",
                            }}
                        >
                            <div
                                className="w-12 h-8 rounded-lg flex items-center justify-center shrink-0"
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
                                    Quieres recordatorios?
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
