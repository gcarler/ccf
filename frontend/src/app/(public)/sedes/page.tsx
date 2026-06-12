"use client";

import { useContentBlock } from "@/hooks/useContent";
import { AnimatePresence,motion } from "framer-motion";
import { Calendar,Clock,Home,Navigation,Phone,Search } from "lucide-react";
import { useEffect,useState } from "react";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";

const MAP_EMBED_URL =
    "https://www.google.com/maps/d/embed?mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM&ehbc=2E312F";

interface LocationItem {
    id: number;
    name: string;
    address: string;
    mapsUrl?: string;
    phone?: string;
    schedule?: string;
    midweek?: string;
    isMain?: boolean;
    services?: string[];
}

const fallbackLocations: LocationItem[] = [
    {
        id: 1,
        name: "Sede Central",
        address: "Av. Esperanza 124, Centro Financiero",
        phone: "+57 320 000 0000",
        schedule: "Domingos 9 AM y 11 AM",
        midweek: "Lunes 7 PM",
        isMain: true,
    },
    {
        id: 2,
        name: "Campus Norte",
        address: "Calle 170 #54-12, Sector Universitario",
        phone: "+57 310 111 2222",
        schedule: "Domingos 10 AM",
        midweek: "Sábados 6 PM",
    },
];

export default function SedesPage() {
    const { data: heroContent } = useContentBlock("faro_locations_hero");
    const { data: locationsContent } = useContentBlock("faro_locations_feed");

    const parsedLocations: LocationItem[] = Array.isArray(locationsContent?.parsed)
        ? (locationsContent.parsed as LocationItem[])
        : [];

    const locations: LocationItem[] =
        parsedLocations.length > 0
            ? parsedLocations.map((loc, i) => ({
                  ...loc,
                  id: loc.id ?? i + 1,
                  isMain: loc.isMain ?? i === 0,
                  schedule: loc.services?.join(" • ") || loc.schedule || "Domingos 9 AM",
              }))
            : fallbackLocations;

    const [selected, setSelected] = useState<LocationItem | null>(locations[0] || null);
    const [search, setSearch] = useState("");

    useEffect(() => {
        setSelected(
            (current) =>
                locations.find((l) => l.id === current?.id) ?? locations[0] ?? null
        );
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [locationsContent?.parsed]);

    const filtered = locations.filter(
        (l) =>
            l.name.toLowerCase().includes(search.toLowerCase()) ||
            l.address.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <CmsPageOverride slug="sedes">
            <main className="pt-[88px] flex flex-col md:flex-row bg-faro-surface" style={{ minHeight: "100vh" }}>

            {/* ── LISTADO DE SEDES ──────────────────────────── */}
            <aside className="w-full md:w-[450px] lg:w-[500px] flex flex-col md:h-[calc(100vh-88px)] md:sticky md:top-[88px] bg-faro-surface-container-lowest border-r border-faro-outline-variant/10">
                <div className="p-4 border-b border-faro-outline-variant/10">
                    <span className="font-semibold text-[10px] tracking-wide uppercase block mb-4">
                        {heroContent?.eyebrow || "Nuestra Presencia"}
                    </span>
                    <h1 className="text-lg font-bold tracking-tight text-faro-on-surface mb-3">
                        {heroContent?.title || "Nuestras Sedes"}
                    </h1>
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-faro-outline w-4 h-4" />
                        <input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-faro-surface-container-highest rounded-lg py-1.5 pl-12 pr-4 text-sm outline-none focus:ring-2 focus:ring-faro-primary/30 transition-all"
                            placeholder={heroContent?.search_placeholder || "Buscar ciudad o dirección..."}
                        />
                    </div>
                </div>

                {locations.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center p-4 text-center">
                        <div>
                            <Home size={40} className="mx-auto mb-4 opacity-20" style={{ color: "var(--faro-primary)" }} />
                            <p className="text-sm" style={{ color: "var(--faro-on-surface-variant)" }}>
                                No hay sedes configuradas para mostrar.
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-thin">
                        {filtered.map((loc) => (
                            <motion.div
                                key={loc.id}
                                onClick={() => setSelected(loc)}
                                className={`p-3 rounded-lg border-2 transition-all cursor-pointer ${
                                    selected?.id === loc.id
                                        ? "border-faro-primary bg-faro-primary-container/20"
                                        : "border-transparent bg-faro-surface-container hover:bg-faro-surface-container-high"
                                }`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div
                                        className={`p-3 rounded-lg ${
                                            selected?.id === loc.id
                                                ? "bg-faro-primary"
                                                : "bg-faro-primary-container text-faro-primary"
                                        }`}
                                        style={selected?.id === loc.id ? { color: "var(--faro-on-primary)" } : undefined}
                                    >
                                        <Home size={20} />
                                    </div>
                                    {loc.isMain && (
                                        <span className="text-[9px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full" style={{ background: "var(--faro-cta-gradient)", color: "white" }}>
                                            Principal
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-xl font-bold text-faro-on-surface mb-2">{loc.name}</h3>
                                <p className="text-faro-on-surface-variant text-sm mb-3 leading-relaxed opacity-80">
                                    {loc.address}
                                </p>

                                <AnimatePresence>
                                    {selected?.id === loc.id && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="space-y-3 pt-4 border-t border-faro-outline-variant/10 overflow-hidden"
                                        >
                                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                                <Clock size={14} className="text-faro-primary" />
                                                <span>{loc.schedule}</span>
                                            </div>
                                            {loc.midweek && (
                                                <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                                    <Calendar size={14} className="text-faro-primary" />
                                                    <span>{loc.midweek}</span>
                                                </div>
                                            )}
                                            {loc.phone && (
                                                <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                                    <Phone size={14} className="text-faro-primary" />
                                                    <span>{loc.phone}</span>
                                                </div>
                                            )}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    window.open(
                                                        loc.mapsUrl ?? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(loc.address)}`,
                                                        "_blank",
                                                        "noopener,noreferrer"
                                                    );
                                                }}
                                                className="mt-1 w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold hover:opacity-90 transition-opacity"
                                                style={{ background: "var(--faro-cta-gradient)", color: "white" }}
                                            >
                                                <Navigation size={13} />
                                                Cómo llegar
                                            </button>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        ))}
                        {filtered.length === 0 && (
                            <div className="rounded-lg border border-dashed border-faro-outline-variant/20 p-3 text-center text-sm text-faro-on-surface-variant">
                                No se encontraron sedes con ese criterio.
                            </div>
                        )}
                    </div>
                )}
            </aside>

            {/* ── MAPA GOOGLE MY MAPS ────────────────────────────── */}
            <section className="flex-1 min-h-[50vh] md:h-[calc(100vh-88px)] md:sticky md:top-[88px]">
                <iframe
                    src={MAP_EMBED_URL}
                    className="w-full h-full border-0 block"
                    allowFullScreen
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                    title="Mapa de sedes El Faro"
                    style={{ minHeight: "50vh" }}
                />
            </section>
        </main>
        </CmsPageOverride>
    );
}
