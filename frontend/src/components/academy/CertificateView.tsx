"use client";

import React, { useState, useEffect } from 'react';
import { Award, Download, Share2, Copy, Check } from 'lucide-react';

interface CertificateProps {
    data: {
        certificate_code: string;
        issued_at: string;
        certificate_type: string;
        enrollment: {
            student: { username: string };
            course: { title: string };
        };
    };
}

export default function CertificateView({ data }: CertificateProps) {
    const issueDate = new Date(data.issued_at).toLocaleDateString('es-ES', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    });

    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://ccf.la';
    const validationUrl = `${origin}/academy/certificates/${data.certificate_code}`;
    const validationPath = validationUrl.replace(/^https?:\/\/[^/]+/, '');

    // ACAD-HIGH-002: cero dependencia externa (sin api.qrserver.com).
    // ACAD-LOW-001: handlers reales para Download y Share.
    const [copyState, setCopyState] = useState<'idle' | 'copied'>('idle');

    useEffect(() => {
        let timer: ReturnType<typeof setTimeout> | undefined;
        if (copyState === 'copied') {
            timer = setTimeout(() => setCopyState('idle'), 1800);
        }
        return () => { if (timer) clearTimeout(timer); };
    }, [copyState]);

    const handleCopy = async () => {
        try {
            if (typeof navigator !== 'undefined' && navigator.clipboard) {
                await navigator.clipboard.writeText(validationUrl);
            }
            setCopyState('copied');
        } catch {
            setCopyState('copied');
        }
    };

    const handleShare = async () => {
        if (typeof navigator !== 'undefined' && (navigator as any).share) {
            try {
                await (navigator as any).share({
                    title: `Certificado CCF — ${data.enrollment.course.title}`,
                    text: `${data.enrollment.student.username} ${
                        data.certificate_type ? '(' + data.certificate_type + ')' : ''
                    }`,
                    url: validationUrl,
                });
                return;
            } catch {
                /* user cancelled or unsupported */
            }
        }
        await handleCopy();
    };

    const handleDownload = () => {
        // Genera un blob imprimible (HTML serializado) y lo descarga.
        const css = `
        body { font-family: Georgia, serif; padding: 40px; background: #f8fafc; color: #001b48; text-align: center; }
        .badge { display: inline-block; padding: 6px 16px; border-radius: 999px; background: #001b48; color: white; font-weight: bold; letter-spacing: 0.18em; font-size: 12px; }
        h1 { font-size: 24px; letter-spacing: 0.04em; text-transform: uppercase; }
        h2 { font-size: 20px; color: #018abd; }
        .code { font-family: monospace; padding: 4px 10px; border: 1px solid #cbd5f5; border-radius: 6px; background: white; }
        `;
        const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Certificado ${
            data.certificate_code
        }</title><style>${css}</style></head><body>
        <span class="badge">Certificado Académico CCF</span>
        <h1>${data.certificate_type ?? 'Certificado de Logro Académico'}</h1>
        <p>Por la presente se certifica que</p>
        <h2>${data.enrollment.student.username}</h2>
        <p>ha completado satisfactoriamente los requisitos académicos del curso</p>
        <h2>${data.enrollment.course.title}</h2>
        <p>Emitido el ${issueDate}</p>
        <p>Código de validación: <span class="code">${data.certificate_code}</span></p>
        <p style="color:#64748b;font-size:12px">Validar en: ${validationUrl}</p>
        </body></html>`;
        const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `certificado-${data.certificate_code}.html`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="max-w-4xl mx-auto space-y-3 animate-fade-in">
            {/* Professional Certificate Render */}
            <div className="relative aspect-[1.414/1] w-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] border-[16px] border-[hsl(var(--border))] dark:border-blue-900/20 shadow-2xl p-4 flex flex-col items-center justify-between text-center overflow-hidden group">
                {/* Background Decoration */}
                <div className="absolute top-0 right-0 w-64 h-48 bg-[hsl(var(--surface-1))] dark:bg-blue-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                <div className="absolute bottom-0 left-0 w-64 h-48 bg-[hsl(var(--surface-1))] dark:bg-blue-500/5 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

                {/* Header */}
                <div className="relative z-10 space-y-4">
                    <div className="size-10 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--primary))] rounded-lg mx-auto flex items-center justify-center text-white shadow-xl">
                        <Award size={40} />
                    </div>
                    <h1 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        Certificado de Logro Academico
                    </h1>
                </div>

                {/* Body */}
                <div className="relative z-10 space-y-3 py-8">
                    <div>
                        <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] italic font-serif text-lg">
                            Este documento certifica que
                        </p>
                        <h2 className="text-xl lg:text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight mt-2 uppercase">
                            {data.enrollment.student.username}
                        </h2>
                    </div>

                    <div className="max-w-lg mx-auto">
                        <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] font-medium">
                            Ha completado satisfactoriamente los requisitos academicos para el curso de:
                        </p>
                        <h3 className="text-xl font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] mt-2">
                            {data.enrollment.course.title}
                        </h3>
                    </div>
                </div>

                {/* Footer */}
                <div className="relative z-10 w-full flex justify-between items-end border-t border-[hsl(var(--border))] dark:border-white/5 pt-8">
                    <div className="text-left space-y-1">
                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                            Fecha de Emision
                        </p>
                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                            {issueDate}
                        </p>
                    </div>

                    <div className="flex flex-col items-center gap-2">
                        <div className="relative px-4 py-2 border-2 border-[hsl(var(--border))] dark:border-white/10 rounded-lg overflow-hidden bg-[hsl(var(--bg-primary))]">
                            <p className="text-[10px] font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">
                                Codigo de validacion
                            </p>
                            <code className="font-mono text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white break-all">
                                {data.certificate_code}
                            </code>
                        </div>
                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-tighter text-[10px]">
                            Validar en:{' '}
                            <span className="text-[hsl(var(--primary))]">
                                {validationPath}
                            </span>
                        </p>
                    </div>

                    <div className="text-right space-y-1">
                        <p className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                            Firma Autorizada
                        </p>
                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] font-serif italic">
                            Direccion Academica CCF
                        </p>
                    </div>
                </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-center gap-3 flex-wrap">
                <button
                    onClick={handleDownload}
                    className="px-3 py-2 bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] rounded-lg font-black text-[11px] uppercase tracking-wide flex items-center gap-2 shadow-xl active:scale-95 transition-all"
                >
                    <Download size={16} /> Descargar
                </button>
                <button
                    onClick={handleShare}
                    className="px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg font-black text-[11px] uppercase tracking-wide flex items-center gap-2 hover:bg-[hsl(var(--surface-1))] transition-all active:scale-95"
                >
                    <Share2 size={16} /> Compartir Logro
                </button>
                <button
                    onClick={handleCopy}
                    className="px-3 py-2 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg font-black text-[11px] uppercase tracking-wide flex items-center gap-2 hover:bg-[hsl(var(--surface-1))] transition-all active:scale-95"
                >
                    {copyState === 'copied' ? (
                        <>
                            <Check size={16} /> Copiado
                        </>
                    ) : (
                        <>
                            <Copy size={16} /> Copiar Link
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}
