"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { MapPin, Plus, CalendarDays, Users } from 'lucide-react';
import { motion } from 'framer-motion';
import { apiFetch } from '@/lib/http';
import Skeleton from '@/components/ui/Skeleton';

interface EventRecord {
    id: number;
    title: string;
    description: string;
    date: string;
    category: string;
    location: string;
    attendees_count: number;
}

export default function EventsCalendar() {
    const { isAuthenticated, token } = useAuth();
    const [activeTab, setActiveTab] = useState('Todos');
    const [events, setEvents] = useState<EventRecord[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!isAuthenticated || !token) return;
        const fetchEvents = async () => {
            setLoading(true);
            try {
                const data = await apiFetch<EventRecord[]>('/community/events', { token });
                setEvents(Array.isArray(data) ? data : []);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchEvents();
    }, [isAuthenticated, token]);

    if (!isAuthenticated) return null;

    const tabs = ['Todos', 'Servicios', 'Juveniles', 'Estudios', 'Misiones'];

    const filteredEvents = events.filter(e => activeTab === 'Todos' || e.category === activeTab);

    return (
 <div className="p-4 lg:p-4 space-y-3 w-full animate-in fade-in duration-700">
            <header className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-2 text-[hsl(var(--primary))] font-bold uppercase tracking-wide text-[10px]">
                        <div className="size-1.5 rounded-full bg-current shadow-[0_0_8px_currentColor]"></div>
                        Comunidad El Faro
                    </div>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tighter">Calendario de Eventos</h1>
                </div>
                
                <div className="flex items-center gap-3">
                    <h2 className="text-sm font-bold tabular-nums">Eventos Próximos</h2>
                </div>
            </header>

            <div className="space-y-3">
                <div className="flex gap-4 border-b border-[hsl(var(--border))] px-2">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-2 text-[10px] font-bold uppercase tracking-wide transition-all relative ${activeTab === tab
                                ? 'text-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
                                }`}
                        >
                            {tab}
                            {activeTab === tab && (
                                <motion.div 
                                    layoutId="active-tab"
                                    className="absolute bottom-[-1px] left-0 right-0 h-0.5 bg-[hsl(var(--primary))] shadow-[0_0_12px_hsl(var(--primary)/0.5)]" 
                                />
                            )}
                        </button>
                    ))}
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {[1, 2].map(i => <Skeleton key={i} className="h-48 w-full rounded-md" />)}
                    </div>
                ) : filteredEvents.length === 0 ? (
                    <div className="text-center py-1.5 text-[hsl(var(--text-secondary))]">
                        <CalendarDays className="mx-auto h-8 w-12 mb-4 opacity-20" />
                        <p className="font-bold text-sm">No hay eventos en esta categoría</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 pb-4">
                        {filteredEvents.map(event => (
                            <motion.div 
                                key={event.id}
                                whileHover={{ y: -2 }}
                                className="group bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-md overflow-hidden shadow-sm hover:shadow-md hover:border-[hsl(var(--primary)/0.3)] transition-all flex flex-col"
                            >
                                <div className="p-4 flex-1">
                                    <div className="flex items-center justify-between mb-3">
                                        <span className="rounded-md bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] px-2 py-1 text-[9px] font-bold uppercase tracking-wide">{event.category}</span>
                                        <div className="flex items-center gap-1.5 text-[hsl(var(--text-secondary))] text-[10px] font-bold">
                                            <CalendarDays size={12} />
                                            {new Date(event.date).toLocaleDateString()}
                                        </div>
                                    </div>
                                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] leading-tight mb-2 group-hover:text-[hsl(var(--primary))] transition-colors">{event.title}</h3>
                                    <p className="text-xs text-[hsl(var(--text-secondary))] font-medium line-clamp-2 mb-4">{event.description}</p>
                                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-[hsl(var(--text-secondary))] mb-2">
                                        <MapPin size={12} />
                                        {event.location}
                                    </div>
                                </div>
                                <div className="flex items-center justify-between px-4 py-3 border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-[hsl(var(--text-secondary))]">
                                        <Users size={14} />
                                        {event.attendees_count} Asistentes
                                    </div>
                                    <button className="px-3 py-1.5 bg-[hsl(var(--text-primary))] text-[hsl(var(--bg-primary))] rounded-lg text-[9px] font-bold uppercase tracking-wide shadow-sm hover:opacity-90 transition-all active:scale-95">
                                        Reservar
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>

            <motion.button 
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="fixed bottom-6 right-6 size-7 bg-[hsl(var(--primary))] text-white rounded-md shadow-lg flex items-center justify-center z-50 border border-white/20"
            >
                <Plus size={24} />
            </motion.button>
        </div>
    );
}

