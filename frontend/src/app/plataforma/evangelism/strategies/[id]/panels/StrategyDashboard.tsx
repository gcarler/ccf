import type { Dispatch, SetStateAction } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart3, Calendar, ClipboardList, Copy, Home, Loader2, Plus, Share2, Trash2, Users } from 'lucide-react';
import ErrorBoundary from '@/components/ErrorBoundary';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { SessionRow, Strategy, StrategyGroup, StrategyMetrics } from '../../../types';
import type { CustomRole, FollowUpRecord } from '../strategyDetailShared';
import CustomRolesPanel from './CustomRolesPanel';

export interface AttendanceByGroupEntry {
  group: StrategyGroup;
  sessions: SessionRow[];
  latest: SessionRow | null;
}

interface StrategyDashboardProps {
  strategy: Strategy;
  id: string;
  token: string | null;
  canManage: boolean;
  activeTab: string;
  groups: StrategyGroup[];
  metrics: StrategyMetrics | null;
  sessionsLoading: boolean;
  attendanceByGroup: AttendanceByGroupEntry[];
  formatDate: (dateStr: string | null | undefined) => string;
  onOpenGroupDrawer: () => void;
  onOpenPersona: (group: StrategyGroup) => void;
  onRequestDeleteGroup: (id: string, name: string) => void;
  onOpenGroupAttendance: (group: StrategyGroup) => void;
  onOpenAttendance: (session: SessionRow) => void;
  onToggleHabilitacion: (session: SessionRow) => void;
  shareMenuId: string | null;
  onShareMenuToggle: (id: string) => void;
  shareGroupLink: (groupId: string, gName: string, via: 'copy' | 'whatsapp' | 'telegram') => void;
  customRoles: CustomRole[];
  loadingRoles: boolean;
  showRoleForm: boolean;
  setShowRoleForm: Dispatch<SetStateAction<boolean>>;
  newRoleName: string;
  setNewRoleName: Dispatch<SetStateAction<string>>;
  newRoleDesc: string;
  setNewRoleDesc: Dispatch<SetStateAction<string>>;
  editDefaultRoleId: string | null | undefined;
  setEditDefaultRoleId: Dispatch<SetStateAction<string | null | undefined>>;
  onCreateRole: () => void;
  onRequestDeleteRole: (role: CustomRole) => void;
  followUps: FollowUpRecord[];
  loadingFollowUps: boolean;
  onFollowUpsChanged: () => void;
}

