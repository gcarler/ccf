"use client";

import React from 'react';
import OptimizedImage from "@/components/ui/OptimizedImage";
import { Award, Download, Share2 } from 'lucide-react';

interface CertificateProps {
    data: {
        certificate_code: string;
        issued_at: string;
        certificate_type: string;
        enrollment: {
            student: { username: string };
            course: { title: string };
        }
    };
}

export default function CertificateView({ data }: CertificateProps) {
    const issueDate = new Date(data.issued_at).toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });

    return (
        <div className="max-w-4xl mx-auto space-y-3 animate-fade-in">
            {/* Professional Certificate Render */}
            <div className="relative aspect-[1.414/1] w-full bg-[hsl(var(--bg-primary))] dark:bg-slate-900 border-[16px] border-slate-900 dark:border-blue-900/20 shadow-2xl p-4 flex flex-col items-center justify-between text-center overflow-hidden group">
                {/* Background Decoration */}
                <div className="absolute top-0 right-0 w-64 h-48 bg-slate-50 dark:bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                <div className="absolute bottom-0 left-0 w-64 h-48 bg-slate-50 dark:bg-blue-500/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

                {/* Header */}
                <div className="relative z-10 space-y-4">
                    <div className="size-10 bg-slate-900 dark:bg-[hsl(var(--primary))] rounded-lg mx-auto flex items-center justify-center text-white shadow-xl">
                        <Award size={40} />
                    </div>
                    <h1 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Certificado de Logro Academico</h1>
                </div>

                {/* Body */}
                <div className="relative z-10 space-y-3 py-8">
                    <div>
                        <p className="text-slate-500 dark:text-slate-400 italic font-serif text-lg">Este documento certifica que</p>
                        <h2 className="text-xl lg:text-xl font-bold text-slate-900 dark:text-white tracking-tight mt-2 uppercase">
                            {data.enrollment.student.username}
                        </h2>
                    </div>

                    <div className="max-w-lg mx-auto">
                        <p className="text-slate-500 dark:text-slate-400 font-medium">Ha completado satisfactoriamente los requisitos academicos para el curso de:</p>
                        <h3 className="text-xl font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] mt-2">
                            {data.enrollment.course.title}
                        </h3>
                    </div>
                </div>

                {/* Footer */}
                <div className="relative z-10 w-full flex justify-between items-end border-t border-slate-100 dark:border-white/5 pt-8">
                    <div className="text-left space-y-1">
                        <p className="font-semibold text-slate-400 uppercase tracking-wide">Fecha de Emision</p>
                        <p className="text-sm font-bold text-slate-700 dark:text-slate-200">{issueDate}</p>
                    </div>

                    <div className="flex flex-col items-center gap-2">
                        <div className="relative size-10 border-2 border-slate-100 dark:border-white/10 rounded-lg overflow-hidden bg-[hsl(var(--bg-primary))] p-1">
                            <OptimizedImage
                                src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(typeof window !== 'undefined' ? window.location.origin : 'https://ccf.la')}/academy/certificates/${data.certificate_code}`}
                                alt="QR Code"
                                fill
                                sizes="40px"
                            />
                        </div>
                        <p className="font-semibold text-slate-400 uppercase tracking-tighter">Validar: {data.certificate_code}</p>
                    </div>

                    <div className="text-right space-y-1">
                        <p className="font-semibold text-slate-400 uppercase tracking-wide">Firma Autorizada</p>
                        <p className="text-sm font-bold text-slate-700 dark:text-slate-200 font-serif italic">Direccion Academica CCF</p>
                    </div>
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-4">
                <button className="px-3 py-1.5 bg-slate-900 dark:bg-[hsl(var(--bg-primary))] text-white dark:text-slate-900 rounded-lg font-black text-xs uppercase tracking-wide flex items-center gap-2 shadow-xl active:scale-95 transition-all">
                    <Download size={18} /> Descargar PDF
                </button>
                <button className="px-3 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg font-black text-xs uppercase tracking-wide flex items-center gap-2 hover:bg-slate-50 transition-all active:scale-95">
                    <Share2 size={18} /> Compartir Logro
                </button>
            </div>
        </div>
    );
}
