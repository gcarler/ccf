"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { Shield, Monitor, Smartphone, Trash2 } from "lucide-react";
import SidePanel from "@/components/ui/SidePanel";

interface Session { id: string; browser: string | null; os: string | null; is_mobile: boolean; ip_address: string | null; last_activity_at: string; created_at: string; }

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingAction, setPendingAction] = useState<{ type: "one"; id: string } | { type: "all" } | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<Session[]>("/cms/v2/sessions", { silent: true });
      setSessions(Array.isArray(data) ? data : []);
    } catch { setSessions([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const revoke = async (id: string) => {
    await apiFetch(`/cms/v2/sessions/${id}/revoke`, { method: "POST", silent: true });
    setPendingAction(null);
    load();
  };

  const revokeAll = async () => {
    await apiFetch("/cms/v2/sessions/revoke-all", { method: "POST", silent: true });
    setPendingAction(null);
    load();
  };

  const confirmPendingAction = () => {
    if (!pendingAction) return;
    if (pendingAction.type === "all") {
      revokeAll();
      return;
    }
    revoke(pendingAction.id);
  };

  const parseUA = (ua: string | null) => {
    if (!ua) return { browser: "Desconocido", os: "Desconocido" };
    const browser = ua.includes("Chrome") ? "Chrome" : ua.includes("Firefox") ? "Firefox" : ua.includes("Safari") ? "Safari" : ua.split(" ")[0];
    const os = ua.includes("Windows") ? "Windows" : ua.includes("Mac") ? "macOS" : ua.includes("Linux") ? "Linux" : ua.includes("Android") ? "Android" : ua.includes("iPhone") ? "iOS" : "Otro";
    return { browser, os };
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Sesiones Activas</h1>
            <p className="text-sm text-slate-500">{sessions.length} sesiones activas</p>
          </div>
        </div>
        {sessions.length > 1 && (
          <button onClick={() => setPendingAction({ type: "all" })} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border border-red-200 text-red-600 hover:bg-red-50">
            <Trash2 size={14} /> Revocar todas
          </button>
        )}
      </div>

      <div className="space-y-3">
        {loading ? <div className="py-12 text-center text-slate-400">Cargando...</div> : sessions.length === 0 ? (
          <div className="py-12 text-center text-slate-400">Sin sesiones</div>
        ) : sessions.map(s => {
          const ua = parseUA(s.browser || s.os);
          return (
            <div key={s.id} className="flex items-center gap-4 p-4 border rounded-xl bg-white">
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                {s.is_mobile ? <Smartphone size={18} className="text-slate-500" /> : <Monitor size={18} className="text-slate-500" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{ua.browser} en {ua.os}</p>
                <p className="text-xs text-slate-400">IP: {s.ip_address || "N/A"}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-slate-500">Activa: {new Date(s.last_activity_at).toLocaleString("es")}</p>
                <p className="text-[10px] text-slate-400">Inicio: {new Date(s.created_at).toLocaleString("es")}</p>
              </div>
              <button onClick={() => setPendingAction({ type: "one", id: s.id })} className="p-2 rounded-lg hover:bg-red-50 shrink-0" title="Revocar">
                <Trash2 size={14} className="text-red-400" />
              </button>
            </div>
          );
        })}
      </div>
      <SidePanel
        isOpen={!!pendingAction}
        onClose={() => setPendingAction(null)}
        title="Revocar sesion"
        subtitle={pendingAction?.type === "all" ? "Todas excepto la actual" : "Sesion seleccionada"}
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">Esta accion cerrara el acceso de la sesion indicada.</p>
          <div className="flex gap-2">
            <button onClick={() => setPendingAction(null)} className="flex-1 rounded-lg border px-3 py-2 text-sm font-medium">Cancelar</button>
            <button onClick={confirmPendingAction} className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white hover:bg-red-700">Revocar</button>
          </div>
        </div>
      </SidePanel>
    </div>
  );
}
