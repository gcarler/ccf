"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MapPin, Search, Phone, Clock, Calendar, Navigation, Plus, Minus, Home } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";

const LOCATIONS = [
    {
        id: 1,
        name: "FARO Central",
        address: "Av. de la Iluminación 450, Distrito Tecnológico, Ciudad de México.",
        phone: "+52 55 1234 5678",
        schedule: "Domingos: 09:00 AM • 11:30 AM • 06:00 PM",
        midweek: "Miércoles: 07:30 PM (Noche de Oración)",
        coordinates: { x: "35%", y: "45%" },
        isMain: true
    },
    {
        id: 2,
        name: "FARO Norte",
        address: "Calle del Resplandor 12, Zona Esmeralda, Monterrey.",
        phone: "+52 81 9876 5432",
        schedule: "Domingos: 10:00 AM • 01:00 PM",
        coordinates: { x: "65%", y: "30%" }
    },
    {
        id: 3,
        name: "FARO Poniente",
        address: "Boulevard de los Guías 889, Santa Fe, Ciudad de México.",
        phone: "+52 55 8765 4321",
        schedule: "Domingos: 11:00 AM • 05:00 PM",
        coordinates: { x: "40%", y: "60%" }
    }
];

export default function SedesPage() {
    const { data: heroContent } = useContentBlock("faro_locations_hero");
    const { data: locationsContent } = useContentBlock("faro_locations_feed");
    
    const locations = Array.isArray(locationsContent?.parsed) && locationsContent.parsed.length > 0 
        ? locationsContent.parsed.map((loc: any, i: number) => ({
            ...loc,
            id: i + 1,
            coordinates: i === 0 ? { x: "35%", y: "45%" } : { x: "65%", y: "30%" },
            isMain: i === 0,
            schedule: loc.services?.join(" • ") || "Domingos 9 AM",
        })) 
        : LOCATIONS;

    const [selected, setSelected] = useState(locations[0] || LOCATIONS[0]);
    const [search, setSearch] = useState("");

    const filtered = locations.filter((l: any) => 
        l.name.toLowerCase().includes(search.toLowerCase()) || 
        l.address.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <main className="pt-[88px] min-h-screen flex flex-col md:flex-row bg-faro-surface">
            {/* ── LISTADO DE SEDES ──────────────────────────── */}
            <aside className="w-full md:w-[450px] lg:w-[500px] flex flex-col h-[calc(100vh-88px)] bg-faro-surface-container-lowest border-r border-faro-outline-variant/10 z-20">
                <div className="p-8 lg:p-10 border-b border-faro-outline-variant/10">
                    <span className="text-faro-primary font-black text-[10px] tracking-[0.3em] uppercase block mb-4">
                        {heroContent?.eyebrow || "Nuestra Presencia"}
                    </span>
                    <h1 className="text-4xl font-black tracking-tight text-faro-on-surface mb-8">
                        {heroContent?.title || "Nuestras Sedes"}
                    </h1>
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-faro-outline w-4 h-4" />
                        <input 
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-faro-surface-container-highest rounded-2xl py-4 pl-12 pr-4 text-sm outline-none focus:ring-2 focus:ring-faro-primary/30 transition-all"
                            placeholder={heroContent?.search_placeholder || "Buscar ciudad o dirección..."}
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
                    {filtered.map((loc) => (
                        <motion.div 
                            key={loc.id}
                            onClick={() => setSelected(loc)}
                            className={`p-6 rounded-3xl border-2 transition-all cursor-pointer group ${
                                selected.id === loc.id 
                                ? "border-faro-primary bg-faro-primary-container/20" 
                                : "border-transparent bg-faro-surface-container hover:bg-faro-surface-container-high"
                            }`}
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className={`p-3 rounded-2xl ${selected.id === loc.id ? "bg-faro-primary text-white" : "bg-faro-primary-container text-faro-primary"}`}>
                                    <Home size={20} />
                                </div>
                                {loc.isMain && (
                                    <span className="text-[9px] font-black uppercase tracking-widest bg-faro-secondary text-white px-2.5 py-1 rounded-full">Principal</span>
                                )}
                            </div>
                            <h3 className="text-xl font-black text-faro-on-surface mb-2">{loc.name}</h3>
                            <p className="text-faro-on-surface-variant text-sm mb-6 leading-relaxed opacity-80">{loc.address}</p>
                            
                            <AnimatePresence>
                                {selected.id === loc.id && (
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
                </div>
            </aside>

            {/* ── MAPA INTERACTIVO ────────────────────────────── */}
            <section className="flex-1 relative bg-faro-surface-container-low overflow-hidden min-h-[400px]">
                {/* Simulated Map Background */}
                <div className="absolute inset-0 z-0">
                    <div 
                        className="w-full h-full opacity-40 grayscale contrast-125"
                        style={{ 
                            backgroundImage: "url('https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=1600&q=80')", 
                            backgroundSize: "cover",
                            filter: "brightness(0.5) contrast(1.2)"
                        }}
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-faro-surface-container-lowest via-transparent to-transparent" />
                </div>

                {/* Map Pins */}
                {LOCATIONS.map((loc) => (
                    <motion.div 
                        key={loc.id}
                        initial={false}
                        animate={{ scale: selected.id === loc.id ? 1.2 : 1 }}
                        className="absolute z-10 cursor-pointer"
                        style={{ left: loc.coordinates.x, top: loc.coordinates.y }}
                        onClick={() => setSelected(loc)}
                    >
                        <div className="relative group">
                            <AnimatePresence>
                                {selected.id === loc.id && (
                                    <motion.div 
                                        initial={{ scale: 0, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        exit={{ scale: 0, opacity: 0 }}
                                        className="absolute -inset-4 bg-faro-primary/30 blur-xl rounded-full animate-pulse" 
                                    />
                                )}
                            </AnimatePresence>
                            <div className={`relative p-3 rounded-2xl shadow-2xl transition-all ${
                                selected.id === loc.id ? "bg-faro-primary text-white" : "bg-faro-surface-bright text-faro-primary border border-faro-primary/20"
                            }`}>
                                <MapPin size={24} fill={selected.id === loc.id ? "currentColor" : "none"} />
                            </div>
                            
                            {/* Tooltip */}
                            <AnimatePresence>
                                {selected.id === loc.id && (
                                    <motion.div 
                                        initial={{ y: 10, opacity: 0 }}
                                        animate={{ y: 0, opacity: 1 }}
                                        className="absolute bottom-full mb-4 left-1/2 -translate-x-1/2 whitespace-nowrap bg-faro-surface-container-highest px-4 py-2 rounded-xl border border-faro-primary/20 shadow-2xl"
                                    >
                                        <p className="text-[10px] font-black text-faro-primary uppercase tracking-widest">{loc.name}</p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                ))}

                {/* Map Controls */}
                <div className="absolute bottom-10 right-10 flex flex-col gap-4 z-20">
                    <button className="w-14 h-14 rounded-2xl bg-faro-surface-bright/80 backdrop-blur-xl border border-faro-outline-variant/20 flex items-center justify-center text-faro-primary shadow-xl hover:scale-110 transition-all">
                        <Plus size={20} />
                    </button>
                    <button className="w-14 h-14 rounded-2xl bg-faro-surface-bright/80 backdrop-blur-xl border border-faro-outline-variant/20 flex items-center justify-center text-faro-primary shadow-xl hover:scale-110 transition-all">
                        <Minus size={20} />
                    </button>
                    <button className="w-14 h-14 rounded-2xl bg-faro-primary text-white flex items-center justify-center shadow-2xl hover:scale-110 transition-all">
                        <Navigation size={20} />
                    </button>
                </div>

                {/* Floating Info (Desktop) */}
                <div className="absolute top-10 left-10 hidden lg:block z-20">
                    <div className="bg-faro-surface-container-highest/90 backdrop-blur-xl p-1 rounded-2xl border border-faro-outline-variant/20 flex shadow-2xl">
                        <button className="px-8 py-2.5 rounded-xl bg-faro-primary text-white text-[10px] font-black uppercase tracking-widest shadow-lg">Mapa</button>
                        <button className="px-8 py-2.5 rounded-xl text-faro-on-surface/50 text-[10px] font-black uppercase tracking-widest hover:text-faro-on-surface transition-all">Satélite</button>
                    </div>
                </div>
            </section>
        </main>
    );
}

