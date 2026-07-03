"use client";

import React, { useState, useCallback, useEffect } from 'react';
import { SITE_NAME, SITE_EMAIL } from '@/lib/site-config';
import { 
    Settings as SettingsIcon, Save, Globe, Shield,
    Smartphone, Users, Database, Bell,
    AlertTriangle, Zap,
    Lock, Activity,
    Plus, Pencil
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useCrmAccess } from '@/hooks/useCrmAccess';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import { SettingsNavButton, SettingInput, ToggleSetting } from '@/components/crm/ui';

export default function CrmSettingsPage() {
    const { token } = useAuth();
    const { canEditCrm } = useCrmAccess();
    const { addToast } = useToast();
    const [isSaving, setIsSaving] = useState(false);
    const [activeSection, setActiveTab] = useState('general');
    const [positions, setPositions] = useState<any[]>([]);
    const [isLoadingPositions, setIsLoadingPositions] = useState(false);
    const [isCreatingPosition, setIsCreatingPosition] = useState(false);
    const [editingPositionId, setEditingPositionId] = useState<number | null>(null);
    const [positionForm, setPositionForm] = useState({
        name: '',
        description: '',
        category: 'consolidation',
        is_active: true,
    });

    const [config, setConfig] = useState<any>({
        churchName: SITE_NAME,
        contactEmail: SITE_EMAIL || '',
        timezone: 'America/Bogota',
        enableWhatsApp: false,
        enableSMS: false,
        twilioApiKey: '',
        smtpServer: ''
    });

    const fetchSettings = useCallback(async () => {
        if (!token) return;
        try {
            const data = await apiFetch('/crm/settings', { token, cache: 'no-store' });
            if (data) setConfig(data);
        } catch (err) {
            console.error("Error fetching settings", err);
        }
    }, [token]);

    const fetchPositions = useCallback(async () => {
        if (!token) return;
        setIsLoadingPositions(true);
        try {
            const data = await apiFetch<any[]>('/crm/positions', { token, cache: 'no-store' });
            setPositions(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('Error fetching consolidation positions', err);
        } finally {
            setIsLoadingPositions(false);
        }
    }, [token]);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    useEffect(() => {
        if (activeSection === 'consolidation') {
            fetchPositions();
        }
    }, [activeSection, fetchPositions]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!canEditCrm) return;
        setIsSaving(true);
        try {
            await apiFetch('/crm/settings', {
                method: 'POST',
                token,
                body: config
            });
            addToast("Configuraciones globales actualizadas", "success");
        } catch {
            addToast("Error al guardar en el servidor", "error");
        } finally {
            setIsSaving(false);
        }
    };

    const resetPositionForm = () => {
        setPositionForm({
            name: '',
            description: '',
            category: 'consolidation',
            is_active: true,
        });
        setEditingPositionId(null);
    };

    const handleSavePosition = async () => {
        if (!canEditCrm || !token || !positionForm.name.trim()) return;
        setIsCreatingPosition(true);
        try {
            const payload = {
                name: positionForm.name.trim(),
                description: positionForm.description.trim() || null,
                category: positionForm.category.trim() || null,
                is_active: positionForm.is_active,
            };
            if (editingPositionId) {
                await apiFetch(`/crm/positions/${editingPositionId}`, {
                    method: 'PATCH',
                    token,
                    body: payload,
                });
            } else {
                await apiFetch('/crm/positions', {
                    method: 'POST',
                    token,
                    body: payload,
                });
            }
            await fetchPositions();
            resetPositionForm();
            addToast('Cargo actualizado', 'success');
        } catch (err) {
            addToast('No se pudo guardar el cargo', 'error');
        } finally {
            setIsCreatingPosition(false);
        }
    };

    const startEditPosition = (row: any) => {
        setEditingPositionId(row.id);
        setPositionForm({
            name: row.name || '',
            description: row.description || '',
            category: row.category || 'consolidation',
            is_active: Boolean(row.is_active),
        });
        setActiveTab('consolidation');
    };

    const containerVariants = {
        hidden: { opacity: 0 },
        show: { opacity: 1, transition: { staggerChildren: 0.05 } }
    };

    const itemVariants = {
        hidden: { opacity: 0, x: -10 },
        show: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 300, damping: 24 } }
    };

    return (
        <CrmShell
            breadcrumbs={[
                { label: 'Consolidación', icon: Users },
                { label: 'Configuración de Sistema', icon: SettingsIcon }
            ]}
            rightActions={canEditCrm ? (
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-[hsl(var(--primary))] px-4 py-1.5 rounded-lg text-[11px] font-bold tracking-wide text-white hover:bg-[hsl(var(--primary))] transition-all uppercase shadow-xl shadow-blue-500/20 disabled:opacity-50 active:scale-95"
                >
                    {isSaving ? <SpinnerIcon className="animate-spin" size={14} /> : <Save size={14} />}
                    {isSaving ? 'Sincronizando...' : 'Guardar Cambios'}
                </button>
            ) : undefined}
        >
            <div className="max-w-[1000px] mx-auto space-y-3 pb-4 pt-6 px-4 font-sans">
                
                {/* 1. Header */}
                <div className="flex flex-col space-y-1">
                    <div className="flex items-center gap-2 mb-2">
                        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-rose-100 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 rounded-md text-[10px] font-bold uppercase tracking-wide">
                            <Shield size={10} /> Privilegios Root
                        </div>
                    </div>
                    <h1 className="text-base font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">Control Maestro</h1>
                    <p className="text-xs font-medium text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Administra los parámetros base, integraciones y seguridad del ecosistema.</p>
                </div>

                {/* 2. Settings Grid Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                    
                    {/* Navigation Sidebar */}
                    <motion.aside variants={containerVariants} initial="hidden" animate="show" className="space-y-1">
                        <SettingsNavButton active={activeSection === 'general'} onClick={() => canEditCrm && setActiveTab('general')} icon={Globe} label="Información General" />
                        <SettingsNavButton active={activeSection === 'integrations'} onClick={() => canEditCrm && setActiveTab('integrations')} icon={Zap} label="Integraciones" />
                        <SettingsNavButton active={activeSection === 'notifications'} onClick={() => canEditCrm && setActiveTab('notifications')} icon={Bell} label="Notificaciones" />
                        <SettingsNavButton active={activeSection === 'consolidation'} onClick={() => canEditCrm && setActiveTab('consolidation')} icon={Users} label="Consolidación" />
                        <SettingsNavButton active={activeSection === 'security'} onClick={() => canEditCrm && setActiveTab('security')} icon={Lock} label="Seguridad & Datos" />
                    </motion.aside>

                    {/* Main Settings Form */}
                    <motion.div variants={itemVariants} initial="hidden" animate="show" className="lg:col-span-3">
                        <AnimatePresence mode="wait">
                            {activeSection === 'general' && (
                                <motion.div key="general" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 md:p-4 shadow-sm">
                                    <div className="space-y-1 border-b border-[hsl(var(--border))] dark:border-white/5 pb-4">
                                        <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Parámetros de Identidad</h3>
                                        <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium">Define cómo se identifica tu ministerio en reportes y correos.</p>
                                    </div>

                                    <div className="grid grid-cols-1 gap-4">
                                        <SettingInput disabled={!canEditCrm} label="Nombre de la Iglesia" value={config.churchName} onChange={(val: string) => setConfig({...config, churchName: val})} />
                                        <SettingInput disabled={!canEditCrm} label="Email de Respuesta Público" value={config.contactEmail} onChange={(val: string) => setConfig({...config, contactEmail: val})} />
                                        <div className="space-y-1.5">
                                            <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-1">Zona Horaria Base</label>
                                            <select disabled={!canEditCrm} className="w-full bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] dark:bg-black/20 dark:hover:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md px-4 py-2.5 text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white outline-none focus:ring-2 focus:ring-blue-500/30 transition-all appearance-none cursor-pointer disabled:opacity-50" value={config.timezone} onChange={e => setConfig({...config, timezone: e.target.value})}>
                                                <option value="America/Bogota">Bogotá (GMT-5)</option>
                                                <option value="America/New_York">New York (GMT-4)</option>
                                                <option value="Europe/Madrid">Madrid (GMT+2)</option>
                                            </select>
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'integrations' && (
                                <motion.div key="integrations" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 md:p-4 shadow-sm">
                                    <div className="space-y-1 border-b border-[hsl(var(--border))] dark:border-white/5 pb-4">
                                        <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Pasarelas de Conexión</h3>
                                        <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium">Habilita canales oficiales para mensajería y automatizaciones.</p>
                                    </div>

                                    <div className="space-y-4">
                                        <ToggleSetting 
                                            disabled={!canEditCrm}
                                            icon={Smartphone} color="text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10" title="Canal de WhatsApp Business" 
                                            desc="Habilita envío de notificaciones y seguimiento automático."
                                            active={config.enableWhatsApp} onToggle={(v: boolean) => setConfig({...config, enableWhatsApp: v})}
                                        />
                                        <ToggleSetting 
                                            disabled={!canEditCrm}
                                            icon={Smartphone} color="text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10" title="Notificaciones SMS (Twilio)" 
                                            desc="Para alertas urgentes cuando no hay internet."
                                            active={config.enableSMS} onToggle={(v: boolean) => setConfig({...config, enableSMS: v})}
                                        />
                                        {config.enableSMS && (
                                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="pl-4 ml-4 border-l-2 border-[hsl(var(--border))] dark:border-white/10 py-2 space-y-4">
                                                <SettingInput disabled={!canEditCrm} label="Twilio Account SID" value={config.twilioApiKey} onChange={(v: string) => setConfig({...config, twilioApiKey: v})} placeholder="ACxxxxxxxxxxxxxxxx" />
                                                <SettingInput disabled={!canEditCrm} label="Auth Token" value="••••••••••••••••" onChange={() => {}} type="password" />
                                            </motion.div>
                                        )}
                                        <div className="pt-4 mt-2 border-t border-[hsl(var(--border))] dark:border-white/5">
                                            <SettingInput disabled={!canEditCrm} label="Servidor SMTP Principal" value={config.smtpServer} onChange={(v: string) => setConfig({...config, smtpServer: v})} placeholder="smtp.mail.ccf.org" />
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'security' && (
                                <motion.div key="security" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3">
                                    <div className="bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 md:p-4 shadow-sm space-y-3">
                                        <div className="space-y-1 border-b border-[hsl(var(--border))] dark:border-white/5 pb-4">
                                            <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Políticas de Seguridad</h3>
                                            <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium">Controla la infraestructura y salvaguardia de datos.</p>
                                        </div>

                                        <div className="flex items-center justify-between p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/5">
                                            <div className="flex items-start gap-4">
                                                <Database size={18} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] mt-0.5" />
                                                <div>
                                                    <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">Respaldo Automático Base de Datos</h4>
                                                    <p className="text-[12px] text-[hsl(var(--text-secondary))] mt-0.5">MESH encripta y guarda un backup cada 24h.</p>
                                                </div>
                                            </div>
                                            <span className="px-2 py-1 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 rounded-md text-[10px] font-bold uppercase tracking-wide">Activo</span>
                                        </div>

                                        <div className="flex items-center justify-between p-4 rounded-md bg-rose-50 dark:bg-rose-500/5 border border-rose-100 dark:border-rose-500/20 mt-4">
                                            <div className="flex items-start gap-4">
                                                <AlertTriangle size={18} className="text-rose-600 dark:text-rose-500 mt-0.5" />
                                                <div>
                                                    <h4 className="text-xs font-bold text-rose-900 dark:text-rose-400">Purga del Sistema</h4>
                                                    <p className="text-[12px] text-rose-700/70 dark:text-rose-500/80 mt-0.5">Atención: esto borrará todos los registros de personas permanentemente.</p>
                                                </div>
                                            </div>
                                            <button className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold shadow-sm transition-all active:scale-95 shrink-0">
                                                Purga Manual
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'notifications' && (
                                <motion.div key="notifications" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 md:p-4 shadow-sm">
                                    <div className="flex flex-col items-center justify-center p-4 text-center text-[hsl(var(--text-secondary))]">
                                        <Bell size={32} className="mb-4 opacity-50 text-[hsl(var(--text-secondary))]" />
                                        <h4 className="text-xs font-bold mb-1 text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">Sin notificaciones configuradas</h4>
                                        <p className="text-[12px]">Las preferencias de alerta de sistema aparecerán aquí.</p>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'consolidation' && (
                                <motion.div key="consolidation" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-3 bg-[hsl(var(--surface-1))] dark:bg-[#1E1F21] rounded-lg border border-[hsl(var(--border))] dark:border-white/5 p-4 md:p-4 shadow-sm">
                                    <div className="space-y-1 border-b border-[hsl(var(--border))] dark:border-white/5 pb-4">
                                        <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Cargos de Consolidación</h3>
                                        <p className="text-[12px] text-[hsl(var(--text-secondary))] font-medium">Define los roles nativos que operan el seguimiento de personas.</p>
                                    </div>

                                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                                        <div className="space-y-4 p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/5">
                                            <div className="flex items-center justify-between">
                                                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                                    {editingPositionId ? 'Editar cargo' : 'Nuevo cargo'}
                                                </h4>
                                                {editingPositionId && (
                                                    <button
                                                        type="button"
                                                        onClick={resetPositionForm}
                                                        className="text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]"
                                                    >
                                                        Cancelar
                                                    </button>
                                                )}
                                            </div>
                                            <SettingInput disabled={!canEditCrm} label="Nombre" value={positionForm.name} onChange={(v: string) => setPositionForm({ ...positionForm, name: v })} placeholder="Pastor de consolidación" />
                                            <SettingInput disabled={!canEditCrm} label="Categoría" value={positionForm.category} onChange={(v: string) => setPositionForm({ ...positionForm, category: v })} placeholder="consolidation" />
                                            <div className="space-y-1.5">
                                                <label className="text-[10px] font-bold text-[hsl(var(--text-secondary))] uppercase tracking-wide pl-1">Descripción</label>
                                                <textarea
                                                    disabled={!canEditCrm}
                                                    value={positionForm.description}
                                                    onChange={(e) => setPositionForm({ ...positionForm, description: e.target.value })}
                                                    rows={4}
                                                    className="w-full bg-[hsl(var(--surface-1))] hover:bg-[hsl(var(--surface-2))] dark:bg-black/20 dark:hover:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-md px-4 py-2.5 text-xs font-medium text-[hsl(var(--text-primary))] dark:text-white outline-none focus:ring-2 focus:ring-blue-500/30 transition-all placeholder:text-[hsl(var(--text-secondary))]"
                                                />
                                            </div>
                                            <label className="flex items-center gap-3 text-xs font-medium text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                                                <input
                                                    disabled={!canEditCrm}
                                                    type="checkbox"
                                                    checked={positionForm.is_active}
                                                    onChange={(e) => setPositionForm({ ...positionForm, is_active: e.target.checked })}
                                                    className="size-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-blue-500"
                                                />
                                                Activo
                                            </label>
                                            {canEditCrm && (
                                                <button
                                                    type="button"
                                                    onClick={handleSavePosition}
                                                    disabled={isCreatingPosition || !positionForm.name.trim()}
                                                    className="inline-flex items-center justify-center gap-2 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-[11px] font-bold uppercase tracking-wide text-white hover:bg-[hsl(var(--primary))] transition-all disabled:opacity-50"
                                                >
                                                    {isCreatingPosition ? <SpinnerIcon className="animate-spin" size={14} /> : <Plus size={14} />}
                                                    {editingPositionId ? 'Guardar cambios' : 'Crear cargo'}
                                                </button>
                                            )}
                                        </div>

                                        <div className="space-y-4 p-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-white/[0.02] border border-[hsl(var(--border))] dark:border-white/5">
                                            <div className="flex items-center justify-between">
                                                <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">Catálogo actual</h4>
                                                <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                    {isLoadingPositions ? 'Cargando...' : `${positions.length} cargos`}
                                                </span>
                                            </div>

                                            {isLoadingPositions ? (
                                                <div className="space-y-3">
                                                    {[...Array(3)].map((_, i) => (
                                                        <div key={i} className="h-8 rounded-md bg-[hsl(var(--surface-1))] dark:bg-black/20 border border-[hsl(var(--border))] dark:border-white/10 animate-pulse" />
                                                    ))}
                                                </div>
                                            ) : positions.length === 0 ? (
                                                <div className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/10 p-4 text-center text-[hsl(var(--text-secondary))]">
                                                    No hay cargos registrados aún.
                                                </div>
                                            ) : (
                                                <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                                                    {positions.map((position) => (
                                                        <div key={position.id} className="flex items-start justify-between gap-4 rounded-md bg-[hsl(var(--surface-1))] dark:bg-[#111317] border border-[hsl(var(--border))] dark:border-white/10 p-4">
                                                            <div className="min-w-0">
                                                                <div className="flex items-center gap-2">
                                                                    <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white truncate">{position.name}</p>
                                                                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide ${position.is_active ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]'}`}>
                                                                        {position.is_active ? 'Activo' : 'Inactivo'}
                                                                    </span>
                                                                </div>
                                                                <p className="text-[12px] text-[hsl(var(--text-secondary))] mt-1">{position.category || 'Sin categoría'}</p>
                                                                {position.description && (
                                                                    <p className="text-[12px] text-[hsl(var(--text-secondary))] mt-1 line-clamp-2">{position.description}</p>
                                                                )}
                                                            </div>
                                                            {canEditCrm && (
                                                                <button
                                                                    type="button"
                                                                    onClick={() => startEditPosition(position)}
                                                                    className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                                                                >
                                                                    <Pencil size={12} />
                                                                    Editar
                                                                </button>
                                                            )}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                </div>
            </div>
        </CrmShell>
    );
}

function SpinnerIcon({ className, size = 24 }: any) {
    return <Activity size={size} className={clsx("animate-spin", className)} />;
}
