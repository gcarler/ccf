"use client";

import React, { useState, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import { apiUrl } from '@/lib/api';
import {
    Search,
    ChevronDown,
    PlayCircle,
    Calendar,
    Bookmark,
    ChevronRight,
    Loader2
} from 'lucide-react';

interface PageContent {
    page_key: string;
    title?: string;
    content?: string;
}

export default function SermonsPage() {
    const [activeTab, setActiveTab] = useState('Todas');
    const [sermons, setSermons] = useState<any[]>([]);
    const [pageContent, setPageContent] = useState<PageContent | null>(null);
    const [loading, setLoading] = useState(true);
    const tabs = ['Todas', 'Series', 'Predicadores', 'Temas'];

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [serRes, contRes] = await Promise.all([
                    fetch(apiUrl("/sermons")),
                    fetch(apiUrl("/content/sermons_hero"))
                ]);
                if (serRes.ok) setSermons(await serRes.json());
                if (contRes.ok) setPageContent(await contRes.json());
            } catch (err) {
                console.error("Error fetching data:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    return (
        <main className="min-h-screen bg-slate-50 selection:bg-blue-100 selection:text-blue-900 pb-20">
            <Navbar />

            {/* Hero Header */}
            <section className="relative pt-32 pb-12 lg:pt-40 lg:pb-16 bg-[#0A192F] overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-[#1973f0]/20 to-transparent pointer-events-none"></div>
                <div className="container mx-auto px-6 relative z-10 text-center">
                    <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-white mb-6 tracking-tight font-primary">
                        {pageContent?.title || "Biblioteca de Prédicas"}
                    </h1>
                    <p className="text-white/70 max-w-2xl mx-auto text-lg mb-8 font-primary">
                        {pageContent?.content || "Encuentra inspiración, esperanza y dirección a través de la Palabra de Dios compartida en nuestra comunidad."}
                    </p>

                    {/* Search Bar */}
                    <div className="max-w-2xl mx-auto relative group">
                        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-blue-500 transition-colors">
                            <Search size={20} />
                        </div>
                        <input
                            type="text"
                            placeholder="Buscar prédicas, series o pastores..."
                            className="w-full bg-white/10 backdrop-blur-md border border-white/20 text-white placeholder:text-white/50 rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white/20 transition-all font-medium font-primary"
                        />
                    </div>
                </div>
            </section>

            {/* Main Content Area */}
            <section className="container mx-auto px-6 py-12">

                {/* Filters/Tabs */}
                <div className="flex gap-3 overflow-x-auto pb-6 hide-scrollbar">
                    {tabs.map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`flex h-11 shrink-0 items-center justify-center gap-x-2 rounded-full px-6 transition-all font-primary ${activeTab === tab
                                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                                : 'bg-white border text-slate-600 hover:bg-slate-50 border-slate-200'
                                }`}
                        >
                            <span className="text-sm font-bold font-primary">{tab}</span>
                            {tab !== 'Todas' && <ChevronDown size={16} />}
                        </button>
                    ))}
                </div>

                {/* Recent Sermons List */}
                <div className="mt-8">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-slate-900 text-2xl font-black tracking-tight font-primary">Prédicas Recientes</h3>
                        <button className="text-blue-600 flex items-center gap-1 text-sm font-bold hover:underline font-primary">
                            Ver Todo <ChevronRight size={16} />
                        </button>
                    </div>

                    {loading ? (
                        <div className="flex justify-center py-20">
                            <Loader2 className="animate-spin text-blue-600" size={48} />
                        </div>
                    ) : sermons.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {sermons.map((sermon) => (
                                <div key={sermon.id} className="group relative flex flex-col overflow-hidden rounded-3xl bg-white border border-slate-100 hover:border-blue-200 hover:shadow-2xl hover:shadow-blue-100 transition-all cursor-pointer">

                                    {/* Thumbnail */}
                                    <div className="relative aspect-video w-full overflow-hidden">
                                        {sermon.image_url ? (
                                            <img
                                                src={sermon.image_url}
                                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                                                alt={sermon.title}
                                            />
                                        ) : (
                                            <div className="h-full w-full bg-slate-900 flex items-center justify-center">
                                                <div className="absolute inset-0 bg-gradient-to-br from-primary/30 via-slate-900/40 to-slate-900 opacity-60"></div>
                                                <PlayCircle size={48} className="text-white/20 group-hover:text-blue-500/40 transition-colors" />
                                            </div>
                                        )}

                                        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 via-transparent to-transparent opacity-80 group-hover:opacity-100 transition-opacity"></div>

                                        {/* Play Button Overlay */}
                                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300">
                                            <div className="size-16 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-xl shadow-blue-600/40 backdrop-blur-sm -translate-y-4 group-hover:translate-y-0 transition-transform duration-300">
                                                <PlayCircle size={32} className="fill-current" />
                                            </div>
                                        </div>
                                    </div>

                                    {/* Content */}
                                    <div className="flex flex-col p-6 text-left">
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md font-primary">
                                                Serie: {sermon.series || "General"}
                                            </span>
                                        </div>
                                        <h4 className="text-xl font-black leading-tight text-slate-900 group-hover:text-blue-600 transition-colors mb-2 font-primary">
                                            {sermon.title}
                                        </h4>
                                        <p className="text-sm text-slate-500 font-medium mb-4 font-primary">
                                            {sermon.preacher}
                                        </p>

                                        {/* Meta Info */}
                                        <div className="mt-auto flex items-center justify-between pt-4 border-t border-slate-50">
                                            <div className="flex items-center gap-4 text-slate-400">
                                                <span className="flex items-center gap-1.5 text-xs font-bold font-primary">
                                                    <Calendar size={14} /> {new Date(sermon.date).toLocaleDateString()}
                                                </span>
                                            </div>
                                            <button className="size-10 rounded-full flex items-center justify-center bg-slate-50 hover:bg-slate-100 border border-slate-100 text-slate-400 hover:text-blue-600 transition-colors">
                                                <Bookmark size={16} />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="py-20 text-center text-slate-500 font-medium italic animate-pulse font-primary">
                            No hay prédicas disponibles en este momento.
                        </div>
                    )}
                </div>
            </section>

        </main>
    );
}
