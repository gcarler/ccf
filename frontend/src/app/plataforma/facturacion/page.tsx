"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  CheckCircle,
  DollarSign,
  FileText,
  Landmark,
  Plus,
  Search,
  Send,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";
import { toast } from "sonner";

interface InvoiceItem {
  description: string;
  quantity: number;
  unit_price: number;
}

interface Invoice {
  id: string;
  invoice_number: string;
  customer_name: string;
  total: number;
  status: string;
  issue_date: string;
  electronic_status: string;
}

interface SalesOrder {
  id: string;
  order_number: string;
  customer_name: string;
  total_amount: number;
  status: string;
  order_date: string;
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

export default function FacturacionPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"orders" | "invoices">("invoices");
  const [orders, setOrders] = useState<SalesOrder[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [showPayment, setShowPayment] = useState<string | null>(null);
  const [form, setForm] = useState({ customer_name: "", customer_email: "", customer_tax_id: "", issue_date: "", due_date: "", items: [{ description: "", quantity: 1, unit_price: 0 }] as InvoiceItem[] });
  const [paymentForm, setPaymentForm] = useState({ amount: 0, payment_date: "", payment_method: "transfer", reference: "" });

  useEffect(() => {
    const ctrl = new AbortController();
    if (!token) { setLoading(false); return; }
    setLoading(true);
    Promise.all([
      apiFetch<SalesOrder[]>("/finance-suite/sales-orders?limit=50", { token, cache: "no-store", signal: ctrl.signal }),
      apiFetch<Invoice[]>("/finance-suite/invoices?limit=50", { token, cache: "no-store", signal: ctrl.signal }),
    ]).then(([o, i]) => {
      if (Array.isArray(o)) setOrders(o);
      if (Array.isArray(i)) setInvoices(i);
    }).catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
    .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [token]);

  const filtered = tab === "invoices"
    ? invoices.filter((i) => i.invoice_number?.toLowerCase().includes(search.toLowerCase()) || i.customer_name?.toLowerCase().includes(search.toLowerCase()))
    : orders.filter((o) => o.order_number?.toLowerCase().includes(search.toLowerCase()) || o.customer_name?.toLowerCase().includes(search.toLowerCase()));

  const handleCreateInvoice = async () => {
    if (!token) return;
    const payload = {
      customer_name: form.customer_name,
      customer_email: form.customer_email || null,
      customer_tax_id: form.customer_tax_id || null,
      issue_date: form.issue_date,
      due_date: form.due_date || null,
      items: form.items.filter((it) => it.description && it.unit_price > 0),
    };
    try {
      await apiFetch("/finance-suite/invoices", { token, method: "POST", body: payload });
      setShowCreate(false);
      setForm({ customer_name: "", customer_email: "", customer_tax_id: "", issue_date: "", due_date: "", items: [{ description: "", quantity: 1, unit_price: 0 }] });
      toast.success("Factura creada");
      fetchData();
    } catch (e) { console.error(e); toast.error("Error al crear factura"); }
  };

  const handlePayment = async (invoiceId: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/invoices/${invoiceId}/payments`, {
        token, method: "POST", body: { ...paymentForm, amount: Number(paymentForm.amount) },
      });
      setShowPayment(null);
      setPaymentForm({ amount: 0, payment_date: "", payment_method: "transfer", reference: "" });
      toast.success("Pago registrado");
      fetchData();
    } catch (e) { console.error(e); toast.error("Error al registrar pago"); }
  };

  const handleSendElectronic = async (id: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/invoices/${id}/send-electronic`, { token, method: "POST" });
      toast.success("Factura enviada");
      fetchData();
    } catch (e) { console.error(e); toast.error("Error al enviar factura electrónica"); }
  };

