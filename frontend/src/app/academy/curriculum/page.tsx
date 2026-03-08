"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { ArrowLeft, GripVertical, CheckCircle, Link as LinkIcon, PlusCircle, BookOpen } from 'lucide-react';
import Link from 'next/link';

export default function StudentCurriculum() {
    const { isAuthenticated } = useAuth();
    const router = useRouter();
    const [activeSemester, setActiveSemester] = useState(1);

    if (!isAuthenticated) return null;

    const semesters = [1, 2, 3, 4];

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 font-display selection:bg-primary/30 relative overflow-x-hidden">
            {/* Ambient Backgrounds */}
            <div className="fixed inset-0 z-0 bg-slate-950 pointer-events-none">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/10 via-slate-950 to-slate-950 opacity-60 blur-3xl rounded-full mix-blend-screen"></div>
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col h-screen">
                {/* Header */}
                <div className="flex items-center p-6 justify-between sticky top-0 bg-slate-950/80 backdrop-blur-xl border-b border-white/5 z-20">
                    <button onClick={() => router.back()} className="text-primary flex size-10 shrink-0 items-center justify-center rounded-full bg-primary/10 hover:bg-primary/20 transition-colors">
                        <ArrowLeft size={20} />
                    </button>
                    <h2 className="text-white text-lg font-bold leading-tight tracking-tight flex-1 text-center">Organizador Curricular</h2>
                    <div className="flex w-10 items-center justify-end">
                        <span className="text-primary text-[10px] uppercase font-black tracking-widest cursor-pointer hover:underline">Editar</span>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto hide-scrollbar pb-24 relative z-10">
                    {/* Semester Navigation */}
                    <div className="flex overflow-x-auto hide-scrollbar px-6 gap-3 py-6">
                        {semesters.map((sem) => (
                            <button
                                key={sem}
                                onClick={() => setActiveSemester(sem)}
                                className={`flex-none px-6 py-3 rounded-2xl font-bold text-[10px] uppercase tracking-widest transition-all whitespace-nowrap ${activeSemester === sem
                                        ? 'bg-primary text-white shadow-xl shadow-primary/30 border border-primary/20'
                                        : 'bg-slate-900 border border-white/10 text-slate-400 hover:text-white hover:border-white/20'
                                    }`}
                            >
                                Semestre {sem}
                            </button>
                        ))}
                    </div>

                    {/* Section Title */}
                    <div className="px-6 mb-8 flex items-end justify-between border-b border-white/5 pb-4">
                        <h2 className="text-3xl font-black text-white tracking-tight leading-none bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">Semestre {activeSemester}</h2>
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest bg-white/5 px-2 py-1 rounded">3 Materias</span>
                    </div>

                    {/* Course List */}
                    <div className="px-6 space-y-4 animate-in fade-in slide-in-from-bottom-8 duration-500">
                        {/* Course Card 1 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-[2rem] p-5 shadow-xl border border-white/5 flex items-center gap-4 group hover:border-primary/30 transition-all cursor-pointer">
                            <div className="text-slate-600 cursor-grab active:cursor-grabbing hover:text-white transition-colors p-2">
                                <GripVertical size={20} />
                            </div>
                            <div className="flex-1">
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-black uppercase tracking-widest mb-3">
                                    <CheckCircle size={12} />
                                    Requisitos
                                </div>
                                <h3 className="text-lg font-bold text-white leading-tight mb-1 group-hover:text-primary transition-colors">Teología Sistemática I</h3>
                                <p className="text-xs text-slate-400 font-medium">Dr. Ricardo Méndez</p>
                            </div>
                            <div className="relative w-20 h-20 rounded-2xl overflow-hidden shrink-0 border border-white/5 group-hover:border-primary/30 transition-colors shadow-inner flex items-center justify-center bg-slate-800">
                                <BookOpen className="text-slate-600 w-8 h-8 group-hover:text-primary transition-colors" />
                            </div>
                        </div>

                        {/* Course Card 2 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-[2rem] p-5 shadow-xl border border-white/5 flex items-center gap-4 group hover:border-primary/30 transition-all cursor-pointer">
                            <div className="text-slate-600 cursor-grab active:cursor-grabbing hover:text-white transition-colors p-2">
                                <GripVertical size={20} />
                            </div>
                            <div className="flex-1">
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-white/10 text-[9px] font-black uppercase tracking-widest mb-3">
                                    <LinkIcon size={12} />
                                    Sin Requisitos
                                </div>
                                <h3 className="text-lg font-bold text-white leading-tight mb-1 group-hover:text-primary transition-colors">Historia del Avivamiento</h3>
                                <p className="text-xs text-slate-400 font-medium">Mtra. Elena Gómez</p>
                            </div>
                            <div className="relative w-20 h-20 rounded-2xl overflow-hidden shrink-0 border border-white/5 group-hover:border-primary/30 transition-colors shadow-inner flex items-center justify-center bg-slate-800">
                                <BookOpen className="text-slate-600 w-8 h-8 group-hover:text-primary transition-colors" />
                            </div>
                        </div>

                        {/* Course Card 3 */}
                        <div className="bg-slate-900/50 backdrop-blur-xl rounded-[2rem] p-5 shadow-xl border border-white/5 flex items-center gap-4 group hover:border-primary/30 transition-all cursor-pointer">
                            <div className="text-slate-600 cursor-grab active:cursor-grabbing hover:text-white transition-colors p-2">
                                <GripVertical size={20} />
                            </div>
                            <div className="flex-1">
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-black uppercase tracking-widest mb-3">
                                    <CheckCircle size={12} />
                                    Requisitos
                                </div>
                                <h3 className="text-lg font-bold text-white leading-tight mb-1 group-hover:text-primary transition-colors">Hermenéutica Bíblica</h3>
                                <p className="text-xs text-slate-400 font-medium">Pbro. Samuel Torres</p>
                            </div>
                            <div className="relative w-20 h-20 rounded-2xl overflow-hidden shrink-0 border border-white/5 group-hover:border-primary/30 transition-colors shadow-inner flex items-center justify-center bg-slate-800">
                                <BookOpen className="text-slate-600 w-8 h-8 group-hover:text-primary transition-colors" />
                            </div>
                        </div>

                        {/* Add New Course Button */}
                        <Link href="/academy" className="bg-primary/5 backdrop-blur-xl rounded-[2rem] p-6 shadow-none border-2 border-dashed border-primary/20 flex flex-col items-center justify-center gap-3 group hover:border-primary/50 hover:bg-primary/10 transition-all cursor-pointer mt-8">
                            <div className="text-primary/50 group-hover:text-primary transition-colors">
                                <PlusCircle size={32} />
                            </div>
                            <p className="text-primary font-bold text-xs uppercase tracking-widest">Añadir Nueva Materia</p>
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
