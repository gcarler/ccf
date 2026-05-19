"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { useNotifications } from "@/hooks/useNotifications";
import {
  Bell,
  CalendarDays,
  CheckCircle2,
  Clock,
  MessageSquare,
  Settings,
  UserCircle,
} from "lucide-react";

type TaskItem = {
  id: number;
  title: string;
  status: string;
  due_date?: string | null;
  project_title?: string;
};

type CalendarItem = {
  id: string;
  title: string;
  start: string;
  type: "task" | "agenda_event" | "evangelism_event" | "reminder";
};

type FaroPendingItem = {
  session_id: number;
  glory_house_id: number;
  glory_house_name?: string | null;
  season_name?: string | null;
  session_date?: string | null;
  status?: string | null;
  attendance_count: number;
  expected_count: number;
  report_deadline?: string | null;
};

export default function MiVistaPage() {
  const { token } = useAuth();
  const { notifications, loading: loadingNotifications } = useNotifications(20);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [calendarItems, setCalendarItems] = useState<CalendarItem[]>([]);
  const [faroPending, setFaroPending] = useState<FaroPendingItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const [taskData, calendarData, faroPendingData] = await Promise.all([
          apiFetch<TaskItem[]>("/projects/tasks", { token, cache: "no-store" }).catch(() => []),
          apiFetch<any[]>("/system/calendar", { token, cache: "no-store" }).catch(() => []),
          apiFetch<FaroPendingItem[]>("/evangelism/faro/sessions/mine/pending", {
            token,
            cache: "no-store",
          }).catch(() => []),
        ]);

        const pendingTasks = (Array.isArray(taskData) ? taskData : [])
          .filter((task) => task.status !== "done")
          .slice(0, 10);
        setTasks(pendingTasks);

        const mappedCalendar = (Array.isArray(calendarData) ? calendarData : []).map((event) => ({
          id: String(event.id),
          title: String(event.title || "Evento"),
          start: String(event.start || new Date().toISOString()),
          type: (event.type || "agenda_event") as CalendarItem["type"],
        }));
        setCalendarItems(mappedCalendar);
        setFaroPending(Array.isArray(faroPendingData) ? faroPendingData : []);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [token]);

  const unreadNotifications = useMemo(
    () => notifications.filter((notification) => !notification.read),
    [notifications]
  );

  const pendingTasksCount = tasks.length;
  const pendingMessagesCount = unreadNotifications.length;

  const mergedUpcoming = useMemo(() => {
    const fromTasks = tasks
      .filter((task) => task.due_date)
      .map((task) => ({
        id: `task-${task.id}`,
        title: task.title,
        start: task.due_date as string,
        source: "task" as const,
      }));

    const fromCalendar = calendarItems.map((event) => ({
      id: `event-${event.id}`,
      title: event.title,
      start: event.start,
      source: "event" as const,
    }));

    return [...fromTasks, ...fromCalendar]
      .filter((item) => new Date(item.start).getTime() >= Date.now() - 24 * 60 * 60 * 1000)
      .sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
      .slice(0, 8);
  }, [calendarItems, tasks]);

  return (
    <WorkspaceLayout
      breadcrumbs={[{ label: "Mi Vista", icon: UserCircle, href: "/mi-vista" }]}
      sidebarTitle="Mi Vista"
    >
      <div className="h-full overflow-y-auto bg-slate-50 dark:bg-[#111213] p-6 lg:p-8">
        <div className="mx-auto max-w-7xl space-y-6">
          <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <StatCard
              icon={CheckCircle2}
              label="Tareas Pendientes"
              value={loading ? "..." : String(pendingTasksCount)}
              href="/tasks"
            />
            <StatCard
              icon={MessageSquare}
              label="Mensajes Pendientes"
              value={loadingNotifications ? "..." : String(pendingMessagesCount)}
              href="/inbox"
            />
            <StatCard icon={CalendarDays} label="Agenda" value={String(mergedUpcoming.length)} href="/calendar" />
          </section>

          <section className="grid grid-cols-1 gap-4">
            <Panel title="Faro en Casa · Reportes Pendientes" actionHref="/evangelism/faro" actionLabel="Ir a Faro">
              <ul className="space-y-2">
                {faroPending.slice(0, 6).map((item) => (
                  <li key={item.session_id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-white/5">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {item.glory_house_name || "Faro en Casa"}
                    </div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {item.session_date ? new Date(item.session_date).toLocaleDateString("es-CO") : "Sin fecha"} ·{" "}
                      {item.attendance_count}/{item.expected_count} asistencia reportada
                    </div>
                  </li>
                ))}
                {!loading && faroPending.length === 0 && (
                  <li className="text-sm text-slate-500 dark:text-slate-400">
                    No tienes reportes de Faro pendientes.
                  </li>
                )}
              </ul>
            </Panel>
          </section>

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <Panel title="Mis Tareas Pendientes" actionHref="/tasks" actionLabel="Ver todo">
              <ul className="space-y-2">
                {tasks.slice(0, 6).map((task) => (
                  <li key={task.id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-white/5">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">{task.title}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">
                      {task.project_title || "General"}
                    </div>
                  </li>
                ))}
                {!loading && tasks.length === 0 && (
                  <li className="text-sm text-slate-500 dark:text-slate-400">No tienes tareas pendientes.</li>
                )}
              </ul>
            </Panel>

            <Panel title="Mensajes y Notificaciones" actionHref="/inbox" actionLabel="Ir a bandeja">
              <ul className="space-y-2">
                {unreadNotifications.slice(0, 6).map((notification) => (
                  <li key={notification.id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-white/5">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">{notification.title}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400">{notification.module}</div>
                  </li>
                ))}
                {!loadingNotifications && unreadNotifications.length === 0 && (
                  <li className="text-sm text-slate-500 dark:text-slate-400">No tienes mensajes pendientes.</li>
                )}
              </ul>
            </Panel>

            <Panel title="Calendario Próximo" actionHref="/calendar" actionLabel="Abrir calendario">
              <ul className="space-y-2">
                {mergedUpcoming.map((item) => (
                  <li key={item.id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm dark:bg-white/5">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">{item.title}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
                      <Clock size={12} />
                      {new Date(item.start).toLocaleString("es-CO")}
                    </div>
                  </li>
                ))}
                {!loading && mergedUpcoming.length === 0 && (
                  <li className="text-sm text-slate-500 dark:text-slate-400">Sin actividades próximas.</li>
                )}
              </ul>
            </Panel>
          </section>

          <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <QuickLink href="/account" icon={UserCircle} label="Gestionar Perfil" />
            <QuickLink href="/account/ministry-profile" icon={Bell} label="Preferencias y Notificaciones" />
            <QuickLink href="/settings" icon={Settings} label="Configuración General" />
          </section>
        </div>
      </div>
    </WorkspaceLayout>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  href: string;
}) {
  return (
    <Link href={href} className="rounded-2xl border border-slate-200 bg-white p-4 transition hover:shadow-md dark:border-white/10 dark:bg-[#1a1b1e]">
      <div className="mb-2 flex items-center gap-2 text-slate-500 dark:text-slate-300">
        <Icon size={16} />
        <span className="text-xs font-black uppercase tracking-widest">{label}</span>
      </div>
      <div className="text-3xl font-black text-slate-900 dark:text-white">{value}</div>
    </Link>
  );
}

function Panel({
  title,
  actionHref,
  actionLabel,
  children,
}: {
  title: string;
  actionHref: string;
  actionLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-[#1a1b1e]">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-black text-slate-800 dark:text-slate-200">{title}</h2>
        <Link href={actionHref} className="text-xs font-black uppercase tracking-widest text-blue-600">
          {actionLabel}
        </Link>
      </div>
      {children}
    </div>
  );
}

function QuickLink({
  href,
  icon: Icon,
  label,
}: {
  href: string;
  icon: React.ElementType;
  label: string;
}) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold text-slate-700 transition hover:shadow-md dark:border-white/10 dark:bg-[#1a1b1e] dark:text-slate-200"
    >
      <Icon size={18} />
      {label}
    </Link>
  );
}
