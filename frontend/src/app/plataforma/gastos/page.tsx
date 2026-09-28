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
import ConfirmDeleteDrawer from "@/components/ui/ConfirmDeleteDrawer";
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
  const [lineToDelete, setLineToDelete] = useState<number | null>(null);
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
    draft: { label: "Borrador", color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]" },
    submitted: { label: "Enviado", color: "bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]" },
    approved: { label: "Aprobado", color: "bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]" },
    rejected: { label: "Rechazado", color: "bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))]" },
    reimbursed: { label: "Reembolsado", color: "bg-[hsl(var(--info-muted))] text-[hsl(var(--info))]" },
  };

  return (
    <WorkspaceLayout sidebarTitle="Gastos" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[hsl(var(--bg-primary))] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push("/plataforma/contabilidad")} className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))]">
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] tracking-tight uppercase">Gastos</h1>
                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">Reportes · Recibos · Aprobaciones · Reembolsos</p>
              </div>
            </div>
            <button type="button" onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] rounded-md text-2xs font-semibold shadow-sm active:scale-95 transition-all">
              <Plus size={12} /> Nuevo Reporte
            </button>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar reportes..." className="pl-9 pr-4 py-1.5 bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg text-sm w-full text-[hsl(var(--text-primary))] focus:ring-2 focus:ring-[hsl(var(--primary))/0.2]" />
          </div>

          {showCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">Nuevo Reporte de Gastos</h3>
              <input type="text" placeholder="Descripción general" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))]" />
              <div className="space-y-2">
                {form.items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-1 md:grid-cols-5 gap-2">
                    <input type="date" value={item.expense_date} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, expense_date: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))]" />
                    <input type="text" placeholder="Categoría" value={item.category} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, category: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))]" />
                    <input type="text" placeholder="Descripción" value={item.description} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, description: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))]" />
                    <input type="number" min={0} placeholder="Monto" value={item.amount} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, amount: Number(e.target.value) } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-sm bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-lg text-[hsl(var(--text-primary))]" />
                    <button type="button" onClick={() => setLineToDelete(idx)} className="p-2 text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] rounded-lg" title="Eliminar línea"><Trash2 size={14} /></button>
                  </div>
                ))}
                <button type="button" onClick={() => setForm({ ...form, items: [...form.items, { expense_date: "", category: "", description: "", amount: 0, vendor: "" }] })} className="text-xs font-semibold text-[hsl(var(--primary))] hover:underline">+ Agregar línea</button>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] text-xs font-semibold text-[hsl(var(--text-secondary))]">Cancelar</button>
                <button type="button" onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--text-inverse))] text-xs font-semibold">Crear Reporte</button>
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
                  <motion.div key={report.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--surface-1))] rounded-lg border border-[hsl(var(--border))] p-3 shadow-sm">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={clsx("px-2 py-0.5 rounded-full text-2xs font-bold uppercase tracking-wide", st.color)}>{st.label}</span>
                        <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{report.report_number}</p>
                      </div>
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))]">{fmtCOP(Number(report.total_amount))}</p>
                    </div>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mb-2">{report.description || "Sin descripción"}</p>
                    <div className="flex flex-wrap gap-1">
                      {report.status === "draft" && (
                        <button onClick={() => handleAction(report.id, "submit")} className="px-2 py-1 rounded-md bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] text-2xs font-bold uppercase tracking-wide flex items-center gap-1"><Send size={10} /> Enviar</button>
                      )}
                      {report.status === "submitted" && (
                        <>
                          <button onClick={() => handleAction(report.id, "approve")} className="px-2 py-1 rounded-md bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] text-2xs font-bold uppercase tracking-wide flex items-center gap-1"><Check size={10} /> Aprobar</button>
                          <button onClick={() => handleAction(report.id, "reject")} className="px-2 py-1 rounded-md bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))] text-2xs font-bold uppercase tracking-wide flex items-center gap-1"><XCircle size={10} /> Rechazar</button>
                        </>
                      )}
                      {report.status === "approved" && (
                        <button onClick={() => handleAction(report.id, "reimburse")} className="px-2 py-1 rounded-md bg-[hsl(var(--info-muted))] text-[hsl(var(--info))] text-2xs font-bold uppercase tracking-wide flex items-center gap-1"><DollarSign size={10} /> Reembolsar</button>
                      )}
                    </div>
                    {report.items?.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-[hsl(var(--border))] space-y-1">
                        {report.items.map((item: ExpenseReportItem) => (
                          <div key={item.id} className="flex items-center justify-between text-xs">
                            <span className="text-[hsl(var(--text-secondary))]">{item.description}</span>
                            <span className="font-semibold text-[hsl(var(--text-primary))]">{fmtCOP(Number(item.amount))}</span>
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
      <ConfirmDeleteDrawer
        open={lineToDelete !== null}
        onClose={() => setLineToDelete(null)}
        onConfirm={() => {
          if (lineToDelete !== null) {
            setForm(prev => ({ ...prev, items: prev.items.filter((_, i) => i !== lineToDelete) }));
            setLineToDelete(null);
          }
        }}
        title="¿Eliminar línea de gasto?"
        description="Esta línea se eliminará del reporte de gastos actual en preparación."
        confirmLabel="Eliminar línea"
      />
    </WorkspaceLayout>
  );
}
