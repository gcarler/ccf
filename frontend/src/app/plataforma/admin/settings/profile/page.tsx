"use client";

import React, { useEffect, useState, useCallback } from 'react';
import { SITE_NAME } from '@/lib/site-config';
import { motion } from 'framer-motion';
import { Church, Camera, Save, Edit2, AlertCircle, Loader2 } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';

export default function AdminSettingsProfilePage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [editing, setEditing] = useState(false);
    const [_loading, setLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const [form, setForm] = useState({
        name: SITE_NAME,
        slogan: '',
        mission: '',
        vision: '',
        city: 'Mocoa',
        department: 'Putumayo',
        country: 'Colombia',
        founded: '2020',
    });

    const fetchProfileVariables = useCallback(async (signal?: AbortSignal) => {
        if (!token) return;
        setLoading(true);
        try {
            const vars = await apiFetch<Record<string, string>>('/admin/variables', { token, signal });
            if (vars) {
                setForm(prev => ({
                    ...prev,
                    name: vars['ministry_name'] || prev.name,
                    slogan: vars['ministry_slogan'] || prev.slogan,
                    mission: vars['ministry_mission'] || prev.mission,
                    vision: vars['ministry_vision'] || prev.vision,
                    city: vars['ministry_city'] || prev.city,
                    department: vars['ministry_department'] || prev.department,
                    country: vars['ministry_country'] || prev.country,
                    founded: vars['ministry_founded'] || prev.founded,
                }));
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        if (!isAuthenticated) return;
        const controller = new AbortController();
        fetchProfileVariables(controller.signal);
        return () => controller.abort();
    }, [isAuthenticated, fetchProfileVariables]);

    const handleSave = async () => {
        if (!token) return;
        setIsSaving(true);
        try {
            const updates = [
                { key: 'ministry_name', value: form.name },
                { key: 'ministry_slogan', value: form.slogan },
                { key: 'ministry_mission', value: form.mission },
                { key: 'ministry_vision', value: form.vision },
                { key: 'ministry_city', value: form.city },
                { key: 'ministry_department', value: form.department },
                { key: 'ministry_country', value: form.country },
                { key: 'ministry_founded', value: form.founded },
            ];
            for (const item of updates) {
                await apiFetch('/admin/variables', {
                    token,
                    method: 'POST',
                    body: item,
                });
            }
            setSaved(true);
            setEditing(false);
            addToast("Perfil del ministerio actualizado", "success");
            setTimeout(() => setSaved(false), 3000);
        } catch (err) {
            console.error(err);
            addToast("Error al guardar el perfil", "error");
        } finally {
            setIsSaving(false);
        }
    };

    if (!isAuthenticated) return null;

    return (
        <div className="min-h-full bg-[hsl(var(--bg-muted))]/20 font-display">
            {/* Header */}
            <div className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-20">
                <div className="px-4 py-2 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Church size={18} className="text-primary" />
                        <h1 className="text-base font-semibold uppercase tracking-wide text-white">
                            Perfil del Ministerio
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        {saved && (
                            <motion.span
                                initial={{ opacity: 0, x: 10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="px-3 py-1.5 bg-[hsl(var(--success))]/20 text-[hsl(var(--success))] rounded-md text-2xs font-semibold uppercase tracking-wide"
                            >
                                ✓ Guardado
                            </motion.span>
                        )}
                        {!editing ? (
                            <button
                                onClick={() => setEditing(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/15 text-white border border-white/10 rounded-md text-xs font-semibold uppercase tracking-wide transition-all"
                            >
                                <Edit2 size={14} /> Editar
                            </button>
                        ) : (
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center gap-2 px-3 py-2 bg-primary hover:bg-primary/80 text-white rounded-md text-xs font-semibold uppercase tracking-wide shadow-lg shadow-primary/20 transition-all disabled:opacity-50"
                            >
                                {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} Guardar Cambios
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div className="max-w-2xl mx-auto px-4 py-1.5 space-y-3">
                {/* Logo Upload */}
                <div className="flex flex-col items-center gap-3">
                    <div className="relative">
                        <div className="size-10 rounded-lg border-2 border-primary/30 bg-primary/10 flex items-center justify-center shadow-2xl shadow-primary/10 overflow-hidden">
                            <Church size={48} className="text-primary" />
                        </div>
                        {editing && (
                            <button className="absolute -bottom-2 -right-2 size-9 rounded-md bg-primary text-white flex items-center justify-center shadow-xl border-2 border-[hsl(var(--border))] hover:scale-110 transition-all">
                                <Camera size={16} />
                            </button>
                        )}
                    </div>
                    {editing && (
                        <p className="text-2xs text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                            Toca el ícono para cambiar el logo
                        </p>
                    )}
                </div>

                {/* Basic Info */}
                <Section title="Información Básica">
                    <Field label="Nombre del Ministerio" value={form.name} editing={editing}
                        onChange={v => setForm(f => ({ ...f, name: v }))} />
                    <Field label="Eslogan / Tagline" value={form.slogan} editing={editing}
                        onChange={v => setForm(f => ({ ...f, slogan: v }))} />
                    <Field label="Año de Fundación" value={form.founded} editing={editing}
                        onChange={v => setForm(f => ({ ...f, founded: v }))} />
                </Section>

                {/* Mission & Vision */}
                <Section title="Misión y Visión">
                    <Field label="Misión" value={form.mission} editing={editing} multiline
                        onChange={v => setForm(f => ({ ...f, mission: v }))} />
                    <Field label="Visión" value={form.vision} editing={editing} multiline
                        onChange={v => setForm(f => ({ ...f, vision: v }))} />
                </Section>

                {/* Location */}
                <Section title="Ubicación Principal">
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Ciudad" value={form.city} editing={editing}
                            onChange={v => setForm(f => ({ ...f, city: v }))} />
                        <Field label="Departamento" value={form.department} editing={editing}
                            onChange={v => setForm(f => ({ ...f, department: v }))} />
                    </div>
                    <Field label="País" value={form.country} editing={editing}
                        onChange={v => setForm(f => ({ ...f, country: v }))} />
                </Section>

                {editing && (
                    <div className="flex items-start gap-3 p-4 bg-[hsl(var(--warning))]/10 border border-[hsl(var(--warning)/100%)]/20 rounded-lg text-xs text-[hsl(var(--warning))] font-bold">
                        <AlertCircle size={16} className="shrink-0 mt-0.5" />
                        Los cambios se reflejarán en todo el ecosistema CCF, incluyendo el sitio público.
                    </div>
                )}
            </div>
        </div>
    );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-[hsl(var(--bg-muted))]/40 backdrop-blur-xl border border-white/5 rounded-lg p-3 space-y-4"
        >
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-5">{title}</p>
            {children}
        </motion.div>
    );
}

function Field({ label, value, editing, onChange, multiline }: {
    label: string; value: string; editing: boolean;
    onChange: (v: string) => void; multiline?: boolean;
}) {
    return (
        <div className="space-y-1.5">
            <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{label}</label>
            {editing ? (
                multiline ? (
                    <textarea
                        rows={3}
                        value={value}
                        onChange={e => onChange(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-sm text-white placeholder:text-[hsl(var(--text-secondary))] focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-all resize-none outline-none"
                    />
                ) : (
                    <input
                        value={value}
                        onChange={e => onChange(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-sm text-white placeholder:text-[hsl(var(--text-secondary))] focus:ring-2 focus:ring-primary/30 focus:border-primary/40 transition-all outline-none"
                    />
                )
            ) : (
                <p className="text-sm text-[hsl(var(--text-secondary))] font-medium leading-relaxed px-1">{value}</p>
            )}
        </div>
    );
}
