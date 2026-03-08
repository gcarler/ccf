"use client";

import React from 'react';
import { 
    X, 
    Download, 
    Printer, 
    Award, 
    ShieldCheck, 
    Calendar, 
    User, 
    BookOpen,
    CheckCircle2
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

    return (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-300">
            <div className="relative w-full max-w-4xl bg-white rounded-[2rem] shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
                {/* Close Button - Hidden on print */}
                <button 
                    onClick={onClose}
                    className="absolute top-6 right-6 p-2 bg-slate-100 text-slate-500 hover:text-slate-900 rounded-full transition-all z-20 print:hidden"
                >
                    <X size={24} />
                </button>

                <div className="flex flex-col md:flex-row h-full">
                    {/* Preview Sidebar - Hidden on print */}
                    <div className="w-full md:w-72 bg-slate-50 p-8 border-r border-slate-100 print:hidden flex flex-col">
                        <div className="mb-8">
                            <div className="size-14 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mb-4">
                                <Award size={32} />
                            </div>
                            <h2 className="text-xl font-bold text-slate-900 leading-tight">Certificado de Logro</h2>
                            <p className="text-sm text-slate-500 mt-2 font-medium">Este documento certifica la finalización exitosa de tu formación académica.</p>
                        </div>

                        <div className="space-y-4 mb-auto">
                            <div className="flex items-start gap-3">
                                <div className="p-1.5 bg-white rounded-lg border border-slate-200 text-slate-400">
                                    <ShieldCheck size={16} />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Código de Validación</p>
                                    <p className="text-xs font-bold text-slate-900 truncate">{certificate.certificate_code}</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-3">
                                <div className="p-1.5 bg-white rounded-lg border border-slate-200 text-slate-400">
                                    <Calendar size={16} />
                                </div>
                                <div className="min-w-0">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Fecha de Emisión</p>
                                    <p className="text-xs font-bold text-slate-900">{new Date(certificate.issued_at).toLocaleDateString()}</p>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 gap-3 mt-8">
                            <button 
                                onClick={handlePrint}
                                className="w-full py-3 bg-slate-900 text-white rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-slate-800 transition-all flex items-center justify-center gap-2 shadow-lg shadow-slate-900/10"
                            >
                                <Printer size={16} /> Imprimir / PDF
                            </button>
                            <button 
                                onClick={() => window.alert("Descarga en proceso...")}
                                className="w-full py-3 bg-white text-slate-900 border border-slate-200 rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-slate-50 transition-all flex items-center justify-center gap-2"
                            >
                                <Download size={16} /> Descargar Imagen
                            </button>
                        </div>
                    </div>

                    {/* Certificate Paper */}
                    <div className="flex-1 p-8 md:p-16 flex items-center justify-center bg-white overflow-y-auto">
                        <div className="certificate-paper w-full aspect-[1.414/1] max-w-[800px] border-[12px] border-double border-slate-200 p-8 md:p-12 relative flex flex-col items-center text-center">
                            {/* Decorative corner */}
                            <div className="absolute top-0 left-0 w-24 h-24 border-t-4 border-l-4 border-slate-300"></div>
                            <div className="absolute top-0 right-0 w-24 h-24 border-t-4 border-r-4 border-slate-300"></div>
                            <div className="absolute bottom-0 left-0 w-24 h-24 border-b-4 border-l-4 border-slate-300"></div>
                            <div className="absolute bottom-0 right-0 w-24 h-24 border-b-4 border-r-4 border-slate-300"></div>

                            <div className="mb-6 flex flex-col items-center">
                                <div className="size-16 bg-slate-900 text-white rounded-full flex items-center justify-center mb-4 shadow-xl">
                                    <Award size={36} />
                                </div>
                                <h3 className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400">Comunidad Cristiana El Faro</h3>
                            </div>

                            <h1 className="text-4xl md:text-5xl font-serif italic text-slate-900 mb-8">Certificado de Finalización</h1>
                            
                            <p className="text-slate-500 font-medium italic mb-2 uppercase tracking-widest text-xs">Se otorga el presente reconocimiento a:</p>
                            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-8 border-b-2 border-slate-100 pb-2 px-12 inline-block">
                                {userName}
                            </h2>

                            <p className="text-slate-600 max-w-lg leading-relaxed mb-10 text-lg">
                                Por haber completado satisfactoriamente los requisitos académicos y evaluativos del curso:
                                <br />
                                <span className="font-black text-slate-900 mt-2 block">&quot;{enrollment.course.title}&quot;</span>
                            </p>

                            <div className="mt-auto w-full flex flex-col md:flex-row justify-between items-end pt-12">
                                <div className="flex flex-col items-center">
                                    <div className="w-48 border-t border-slate-300 pt-2">
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Coordinación Académica</p>
                                    </div>
                                </div>

                                <div className="mb-4 md:mb-0">
                                    <div className="size-20 border-4 border-slate-100 rounded-full flex items-center justify-center text-slate-200">
                                        <ShieldCheck size={40} />
                                    </div>
                                </div>

                                <div className="flex flex-col items-center">
                                    <div className="w-48 border-t border-slate-300 pt-2">
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Dirección General</p>
                                    </div>
                                </div>
                            </div>

                            <div className="absolute bottom-4 left-0 right-0 text-center">
                                <p className="text-[8px] font-bold text-slate-300 uppercase tracking-[0.2em]">Validación: {certificate.certificate_code}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <style jsx global>{`
                @media print {
                    body * {
                        visibility: hidden;
                    }
                    .fixed {
                        position: absolute !important;
                        left: 0 !important;
                        top: 0 !important;
                        padding: 0 !important;
                        margin: 0 !important;
                        background: white !important;
                        backdrop-filter: none !important;
                    }
                    .certificate-paper, .certificate-paper * {
                        visibility: visible;
                    }
                    .certificate-paper {
                        position: absolute;
                        left: 50%;
                        top: 50%;
                        transform: translate(-50%, -50%) scale(1.2);
                        border: 8px double #cbd5e1 !important;
                        box-shadow: none !important;
                        width: 90% !important;
                        max-width: none !important;
                    }
                }
            `}</style>
        </div>
    );
}
