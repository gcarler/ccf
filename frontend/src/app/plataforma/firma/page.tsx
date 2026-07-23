"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  FileText,
  Landmark,
  PenTool,
  Plus,
  Send,
  Trash2,
  User,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import clsx from "clsx";

const SECTIONS = [
  {
    title: "Módulos",
    items: [
      { id: "contabilidad", label: "Contabilidad", href: "/plataforma/contabilidad", icon: Landmark },
      { id: "facturacion", label: "Facturación", href: "/plataforma/facturacion", icon: FileText },
      { id: "gastos", label: "Gastos", href: "/plataforma/gastos", icon: Plus },
      { id: "documentos", label: "Documentos", href: "/plataforma/documentos", icon: FileText },
      { id: "firma", label: "Firma Digital", href: "/plataforma/firma", icon: PenTool },
    ],
  },
];

export default function FirmaPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({
    title: "",
    description: "",
    document_url: "",
    expiry_date: "",
    country_code: "CO",
    legal_framework: "eidas",
    signers: [{ email: "", full_name: "", role: "signer", signing_order: 0 }],
  });

  const fetchData = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    setLoading(true);
    try {
      const r = await apiFetch<any[]>("/finance-suite/sign-requests?limit=50", { token, cache: "no-store" });
      if (Array.isArray(r)) setRequests(r);
    } catch (e) { console.error(e); }
    setLoading(false);
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async () => {
    if (!token) return;
    const payload = {
      ...form,
      expiry_date: form.expiry_date ? new Date(form.expiry_date).toISOString() : null,
      signers: form.signers.filter((s) => s.email && s.full_name),
    };
    try {
      await apiFetch("/finance-suite/sign-requests", { token, method: "POST", body: payload });
      setShowCreate(false);
      setForm({ title: "", description: "", document_url: "", expiry_date: "", country_code: "CO", legal_framework: "eidas", signers: [{ email: "", full_name: "", role: "signer", signing_order: 0 }] });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleSend = async (id: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/sign-requests/${id}/send`, { token, method: "POST" });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const handleSign = async (requestId: string, signerId: string) => {
    if (!token) return;
    try {
      await apiFetch(`/finance-suite/sign-requests/${requestId}/signers/${signerId}/sign`, {
        token, method: "POST", body: { action: "sign", ip_address: "127.0.0.1" },
      });
      fetchData();
    } catch (e) { console.error(e); }
  };

  const statusConfig: Record<string, { label: string; color: string }> = {
    draft: { label: "Borrador", color: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/5 dark:text-[hsl(var(--text-secondary))]" },
    sent: { label: "Enviado", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" },
    completed: { label: "Completado", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" },
    expired: { label: "Expirado", color: "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" },
    cancelled: { label: "Cancelado", color: "bg-gray-100 text-gray-600 dark:bg-gray-900/10 dark:text-gray-400" },
  };

  return (
    <WorkspaceLayout sidebarTitle="Firma Digital" sidebarSections={SECTIONS}>
      <div className="h-full overflow-y-auto bg-[#f8fafc] dark:bg-[#1E1F21] font-display scrollbar-thin">
        <div className="w-full px-4 py-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => router.push("/plataforma/contabilidad")} className="p-1.5 rounded-md hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 text-[hsl(var(--text-secondary))]">
                <ArrowLeft size={16} />
              </button>
              <div>
                <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white tracking-tight uppercase">Firma Digital</h1>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] mt-0.5">Contratos · Firmas · Validez legal internacional</p>
              </div>
            </div>
            <button onClick={() => setShowCreate(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[hsl(var(--primary))] text-white rounded-md text-[10px] font-semibold shadow-sm hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
              <Plus size={12} /> Nueva Solicitud
            </button>
          </div>

          {showCreate && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 space-y-3">
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] dark:text-white">Nueva Solicitud de Firma</h3>
              <input type="text" placeholder="Título del documento" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="text" placeholder="Descripción" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="text" placeholder="URL del documento" value={form.document_url} onChange={(e) => setForm({ ...form, document_url: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <input type="datetime-local" value={form.expiry_date} onChange={(e) => setForm({ ...form, expiry_date: e.target.value })} className="w-full px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
              <div className="grid grid-cols-2 gap-2">
                <select value={form.country_code} onChange={(e) => setForm({ ...form, country_code: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                  <option value="CO">Colombia</option>
                  <option value="MX">México</option>
                  <option value="US">Estados Unidos</option>
                  <option value="CL">Chile</option>
                  <option value="PE">Perú</option>
                </select>
                <select value={form.legal_framework} onChange={(e) => setForm({ ...form, legal_framework: e.target.value })} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                  <option value="eidas">eIDAS (UE)</option>
                  <option value="ueta">UETA (USA)</option>
                  <option value="simple">Firma Simple</option>
                </select>
              </div>
              <div className="space-y-2">
                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Firmantes</p>
                {form.signers.map((signer, idx) => (
                  <div key={idx} className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    <input type="text" placeholder="Nombre completo" value={signer.full_name} onChange={(e) => { const s = [...form.signers]; s[idx].full_name = e.target.value; setForm({ ...form, signers: s }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <input type="email" placeholder="Email" value={signer.email} onChange={(e) => { const s = [...form.signers]; s[idx].email = e.target.value; setForm({ ...form, signers: s }); }} className="px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg" />
                    <div className="flex gap-2">
                      <select value={signer.role} onChange={(e) => { const s = [...form.signers]; s[idx].role = e.target.value; setForm({ ...form, signers: s }); }} className="flex-1 px-3 py-2 text-[12px] bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg">
                        <option value="signer">Firmante</option>
                        <option value="witness">Testigo</option>
                        <option value="approver">Aprobador</option>
                      </select>
                      <button onClick={() => setForm({ ...form, signers: form.signers.filter((_, i) => i !== idx) })} className="p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-lg"><Trash2 size={14} /></button>
                    </div>
                  </div>
                ))}
                <button onClick={() => setForm({ ...form, signers: [...form.signers, { email: "", full_name: "", role: "signer", signing_order: form.signers.length }] })} className="text-[11px] font-semibold text-[hsl(var(--primary))] hover:underline">+ Agregar firmante</button>
              </div>
              <div className="flex gap-2">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 text-[11px] font-semibold">Cancelar</button>
                <button onClick={handleCreate} className="px-4 py-2 rounded-lg bg-[hsl(var(--primary))] text-white text-[11px] font-semibold">Crear Solicitud</button>
              </div>
            </motion.div>
          )}

          <div className="space-y-3">
            {loading ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Cargando...</p>
            ) : requests.length === 0 ? (
              <p className="text-sm text-[hsl(var(--text-secondary))]">Sin solicitudes de firma.</p>
            ) : (
              requests.map((req) => {
                const st = statusConfig[req.status] || statusConfig.draft;
                return (
                  <motion.div key={req.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[hsl(var(--bg-primary))] dark:bg-[#111418] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-4 shadow-sm">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[hsl(var(--primary))] flex items-center justify-center"><PenTool size={16} /></div>
                        <div>
                          <p className="text-[12px] font-bold text-[hsl(var(--text-primary))] dark:text-white">{req.title}</p>
                          <p className="text-[10px] text-[hsl(var(--text-secondary))]">{req.country_code} · {req.legal_framework}</p>
                        </div>
                      </div>
                      <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide", st.color)}>{st.label}</span>
                    </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] mb-3">{req.description || "Sin descripción"}</p>
                    <a href={req.document_url} target="_blank" rel="noopener noreferrer" className="text-[10px] font-bold text-[hsl(var(--primary))] hover:underline mb-3 block">Ver documento →</a>

                    <div className="space-y-2">
                      {req.signers?.map((signer: any) => (
                        <div key={signer.id} className="flex items-center justify-between py-2 border-t border-[hsl(var(--border))] dark:border-white/5">
                          <div className="flex items-center gap-2">
                            <User size={14} className="text-[hsl(var(--text-secondary))]" />
                            <div>
                              <p className="text-[11px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">{signer.full_name}</p>
                              <p className="text-[10px] text-[hsl(var(--text-secondary))]">{signer.email} · {signer.role}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={clsx("px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide",
                              signer.status === "signed" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-400" :
                              signer.status === "declined" ? "bg-rose-100 text-rose-600 dark:bg-rose-900/10 dark:text-rose-400" :
                              "bg-amber-100 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400"
                            )}>{signer.status}</span>
                            {req.status === "sent" && signer.status === "pending" && (
                              <button onClick={() => handleSign(req.id, signer.id)} className="px-2 py-1 rounded-md bg-[hsl(var(--primary))] text-white text-[9px] font-bold uppercase tracking-wide flex items-center gap-1"><PenTool size={10} /> Firmar</button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {req.status === "draft" && (
                      <button onClick={() => handleSend(req.id)} className="mt-3 w-full py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 text-[11px] font-bold uppercase tracking-wide flex items-center justify-center gap-2 hover:bg-blue-100 transition-all"><Send size={14} /> Enviar para firmar</button>
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
