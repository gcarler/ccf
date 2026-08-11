import dynamic from 'next/dynamic';
import { Calendar, Share2, Trash2, Users } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { SessionRow, Strategy, StrategyGroup } from '../../../types';
import { formatLocalDate } from '../../../utils';

const UniversalCalendarView = dynamic(() => import('@/components/ui/UniversalCalendarView'), { ssr: false });
const UniversalGanttView = dynamic(() => import('@/components/ui/UniversalGanttView'), { ssr: false });
const UniversalTableView = dynamic(() => import('@/components/ui/UniversalTableView'), { ssr: false });
const UniversalWikiView = dynamic(() => import('@/components/ui/UniversalWikiView'), { ssr: false });

const isStrategyGroup = (value: unknown): value is StrategyGroup =>
  typeof value === 'object' && value !== null && 'id' in value && 'name' in value;
const isSessionRow = (value: unknown): value is SessionRow =>
  typeof value === 'object' && value !== null && 'id' in value && 'grupo_id' in value;

export type TableSubTab = 'sessions' | 'groups';

interface StrategyViewsProps {
  strategy: Strategy;
  id: string;
  token: string | null;
  canManage: boolean;
  activeTab: string;
  viewType: string;
  tableSubTab: TableSubTab;
  onTableSubTabChange: (v: TableSubTab) => void;
  groups: StrategyGroup[];
  sessions: SessionRow[];
  groupsLoading: boolean;
  sessionsLoading: boolean;
  groupName: (groupId: string) => string;
  formatDate: (dateStr: string | null | undefined) => string;
  onAddGroup: () => void;
  onOpenPersona: (group: StrategyGroup) => void;
  onNavigateGroup: (id: string | number) => void;
  shareGroupLink: (groupId: string, gName: string, via: 'copy' | 'whatsapp' | 'telegram') => void;
  onOpenAttendance: (session: SessionRow) => void;
  onToggleHabilitacion: (session: SessionRow) => void;
  onRequestDeleteSession: (id: string) => void;
  onGroupsChanged: () => void;
  onSessionsChanged: () => void;
}

