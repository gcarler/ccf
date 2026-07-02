'use client';

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import EmptyState from '@/components/ui/EmptyState';
import Skeleton from '@/components/ui/Skeleton';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { useAuth } from '@/context/AuthContext';
import { DSBadge, DSCard } from '@/design';
import { apiFetch } from '@/lib/http';
import {
  GitBranch,
  History,
  Loader2,
  Scissors,
  Users,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

interface MultiplicationCheckItem {
  grupo_id: string;
  grupo_nombre: string;
  lider_nombre: string | null;
  total_miembros: number;
  excede_umbral: boolean;
  sugerencia: string;
}

interface MultiplicationHistoryItem {
  grupo_id: string;
  grupo_nombre: string;
  parent_group_id: string | null;
  parent_group_nombre: string | null;
  notes_historial: string | null;
  created_at: string | null;
  miembros_actuales: number;
  lider_nombre: string | null;
}

interface SplitResponse {
  ok: boolean;
  mensaje: string;
  grupo_original: {
    id: string;
    nombre: string;
    total_miembros: number;
  };
  nuevo_grupo: {
    id: string;
    nombre: string;
    total_miembros: number;
  };
  miembros_transferidos: number;
}

interface PersonaOption {
  id: string;
  nombre_completo: string;
}

export default function MultiplicationPage() {
  const { token } = useAuth();
  const [checks, setChecks] = useState<MultiplicationCheckItem[]>([]);
  const [history, setHistory] = useState<MultiplicationHistoryItem[]>([]);
  const [loadingChecks, setLoadingChecks] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [splitDrawerOpen, setSplitDrawerOpen] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<MultiplicationCheckItem | null>(null);
  const [nuevoNombre, setNuevoNombre] = useState('');
  const [nuevoLiderId, setNuevoLiderId] = useState('');
  const [personasOptions, setPersonasOptions] = useState<PersonaOption[]>([]);
  const [loadingPersonas, setLoadingPersonas] = useState(false);
  const [savingSplit, setSavingSplit] = useState(false);
  const [umbral, setUmbral] = useState(15);

  const fetchChecks = useCallback(
    async (threshold: number) => {
      if (!token) return;
      setLoadingChecks(true);
      try {
        const result = await apiFetch<MultiplicationCheckItem[]>('/evangelism/multiplication/check', {
          token,
          query: { umbral: String(threshold) },
        });
        setChecks(Array.isArray(result) ? result : []);
      } catch (e: any) {
        toast.error(e?.message || 'Error al cargar análisis de multiplicación');
      } finally {
        setLoadingChecks(false);
      }
    },
    [token]
  );

  const fetchHistory = useCallback(async () => {
    if (!token) return;
    setLoadingHistory(true);
    try {
      const result = await apiFetch<MultiplicationHistoryItem[]>('/evangelism/multiplication/history', {
        token,
      });
      setHistory(Array.isArray(result) ? result : []);
    } catch (e: any) {
      toast.error(e?.message || 'Error al cargar historial de multiplicaciones');
    } finally {
      setLoadingHistory(false);
    }
  }, [token]);

  const fetchPersonasForGroup = useCallback(
    async (grupoId: string) => {
      if (!token) return;
      setLoadingPersonas(true);
      try {
        // Fetch group details to get base attendees
        const groupDetail = await apiFetch<{
          base_attendees?: Array<{ persona_id: string; name: string }>;
        }>(`/evangelism/grupos/${grupoId}`, { token });
        const attendees = groupDetail?.base_attendees || [];
        setPersonasOptions(
          attendees.map((a) => ({ id: a.persona_id, nombre_completo: a.name }))
        );
      } catch {
        // Fallback: empty list, user can type manually if needed
        setPersonasOptions([]);
      } finally {
        setLoadingPersonas(false);
      }
    },
    [token]
  );

  useEffect(() => {
    fetchChecks(umbral);
  }, [fetchChecks, umbral]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const openSplitDrawer = (group: MultiplicationCheckItem) => {
    setSelectedGroup(group);
    setNuevoNombre(`${group.grupo_nombre} (Hijo)`);
    setNuevoLiderId('');
    fetchPersonasForGroup(group.grupo_id);
    setSplitDrawerOpen(true);
  };

  const handleSplit = async () => {
    if (!selectedGroup || !nuevoNombre.trim() || !nuevoLiderId) {
      toast.error('Completa el nombre del nuevo grupo y selecciona un líder');
      return;
    }
    setSavingSplit(true);
    try {
      const result = await apiFetch<SplitResponse>('/evangelism/multiplication/split', {
        method: 'POST',
        token,
        body: {
          grupo_id: selectedGroup.grupo_id,
          nuevo_nombre: nuevoNombre.trim(),
          nuevo_lider_id: nuevoLiderId,
        },
      });
      toast.success(result.mensaje);
      setSplitDrawerOpen(false);
      fetchChecks(umbral);
      fetchHistory();
    } catch (e: any) {
      const detail =
        e?.detail && typeof e.detail === 'object' && 'detail' in e.detail
          ? String(e.detail.detail)
          : e?.message;
      toast.error(detail || 'Error al dividir el grupo');
    } finally {
      setSavingSplit(false);
    }
  };

  const eligibleGroups = checks.filter((c) => c.excede_umbral);

  return (
    <EvangelismShell
      breadcrumbs={[
        { label: 'Evangelismo', href: '/plataforma/evangelism' },
        { label: 'Multiplicación' },
      ]}
    >
      <div className="p-4 space-y-5">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1">
              Herramientas y Gestión
            </p>
            <h1 className="text-xl font-bold text-[hsl(var(--text-primary))] tracking-tight flex items-center gap-2">
              <GitBranch size={22} className="text-emerald-500" />
              Multiplicación de Grupos
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="umbral-select" className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
              Umbral:
            </label>
            <select
              id="umbral-select"
              value={umbral}
              onChange={(e) => setUmbral(Number(e.target.value))}
              className="bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1 px-2 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
            >
              {[10, 12, 15, 18, 20, 25].map((v) => (
                <option key={v} value={v}>
                  {v} personas
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Multiplication Check */}
        <section>
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
            <Users size={14} />
            Análisis de Grupos
          </h2>
          {loadingChecks ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 rounded-lg" />
              ))}
            </div>
          ) : checks.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Sin grupos activos"
              description="No hay grupos activos para analizar en esta sede."
            />
          ) : (
            <div className="space-y-2">
              {checks.map((check) => (
                <div
                  key={check.grupo_id}
                  className={`flex items-center gap-3 border rounded-lg p-3 transition-all ${
                    check.excede_umbral
                      ? 'bg-emerald-50/50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-500/20 hover:shadow-md'
                      : 'bg-[hsl(var(--bg-primary))] border-[hsl(var(--border-primary))] hover:shadow-sm'
                  }`}
                >
                  <div
                    className={`size-10 rounded-lg flex items-center justify-center shrink-0 ${
                      check.excede_umbral
                        ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400'
                        : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'
                    }`}
                  >
                    <Users size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                        {check.grupo_nombre}
                      </p>
                      {check.excede_umbral && (
                        <DSBadge tone="emerald" label="Listo para dividir" />
                      )}
                    </div>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                      {check.lider_nombre || 'Sin líder'} · {check.total_miembros} miembros
                    </p>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5">
                      {check.sugerencia}
                    </p>
                  </div>
                  {check.excede_umbral && (
                    <button
                      onClick={() => openSplitDrawer(check)}
                      className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-[10px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all"
                    >
                      <Scissors size={14} />
                      Dividir
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Eligible Groups Summary */}
        {eligibleGroups.length > 0 && (
          <DSCard tone="light" className="border-emerald-200 dark:border-emerald-500/20">
            <div className="flex items-center gap-3">
              <div className="size-10 rounded-lg bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                <GitBranch size={18} />
              </div>
              <div>
                <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                  {eligibleGroups.length} grupo{eligibleGroups.length > 1 ? 's' : ''} listo
                  {eligibleGroups.length > 1 ? 's' : ''} para multiplicar
                </p>
                <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                  Superan el umbral de {umbral} personas. Revisa cada grupo y ejecuta la división
                  cuando el líder esté preparado.
                </p>
              </div>
            </div>
          </DSCard>
        )}

        {/* Multiplication History */}
        <section>
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3 flex items-center gap-2">
            <History size={14} />
            Historial de Multiplicaciones
          </h2>
          {loadingHistory ? (
            <div className="space-y-2">
              {[1, 2].map((i) => (
                <Skeleton key={i} className="h-20 rounded-lg" />
              ))}
            </div>
          ) : history.length === 0 ? (
            <EmptyState
              icon={History}
              title="Sin historial"
              description="Aún no se ha registrado ninguna multiplicación de grupos."
            />
          ) : (
            <div className="space-y-2">
              {history.map((item) => (
                <div
                  key={item.grupo_id}
                  className="flex items-center gap-3 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-3 hover:shadow-sm transition-all"
                >
                  <div className="size-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-[hsl(var(--primary))] flex items-center justify-center shrink-0">
                    <GitBranch size={18} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-[hsl(var(--text-primary))]">
                        {item.grupo_nombre}
                      </p>
                      <DSBadge tone="blue" label="Hijo" />
                    </div>
                    <p className="text-[10px] text-[hsl(var(--text-secondary))] font-medium">
                      {item.parent_group_nombre
                        ? `Nacido de: ${item.parent_group_nombre}`
                        : 'Grupo raíz'}
                      {item.lider_nombre ? ` · Líder: ${item.lider_nombre}` : ''}
                    </p>
                    {item.notes_historial && (
                      <p className="text-[10px] text-[hsl(var(--text-secondary))] mt-0.5 truncate">
                        {item.notes_historial}
                      </p>
                    )}
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-lg font-bold text-[hsl(var(--text-primary))]">
                      {item.miembros_actuales}
                    </p>
                    <p className="text-[9px] text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide">
                      miembros
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Split Drawer */}
      <WorkspaceDrawer
        isOpen={splitDrawerOpen}
        onClose={() => setSplitDrawerOpen(false)}
        title="Dividir Grupo"
        subtitle={`Grupo original: ${selectedGroup?.grupo_nombre}`}
        actions={
          <>
            <button
              disabled={savingSplit}
              onClick={() => setSplitDrawerOpen(false)}
              className="px-4 py-2 text-[11px] font-bold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors disabled:opacity-60"
            >
              Cancelar
            </button>
            <button
              onClick={handleSplit}
              disabled={savingSplit || !nuevoNombre.trim() || !nuevoLiderId}
              className="flex items-center gap-2 px-3 py-2 bg-emerald-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 active:scale-95 transition-all disabled:opacity-60"
            >
              {savingSplit ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Scissors size={14} />
              )}
              Dividir Grupo
            </button>
          </>
        }
      >
        <div className="space-y-4 mt-4">
          <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-100 dark:border-amber-500/30">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300 mb-1">
              Acción irreversible
            </p>
            <p className="text-sm text-amber-800 dark:text-amber-200">
              Esta operación transferirá aproximadamente la mitad de los miembros del grupo{' '}
              <strong>{selectedGroup?.grupo_nombre}</strong> al nuevo grupo. Asegúrate de que el
              nuevo líder esté preparado.
            </p>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">
              Nombre del Nuevo Grupo
            </label>
            <input
              type="text"
              value={nuevoNombre}
              onChange={(e) => setNuevoNombre(e.target.value)}
              placeholder="Ej: Grupo Norte (Hijo)"
              className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] block">
              Nuevo Líder
            </label>
            {loadingPersonas ? (
              <Skeleton className="h-10 rounded-lg" />
            ) : personasOptions.length > 0 ? (
              <select
                value={nuevoLiderId}
                onChange={(e) => setNuevoLiderId(e.target.value)}
                className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500 appearance-none"
              >
                <option value="">— Seleccionar líder —</option>
                {personasOptions.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.nombre_completo}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={nuevoLiderId}
                onChange={(e) => setNuevoLiderId(e.target.value)}
                placeholder="UUID de la persona líder"
                className="w-full bg-[hsl(var(--bg-muted))] dark:bg-black/20 border border-[hsl(var(--border-primary))] rounded-lg py-1.5 px-4 text-sm font-bold outline-none focus:ring-2 focus:ring-blue-500"
              />
            )}
            <p className="text-[10px] text-[hsl(var(--text-secondary))]">
              Selecciona una persona del grupo para liderar la nueva célula.
            </p>
          </div>
        </div>
      </WorkspaceDrawer>
    </EvangelismShell>
  );
}
