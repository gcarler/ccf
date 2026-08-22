"use client";

import React, { useEffect, useState, useCallback } from 'react';
import {
    Shield,
    BookOpen,
    FileText,
    Users,
    Plus,
    CheckCircle2,
    Clock,
    AlertCircle,
    Building2,
    PenTool,
    Loader2,
    Eye,
    ChevronRight,
    RefreshCw
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import type {
    GovernancePolicy,
    GovernanceResolution,
    GovernanceCommittee,
    GovernanceStats
} from '@/types/governance';

export default function GovernancePage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();

    const [activeTab, setActiveTab] = useState<'policies' | 'resolutions' | 'committees'>('policies');
    const [stats, setStats] = useState<GovernanceStats | null>(null);
    const [policies, setPolicies] = useState<GovernancePolicy[]>([]);
    const [resolutions, setResolutions] = useState<GovernanceResolution[]>([]);
    const [committees, setCommittees] = useState<GovernanceCommittee[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal state for creating policy
    const [showPolicyModal, setShowPolicyModal] = useState(false);
    const [newPolicy, setNewPolicy] = useState({
        code: '',
        title: '',
        category: 'OPERACIONAL',
        content: '',
        status: 'BORRADOR',
    });
    const [isSaving, setIsSaving] = useState(false);

    const fetchData = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const [statsRes, policiesRes, resolutionsRes, committeesRes] = await Promise.all([
                apiFetch<GovernanceStats>('/governance/stats', { token, signal }),
                apiFetch<GovernancePolicy[]>('/governance/policies', { token, signal }),
                apiFetch<GovernanceResolution[]>('/governance/resolutions', { token, signal }),
                apiFetch<GovernanceCommittee[]>('/governance/committees', { token, signal }),
            ]);
            setStats(statsRes);
            setPolicies(policiesRes ?? []);
            setResolutions(resolutionsRes ?? []);
            setCommittees(committeesRes ?? []);
        } catch (err) {
            console.error(err);
            addToast("Error al cargar datos de gobernanza", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchData(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchData]);

    const handleCreatePolicy = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        setIsSaving(true);
        try {
            await apiFetch('/governance/policies', {
                token,
                method: 'POST',
                body: newPolicy,
            });
            addToast("Política eclesial creada exitosamente", "success");
            setShowPolicyModal(false);
            setNewPolicy({ code: '', title: '', category: 'OPERACIONAL', content: '', status: 'BORRADOR' });
            fetchData();
        } catch (err) {
            console.error(err);
            addToast("Error al crear política", "error");
        } finally {
            setIsSaving(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="p-4 lg:p-8 max-w-7xl mx-auto space-y-6 font-display">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/5 pb-6">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 shadow-lg shadow-primary/10">
                            <Shield size={22} />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-white tracking-tight uppercase">Gobernanza Institucional</h1>
                            <p className="text-xs text-[hsl(var(--text-secondary))] font-medium uppercase tracking-wider">
                                Políticas eclesiales, actas, resoluciones y estructura directiva
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button
                        onClick={() => fetchData()}
                        className="p-2.5 bg-white/5 hover:bg-white/10 text-[hsl(var(--text-secondary))] hover:text-white rounded-lg border border-white/10 transition-all active:scale-95"
                        title="Actualizar datos"
                    >
                        <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button
                        onClick={() => setShowPolicyModal(true)}
                        className="flex items-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary/90 text-white text-xs font-semibold uppercase tracking-wider rounded-lg shadow-lg shadow-primary/20 transition-all active:scale-95"
                    >
                        <Plus size={16} /> Nueva Política
                    </button>
                </div>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 p-4 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-[hsl(var(--text-secondary))]">
                        <span className="text-2xs font-semibold uppercase tracking-wider">Políticas Activas</span>
                        <BookOpen size={16} className="text-primary" />
                    </div>
                    <p className="text-2xl font-black text-white">{stats?.published_policies ?? 0} <span className="text-xs text-[hsl(var(--text-secondary))] font-normal">/ {stats?.total_policies ?? 0}</span></p>
                </div>

                <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 p-4 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-[hsl(var(--text-secondary))]">
                        <span className="text-2xs font-semibold uppercase tracking-wider">Resoluciones Firmadas</span>
                        <FileText size={16} className="text-emerald-400" />
                    </div>
                    <p className="text-2xl font-black text-white">{stats?.signed_resolutions ?? 0} <span className="text-xs text-[hsl(var(--text-secondary))] font-normal">/ {stats?.total_resolutions ?? 0}</span></p>
                </div>

                <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 p-4 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-[hsl(var(--text-secondary))]">
                        <span className="text-2xs font-semibold uppercase tracking-wider">Comités Pastorales</span>
                        <Building2 size={16} className="text-amber-400" />
                    </div>
                    <p className="text-2xl font-black text-white">{stats?.total_committees ?? 0}</p>
                </div>

                <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 p-4 rounded-xl space-y-2">
                    <div className="flex items-center justify-between text-[hsl(var(--text-secondary))]">
                        <span className="text-2xs font-semibold uppercase tracking-wider">Miembros Directivos</span>
                        <Users size={16} className="text-primary" />
                    </div>
                    <p className="text-2xl font-black text-white">{stats?.active_committee_members ?? 0}</p>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex border-b border-white/10 gap-6 text-sm font-semibold uppercase tracking-wider">
                <button
                    onClick={() => setActiveTab('policies')}
                    className={`pb-3 transition-colors border-b-2 ${activeTab === 'policies' ? 'border-primary text-primary' : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-white'}`}
                >
                    Políticas Eclesiales ({policies.length})
                </button>
                <button
                    onClick={() => setActiveTab('resolutions')}
                    className={`pb-3 transition-colors border-b-2 ${activeTab === 'resolutions' ? 'border-primary text-primary' : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-white'}`}
                >
                    Actas y Resoluciones ({resolutions.length})
                </button>
                <button
                    onClick={() => setActiveTab('committees')}
                    className={`pb-3 transition-colors border-b-2 ${activeTab === 'committees' ? 'border-primary text-primary' : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-white'}`}
                >
                    Comités y Estructura ({committees.length})
                </button>
            </div>

            {/* Content Area */}
            {loading ? (
                <div className="p-12 text-center text-[hsl(var(--text-secondary))] flex items-center justify-center gap-3">
                    <Loader2 className="animate-spin text-primary" size={20} />
                    <span>Cargando datos de gobernanza...</span>
                </div>
            ) : (
                <>
                    {/* Tab 1: Policies */}
                    {activeTab === 'policies' && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {policies.length === 0 ? (
                                <div className="col-span-2 p-12 text-center text-[hsl(var(--text-secondary))] border border-white/5 rounded-xl bg-white/5">
                                    <BookOpen size={36} className="mx-auto mb-3 opacity-40 text-primary" />
                                    <p className="text-sm font-medium">No hay políticas eclesiales registradas aún.</p>
                                </div>
                            ) : (
                                policies.map((p) => (
                                    <div key={p.id} className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-xl p-5 space-y-3 hover:border-white/15 transition-all">
                                        <div className="flex items-center justify-between">
                                            <span className="text-2xs font-mono px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                                                {p.code}
                                            </span>
                                            <span className={`text-2xs font-semibold px-2 py-0.5 rounded ${
                                                p.status === 'PUBLICADA' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                p.status === 'APROBADA' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' :
                                                'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                            }`}>
                                                {p.status}
                                            </span>
                                        </div>
                                        <div>
                                            <h3 className="text-base font-bold text-white tracking-tight">{p.title}</h3>
                                            <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-2 mt-1">{p.content}</p>
                                        </div>
                                        <div className="flex items-center justify-between text-2xs text-[hsl(var(--text-secondary))] pt-2 border-t border-white/5">
                                            <span>Categoría: <strong>{p.category}</strong></span>
                                            <span>Versión {p.version}.0</span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* Tab 2: Resolutions */}
                    {activeTab === 'resolutions' && (
                        <div className="space-y-3">
                            {resolutions.length === 0 ? (
                                <div className="p-12 text-center text-[hsl(var(--text-secondary))] border border-white/5 rounded-xl bg-white/5">
                                    <FileText size={36} className="mx-auto mb-3 opacity-40 text-emerald-400" />
                                    <p className="text-sm font-medium">No hay actas o resoluciones registradas aún.</p>
                                </div>
                            ) : (
                                resolutions.map((r) => (
                                    <div key={r.id} className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:border-white/15 transition-all">
                                        <div className="space-y-1 flex-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-2xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                    Res. {r.number}
                                                </span>
                                                <h3 className="text-base font-bold text-white tracking-tight">{r.title}</h3>
                                            </div>
                                            <p className="text-xs text-[hsl(var(--text-secondary))]">{r.summary || r.content.slice(0, 120)}...</p>
                                        </div>
                                        <div className="flex items-center gap-4 shrink-0">
                                            <div className="text-right">
                                                <p className="text-2xs text-[hsl(var(--text-secondary))] uppercase tracking-wider font-semibold">Firmas</p>
                                                <p className="text-xs font-bold text-white">{r.signatures.filter(s => s.status === 'FIRMADO').length} / {r.signatures.length || 1}</p>
                                            </div>
                                            <span className={`text-2xs font-semibold px-2.5 py-1 rounded ${
                                                r.status === 'FIRMADA' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                            }`}>
                                                {r.status}
                                            </span>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* Tab 3: Committees */}
                    {activeTab === 'committees' && (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {committees.length === 0 ? (
                                <div className="col-span-3 p-12 text-center text-[hsl(var(--text-secondary))] border border-white/5 rounded-xl bg-white/5">
                                    <Users size={36} className="mx-auto mb-3 opacity-40 text-amber-400" />
                                    <p className="text-sm font-medium">No hay comités pastorales creados aún.</p>
                                </div>
                            ) : (
                                committees.map((c) => (
                                    <div key={c.id} className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-xl p-5 space-y-4 hover:border-white/15 transition-all">
                                        <div className="flex items-center justify-between">
                                            <span className="text-2xs font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                                {c.committee_type}
                                            </span>
                                            <span className="text-2xs text-[hsl(var(--text-secondary))]">{c.members.length} miembros</span>
                                        </div>
                                        <div>
                                            <h3 className="text-base font-bold text-white tracking-tight">{c.name}</h3>
                                            <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{c.description || "Comité activo de la congregación."}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </>
            )}

            {/* Modal Crear Política */}
            {showPolicyModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
                    <div className="bg-[#12141a] border border-white/10 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl animate-in fade-in zoom-in-95">
                        <div className="flex items-center justify-between border-b border-white/5 pb-4">
                            <h2 className="text-lg font-bold text-white uppercase tracking-tight">Nueva Política Eclesial</h2>
                            <button onClick={() => setShowPolicyModal(false)} className="text-[hsl(var(--text-secondary))] hover:text-white">✕</button>
                        </div>
                        <form onSubmit={handleCreatePolicy} className="space-y-4">
                            <div className="grid grid-cols-3 gap-3">
                                <div className="space-y-1">
                                    <label className="text-2xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))]">Código</label>
                                    <input
                                        required
                                        placeholder="POL-2026-01"
                                        value={newPolicy.code}
                                        onChange={e => setNewPolicy(p => ({ ...p, code: e.target.value }))}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white outline-none focus:border-primary"
                                    />
                                </div>
                                <div className="col-span-2 space-y-1">
                                    <label className="text-2xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))]">Categoría</label>
                                    <select
                                        value={newPolicy.category}
                                        onChange={e => setNewPolicy(p => ({ ...p, category: e.target.value }))}
                                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white outline-none focus:border-primary"
                                    >
                                        <option value="OPERACIONAL" className="bg-neutral-900">Operacional</option>
                                        <option value="DOCTRINAL" className="bg-neutral-900">Doctrinal</option>
                                        <option value="ADMINISTRATIVA" className="bg-neutral-900">Administrativa</option>
                                        <option value="MINISTERIAL" className="bg-neutral-900">Ministerial</option>
                                    </select>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-2xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))]">Título de la Política</label>
                                <input
                                    required
                                    placeholder="Ej: Política de Protección a la Infancia y Ministerios"
                                    value={newPolicy.title}
                                    onChange={e => setNewPolicy(p => ({ ...p, title: e.target.value }))}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white outline-none focus:border-primary"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-2xs uppercase tracking-wider font-semibold text-[hsl(var(--text-secondary))]">Contenido y Normativa</label>
                                <textarea
                                    required
                                    rows={4}
                                    placeholder="Detalle de los lineamientos y protocolos institucionales..."
                                    value={newPolicy.content}
                                    onChange={e => setNewPolicy(p => ({ ...p, content: e.target.value }))}
                                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white outline-none focus:border-primary resize-none"
                                />
                            </div>
                            <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
                                <button
                                    type="button"
                                    onClick={() => setShowPolicyModal(false)}
                                    className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white rounded-lg text-xs font-semibold uppercase tracking-wider"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSaving}
                                    className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-xs font-semibold uppercase tracking-wider shadow-lg shadow-primary/20 disabled:opacity-50"
                                >
                                    {isSaving ? <Loader2 size={14} className="animate-spin" /> : null} Guardar Política
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
