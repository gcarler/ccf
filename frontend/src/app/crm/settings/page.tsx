"use client";

import React, { useState, useCallback, useEffect } from 'react';
import { 
    Settings as SettingsIcon, Save, Key, Globe, Shield, 
    Smartphone, Link2, Users, Database, Bell,
    CheckCircle2, AlertTriangle, ArrowRight, Zap,
    Lock, Terminal, Server, Sparkles
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

export default function CrmSettingsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [isSaving, setIsSaving] = useState(false);
    const [activeSection, setActiveTab] = useState('general');

    const [config, setConfig] = useState<any>({
        churchName: 'Comunidad Cristiana El Faro',
        contactEmail: 'sistemas@ministeriofaro.org',
        timezone: 'America/Bogota',
        enableWhatsApp: true,
        enableSMS: false,
        twilioApiKey: '••••••••••••••••',
        smtpServer: 'smtp.ministeriofaro.org'
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

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            await apiFetch('/crm/settings', {
                method: 'POST',
                token,
                body: config
            });
            addToast("Configuraciones globales actualizadas", "success");
        } catch (err) {
            addToast("Error al guardar en el servidor", "error");
        } finally {
            setIsSaving(false);
        }
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
                { label: 'CRM Pastoral', icon: Users },
                { label: 'Configuración de Sistema', icon: SettingsIcon }
            ]}
            rightActions={
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-blue-600 px-6 py-2.5 rounded-xl text-[11px] font-black tracking-widest text-white hover:bg-blue-700 transition-all uppercase shadow-xl shadow-blue-500/20 disabled:opacity-50 active:scale-95"
                >
                    {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={16} />}
                    {isSaving ? 'Sincronizando...' : 'Guardar Cambios'}
                </button>
            }
        >
            <div className="max-w-[1400px] mx-auto space-y-10 pb-20 font-sans relative">
                
                {/* 1. Hero Configuration Header */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative rounded-[3.5rem] bg-slate-900 p-12 lg:p-16 overflow-hidden text-white border border-white/5 shadow-2xl">
                    <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none"><Terminal size={160} /></div>
                    <div className="relative z-10 space-y-6 max-w-3xl">
                        <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur-xl border border-white/10 rounded-full text-[10px] font-black uppercase tracking-[0.3em] text-blue-300">
                            <Shield size={12} /> Root Access Level
                        </div>
                        <h1 className="text-5xl lg:text-7xl font-black tracking-tighter leading-none">Control <span className="text-blue-400">Maestro.</span></h1>
                        <p className="text-lg text-slate-400 font-medium leading-relaxed">Configura los parámetros globales de la plataforma, integra pasarelas de comunicación y gestiona la seguridad de la base de datos congregacional.</p>
                    </div>
                </motion.div>

                {/* 2. Settings Grid Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                    
                    {/* Navigation Sidebar */}
                    <motion.aside variants={containerVariants} initial="hidden" animate="show" className="lg:col-span-3 space-y-2">
                        <SettingsNavButton active={activeSection === 'general'} onClick={() => setActiveTab('general')} icon={Globe} label="Información General" />
                        <SettingsNavButton active={activeSection === 'integrations'} onClick={() => setActiveTab('integrations')} icon={Zap} label="APIs & Integraciones" />
                        <SettingsNavButton active={activeSection === 'notifications'} onClick={() => setActiveTab('notifications')} icon={Bell} label="Notificaciones" />
                        <SettingsNavButton active={activeSection === 'security'} onClick={() => setActiveTab('security')} icon={Lock} label="Privacidad & Datos" />
                        <div className="h-px bg-slate-200 dark:bg-white/5 my-6 mx-4" />
                        <SettingsNavButton active={false} onClick={() => {}} icon={Server} label="Estado del Servidor" />
                    </motion.aside>

                    {/* Main Settings Form */}
                    <motion.div variants={itemVariants} initial="hidden" animate="show" className="lg:col-span-9 bg-white dark:bg-[#15171c] rounded-[3rem] border border-slate-100 dark:border-white/5 p-10 lg:p-14 shadow-xl shadow-slate-200/20 dark:shadow-none">
                        <AnimatePresence mode="wait">
                            {activeSection === 'general' && (
                                <motion.div key="general" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="space-y-10">
                                    <div className="space-y-2 border-b border-slate-50 dark:border-white/5 pb-6">
                                        <h3 className="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tighter">Parámetros de Identidad</h3>
                                        <p className="text-sm text-slate-500 font-medium">Define cómo se identifica tu ministerio en los reportes y comunicaciones.</p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                        <SettingInput label="Nombre de la Iglesia" value={config.churchName} onChange={val => setConfig({...config, churchName: val})} />
                                        <SettingInput label="Email de Respuesta" value={config.contactEmail} onChange={val => setConfig({...config, contactEmail: val})} />
                                        <div className="space-y-2">
                                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-4">Zona Horaria</label>
                                            <select className="w-full bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 rounded-2xl px-6 py-4 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none" value={config.timezone} onChange={e => setConfig({...config, timezone: e.target.value})}>
                                                <option value="America/Bogota">Bogotá (GMT-5)</option>
                                                <option value="America/New_York">New York (GMT-4)</option>
                                                <option value="Europe/Madrid">Madrid (GMT+2)</option>
                                            </select>
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'integrations' && (
                                <motion.div key="integrations" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="space-y-10">
                                    <div className="space-y-2 border-b border-slate-50 dark:border-white/5 pb-6">
                                        <h3 className="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tighter">Pasarelas de Conexión</h3>
                                        <p className="text-sm text-slate-500 font-medium">Habilita canales oficiales para mensajería automática y alertas.</p>
                                    </div>

                                    <div className="space-y-6">
                                        <ToggleSetting 
                                            icon={Smartphone} color="text-green-500" title="Canal de WhatsApp Business" 
                                            desc="Permite a MESH AI enviar mensajes directos de bienvenida y seguimiento."
                                            active={config.enableWhatsApp} onToggle={v => setConfig({...config, enableWhatsApp: v})}
                                        />
                                        <ToggleSetting 
                                            icon={Smartphone} color="text-blue-500" title="Notificaciones SMS" 
                                            desc="Ideal para alertas urgentes y recordatorios de eventos sin conexión."
                                            active={config.enableSMS} onToggle={v => setConfig({...config, enableSMS: v})}
                                        />
                                        {config.enableSMS && (
                                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} className="ml-12 pl-6 border-l-2 border-blue-500/20 pt-4 pb-8 space-y-6">
                                                <SettingInput label="Twilio Account SID" value={config.twilioApiKey} onChange={v => setConfig({...config, twilioApiKey: v})} placeholder="ACxxxxxxxxxxxxxxxx" />
                                                <SettingInput label="Auth Token" value="••••••••••••••••" onChange={() => {}} type="password" />
                                            </motion.div>
                                        )}
                                        <div className="pt-6 border-t border-slate-50 dark:border-white/5">
                                            <SettingInput label="Servidor SMTP Principal" value={config.smtpServer} onChange={v => setConfig({...config, smtpServer: v})} placeholder="smtp.mail.faro.org" />
                                        </div>
                                    </div>
                                </motion.div>
                            )}

                            {activeSection === 'security' && (
                                <motion.div key="security" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }} className="space-y-10">
                                    <div className="space-y-2 border-b border-slate-50 dark:border-white/5 pb-6">
                                        <h3 className="text-2xl font-black text-slate-800 dark:text-white uppercase tracking-tighter">Privacidad y Resguardo</h3>
                                        <p className="text-sm text-slate-500 font-medium">Configuraciones de seguridad para la base de datos de miembros.</p>
                                    </div>

                                    <div className="p-8 rounded-[2.5rem] bg-rose-50 dark:bg-rose-500/10 border border-rose-100 dark:border-rose-500/20 flex flex-col md:flex-row items-center justify-between gap-8 group">
                                        <div className="flex items-center gap-6">
                                            <div className="size-16 rounded-[1.5rem] bg-white dark:bg-rose-500 flex items-center justify-center text-rose-600 dark:text-white shadow-xl"><AlertTriangle size={32} /></div>
                                            <div className="space-y-1">
                                                <h4 className="text-xl font-black text-rose-900 dark:text-rose-400">Zona de Peligro</h4>
                                                <p className="text-sm text-rose-700 dark:text-rose-500/70 font-medium">La purga de base de datos eliminará todo el historial de intercesión y miembros.</p>
                                            </div>
                                        </div>
                                        <button className="px-8 py-4 bg-rose-600 hover:bg-rose-700 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl shadow-rose-600/20 active:scale-95">
                                            Ejecutar Purga
                                        </button>
                                    </div>

                                    <div className="p-8 rounded-[2.5rem] bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 flex items-center justify-between">
                                        <div className="flex items-center gap-6">
                                            <div className="size-16 rounded-[1.5rem] bg-white dark:bg-blue-500 flex items-center justify-center text-blue-600 dark:text-white shadow-xl"><Database size={32} /></div>
                                            <div className="space-y-1">
                                                <h4 className="text-xl font-black text-blue-900 dark:text-blue-400">Respaldo Automático</h4>
                                                <p className="text-sm text-blue-700 dark:text-blue-500/70 font-medium">MESH realiza un backup en la nube cada 24 horas.</p>
                                            </div>
                                        </div>
                                        <span className="px-4 py-2 bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 rounded-xl text-[10px] font-black uppercase tracking-widest border border-blue-200">Activo</span>
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

function SettingsNavButton({ active, onClick, icon: Icon, label }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "w-full flex items-center justify-between px-6 py-4 rounded-2xl transition-all group",
                active 
                    ? "bg-white dark:bg-white/10 text-blue-600 dark:text-white shadow-xl shadow-slate-200/20 dark:shadow-none border border-slate-100 dark:border-white/5" 
                    : "text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-white/50 dark:hover:bg-white/5"
            )}
        >
            <div className="flex items-center gap-4">
                <Icon size={18} className={clsx("transition-colors", active ? "text-blue-600 dark:text-blue-400" : "text-slate-300 group-hover:text-slate-500")} />
                <span className="text-[13px] font-bold tracking-tight">{label}</span>
            </div>
            {active && <motion.div layoutId="setting-nav-dot" className="size-1.5 rounded-full bg-blue-600 dark:bg-blue-400 shadow-[0_0_8px_rgba(37,99,235,0.5)]" />}
        </button>
    );
}

