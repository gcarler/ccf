"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Search, Phone, Clock, Calendar, Navigation, Plus, Minus, Home } from "lucide-react";
import RichText from "@/components/public/RichText";
import { useContentBlock } from "@/hooks/useContent";

interface LocationItem {
    id: number;
    name: string;
    address: string;
    phone?: string;
    schedule?: string;
    midweek?: string;
    coordinates: { x: string; y: string };
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
        coordinates: { x: "35%", y: "45%" },
        isMain: true,
    },
    {
        id: 2,
        name: "Campus Norte",
        address: "Calle 170 #54-12, Sector Universitario",
        phone: "+57 310 111 2222",
        schedule: "Domingos 10 AM",
        midweek: "Sábados 6 PM",
        coordinates: { x: "65%", y: "30%" },
    },
];

function buildCoordinates(index: number, total: number): { x: string; y: string } {
    if (total <= 1) return { x: "50%", y: "45%" };
    const positions = [
        { x: "35%", y: "45%" },
        { x: "65%", y: "30%" },
        { x: "40%", y: "60%" },
        { x: "55%", y: "50%" },
    ];
    return positions[index % positions.length];
}

export default function SedesPage() {
    const { data: heroContent } = useContentBlock("faro_locations_hero");
    const { data: locationsContent } = useContentBlock("faro_locations_feed");

    const parsedLocations: LocationItem[] = Array.isArray(locationsContent?.parsed) ? locationsContent.parsed as LocationItem[] : [];

    const locations: LocationItem[] = parsedLocations.length > 0
        ? parsedLocations.map((loc, i) => ({
            ...loc,
            id: loc.id ?? i + 1,
            coordinates: loc.coordinates || buildCoordinates(i, parsedLocations.length),
            isMain: loc.isMain ?? i === 0,
            schedule: loc.services?.join(" • ") || loc.schedule || "Domingos 9 AM",
        }))
        : fallbackLocations;

    const [selected, setSelected] = useState<LocationItem | null>(locations[0] || null);
    const [search, setSearch] = useState("");
    const [zoom, setZoom] = useState(1);
    useEffect(() => {
        setSelected(current => locations.find(location => location.id === current?.id) ?? locations[0] ?? null);
        // La seleccion solo debe resincronizarse cuando llega nuevo contenido del CMS.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [locationsContent?.parsed]);

    const filtered = locations.filter((l) =>
        l.name.toLowerCase().includes(search.toLowerCase()) ||
        l.address.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="pt-[88px] min-h-screen flex flex-col md:flex-row bg-faro-surface">
            {/* ── LISTADO DE SEDES ──────────────────────────── */}
            <aside className="w-full md:w-[450px] lg:w-[500px] flex flex-col h-[calc(100vh-88px)] bg-faro-surface-container-lowest border-r border-faro-outline-variant/10 z-20">
                <div className="p-4 lg:p-4 border-b border-faro-outline-variant/10">
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
                                className={`p-3 rounded-lg border-2 transition-all cursor-pointer group ${
                                    selected?.id === loc.id
                                    ? "border-faro-primary bg-faro-primary-container/20"
                                    : "border-transparent bg-faro-surface-container hover:bg-faro-surface-container-high"
                                }`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <div className={`p-3 rounded-lg ${selected?.id === loc.id ? "bg-faro-primary text-white" : "bg-faro-primary-container text-faro-primary"}`}>
                                        <Home size={20} />
                                    </div>
                                    {loc.isMain && (
                                        <span className="text-[9px] font-semibold uppercase tracking-wide bg-faro-secondary text-white px-2.5 py-1 rounded-full">Principal</span>
                                    )}
                                </div>
                                <h3 className="text-xl font-bold text-faro-on-surface mb-2">{loc.name}</h3>
                                <p className="text-faro-on-surface-variant text-sm mb-3 leading-relaxed opacity-80">{loc.address}</p>

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
                                            <div className="flex items-center gap-3 text-faro-on-surface-variant text-xs">
                                                <Phone size={14} className="text-faro-primary" />
                                                <span>{loc.phone}</span>
                                            </div>
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

            {/* ── MAPA INTERACTIVO ────────────────────────────── */}
            <section className="flex-1 relative bg-faro-surface-container-low overflow-hidden min-h-[400px]">
                <div className="absolute inset-0 z-0">
                    <div
                        className="w-full h-full opacity-40 grayscale contrast-125 transition-transform duration-300"
                        style={{
                            backgroundImage: "url('https://picsum.photos/seed/1526778548025-fa2f459cd5c1/800/600')",
                            backgroundSize: "cover",
                            filter: "brightness(0.5) contrast(1.2)",
                            transform: `scale(${zoom})`
                        }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-faro-surface-container-lowest via-transparent to-transparent" />
                </div>

                {/* Map Pins */}
                {locations.map((loc) => (
                    <motion.div
                        key={loc.id}
                        initial={false}
                        animate={{ scale: selected?.id === loc.id ? 1.2 : 1 }}
                        className="absolute z-10 cursor-pointer"
                        style={{ left: loc.coordinates.x, top: loc.coordinates.y }}
                        onClick={() => setSelected(loc)}
                    >
                        <div className="relative group">
                            <AnimatePresence>
                                {selected?.id === loc.id && (
                                    <motion.div
                                        initial={{ scale: 0, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0, opacity: 0 }}
                                        className="absolute -inset-4 bg-faro-primary/30 blur-xl rounded-full animate-pulse"
                                    />
                                )}
                            </AnimatePresence>
                            <div className={`relative p-3 rounded-lg shadow-2xl transition-all ${
                                selected?.id === loc.id ? "bg-faro-primary text-white" : "bg-faro-surface-bright text-faro-primary border border-faro-primary/20"
                            }`}>
                                <MapPin size={24} fill={selected?.id === loc.id ? "currentColor" : "none"} />
                            </div>

                            <AnimatePresence>
                                {selected?.id === loc.id && (
                                    <motion.div
                                        initial={{ y: 10, opacity: 0 }}
                                        animate={{ y: 0, opacity: 1 }}
                                        className="absolute bottom-full mb-4 left-1/2 -translate-x-1/2 whitespace-nowrap bg-faro-surface-container-highest px-4 py-2 rounded-md border border-faro-primary/20 shadow-2xl"
                                    >
                                        <p className="font-semibold text-faro-primary uppercase tracking-wide">{loc.name}</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                ))}

                {/* Map Controls */}
                <div className="absolute bottom-10 right-10 flex flex-col gap-4 z-20">
                    <button onClick={() => setZoom(value => Math.min(value + 0.1, 1.4))} className="w-14 h-8 rounded-lg bg-faro-surface-bright/80 backdrop-blur-xl border border-faro-outline-variant/20 flex items-center justify-center text-faro-primary shadow-xl hover:scale-110 transition-all">
                        <Plus size={20} />
                    </button>
                    <button onClick={() => setZoom(value => Math.max(value - 0.1, 1))} className="w-14 h-8 rounded-lg bg-faro-surface-bright/80 backdrop-blur-xl border border-faro-outline-variant/20 flex items-center justify-center text-faro-primary shadow-xl hover:scale-110 transition-all">
                        <Minus size={20} />
                    </button>
                    <button onClick={() => selected && window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selected.address)}`, "_blank", "noopener,noreferrer")} className="w-14 h-8 rounded-lg bg-faro-primary text-white flex items-center justify-center shadow-2xl hover:scale-110 transition-all">
                        <Navigation size={20} />
                    </button>
                </div>
            </section>
        </main>
    );
}
