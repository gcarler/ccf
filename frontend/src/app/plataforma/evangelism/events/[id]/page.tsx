"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { useAuth } from "@/context/AuthContext";
import { ApiError, apiFetch } from "@/lib/http";
import EvangelismShell from "@/components/evangelism/EvangelismShell";
import { MapPin, ArrowLeft } from "lucide-react";
import { DSCard } from '@/design';
import clsx from "clsx";

const SessionTab = dynamic(() => import("./tabs/SessionTab"), { ssr: false });
const AnalyticsTab = dynamic(() => import("./tabs/AnalyticsTab"), { ssr: false });

type MinistryEventDetail = {
  id: string;
  name: string;
  title?: string;
  description: string | null;
  event_date: string | null;
  location: string | null;
  attendees_count: number;
  status: string;
  created_at: string | null;
};

export default function EventDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;
  const { token, hasModuleAccess } = useAuth();
  const canOperateEvents = hasModuleAccess('evangelism', 'edit');

  const [event, setEvent] = useState<MinistryEventDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [activeTab, setActiveTab] = useState<'details' | 'session' | 'analytics'>('details');

  useEffect(() => {
    if (!token || !id) return;
    const loadEvent = async () => {
      try {
        setLoading(true);
        setNotFound(false);
        setLoadError(false);
        const data = await apiFetch<MinistryEventDetail>(`/evangelism/events/${id}`, { token, silent: true });
        setEvent(data);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          setEvent(null);
          setNotFound(true);
          return;
        }
        setEvent(null);
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    };
    loadEvent();
  }, [id, token]);

  if (loading) {
    return <div className="p-4 text-center animate-pulse font-bold text-[hsl(var(--text-secondary))]">Cargando...</div>;
  }

  if (notFound) {
    return (
      <EvangelismShell breadcrumbs={[{ label: "Evangelismo", href: "/plataforma/evangelism/events" }, { label: "Eventos", href: "/plataforma/evangelism/events" }, { label: "No encontrado" }]}>
        <div className="p-6">
          <div className="max-w-xl mx-auto rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-6 text-center shadow-sm">
            <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">Evento no encontrado</h2>
            <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
              El evento solicitado no existe o ya fue eliminado.
            </p>
            <button
              onClick={() => router.push('/plataforma/evangelism/events')}
              className="mt-4 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-white"
            >
              Volver a Eventos
            </button>
          </div>
        </div>
      </EvangelismShell>
    );
  }

  if (loadError) {
    return (
      <EvangelismShell breadcrumbs={[{ label: "Evangelismo", href: "/plataforma/evangelism/events" }, { label: "Eventos", href: "/plataforma/evangelism/events" }, { label: "Error" }]}>
        <div className="p-6">
          <div className="max-w-xl mx-auto rounded-xl border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] p-6 text-center shadow-sm">
            <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">No se pudo cargar el evento</h2>
            <p className="mt-2 text-sm text-[hsl(var(--text-secondary))]">
              La plataforma recibió una respuesta inválida al consultar este evento. Puedes volver a intentarlo desde la lista.
            </p>
            <button
              onClick={() => router.push('/plataforma/evangelism/events')}
              className="mt-4 rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-white"
            >
              Volver a Eventos
            </button>
          </div>
        </div>
      </EvangelismShell>
    );
  }

  if (!event) {
    return null;
  }

  return (
    <EvangelismShell breadcrumbs={[{ label: "Evangelismo", href: "/plataforma/evangelism/events" }, { label: "Eventos", href: "/plataforma/evangelism/events" }, { label: event.name }]}>
      <main className="flex-1 overflow-y-auto p-4 lg:p-4">
        <div className="w-full space-y-3">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] uppercase">{event.name}</h1>
              <p className="text-[hsl(var(--text-secondary))] font-medium text-sm flex items-center gap-2 mt-1">
                <MapPin size={14}/> {event.location || 'Sin ubicación'}
              </p>
            </div>
            <div className="flex flex-col items-stretch gap-3">
              <div className="flex flex-wrap justify-end gap-2">
                <span className="rounded-full border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                  Seguimiento ministerial
                </span>
                <span
                  className={`rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                    activeTab === 'session'
                      ? "bg-info-soft text-[hsl(var(--primary))] dark:bg-[hsl(var(--info))]/10 dark:text-info-text"
                      : "bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                  }`}
                >
                  {activeTab === 'session' ? "Sesión activa" : "Evento con seguimiento"}
                </span>
              </div>
              <div className="flex bg-[hsl(var(--bg-muted))] p-1 rounded-lg">
                <button
                  onClick={() => setActiveTab('details')}
                  className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'details' ? "bg-[hsl(var(--bg-primary))] dark:bg-[#252528] text-[hsl(var(--primary))] shadow-sm" : "text-[hsl(var(--text-secondary))]")}
                >Detalles Generales</button>
                {canOperateEvents && (
                  <button
                    onClick={() => setActiveTab('session')}
                    className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'session' ? "bg-[hsl(var(--bg-primary))] dark:bg-[#252528] text-[hsl(var(--primary))] shadow-sm" : "text-[hsl(var(--text-secondary))]")}
                  >Configurar sesión</button>
                )}
                <button
                  onClick={() => setActiveTab('analytics')}
                  className={clsx("px-4 py-2.5 rounded-md text-xs font-semibold uppercase tracking-wide transition-all", activeTab === 'analytics' ? "bg-[hsl(var(--bg-primary))] dark:bg-[#252528] text-[hsl(var(--primary))] shadow-sm" : "text-[hsl(var(--text-secondary))]")}
                >Analítica</button>
              </div>
            </div>
          </div>

          {activeTab === 'details' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="lg:col-span-2 space-y-3">
                <DSCard>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Descripción</h3>
                  <p className="text-[hsl(var(--text-secondary))] font-medium">{event.description || "Sin descripción."}</p>
                </DSCard>
              </div>
              <div className="space-y-3">
                <DSCard>
                  <h3 className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-4">Acciones</h3>
                  <button onClick={() => router.push('/plataforma/evangelism/events')} className="w-full py-1.5 bg-info-soft dark:bg-[hsl(var(--info))]/20 text-[hsl(var(--primary))] rounded-md font-bold flex items-center justify-center gap-2">
                    <ArrowLeft size={16}/> Volver a Eventos
                  </button>
                </DSCard>
              </div>
            </div>
          )}

          {activeTab === 'analytics' && <AnalyticsTab eventId={id} token={token} />}

          {activeTab === 'session' && canOperateEvents && <SessionTab eventId={id} token={token} eventName={event.name} />}
        </div>
      </main>
    </EvangelismShell>
  );
}
