"use client";

import React, { useEffect, useState } from "react";
import { Check, Clock, Shield, X, Loader2, User, Edit2, MessageSquare } from "lucide-react";
import { apiUrl } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/context/ToastContext";

interface Testimonial {
  id: number;
  content: string;
  emotion: string;
  is_approved: boolean;
  created_at: string;
  author_id: number;
}

export default function AdminTestimonialsPage() {
  const { token } = useAuth();
  const { addToast } = useToast();
  const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<'pendientes' | 'aprobados'>('pendientes');

  const fetchTestimonials = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(apiUrl("/admin/testimonials/"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        addToast("Error al cargar testimonios", "error");
        setTestimonials([]);
        return;
      }
      const data = await response.json();
      setTestimonials(data);
    } catch {
      addToast("Error de conexión", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTestimonials();
  }, [token]);

  const handleAction = async (id: number, approved: boolean) => {
    if (!token) return;

    try {
      const response = await fetch(apiUrl(`/admin/testimonials/${id}`), {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_approved: approved }),
      });

      if (response.ok) {
        addToast(approved ? "Testimonio aprobado" : "Testimonio rechazado", "success");
        fetchTestimonials();
      } else {
        addToast("Error al procesar", "error");
      }
    } catch {
      addToast("Error de conexión", "error");
    }
  };

  const filteredTestimonials = testimonials.filter(t => filter === 'pendientes' ? !t.is_approved : t.is_approved);

  return (
    <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
            <h1 className="flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                <Shield className="text-primary" size={32} /> Moderación
            </h1>
            <p className="text-slate-500 font-medium mt-1">Revisa y aprueba los testimonios de la congregación.</p>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex p-1 bg-slate-200/50 dark:bg-slate-800/50 rounded-2xl w-full max-w-sm mb-6">
        <button 
            onClick={() => setFilter('pendientes')}
            className={`flex-1 py-3 px-6 rounded-xl text-sm font-bold transition-all ${filter === 'pendientes' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
        >
            Pendientes
        </button>
        <button 
            onClick={() => setFilter('aprobados')}
            className={`flex-1 py-3 px-6 rounded-xl text-sm font-bold transition-all ${filter === 'aprobados' ? 'bg-white dark:bg-slate-700 shadow-sm text-primary' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
        >
            Aprobados
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="h-12 w-12 animate-spin text-primary" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredTestimonials.map((t) => (
            <div key={t.id} className="glass dark:bg-slate-800/40 rounded-3xl p-6 shadow-sm flex flex-col justify-between border border-slate-200 dark:border-white/5 transition-transform hover:shadow-md">
              <div>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                      <User size={20} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-900 dark:text-white">Autor #{t.author_id}</p>
                      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1 mt-0.5">
                        <Clock size={10} /> {new Date(t.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  {!t.is_approved && (
                    <span className="px-3 py-1 rounded-full bg-amber-500/10 text-[10px] font-bold text-amber-500 uppercase tracking-wider border border-amber-500/20">Pendiente</span>
                  )}
                </div>
                
                <div className="space-y-3 mb-6">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">{t.emotion}</span>
                  </div>
                  <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-medium italic">
                    &quot;{t.content}&quot;
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 pt-4 border-t border-slate-100 dark:border-white/5">
                {!t.is_approved ? (
                  <>
                    <button
                      onClick={() => handleAction(t.id, false)}
                      className="flex-1 flex items-center justify-center gap-2 bg-rose-50 dark:bg-rose-500/10 text-rose-600 py-3 rounded-xl text-xs font-bold hover:bg-rose-100 dark:hover:bg-rose-500/20 transition-all border border-rose-100 dark:border-rose-500/20"
                    >
                      <X size={16} /> Rechazar
                    </button>
                    <button className="flex items-center justify-center size-12 border border-slate-200 dark:border-white/10 text-slate-500 hover:text-primary py-3 rounded-xl transition-all">
                      <Edit2 size={16} />
                    </button>
                    <button
                      onClick={() => handleAction(t.id, true)}
                      className="flex-1 flex items-center justify-center gap-2 bg-emerald-500 text-white py-3 rounded-xl text-xs font-bold shadow-lg shadow-emerald-500/30 hover:bg-emerald-600 transition-all active:scale-95"
                    >
                      <Check size={16} /> Aprobar
                    </button>
                  </>
                ) : (
                  <button
                      onClick={() => handleAction(t.id, false)}
                      className="w-full flex items-center justify-center gap-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 py-3 rounded-xl text-xs font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition-all"
                    >
                      Ocultar / Revocar
                  </button>
                )}
              </div>
            </div>
          ))}

          {filteredTestimonials.length === 0 && (
            <div className="col-span-full bg-slate-50 dark:bg-slate-900/30 border border-dashed border-slate-200 dark:border-white/10 rounded-[2.5rem] py-24 text-center flex flex-col items-center">
              <div className="size-16 bg-white dark:bg-slate-800 rounded-full flex items-center justify-center text-slate-300 mb-4 shadow-sm">
                <MessageSquare size={32} />
              </div>
              <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">No hay testimonios {filter}.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
