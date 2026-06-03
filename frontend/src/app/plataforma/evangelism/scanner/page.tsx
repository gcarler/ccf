'use client';

import React, { useState } from 'react';
import { QrCode, ShieldCheck, Zap, RefreshCcw, UserCheck, Users } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch, ApiError } from '@/lib/http';
import { toast } from 'sonner';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import AdminHero from '@/components/admin/AdminHero';
import type { ScanValidationResult } from '@/app/plataforma/evangelism/types';

// Simulating a QR scanner for this environment since camera access might be restricted in some environments
// or require specific permissions. We provide a premium manual input + auto-scan simulation.

export default function ScannerPage() {
    const [scannedData, setScannedData] = useState<ScanValidationResult | null>(null);
    const [isScanning, setIsScanning] = useState(true);
    const [manualToken, setManualToken] = useState('');
    const [loading, setLoading] = useState(false);
    const { token: authToken } = useAuth();

    const handleScan = async (token: string) => {
        if (!token) return;
        setLoading(true);
        setIsScanning(false);
        try {
            const data = await apiFetch<ScanValidationResult>(`/evangelism/scanner/validate/${token}`, { method: 'POST', token: authToken });
            setScannedData(data);
            toast.success('¡Asistencia Confirmada!');
        } catch (error) {
            const message = error instanceof ApiError && typeof error.detail === 'object' && error.detail && 'detail' in error.detail
                ? String((error.detail as { detail?: string }).detail || 'Error en el escaneo')
                : 'Error en el escaneo';
            toast.error(message);
            setIsScanning(true);
        } finally {
            setLoading(false);
        }
    };

    const resetScanner = () => {
        setScannedData(null);
        setIsScanning(true);
        setManualToken('');
    };

    const heroWatchers = ['Control acceso', 'Optimus Brain'];

    return (
        <EvangelismShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Escáner', icon: QrCode }]}
            rightActions={
                scannedData ? (
                    <button onClick={resetScanner} className="px-4 py-2 bg-slate-900 text-white rounded-md text-[11px] font-semibold uppercase tracking-wide hover:bg-black transition-all">
                        Reiniciar
                    </button>
                ) : undefined
            }
        >
        <AdminHero
            eyebrow="Asistencia"
            title="Escáner de asistencia"
            description="Valida credenciales digitales en segundos. Optimus Brain marca alertas de duplicados y tokens vencidos."
            tags={['QR', 'Tokens', 'Seguridad']}
            watchers={heroWatchers}
            primaryAction={undefined}
            secondaryAction={scannedData ? { label: 'Escanear de nuevo', icon: RefreshCcw, onClick: resetScanner } : undefined}
        />
        <div className="flex flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent"></div>
            <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-primary/20 blur-[120px] rounded-full"></div>
            <div className="absolute -bottom-[10%] -right-[10%] w-[40%] h-[40%] bg-[hsl(var(--primary))]/10 blur-[120px] rounded-full"></div>

            <div className="w-full max-w-md relative z-10 space-y-3">
                {/* Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 rounded-full border border-white/10 text-primary mb-4">
                        <Zap size={14} className="animate-pulse" />
                        <span className="text-[10px] font-semibold uppercase tracking-wide">Validación en Tiempo Real</span>
                    </div>
                    <h1 className="text-xl font-bold text-white tracking-tight">Escáner de Asistencia</h1>
                    <p className="text-slate-500 text-sm">Escanea el QR del carnet digital para validar el ingreso.</p>
                </div>

                {/* Scanner Interface */}
                <div className="relative aspect-square w-full bg-slate-900/50 backdrop-blur-xl rounded-lg border-2 border-dashed border-white/10 flex flex-col items-center justify-center overflow-hidden group shadow-2xl">

                    {isScanning ? (
                        <>
                            {/* Scanning Overlay */}
                            <div className="absolute inset-0 z-10 pointer-events-none">
                                <div className="absolute top-5 left-10 w-12 h-8 border-t-4 border-l-4 border-primary rounded-tl-2xl"></div>
                                <div className="absolute top-5 right-10 w-12 h-8 border-t-4 border-r-4 border-primary rounded-tr-2xl"></div>
                                <div className="absolute bottom-10 left-10 w-12 h-8 border-b-4 border-l-4 border-primary rounded-bl-2xl"></div>
                                <div className="absolute bottom-10 right-10 w-12 h-8 border-b-4 border-r-4 border-primary rounded-br-2xl"></div>

                                {/* Animated scan line */}
                                <div className="absolute top-0 inset-x-0 h-1 bg-gradient-to-r from-transparent via-primary to-transparent shadow-[0_0_15px_rgba(66,66,240,0.8)] animate-scan"></div>
                            </div>

                            <div className="flex flex-col items-center gap-4 p-4 text-center relative z-20">
                                <div className="p-4 bg-primary/10 rounded-full text-primary scale-125 group-hover:scale-150 transition-transform duration-700">
                                    <QrCode size={64} />
                                </div>
                                <div>
                                    <p className="text-white font-bold text-sm mb-2">Buscando Código...</p>
                                    <p className="text-slate-500 text-xs">Apunta la cámara al código QR del feligrés</p>
                                </div>

                                {/* Manual Input Toggle (Simulation) */}
                                <div className="mt-3 w-full space-y-4">
                                    <div className="relative">
                                        <input
                                            type="text"
                                            placeholder="Ingresar Token Manualmente"
                                            value={manualToken}
                                            onChange={(e) => setManualToken(e.target.value)}
                                            className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-primary transition-all text-center"
                                        />
                                    </div>
                                    <button
                                        onClick={() => handleScan(manualToken)}
                                        disabled={!manualToken || loading}
                                        className="w-full py-2 bg-primary hover:bg-primary-600 text-white rounded-lg font-semibold uppercase tracking-wide text-[11px] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                                    >
                                        {loading ? <RefreshCcw className="animate-spin" size={16} /> : <UserCheck size={16} />}
                                        Validar Token
                                    </button>
                                </div>
                            </div>
                        </>
                    ) : (
                        /* SUCCESS STATE */
                        <div className="animate-in zoom-in-95 duration-500 flex flex-col items-center justify-center p-4 text-center space-y-3">
                            <div className="p-4 bg-emerald-500/20 rounded-full text-emerald-500 shadow-[0_0_40px_rgba(16,185,129,0.2)]">
                                <ShieldCheck size={80} />
                            </div>
                            <div className="space-y-2">
                                <h2 className="text-lg font-bold text-white">{scannedData?.member_name}</h2>
                                <p className="text-emerald-500 font-extrabold uppercase tracking-wide text-xs px-3 py-1 bg-emerald-500/10 rounded-full inline-block">
                                    {scannedData?.role} â€¢ VALIDADO
                                </p>
                            </div>
                            <p className="text-slate-400 text-sm max-w-[240px]">
                                El ingreso ha sido registrado exitosamente en el sistema de asistencia.
                            </p>
                            <button
                                onClick={resetScanner}
                                className="mt-3 px-3 py-2 bg-white/5 hover:bg-white/10 text-white border border-white/10 rounded-lg font-semibold uppercase tracking-wide text-[10px] flex items-center gap-2 transition-all"
                            >
                                <RefreshCcw size={16} /> Escanear Siguiente
                            </button>
                        </div>
                    )}
                </div>

                {/* Footer Info */}
                <div className="flex items-center justify-center gap-4 text-slate-500">
                    <div className="flex items-center gap-2">
                        <div className="size-2 bg-emerald-500 rounded-full animate-pulse"></div>
                        <span className="text-[10px] font-semibold uppercase tracking-wide">Servidor Activo</span>
                    </div>
                    <div className="w-px h-3 bg-white/10"></div>
                    <button className="text-[10px] font-semibold uppercase tracking-wide hover:text-white transition-colors">Escaneo activo</button>
                </div>
            </div>

        </div>
        </EvangelismShell>
    );
}



