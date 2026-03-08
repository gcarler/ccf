'use client';

import React, { useState } from 'react';
import {
    Send,
    MessageSquare,
    MessageCircle,
    Mail,
    Smartphone,
    Users,
    Search,
    History,
    CheckCircle2,
    Clock,
    Loader2
} from 'lucide-react';
import { apiUrl } from '@/lib/api';
import { useToast } from '@/context/ToastContext';

export default function MessagingPage() {
    const [channel, setChannel] = useState('whatsapp');
    const [recipientType, setRecipientType] = useState('all');
    const [messageContent, setMessageContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [history, setHistory] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(true);
    const { addToast } = useToast();

    const fetchHistory = async () => {
        setLoadingHistory(true);
        try {
            const response = await fetch(apiUrl('/messaging/history'));
            if (response.ok) {
                const data = await response.json();
                setHistory(data);
            }
        } catch (err) {
            console.error("Error fetching history", err);
        } finally {
            setLoadingHistory(false);
        }
    };

    React.useEffect(() => {
        fetchHistory();
    }, []);


    const handleSendBroadcast = async () => {
        if (!messageContent) return;
        setLoading(true);
        try {
            const response = await fetch(apiUrl('/messaging/send'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    member_id: 0, // 0 for mass broadcast / all 
                    channel: channel,
                    content: messageContent
                })
            });

            if (response.ok) {
                addToast("Comunicado masivo iniciado en segundo plano", "success");
                setMessageContent('');
                fetchHistory(); // Refresh history
            } else {

                addToast("Hubo un error al encolar el mensaje", "error");
            }
        } catch (err) {
            addToast("Error de conexión con el servicio", "error");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500 pb-20">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Centro de Mensajería</h1>
                    <p className="text-slate-500 mt-1">Comunícate de forma masiva y efectiva con toda la congregación.</p>
                </div>
                <div className="flex bg-slate-100 p-1.5 rounded-2xl">
                    <button className="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest bg-white shadow-sm text-blue-600">Nuevo</button>
                    <button className="px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest text-slate-500 hover:text-slate-700">Canales</button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left: Compose Message */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="glass-card p-8 bg-white border border-slate-100 shadow-2xl shadow-slate-100/50 relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-50/30 rounded-full -mr-32 -mt-32 blur-3xl -z-10"></div>

                        <h2 className="text-xl font-black mb-8 text-slate-900 flex items-center gap-3">
                            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white">
                                <Send size={20} />
                            </div>
                            Redactar Comunicado
                        </h2>

                        <div className="space-y-8">
                            {/* Channel Selection */}
                            <div>
                                <label className="block text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] mb-4">Canal de Envío</label>
                                <div className="grid grid-cols-3 gap-6">
                                    {[
                                        { id: 'whatsapp', name: 'WhatsApp', icon: MessageCircle, color: 'text-emerald-600', bg: 'bg-emerald-50', active: 'bg-emerald-600 text-white' },
                                        { id: 'sms', name: 'SMS', icon: Smartphone, color: 'text-blue-600', bg: 'bg-blue-50', active: 'bg-blue-600 text-white' },
                                        { id: 'email', name: 'Email', icon: Mail, color: 'text-indigo-600', bg: 'bg-indigo-50', active: 'bg-indigo-600 text-white' },
                                    ].map((ch) => (
                                        <button
                                            key={ch.id}
                                            onClick={() => setChannel(ch.id)}
                                            className={`flex flex-col items-center gap-3 p-6 rounded-3xl border transition-all duration-300 ${channel === ch.id ? ch.active + ' border-transparent shadow-xl shadow-slate-200' : 'bg-white border-slate-100 hover:border-blue-100 group'}`}
                                        >
                                            <ch.icon size={28} className={channel === ch.id ? 'text-white' : ch.color + ' group-hover:scale-110 transition-transform'} />
                                            <span className="text-xs font-black uppercase tracking-widest">{ch.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Recipient Selection */}
                            <div>
                                <label className="block text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] mb-4">Destinatarios</label>
                                <div className="flex flex-wrap gap-3">
                                    {[
                                        { id: 'all', name: 'Toda la Iglesia' },
                                        { id: 'families', name: 'Por Familias' },
                                        { id: 'members', name: 'Individual' },
                                    ].map((type) => (
                                        <button
                                            key={type.id}
                                            onClick={() => setRecipientType(type.id)}
                                            className={`px-6 py-2.5 rounded-2xl text-xs font-black uppercase tracking-widest border transition-all ${recipientType === type.id ? 'bg-slate-900 text-white border-slate-900 shadow-lg' : 'bg-white border-slate-100 text-slate-400 hover:bg-slate-50'}`}
                                        >
                                            {type.name}
                                        </button>
                                    ))}
                                </div>
                                {recipientType !== 'all' && (
                                    <div className="mt-4 animate-in slide-in-from-top-2 duration-300">
                                        <div className="relative">
                                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-300" size={16} />
                                            <input
                                                type="text"
                                                placeholder={recipientType === 'families' ? "Filtre por nombres de familia..." : "Busque miembros específicos..."}
                                                className="w-full pl-12 pr-6 py-4 rounded-2xl border border-slate-100 bg-slate-50 focus:outline-none focus:ring-4 focus:ring-blue-500/5 focus:border-blue-500 transition-all text-sm font-medium"
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Message Content */}
                            <div>
                                <label className="block text-[10px] font-black uppercase text-slate-400 tracking-[0.2em] mb-4">Mensaje</label>
                                <div className="relative border border-slate-100 rounded-3xl overflow-hidden focus-within:ring-4 focus-within:ring-blue-500/5 focus-within:border-blue-500 transition-all bg-white">
                                    <textarea
                                        rows={6}
                                        value={messageContent}
                                        onChange={(e) => setMessageContent(e.target.value)}
                                        placeholder="Escriba aquí el contenido del comunicado..."
                                        className="w-full p-6 focus:outline-none text-slate-700 font-medium resize-none"
                                    ></textarea>
                                    <div className="bg-slate-50/80 px-6 py-3 border-t border-slate-100 flex justify-between items-center">
                                        <span className="text-[10px] text-slate-400 font-black uppercase tracking-widest">
                                            {channel === 'sms' ? 'SMS: 160 caracteres máx' : 'Multimedia disponible'}
                                        </span>
                                        <span className={`text-[10px] font-black tracking-widest ${messageContent.length > 2000 ? 'text-rose-500' : 'text-slate-400'}`}>
                                            {messageContent.length} / 2000
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={handleSendBroadcast}
                                disabled={loading || !messageContent || messageContent.length > 2000}
                                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-5 rounded-3xl font-black text-sm uppercase tracking-[0.2em] shadow-2xl shadow-blue-100 transition-all flex items-center justify-center gap-4 group"
                            >
                                {loading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />}
                                {loading ? 'Enviando...' : 'Lanzar Comunicado'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Right: History & Stats */}
                <div className="space-y-8">
                    <div className="glass-card p-6 bg-white border border-slate-100 shadow-xl shadow-slate-100/30">
                        <h3 className="font-black text-xs uppercase tracking-[0.2em] text-slate-400 flex items-center gap-3 mb-8 px-2">
                            <History size={16} className="text-slate-300" />
                            Historial
                        </h3>
                        <div className="space-y-6">
                            {loadingHistory ? (
                                <div className="flex justify-center py-10">
                                    <Loader2 className="animate-spin text-slate-300" size={32} />
                                </div>
                            ) : history.length > 0 ? (
                                history.map((item) => (
                                    <div key={item.id} className="relative pl-6 border-l-2 border-slate-100 hover:border-blue-200 transition-colors py-1 group">
                                        <div className="absolute -left-[5px] top-2 w-2 h-2 rounded-full bg-slate-200 group-hover:bg-blue-300 transition-colors"></div>

                                        <div className="flex justify-between items-start mb-2">
                                            <span className={`text-[10px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest bg-emerald-50 text-emerald-600`}>
                                                Enviado
                                            </span>
                                            <span className="text-[10px] font-bold text-slate-300">
                                                {new Date(item.sent_at).toLocaleDateString()}
                                            </span>
                                        </div>

                                        <h4 className="font-bold text-slate-800 text-sm mb-1 leading-tight line-clamp-2">{item.content}</h4>

                                        <div className="flex items-center gap-3 mt-3">
                                            <div className="flex items-center gap-1.5 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                                {item.channel === 'whatsapp' ? <MessageCircle size={10} className="text-emerald-500" /> : item.channel === 'sms' ? <Smartphone size={10} className="text-blue-500" /> : <Mail size={10} className="text-indigo-500" />}
                                                {item.channel}
                                            </div>
                                            <div className="w-1 h-1 rounded-full bg-slate-100"></div>
                                            <div className="flex items-center gap-1.5 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                                <Users size={10} />
                                                ID: #{item.member_id === 0 ? 'Mass' : item.member_id}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="text-center py-10 space-y-2">
                                    <MessageSquare size={48} className="mx-auto text-slate-100" />
                                    <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Sin envíos registrados.</p>
                                </div>
                            )}
                        </div>


                        <button className="w-full mt-10 py-3 rounded-2xl border border-slate-100 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 hover:bg-slate-50 hover:text-slate-600 transition-all">
                            Ver Historial Completo
                        </button>
                    </div>

                    <div className="glass-card p-8 bg-slate-900 text-white relative overflow-hidden shadow-2xl shadow-slate-200">
                        <div className="absolute top-0 right-0 p-4 opacity-10 scale-150 rotate-12">
                            <MessageSquare size={120} />
                        </div>
                        <h3 className="text-lg font-black mb-6 uppercase tracking-widest">Políticas</h3>
                        <ul className="space-y-4 text-xs text-slate-400 font-bold tracking-wide">
                            <li className="flex gap-4 items-start">
                                <div className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 shadow-[0_0_10px_rgba(59,130,246,0.8)]"></div>
                                <span>Frecuencia: Máximo 2 envíos masivos semanales recomendados.</span>
                            </li>
                            <li className="flex gap-4 items-start">
                                <div className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0"></div>
                                <span>Horarios: Restringidos de 08:30 a 20:00 para cumplimiento legal.</span>
                            </li>
                            <li className="flex gap-4 items-start border-t border-white/5 pt-4 mt-2">
                                <div className="mt-1 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></div>
                                <span>Privacidad: Los datos de contacto están cifrados y protegidos.</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}
