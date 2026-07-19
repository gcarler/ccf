"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle,
  Check,
  DollarSign,
  FileText,
  Landmark,
  Plus,
  Search,
  Trash2,
  Send,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";
import { toast } from "sonner";

interface ExpenseItem {
  expense_date: string;
  category: string;
  description: string;
  amount: number;
  vendor: string;
}

interface ExpenseReportItem {
  id: string;
  description: string;
  amount: number;
}

interface ExpenseReport {
  id: string;
  report_number: string;
  description: string;
  total_amount: number;
  status: string;
  items: ExpenseReportItem[];
}

const SECTIONS = [
  {
    title: "Módulos",
    items: [
      { id: "contabilidad", label: "Contabilidad", href: "/plataforma/contabilidad", icon: Landmark },
      { id: "facturacion", label: "Facturación", href: "/plataforma/facturacion", icon: FileText },
      { id: "gastos", label: "Gastos", href: "/plataforma/gastos", icon: DollarSign },
      { id: "documentos", label: "Documentos", href: "/plataforma/documentos", icon: FileText },
      { id: "firma", label: "Firma Digital", href: "/plataforma/firma", icon: CheckCircle },
    ],
  },
];

function fmtCOP(n: number) {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n);
}

export default function GastosPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [reports, setReports] = useState<ExpenseReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ description: "", items: [{ expense_date: "", category: "", description: "", amount: 0, vendor: "" }] as ExpenseItem[] });

  useEffect(() => {
    const ctrl = new AbortController();
    if (!token) { setLoading(false); return; }
    setLoading(true);
    apiFetch<ExpenseReport[]>("/finance-suite/expense-reports?limit=50", { token, cache: "no-store", signal: ctrl.signal })
      .then(r => { if (Array.isArray(r)) setReports(r); })
      .catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [token]);

  const filtered = reports.filter((r) => r.report_number?.toLowerCase().includes(search.toLowerCase()) || r.description?.toLowerCase().includes(search.toLowerCase()));

  const handleCreate = async () => {
    if (!token) return;
    const payload = {
      description: form.description,
      items: form.items.filter((it) => it.description && it.amount > 0),
    };
    try {
      await apiFetch("/finance-suite/expense-reports", { token, method: "POST", body: payload });
      setShowCreate(false);
      setForm({ description: "", items: [{ expense_date: "", category: "", description: "", amount: 0, vendor: "" }] });
      toast.success("Reporte creado");
      fetchData();
    } catch (e) { console.error(e); toast.error("Error al crear reporte"); }
  };

  const handleAction = async (id: string, action: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/expense-reports/${id}/${action}`, { token, method: "POST" });
      toast.success("Acción realizada");
      fetchData();
    } catch (e) { console.error(e); toast.error("Error al realizar acción"); }
  };

  const fetchData = async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const r = await apiFetch<ExpenseReport[]>("/finance-suite/expense-reports?limit=50", { token, cache: "no-store" });
      if (Array.isArray(r)) setReports(r);
    } catch (e) { console.error(e); toast.error("Error al cargar datos"); }
    setLoading(false);
  };

  const statusConfig: Record<string, { label: string; color: string }> = {
    draft: { label: "Borrador", color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]" },
    submitted: { label: "Enviado", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
    approved: { label: "Aprobado", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" },
    rejected: { label: "Rechazado", color: "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" },
    reimbursed: { label: "Reembolsado", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" },
  };

  return (
    <WorkspaceLayout sidebarTitle="Gastos" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push("/plataforma/contabilidad")} className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]">
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">Gastos</h1>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">Reportes · Recibos · Aprobaciones · Reembolsos</p>
              </div>
            </div>
            <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold shadow-sm hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
              <Plus size={12} /> Nuevo Reporte
            </button>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar reportes..." className="pl-9 pr-4 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[12px] w-full focus:ring-2 focus:ring-blue-500/20" />
          </div>

          {showCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Nuevo Reporte de Gastos</h3>
              <input type="text" placeholder="Descripción general" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <div className="space-y-2">
                {form.items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-1 md:grid-cols-5 gap-2">
                    <input type="date" value={item.expense_date} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, expense_date: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="text" placeholder="Categoría" value={item.category} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, category: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="text" placeholder="Descripción" value={item.description} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, description: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="number" min={0} placeholder="Monto" value={item.amount} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, amount: Number(e.target.value) } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <button onClick={() => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) })} className="p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg"><Trash2 size={14} /></button>
                  </div>
                ))}
                <button onClick={() => setForm({ ...form, items: [...form.items, { expense_date: "", category: "", description: "", amount: 0, vendor: "" }] })} className="text-[11px] font-semibold text-[hsl(var(--primary))] hover:underline">+ Agregar línea</button>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-semibold">Crear Reporte</button>
              </div>
            </motion.div>
          )}

          <div className="space-y-2">
            {loading ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
            ) : filtered.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin reportes de gastos.</p>
            ) : (
              filtered.map((report) => {
                const st = statusConfig[report.status] || statusConfig.draft;
                return (
                  <motion.div key={report.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide", st.color)}>{st.label}</span>
                        <p className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white">{report.report_number}</p>
                      </div>
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{fmtCOP(Number(report.total_amount))}</p>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] mb-2">{report.description || "Sin descripción"}</p>
                    <div className="flex flex-wrap gap-1">
                      {report.status === "draft" && (
                        <button onClick={() => handleAction(report.id, "submit")} className="px-2 py-1 rounded-md bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 text-[9px] font-bold uppercase tracking-wide flex items-center gap-1"><Send size={10} /> Enviar</button>
                      )}
                      {report.status === "submitted" && (
                        <>
                          <button onClick={() => handleAction(report.id, "approve")} className="px-2 py-1 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 text-[9px] font-bold uppercase tracking-wide flex items-center gap-1"><Check size={10} /> Aprobar</button>
                          <button onClick={() => handleAction(report.id, "reject")} className="px-2 py-1 rounded-md bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-400 text-[9px] font-bold uppercase tracking-wide flex items-center gap-1"><XCircle size={10} /> Rechazar</button>
                        </>
                      )}
                      {report.status === "approved" && (
                        <button onClick={() => handleAction(report.id, "reimburse")} className="px-2 py-1 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-[9px] font-bold uppercase tracking-wide flex items-center gap-1"><DollarSign size={10} /> Reembolsar</button>
                      )}
                    </div>
                    {report.items?.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-[hsl(var(--border))] dark:border-white/5 space-y-1">
                        {report.items.map((item: ExpenseReportItem) => (
                          <div key={item.id} className="flex items-center justify-between text-[11px]">
                            <span className="text-[hsl(var(--text-secondary))]">{item.description}</span>
                            <span className="font-semibold text-[hsl(var(--text-primary))] dark:text-white">{fmtCOP(Number(item.amount))}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </motion.div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
