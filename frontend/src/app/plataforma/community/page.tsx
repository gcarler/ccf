"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { Bell, CalendarDays, Download, Heart, HeartHandshake, Megaphone, MessageSquare, Plus, RefreshCw, Search, Star, Users } from "lucide-react";
import { toast } from "sonner";
import { DSButton, DSCard, DSInput, DSSkeleton } from "@/design";
import RightPanel from "@/components/ui/RightPanel";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { formatDate } from "@/lib/format";

interface CommunityBoardCard {
  id: string;
  title: string;
  body?: string | null;
  created_at: string;
}

const COMMUNITY_MODULES = [
  { title: "Notificaciones", description: "Avisos y actualizaciones de la comunidad.", icon: Bell, href: "/plataforma/community/notifications" },
  { title: "Anuncios", description: "Comunicaciones oficiales para la comunidad.", icon: Megaphone, href: "/plataforma/community/announcements" },
  { title: "Mensajes", description: "Conversaciones y coordinación de equipos.", icon: MessageSquare, href: "/plataforma/community/messages" },
  { title: "Eventos", description: "Calendario de reuniones y actividades.", icon: CalendarDays, href: "/plataforma/community/events" },
  { title: "Ofrendas", description: "Campañas de generosidad y apoyo.", icon: HeartHandshake, href: "/plataforma/community/give" },
  { title: "Oración", description: "Peticiones y testimonios de oración.", icon: Heart, href: "/plataforma/community/prayer" },
  { title: "Testimonios", description: "Historias compartidas por la comunidad.", icon: Star, href: "/plataforma/community/testimonies" },
  { title: "Grupos pequeños", description: "Conexión y vida en grupos.", icon: Users, href: "/plataforma/community/grupos" },
  { title: "Descubrir", description: "Explora grupos y oportunidades para participar.", icon: Search, href: "/plataforma/community/discover" },
];

