"use client";

import { useCallback, useMemo, useState, useEffect } from "react";
import Link from "next/link";
import {
  Calendar as CalendarIcon,
  Clock,
  MapPin,
  Download,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Heart,
  CheckCircle2,
  CalendarDays,
  BookmarkPlus,
} from "lucide-react";
import { toast } from "sonner";

import { apiFetch } from "@/lib/http";
import PublicHeroWithSlides from "@/components/public/PublicHeroWithSlides";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import PublicEventRegisterDrawer, {
  type PublicMeetingEvent,
} from "@/components/public/PublicEventRegisterDrawer";

interface CalendarDayInfo {
  dayNumber: number;
  date: Date;
  isCurrentMonth: boolean;
  isToday: boolean;
  events: PublicMeetingEvent[];
}

export default function EventosPage() {
  // Set explicit SEO document title
  useEffect(() => {
    document.title = "Eventos y Calendario | Comunidad Cristiana El Faro (CCF)";
  }, []);

  const heroPage = useCmsV2Page("events");
  const heroContent = heroPage?.blocks?.hero as Record<string, unknown> | undefined;

  const [publicMeetings, setPublicMeetings] = useState<PublicMeetingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeCategory, setActiveCategory] = useState<string>("Todas");

  // Calendar State
  const today = useMemo(() => new Date(), []);
  const [currentMonth, setCurrentMonth] = useState(today.getMonth());
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [selectedDay, setSelectedDay] = useState<Date>(today);

  // Drawer State
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedEventForDrawer, setSelectedEventForDrawer] = useState<PublicMeetingEvent | null>(null);

  // Fetch enriched public events from backend
  useEffect(() => {
    setLoading(true);
    apiFetch<PublicMeetingEvent[]>("/evangelism/public/upcoming-events", { silent: true })
      .then((data) => {
        if (Array.isArray(data)) {
          setPublicMeetings(data);
        }
      })
      .catch((err) => {
        console.error("Error fetching public upcoming events:", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  // Hero section contents
  const heroEyebrow =
    typeof heroContent?.eyebrow === "string" && heroContent.eyebrow
      ? heroContent.eyebrow
      : "Comunidad Cristiana El Faro";
  const heroTitle =
    typeof heroContent?.title === "string" && heroContent.title
      ? heroContent.title
      : "Reuniones Semanales y Próximos Eventos";
  const heroDescription =
    typeof heroContent?.description === "string" && heroContent.description
      ? heroContent.description
      : "Te invitamos a ser parte de nuestra familia de fe. Conoce nuestros horarios de adoración, grupos en hogares y encuentros especiales para toda la familia.";

  const heroSlides = useMemo(() => {
    return [
      {
        src: "/images/events/escuela-dominical.jpg",
        alt: "Culto y Escuela Dominical",
        title: "Escuela Dominical y Culto de Adoración",
        caption: "Cada domingo en Sede Norte y sedes filiales",
      },
      {
        src: "/images/events/faros-en-casa.jpg",
        alt: "Faros en Casa",
        title: "Faros en Casa: Grupos de Hogar",
        caption: "Cada miércoles a las 19:30 hrs",
      },
    ];
  }, []);

  // Categories list
  const categories = useMemo(() => {
    const set = new Set<string>();
    publicMeetings.forEach((m) => {
      if (m.categoria_pastoral) set.add(m.categoria_pastoral);
    });
    return ["Todas", ...Array.from(set)];
  }, [publicMeetings]);

  // Filtered meetings
  const filteredMeetings = useMemo(() => {
    if (activeCategory === "Todas") return publicMeetings;
    return publicMeetings.filter((m) => m.categoria_pastoral === activeCategory);
  }, [publicMeetings, activeCategory]);

  // Calendar logic: synchronize real weekly church meetings
  // Wednesdays = Faros en Casa (19:30)
  // Sundays = Primera Escuela Dominical (06:00), Segunda Escuela Dominical (21:00)
  const getEventsForDate = useCallback((date: Date): PublicMeetingEvent[] => {
    const dayOfWeek = date.getDay(); // 0 = Domingo, 3 = Miércoles
    const ymd = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
      date.getDate()
    ).padStart(2, "0")}`;

    const matching: PublicMeetingEvent[] = [];

    publicMeetings.forEach((m) => {
      // Check explicit next_date match
      if (m.next_date === ymd) {
        matching.push(m);
        return;
      }

      // Check recurring day of week match
      const dia = (m.dia_reunion || "").toLowerCase();
      if (dayOfWeek === 3 && (dia.includes("miér") || dia.includes("mier"))) {
        matching.push(m);
      } else if (dayOfWeek === 0 && dia.includes("dom")) {
        matching.push(m);
      }
    });

    return matching;
  }, [publicMeetings]);

  // Build calendar matrix
  const calendarMatrix = useMemo(() => {
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    const firstDayOfWeek = new Date(currentYear, currentMonth, 1).getDay(); // 0=Dom..6=Sab
    const prevMonthDays = new Date(currentYear, currentMonth, 0).getDate();

    const days: CalendarDayInfo[] = [];

    // Previous month tail days
    for (let i = 0; i < firstDayOfWeek; i++) {
      const dNum = prevMonthDays - firstDayOfWeek + i + 1;
      const d = new Date(currentYear, currentMonth - 1, dNum);
      days.push({
        dayNumber: dNum,
        date: d,
        isCurrentMonth: false,
        isToday: false,
        events: getEventsForDate(d),
      });
    }

    // Current month days
    for (let i = 1; i <= daysInMonth; i++) {
      const d = new Date(currentYear, currentMonth, i);
      const isToday =
        d.getDate() === today.getDate() &&
        d.getMonth() === today.getMonth() &&
        d.getFullYear() === today.getFullYear();

      days.push({
        dayNumber: i,
        date: d,
        isCurrentMonth: true,
        isToday,
        events: getEventsForDate(d),
      });
    }

    return days;
  }, [currentMonth, currentYear, today, getEventsForDate]);

  const monthNames = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
  ];

  // Selected day events
  const selectedDayEvents = useMemo(() => {
    return getEventsForDate(selectedDay);
  }, [selectedDay, getEventsForDate]);

  // Open Drawer handler
  const handleOpenDrawer = (meeting: PublicMeetingEvent) => {
    setSelectedEventForDrawer(meeting);
    setDrawerOpen(true);
  };

  // Download complete full calendar .ics
  const handleDownloadFullCalendarIcs = () => {
    const nowIso = new Date().toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";
    const eventsIcs = publicMeetings
      .map((m, idx) => {
        const startIso = m.next_datetime ? new Date(m.next_datetime) : new Date();
        const endIso = new Date(startIso.getTime() + 90 * 60 * 1000);
        const formatD = (d: Date) => d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

        return [
          "BEGIN:VEVENT",
          `UID:ccf-event-${m.id || idx}-${idx}@ccf.org`,
          `DTSTAMP:${nowIso}`,
          `DTSTART:${formatD(startIso)}`,
          `DTEND:${formatD(endIso)}`,
          `SUMMARY:${m.nombre} - Comunidad Cristiana El Faro`,
          `DESCRIPTION:${m.descripcion || "Reunión semanal en Comunidad Cristiana El Faro."}`,
          `LOCATION:${m.lugar || "Comunidad Cristiana El Faro"}`,
          "STATUS:CONFIRMED",
          "END:VEVENT",
        ].join("\r\n");
      })
      .join("\r\n");

    const fullIcs = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Comunidad Cristiana El Faro//Calendario Oficial//ES",
      "CALSCALE:GREGORIAN",
      "METHOD:PUBLISH",
      eventsIcs,
      "END:VCALENDAR",
    ].join("\r\n");

    const blob = new Blob([fullIcs], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `calendario-reuniones-ccf.ics`;
    link.click();
    URL.revokeObjectURL(url);
    toast.success("Calendario de reuniones descargado con éxito.");
  };

  return (
    <main className="pt-[88px] pb-16 overflow-hidden min-h-screen">
      <title>Eventos y Calendario | Comunidad Cristiana El Faro (CCF)</title>
      <meta
        name="description"
        content="Conoce los horarios de nuestras reuniones semanales, cultos dominicales, grupos de hogar y próximos eventos en Comunidad Cristiana El Faro."
      />
      {/* 1. Hero Section con Slides */}
      <PublicHeroWithSlides
        eyebrow={heroEyebrow}
        title={heroTitle}
        description={heroDescription}
        slides={heroSlides}
      />

      {/* 2. Sección de Reuniones Semanales (Tarjetas Enriquecidas) */}
      <section className="ccf-container my-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Sparkles size={18} style={{ color: "var(--site-primary, #2563eb)" }} />
              <span
                className="text-xs font-bold uppercase tracking-wider"
                style={{ color: "var(--site-primary, #2563eb)" }}
              >
                Vida Congregacional
              </span>
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
              Nuestras Reuniones Semanales
            </h2>
            <p className="text-sm mt-1 max-w-xl" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
              Encuentra un horario y un lugar para adorar a Dios y compartir en comunión. Todas nuestras sedes y hogares están abiertos para ti.
            </p>
          </div>

          {/* Categorías Filter */}
          {categories.length > 2 && (
            <div
              className="inline-flex p-1 rounded-xl overflow-x-auto max-w-full"
              style={{ background: "var(--site-surface-container, rgba(0,0,0,0.04))" }}
            >
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className="px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all"
                  style={
                    activeCategory === cat
                      ? {
                          background: "var(--site-primary, #2563eb)",
                          color: "var(--site-on-primary, #ffffff)",
                          boxShadow: "0 2px 6px rgba(0,0,0,0.08)",
                        }
                      : { color: "var(--site-on-surface-variant, #64748b)" }
                  }
                >
                  {cat}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Tarjetas de Eventos */}
        {filteredMeetings.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredMeetings.map((meeting) => {
              const nextDateObj = meeting.next_datetime ? new Date(meeting.next_datetime) : null;
              const dayStr = nextDateObj ? nextDateObj.getDate() : meeting.dia_reunion?.substring(0, 3) || "CCF";
              const monthStr = nextDateObj
                ? nextDateObj.toLocaleDateString("es-ES", { month: "short" })
                : "SEM";

              return (
                <article
                  key={meeting.id}
                  className="rounded-2xl border overflow-hidden flex flex-col justify-between transition-all duration-300 hover:shadow-xl hover:-translate-y-1 group"
                  style={{
                    background: "var(--site-surface-1, #ffffff)",
                    borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                  }}
                >
                  {/* Imagen y Badge */}
                  <div className="relative h-48 w-full overflow-hidden">
                    <div
                      className="absolute inset-0 z-0 bg-cover bg-center transition-transform duration-500 group-hover:scale-105"
                      style={{
                        backgroundImage: `url(${meeting.imagen_url || "/images/events/reunion-general.jpg"})`,
                        backgroundColor: "var(--site-surface-container-high, #cbd5e1)",
                      }}
                    />
                    <div
                      className="absolute inset-0 z-10"
                      style={{
                        background:
                          "linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.1) 60%, transparent 100%)",
                      }}
                    />

                    {/* Badge Fecha */}
                    <div
                      className="absolute top-4 right-4 z-20 px-3 py-1.5 rounded-xl text-center shadow-lg backdrop-blur-md"
                      style={{
                        background: "rgba(255, 255, 255, 0.92)",
                        color: "#1e1f21",
                        border: "1px solid rgba(255,255,255,0.4)",
                      }}
                    >
                      <span className="block text-2xs font-extrabold uppercase tracking-wider text-primary" style={{ color: "var(--site-primary, #2563eb)" }}>
                        {monthStr}
                      </span>
                      <span className="block text-lg font-black leading-none">{dayStr}</span>
                    </div>

                    {/* Categoría Pill */}
                    <div className="absolute bottom-3 left-4 z-20">
                      <span
                        className="px-2.5 py-1 rounded-md text-2xs font-bold uppercase tracking-wider shadow-sm"
                        style={{
                          background: "var(--site-primary, #2563eb)",
                          color: "var(--site-on-primary, #ffffff)",
                        }}
                      >
                        {meeting.categoria_pastoral || "Reunión CCF"}
                      </span>
                    </div>
                  </div>

                  {/* Contenido Pastoral */}
                  <div className="p-6 flex-1 flex flex-col justify-between space-y-4">
                    <div className="space-y-2">
                      <h3
                        className="text-xl font-bold tracking-tight group-hover:text-primary transition-colors"
                        style={{ color: "var(--site-on-surface, #1e1f21)" }}
                      >
                        {meeting.nombre}
                      </h3>
                      <p
                        className="text-sm leading-relaxed line-clamp-2"
                        style={{ color: "var(--site-on-surface-variant, #64748b)" }}
                      >
                        {meeting.descripcion}
                      </p>
                    </div>

                    {/* Metadatos Horario y Sede */}
                    <div
                      className="pt-4 border-t space-y-2.5 text-xs font-medium"
                      style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.06))" }}
                    >
                      {meeting.dia_reunion && (
                        <div className="flex items-center gap-2" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                          <Clock size={15} style={{ color: "var(--site-primary, #2563eb)" }} />
                          <span>
                            Todos los <strong>{meeting.dia_reunion}s</strong>
                            {meeting.hora_reunion ? ` a las ${meeting.hora_reunion} hrs` : ""}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center gap-2" style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                        <MapPin size={15} style={{ color: "var(--site-primary, #2563eb)" }} />
                        <span>
                          {meeting.lugar || "Comunidad Cristiana El Faro"}
                          {meeting.sede && (
                            <Link
                              href="/sedes"
                              className="ml-1.5 underline font-semibold"
                              style={{ color: "var(--site-primary, #2563eb)" }}
                            >
                              (Ver sede)
                            </Link>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Botón de Acción Inscribirme / Asistir */}
                    <button
                      onClick={() => handleOpenDrawer(meeting)}
                      className="w-full mt-2 py-2.5 px-4 rounded-xl font-bold text-xs uppercase tracking-wider shadow-sm transition-all flex items-center justify-center gap-2 hover:opacity-95 hover:scale-[1.01]"
                      style={{
                        background: "var(--site-primary, #2563eb)",
                        color: "var(--site-on-primary, #ffffff)",
                      }}
                    >
                      <BookmarkPlus size={15} />
                      <span>Inscribirme / Asistir</span>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-80 rounded-2xl animate-pulse"
                style={{ background: "var(--site-surface-container, rgba(0,0,0,0.05))" }}
              />
            ))}
          </div>
        ) : (
          <div
            className="p-8 rounded-2xl text-center border space-y-2"
            style={{
              background: "var(--site-surface-container-low, #f8f9fb)",
              borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
            }}
          >
            <CalendarDays size={40} className="mx-auto text-primary" style={{ color: "var(--site-primary, #2563eb)" }} />
            <h3 className="font-bold text-lg" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
              No hay reuniones para este filtro
            </h3>
            <p className="text-sm" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
              Selecciona otra categoría o explora el calendario para conocer todos los horarios.
            </p>
          </div>
        )}
      </section>

      {/* 3. Calendario Mensual Interactivo Sincronizado */}
      <section className="ccf-container my-16">
        <div className="p-6 md:p-8 rounded-3xl border shadow-sm" style={{ background: "var(--site-surface-1, #ffffff)", borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}>
          <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <CalendarIcon size={18} style={{ color: "var(--site-primary, #2563eb)" }} />
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--site-primary, #2563eb)" }}>
                  Planifica tu Semana
                </span>
              </div>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                Calendario de Reuniones y Servicios
              </h2>
              <p className="text-sm mt-1" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                Haz clic en cualquier día para consultar las reuniones programadas o sincroniza el calendario completo.
              </p>
            </div>

            <button
              onClick={handleDownloadFullCalendarIcs}
              className="py-2.5 px-4 rounded-xl border text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all hover:scale-105 shrink-0"
              style={{
                borderColor: "var(--site-primary, #2563eb)",
                color: "var(--site-primary, #2563eb)",
                background: "var(--site-primary-container, rgba(37,99,235,0.06))",
              }}
            >
              <Download size={15} />
              <span>Sincronizar Calendario (.ics)</span>
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Grilla Calendario */}
            <div className="lg:col-span-8 space-y-4">
              {/* Barra de Navegación de Mes */}
              <div
                className="flex items-center justify-between p-3 rounded-xl border"
                style={{
                  background: "var(--site-surface-container-low, #f8f9fb)",
                  borderColor: "var(--site-outline-variant, rgba(0,0,0,0.06))",
                }}
              >
                <div className="flex items-center gap-3">
                  <h3 className="text-lg font-bold" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                    {monthNames[currentMonth]} {currentYear}
                  </h3>
                  <div className="flex gap-1">
                    <button
                      onClick={() => {
                        if (currentMonth === 0) {
                          setCurrentMonth(11);
                          setCurrentYear((y) => y - 1);
                        } else {
                          setCurrentMonth((m) => m - 1);
                        }
                      }}
                      className="p-1.5 rounded-lg border transition-colors hover:scale-105"
                      style={{
                        background: "var(--site-surface-1, #ffffff)",
                        borderColor: "var(--site-outline-variant, rgba(0,0,0,0.1))",
                      }}
                      aria-label="Mes anterior"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <button
                      onClick={() => {
                        if (currentMonth === 11) {
                          setCurrentMonth(0);
                          setCurrentYear((y) => y + 1);
                        } else {
                          setCurrentMonth((m) => m + 1);
                        }
                      }}
                      className="p-1.5 rounded-lg border transition-colors hover:scale-105"
                      style={{
                        background: "var(--site-surface-1, #ffffff)",
                        borderColor: "var(--site-outline-variant, rgba(0,0,0,0.1))",
                      }}
                      aria-label="Mes siguiente"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => {
                    setCurrentMonth(today.getMonth());
                    setCurrentYear(today.getFullYear());
                    setSelectedDay(today);
                  }}
                  className="text-xs font-bold uppercase tracking-wider px-3 py-1.5 rounded-lg transition-colors hover:bg-black/5"
                  style={{ color: "var(--site-primary, #2563eb)" }}
                >
                  Hoy
                </button>
              </div>

              {/* Días de la semana */}
              <div className="grid grid-cols-7 gap-1 text-center font-bold text-xs uppercase tracking-wider py-1" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                <div>Dom</div>
                <div>Lun</div>
                <div>Mar</div>
                <div>Mié</div>
                <div>Jue</div>
                <div>Vie</div>
                <div>Sáb</div>
              </div>

              {/* Matriz de Días */}
              <div className="grid grid-cols-7 gap-1.5 sm:gap-2">
                {calendarMatrix.map((item, idx) => {
                  const isSelected =
                    item.date.getDate() === selectedDay.getDate() &&
                    item.date.getMonth() === selectedDay.getMonth() &&
                    item.date.getFullYear() === selectedDay.getFullYear();
                  const hasEvents = item.events.length > 0;

                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedDay(item.date)}
                      className={`min-h-[64px] sm:min-h-[76px] p-2 rounded-xl flex flex-col justify-between items-start text-left transition-all border ${
                        isSelected
                          ? "ring-2 ring-primary shadow-md scale-[1.02]"
                          : "hover:border-primary/50"
                      }`}
                      style={{
                        background: isSelected
                          ? "var(--site-primary-container, rgba(37,99,235,0.12))"
                          : item.isCurrentMonth
                          ? "var(--site-surface-container-lowest, #ffffff)"
                          : "var(--site-surface-container, rgba(0,0,0,0.02))",
                        borderColor: isSelected
                          ? "var(--site-primary, #2563eb)"
                          : "var(--site-outline-variant, rgba(0,0,0,0.08))",
                        opacity: item.isCurrentMonth ? 1 : 0.4,
                      }}
                    >
                      <div className="w-full flex items-center justify-between">
                        <span
                          className={`text-xs sm:text-sm font-bold rounded-full w-6 h-6 flex items-center justify-center ${
                            item.isToday
                              ? "bg-primary text-white shadow-sm"
                              : ""
                          }`}
                          style={
                            item.isToday
                              ? {
                                  background: "var(--site-primary, #2563eb)",
                                  color: "var(--site-on-primary, #ffffff)",
                                }
                              : { color: "var(--site-on-surface, #1e1f21)" }
                          }
                        >
                          {item.dayNumber}
                        </span>
                        {hasEvents && (
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ background: "var(--site-primary, #2563eb)" }}
                          />
                        )}
                      </div>

                      {hasEvents && (
                        <div className="w-full mt-1 hidden sm:block">
                          <span
                            className="block text-3xs font-semibold truncate rounded px-1 py-0.5"
                            style={{
                              background: "var(--site-primary-container, rgba(37,99,235,0.15))",
                              color: "var(--site-primary, #2563eb)",
                            }}
                          >
                            {item.events[0]?.nombre}
                          </span>
                          {item.events.length > 1 && (
                            <span className="block text-3xs font-bold text-muted-foreground mt-0.5" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                              +{item.events.length - 1} más
                            </span>
                          )}
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Panel de Detalle del Día Seleccionado */}
            <div
              className="lg:col-span-4 p-5 rounded-2xl border flex flex-col justify-between space-y-4"
              style={{
                background: "var(--site-surface-container-low, #f8f9fb)",
                borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
              }}
            >
              <div className="space-y-4">
                <div className="border-b pb-3" style={{ borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))" }}>
                  <span className="text-2xs font-extrabold uppercase tracking-wider" style={{ color: "var(--site-primary, #2563eb)" }}>
                    Reuniones Programadas
                  </span>
                  <h3 className="text-lg font-bold capitalize mt-0.5" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                    {selectedDay.toLocaleDateString("es-ES", {
                      weekday: "long",
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })}
                  </h3>
                </div>

                {selectedDayEvents.length > 0 ? (
                  <div className="space-y-3">
                    {selectedDayEvents.map((evt) => (
                      <div
                        key={evt.id}
                        className="p-3.5 rounded-xl border space-y-2 transition-all hover:shadow-sm"
                        style={{
                          background: "var(--site-surface-1, #ffffff)",
                          borderColor: "var(--site-outline-variant, rgba(0,0,0,0.08))",
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <span
                            className="text-2xs font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                            style={{
                              background: "var(--site-primary-container, rgba(37,99,235,0.1))",
                              color: "var(--site-primary, #2563eb)",
                            }}
                          >
                            {evt.categoria_pastoral || "Reunión"}
                          </span>
                          {evt.hora_reunion && (
                            <span className="text-xs font-bold" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                              {evt.hora_reunion} hrs
                            </span>
                          )}
                        </div>
                        <h4 className="font-bold text-sm" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                          {evt.nombre}
                        </h4>
                        {evt.lugar && (
                          <p className="text-xs flex items-center gap-1.5" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                            <MapPin size={13} style={{ color: "var(--site-primary, #2563eb)" }} />
                            <span>{evt.lugar}</span>
                          </p>
                        )}
                        <button
                          onClick={() => handleOpenDrawer(evt)}
                          className="w-full mt-2 py-1.5 px-3 rounded-lg text-xs font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-1.5 hover:opacity-90"
                          style={{
                            background: "var(--site-primary, #2563eb)",
                            color: "var(--site-on-primary, #ffffff)",
                          }}
                        >
                          <BookmarkPlus size={14} />
                          <span>Asistir a esta reunión</span>
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center space-y-3">
                    <Heart size={32} className="mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm font-semibold" style={{ color: "var(--site-on-surface, #1e1f21)" }}>
                      Sin reuniones generales este día
                    </p>
                    <p className="text-xs leading-relaxed max-w-xs mx-auto" style={{ color: "var(--site-on-surface-variant, #64748b)" }}>
                      Te invitamos a acompañarnos en nuestros <strong>Faros en Casa</strong> los miércoles o en nuestras <strong>Escuelas Dominicales</strong> los domingos.
                    </p>
                  </div>
                )}
              </div>

              {/* Tips de Bienvenida */}
              <div
                className="p-3.5 rounded-xl border text-xs space-y-1.5"
                style={{
                  background: "var(--site-primary-container, rgba(37,99,235,0.06))",
                  borderColor: "var(--site-primary, rgba(37,99,235,0.2))",
                }}
              >
                <div className="flex items-center gap-1.5 font-bold" style={{ color: "var(--site-primary, #2563eb)" }}>
                  <CheckCircle2 size={15} />
                  <span>¿Primera vez en CCF?</span>
                </div>
                <p style={{ color: "var(--site-on-surface-variant, #475569)" }}>
                  Nuestras puertas están siempre abiertas. Contamos con atención para niños, jóvenes y traducción en nuestras sedes.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Drawer Canónico de Registro y Asistencia (0 modales) */}
      <PublicEventRegisterDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        event={selectedEventForDrawer}
      />
    </main>
  );
}
