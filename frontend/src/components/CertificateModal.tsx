"use client";

import React from 'react';
import { 
    X, 
    Download, 
    Printer, 
    Award, 
    ShieldCheck, 
    Calendar, 
    QrCode,
    Verified
} from 'lucide-react';

interface Certificate {
    id: number;
    enrollment_id: number;
    certificate_code: string;
    certificate_type?: string | null;
    issued_at: string;
}

interface Enrollment {
    id: number;
    course: {
        title: string;
        modality: string;
    };
    student?: {
        username: string;
        email: string;
    };
}

interface CertificateModalProps {
    certificate: Certificate;
    enrollment: Enrollment;
    userName: string;
    onClose: () => void;
}

export default function CertificateModal({ certificate, enrollment, userName, onClose }: CertificateModalProps) {
    const handlePrint = () => {
        window.print();
    };

    const handleDownloadImage = () => {
        // En una implementación real usaríamos html2canvas o similar.
        // Por ahora, sugerimos imprimir como PDF para máxima calidad.
        window.print();
    };

    return (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-0 md:p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-300">
            <div className="relative w-full max-w-6xl bg-white dark:bg-[#0b0d11] md:rounded-lg shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300 flex flex-col md:flex-row h-full md:h-[min(90vh,800px)]">
                
                {/* Close Button - Premium Positioning */}
                <button 
                    onClick={onClose}
                    className="absolute top-6 right-6 p-3 bg-white/10 hover:bg-white/20 text-white backdrop-blur-md rounded-full transition-all z-50 border border-white/10 print:hidden"
                >
                    <X size={24} />
                </button>

                {/* Sidebar - Control Panel */}
                <div className="w-full md:w-80 bg-slate-50 dark:bg-[#15171c] p-4 border-r border-slate-100 dark:border-white/5 print:hidden flex flex-col shrink-0">
                    <div className="mb-3">
                        <div className="size-8 bg-blue-600 text-white rounded-lg flex items-center justify-center mb-3 shadow-xl shadow-blue-600/20">
                            <Award size={36} />
                        </div>
                        <h2 className="text-lg font-black text-slate-900 dark:text-white tracking-tighter leading-tight">Certificado Oficial</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400 mt-3 font-medium leading-relaxed">
                            Este documento avala tu formación teológica y ministerial en la Comunidad Cristiana El Faro.
                        </p>
                    </div>

                    <div className="space-y-6 mb-auto">
                        <div className="p-3 bg-white dark:bg-black/20 rounded-lg border border-slate-100 dark:border-white/5 space-y-4 shadow-sm">
                            <div className="flex items-start gap-3">
                                <div className="p-2 bg-blue-50 dark:bg-blue-500/10 rounded-md text-blue-600">
                                    <ShieldCheck size={18} />
                                </div>
                                <div className="min-w-0">
                                    <p className="font-semibold text-slate-400 uppercase tracking-wide">Validación</p>
                                    <p className="text-sm font-bold text-slate-900 dark:text-white truncate">{certificate.certificate_code}</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <div className="p-2 bg-sky-50 dark:bg-sky-500/10 rounded-md text-sky-600">
                                    <Calendar size={18} />
                                </div>
                                <div className="min-w-0">
                                    <p className="font-semibold text-slate-400 uppercase tracking-wide">Emisión</p>
                                    <p className="text-sm font-bold text-slate-900 dark:text-white">
                                        {new Date(certificate.issued_at).toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' })}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="p-3 bg-amber-50 dark:bg-amber-500/5 rounded-lg border border-amber-200/50 dark:border-amber-500/10 flex items-center gap-4">
                            <Verified className="text-amber-500 shrink-0" size={24} />
                            <p className="text-[11px] font-bold text-amber-800 dark:text-amber-200 leading-tight">
                                Verificado por el motor de inteligencia ministerial Optimus Brain.
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 gap-3 mt-3">
                        <button 
                            onClick={handlePrint}
                            className="w-full py-1.5 bg-blue-600 text-white rounded-lg text-xs font-semibold uppercase tracking-wide hover:bg-blue-500 active:scale-[0.98] transition-all flex items-center justify-center gap-3 shadow-xl shadow-blue-600/20"
                        >
                            <Printer size={18} /> Imprimir / PDF
                        </button>
                        <button 
                            onClick={handleDownloadImage}
                            className="w-full py-1.5 bg-white dark:bg-white/5 text-slate-900 dark:text-white border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-semibold uppercase tracking-wide hover:bg-slate-50 dark:hover:bg-white/10 transition-all flex items-center justify-center gap-3"
                        >
                            <Download size={18} /> Guardar Imagen
                        </button>
                    </div>
                </div>

                {/* Certificate Viewport */}
                <div className="flex-1 p-4 md:p-4 flex items-center justify-center bg-[#f1f5f9] dark:bg-black overflow-y-auto">
                    
                    {/* The Actual Document */}
                    <div id="certificate-to-print" className="certificate-paper w-full aspect-[1.414/1] max-w-[850px] bg-white border-[16px] border-double border-[#e2e8f0] p-4 md:p-4 relative flex flex-col items-center text-center shadow-[0_40px_100px_-20px_rgba(0,0,0,0.3)] print:shadow-none">
                        
                        {/* Elegant Corner Motifs */}
                        <div className="absolute top-4 left-4 size-10 border-t-4 border-l-4 border-amber-400/30 rounded-tl-[2rem]"></div>
                        <div className="absolute top-4 right-4 size-10 border-t-4 border-r-4 border-amber-400/30 rounded-tr-[2rem]"></div>
                        <div className="absolute bottom-4 left-4 size-10 border-b-4 border-l-4 border-amber-400/30 rounded-bl-[2rem]"></div>
                        <div className="absolute bottom-4 right-4 size-10 border-b-4 border-r-4 border-amber-400/30 rounded-br-[2rem]"></div>

                        {/* Background Watermark */}
                        <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none">
                            <Award size={500} strokeWidth={0.5} />
                        </div>

                        {/* Header */}
                        <div className="mb-3 flex flex-col items-center relative z-10">
                            <div className="size-8 bg-slate-900 text-white rounded-full flex items-center justify-center mb-3 shadow-2xl">
                                <Award size={44} />
                            </div>
                            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">Comunidad Cristiana El Faro</h3>
                            <div className="h-0.5 w-12 bg-amber-400 rounded-full"></div>
                        </div>

                        <h1 className="text-xl md:text-xl font-serif italic text-slate-900 mb-3 relative z-10">Diploma de Reconocimiento</h1>
                        
                        <p className="text-slate-500 font-bold italic mb-3 uppercase tracking-wide text-[10px] relative z-10">Se otorga con distinción a:</p>
                        <div className="relative mb-3 px-4 z-10">
                            <h2 className="text-lg md:text-xl font-black text-slate-900 tracking-tight">
                                {userName}
                            </h2>
                            <div className="absolute -bottom-4 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>
                        </div>

                        <p className="text-slate-600 max-w-xl leading-relaxed mb-3 text-xl font-medium relative z-10">
                            Por haber culminado con excelencia académica todos los módulos, evaluaciones y requisitos prácticos del curso:
                            <br />
                            <span className="font-black text-lg text-slate-900 mt-4 block tracking-tight uppercase">&quot;{enrollment.course.title}&quot;</span>
                        </p>

                        {/* Signatures & Seal Area */}
                        <div className="mt-auto w-full grid grid-cols-3 items-end pt-12 relative z-10">
                            <div className="flex flex-col items-center">
                                <div className="w-full max-w-[180px] border-t-2 border-slate-900 pt-3">
                                    <p className="font-semibold text-slate-900 uppercase tracking-wide">Coordinación Faro</p>
                                </div>
                            </div>

                            <div className="flex flex-col items-center justify-center relative">
                                {/* Premium Gold Seal */}
                                <div className="size-10 rounded-full bg-gradient-to-br from-amber-300 via-amber-500 to-amber-600 shadow-xl flex items-center justify-center relative group transform transition-transform hover:scale-105">
                                    <div className="absolute inset-1 border-4 border-white/30 rounded-full border-dashed"></div>
                                    <div className="flex flex-col items-center text-white">
                                        <ShieldCheck size={40} className="drop-shadow-lg" />
                                        <span className="text-[7px] font-semibold uppercase tracking-wide mt-1">Garantía MESH</span>
                                    </div>
                                    {/* Ribbon effect */}
                                    <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 flex gap-1">
                                        <div className="w-4 h-8 bg-amber-600 origin-top -rotate-12 rounded-b-md shadow-lg"></div>
                                        <div className="w-4 h-8 bg-amber-600 origin-top rotate-12 rounded-b-md shadow-lg"></div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col items-center">
                                <div className="w-full max-w-[180px] border-t-2 border-slate-900 pt-3">
                                    <p className="font-semibold text-slate-900 uppercase tracking-wide">Dirección General</p>
                                </div>
                            </div>
                        </div>

                        {/* Footer Info / QR Placeholder */}
                        <div className="absolute bottom-6 left-10 flex items-center gap-3">
                             <div className="size-7 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-center text-slate-300">
                                <QrCode size={32} strokeWidth={1.5} />
                             </div>
                             <div className="text-left">
                                <p className="font-semibold text-slate-400 uppercase tracking-wide leading-none">Validación Digital</p>
                                <p className="text-[9px] font-bold text-slate-900 leading-tight mt-1">{certificate.certificate_code}</p>
                             </div>
                        </div>

                        <div className="absolute bottom-6 right-10 text-right">
                             <p className="font-semibold text-slate-400 uppercase tracking-wide leading-none">Fecha de Emisión</p>
                             <p className="text-[9px] font-bold text-slate-900 leading-tight mt-1">{new Date(certificate.issued_at).toLocaleDateString()}</p>
                        </div>
                    </div>
                </div>
            </div>

            <style jsx global>{`
                @media print {
                    @page {
                        size: landscape;
                        margin: 0;
                    }
                    body * {
                        visibility: hidden !important;
                    }
                    #certificate-to-print, #certificate-to-print * {
                        visibility: visible !important;
                    }
                    #certificate-to-print {
                        position: fixed !important;
                        left: 0 !important;
                        top: 0 !important;
                        width: 100vw !important;
                        height: 100vh !important;
                        max-width: none !important;
                        border: none !important;
                        padding: 2cm !important;
                        margin: 0 !important;
                        display: flex !important;
                        flex-direction: column !important;
                        align-items: center !important;
                        justify-content: center !important;
                        transform: none !important;
                        background: white !important;
                        box-shadow: none !important;
                    }
                    .md\\:rounded-\\[3rem\\] {
                        border-radius: 0 !important;
                    }
                }
            `}</style>
        </div>
    );
}
