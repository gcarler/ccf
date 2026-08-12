import { AlertCircle, CheckCircle2, ClipboardList, Plus, Search, Sparkles, Trash2, Users, X } from 'lucide-react';
import ErrorBoundary from '@/components/ErrorBoundary';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type {
  BulkHabilitacionResponse,
  GenerateSessionsResponse,
  SessionRow,
  Strategy,
  StrategyGroup,
} from '../../../types';
import { getErrorMessage } from '../../../utils';

export type SessionHabFilter = 'all' | 'HABILITADO' | 'DESHABILITADO' | 'CERRADO';

interface SessionsSectionProps {
  strategy: Strategy;
  id: string;
  token: string | null;
  canManage: boolean;
  groups: StrategyGroup[];
  sessions: SessionRow[];
  filteredSessions: SessionRow[];
  sessionsLoading: boolean;
  search: string;
  onSearchChange: (v: string) => void;
  groupFilter: string;
  onGroupFilterChange: (v: string) => void;
  habFilter: SessionHabFilter;
  onHabFilterChange: (v: SessionHabFilter) => void;
  months: string[];
  monthFilter: string;
  onMonthFilterChange: (v: string) => void;
  groupName: (groupId: string) => string;
  sessionMenuId: string | null;
  onMenuToggle: (id: string) => void;
  onToggleHabilitacion: (s: SessionRow) => void;
  onOpenAttendance: (s: SessionRow) => void;
  onRequestDelete: (id: string) => void;
  onBlockAll: () => void;
  onNewSession: () => void;
  onSessionsChanged: () => void;
}

