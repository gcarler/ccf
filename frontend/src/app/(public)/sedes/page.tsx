"use client";

import { useCmsV2Page } from "@/hooks/useCmsV2Page";

import { AnimatePresence,motion } from "framer-motion";
import { Calendar,Clock,Home,Navigation,Phone,Search } from "lucide-react";
import { useEffect,useState } from "react";

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

export default function SedesPage() {
    const heroPage = useCmsV2Page('locations');
    const heroContent = heroPage?.blocks?.hero;
    const locationsContent = heroPage?.blocks?.feed;
    const mapEmbedUrl = typeof heroContent?.map_embed_url === "string" ? heroContent.map_embed_url : "";
    const mainBadge = typeof heroContent?.main_badge === "string" ? heroContent.main_badge : "";
    const directionsCta = typeof heroContent?.directions_cta === "string" ? heroContent.directions_cta : "";
    const emptyLocations = typeof heroContent?.empty_locations === "string" ? heroContent.empty_locations : "";
    const emptySearch = typeof heroContent?.empty_search === "string" ? heroContent.empty_search : "";
    const eyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "";
    const title = typeof heroContent?.title === "string" ? heroContent.title : "";
    const searchPlaceholder = typeof heroContent?.search_placeholder === "string" ? heroContent.search_placeholder : "";

    const parsedLocations: LocationItem[] = Array.isArray(locationsContent?.parsed)
        ? (locationsContent.parsed as LocationItem[])
        : [];

    const locations: LocationItem[] = parsedLocations.map((loc, i) => ({
        ...loc,
        id: loc.id ?? i + 1,
        isMain: loc.isMain ?? i === 0,
        schedule: loc.services?.join(" • ") || loc.schedule || "",
    }));

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
        <main className="pt-[88px] flex flex-col md:flex-row bg-site-surface" style={{ minHeight: "100vh" }}>

            {/* ── LISTADO DE SEDES ──────────────────────────── */}
            <aside className="w-full md:w-[340px] lg:w-[420px] xl:w-[480px] flex flex-col max-h-[60vh] md:max-h-none md:h-[calc(100vh-88px)] md:sticky md:top-[88px] bg-site-surface-container-lowest border-r border-site-outline-variant/10 overflow-hidden">
                <div className="p-4 border-b border-site-outline-variant/10">
                    {eyebrow && (
                        <span className="font-semibold text-[10px] tracking-wide uppercase block mb-4">
                            {eyebrow}
                        </span>
                    )}
                    {title && (
                        <h1 className="text-lg font-bold tracking-tight text-site-on-surface mb-3">
                            {title}
                        </h1>
                    )}
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-site-outline w-4 h-4" />
                        <input
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-site-surface-container-highest rounded-lg py-1.5 pl-12 pr-4 text-sm outline-none focus:ring-2 focus:ring-site-primary/30 transition-all"
                            placeholder={searchPlaceholder}
                        />
                    </div>
                </div>

                {locations.length === 0 ? (
                    <div className="flex-1 flex items-center justify-center p-4 text-center">
                        <div>
                            <Home size={40} className="mx-auto mb-4 opacity-20" style={{ color: "var(--site-primary)" }} />
                            {emptyLocations && (
                                <p className="text-sm" style={{ color: "var(--site-on-surface-variant)" }}>
                                    {emptyLocations}
                                </p>
                            )}
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
                                        ? "border-site-primary bg-site-primary-container/20"
                                        : "border-transparent bg-site-surface-container hover:bg-site-surface-container-high"
                                }`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div
                                        className={`p-3 rounded-lg ${
                                            selected?.id === loc.id
                                                ? "bg-site-primary"
                                                : "bg-site-primary-container text-site-primary"
                                        }`}
                                        style={selected?.id === loc.id ? { color: "var(--site-on-primary)" } : undefined}
                                    >
                                        <Home size={20} />
                                    </div>
                                    {loc.isMain && mainBadge && (
                                        <span className="text-[9px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full" style={{ background: "var(--site-cta-gradient)", color: "white" }}>
                                            {mainBadge}
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-xl font-bold text-site-on-surface mb-2">{loc.name}</h3>
                                <p className="text-site-on-surface-variant text-sm mb-3 leading-relaxed opacity-80">
                                    {loc.address}
                                </p>

                                <AnimatePresence>
                                    {selected?.id === loc.id && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            className="space-y-3 pt-4 border-t border-site-outline-variant/10 overflow-hidden"
                                        >
                                            {loc.schedule && (
                                                <div className="flex items-center gap-3 text-site-on-surface-variant text-xs">
                                                    <Clock size={14} className="text-site-primary" />
                                                    <span>{loc.schedule}</span>
                                                </div>
                                            )}
                                            {loc.midweek && (
                                                <div className="flex items-center gap-3 text-site-on-surface-variant text-xs">
                                                    <Calendar size={14} className="text-site-primary" />
                                                    <span>{loc.midweek}</span>
                                                </div>
                                            )}
                                            {loc.phone && (
                                                <div className="flex items-center gap-3 text-site-on-surface-variant text-xs">
                                                    <Phone size={14} className="text-site-primary" />
                                                    <span>{loc.phone}</span>
                                                </div>
                                            )}
                                            {directionsCta && (
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
                                                    style={{ background: "var(--site-cta-gradient)", color: "white" }}
                                                >
                                                    <Navigation size={13} />
                                                    {directionsCta}
                                                </button>
                                            )}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        ))}
                        {filtered.length === 0 && emptySearch && (
                            <div className="rounded-lg border border-dashed border-site-outline-variant/20 p-3 text-center text-sm text-site-on-surface-variant">
                                {emptySearch}
                            </div>
                        )}
                    </div>
                )}
            </aside>

            {/* ── MAPA GOOGLE MY MAPS ────────────────────────────── */}
            {mapEmbedUrl && (
                <section className="flex-1 min-h-[50vh] md:h-[calc(100vh-88px)] md:sticky md:top-[88px]">
                    <iframe
                        src={mapEmbedUrl}
                        className="w-full h-full border-0 block"
                        allowFullScreen
                        loading="lazy"
                        referrerPolicy="no-referrer-when-downgrade"
                        title="Mapa de sedes"
                        style={{ minHeight: "50vh" }}
                    />
                </section>
            )}
        </main>
    );
}
