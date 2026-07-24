"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { Bell, Check, CheckCheck } from "lucide-react";
import { toast } from "sonner";

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
  const { user: _user } = useAuth();
  const [notifs, setNotifs] = useState<Notification[]>([]);
  const [totalUnread, setTotalUnread] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = filter === "unread" ? "?unread_only=true" : "";
      const data = await apiFetch<{ items: Notification[]; total_unread: number }>(`/cms/v2/notifications${params}`, { silent: true });
      setNotifs(data?.items || []);
      setTotalUnread(data?.total_unread || 0);
    } catch { toast.error("Error al cargar datos"); setNotifs([]); }
    setLoading(false);
  }, [filter]);

  useEffect(() => { load(); }, [filter, load]);

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
    mention: "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]",
    approval_requested: "bg-[hsl(var(--warning-muted))] text-warning-text",
    approval_granted: "bg-green-100 text-[hsl(var(--secondary))]",
    approval_rejected: "bg-red-100 text-[hsl(var(--destructive))]",
    page_published: "bg-[hsl(var(--info-muted))] text-[hsl(var(--primary))]",
    page_archived: "bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]",
    comment_added: "bg-[hsl(var(--domain-cyan)/20%)] text-[hsl(var(--domain-cyan)/90%)]",
    workflow_changed: "bg-[hsl(var(--info-muted))] text-info-text",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bell size={24} className="text-[hsl(var(--primary))]" />
          <div>
            <h1 className="text-xl font-bold">Notificaciones</h1>
            <p className="text-sm text-[hsl(var(--text-secondary))]">{totalUnread} sin leer</p>
          </div>
        </div>
        {totalUnread > 0 && (
          <button onClick={markAllRead} className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg border hover:bg-[hsl(var(--surface-1))]">
            <CheckCheck size={14} /> Marcar todo como leido
          </button>
        )}
      </div>

      <div className="flex gap-2">
        <button onClick={() => setFilter("all")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "all" ? "bg-[hsl(var(--primary))] text-white" : "border hover:bg-[hsl(var(--surface-1))]"}`}>Todas</button>
        <button onClick={() => setFilter("unread")} className={`px-4 py-2 text-sm font-medium rounded-lg ${filter === "unread" ? "bg-[hsl(var(--primary))] text-white" : "border hover:bg-[hsl(var(--surface-1))]"}`}>Sin leer ({totalUnread})</button>
      </div>

      <div className="space-y-2">
        {loading ? (
          <div className="py-12 text-center text-[hsl(var(--text-secondary))]">Cargando...</div>
        ) : notifs.length === 0 ? (
          <div className="py-12 text-center text-[hsl(var(--text-secondary))]">Sin notificaciones</div>
        ) : notifs.map(n => (
          <div key={n.id} className={`flex items-start gap-4 p-4 rounded-xl border transition-colors ${!n.is_read ? "bg-info-soft/50 border-[hsl(var(--info)/25%)]" : "bg-[hsl(var(--bg-primary))]"}`}>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${typeColors[n.type] || "bg-[hsl(var(--surface-2))]"}`}>{n.type}</span>
                {!n.is_read && <span className="w-2 h-2 rounded-full bg-[hsl(var(--primary))]" />}
              </div>
              <p className="text-sm font-medium">{n.title}</p>
              {n.body && <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{n.body}</p>}
              <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-2">{new Date(n.created_at).toLocaleString("es")}</p>
            </div>
            <div className="flex gap-1 shrink-0">
              {!n.is_read && (
                <button onClick={() => markRead(n.id)} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))]" title="Marcar leido">
                  <Check size={14} className="text-[hsl(var(--text-secondary))]" />
                </button>
              )}
              {n.action_url && (
                <a href={n.action_url} className="p-1.5 rounded-lg hover:bg-[hsl(var(--surface-2))] text-xs text-[hsl(var(--primary))] font-medium">Ver</a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
