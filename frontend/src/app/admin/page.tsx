"use client";

import React, { useEffect, useState } from "react";
import { Check, Clock, Shield, X, Loader2, ArrowUpRight, FileText, CheckCircle2, TrendingUp, Users, Calendar, CheckSquare, MessageSquare } from "lucide-react";
import clsx from "clsx";
import { apiUrl } from "../../lib/api";
import { useAuth } from "@/context/AuthContext";
import Link from 'next/link';

interface Testimonial {
  id: number;
  content: string;
  emotion: string;
  is_approved: boolean;
  created_at: string;
  author_id: number;
}

interface AgentTask {
  id: number;
  title: string;
  description?: string;
  status: string;
  priority: string;
}

interface AgentInsight {
  id: number;
  title: string;
  insight_type: string;
  payload: string;
}

export default function AdminDashboardPage() {
  const { token, user } = useAuth();
  const [testimonials, setTestimonials] = useState<Testimonial[]>([]);
  const [agentTasks, setAgentTasks] = useState<AgentTask[]>([]);
  const [agentInsights, setAgentInsights] = useState<AgentInsight[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      if (!token) return;
      setLoading(true);
      try {
        const [testRes, taskRes, insightRes] = await Promise.all([
          fetch(apiUrl("/admin/testimonials/"), { headers: { Authorization: `Bearer ${token}` } }),
          fetch(apiUrl("/agents/tasks"), { headers: { Authorization: `Bearer ${token}` } }),
          fetch(apiUrl("/agents/insights"), { headers: { Authorization: `Bearer ${token}` } })
        ]);

        if (testRes.ok) setTestimonials(await testRes.json());
        if (taskRes.ok) setAgentTasks(await taskRes.json());
        if (insightRes.ok) setAgentInsights(await insightRes.json());
      } catch (e) {
        console.error("Error fetching admin data", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [token]);

  const pendingTestimonials = testimonials.filter(t => !t.is_approved).length;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">Bienvenido, {user?.username}</h1>
          <p className="text-slate-500 font-medium mt-1">Resumen del estado de la iglesia y la plataforma.</p>
        </div>
        <div className="flex gap-3">
          <button className="px-5 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-xl text-xs font-bold shadow-sm hover:shadow-md transition-all flex items-center gap-2">
            <Calendar size={16} /> Este Mes
          </button>
          <button className="px-5 py-2.5 bg-primary text-white rounded-xl text-xs font-bold shadow-lg shadow-primary/30 hover:bg-primary/90 transition-all flex items-center gap-2">
            Generar Reporte <ArrowUpRight size={16} />
          </button>
        </div>
      </header>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Highlight Stat */}
        <div className="lg:col-span-2 relative overflow-hidden rounded-[2.5rem] bg-gradient-to-br from-primary to-blue-600 p-8 text-white shadow-xl shadow-primary/20">
          <div className="relative z-10 flex flex-col h-full justify-between">
            <div>
              <p className="text-blue-100 text-sm font-bold uppercase tracking-widest mb-2">Ofrendas del Mes</p>
              <h3 className="text-5xl font-black">$12,450.00</h3>
            </div>
            <div className="flex items-center gap-2 mt-6 bg-white/20 w-fit px-3 py-1.5 rounded-xl text-xs font-bold backdrop-blur-md">
              <TrendingUp size={16} />
              <span>+15% vs mes anterior</span>
            </div>
          </div>
          <div className="absolute -right-10 -bottom-10 size-48 bg-white/10 rounded-full blur-3xl"></div>
        </div>

        <div className="rounded-[2.5rem] bg-white dark:bg-slate-800/40 p-8 border border-slate-200 dark:border-white/5 shadow-sm flex flex-col justify-between">
          <div className="size-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-4">
            <Users size={24} />
          </div>
          <div>
            <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">Miembros Activos</p>
            <p className="text-3xl font-black text-slate-900 dark:text-white">1,240</p>
            <p className="text-xs text-emerald-500 font-bold mt-2 flex items-center gap-1"><ArrowUpRight size={12} /> +42 nuevos</p>
          </div>
        </div>

        <div className="rounded-[2.5rem] bg-white dark:bg-slate-800/40 p-8 border border-slate-200 dark:border-white/5 shadow-sm flex flex-col justify-between">
          <div className="size-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 mb-4">
            <span className="material-symbols-outlined text-[24px]">event_available</span>
          </div>
          <div>
            <p className="text-slate-400 text-[10px] font-black uppercase tracking-widest mb-1">Asistencia Promedio</p>
            <p className="text-3xl font-black text-slate-900 dark:text-white">850</p>
            <p className="text-xs text-emerald-500 font-bold mt-2 flex items-center gap-1"><ArrowUpRight size={12} /> Estable</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 pt-4">

        {/* Tasks Section */}
        <div className="xl:col-span-2 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-slate-900 dark:text-white">Acciones Requeridas</h3>
            <div className="size-8 bg-rose-500/10 text-rose-500 rounded-full flex items-center justify-center text-sm font-bold">{agentTasks.length + (pendingTestimonials > 0 ? 1 : 0)}</div>
          </div>

          <div className="space-y-4">
            {/* Dynamic Agent Tasks */}
            {agentTasks.map((task) => (
              <div key={task.id} className="flex flex-col sm:flex-row items-start sm:items-center gap-5 p-5 rounded-3xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-white/5 shadow-sm hover:shadow-md transition-all">
                <div className={clsx("size-14 shrink-0 rounded-2xl flex items-center justify-center",
                  task.priority === 'high' ? "bg-rose-500/10 text-rose-500" : "bg-primary/10 text-primary")}>
                  {task.priority === 'high' ? <Shield size={24} /> : <CheckSquare size={24} />}
                </div>
                <div className="flex-1">
                  <p className="text-base font-bold text-slate-900 dark:text-white">{task.title}</p>
                  <p className="text-sm text-slate-500">{task.description}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className="px-3 py-1 bg-slate-100 dark:bg-white/5 text-[10px] font-black uppercase tracking-widest rounded-lg">
                    {task.status}
                  </span>
                  <button className="text-[10px] font-bold text-primary hover:underline uppercase tracking-tight">Atender</button>
                </div>
              </div>
            ))}

            {/* Dynamic Task from Testimonials */}
            {pendingTestimonials > 0 && (
              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5 p-5 rounded-3xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-white/5 shadow-sm hover:shadow-md transition-all border-l-4 border-l-amber-500">
                <div className="size-14 shrink-0 rounded-2xl bg-amber-500/10 flex items-center justify-center text-amber-500">
                  <MessageSquare size={24} />
                </div>
                <div className="flex-1">
                  <p className="text-base font-bold text-slate-900 dark:text-white">Moderación de Testimonios</p>
                  <p className="text-sm text-slate-500">Hay {pendingTestimonials} testimonios esperando aprobación pública.</p>
                </div>
                <Link href="/admin/testimonials" className="w-full sm:w-auto px-6 py-3 bg-slate-100 dark:bg-white/5 text-slate-900 dark:text-white text-xs font-bold uppercase tracking-widest rounded-xl hover:bg-slate-200 dark:hover:bg-white/10 transition-colors text-center">
                  Revisar
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Neural Insights Section */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-slate-900 dark:text-white tracking-tighter">Neural Insights</h3>
            <div className="px-3 py-1 bg-indigo-500/10 text-indigo-400 text-[9px] font-black rounded-lg border border-indigo-500/20 uppercase tracking-widest animate-pulse">Live</div>
          </div>

          <div className="space-y-4">
            {agentInsights.map((insight) => {
              let parsedPayload;
              try {
                parsedPayload = JSON.parse(insight.payload);
              } catch (e) {
                parsedPayload = { insight: insight.payload };
              }

              return (
                <div key={insight.id} className="p-6 rounded-[2.5rem] bg-indigo-500/5 border border-indigo-500/10 shadow-sm relative overflow-hidden group hover:bg-indigo-500/10 transition-all">
                  <div className="relative z-10">
                    <div className="flex items-center justify-between mb-3">
                      <p className="text-[9px] font-black uppercase tracking-[0.3em] text-indigo-400">{insight.insight_type}</p>
                      <ArrowUpRight size={14} className="text-indigo-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </div>
                    <h4 className="text-sm font-black text-slate-900 dark:text-white leading-tight">{insight.title}</h4>
                    <div className="mt-4 p-4 bg-white/40 dark:bg-black/20 rounded-2xl border border-white/5">
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium leading-relaxed italic">
                        {parsedPayload.insight || parsedPayload.metric || parsedPayload.impact || "Analizando flujo de datos..."}
                      </p>
                      {parsedPayload.recommendation && (
                        <div className="mt-2 text-[10px] text-primary font-bold uppercase tracking-tight">Rec: {parsedPayload.recommendation}</div>
                      )}
                    </div>
                  </div>
                  <div className="absolute -right-6 -bottom-6 size-24 bg-indigo-500/10 rounded-full blur-3xl group-hover:bg-indigo-500/20 transition-all duration-700"></div>
                </div>
              );
            })}
            {agentInsights.length === 0 && (
              <div className="p-8 text-center rounded-[2.5rem] border border-dashed border-slate-200 dark:border-white/10">
                <p className="text-xs text-slate-400 italic font-medium">No hay nuevos hallazgos neuronales en este momento.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