  const fetchData = async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const [o, i] = await Promise.all([
        apiFetch<SalesOrder[]>("/finance-suite/sales-orders?limit=50", { token, cache: "no-store" }),
        apiFetch<Invoice[]>("/finance-suite/invoices?limit=50", { token, cache: "no-store" }),
      ]);
      if (Array.isArray(o)) setOrders(o);
      if (Array.isArray(i)) setInvoices(i);
    } catch (e) { console.error(e); toast.error("Error al cargar datos"); }
    setLoading(false);
  };

  return (
    <WorkspaceLayout sidebarTitle="Facturación" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push("/plataforma/contabilidad")} className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]">
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">Facturación</h1>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">Órdenes de venta · Facturas electrónicas · Pagos</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg overflow-hidden border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-bold">
                {(["invoices", "orders"] as const).map((t) => (
                  <button key={t} onClick={() => setTab(t)} className={clsx("px-3 py-1.5 transition-colors", tab === t ? "bg-[hsl(var(--primary))] text-white" : "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]")}>
                    {t === "invoices" ? "Facturas" : "Órdenes"}
                  </button>
                ))}
              </div>
              <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold shadow-sm hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                <Plus size={12} /> Nueva {tab === "invoices" ? "Factura" : "Orden"}
              </button>
            </div>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={`Buscar ${tab}...`} className="pl-9 pr-4 py-1.5 bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg text-[12px] w-full focus:ring-2 focus:ring-blue-500/20" />
          </div>

          {showCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Nueva Factura</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input type="text" placeholder="Cliente" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <input type="email" placeholder="Email" value={form.customer_email} onChange={(e) => setForm({ ...form, customer_email: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <input type="text" placeholder="NIT / Tax ID" value={form.customer_tax_id} onChange={(e) => setForm({ ...form, customer_tax_id: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input type="date" value={form.issue_date} onChange={(e) => setForm({ ...form, issue_date: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <input type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              </div>
              <div className="space-y-2">
                {form.items.map((item, idx) => (
                  <div key={idx} className="grid grid-cols-1 md:grid-cols-4 gap-2">
                    <input type="text" placeholder="Descripción" value={item.description} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, description: e.target.value } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="number" min={0} placeholder="Cantidad" value={item.quantity} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, quantity: Number(e.target.value) } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="number" min={0} placeholder="Precio unitario" value={item.unit_price} onChange={(e) => { const items = form.items.map((it, i) => i === idx ? { ...it, unit_price: Number(e.target.value) } : it); setForm({ ...form, items }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <button onClick={() => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) })} className="p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg"><Trash2 size={14} /></button>
                  </div>
                ))}
                <button onClick={() => setForm({ ...form, items: [...form.items, { description: "", quantity: 1, unit_price: 0 }] })} className="text-[11px] font-semibold text-[hsl(var(--primary))] hover:underline">+ Agregar línea</button>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                <button onClick={handleCreateInvoice} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-semibold">Crear Factura</button>
              </div>
            </motion.div>
          )}

          <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 shadow-sm overflow-hidden">
            <div className="px-3 py-2 border-b border-[hsl(var(--border))] dark:border-white/5 grid grid-cols-12 gap-2 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              <div className="col-span-3">{tab === "invoices" ? "Factura" : "Orden"}</div>
              <div className="col-span-3">Cliente</div>
              <div className="col-span-2">Total</div>
              <div className="col-span-2">Estado</div>
              <div className="col-span-2 text-right">Acciones</div>
            </div>
            {loading ? (
              <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">Cargando...</div>
            ) : filtered.length === 0 ? (
              <div className="p-4 text-sm text-[hsl(var(--text-secondary))]">Sin registros.</div>
            ) : (
              filtered.map((item) => {
                const isInvoice = tab === "invoices";
                const number = isInvoice ? (item as Invoice).invoice_number : (item as SalesOrder).order_number;
                const total = isInvoice ? (item as Invoice).total : (item as SalesOrder).total_amount;
                const itemStatus = item.status;
                return (
                  <div key={item.id} className="px-3 py-2 border-b border-[hsl(var(--border))] dark:border-white/5 grid grid-cols-12 gap-2 items-center hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/[0.02] transition-colors">
                    <div className="col-span-3">
                      <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">{number}</p>
                      <p className="text-[10px] text-[hsl(var(--text-secondary))]">{isInvoice ? (item as Invoice).issue_date : (item as SalesOrder).order_date}</p>
                    </div>
                    <div className="col-span-3 text-[12px] text-[hsl(var(--text-secondary))] truncate">{item.customer_name}</div>
                    <div className="col-span-2 text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white">{fmtCOP(Number(total))}</div>
                    <div className="col-span-2">
                      <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide",
                        itemStatus === "paid" || itemStatus === "completed" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" :
                        itemStatus === "overdue" || itemStatus === "cancelled" ? "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" :
                        "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
                      )}>{itemStatus}</span>
                    </div>
                    <div className="col-span-2 flex justify-end gap-1">
                      {isInvoice && itemStatus !== "paid" && (
                        <button onClick={() => setShowPayment(item.id)} className="p-1.5 rounded-md bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 hover:bg-emerald-100" title="Registrar pago"><DollarSign size={12} /></button>
                      )}
                      {isInvoice && (item as Invoice).electronic_status === "not_sent" && (
                        <button onClick={() => handleSendElectronic(item.id)} className="p-1.5 rounded-md bg-blue-50 dark:bg-blue-900/20 text-blue-600 hover:bg-blue-100" title="Enviar electrónica"><Send size={12} /></button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {showPayment && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
              <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1b1e] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 w-full max-w-md space-y-3">
                <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Registrar Pago</h3>
                <input type="number" placeholder="Monto" value={paymentForm.amount} onChange={(e) => setPaymentForm({ ...paymentForm, amount: Number(e.target.value) })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <input type="date" value={paymentForm.payment_date} onChange={(e) => setPaymentForm({ ...paymentForm, payment_date: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <select value={paymentForm.payment_method} onChange={(e) => setPaymentForm({ ...paymentForm, payment_method: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                  <option value="transfer">Transferencia</option>
                  <option value="cash">Efectivo</option>
                  <option value="card">Tarjeta</option>
                  <option value="check">Cheque</option>
                </select>
                <input type="text" placeholder="Referencia" value={paymentForm.reference} onChange={(e) => setPaymentForm({ ...paymentForm, reference: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                <div className="flex gap-2">
                  <button onClick={() => setShowPayment(null)} className="flex-1 px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                  <button onClick={() => handlePayment(showPayment)} className="flex-1 px-4 py-2 rounded-lg bg-emerald-500 text-white text-[11px] font-semibold">Guardar Pago</button>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </WorkspaceLayout>
  );
}
