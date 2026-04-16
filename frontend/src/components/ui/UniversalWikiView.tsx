"use client";

import React, { useState, useEffect } from 'react';
import { 
    BookOpen, Save, Trash2, Search, 
    ChevronRight, MoreHorizontal, Sparkles, 
    FileText, Zap, Link2, Clock, ShieldCheck
} from 'lucide-react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface WikiProps {
    moduleName: string;
    storageKey?: string;
    onSave?: (content: string) => void;
}

export default function UniversalWikiView({ moduleName, storageKey, onSave }: WikiProps) {
    const [content, setContent] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<string | null>(null);

    // Persistencia local para el placeholder funcional
    useEffect(() => {
        if (storageKey) {
            const saved = localStorage.getItem(storageKey);
            if (saved) setContent(saved);
        }
    }, [storageKey]);

    const handleSave = () => {
        setIsSaving(true);
        if (storageKey) {
            localStorage.setItem(storageKey, content);
        }
        onSave?.(content);
        
        setTimeout(() => {
            setIsSaving(false);
            setLastSaved(new Date().toLocaleTimeString());
        }, 800);
    };

    return (
        <div className="flex h-[700px] bg-white dark:bg-[#0b0d11] rounded-[2.5rem] border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
            
            {/* ─── Sidebar de Navegación Wiki ─── */}
            <aside className="w-80 border-r border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02] flex flex-col">
                <div className="p-8 border-b border-slate-100 dark:border-white/5 flex items-center gap-4">
                    <div className="size-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                        <BookOpen size={20} />
                    </div>
                    <div>
                        <h4 className="text-xs font-black uppercase tracking-widest text-slate-900 dark:text-white">Wiki Pro</h4>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{moduleName}</p>
                    </div>
                </div>

                <div className="p-4 space-y-2 flex-1 overflow-y-auto">
                    <div className="p-4 bg-white dark:bg-white/5 border border-indigo-100 dark:border-indigo-500/20 rounded-2xl shadow-sm">
                        <div className="flex items-center gap-3 text-indigo-600 mb-1">
                            <FileText size={16} />
                            <span className="text-[11px] font-black uppercase tracking-widest">General</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-medium">Protocolos y estándares del módulo {moduleName}.</p>
                    </div>
                    
                    {[1, 2, 3].map(i => (
                        <div key={i} className="p-4 flex items-center justify-between group hover:bg-slate-200/50 dark:hover:bg-white/5 rounded-2xl transition-all cursor-pointer">
                            <div className="flex items-center gap-3">
                                <FileText size={16} className="text-slate-300 group-hover:text-indigo-500" />
                                <span className="text-[11px] font-black uppercase tracking-widest text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white">Capítulo {i}</span>
                            </div>
                            <ChevronRight size={14} className="text-slate-200 group-hover:text-indigo-400" />
                        </div>
                    ))}
                </div>

                <div className="p-6 border-t border-slate-100 dark:border-white/5 bg-slate-100/50 dark:bg-black/20">
                    <button className="w-full py-4 bg-slate-900 dark:bg-white/5 text-white rounded-[1.5rem] text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 hover:opacity-80 transition-all">
                        <Link2 size={14} /> Vincular Recursos
                    </button>
                </div>
            </aside>

            {/* ─── Editor de Contenido ─── */}
            <main className="flex-1 flex flex-col bg-white dark:bg-[#0b0d11]">
                <header className="px-10 py-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <ShieldCheck size={18} className="text-indigo-600" />
                        <h2 className="text-xl font-black italic tracking-tighter text-slate-900 dark:text-white uppercase leading-none">Protocolo de Operación</h2>
                    </div>
                    <div className="flex items-center gap-6">
                        {lastSaved && (
                            <div className="flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-emerald-500" />
                                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest italic">Guardado a las {lastSaved}</span>
                            </div>
                        )}
                        <button 
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-8 py-3 bg-indigo-600 text-white rounded-[1.5rem] text-[10px] font-black uppercase tracking-widest flex items-center gap-3 shadow-xl shadow-indigo-500/20 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {isSaving ? <Sparkles size={14} className="animate-spin" /> : <Save size={14} />}
                            {isSaving ? 'Sincronizando...' : 'Guardar Wiki'}
                        </button>
                    </div>
                </header>

                <div className="flex-1 p-10 relative">
                    <div className="absolute top-10 right-10 opacity-5 pointer-events-none">
                        <Zap size={200} fill="currentColor" className="text-indigo-600" />
                    </div>
                    <textarea 
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        placeholder="Comienza a redactar la documentación oficial para este espacio de trabajo..."
                        className="w-full h-full bg-transparent resize-none border-none outline-none text-lg font-medium text-slate-700 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-white/10 leading-relaxed scrollbar-thin"
                    />
                </div>

                <footer className="p-6 border-t border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-transparent flex items-center justify-between">
                    <div className="flex items-center gap-6">
                        <div className="flex items-center gap-2">
                            <Clock size={14} className="text-slate-400" />
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Editado por: Optimus Admin</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="p-3 text-slate-300 hover:text-rose-500 transition-colors"><Trash2 size={18} /></button>
                        <button className="p-3 text-slate-300 hover:text-indigo-600 transition-colors"><MoreHorizontal size={18} /></button>
                    </div>
                </footer>
            </main>
        </div>
    );
}