export default function StrategyViews({
  strategy,
  id,
  token,
  canManage,
  activeTab,
  viewType,
  tableSubTab,
  onTableSubTabChange,
  groups,
  sessions,
  groupsLoading,
  sessionsLoading,
  groupName,
  formatDate,
  onAddGroup,
  onOpenPersona,
  onNavigateGroup,
  shareGroupLink,
  onOpenAttendance,
  onToggleHabilitacion,
  onRequestDeleteSession,
  onGroupsChanged,
  onSessionsChanged,
}: StrategyViewsProps) {
  return (
    <>
      {/* ── View: Calendar ── */}
      {viewType === 'calendar' && (
        <UniversalCalendarView
          title={`Sesiones — ${strategy.name}`}
          events={sessions.map(s => ({
            id: String(s.id), title: s.topic || `Sesión #${s.id}`,
            date: s.session_date,
            color: s.status === 'Realizada' ? 'emerald' : 'blue' as const,
            location: groupName(s.grupo_id),
          }))}
        />
      )}

      {/* ── View: Gantt ── */}
      {viewType === 'gantt' && (
        <UniversalGanttView moduleName="Evangelismo"
          items={[
            ...groups.map(g => ({
              id: String(g.id), name: g.name, title: g.name,
              start_date: formatLocalDate(new Date()),
              end_date: formatLocalDate(new Date(Date.now() + 30 * 86400000)),
              progress: Math.min(g.personas_count * 20, 100),
              color: 'blue' as const, subtitle: `${g.personas_count} personas`,
            })),
            ...sessions.map(s => ({
              id: `s-${s.id}`, title: s.topic || `Sesión #${s.id}`,
              start_date: s.session_date, end_date: s.session_date,
              progress: s.status === 'Realizada' ? 100 : 0,
              color: s.status === 'Realizada' ? 'emerald' as const : 'blue' as const,
              subtitle: groupName(s.grupo_id),
            })),
          ]}
        />
      )}

      {/* ── View: Wiki ── */}
      {viewType === 'wiki' && (
        <UniversalWikiView moduleName="evangelism" storageKey={`strategy_${id}`} />
      )}

      {/* ── View: Kanban ── */}
      {viewType === 'kanban' && (activeTab === 'sessions' || activeTab === 'overview') && (
        <div className="flex gap-3 overflow-x-auto pb-4">
          {['Pendiente', 'Programada', 'Realizada'].map(label => {
            const colors: Record<string, string> = { 'Pendiente': 'hsl(var(--warning))', 'Programada': 'hsl(var(--info))', 'Realizada': 'hsl(var(--success))' };
            const filtered = sessions.filter(s => s.status === label);
            return (
              <div key={label} className="min-w-[280px] w-[280px] shrink-0">
                <div className="rounded-lg p-3 mb-2 text-xs font-bold uppercase" style={{ background: `${colors[label]}15`, color: colors[label] }}>
                  {label} ({filtered.length})
                </div>
                <div className="space-y-2">
                  {filtered.map(s => (
                    <div key={s.id} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] p-3">
                      <p className="text-sm font-semibold text-[hsl(var(--text-primary))]">{s.topic || `Sesión #${s.id}`}</p>
                      <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{groupName(s.grupo_id)}</p>
                      <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{formatDate(s.session_date)}</p>
                    </div>
                  ))}
                  {filtered.length === 0 && <p className="text-xs text-[hsl(var(--text-secondary))] p-3">Sin sesiones</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── View: Table (ag-grid, editable como Airtable) ── */}
      {viewType === 'table' && (
        <div className="flex flex-col gap-3">
          {/* Sub-tab switcher */}
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={() => onTableSubTabChange('groups')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                tableSubTab === 'groups'
                  ? 'bg-[hsl(var(--primary))] text-white'
                  : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
              }`}
            >
              Grupos ({groups.length})
            </button>
            <button
              onClick={() => { onTableSubTabChange('sessions'); if (sessions.length === 0) onSessionsChanged(); }}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
                tableSubTab === 'sessions'
                  ? 'bg-[hsl(var(--primary))] text-white'
                  : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
              }`}
            >
              Sesiones ({sessions.length})
            </button>
          </div>

          {/* Groups table */}
          {tableSubTab === 'groups' && (
            <div className="h-[calc(100vh-280px)]">
              <UniversalTableView
                key="groups-table"
                viewName={`strategy_groups_${id}`}
                data={groups}
                isLoading={groupsLoading}
                emptyMessage="Sin grupos en esta estrategia"
                onAddItem={canManage ? () => onAddGroup() : undefined}
                onUpdateItem={canManage ? async (rowId, field, value) => {
                  const group = groups.find(g => g.id === rowId);
                  if (!group) return false;
                  try {
                    await apiFetch(`/evangelism/grupos/${rowId}`, {
                      method: 'PUT', token, silent: true,
                      body: { [field]: value },
                    });
                    onGroupsChanged();
                    toast.success('Grupo actualizado');
                    return true;
                  } catch {
                    toast.error('Error al actualizar');
                    return false;
                  }
                } : undefined}
                columns={[
                  {
                    key: 'name',
                    label: 'Nombre',
                    type: 'text',
                    editable: canManage,
                  },
                  {
                    key: 'personas_count',
                    label: 'Personas',
                    type: 'number',
                    width: '95',
                    editable: false,
                    filterable: true,
                    render: (v: unknown) => (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-xs font-semibold">
                        <Users size={10} />{String(v ?? '—')}
                      </span>
                    ),
                  },
                  {
                    key: 'leader_name',
                    label: 'Líder',
                    type: 'user',
                    editable: false,
                  },
                  {
                    key: 'zone',
                    label: 'Zona',
                    type: 'text',
                    editable: canManage,
                  },
                  {
                    key: 'capacity',
                    label: 'Capacidad',
                    type: 'number',
                    width: '100',
                    editable: false,
                  },
                  {
                    key: 'status',
                    label: 'Estado',
                    type: 'status',
                    width: '110',
                    editable: false,
                  },
                  {
                    key: '_acciones',
                    label: '',
                    type: 'text',
                    width: '150',
                    editable: false,
                    filterable: false,
                    hidden: !canManage,
                    render: (_: unknown, item) => isStrategyGroup(item) ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); onOpenPersona(item); }}
                          className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-2xs font-semibold hover:bg-[hsl(var(--info-muted))] hover:text-[hsl(var(--info))] dark:hover:bg-[hsl(var(--info)/0.15)] dark:hover:text-[hsl(var(--primary))] transition-colors"
                        >
                          <Users size={10} /> Personas
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); onNavigateGroup(item.id); }}
                          className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-2xs font-semibold hover:bg-[hsl(var(--info-muted))] hover:text-[hsl(var(--info))] dark:hover:bg-[hsl(var(--info)/0.15)] dark:hover:text-[hsl(var(--primary))] transition-colors"
                        >
                          <Calendar size={10} /> Detalle
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); shareGroupLink(item.id, item.name, 'whatsapp'); }}
                          title="Compartir por WhatsApp"
                          className="w-6 h-6 inline-flex items-center justify-center rounded bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] hover:bg-[hsl(var(--success)/0.2)] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))] transition-colors"
                        >
                          <Share2 size={10} />
                        </button>
                      </div>
                    ) : null,
                  },
                ]}
              />
            </div>
          )}

          {/* Sessions table */}
          {tableSubTab === 'sessions' && (
            <div className="h-[calc(100vh-280px)]">
              <UniversalTableView
                key="sessions-table"
                viewName={`strategy_sessions_${id}`}
                data={sessions.map(s => ({
                  ...s,
                  __displayName: s.topic || `Sesión #${s.id}`,
                  grupo_nombre: groupName(s.grupo_id),
                }))}
                isLoading={sessionsLoading}
                emptyMessage="Sin sesiones registradas"
                onUpdateItem={canManage ? async (rowId, field, value) => {
                  const actualField = field === '__displayName' ? 'topic' : field;
                  try {
                    await apiFetch(`/evangelism/sessions/${rowId}`, {
                      method: 'PUT', token, silent: true,
                      body: { [actualField]: value },
                    });
                    onSessionsChanged();
                    toast.success('Sesión actualizada');
                    return true;
                  } catch {
                    toast.error('Error al actualizar');
                    return false;
                  }
                } : undefined}
                columns={[
                  {
                    key: '__displayName',
                    label: 'Tema / Sesión',
                    type: 'text',
                    editable: canManage,
                  },
                  {
                    key: 'grupo_nombre',
                    label: 'Grupo',
                    type: 'text',
                    width: '130',
                    editable: false,
                  },
                  {
                    key: 'session_date',
                    label: 'Fecha',
                    type: 'date',
                    width: '110',
                    editable: false,
                  },
                  {
                    key: 'status',
                    label: 'Estado',
                    type: 'status',
                    width: '120',
                    editable: false,
                  },
                  {
                    key: 'estado_habilitacion',
                    label: 'Habilitación',
                    type: 'status',
                    width: '120',
                    editable: false,
                  },
                  {
                    key: '_acciones',
                    label: '',
                    type: 'text',
                    width: '160',
                    editable: false,
                    filterable: false,
                    render: (_: unknown, item) => isSessionRow(item) ? (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => { e.stopPropagation(); onOpenAttendance(item); }}
                          className="inline-flex items-center gap-1 px-2 h-6 rounded bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] text-2xs font-semibold hover:bg-[hsl(var(--info-muted))] hover:text-[hsl(var(--info))] dark:hover:bg-[hsl(var(--info)/0.15)] dark:hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap"
                        >
                          <Users size={10} /> Asistencia
                        </button>
                        {item.estado_habilitacion !== 'CERRADO' && item.estado_habilitacion !== 'CANCELADA' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); onToggleHabilitacion(item); }}
                            title={item.estado_habilitacion === 'HABILITADO' ? 'Cerrar sesión' : 'Abrir sesión'}
                            className={`w-6 h-6 inline-flex items-center justify-center rounded font-bold text-xs transition-colors ${
                              item.estado_habilitacion === 'HABILITADO'
                                ? 'bg-[hsl(var(--success)/0.2)] text-[hsl(var(--success))] hover:bg-[hsl(var(--destructive)/0.08)] hover:text-[hsl(var(--destructive))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]'
                                : 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] hover:bg-[hsl(var(--success)/0.2)] hover:text-[hsl(var(--success))] dark:bg-[hsl(var(--warning)/0.15)] dark:text-[hsl(var(--warning))]'
                            }`}
                          >
                            {item.estado_habilitacion === 'HABILITADO' ? '✓' : '○'}
                          </button>
                        )}
                        <button
                          onClick={(e) => { e.stopPropagation(); onRequestDeleteSession(item.id); }}
                          className="w-6 h-6 inline-flex items-center justify-center rounded text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--destructive)/0.08)] hover:text-[hsl(var(--destructive))] dark:hover:bg-[hsl(var(--destructive)/0.15)] transition-colors"
                          title="Eliminar"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    ) : null,
                  },
                ]}
              />
            </div>
          )}
        </div>
      )}

      {/* ── View: List (tab-aware) ── */}
      {viewType === 'list' && (
        <div className="space-y-1">
          {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
            <div key={`g-${g.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-all">
              <div className="w-8 h-8 rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.15)] flex items-center justify-center shrink-0"><Users size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{g.name}</p>
                <p className="text-xs text-[hsl(var(--text-secondary))]">{g.personas_count} personas{g.zone ? ` · ${g.zone}` : ''}</p>
              </div>
              <span className="px-2 py-0.5 rounded text-2xs font-bold bg-[hsl(var(--success-muted))] text-[hsl(var(--success))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]">Grupo</span>
            </div>
          ))}
          {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
            <div key={`s-${s.id}`} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 transition-all">
              <div className="w-8 h-8 rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.15)] flex items-center justify-center shrink-0"><Calendar size={14} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-[hsl(var(--text-primary))] truncate">{s.topic || `Sesión #${s.id}`}</p>
                <p className="text-xs text-[hsl(var(--text-secondary))]">{groupName(s.grupo_id)} · {formatDate(s.session_date)}</p>
              </div>
              <span className="px-2 py-0.5 rounded text-2xs font-bold" style={{ backgroundColor: s.status === 'Realizada' ? 'hsl(var(--success)/0.125)' : '#3B82F620', color: s.status === 'Realizada' ? 'hsl(var(--success))' : 'hsl(var(--info))' }}>{s.status}</span>
            </div>
          ))}
        </div>
      )}

      {/* ── View: Grid (tab-aware) ── */}
      {viewType === 'grid' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {(activeTab === 'groups' || activeTab === 'overview') && groups.map(g => (
            <div key={`g-${g.id}`} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.15)] flex items-center justify-center"><Users size={12} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
                <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">GRUPO</span>
              </div>
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{g.name}</h3>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{g.zone || 'Sin zona'}</p>
              <span className="text-xs font-medium text-[hsl(var(--text-secondary))] mt-3 block">{g.personas_count} personas</span>
            </div>
          ))}
          {(activeTab === 'sessions' || activeTab === 'overview') && sessions.map(s => (
            <div key={`s-${s.id}`} className="rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.15)] flex items-center justify-center"><Calendar size={12} className="text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" /></div>
                <span className="text-xs font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">SESIÓN</span>
              </div>
              <h3 className="text-sm font-bold text-[hsl(var(--text-primary))]">{s.topic || `Sesión #${s.id}`}</h3>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{groupName(s.grupo_id)}</p>
              <div className="flex items-center justify-between mt-3">
                <span className="text-xs text-[hsl(var(--text-secondary))]">{formatDate(s.session_date)}</span>
                <span className="px-1.5 py-0.5 rounded text-2xs font-bold" style={{ backgroundColor: s.status === 'Realizada' ? 'hsl(var(--success)/0.125)' : '#3B82F620', color: s.status === 'Realizada' ? 'hsl(var(--success))' : 'hsl(var(--info))' }}>{s.status}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
