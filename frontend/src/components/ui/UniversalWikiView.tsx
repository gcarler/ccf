"use client";

import React from 'react';
import {
    BookOpen,
    Save,
    Trash2,
    ChevronRight,
    MoreHorizontal,
    Sparkles,
    FileText,
    Zap,
    Link2,
    Clock,
    ShieldCheck,
    Loader2,
} from 'lucide-react';
import { useWikiDocument } from '@/hooks/useWikiDocument';

interface WikiProps {
    moduleName: string;
    storageKey?: string;
    onSave?: (content: string) => void;
}

function toWikiKey(moduleName: string) {
    return `wiki_${moduleName.toLowerCase().replace(/\s+/g, '_').replace(/[^\w-]/g, '')}`;
}

export default function UniversalWikiView({ moduleName, storageKey, onSave }: WikiProps) {
    const pageKey = storageKey || toWikiKey(moduleName);
    const {
        content,
        setContent,
        isLoading,
        isSaving,
        lastSaved,
        error,
        saveNow,
    } = useWikiDocument(pageKey, { title: `${moduleName} Wiki` });

    const handleSave = async () => {
        await saveNow();
        onSave?.(content);
    };

    return (
        <div className="flex h-[700px] bg-white dark:bg-[#0b0d11] rounded-lg border border-slate-200 dark:border-white/5 overflow-hidden shadow-sm">
            <aside className="w-80 border-r border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02] flex flex-col">
                <div className="p-4 border-b border-slate-100 dark:border-white/5 flex items-center gap-4">
                    <div className="size-10 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                        <BookOpen size={20} />
                    </div>
                    <div>
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-900 dark:text-white">Wiki Pro</h4>
                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">{moduleName}</p>
                    </div>
                </div>

                <div className="p-4 space-y-2 flex-1 overflow-y-auto">
                    <div className="p-4 bg-white dark:bg-white/5 border border-indigo-100 dark:border-indigo-500/20 rounded-lg shadow-sm">
                        <div className="flex items-center gap-3 text-indigo-600 mb-1">
                            <FileText size={16} />
                            <span className="text-[11px] font-semibold uppercase tracking-wide">General</span>
                        </div>
                        <p className="text-[10px] text-slate-400 font-medium">Protocolos y estandares del modulo {moduleName}.</p>
                    </div>

                    {[1, 2, 3].map((index) => (
                        <div key={index} className="p-4 flex items-center justify-between group hover:bg-slate-200/50 dark:hover:bg-white/5 rounded-lg transition-all cursor-pointer">
                            <div className="flex items-center gap-3">
                                <FileText size={16} className="text-slate-300 group-hover:text-indigo-500" />
                                <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400 group-hover:text-slate-900 dark:group-hover:text-white">Capitulo {index}</span>
                            </div>
                            <ChevronRight size={14} className="text-slate-200 group-hover:text-indigo-400" />
                        </div>
                    ))}
                </div>

                <div className="p-3 border-t border-slate-100 dark:border-white/5 bg-slate-100/50 dark:bg-black/20">
                    <button className="w-full py-1.5 bg-slate-900 dark:bg-white/5 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center justify-center gap-2 hover:opacity-80 transition-all">
                        <Link2 size={14} /> Vincular Recursos
                    </button>
                </div>
            </aside>

            <main className="flex-1 flex flex-col bg-white dark:bg-[#0b0d11]">
                <header className="px-4 py-2 border-b border-slate-100 dark:border-white/5 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <ShieldCheck size={18} className="text-indigo-600" />
                        <h2 className="text-xl font-black italic tracking-tighter text-slate-900 dark:text-white uppercase leading-none">Protocolo de Operacion</h2>
                    </div>
                    <div className="flex items-center gap-3">
                        {lastSaved && (
                            <div className="flex items-center gap-2">
                                <div className="size-1.5 rounded-full bg-emerald-500" />
                                <span className="font-semibold text-slate-400 uppercase tracking-wide italic">Guardado a las {lastSaved.toLocaleTimeString()}</span>
                            </div>
                        )}
                        <button
                            onClick={handleSave}
                            disabled={isSaving}
                            className="px-4 py-3 bg-indigo-600 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide flex items-center gap-3 shadow-xl shadow-indigo-500/20 hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                        >
                            {isSaving ? <Sparkles size={14} className="animate-spin" /> : <Save size={14} />}
                            {isSaving ? 'Sincronizando...' : 'Guardar Wiki'}
                        </button>
                    </div>
                </header>

                <div className="flex-1 p-4 relative">
                    <div className="absolute top-10 right-10 opacity-5 pointer-events-none">
                        <Zap size={200} fill="currentColor" className="text-indigo-600" />
                    </div>
                    {isLoading ? (
                        <div className="flex h-full items-center justify-center gap-2 text-sm font-bold text-slate-400">
                            <Loader2 size={16} className="animate-spin" />
                            Cargando wiki compartida...
                        </div>
                    ) : (
                        <textarea
                            value={content}
                            onChange={(event) => setContent(event.target.value)}
                            placeholder="Comienza a redactar la documentacion oficial para este espacio de trabajo..."
                            className="w-full h-full bg-transparent resize-none border-none outline-none text-lg font-medium text-slate-700 dark:text-slate-100 placeholder:text-slate-300 dark:placeholder:text-white/10 leading-relaxed scrollbar-thin"
                        />
                    )}
                    {error && (
                        <p className="absolute bottom-4 left-10 rounded-full bg-rose-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-rose-600 dark:bg-rose-500/10 dark:text-rose-300">
                            {error}
                        </p>
                    )}
                </div>

                <footer className="p-3 border-t border-slate-100 dark:border-white/5 bg-slate-50 dark:bg-transparent flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Clock size={14} className="text-slate-400" />
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wide">Persistencia compartida</span>
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
