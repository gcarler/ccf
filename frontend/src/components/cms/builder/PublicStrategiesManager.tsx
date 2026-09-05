import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function PublicStrategiesManager({ token }: { token: string }): React.ReactElement | null {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [strategies, setStrategies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const res = (await apiFetch("/api/evangelism/strategies/public-config", {
          headers: { Authorization: `Bearer ${token}` }
        })) as Response;
        
        if (res.ok) {
          const data = await res.json();
          setStrategies(data);
        }
      } catch (e) {
        console.error(e);
        toast.error("Error al cargar estrategias");
      } finally {
        setLoading(false);
      }
    };

    fetchStrategies();
  }, [token]);

  const togglePublic = async (id: string, currentVal: boolean) => {
    try {
      const res = (await apiFetch(`/api/evangelism/strategies/${id}/toggle-public`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ is_public: !currentVal })
      })) as Response;
      
      if (res.ok) {
        setStrategies(s => s.map(st => st.id === id ? { ...st, is_public: !currentVal } : st));
        toast.success("Estado actualizado");
      } else {
        toast.error("No se pudo actualizar");
      }
    } catch (e) {
      toast.error("Error de red");
    }
  };

  if (loading) {
    return <div className="p-4 flex items-center gap-2"><Loader2 className="animate-spin" size={16} /> Cargando estrategias...</div>;
  }

  return (
    <div className="shrink-0 bg-white dark:bg-[hsl(var(--surface-2))] border-t border-[hsl(var(--border))] max-h-64 overflow-y-auto p-4 z-10 relative">
      <h3 className="font-bold mb-3 text-sm">Gestión de Estrategias Públicas (/eventos)</h3>
      <div className="space-y-2">
        {strategies.map(st => (
          <div key={st.id} className="flex items-center justify-between p-3 border border-[hsl(var(--border))] rounded-lg bg-[hsl(var(--surface-1))]">
            <div>
              <p className="font-semibold text-sm">{st.nombre}</p>
              <p className="text-xs text-[hsl(var(--text-secondary))] capitalize">
                {st.typology?.replace('_', ' ') || 'Sin tipo'} • {st.dia_reunion || 'N/A'} {st.hora_reunion || 'N/A'}
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={st.is_public || false}
                onChange={() => togglePublic(st.id, st.is_public)}
              />
              <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all dark:border-gray-600 peer-checked:bg-[hsl(var(--primary))]"></div>
            </label>
          </div>
        ))}
      </div>
    </div>
  );
}