export default function SessionsSection({
  strategy,
  id,
  token,
  canManage,
  groups,
  sessions,
  filteredSessions,
  sessionsLoading,
  search,
  onSearchChange,
  groupFilter,
  onGroupFilterChange,
  habFilter,
  onHabFilterChange,
  months,
  monthFilter,
  onMonthFilterChange,
  groupName,
  sessionMenuId,
  onMenuToggle,
  onToggleHabilitacion,
  onOpenAttendance,
  onRequestDelete,
  onBlockAll,
  onNewSession,
  onSessionsChanged,
}: SessionsSectionProps) {
  return (
    <ErrorBoundary moduleName="Estrategia - Sesiones">
      <div className="space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">Registro de sesiones</h2>
          <div className="flex items-center gap-2 flex-wrap">
            {canManage && strategy.recurrence && strategy.start_date && strategy.end_date && (
              <button onClick={async () => {
                const btn = toast.loading('Generando sesiones...');
                try {
                  const res = await apiFetch<GenerateSessionsResponse>(`/evangelism/strategies/${id}/generate-sessions`, { method: 'POST', token, silent: true });
                  toast.dismiss(btn);
                  if (res.message) {
                    toast.info(res.message);
                  } else {
                    toast.success(`Sesiones generadas: ${res.sessions_per_group || ''} por grupo (${res.total_sessions_created} totales)`);
                  }
                  onSessionsChanged();
                } catch (error: unknown) {
                  toast.dismiss(btn);
                  toast.error('Error: ' + getErrorMessage(error, 'Verifica fechas y frecuencia'));
                }
              }}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-[hsl(var(--border-primary))] dark:border-white/20 text-[hsl(var(--text-secondary))] text-xs font-semibold hover:bg-[hsl(var(--bg-muted))] transition-colors">
                <Sparkles size={14} />Generar sesiones
              </button>
            )}
            {canManage ? (
              <button onClick={async () => {
                try {
                  const res = await apiFetch<BulkHabilitacionResponse>(`/evangelism/strategies/${id}/habilitar-todas`, { method: 'POST', token, silent: true });
                  toast.success(`${res.sesiones_habilitadas} sesiones habilitadas`);
                  onSessionsChanged();
                } catch { toast.error('Error al habilitar sesiones'); }
              }}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-[hsl(var(--success)/0.4)] dark:border-[hsl(var(--success)/0.4)] text-[hsl(var(--success))] text-xs font-semibold hover:bg-[hsl(var(--success-muted))] dark:hover:bg-[hsl(var(--success)/0.15)] transition-colors">
                <CheckCircle2 size={14} />Habilitar sesiones
              </button>
            ) : null}
            {canManage ? (
              <button onClick={onBlockAll}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg border border-[hsl(var(--destructive)/0.3)] dark:border-[hsl(var(--destructive)/0.4)] text-[hsl(var(--destructive))] text-xs font-semibold hover:bg-[hsl(var(--destructive)/0.08)] dark:hover:bg-[hsl(var(--destructive)/0.15)] transition-colors">
                <AlertCircle size={14} />Bloquear sesiones
              </button>
            ) : null}
            {canManage ? (
              <button onClick={onNewSession}
                className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:opacity-90 transition-colors">
                <Plus size={14} />Nueva sesión
              </button>
            ) : null}
          </div>
        </div>

        {/* Buscador + filtros */}
        <div className="flex flex-col gap-2">
          {/* Buscador */}
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] pointer-events-none" />
            <input
              value={search}
              onChange={e => onSearchChange(e.target.value)}
              placeholder="Buscar por tema, grupo o mes (ej. 2025-03)…"
              className="w-full pl-8 pr-8 h-8 text-xs rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--info))]"
            />
            {search && (
              <button onClick={() => onSearchChange('')} className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))]">
                <X size={12} />
              </button>
            )}
          </div>
          {/* Filtros en fila */}
          <div className="flex items-center gap-2 flex-wrap">
            {groups.length > 1 && (
              <select
                value={groupFilter}
                onChange={e => onGroupFilterChange(e.target.value)}
                className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--info))]">
                <option value="all">Todos los grupos</option>
                {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
            )}
            <select
              value={habFilter}
              onChange={e => onHabFilterChange(e.target.value as SessionHabFilter)}
              className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--info))]">
              <option value="all">Todas las habilitaciones</option>
              <option value="HABILITADO">Abiertas</option>
              <option value="DESHABILITADO">Bloqueadas</option>
              <option value="CERRADO">Cerradas</option>
            </select>
            {months.length > 1 && (
              <select
                value={monthFilter}
                onChange={e => onMonthFilterChange(e.target.value)}
                className="h-7 px-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-xs text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--info))]">
                <option value="all">Todos los meses</option>
                {months.map(m => {
                  const [y, mo] = m.split('-');
                  const label = new Date(Number(y), Number(mo) - 1, 1).toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
                  return <option key={m} value={m}>{label}</option>;
                })}
              </select>
            )}
            {/* Contador */}
            <span className="ml-auto text-xs text-[hsl(var(--text-secondary))]">
              {filteredSessions.length !== sessions.length
                ? `${filteredSessions.length} de ${sessions.length} sesiones`
                : `${sessions.length} sesión${sessions.length !== 1 ? 'es' : ''}`}
            </span>
          </div>
        </div>

        {sessionsLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => <div key={i} className="h-14 bg-[hsl(var(--bg-muted))] rounded-lg animate-pulse" />)}
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg">
            <ClipboardList size={32} className="text-[hsl(var(--text-secondary))] mb-2" />
            <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">
              {sessions.length === 0 ? 'Sin sesiones registradas' : 'Sin sesiones con esos filtros'}
            </p>
            <p className="text-xs text-[hsl(var(--text-secondary))]">
              {sessions.length === 0 ? 'Registra la primera sesión semanal' : 'Prueba ajustando la búsqueda o los filtros'}
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredSessions.map(s => (
              <div key={s.id} className={`flex items-center gap-3 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border rounded-lg px-4 py-3 transition-all ${
                s.estado_habilitacion === 'HABILITADO'
                  ? 'border-[hsl(var(--success)/0.5)] dark:border-[hsl(var(--success)/0.4)]'
                  : s.estado_habilitacion === 'CERRADO'
                    ? 'border-[hsl(var(--border-primary))] opacity-60'
                    : 'border-[hsl(var(--border-primary))]'
              }`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold text-[hsl(var(--text-primary))]">
                      {new Date(s.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'short', year: 'numeric' })}
                    </span>
                    <span className="px-1.5 py-0.5 rounded text-2xs font-semibold bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]">
                      {s.status}
                    </span>
                    {/* Badge de habilitación */}
                    {s.estado_habilitacion === 'HABILITADO' && (
                      <span className="px-1.5 py-0.5 rounded text-2xs font-bold bg-[hsl(var(--success)/0.2)] text-[hsl(var(--success))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]">Abierta</span>
                    )}
                    {s.estado_habilitacion === 'CERRADO' && (
                      <span className="px-1.5 py-0.5 rounded text-2xs font-bold bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">Cerrada</span>
                    )}
                    {(!s.estado_habilitacion || s.estado_habilitacion === 'DESHABILITADO') && (
                      <span className="px-1.5 py-0.5 rounded text-2xs font-bold bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] dark:bg-[hsl(var(--warning)/0.15)] dark:text-[hsl(var(--warning))]">Bloqueada</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                    <span>{groupName(String(s.grupo_id))}</span>
                    {s.topic && <span>· {s.topic}</span>}
                    {s.offering_amount != null && <span>· Ofrenda: ${s.offering_amount.toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* Toggle habilitación individual */}
                  {canManage ? (
                    <button
                      onClick={() => onToggleHabilitacion(s)}
                      title={s.estado_habilitacion === 'HABILITADO' ? 'Bloquear sesión' : 'Habilitar sesión'}
                      className={`w-7 h-7 flex items-center justify-center rounded-lg transition-colors text-xs font-bold ${
                        s.estado_habilitacion === 'HABILITADO'
                          ? 'bg-[hsl(var(--success)/0.2)] text-[hsl(var(--success))] hover:bg-[hsl(var(--destructive)/0.08)] hover:text-[hsl(var(--destructive))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]'
                          : 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] hover:bg-[hsl(var(--success)/0.2)] hover:text-[hsl(var(--success))] dark:bg-[hsl(var(--warning)/0.15)] dark:text-[hsl(var(--warning))]'
                      }`}
                    >
                      {s.estado_habilitacion === 'HABILITADO' ? '✓' : '○'}
                    </button>
                  ) : null}
                  {canManage ? (
                    <button onClick={() => onOpenAttendance(s)}
                      className="inline-flex items-center gap-1.5 px-3 h-7 rounded-lg bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-xs font-semibold hover:bg-[hsl(var(--info-muted))] hover:text-[hsl(var(--info))] dark:hover:bg-[hsl(var(--info)/0.15)] dark:hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap">
                      <Users size={12} />Asistencia
                    </button>
                  ) : null}
                  {canManage ? (
                    <div className="relative">
                      <button onClick={() => onMenuToggle(String(s.id))}
                        className="w-7 h-7 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10 hover:text-[hsl(var(--text-secondary))] dark:hover:text-white transition-colors">
                        <span className="text-base leading-none">⋯</span>
                      </button>
                      {sessionMenuId === String(s.id) && (
                        <div className="absolute right-0 top-8 z-20 bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-[hsl(var(--border-primary))] rounded-lg shadow-lg py-1 min-w-[130px]">
                          <button
                            onClick={() => onRequestDelete(String(s.id))}
                            className="w-full text-left px-3 py-2 text-xs text-[hsl(var(--destructive))] dark:text-[hsl(var(--destructive))] hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2">
                            <Trash2 size={12} />Eliminar sesión
                          </button>
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
}
