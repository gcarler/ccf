"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Calculator,
  FileText,
  Landmark as Building2,
  Receipt,
  PenTool,
  Wallet,
}from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";

interface MetricCard {
  label: string;
  value: string;
  icon: React.ElementType;
  color: string;
}

const SECTIONS = [
  {
    title: "Módulos",
    items: [
      { id: "contabilidad", label: "Contabilidad", href: "/plataforma/contabilidad", icon: Calculator },
      { id: "facturacion", label: "Facturación", href: "/plataforma/facturacion", icon: Receipt },
      { id: "gastos", label: "Gastos", href: "/plataforma/gastos", icon: Wallet },
      { id: "documentos", label: "Documentos", href: "/plataforma/documentos", icon: FileText },
      { id: "firma", label: "Firma Digital", href: "/plataforma/firma", icon: PenTool },
    ],
  },
];

function fmtCOP(n: number) {
  return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(n);
}

export default function ContabilidadPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [bankAccounts, setBankAccounts] = useState<any[]>([]);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [expenseReports, setExpenseReports] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [signRequests, setSignRequests] = useState<any[]>([]);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    Promise.all([
      apiFetch<any[]>("/finance-suite/bank-accounts", { token, cache: "no-store" }),
      apiFetch<any[]>("/finance-suite/bank-transactions?limit=5", { token, cache: "no-store" }),
      apiFetch<any[]>("/finance-suite/invoices?limit=5", { token, cache: "no-store" }),
      apiFetch<any[]>("/finance-suite/expense-reports?limit=5", { token, cache: "no-store" }),
      apiFetch<any[]>("/finance-suite/documents?limit=5", { token, cache: "no-store" }),
      apiFetch<any[]>("/finance-suite/sign-requests?limit=5", { token, cache: "no-store" }),
    ]).then(([ba, tx, inv, exp, doc, sign]) => {
      if (Array.isArray(ba)) setBankAccounts(ba);
      if (Array.isArray(tx)) setTransactions(tx);
      if (Array.isArray(inv)) setInvoices(inv);
      if (Array.isArray(exp)) setExpenseReports(exp);
      if (Array.isArray(doc)) setDocuments(doc);
      if (Array.isArray(sign)) setSignRequests(sign);
    }).catch(console.error).finally(() => setLoading(false));
  }, [token]);

  const totalBalance = useMemo(() => bankAccounts.reduce((s, a) => s + (Number(a.current_balance) || 0), 0), [bankAccounts]);
  const pendingInvoices = useMemo(() => invoices.filter((i) => i.status === "draft" || i.status === "sent").length, [invoices]);
  const pendingExpenses = useMemo(() => expenseReports.filter((e) => e.status === "submitted").length, [expenseReports]);
  const pendingSign = useMemo(() => signRequests.filter((s) => s.status === "sent").length, [signRequests]);

  const metrics: MetricCard[] = [
    { label: "Saldo Bancario", value: fmtCOP(totalBalance), icon: Building2, color: "text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20" },
    { label: "Facturas Pendientes", value: String(pendingInvoices), icon: Receipt, color: "text-amber-600 bg-amber-50 dark:bg-amber-900/20" },
    { label: "Gastos por Aprobar", value: String(pendingExpenses), icon: Wallet, color: "text-rose-600 bg-rose-50 dark:bg-rose-900/20" },
    { label: "Firmas Pendientes", value: String(pendingSign), icon: PenTool, color: "text-blue-600 bg-blue-50 dark:bg-blue-900/20" },
  ];

  const modules = [
    {
      title: "Contabilidad",
      description: "Conciliación bancaria, estados financieros y localización fiscal.",
      icon: Calculator,
      href: "/plataforma/contabilidad",
      stats: `${bankAccounts.length} cuentas`,
      color: "from-emerald-500 to-teal-600",
    },
    {
      title: "Facturación",
      description: "Facturas electrónicas, órdenes de venta y registro de pagos.",
      icon: Receipt,
      href: "/plataforma/facturacion",
      stats: `${invoices.length} facturas`,
      color: "from-blue-500 to-blue-700",
    },
    {
      title: "Gastos",
      description: "Reportes de gastos, recibos por foto y reembolsos.",
      icon: Wallet,
      href: "/plataforma/gastos",
      stats: `${expenseReports.length} reportes`,
      color: "from-amber-500 to-orange-600",
    },
    {
      title: "Documentos",
      description: "Archivo centralizado con etiquetas inteligentes.",
      icon: FileText,
      href: "/plataforma/documentos",
      stats: `${documents.length} documentos`,
      color: "from-fuchsia-500 to-pink-600",
    },
    {
      title: "Firma Digital",
      description: "Contratos y documentos con validez legal internacional.",
      icon: PenTool,
      href: "/plataforma/firma",
      stats: `${signRequests.length} solicitudes`,
      color: "from-rose-500 to-pink-600",
    },
  ];

  return (
    <WorkspaceLayout sidebarTitle="Finanzas Pro" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">
                Suite Financiera
              </h1>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">
                Contabilidad · Facturación · Gastos · Documentos · Firma
              </p>
            </div>
          </div>

          {/* Metrics */}
          <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
            {metrics.map((m, idx) => {
              const Icon = m.icon;
              return (
                <motion.div
                  key={m.label}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 shadow-sm"
                >
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{m.label}</p>
                    <div className={clsx("size-8 rounded-lg flex items-center justify-center", m.color)}>
                      <Icon size={16} />
                    </div>
                  </div>
                  <p className="text-xl font-bold text-[hsl(var(--text-primary))] dark:text-white">{loading ? "..." : m.value}</p>
                </motion.div>
              );
            })}
          </section>

          {/* Modules Grid */}
          <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {modules.map((mod, idx) => {
              const Icon = mod.icon;
              return (
                <motion.button
                  key={mod.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 + idx * 0.06 }}
                  onClick={() => router.push(mod.href)}
                  className="group text-left bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 shadow-sm hover:shadow-xl hover:border-blue-500/30 transition-all duration-200"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className={clsx("size-10 rounded-xl bg-gradient-to-br flex items-center justify-center text-white shadow-lg", mod.color)}>
                      <Icon size={20} />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5 px-2 py-1 rounded-full">
                      {mod.stats}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white mb-1">{mod.title}</h3>
                  <p className="text-[11px] text-[hsl(var(--text-secondary))] leading-relaxed">{mod.description}</p>
                </motion.button>
              );
            })}
          </section>

          {/* Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 shadow-sm">
              <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Transacciones Recientes</h3>
              <div className="space-y-2">
                {loading ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
                ) : transactions.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">Sin transacciones.</p>
                ) : (
                  transactions.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))] dark:border-white/5 last:border-0">
                      <div>
                        <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">{tx.description}</p>
                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{tx.reference || "Sin referencia"}</p>
                      </div>
                      <span className={clsx("text-sm font-bold", tx.transaction_type === "credit" ? "text-emerald-600" : "text-rose-500")}>
                        {tx.transaction_type === "credit" ? "+" : "-"}{fmtCOP(Number(tx.amount))}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 shadow-sm">
              <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Facturas Recientes</h3>
              <div className="space-y-2">
                {loading ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
                ) : invoices.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">Sin facturas.</p>
                ) : (
                  invoices.map((inv) => (
                    <div key={inv.id} className="flex items-center justify-between py-2 border-b border-[hsl(var(--border))] dark:border-white/5 last:border-0">
                      <div>
                        <p className="text-[12px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">{inv.invoice_number}</p>
                        <p className="text-[10px] text-[hsl(var(--text-secondary))]">{inv.customer_name}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">{fmtCOP(Number(inv.total))}</p>
                        <span className={clsx(
                          "text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full",
                          inv.status === "paid" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" :
                          inv.status === "overdue" ? "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" :
                          "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
                        )}>{inv.status}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