export default function CommunityHubPage() {
  const { token } = useAuth();
  const [cards, setCards] = useState<CommunityBoardCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const requestInFlight = useRef(false);
  const submitInFlight = useRef(false);
  const requestVersion = useRef(0);
  const sessionGeneration = useRef(0);
  const sessionToken = useRef(token);

  const loadCards = useCallback(async (force = false) => {
    if (requestInFlight.current && !force) return;
    requestInFlight.current = true;
    const version = ++requestVersion.current;
    setRefreshing(true);
    try {
      const result = await apiFetch<CommunityBoardCard[]>("/community/cards", {
        ...(token ? { token } : {}),
        cache: "no-store",
      });
      if (version !== requestVersion.current) return;
      setCards(Array.isArray(result) ? result : []);
      setLoadError(false);
    } catch {
      if (version === requestVersion.current) setLoadError(true);
    } finally {
      if (version === requestVersion.current) {
        requestInFlight.current = false;
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [token]);

  useEffect(() => {
    if (sessionToken.current !== token) {
      sessionToken.current = token;
      setCreateOpen(false);
      setTitle("");
      setBody("");
    }
    sessionGeneration.current += 1;
    const activeSession = sessionGeneration.current;
    requestVersion.current += 1;
    requestInFlight.current = false;
    setCards([]);
    setLoading(true);
    void loadCards();
    return () => {
      if (sessionGeneration.current === activeSession) sessionGeneration.current += 1;
      requestVersion.current += 1;
      requestInFlight.current = false;
    };
  }, [loadCards, token]);

  const resetForm = () => {
    setTitle("");
    setBody("");
  };

  const closeCreatePanel = () => setCreateOpen(false);

  const handleCreateCard = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitInFlight.current || !title.trim()) return;

    const submittingSession = sessionGeneration.current;
    submitInFlight.current = true;
    setSubmitting(true);
    try {
      const createdCard = await apiFetch<CommunityBoardCard>("/community/cards", {
        method: "POST",
        ...(token ? { token } : {}),
        body: { title: title.trim(), body: body.trim() || null },
      });
      if (submittingSession !== sessionGeneration.current) return;
      setCards((current) => [createdCard, ...current.filter((card) => card.id !== createdCard.id)]);
      setLoadError(false);
      toast.success("Tarjeta creada");
      resetForm();
      closeCreatePanel();
      await loadCards(true);
    } catch {
      if (submittingSession === sessionGeneration.current) {
        toast.error("No se pudo crear la tarjeta. Revisa tus permisos e inténtalo de nuevo.");
      }
    } finally {
      submitInFlight.current = false;
      setSubmitting(false);
    }
  };

  const handleExport = () => {
    if (cards.length === 0 || typeof window === "undefined") return;
    const csvRows = [
      ["Título", "Descripción", "Fecha de creación"],
      ...cards.map((card) => [card.title, card.body ?? "", formatDate(card.created_at, { fallback: "" })]),
    ];
    const csv = csvRows.map((row) => row.map(escapeCsvCell).join(",")).join("\r\n");
    const blob = new Blob([`\uFEFF${csv}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "comunidad-tarjetas.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto w-full max-w-7xl space-y-8 px-4 py-5 pb-10 sm:px-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Comunidad CCF</p>
          <h1 className="text-2xl font-bold tracking-tight text-[hsl(var(--text-primary))]">Comunidad</h1>
          <p className="max-w-2xl text-sm text-[hsl(var(--text-secondary))]">
            Canales y recursos para mantener conectada a la comunidad.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <DSButton variant="secondary" onClick={() => void loadCards()} disabled={refreshing} aria-label="Actualizar tarjetas">
            <RefreshCw size={14} aria-hidden="true" className={refreshing ? "animate-spin" : undefined} />
            Actualizar
          </DSButton>
          <DSButton onClick={() => setCreateOpen(true)}>
            <Plus size={15} aria-hidden="true" /> Nueva tarjeta
          </DSButton>
        </div>
      </header>

      <section aria-labelledby="community-cards-title" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-1">
            <h2 id="community-cards-title" className="text-lg font-semibold text-[hsl(var(--text-primary))]">Tablero de la comunidad</h2>
            <p className="text-sm text-[hsl(var(--text-secondary))]">Tarjetas y comunicados compartidos con la comunidad.</p>
          </div>
          {cards.length > 0 && (
            <DSButton variant="ghost" onClick={handleExport}>
              <Download size={14} aria-hidden="true" /> Exportar CSV
            </DSButton>
          )}
        </div>

        {loadError && (
          <div className="flex flex-col gap-3 rounded-lg border border-[hsl(var(--destructive)/0.3)] bg-[hsl(var(--surface-1))] p-4 sm:flex-row sm:items-center sm:justify-between" role="alert">
            <p className="text-sm text-[hsl(var(--destructive))]">No se pudieron cargar las tarjetas de Comunidad.</p>
            <DSButton variant="secondary" onClick={() => void loadCards()} disabled={refreshing}>Reintentar</DSButton>
          </div>
        )}

        {loading ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3" aria-label="Cargando tarjetas" aria-busy="true">
            {Array.from({ length: 3 }, (_, index) => (
              <DSCard key={index} className="space-y-3 p-4">
                <DSSkeleton className="h-4 w-2/3" />
                <DSSkeleton className="h-3 w-full" />
                <DSSkeleton className="h-3 w-1/2" />
              </DSCard>
            ))}
          </div>
        ) : cards.length === 0 && !loadError ? (
          <div className="rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-5 py-10 text-center">
            <h3 className="text-base font-semibold text-[hsl(var(--text-primary))]">Aún no hay tarjetas</h3>
            <p className="mx-auto mt-1 max-w-md text-sm text-[hsl(var(--text-secondary))]">
              Cuando se publiquen tarjetas de Comunidad, aparecerán aquí.
            </p>
            <DSButton className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus size={14} aria-hidden="true" /> Crear tarjeta
            </DSButton>
          </div>
        ) : cards.length > 0 ? (
          <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <DSCard key={card.id} className="min-w-0 p-[calc(1rem+var(--density-pad-y-delta,0px))]">
                <article aria-labelledby={`community-card-${card.id}`}>
                  <h3 id={`community-card-${card.id}`} className="break-words text-base font-semibold text-[hsl(var(--text-primary))]">
                    {card.title}
                  </h3>
                  {card.body ? (
                    <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[hsl(var(--text-secondary))]">{card.body}</p>
                  ) : null}
                  <p className="mt-4 border-t border-[hsl(var(--border))] pt-3 text-2xs text-[hsl(var(--text-secondary))]">
                    Publicada {formatDate(card.created_at, { fallback: "en fecha no disponible" })}
                  </p>
                </article>
              </DSCard>
            ))}
          </div>
        ) : null}
      </section>

      <section aria-labelledby="community-modules-title" className="space-y-4">
        <div className="space-y-1">
          <h2 id="community-modules-title" className="text-lg font-semibold text-[hsl(var(--text-primary))]">Explora Comunidad</h2>
          <p className="text-sm text-[hsl(var(--text-secondary))]">Accede directamente a los espacios de interacción.</p>
        </div>
        <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {COMMUNITY_MODULES.map(({ title: moduleTitle, description, icon: Icon, href }) => (
            <Link key={moduleTitle} href={href} className="group min-w-0 rounded-lg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]">
              <DSCard className="flex h-full min-w-0 items-start gap-3 p-[calc(1rem+var(--density-pad-y-delta,0px))] transition-colors group-hover:border-[hsl(var(--primary)/0.4)] group-hover:bg-[hsl(var(--surface-2))]">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))]">
                  <Icon size={17} aria-hidden="true" />
                </span>
                <span className="min-w-0 space-y-1">
                  <span className="block text-sm font-semibold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))]">{moduleTitle}</span>
                  <span className="block break-words text-xs leading-relaxed text-[hsl(var(--text-secondary))]">{description}</span>
                </span>
              </DSCard>
            </Link>
          ))}
        </div>
      </section>

      <RightPanel open={createOpen} onClose={closeCreatePanel} title="Nueva tarjeta" subtitle="Publica una tarjeta para la comunidad." width="w-full sm:max-w-xl">
        <form onSubmit={handleCreateCard} className="space-y-5 p-4">
          <DSInput
            label="Título"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            maxLength={200}
            required
            autoFocus
            placeholder="Escribe un título"
          />
          <label className="flex flex-col gap-1.5 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]" htmlFor="community-card-body">
            Descripción <span className="font-normal normal-case">(opcional)</span>
            <textarea
              id="community-card-body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              rows={6}
              className="w-full resize-y rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-sm font-normal normal-case text-[hsl(var(--text-primary))] outline-none focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))]"
              placeholder="Agrega contexto para la comunidad"
            />
          </label>
          <div className="flex justify-end gap-2 border-t border-[hsl(var(--border))] pt-4">
            <DSButton variant="secondary" onClick={() => { closeCreatePanel(); resetForm(); }} disabled={submitting}>Cancelar</DSButton>
            <DSButton type="submit" loading={submitting} disabled={!title.trim() || submitting}>Publicar tarjeta</DSButton>
          </div>
        </form>
      </RightPanel>
    </div>
  );
}

function escapeCsvCell(value: string): string {
  const safeValue = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${safeValue.replaceAll('"', '""')}"`;
}
