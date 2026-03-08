"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { useToast } from '@/context/ToastContext';
import { 
    Plus, 
    Trash2, 
    Image as ImageIcon, 
    Video, 
    Megaphone, 
    Loader2, 
    Layout,
    Globe,
    CheckCircle2
} from 'lucide-react';

export default function CMSAdminPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [loading, setLoading] = useState(true);
    const [announcements, setAnnouncements] = useState<any[]>([]);
    const [sermons, setSermons] = useState<any[]>([]);
    const [activeTab, setActiveTab] = useState<'noticias' | 'predicas'>('noticias');

    // Form States
    const [showForm, setShowForm] = useState(false);
    const [newAnn, setNewAnn] = useState({ title: '', content: '', category: 'Noticia', image_url: '' });
    const [newSermon, setNewSermon] = useState({ title: '', preacher: '', series: '', video_url: '', thumbnail_url: '', duration: '' });

    const fetchData = async () => {
        setLoading(true);
        try {
            const [annRes, serRes] = await Promise.all([
                fetch(apiUrl('/announcements/')),
                fetch(apiUrl('/sermons/'))
            ]);
            if (annRes.ok) setAnnouncements(await annRes.json());
            if (serRes.ok) setSermons(await serRes.json());
        } catch (e) {
            addToast("Error al cargar contenidos", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleCreateAnn = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch(apiUrl('/announcements/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify(newAnn)
            });
            if (res.ok) {
                addToast("Noticia publicada", "success");
                setShowForm(false);
                fetchData();
            }
        } catch (e) { addToast("Error al publicar", "error"); }
    };

    const handleCreateSermon = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const res = await fetch(apiUrl('/sermons/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
                body: JSON.stringify(newSermon)
            });
            if (res.ok) {
                addToast("Prédica añadida a la biblioteca", "success");
                setShowForm(false);
                fetchData();
            }
        } catch (e) { addToast("Error al guardar prédica", "error"); }
    };

    const handleDelete = async (type: 'ann' | 'ser', id: number) => {
        if (!confirm("¿Eliminar este contenido?")) return;
        const endpoint = type === 'ann' ? `/announcements/${id}` : `/sermons/${id}`;
        try {
            const res = await fetch(apiUrl(endpoint), {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) {
                addToast("Contenido eliminado", "success");
                fetchData();
            }
        } catch (e) { addToast("Error al eliminar", "error"); }
    };

    return (
        <div className="space-y-8 animate-in fade-in duration-500 max-w-6xl mx-auto">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
                        <Globe className="text-primary" size={32} /> Gestor de Contenidos Web
                    </h1>
                    <p className="text-slate-500 font-medium mt-1">Controla lo que se muestra en el inicio y la biblioteca pública.</p>
                </div>
                <button 
                    onClick={() => setShowForm(!showForm)}
                    className="flex items-center gap-2 bg-primary text-white px-6 py-3.5 rounded-2xl shadow-lg shadow-primary/40 active:scale-95 transition-all hover:bg-primary/90"
                >
                    <Plus size={18} />
                    <span className="font-bold text-xs uppercase tracking-widest">Crear Nuevo</span>
                </button>
            </header>

            {/* Tabs */}
            <div className="flex gap-4 p-1 bg-slate-200/50 dark:bg-slate-800/50 rounded-2xl w-fit">
                <button 
                    onClick={() => setActiveTab('noticias')}
                    className={`px-8 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === 'noticias' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                >
                    Noticias y Anuncios
                </button>
                <button 
                    onClick={() => setActiveTab('predicas')}
                    className={`px-8 py-3 rounded-xl text-sm font-bold transition-all ${activeTab === 'predicas' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
                >
                    Biblioteca de Prédicas
                </button>
            </div>

            {/* Content Form Overlay */}
            {showForm && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="bg-white dark:bg-slate-900 rounded-[2.5rem] p-10 max-w-lg w-full shadow-2xl border border-white/10">
                        <h3 className="text-2xl font-black mb-6">Nuevo Contenido ({activeTab === 'noticias' ? 'Noticia' : 'Prédica'})</h3>
                        
                        {activeTab === 'noticias' ? (
                            <form onSubmit={handleCreateAnn} className="space-y-4">
                                <input placeholder="Título de la noticia" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newAnn.title} onChange={e => setNewAnn({...newAnn, title: e.target.value})} required />
                                <textarea placeholder="Descripción o contenido..." className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10 h-32" value={newAnn.content} onChange={e => setNewAnn({...newAnn, content: e.target.value})} required />
                                <input placeholder="URL de la Imagen (Opcional)" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newAnn.image_url} onChange={e => setNewAnn({...newAnn, image_url: e.target.value})} />
                                <div className="flex gap-3 pt-4">
                                    <button type="submit" className="flex-1 bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-widest text-xs">Publicar Ahora</button>
                                    <button type="button" onClick={() => setShowForm(false)} className="px-6 bg-slate-100 dark:bg-white/5 rounded-2xl text-xs font-black uppercase">Cancelar</button>
                                </div>
                            </form>
                        ) : (
                            <form onSubmit={handleCreateSermon} className="space-y-4">
                                <input placeholder="Título de la prédica" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newSermon.title} onChange={e => setNewSermon({...newSermon, title: e.target.value})} required />
                                <div className="grid grid-cols-2 gap-4">
                                    <input placeholder="Predicador" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newSermon.preacher} onChange={e => setNewSermon({...newSermon, preacher: e.target.value})} required />
                                    <input placeholder="Serie" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newSermon.series} onChange={e => setNewSermon({...newSermon, series: e.target.value})} />
                                </div>
                                <input placeholder="URL del Video (YouTube)" className="w-full p-4 rounded-xl bg-slate-50 dark:bg-white/5 border-0 ring-1 ring-slate-200 dark:ring-white/10" value={newSermon.video_url} onChange={e => setNewSermon({...newSermon, video_url: e.target.value})} required />
                                <div className="flex gap-3 pt-4">
                                    <button type="submit" className="flex-1 bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-widest text-xs">Añadir Prédica</button>
                                    <button type="button" onClick={() => setShowForm(false)} className="px-6 bg-slate-100 dark:bg-white/5 rounded-2xl text-xs font-black uppercase">Cancelar</button>
                                </div>
                            </form>
                        )}
                    </div>
                </div>
            )}

            {/* List View */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {loading ? (
                    <div className="col-span-full py-20 flex justify-center"><Loader2 className="animate-spin text-primary" size={40} /></div>
                ) : activeTab === 'noticias' ? (
                    announcements.map(ann => (
                        <div key={ann.id} className="glass dark:bg-slate-900/40 rounded-3xl overflow-hidden border border-slate-200 dark:border-white/5 shadow-sm group">
                            <div className="h-48 bg-slate-200 dark:bg-slate-800 relative">
                                {ann.image_url ? (
                                    <img src={ann.image_url} alt={ann.title} className="w-full h-full object-cover" />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-slate-400"><ImageIcon size={48} /></div>
                                )}
                                <button onClick={() => handleDelete('ann', ann.id)} className="absolute top-4 right-4 size-10 bg-rose-500 text-white rounded-xl flex items-center justify-center shadow-lg opacity-0 group-hover:opacity-100 transition-all"><Trash2 size={18} /></button>
                            </div>
                            <div className="p-6">
                                <span className="px-3 py-1 bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest rounded-lg">{ann.category}</span>
                                <h4 className="text-xl font-black mt-3 mb-2">{ann.title}</h4>
                                <p className="text-sm text-slate-500 line-clamp-3">{ann.content}</p>
                            </div>
                        </div>
                    ))
                ) : (
                    sermons.map(ser => (
                        <div key={ser.id} className="glass dark:bg-slate-900/40 rounded-3xl overflow-hidden border border-slate-200 dark:border-white/5 shadow-sm group">
                            <div className="h-48 bg-slate-200 dark:bg-slate-800 relative">
                                {ser.thumbnail_url ? (
                                    <img src={ser.thumbnail_url} alt={ser.title} className="w-full h-full object-cover" />
                                ) : (
                                    <div className="flex items-center justify-center h-full text-slate-400 bg-navy-dark"><Video size={48} /></div>
                                )}
                                <button onClick={() => handleDelete('ser', ser.id)} className="absolute top-4 right-4 size-10 bg-rose-500 text-white rounded-xl flex items-center justify-center shadow-lg opacity-0 group-hover:opacity-100 transition-all"><Trash2 size={18} /></button>
                            </div>
                            <div className="p-6">
                                <p className="text-[10px] font-black uppercase tracking-widest text-primary mb-1">Serie: {ser.series || 'N/A'}</p>
                                <h4 className="text-lg font-black">{ser.title}</h4>
                                <p className="text-sm text-slate-500 font-medium mt-1">{ser.preacher}</p>
                            </div>
                        </div>
                    ))
                )}

                {((activeTab === 'noticias' && announcements.length === 0) || (activeTab === 'predicas' && sermons.length === 0)) && !loading && (
                    <div className="col-span-full py-24 text-center bg-slate-50 dark:bg-slate-900/30 border border-dashed border-slate-200 dark:border-white/10 rounded-[3rem] flex flex-col items-center">
                        <Layout size={48} className="text-slate-300 mb-4" />
                        <p className="text-slate-500 font-black uppercase tracking-widest text-xs">No hay contenidos publicados todavía.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
