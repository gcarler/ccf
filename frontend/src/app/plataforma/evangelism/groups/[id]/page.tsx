'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import ErrorBoundary from '@/components/ErrorBoundary';
import { Activity, Home, Loader2, UserPlus } from 'lucide-react';
import GroupHeader from './panels/GroupHeader';
import GroupMonitoringPanel from './panels/GroupMonitoringPanel';
import GroupAttendeeList from './panels/GroupAttendeeList';
import GroupAddAttendeeDrawer from './panels/GroupAddAttendeeDrawer';
import { useGroupDetailPage } from './useGroupDetailPage';

function GroupDetailPage() {
  const params = useParams();
  const id = params?.id as string | undefined;
  const {
    // State - house
    house, loading, loadError,
    // State - active session + attendance
    activeSession, attendance, loadingAtt, savingReport,
    activeSessionEnabled,
    // Persona selector
    showAddAttendee, setShowAddAttendee,
    personaQuery, setPersonaQuery,
    setRemoteQuery,
    remoteLoading,
    saving, selectedIds, setSelectedIds,
    filteredPersonas,
    // Report form state
    reportTopic, setReportTopic,
    reportOfferingAmount, setReportOfferingAmount,
    reportNotes, setReportNotes,
    reportNoveltyType, setReportNoveltyType,
    reportNoveltyDetail, setReportNoveltyDetail,
    reportCancellationReason, setReportCancellationReason,
    reportStatus, setReportStatus,
    reportPersonas, setReportPersonas,
    // Persona creation
    isCreatingPersona, setIsCreatingPersona,
    newPersonaForm, setNewPersonaForm,
    creatingPersona,
    // Permission
    canManageEvangelism,
    // Handlers
    handleSaveAttendance, handleCreatePersona, handleSaveReport,
    // Router
    router,
  } = useGroupDetailPage(id);

  if (loading) return (
    <EvangelismShell breadcrumbs={[{ label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home }, { label: '...', icon: Home }]}>
      <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin text-[hsl(var(--primary))]" size={40} /></div>
    </EvangelismShell>
  );

  if (loadError) return (
    <EvangelismShell breadcrumbs={[{ label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home }]}>
      <div className="p-4 text-center text-[hsl(var(--text-secondary))]">
        <p className="mb-4">No se pudo cargar el grupo.</p>
        <Link href="/plataforma/evangelism/groups" className="text-[hsl(var(--primary))] underline">Volver a grupos</Link>
      </div>
    </EvangelismShell>
  );

  if (!house) return (
    <EvangelismShell breadcrumbs={[{ label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home }]}>
      <div className="p-4 text-center text-[hsl(var(--text-secondary))]">
        <p className="mb-4">Grupo no encontrado.</p>
        <Link href="/plataforma/evangelism/groups" className="text-[hsl(var(--primary))] underline">Volver a grupos</Link>
      </div>
    </EvangelismShell>
  );

  const avgAttendance = house.total_sessions > 0 ? Math.round(house.total_attendance / house.total_sessions) : 0;
  void canManageEvangelism; // disponible para uso futuro (ej. bloquear acciones); hoy no se consume en el page para evitar warnings TS6133.

  return (
    <EvangelismShell breadcrumbs={[
      { label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home },
      { label: house.name, icon: Home }
    ]}>
      <main className="flex-1 overflow-y-auto">
        {/* Page Header */}
        <div className="px-3 pt-8 pb-6 border-b border-[hsl(var(--border-primary))]">
          <GroupHeader house={house} avgAttendance={avgAttendance} onBack={() => router.back()} />
        </div>

        <div className="p-4">
          {/* ATTENDANCE PANEL */}
          <ErrorBoundary moduleName="Grupo - Asistencia">
            <div className="w-full">
              {!activeSession ? (
                <div className="h-full flex items-center justify-center py-1.5 text-[hsl(var(--text-secondary))]">
                  <div className="text-center">
                    <Activity size={40} className="mx-auto mb-4 opacity-30" />
                    <p className="font-bold">Selecciona una sesión para ver la asistencia</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-semibold text-[hsl(var(--text-primary))]">
                        {activeSession.topic ? activeSession.topic : new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                      </h2>
                      {activeSession.topic && <p className="text-xs text-[hsl(var(--text-secondary))] font-bold mt-0.5">{new Date(activeSession.session_date + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>}
                      {activeSession.season_name && !activeSession.topic && <p className="text-xs text-[hsl(var(--text-secondary))] font-bold mt-0.5">{activeSession.season_name}</p>}
                    </div>
                    <button
                      onClick={() => setShowAddAttendee(true)}
                      disabled={!activeSessionEnabled}
                      className="flex items-center gap-2 px-3 py-2.5 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-[hsl(var(--info)/20%)]"
                    >
                      <UserPlus size={14} /> Añadir Asistentes
                    </button>
                  </div>

                  {/* Stat strip */}
                  <div className="flex gap-4">
                    <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
                      <p className="text-lg font-bold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">{loadingAtt ? '—' : attendance?.total ?? 0}</p>
                      <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Presentes</p>
                    </div>
                    <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
                      <p className="text-lg font-bold text-[hsl(var(--text-primary))]">{house.capacity ?? '—'}</p>
                      <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Capacidad</p>
                    </div>
                    <div className="flex-1 bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg p-4 text-center">
                      <p className="text-lg font-bold text-success-text dark:text-emerald-400">
                        {house.capacity && attendance ? `${Math.round(attendance.total / house.capacity * 100)}%` : '—'}
                      </p>
                      <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mt-1">Ocupación</p>
                    </div>
                  </div>

                  <ErrorBoundary moduleName="Grupo - Monitoreo">
                    <GroupMonitoringPanel
                      houseMonitoring={house.monitoring}
                      avgAttendance={avgAttendance}
                      activeSession={activeSession}
                      activeSessionEnabled={activeSessionEnabled}
                      reportTopic={reportTopic}
                      setReportTopic={setReportTopic}
                      reportOfferingAmount={reportOfferingAmount}
                      setReportOfferingAmount={setReportOfferingAmount}
                      reportStatus={reportStatus}
                      setReportStatus={setReportStatus}
                      reportNoveltyType={reportNoveltyType}
                      setReportNoveltyType={setReportNoveltyType}
                      reportNoveltyDetail={reportNoveltyDetail}
                      setReportNoveltyDetail={setReportNoveltyDetail}
                      reportCancellationReason={reportCancellationReason}
                      setReportCancellationReason={setReportCancellationReason}
                      reportNotes={reportNotes}
                      setReportNotes={setReportNotes}
                      reportPersonas={reportPersonas}
                      setReportPersonas={setReportPersonas}
                      savingReport={savingReport}
                      onSaveReport={handleSaveReport}
                    />
                  </ErrorBoundary>

                  {/* Attendee list */}
                  <GroupAttendeeList loadingAtt={loadingAtt} attendance={attendance} />
                </div>
              )}
            </div>
          </ErrorBoundary>
        </div>
      </main>

      {/* ADD ATTENDEES INLINE SECTION */}
      <ErrorBoundary moduleName="Grupo - Participantes">
        <GroupAddAttendeeDrawer
          show={showAddAttendee}
          activeSessionEnabled={activeSessionEnabled}
          personaQuery={personaQuery}
          setPersonaQuery={setPersonaQuery}
          setRemoteQuery={setRemoteQuery}
          remoteLoading={remoteLoading}
          filteredPersonas={filteredPersonas}
          selectedIds={selectedIds}
          setSelectedIds={setSelectedIds}
          saving={saving}
          onSave={handleSaveAttendance}
          onCancel={() => {
            setShowAddAttendee(false);
            setSelectedIds(new Set());
            setIsCreatingPersona(false);
          }}
          isCreatingPersona={isCreatingPersona}
          setIsCreatingPersona={setIsCreatingPersona}
          newPersonaForm={newPersonaForm}
          setNewPersonaForm={setNewPersonaForm}
          creatingPersona={creatingPersona}
          onCreatePersona={handleCreatePersona}
        />
      </ErrorBoundary>
    </EvangelismShell>
  );
}

export default dynamic(() => Promise.resolve(GroupDetailPage), { ssr: false });
