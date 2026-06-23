"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Bell, Check, CheckCheck } from "lucide-react";

interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  entity_type: string | null;
  entity_slug: string | null;
  is_read: boolean;
  action_url: string | null;
  created_at: string;
}

export default function NotificationsPage() {
  const { user } = useAuth();
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [totalUnread, setTotalUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const load = async () => {
    setLoading(true);
    try {
      const params = filter === "unread" ? "?unread_only=true" : "";
      const data = await apiFetch<{ items: Notification[]; total_unread: number }>(`/cms/v2/notifications${params}`, { silent: true });
      setNotifs(data?.items || []);
      setTotalUnread(data?.total_unread || 0);
    } catch { setNotifs([]); }
    setLoading(false);
  };

  useEffect(() => { load(); }, [filter]);

  const markRead = async (id: string) => {
    await apiFetch(`/cms/v2/notifications/${id}/read`, { method: "POST", silent: true });
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    setTotalUnread(prev => Math.max(0, prev - 1));
  };

  const markAllRead = async () => {
    await apiFetch("/cms/v2/notifications/read-all", { method: "POST", silent: true });
    setNotifs(prev => prev.map(n => ({ ...n, is_read: true })));
    setTotalUnread(0);
  };

  const typeColors: Record<string, string> = {
    mention: "bg-blue-100 text-blue-700",
    approval_requested: "bg-amber-100 text-amber-700",
    approval_granted: "bg-green-100 text-green-700",
    approval_rejected: "bg-red-100 text-red-700",
    page_published: "bg-blue-100 text-blue-700",
    page_archived: "bg-slate-100 text-slate-600",
    comment_added: "bg-cyan-100 text-cyan-700",
    workflow_changed: "bg-blue-100 text-blue-800",
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Notificaciones</h1>
            <p className="text-sm text-slate-500">{totalUnread} sin leer</p>
          </div>
        </div>
        {totalUnread > 0 && (
          <button onClick={markAllRead} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border hover:bg-slate-50">
            <CheckCheck size={14} /> Marcar todo como leido
          </button>
        )}
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter("all")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "all" ? "bg-[hsl(var(--primary))] text-white" : "border hover:bg-slate-50"}`}>Todas</button>
        <button onClick={() => setFilter("unread")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "unread" ? "bg-[hsl(var(--primary))] text-white" : "border hover:bg-slate-50"}`}>Sin leer ({totalUnread})</button>
      </div>

      <div className="space-y-2">
        {loading ? (
          <div className="py-12 text-center text-slate-400">Cargando...</div>
        ) : notifs.length === 0 ? (
          <div className="py-12 text-center text-slate-400">Sin notificaciones</div>
        ) : notifs.map(n => (
          <div key={n.id} className={`flex items-start gap-4 p-4 rounded-xl border transition-colors ${!n.is_read ? "bg-blue-50/50 border-blue-200" : "bg-white"}`}>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${typeColors[n.type] || "bg-slate-100"}`}>{n.type}</span>
                {!n.is_read && <span className="w-2 h-2 rounded-full bg-blue-500" />}
              </div>
              <p className="text-sm font-medium">{n.title}</p>
              {n.body && <p className="text-xs text-slate-500 mt-1">{n.body}</p>}
              <p className="text-[10px] text-slate-400 mt-2">{new Date(n.created_at).toLocaleString("es")}</p>
            </div>
            <div className="flex gap-1 shrink-0">
              {!n.is_read && (
                <button onClick={() => markRead(n.id)} className="p-1.5 rounded-lg hover:bg-slate-100" title="Marcar leido">
                  <Check size={14} className="text-slate-400" />
                </button>
              )}
              {n.action_url && (
                <a href={n.action_url} className="p-1.5 rounded-lg hover:bg-slate-100 text-xs text-[hsl(var(--primary))] font-medium">Ver</a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
