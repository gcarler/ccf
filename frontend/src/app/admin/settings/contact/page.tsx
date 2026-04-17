"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Contact, Phone, Mail, MapPin, Clock, Save, Edit2, Plus, Trash2 } from 'lucide-react';

const INITIAL_CONTACTS = [
    { id: 1, label: 'Línea Principal', value: '+57 (8) 420 0000', type: 'phone', active: true },
    { id: 2, label: 'WhatsApp Pastoral', value: '+57 300 000 0001', type: 'whatsapp', active: true },
    { id: 3, label: 'Correo General', value: 'info@ccfaro.org', type: 'email', active: true },
    { id: 4, label: 'Correo de Soporte', value: 'soporte@ccfaro.org', type: 'email', active: false },
    { id: 5, label: 'Dirección Sede Central', value: 'Calle 10 #5-20, Mocoa, Putumayo', type: 'address', active: true },
];

const TYPE_ICON: Record<string, any> = { phone: Phone, whatsapp: Phone, email: Mail, address: MapPin };
const TYPE_COLOR: Record<string, string> = {
    phone: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10',
    whatsapp: 'text-green-500 bg-green-50 dark:bg-green-500/10',
    email: 'text-blue-500 bg-blue-50 dark:bg-blue-500/10',
    address: 'text-amber-500 bg-amber-50 dark:bg-amber-500/10',
};

export default function AdminSettingsContactPage() {
    const [contacts, setContacts] = useState(INITIAL_CONTACTS);
    const [editing, setEditing] = useState(false);
    const [saved, setSaved] = useState(false);
    const [schedule, setSchedule] = useState([
        { day: 'Lunes – Viernes', hours: '8:00 AM – 12:00 PM / 2:00 PM – 6:00 PM' },
        { day: 'Sábados', hours: '9:00 AM – 1:00 PM' },
        { day: 'Domingos', hours: 'Actividades pastorales' },
    ]);

    const handleSave = () => {
        setSaved(true);
        setEditing(false);
        setTimeout(() => setSaved(false), 3000);
    };

    return (
        <div className="min-h-full bg-slate-950/20 font-display">
            <div className="bg-slate-900/40 backdrop-blur-xl border-b border-white/5 sticky top-0 z-20">
                <div className="px-8 py-5 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Contact size={18} className="text-primary" />
                        <h1 className="text-[13px] font-black uppercase tracking-widest text-white">
                            Información de Contacto
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        {saved && (
                            <motion.span initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
                                className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-xl text-[10px] font-black uppercase tracking-widest">
                                ✓ Guardado
                            </motion.span>
                        )}
                        {!editing ? (
                            <button onClick={() => setEditing(true)}
                                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/15 text-white border border-white/10 rounded-xl text-[11px] font-black uppercase tracking-widest transition-all">
                                <Edit2 size={14} /> Editar
                            </button>
                        ) : (
                            <button onClick={handleSave}
                                className="flex items-center gap-2 px-5 py-2 bg-primary hover:bg-primary/80 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-lg shadow-primary/20 transition-all">
                                <Save size={14} /> Guardar
                            </button>
                        )}
                    </div>
                </div>
            </div>

            <div className="max-w-2xl mx-auto px-8 py-10 space-y-8">
                {/* Contact Points */}
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6">
                    <div className="flex items-center justify-between mb-6">
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Medios de Contacto</p>
                        {editing && (
                            <button className="flex items-center gap-1 text-primary text-[10px] font-black uppercase tracking-widest hover:opacity-70 transition-opacity">
                                <Plus size={12} /> Agregar
                            </button>
                        )}
                    </div>
                    <div className="space-y-3">
                        {contacts.map(c => {
                            const Icon = TYPE_ICON[c.type] ?? Phone;
                            return (
                                <div key={c.id} className="flex items-center gap-4 p-3 rounded-2xl bg-white/5 hover:bg-white/8 transition-all">
                                    <div className={`size-10 rounded-xl flex items-center justify-center shrink-0 ${TYPE_COLOR[c.type]}`}>
                                        <Icon size={16} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">{c.label}</p>
                                        {editing ? (
                                            <input
                                                value={c.value}
                                                onChange={e => setContacts(prev => prev.map(x => x.id === c.id ? { ...x, value: e.target.value } : x))}
                                                className="bg-transparent border-b border-white/20 text-sm text-white w-full outline-none focus:border-primary transition-colors py-0.5"
                                            />
                                        ) : (
                                            <p className="text-sm text-slate-200 font-medium truncate">{c.value}</p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0">
                                        <button
                                            onClick={() => setContacts(prev => prev.map(x => x.id === c.id ? { ...x, active: !x.active } : x))}
                                            className={`w-10 h-5 rounded-full transition-all ${c.active ? 'bg-primary' : 'bg-white/10'} relative`}
                                        >
                                            <div className={`absolute top-0.5 size-4 rounded-full bg-white transition-all ${c.active ? 'left-5' : 'left-0.5'}`} />
                                        </button>
                                        {editing && (
                                            <button onClick={() => setContacts(prev => prev.filter(x => x.id !== c.id))}
                                                className="p-1.5 text-rose-500/50 hover:text-rose-500 transition-colors rounded-lg hover:bg-rose-500/10">
                                                <Trash2 size={14} />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </motion.div>

                {/* Office Hours */}
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
                    className="bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-3xl p-6">
                    <div className="flex items-center gap-2 mb-6">
                        <Clock size={14} className="text-primary" />
                        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Horarios de Atención</p>
                    </div>
                    <div className="space-y-3">
                        {schedule.map((s, i) => (
                            <div key={i} className="flex items-center justify-between p-3 rounded-2xl bg-white/5">
                                <p className="text-sm font-bold text-slate-300">{s.day}</p>
                                {editing ? (
                                    <input
                                        value={s.hours}
                                        onChange={e => setSchedule(prev => prev.map((x, xi) => xi === i ? { ...x, hours: e.target.value } : x))}
                                        className="bg-transparent border-b border-white/20 text-sm text-white text-right outline-none focus:border-primary transition-colors w-64"
                                    />
                                ) : (
                                    <p className="text-[11px] text-slate-400 font-medium">{s.hours}</p>
                                )}
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>
        </div>
    );
}

