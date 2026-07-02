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
  ProjectWhiteboard,
} from "@/lib/whiteboards";
import { useAuth } from "@/context/AuthContext";

export default function WhiteboardPage() {
  const router = useRouter();
  const { token } = useAuth();
  const [query, setQuery] = useState("");
  const [boards, setBoards] = useState<ProjectWhiteboard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBoards();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchBoards = async () => {
    if (!token) return;
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

  const deleteBoard = async (projectId: string) => {
    if (!token) return;
    try {
      await deleteProjectWhiteboard(projectId, token);
      setBoards((prev) => prev.filter((b) => b.project_id !== projectId));
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
              className="w-full bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 rounded-lg py-3 pl-12 pr-4 text-sm outline-none focus:ring-4 focus:ring-blue-500/10 transition-all"
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
                  className="group rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 shadow-sm transition-all hover:border-blue-300 hover:shadow-xl dark:border-white/10 dark:bg-white/5"
                >
                  <button
                    onClick={() =>
                      router.push(`/plataforma/whiteboard/${board.project_id}`)
                    }
                    className="block w-full text-left"
                  >
                    <div className="mb-5 flex h-36 items-center justify-center rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] bg-[radial-gradient(#cbd5e1_1px,transparent_1px)] [background-size:20px_20px] dark:border-white/10 dark:bg-black/20 dark:bg-[radial-gradient(#334155_1px,transparent_1px)]">
                      <Sparkles
                        className="text-[hsl(var(--primary))] opacity-70"
                        size={34}
                      />
                    </div>
                    <h3 className="text-lg font-bold tracking-tight text-[hsl(var(--text-primary))] dark:text-white">
                      {board.title}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-sm font-medium text-[hsl(var(--text-secondary))]">
                      Proyecto: {board.project_id.slice(0, 8)}...
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <Clock size={12} />
                      {formatBoardDate(board.updated_at || board.created_at)}
                    </div>
                  </button>
                  <div className="mt-5 flex items-center justify-between border-t border-[hsl(var(--border))] pt-4 dark:border-white/10">
                    <button
                      onClick={() =>
                        router.push(`/plataforma/whiteboard/${board.project_id}`)
                      }
                      className="rounded-md bg-[hsl(var(--primary))] px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20"
                    >
                      Abrir
                    </button>
                    <button
                      onClick={() => deleteBoard(board.project_id)}
                      className="rounded-md p-2 text-[hsl(var(--text-secondary))] transition-all hover:bg-rose-50 hover:text-rose-500 dark:hover:bg-rose-500/10"
                      title="Eliminar pizarra"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="border-2 border-dashed border-[hsl(var(--border))] dark:border-white/10 rounded-lg p-4 text-center bg-white/60 dark:bg-white/[0.03]">
              <Sparkles
                size={40}
                className="mx-auto text-[hsl(var(--text-secondary))] mb-3"
              />
              <p className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                {boards.length === 0
                  ? "No hay pizarras registradas todavia"
                  : "Sin resultados"}
              </p>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-2">
                {boards.length === 0
                  ? "Crea una nueva pizarra seleccionando un proyecto."
                  : "Ajusta la busqueda para encontrar otro lienzo."}
              </p>
            </div>
          )}
        </div>
      </div>
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
