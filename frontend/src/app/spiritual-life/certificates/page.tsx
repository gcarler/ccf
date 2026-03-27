"use client";

import React from 'react';
import { 
    Download, 
    FileCheck, 
    Award, 
    ShieldCheck, 
    ExternalLink,
    Waves
} from 'lucide-react';

export default function DigitalCertificatesPage() {
    return (
        <div className="p-8 space-y-12 animate-in fade-in duration-1000">
            <div className="flex flex-col gap-2">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-cyan-500/10 text-cyan-500 rounded-full text-[10px] font-black uppercase tracking-[0.2em] w-fit">
                    <ShieldCheck size={12} /> Certificacion Digital Oficial
                </div>
                <h1 className="text-4xl font-black tracking-tighter text-white uppercase italic">
                    Mis <span className="text-cyan-500">Certificados</span>
                </h1>
                <p className="text-muted-foreground text-sm max-w-2xl">
                    Descarga tus actas de bautismo y reconocimientos ministeriales con validez digital dentro del ecosistema CCF.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {[
                    { title: 'Acta de Bautismo en Aguas', date: '15 de Mayo, 2025', id: 'CCF-B-2025-001', type: 'Sacramento' },
                    { title: 'Diploma Fundamentos de la Fe', date: '10 de Marzo, 2026', id: 'CCF-A-2026-442', type: 'Academia' },
                ].map((cert, i) => (
                    <div key={i} className="group bg-[#1e1f21] border border-white/5 p-8 rounded-[2rem] hover:border-cyan-500/30 transition-all duration-500 relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-8 opacity-[0.02] group-hover:opacity-10 group-hover:rotate-12 transition-all duration-700">
                            <Award size={150} />
                        </div>
                        
                        <div className="space-y-6 relative z-10">
                            <div className="flex items-start justify-between">
                                <div className="w-16 h-16 bg-cyan-500/10 rounded-2xl flex items-center justify-center text-cyan-500">
                                    {cert.type === 'Sacramento' ? <Waves size={32} /> : <FileCheck size={32} />}
                                </div>
                                <span className="text-[10px] font-black text-cyan-500 uppercase tracking-widest bg-cyan-500/5 px-3 py-1 rounded-full border border-cyan-500/20">
                                    {cert.type}
                                </span>
                            </div>

                            <div>
                                <h3 className="text-2xl font-black text-white italic uppercase tracking-tight mb-1">{cert.title}</h3>
                                <p className="text-xs text-muted-foreground font-bold uppercase tracking-widest">{cert.date}</p>
                            </div>

                            <div className="pt-6 border-t border-white/5 flex items-center justify-between">
                                <div className="text-[10px] text-muted-foreground font-mono uppercase">ID: {cert.id}</div>
                                <div className="flex items-center gap-2">
                                    <button className="flex items-center gap-2 px-4 py-2 bg-white text-black text-[10px] font-black uppercase tracking-widest rounded-xl hover:bg-cyan-500 transition-colors">
                                        <Download size={14} /> PDF
                                    </button>
                                    <button className="p-2 bg-white/5 hover:bg-white/10 text-white rounded-xl transition-all">
                                        <ExternalLink size={16} />
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="bg-cyan-500/5 border border-cyan-500/10 p-8 rounded-3xl flex flex-col md:flex-row items-center gap-6">
                <div className="w-16 h-16 bg-cyan-500 text-black rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.4)]">
                    <ShieldCheck size={32} />
                </div>
                <div className="flex-1 text-center md:text-left space-y-1">
                    <h4 className="text-white font-bold uppercase tracking-tight">Verificación de Autenticidad</h4>
                    <p className="text-sm text-muted-foreground">Cada certificado contiene un código único y un token QR para validar su veracidad ante autoridades eclesiásticas.</p>
                </div>
                <button className="px-6 py-3 bg-white/5 text-white text-xs font-black uppercase tracking-widest rounded-2xl hover:bg-white/10 transition-all border border-white/5">
                    Validar Código
                </button>
            </div>
        </div>
    );
}
