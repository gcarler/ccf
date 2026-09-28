"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import CrmShell from "@/components/crm/CrmShell";
import AdminHero from "@/components/admin/AdminHero";
import {
  LayoutDashboard,
  Sparkles,
  Plus,
  Search,
  Clock,
  Trash2,
  Loader2,
} from "lucide-react";
import {
  fetchProjectWhiteboards,
  deleteProjectWhiteboard,
  resolveApiUrl,
  ProjectWhiteboard,
} from "@/lib/whiteboards";
import { useAuth } from "@/context/AuthContext";
import ConfirmDeleteDrawer from "@/components/ui/ConfirmDeleteDrawer";

export default function WhiteboardPage() {
  const router = useRouter();
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [boards, setBoards] = useState<ProjectWhiteboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [boardToDelete, setBoardToDelete] = useState<ProjectWhiteboard | null>(null);

  useEffect(() => {
    fetchBoards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchBoards = async () => {
    if (!token) {
      setBoards([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchProjectWhiteboards(token);
      setBoards(data);
    } catch (err) {
      console.error("Error loading whiteboards:", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return boards;
    return boards.filter((board) =>
      board.title.toLowerCase().includes(normalized)
    );
  }, [boards, query]);

  const confirmDeleteBoard = async () => {
    if (!token || !boardToDelete) return;
    try {
      await deleteProjectWhiteboard(boardToDelete.project_id, token);
      setBoards((prev) => prev.filter((b) => b.project_id !== boardToDelete.project_id));
      setBoardToDelete(null);
    } catch (err) {
      console.error("Error deleting whiteboard:", err);
    }
  };

  return (
    <CrmShell
      breadcrumbs={[
        { label: "CCF Tools", icon: LayoutDashboard },
        { label: "Lienzo Colaborativo", icon: Sparkles },
      ]}
    >
      <div className="space-y-3 px-4 py-8">
        <AdminHero
          eyebrow="PRODUCTIVIDAD"
          title="Pizarras Infinitas"
          description="Espacios de trabajo visuales con canvas real, capas y persistencia en la nube vinculada a proyectos."
          tags={["Canvas", "Cloud"]}
          watchers={["Equipo Estrategico", "Diseno"]}
          primaryAction={{
            label: "Nueva Pizarra",
            icon: Plus,
            onClick: () => router.push("/plataforma/whiteboard/new"),
          }}
        />

        <div className="w-full space-y-3">
          <div className="relative max-w-md">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
              size={18}
            />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar en tus lienzos..."
              className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-lg py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-[hsl(var(--primary))]/10 transition-all text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))]"
            />
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12 text-[hsl(var(--text-secondary))]">
              <Loader2 size={24} className="animate-spin mr-2" />
              Cargando pizarras...
            </div>
          ) : filtered.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {filtered.map((board) => (
                <article
                  key={board.project_id}
                  className="group rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3 shadow-sm transition-all hover:border-[hsl(var(--primary))/0.3] hover:shadow-xl"
                >
                  <button
                    onClick={() =>
                      router.push(`/plataforma/whiteboard/${board.project_id}`)
                    }
                    className="block w-full text-left"
                  >
                    <div className="relative mb-5 flex h-36 items-center justify-center overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] [background-size:20px_20px]">
                      {board.thumbnail_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={resolveApiUrl(board.thumbnail_url)}
                          alt={board.title}
                          className="absolute inset-0 h-full w-full object-cover"
                        />
                      ) : (
                        <Sparkles
                          className="text-[hsl(var(--primary))] opacity-70"
                          size={34}
                        />
                      )}
                    </div>
                    <h3 className="text-lg font-bold tracking-tight text-[hsl(var(--text-primary))]">
                      {board.title}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-sm font-medium text-[hsl(var(--text-secondary))]">
                      Proyecto: {board.project_id.slice(0, 8)}...
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <Clock size={12} />
                      {formatBoardDate(board.updated_at || board.created_at)}
                    </div>
                  </button>
                  <div className="mt-5 flex items-center justify-between border-t border-[hsl(var(--border))] pt-4">
                    <button
                      onClick={() =>
                        router.push(`/plataforma/whiteboard/${board.project_id}`)
                      }
                      className="rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))] shadow-lg shadow-[hsl(var(--primary))/0.2]"
                    >
                      Abrir
                    </button>
                    <button
                      onClick={() => setBoardToDelete(board)}
                      className="rounded-md p-2 text-[hsl(var(--text-secondary))] transition-all hover:bg-[hsl(var(--danger))]/10 hover:text-[hsl(var(--danger))]"
                      title="Eliminar pizarra"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="border-2 border-dashed border-[hsl(var(--border))] rounded-lg p-4 text-center bg-[hsl(var(--surface-1))]/60">
              <Sparkles
                size={40}
                className="mx-auto text-[hsl(var(--text-secondary))] mb-3"
              />
              <p className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                {!token
                  ? "Debes iniciar sesión"
                  : boards.length === 0
                  ? "No hay pizarras registradas todavia"
                  : "Sin resultados"}
              </p>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-2">
                {!token
                  ? "Inicia sesión para ver y administrar las pizarras vinculadas a tus proyectos."
                  : boards.length === 0
                  ? "Crea una nueva pizarra seleccionando un proyecto."
                  : "Ajusta la busqueda para encontrar otro lienzo."}
              </p>
            </div>
          )}
        </div>
      </div>
      <ConfirmDeleteDrawer
        open={Boolean(boardToDelete)}
        onClose={() => setBoardToDelete(null)}
        onConfirm={confirmDeleteBoard}
        title="¿Eliminar pizarra de proyecto?"
        description={
          boardToDelete
            ? `Se eliminará la pizarra vinculada al proyecto "${boardToDelete.title || boardToDelete.project_id}". Esta acción no se puede deshacer.`
            : "Eliminar esta pizarra no se puede deshacer."
        }
        confirmLabel="Eliminar pizarra"
      />
    </CrmShell>
  );
}

function formatBoardDate(value: string | null | undefined) {
  if (!value) return "Sin fecha";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Sin fecha";
  return date.toLocaleDateString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
