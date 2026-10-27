"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/http";

interface AgendaResource {
  id: string;
  name: string;
  resource_type: string;
  capacity: number | null;
  is_active: boolean;
}

interface AgendaReservation {
  id: string;
  event_id: string;
  resource_id: string;
  starts_at: string;
  ends_at: string;
}

function useAgendaCollection<T>(url: string, token: string | null, errorMessage: string) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestSequence = useRef(0);
  const refresh = useCallback(async () => {
    const request = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const data = token ? await apiFetch<T[]>(url, { token, cache: "no-store" }) : [];
      if (!Array.isArray(data)) throw new Error("Invalid agenda collection response");
      if (request === requestSequence.current) setItems(data);
    } catch {
      if (request === requestSequence.current) {
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } finally {
      if (request === requestSequence.current) setLoading(false);
    }
  }, [url, token, errorMessage]);
  useEffect(() => {
    setItems([]);
    void refresh();
    return () => { requestSequence.current += 1; };
  }, [refresh]);
  return { items, loading, error, refresh };
}

const panelClass = "rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3";
const retryClass = "rounded-md border border-[hsl(var(--border))] px-3 py-2 text-sm text-[hsl(var(--primary))]";

export function AgendaEventResources({ eventId, token }: { eventId: string; token: string | null }) {
  const sectionId = useId();
  const resources = useAgendaCollection<AgendaResource>("/agenda/resources", token, "No se pudieron cargar los recursos.");
  const reservations = useAgendaCollection<AgendaReservation>(`/agenda/events/${eventId}/reservations`, token, "No se pudieron cargar las reservas.");
  const available = resources.items.filter(resource => resource.is_active);
  const formatTime = (value: string) => new Date(value).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", hour12: false });
  return (
    <div className="grid min-w-0 gap-4 lg:grid-cols-2">
      <section role="region" aria-labelledby={`${sectionId}-resources`} className={panelClass}>
        <h2 id={`${sectionId}-resources`} className="font-semibold text-[hsl(var(--text-primary))]">Recursos disponibles</h2>
        {resources.loading ? <div role="status" aria-label="Cargando recursos" className="h-20 animate-pulse rounded bg-[hsl(var(--surface-2))]" />
          : resources.error ? <div role="alert"><p>{resources.error}</p><button type="button" className={retryClass} onClick={() => void resources.refresh()}>Reintentar recursos</button></div>
          : available.length === 0 ? <p className="text-sm text-[hsl(var(--text-secondary))]">No hay recursos disponibles.</p>
          : <ul className="space-y-2">{available.map(resource => <li key={resource.id} className="rounded-md bg-[hsl(var(--surface-2))] p-3 text-sm">
            <p className="font-medium">{resource.name}</p><p className="text-[hsl(var(--text-secondary))]">{resource.resource_type}</p>
            {resource.capacity != null && <p>Capacidad: {resource.capacity}</p>}
          </li>)}</ul>}
      </section>
      <section role="region" aria-labelledby={`${sectionId}-reservations`} className={panelClass}>
        <h2 id={`${sectionId}-reservations`} className="font-semibold text-[hsl(var(--text-primary))]">Reservas del evento</h2>
        {reservations.loading ? <div role="status" aria-label="Cargando reservas" className="h-20 animate-pulse rounded bg-[hsl(var(--surface-2))]" />
          : reservations.error ? <div role="alert"><p>{reservations.error}</p><button type="button" className={retryClass} onClick={() => void reservations.refresh()}>Reintentar reservas</button></div>
          : reservations.items.length === 0 ? <p className="text-sm text-[hsl(var(--text-secondary))]">No hay reservas para este evento.</p>
          : <ul className="space-y-2">{reservations.items.map(reservation => <li key={reservation.id} className="rounded-md bg-[hsl(var(--surface-2))] p-3 text-sm">
            <p className="font-medium">{resources.items.find(resource => resource.id === reservation.resource_id)?.name ?? "Recurso no disponible"}</p>
            <p><time dateTime={reservation.starts_at}>{formatTime(reservation.starts_at)}</time> – <time dateTime={reservation.ends_at}>{formatTime(reservation.ends_at)}</time></p>
          </li>)}</ul>}
      </section>
    </div>
  );
}
