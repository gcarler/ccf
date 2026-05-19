"use client";

import React from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Users, MapPin, Clock, Search, Plus, Filter } from 'lucide-react';

export default function GroupsPage() {
    const groups = [
        {
            id: 1,
            name: "Conexión Vida - Norte",
            leader: "Carlos & Ana Méndez",
            location: "Col. San Benito",
            schedule: "Jueves, 7:30 PM",
            members: 12,
            category: "Familias",
            image: "https://picsum.photos/seed/1511632765486-a01980e01a18/800/600"
        },
        {
            id: 2,
            name: "Jóvenes Proezas",
            leader: "Josué G.",
            location: "Auditorio CCF",
            schedule: "Sábados, 5:00 PM",
            members: 45,
            category: "Jóvenes",
            image: "https://picsum.photos/seed/1529156069898-49953e39b3ac/800/600"
        },
        {
            id: 3,
            name: "Hombres de Honor",
            leader: "David R.",
            location: "Virtual (Zoom)",
            schedule: "Martes, 6:00 AM",
            members: 28,
            category: "Hombres",
            image: "https://picsum.photos/seed/1507003211169-0a1dd7228f2d/800/600"
        }
    ];

    return (
        <div className="max-w-6xl mx-auto space-y-10 pb-20 animate-in fade-in duration-700">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-2">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-black uppercase tracking-[0.3em] text-[10px]">
                        <div className="size-2 rounded-full bg-current shadow-[0_0_10px_currentColor]"></div>
                        Grupos Pequeños
                    </div>
                    <h1 className="text-4xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Comunidades</h1>
                    <p className="text-[hsl(var(--text-secondary))] font-medium">Encuentra un grupo para crecer juntos en fe y amistad.</p>
                </div>

                <div className="flex items-center gap-3">
                    <div className="relative group">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] size-4" />
                        <input 
                            placeholder="Buscar grupo..."
                            className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-2xl h-12 pl-12 pr-6 text-sm font-medium w-64 focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] focus:border-[hsl(var(--primary))] outline-none transition-all"
                        />
                    </div>
                    <button className="size-12 rounded-2xl bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-all">
                        <Filter size={18} />
                    </button>
                    <button className="h-12 px-6 rounded-2xl bg-[hsl(var(--primary))] text-white font-black uppercase tracking-widest text-[10px] flex items-center gap-2 shadow-lg shadow-primary/20 hover:opacity-90 transition-all">
                        <Plus size={16} strokeWidth={3} />
                        Unirse a un Grupo
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {groups.map((group, idx) => (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.1 }}
                        key={group.id}
                        className="group bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2.5rem] overflow-hidden hover:border-[hsl(var(--primary)/0.3)] hover:shadow-2xl transition-all shadow-sm flex flex-col"
                    >
                        <div className="h-48 relative overflow-hidden">
                            <Image
                                src={group.image}
                                alt={group.name}
                                fill
                                unoptimized
                                className="object-cover group-hover:scale-110 transition-transform duration-1000"
                                sizes="(min-width: 1024px) 33vw, (min-width: 768px) 50vw, 100vw"
                            />
                            <div className="absolute inset-0 bg-gradient-to-t from-[hsl(var(--surface-2))] via-transparent to-transparent"></div>
                            <div className="absolute top-4 left-4 h-8 px-4 rounded-full bg-white/20 backdrop-blur-md border border-white/30 flex items-center justify-center text-[10px] font-black uppercase tracking-widest text-white">
                                {group.category}
                            </div>
                        </div>

                        <div className="p-8 space-y-6 flex-1 flex flex-col">
                            <div className="space-y-1">
                                <h3 className="text-xl font-black text-[hsl(var(--text-primary))] tracking-tighter group-hover:text-[hsl(var(--primary))] transition-colors">
                                    {group.name}
                                </h3>
                                <p className="text-[hsl(var(--text-secondary))] text-xs font-bold uppercase tracking-widest">
                                    {group.leader}
                                </p>
                            </div>

                            <div className="space-y-3 pt-2">
                                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                                    <MapPin size={14} className="text-[hsl(var(--primary))]" />
                                    {group.location}
                                </div>
                                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                                    <Clock size={14} className="text-[hsl(var(--primary))]" />
                                    {group.schedule}
                                </div>
                                <div className="flex items-center gap-3 text-[hsl(var(--text-secondary))] text-xs font-medium">
                                    <Users size={14} className="text-[hsl(var(--primary))]" />
                                    {group.members} Integrantes
                                </div>
                            </div>

                            <div className="pt-4 mt-auto">
                                <button className="w-full h-12 rounded-2xl bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] font-black uppercase tracking-widest text-[9px] hover:bg-[hsl(var(--primary))] hover:text-white hover:border-transparent transition-all">
                                    Ver Detalles
                                </button>
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