function SettingInput({ label, value, onChange, placeholder, type = "text" }: any) {
    return (
        <div className="space-y-2">
            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-4">{label}</label>
            <input 
                type={type}
                value={value}
                onChange={e => onChange(e.target.value)}
                placeholder={placeholder}
                className="w-full bg-slate-50 dark:bg-black/20 border border-slate-100 dark:border-white/5 rounded-2xl px-6 py-4 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-4 focus:ring-blue-500/10 transition-all placeholder:text-slate-300"
            />
        </div>
    );
}

function ToggleSetting({ icon: Icon, color, title, desc, active, onToggle }: any) {
    return (
        <div className="flex items-center justify-between p-6 rounded-[2rem] bg-slate-50/50 dark:bg-black/20 border border-slate-100 dark:border-white/5 hover:border-blue-500/20 transition-all group">
            <div className="flex items-center gap-6">
                <div className={clsx("size-12 rounded-2xl bg-white dark:bg-[#15171c] flex items-center justify-center shadow-inner shrink-0 group-hover:scale-110 transition-transform", color)}>
                    <Icon size={20} strokeWidth={2.5} />
                </div>
                <div>
                    <h4 className="font-black text-slate-800 dark:text-white text-sm uppercase tracking-tight">{title}</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">{desc}</p>
                </div>
            </div>
            <button 
                onClick={() => onToggle(!active)}
                className={clsx(
                    "relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300 outline-none",
                    active ? "bg-blue-600" : "bg-slate-200 dark:bg-white/10"
                )}
            >
                <motion.div 
                    animate={{ x: active ? 24 : 4 }}
                    className="size-5 rounded-full bg-white shadow-lg"
                />
            </button>
        </div>
    );
}

function Loader2({ className, size = 24 }: any) {
    return <Activity size={size} className={clsx("animate-spin", className)} />;
}
