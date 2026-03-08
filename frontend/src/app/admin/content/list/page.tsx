"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    ArrowLeft,
    Plus,
    Search,
    Edit3,
    Eye,
    EyeOff
} from 'lucide-react';

interface ContentItem {
    id: string;
    title: string;
    author: string;
    date: string;
    status: 'Activo' | 'Borrador';
    visible: boolean;
    type: 'Prédica' | 'Curso' | 'Material';
}

export default function ContentList() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeTab, setActiveTab] = useState('Prédicas');
    const [searchQuery, setSearchQuery] = useState('');

    const items: ContentItem[] = [
        { id: '1', title: 'La Gracia Inagotable', author: 'Pastor Juan Pérez', date: '12 Oct 2023', status: 'Activo', visible: true, type: 'Prédica' },
        { id: '2', title: 'Caminando en el Espíritu', author: 'Invitado Especial', date: '05 Oct 2023', status: 'Borrador', visible: false, type: 'Prédica' },
        { id: '3', title: 'Serie: Fundamentos Bíblicos', author: 'Dpto. Educación', date: '28 Sep 2023', status: 'Activo', visible: true, type: 'Curso' },
        { id: '4', title: 'Renovación Mental', author: 'Pastora Elena M.', date: '20 Sep 2023', status: 'Activo', visible: true, type: 'Prédica' },
    ];

    if (!isAuthenticated) return null;

    const filteredItems = items.filter(item => {
        const matchesTab = (activeTab === 'Prédicas' && item.type === 'Prédica') ||
            (activeTab === 'Cursos' && item.type === 'Curso') ||
            (activeTab === 'Materiales' && item.type === 'Material');
        const matchesSearch = item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.author.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesTab && matchesSearch;
    });

    return (
        <div className="flex flex-col h-full bg-slate-950/20 font-display">
            {/* Header Area */}
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-50">
                <div className="px-8 pt-10 pb-4 flex items-center justify-between">
                    <button onClick={() => router.back()} className="p-3 rounded-2xl bg-white/5 border border-white/10 text-primary hover:bg-primary/10 transition-all">
                        <ArrowLeft size={20} />
                    </button>
                    <h1 className="text-xl font-black text-white tracking-tight uppercase tracking-[0.1em]">Gestión de Contenidos</h1>
                    <button
                        onClick={() => router.push('/admin/content/new')}
                        className="p-3 rounded-2xl bg-primary text-white shadow-lg shadow-primary/20 hover:scale-110 active:scale-95 transition-all"
                    >
                        <Plus size={20} />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex px-8 gap-10 overflow-x-auto hide-scrollbar pt-4">
                    {['Prédicas', 'Cursos', 'Materiales'].map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`pb-4 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative ${activeTab === tab ? 'text-primary' : 'text-slate-500 hover:text-slate-300'
                                }`}
                        >
                            {tab}
                            {activeTab === tab && (
                                <div className="absolute bottom-0 left-0 w-full h-1 bg-primary rounded-full shadow-[0_0_8px_#259df4]"></div>
                            )}
                        </button>
                    ))}
                </div>
            </div>

            {/* Search Bar */}
            <div className="px-8 py-8">
                <div className="relative group">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors" size={20} />
                    <input
                        type="text"
                        placeholder="Buscar por título o pastor..."
                        className="w-full bg-slate-900/40 border border-white/5 rounded-2xl py-4 pl-14 pr-6 text-sm font-medium focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all outline-none backdrop-blur-xl"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
            </div>

            {/* Content List */}
            <main className="flex-1 px-8 pb-32 space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-700">
                {filteredItems.map((item) => (
                    <div key={item.id} className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-[2rem] p-6 shadow-2xl group hover:border-white/10 transition-all">
                        <div className="flex items-start justify-between mb-6">
                            <div className="flex-1">
                                <h4 className="text-lg font-black text-white tracking-tight group-hover:text-primary transition-colors">{item.title}</h4>
                                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">
                                    {item.author} • <span className="text-slate-700">{item.date}</span>
                                </p>
                            </div>
                            <span className={`text-[9px] font-black uppercase tracking-widest px-3 py-1 rounded-lg border ${item.status === 'Activo'
                                    ? 'bg-primary/10 text-primary border-primary/20 shadow-lg shadow-primary/5'
                                    : 'bg-slate-800 text-slate-500 border-white/5'
                                }`}>
                                {item.status}
                            </span>
                        </div>

                        <div className="flex items-center justify-between pt-6 border-t border-white/5">
                            <div className="flex items-center gap-2">
                                <button className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all border ${item.visible
                                        ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                                        : 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                                    }`}>
                                    {item.visible ? <Eye size={14} /> : <EyeOff size={14} />}
                                    {item.visible ? 'Visible' : 'Oculto'}
                                </button>
                            </div>
                            <button className="flex items-center gap-2 text-primary bg-primary/10 hover:bg-primary hover:text-white px-5 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all active:scale-95 border border-primary/20">
                                <Edit3 size={16} />
                                Editar
                            </button>
                        </div>
                    </div>
                ))}

                {filteredItems.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-20 text-center space-y-4 opacity-50">
                        <div className="size-20 rounded-[2rem] bg-white/5 flex items-center justify-center text-slate-700">
                            <Search size={32} />
                        </div>
                        <p className="text-[10px] font-black text-slate-600 uppercase tracking-[0.2em]">No se encontraron resultados</p>
                    </div>
                )}
            </main>
        </div>
    );
}
