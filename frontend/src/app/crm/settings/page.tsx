'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { Settings as SettingsIcon, Save, Key, Globe, Shield, Smartphone, Link2, Users } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';


export default function SettingsPage() {
    const { token } = useAuth();
    const { addToast } = useToast();

    const [isSaving, setIsSaving] = useState(false);

    const [config, setConfig] = useState<any>({
        churchName: '',
        contactEmail: '',
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
            addToast("Configuraciones guardadas correctamente", "success");
        } catch (err) {
            addToast("Error de conexión", "error");
        } finally {
            setIsSaving(false);
        }
    };


    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Configuración', icon: SettingsIcon }]}
            rightActions={
                <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-slate-900 px-6 py-2 rounded-2xl text-[11px] font-black tracking-widest text-white hover:bg-slate-800 transition-all uppercase disabled:opacity-50"
                >
                    {isSaving ? 'Guardando...' : (
                        <>
                            <Save size={16} /> Guardar
                        </>
                    )}
                </button>
            }
        >
            <AdminHero
                eyebrow="Configuración"
                title="Configuración del CRM"
                description="Administra parámetros globales, APIs y seguridad de la plataforma."
                tags={['APIs', 'Seguridad', 'IA']}
                watchers={['Equipo Sistemas', 'Optimus Brain']}
                primaryAction={{ label: 'Documentación API', icon: Link2, onClick: () => {} }}
            />

            <form onSubmit={handleSave} className="space-y-8 max-w-4xl mx-auto">

                {/* General Settings */}
                <div className="glass-card p-8 border border-slate-100 rounded-3xl shadow-sm">
                    <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
                        <Globe className="text-blue-500" size={24} />
                        <h2 className="text-lg font-black text-slate-800">Información General</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nombre de la Iglesia / Sede</label>
                            <input
                                value={config.churchName}
                                onChange={e => setConfig({ ...config, churchName: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email de Contacto Público</label>
                            <input
                                value={config.contactEmail}
                                onChange={e => setConfig({ ...config, contactEmail: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Zona Horaria</label>
                            <select
                                value={config.timezone}
                                onChange={e => setConfig({ ...config, timezone: e.target.value })}
                                className="w-full px-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white appearance-none"
                            >
                                <option value="America/Bogota">America/Bogota</option>
                                <option value="America/New_York">America/New_York</option>
                                <option value="Europe/Madrid">Europe/Madrid</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* API & Integrations Settings */}
                <div className="glass-card p-8 border border-slate-100 rounded-3xl shadow-sm">
                    <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
                        <Key className="text-indigo-500" size={24} />
                        <h2 className="text-lg font-black text-slate-800">Integraciones y APIs</h2>
                    </div>

                    <div className="space-y-6">
                        <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-100 bg-slate-50/50">
                            <div>
                                <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2"><Smartphone size={16} className="text-green-500" /> API de WhatsApp</h4>
                                <p className="text-xs text-slate-500 mt-1">Permite enviar mensajes a través del canal oficial de WhatsApp Business.</p>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={config.enableWhatsApp}
                                    onChange={e => setConfig({ ...config, enableWhatsApp: e.target.checked })}
                                />
                                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-green-500"></div>
                            </label>
                        </div>

                        <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-100 bg-slate-50/50">
                            <div>
                                <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2"><Smartphone size={16} className="text-blue-500" /> Pasarela SMS (Twilio)</h4>
                                <p className="text-xs text-slate-500 mt-1">Habilita notificaciones por mensajes de texto SMS.</p>
                            </div>
                            <label className="relative inline-flex items-center cursor-pointer">
                                <input
                                    type="checkbox"
                                    className="sr-only peer"
                                    checked={config.enableSMS}
                                    onChange={e => setConfig({ ...config, enableSMS: e.target.checked })}
                                />
                                <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                            </label>
                        </div>

                        {config.enableSMS && (
                            <div className="space-y-1.5 mt-4 ml-4 pl-4 border-l-2 border-blue-100">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">API Key de Twilio</label>
                                <input
                                    type="password"
                                    value={config.twilioApiKey}
                                    onChange={e => setConfig({ ...config, twilioApiKey: e.target.value })}
                                    className="w-full px-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white"
                                />
                            </div>
                        )}

                        <div className="space-y-1.5 mt-4">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Servidor SMTP (Envío de Emails)</label>
                            <input
                                value={config.smtpServer}
                                onChange={e => setConfig({ ...config, smtpServer: e.target.value })}
                                className="w-full max-w-md px-4 py-3 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm bg-white"
                            />
                        </div>
                    </div>
                </div>

                {/* Security Settings */}
                <div className="glass-card p-8 border border-slate-100 rounded-3xl shadow-sm mb-12">
                    <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-4">
                        <Shield className="text-rose-500" size={24} />
                        <h2 className="text-lg font-black text-slate-800">Seguridad CRM</h2>
                    </div>

                    <div className="p-4 rounded-2xl bg-rose-50 border border-rose-100 text-rose-800">
                        <h4 className="font-bold text-sm mb-1">Zona de Peligro</h4>
                        <p className="text-xs mb-4">Acciones irreversibles sobre la base de datos de miembros.</p>
                        <button type="button" className="px-4 py-2 bg-rose-600 text-white rounded-xl text-xs font-bold hover:bg-rose-700 transition-colors">
                            Purgar Base de Datos (Requiere Confirmación)
                        </button>
                    </div>
                </div>

            </form>
        </CrmShell>
    );
}
