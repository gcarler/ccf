import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

type Strategy = {
  id: string;
  nombre: string;
  typology: string;
  dia_reunion: string;
  hora_reunion: string;
  is_public: boolean;
};

export default function PublicStrategiesManager({ token }: { token: string }): React.ReactElement | null {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<Strategy[]>("/evangelism/strategies/public-config", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((data) => setStrategies(data))
      .catch(() => toast.error("Error al cargar estrategias"))
      .finally(() => setLoading(false));
  }, [token]);

  const togglePublic = async (id: string, currentVal: boolean) => {
    setStrategies((prev) =>
      prev.map((st) => (st.id === id ? { ...st, is_public: !currentVal } : st))
    );
    try {
      await apiFetch(`/evangelism/strategies/${id}/toggle-public`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ is_public: !currentVal }),
      });
      toast.success(`Estrategia ${!currentVal ? "publicada ✓" : "ocultada"}`);
    } catch {
      setStrategies((prev) =>
        prev.map((st) => (st.id === id ? { ...st, is_public: currentVal } : st))
      );
      toast.error("No se pudo actualizar");
    }
  };

  if (loading) {
    return (
      <div className="p-4 flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="animate-spin" size={16} /> Cargando estrategias…
      </div>
    );
  }

  if (strategies.length === 0) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        No hay estrategias de evangelismo activas.
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="font-bold mb-2 text-sm">
        📢 Estrategias en <code className="text-xs bg-muted px-1 rounded">/eventos</code> y home
      </h3>
      <p className="text-xs text-muted-foreground mb-3">
        Activa una estrategia para que aparezca en el home y en /eventos con su próxima fecha automáticamente.
      </p>
      <div className="space-y-2">
        {strategies.map((st) => (
          <div
            key={st.id}
            className="flex items-center justify-between p-3 border rounded-lg bg-background"
          >
            <div>
              <p className="font-semibold text-sm">{st.nombre}</p>
              <p className="text-xs text-muted-foreground capitalize">
                {st.typology?.replace("_", " ") || "Sin tipo"} •{" "}
                {st.dia_reunion || "—"} {st.hora_reunion || ""}
              </p>
            </div>
            <button
              role="switch"
              aria-checked={st.is_public}
              onClick={() => togglePublic(st.id, st.is_public)}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                st.is_public ? "bg-primary" : "bg-muted-foreground/30"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  st.is_public ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
