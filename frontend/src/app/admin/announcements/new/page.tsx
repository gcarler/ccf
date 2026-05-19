"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
    Bell, 
    Save, 
    Send, 
    ImageIcon, 
    Users, 
    Eye, 
    Sparkles,
    Bot
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';

export default function NewAnnouncementPage() {
    const router = useRouter();
    const { token } = useAuth();
    const { addToast } = useToast();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState({
        title: '',
        content: '',
        category: 'General',
        is_featured: false,
        status: 'published'
    });

    const handlePublish = async () => {
        if (!formData.title || !formData.content) {
            addToast('Completa el título y el contenido', 'warning');
            return;
        }
        setLoading(true);
        try {
            await apiFetch('/cms/announcements', {
                method: 'POST',
                token,
                body: { ...formData, status: 'published' }
            });
            addToast('Anuncio publicado correctamente', 'success');
            router.push('/admin/announcements');
        } catch {
            addToast('Error al publicar el anuncio', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleSaveDraft = async () => {
        if (!formData.title || !formData.content) {
            addToast('Completa el tÃ­tulo y el contenido', 'warning');
            return;
        }
        setLoading(true);
        try {
            await apiFetch('/cms/announcements', {
                method: 'POST',
                token,
                body: { ...formData, status: 'draft' }
            });
            addToast('Borrador guardado en CMS', 'success');
            router.push('/admin/announcements');
        } catch {
            addToast('Error al guardar el borrador', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <AdminShell
            breadcrumbs={[
                { label: 'Comunicación', icon: Bell },
                { label: 'Nuevo Anuncio', icon: Send }
            ]}
        >
            <AdminHero
                eyebrow="Broadcast Center"
                title="Publicar Noticia Institucional"
                description="Crea anuncios de alto impacto que aparecerán en el dashboard de todos los usuarios. Comunica eventos, cambios de horario o noticias pastorales."
                tags={['Global Reach', 'Instant', 'Official']}
                watchers={['Comité de Comunicación', 'Pastoral']}
                primaryAction={{ label: loading ? 'Publicando...' : 'Lanzar Anuncio', icon: Send, onClick: handlePublish }}
                secondaryAction={{ label: 'Guardar Borrador', icon: Save, onClick: handleSaveDraft }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-32">
                {/* Editor Content */}
                <div className="lg:col-span-8 space-y-8">
                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8 relative overflow-hidden">
                        <div className="absolute top-0 right-0 -mr-12 -mt-12 size-40 bg-blue-600/5 rounded-full blur-3xl" />
                        
                        <div className="relative z-10 space-y-8">
                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Encabezado de la Noticia</label>
                                <input 
                                    value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})}
                                    placeholder="Ej: Gran Vigilia de Oración - Próximo Viernes"
                                    className="w-full bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-2xl py-5 px-8 text-lg font-black outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4">Cuerpo del Mensaje</label>
                                <textarea 
                                    value={formData.content} onChange={e => setFormData({...formData, content: e.target.value})}
                                    placeholder="Escribe los detalles aquí..."
                                    className="w-full h-64 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/5 rounded-[2.5rem] p-8 text-[16px] font-medium leading-relaxed outline-none focus:ring-4 focus:ring-blue-500/10 transition-all resize-none"
                                />
                            </div>
                        </div>
                    </section>

                    {/* AI Copywriting Suggestion */}
                    <section className="bg-blue-50 dark:bg-blue-900/10 rounded-[3rem] p-10 border border-blue-100 dark:border-blue-500/20 flex gap-6 items-start group">
                        <div className="size-12 rounded-2xl bg-blue-600 flex items-center justify-center shrink-0 shadow-lg shadow-blue-500/20 transition-transform group-hover:scale-110"><Bot size={24} className="text-white" /></div>
                        <div className="space-y-2">
                            <h4 className="text-[11px] font-black text-blue-600 dark:text-blue-400 uppercase tracking-widest flex items-center gap-2"><Sparkles size={14} /> Optimus Copy Helper</h4>
                            <p className="text-[14px] text-slate-600 dark:text-slate-300 font-medium italic leading-relaxed">
                                &ldquo;Tu anuncio tiene un tono formal excelente. Sugiero añadir una invitación a la acción (Call to Action) al final para aumentar la participación en un 20%.&rdquo;
                            </p>
                        </div>
                    </section>
                </div>

                {/* Settings Sidebar */}
                <aside className="lg:col-span-4 space-y-8">
                    <section className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] shadow-xl space-y-8">
                        <h3 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Ajustes de Publicación</h3>
                        
                        <div className="space-y-6">
                            <div className="space-y-2">
                                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest px-2">Categoría</label>
                                <select 
                                    value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})}
                                    className="w-full bg-slate-50 dark:bg-black/10 border-none rounded-xl py-3 px-4 text-xs font-bold outline-none"
                                >
                                    <option>General</option>
                                    <option>Eventos</option>
                                    <option>Academia</option>
                                    <option>Misiones</option>
                                </select>
                            </div>

                            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-black/10 rounded-2xl">
                                <div className="flex items-center gap-3">
                                    <Users size={18} className="text-slate-400" />
                                    <span className="text-[11px] font-bold text-slate-600 dark:text-slate-300 uppercase">Alcance Global</span>
                                </div>
                                <div className="size-5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]" />
                            </div>

                            <button
                                type="button"
                                onClick={() => setFormData({ ...formData, is_featured: !formData.is_featured })}
                                className={`w-full flex items-center justify-between p-4 rounded-2xl transition-all ${
                                    formData.is_featured
                                        ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-300'
                                        : 'bg-slate-50 dark:bg-black/10 text-slate-500 dark:text-slate-300'
                                }`}
                            >
                                <span className="text-[11px] font-bold uppercase">Destacar anuncio</span>
                                <span className={`size-5 rounded-full ${formData.is_featured ? 'bg-blue-600' : 'bg-slate-300 dark:bg-white/20'}`} />
                            </button>

                            <button className="w-full py-4 border-2 border-dashed border-slate-200 dark:border-white/10 rounded-2xl text-slate-400 hover:text-blue-600 transition-all flex flex-col items-center gap-2">
                                <ImageIcon size={24} />
                                <span className="text-[9px] font-black uppercase">Añadir Imagen de Portada</span>
                            </button>
                        </div>
                    </section>

                    <section className="p-8 bg-slate-900 rounded-[3rem] text-white shadow-2xl space-y-6 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-blue-600/20 rounded-full blur-3xl" />
                        <div className="relative z-10 flex flex-col gap-6">
                            <div className="flex items-center gap-3">
                                <Eye size={20} className="text-blue-400" />
                                <h4 className="text-[11px] font-black uppercase tracking-widest">Vista Previa Móvil</h4>
                            </div>
                            <div className="aspect-[9/16] w-full rounded-3xl bg-white/5 border border-white/10 p-6 space-y-4">
                                <div className="h-4 w-2/3 bg-white/20 rounded-full" />
                                <div className="h-32 w-full bg-white/5 rounded-2xl" />
                                <div className="space-y-2">
                                    <div className="h-3 w-full bg-white/10 rounded-full" />
                                    <div className="h-3 w-full bg-white/10 rounded-full" />
                                    <div className="h-3 w-1/2 bg-white/10 rounded-full" />
                                </div>
                            </div>
                        </div>
                    </section>
                </aside>
            </div>
        </AdminShell>
    );
}