export default function StrategyDashboard({
  strategy,
  id,
  token,
  canManage,
  activeTab,
  groups,
  metrics,
  sessionsLoading,
  attendanceByGroup,
  formatDate,
  onOpenGroupDrawer,
  onOpenPersona,
  onRequestDeleteGroup,
  onOpenGroupAttendance,
  onOpenAttendance,
  onToggleHabilitacion,
  shareMenuId,
  onShareMenuToggle,
  shareGroupLink,
  customRoles,
  loadingRoles,
  showRoleForm,
  setShowRoleForm,
  newRoleName,
  setNewRoleName,
  newRoleDesc,
  setNewRoleDesc,
  editDefaultRoleId,
  setEditDefaultRoleId,
  onCreateRole,
  onRequestDeleteRole,
  followUps,
  loadingFollowUps,
  onFollowUpsChanged,
}: StrategyDashboardProps) {
  const router = useRouter();

  return (
    <>
      {/* ── Grupos ── */}
      {activeTab === 'groups' && (
        <ErrorBoundary moduleName="Estrategia - Grupos" compact>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-[hsl(var(--text-primary))]">Grupos de esta estrategia</h2>
                {strategy.typology === 'relacional' && (
                  <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                    Config: {strategy.recurrence} · {strategy.day_of_week ? `Día: ${strategy.day_of_week}` : ''} {strategy.start_time ? `Hora: ${strategy.start_time}` : ''}
                  </p>
                )}
              </div>
              {canManage ? (
                <button onClick={onOpenGroupDrawer}
                  className="inline-flex items-center gap-1.5 px-3 h-8 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
                  <Plus size={14} />Nuevo grupo
                </button>
              ) : null}
            </div>
            {groups.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg">
                <Home size={32} className="text-[hsl(var(--text-secondary))] mb-2" />
                <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">Sin grupos aún</p>
                <p className="text-xs text-[hsl(var(--text-secondary))]">Crea el primer grupo para esta estrategia</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {groups.map(g => (
                  <div key={g.id}
                    role="button"
                    tabIndex={0}
                    className="group bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg p-4 hover:border-[hsl(var(--primary)/0.3)] dark:hover:border-[hsl(var(--primary)/0.5)] transition-all cursor-pointer relative"
                    onClick={() => canManage ? onOpenPersona(g) : router.push(`/plataforma/evangelism/groups/${g.id}`)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); (e.currentTarget as HTMLElement).click(); } }}>
                    {canManage ? (
                      <button onClick={e => { e.stopPropagation(); onRequestDeleteGroup(g.id, g.name); }}
                        className="absolute top-2 right-2 p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] dark:hover:bg-[hsl(var(--destructive)/0.15)] opacity-0 group-hover:opacity-100 transition-all z-10" title="Eliminar">
                        <Trash2 size={14} />
                      </button>
                    ) : null}
                    <button onClick={e => { e.stopPropagation(); router.push(`/plataforma/evangelism/groups/${g.id}`); }}
                      className="absolute top-2 right-8 p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] hover:bg-info-soft dark:hover:bg-[hsl(var(--info))]/20 opacity-0 group-hover:opacity-100 transition-all z-10" title="Ver detalle">
                      <Calendar size={14} />
                    </button>
                    {canManage ? (
                      <button onClick={e => { e.stopPropagation(); onOpenGroupAttendance(g); }}
                        className="absolute top-2 right-[3.25rem] p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--success))] hover:bg-[hsl(var(--success-muted))] dark:hover:bg-[hsl(var(--success)/0.15)] opacity-0 group-hover:opacity-100 transition-all z-10" title="Registrar asistencia">
                        <ClipboardList size={14} />
                      </button>
                    ) : null}
                    {/* Share button + dropdown */}
                    <div className="absolute top-2 right-[4.75rem] z-20">
                      <button
                        onClick={e => { e.stopPropagation(); onShareMenuToggle(g.id); }}
                        className="p-1 rounded text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--success))] hover:bg-[hsl(var(--success-muted))] dark:hover:bg-[hsl(var(--success)/0.15)] opacity-0 group-hover:opacity-100 transition-all"
                        title="Compartir enlace del grupo"
                      >
                        <Share2 size={14} />
                      </button>
                      {shareMenuId === g.id && (
                        <div
                          onClick={e => e.stopPropagation()}
                          className="absolute top-7 right-0 w-52 bg-[hsl(var(--bg-primary))] dark:bg-[#2a2b2d] border border-[hsl(var(--border-primary))] rounded-lg shadow-xl py-1"
                        >
                          <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-3 py-1.5">Compartir enlace del grupo</p>
                          <button onClick={() => shareGroupLink(g.id, g.name, 'copy')}
                            className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
                            <Copy size={12} className="shrink-0" /> Copiar enlace
                          </button>
                          <button onClick={() => shareGroupLink(g.id, g.name, 'whatsapp')}
                            className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
                            <span className="shrink-0 w-3 h-3 rounded-full bg-[hsl(var(--success))] inline-block" />WhatsApp
                          </button>
                          <button onClick={() => shareGroupLink(g.id, g.name, 'telegram')}
                            className="w-full text-left px-3 py-2 text-xs font-medium text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2">
                            <span className="shrink-0 w-3 h-3 rounded-full bg-[hsl(var(--info))] inline-block" />Telegram
                          </button>
                        </div>
                      )}
                    </div>
                    <h3 className="text-sm font-bold text-[hsl(var(--text-primary))] pr-28">{g.name}</h3>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">{g.zone || 'Sin zona'}</p>
                    <div className="flex items-center gap-3 mt-3 text-xs text-[hsl(var(--text-secondary))]">
                      <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[hsl(var(--bg-muted))]">
                        <Users size={12} />{g.personas_count} personas
                      </span>
                      {g.leader_name && <span>Líder: {g.leader_name}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ErrorBoundary>
      )}

      {/* ── Asistencia ── */}
      {activeTab === 'attendance' && (
        <ErrorBoundary moduleName="Estrategia - Asistencia" compact>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                Grupos — sesiones recientes
              </p>
              {sessionsLoading && <Loader2 size={14} className="animate-spin text-[hsl(var(--text-secondary))]" />}
            </div>

            {sessionsLoading && attendanceByGroup.length === 0 ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <div key={i} className="h-28 rounded-xl bg-[hsl(var(--bg-muted))] animate-pulse" />)}
              </div>
            ) : attendanceByGroup.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-10 border-2 border-dashed border-[hsl(var(--border-primary))] rounded-xl text-center">
                <ClipboardList size={28} className="text-[hsl(var(--text-secondary))] opacity-40" />
                <p className="text-sm font-semibold text-[hsl(var(--text-secondary))]">Sin sesiones registradas</p>
                <p className="text-xs text-[hsl(var(--text-secondary))] opacity-70">Crea sesiones en la pestaña Sesiones para poder reportar asistencia</p>
              </div>
            ) : (
              <div className="space-y-3">
                {attendanceByGroup.map(({ group: grp, sessions: grpSessions, latest }) => {
                  const isHabilitado = latest?.estado_habilitacion === 'HABILITADO';
                  return (
                    <div key={grp.id} className={`bg-[hsl(var(--bg-primary))] rounded-xl border overflow-hidden ${isHabilitado ? 'border-[hsl(var(--success)/0.3)] dark:border-[hsl(var(--success)/0.2)]' : 'border-[hsl(var(--border-primary))]'}`}>
                      {/* Cabecera del grupo */}
                      <div className={`flex items-center justify-between px-4 py-3 ${isHabilitado ? 'bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success)/0.1)]' : 'bg-[hsl(var(--bg-secondary))]'}`}>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            {isHabilitado && <span className="size-1.5 rounded-full bg-[hsl(var(--success))] animate-pulse shrink-0" />}
                            <p className="text-sm font-bold text-[hsl(var(--text-primary))] truncate">{grp.name}</p>
                          </div>
                          <div className="flex items-center gap-3 mt-0.5 text-xs text-[hsl(var(--text-secondary))]">
                            {grp.leader_name && <span>{grp.leader_name}</span>}
                            <span>{grp.personas_count} personas</span>
                          </div>
                        </div>
                        {latest && isHabilitado && canManage && (
                          <button
                            onClick={() => onOpenAttendance(latest)}
                            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide transition-all active:scale-95 bg-[hsl(var(--primary))] text-white hover:opacity-90 shadow-sm"
                          >
                            <ClipboardList size={12} />
                            Registrar
                          </button>
                        )}
                      </div>

                      {/* Lista de sesiones recientes del grupo */}
                      <div className="divide-y divide-[hsl(var(--border-primary))]">
                        {grpSessions.map(s => {
                          const dateStr = new Date(s.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', {
                            weekday: 'short', day: 'numeric', month: 'short',
                          });
                          const isClosed = s.estado_habilitacion === 'CERRADO' || s.estado_habilitacion === 'CANCELADA';
                          const habColor = s.estado_habilitacion === 'HABILITADO'
                            ? 'bg-[hsl(var(--success)/0.2)] text-[hsl(var(--success))] dark:bg-[hsl(var(--success)/0.15)] dark:text-[hsl(var(--success))]'
                            : s.estado_habilitacion === 'CANCELADA'
                              ? 'bg-[hsl(var(--destructive)/0.08)] text-[hsl(var(--destructive))] dark:bg-[hsl(var(--destructive)/0.15)]'
                              : s.estado_habilitacion === 'CERRADO'
                                ? 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/10 dark:text-[hsl(var(--text-secondary))]'
                                : 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))] dark:bg-[hsl(var(--warning)/0.15)] dark:text-[hsl(var(--warning))]';
                          return (
                            <div key={s.id} className="flex items-center gap-3 px-4 py-2.5 hover:bg-[hsl(var(--bg-muted))] transition-colors">
                              <div className="flex-1 min-w-0 flex items-center gap-2">
                                <span className={`shrink-0 px-1.5 py-0.5 rounded text-2xs font-bold uppercase tracking-wide ${habColor}`}>
                                  {s.estado_habilitacion ?? 'DESHABILITADO'}
                                </span>
                                <p className="text-sm text-[hsl(var(--text-secondary))] capitalize truncate">
                                  {dateStr}{s.topic ? ` · ${s.topic}` : ''}
                                </p>
                              </div>
                              {!isClosed && (
                                <div className="shrink-0 flex items-center gap-2">
                                  {canManage && s.estado_habilitacion !== 'HABILITADO' && (
                                    <button
                                      onClick={() => onToggleHabilitacion(s)}
                                      className="text-xs font-semibold text-[hsl(var(--warning))] hover:text-[hsl(var(--success))] transition-colors whitespace-nowrap"
                                    >
                                      Habilitar
                                    </button>
                                  )}
                                  {canManage && s.estado_habilitacion === 'HABILITADO' && (
                                    <button
                                      onClick={() => onOpenAttendance(s)}
                                      className="text-xs font-semibold text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] transition-colors whitespace-nowrap"
                                    >
                                      Reportar
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </ErrorBoundary>
      )}

      {/* ── Métricas ── */}
      {activeTab === 'metrics' && (
        <ErrorBoundary moduleName="Estrategia - Metricas">
          <div className="space-y-4">
            <div className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-xl p-8 flex flex-col items-center text-center gap-4">
              <div className="p-4 rounded-2xl bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--info)/0.15)]">
                <BarChart3 size={36} className="text-[hsl(var(--primary))]" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[hsl(var(--text-primary))] mb-1">Panel de métricas</h3>
                <p className="text-sm text-[hsl(var(--text-secondary))] max-w-sm">
                  Tendencias de asistencia, embudo de roles, mapa de calor, alertas tempranas y velocidad ministerial en tiempo real.
                </p>
              </div>
              <button
                onClick={() => router.push(`/plataforma/evangelism/strategies/${id}/analytics`)}
                className="flex items-center gap-2 px-5 py-2.5 bg-[hsl(var(--primary))] hover:opacity-90 text-white rounded-lg text-sm font-semibold transition-all shadow-sm"
              >
                <BarChart3 size={15} />
                Abrir dashboard analítico
              </button>
            </div>
            {metrics && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'Grupos', value: metrics.summary.total_groups },
                  { label: 'Sesiones', value: metrics.summary.total_sessions },
                  { label: 'Primera vez', value: metrics.summary.total_first_timers, cls: 'text-[hsl(var(--success))]' },
                  { label: 'Inasistencias', value: metrics.summary.total_absences, cls: 'text-[hsl(var(--destructive))]' },
                ].map(stat => (
                  <div key={stat.label} className="bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
                    <p className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">{stat.label}</p>
                    <p className={`text-2xl font-black mt-1 ${stat.cls || 'text-[hsl(var(--text-primary))]'}`}>{stat.value}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </ErrorBoundary>
      )}

      {/* Metadata */}
      {activeTab === 'overview' && (
        <ErrorBoundary moduleName="Estrategia - Informacion" compact>
          <>
            <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
              <h3 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-3">Información</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">ID</p><p className="text-[hsl(var(--text-primary))] font-bold">{strategy.codigo ? strategy.codigo : `#${strategy.id}`}</p></div>
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">Inicio</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.start_date)}</p></div>
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">Fin</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.end_date)}</p></div>
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">Actualización</p><p className="text-[hsl(var(--text-primary))] font-bold">{formatDate(strategy.updated_at)}</p></div>
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">Clase</p><p className="text-[hsl(var(--text-primary))] font-bold capitalize">{strategy.clase_raiz || strategy.typology || '—'}</p></div>
                <div><p className="text-[hsl(var(--text-secondary))] font-medium">Activa</p><p className={`font-bold ${strategy.activa ? 'text-[hsl(var(--success))]' : 'text-[hsl(var(--text-secondary))]'}`}>{strategy.activa ? 'Sí' : 'No'}</p></div>
              </div>
            </div>

            {/* ── Roles Personalizados ── */}
            <CustomRolesPanel
              customRoles={customRoles}
              loadingRoles={loadingRoles}
              showRoleForm={showRoleForm}
              setShowRoleForm={setShowRoleForm}
              newRoleName={newRoleName}
              setNewRoleName={setNewRoleName}
              newRoleDesc={newRoleDesc}
              setNewRoleDesc={setNewRoleDesc}
              editDefaultRoleId={editDefaultRoleId}
              setEditDefaultRoleId={setEditDefaultRoleId}
              canManage={canManage}
              onCreateRole={onCreateRole}
              onRequestDeleteRole={onRequestDeleteRole}
            />

            {/* ── Seguimiento Pendiente ── */}
            <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Seguimiento Pendiente</h3>
                <span className="text-2xs font-bold px-2 py-0.5 bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))] rounded-full">
                  {followUps.filter(f => !f.estado_completado).length}
                </span>
              </div>
              {loadingFollowUps ? (
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">Cargando...</p>
              ) : followUps.filter(f => !f.estado_completado).length === 0 ? (
                <p className="text-xs text-[hsl(var(--text-secondary))] italic">Sin seguimientos pendientes</p>
              ) : (
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {followUps.filter(f => !f.estado_completado).slice(0, 10).map(f => (
                    <div key={f.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))]">
                      <div className="flex items-center gap-2">
                        <span className={`text-2xs font-bold px-1.5 py-0.5 rounded-full ${(f.tipo ?? '').toLowerCase().includes('llamada') ? 'bg-[hsl(var(--info-muted))] text-[hsl(var(--info))]' : (f.tipo ?? '').toLowerCase().includes('visita') ? 'bg-[hsl(var(--success-muted))] text-[hsl(var(--success))]' : (f.tipo ?? '').toLowerCase().includes('oracion') ? 'bg-[hsl(var(--warning-muted))] text-[hsl(var(--warning))]' : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))]'}`}>
                          {f.tipo}
                        </span>
                        <span className="text-xs text-[hsl(var(--text-secondary))]">{f.observaciones || '—'}</span>
                      </div>
                      {canManage ? (
                        <button onClick={async () => {
                          try {
                            await apiFetch(`/evangelism/follow-up/${f.id}`, {
                              method: 'PATCH', token, silent: true,
                              body: { estado_completado: true, fecha_seguimiento: new Date().toISOString() },
                            });
                            toast.success('Seguimiento completado');
                            onFollowUpsChanged();
                          } catch { toast.error('Error al actualizar'); }
                        }} className="px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))] hover:bg-[hsl(var(--success-muted))] dark:hover:bg-[hsl(var(--success)/0.15)] rounded transition-colors">
                          Completar
                        </button>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        </ErrorBoundary>
      )}
    </>
  );
}
