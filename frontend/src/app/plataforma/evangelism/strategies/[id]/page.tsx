"use client";

import EvangelismShell from '@/components/evangelism/EvangelismShell';
import ConfirmActionDrawer from '@/components/evangelism/ConfirmActionDrawer';
import ViewSwitcher from '@/components/ViewSwitcher';
import { FULL_VIEWS } from '@/hooks/useViewType';
import StrategyOverviewForm from './panels/StrategyOverviewForm';
import StrategyHeader from './panels/StrategyHeader';
import GroupCreationDrawer from './panels/GroupCreationDrawer';
import AttendanceDrawer from './panels/AttendanceDrawer';
import PersonaManagementDrawer from './panels/PersonaManagementDrawer';
import NewSessionDrawer from './panels/NewSessionDrawer';
import SessionsSection from './panels/SessionsSection';
import StrategyViews from './panels/StrategyViews';
import StrategyDashboard from './panels/StrategyDashboard';
import { TABS } from './strategyDetailShared';
import { AlertCircle, Flame } from 'lucide-react';
import { useRouter } from 'next/navigation';
import ErrorBoundary from '@/components/ErrorBoundary';
import { useStrategyDetailPage } from './useStrategyDetailPage';

export default function StrategyDetailPage() {
 const router = useRouter();
 const {
  id,
  token,
  authLoading,
  canReadStrategySurface,
  canManageStrategySurface,
  strategy,
  loading,
  loadError,
  saving,
  editName, setEditName,
  editDesc, setEditDesc,
  editType, setEditType,
  editStatus, setEditStatus,
  editActiva, setEditActiva,
  editClaseRaiz, setEditClaseRaiz,
  editDefaultRoleId, setEditDefaultRoleId,
  editStartDate, setEditStartDate,
  editEndDate, setEditEndDate,
  editRecurrence, setEditRecurrence,
  handleSave,
  fetchStrategy,
  customRoles,
  loadingRoles,
  showRoleForm, setShowRoleForm,
  newRoleName, setNewRoleName,
  newRoleDesc, setNewRoleDesc,
  followUps,
  loadingFollowUps,
  fetchFollowUps,
  confirmAction, setConfirmAction,
  activeTab, setActiveTab,
  viewType, setViewType,
  groups, groupsLoading, fetchGroups,
  metrics,
  personaCache, setPersonaCache,
  roleResults, roleLoading,
  roleSearch, setRoleSearch,
  roleDropdown, setRoleDropdown,
  isGroupDrawerOpen, setIsGroupDrawerOpen,
  groupForm, setGroupForm,
  groupRoleAssignments, setGroupRoleAssignments,
  groupSaving,
  isPersonaDrawerOpen, setIsPersonaDrawerOpen,
  selectedGroup,
  groupPersonas,
  personaSearch, setPersonaSearch,
  personaSearchLoading,
  personaSearchResults,
  personaSaving,
  personaSplitHeight,
  personaSplitRef,
  handlePersonaSplitDrag,
  sessions, sessionsLoading, fetchSessions,
  toggleSessionHabilitacion,
  isNewSessionDrawerOpen, setIsNewSessionDrawerOpen,
  sessionForm, setSessionForm,
  sessionSaving,
  attendanceSession,
  attendancePersonas, setAttendancePersonas,
  attendanceSaving,
  isAttendanceDrawerOpen, setIsAttendanceDrawerOpen,
  sessionMenuId, setSessionMenuId,
  shareMenuId, setShareMenuId,
  sessionGroupFilter, setSessionGroupFilter,
  sessionHabFilter, setSessionHabFilter,
  sessionMonthFilter, setSessionMonthFilter,
  sessionSearch, setSessionSearch,
  tableSubTab, setTableSubTab,
  personaRoleOptions,
  strategyGroupCount,
  getRoleLabel,
  getRoleColor,
  handleCreateGroup,
  openGroupDrawer,
  requestDeleteGroup,
  openPersonaDrawer,
  handleSavePersonas,
  addPersonaToGroup,
  updateGroupPersonaRole,
  removePersonaFromGroup,
  handleCreateSession,
  openGroupAttendance,
  openAttendanceDrawer,
  handleSaveAttendance,
  requestDeleteSession,
  requestDeleteStrategy,
  requestBlockAllSessions,
  handleCreateRole,
  requestDeleteRole,
  formatDate,
  formatLocalDate,
  groupName,
  shareGroupLink,
  sessionMonths,
  attendanceByGroup,
  filteredSessions,
 } = useStrategyDetailPage();


 if (!authLoading && !canReadStrategySurface) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'Acceso restringido' }
 ]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">Acceso restringido</h2>
 <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] max-w-md">
 Esta vista requiere permisos de lectura sobre evangelismo.
 </p>
 <button onClick={() => router.push('/plataforma/evangelism')}
 className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
 Volver a Evangelismo
 </button>
 </div>
 </EvangelismShell>
 );
 }

 if (loading) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'Cargando...' }
 ]}>
 <div className="space-y-3 p-3">
 {[1, 2, 3].map(i => <div key={i} className="h-12 bg-[hsl(var(--bg-muted))] rounded-lg animate-pulse" />)}
 </div>
 </EvangelismShell>
 );
 }

 if (loadError) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'Error' }
 ]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">No se pudo cargar la estrategia</h2>
 <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] max-w-md">La estrategia respondió con un estado inválido o el recurso no está disponible. Vuelve a la lista para reintentar.</p>
 <button onClick={() => router.push('/plataforma/evangelism')}
 className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
 Volver a Estrategias
 </button>
 </div>
 </EvangelismShell>
 );
 }

 if (!strategy) {
 return (
 <EvangelismShell breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: 'No encontrada' }
 ]}>
 <div className="flex flex-col items-center justify-center py-16 text-center">
 <AlertCircle size={48} className="text-[hsl(var(--text-secondary))] mb-4" />
 <h2 className="text-lg font-bold text-[hsl(var(--text-primary))]">Estrategia no encontrada</h2>
 <button onClick={() => router.push('/plataforma/evangelism')}
 className="mt-4 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] transition-colors">
 Volver a Estrategias
 </button>
 </div>
 </EvangelismShell>
 );
 }

 return (
 <EvangelismShell
 breadcrumbs={[
 { label: 'Evangelismo', icon: Flame, href: '/plataforma/evangelism' },
 { label: 'Estrategias', href: '/plataforma/evangelism' },
 { label: strategy.name }
 ]}
 sidebarGroups={groups.map(g => ({ id: g.id, name: g.name, estrategiaId: id as string }))}
 >
 <div className="flex-1 space-y-3 animate-fade-in px-3 md:px-6 lg:px-8 xl:px-12 py-1">
 {/* Header */}
 <StrategyHeader
   strategy={strategy}
   groupCount={strategyGroupCount}
   canManage={canManageStrategySurface}
   onDelete={requestDeleteStrategy}
   onBack={() => router.push('/plataforma/evangelism')}
 />

 {/* Tabs */}
 <div
 role="tablist"
 className="flex items-center gap-1 border-b border-[hsl(var(--border-primary))]"
  onKeyDown={(e) => {
   const tabs = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('[role="tab"]'));
   const idx = tabs.indexOf(document.activeElement as HTMLElement);
   if (idx === -1) return;
   let nextIdx: number | undefined;
   if (e.key === 'ArrowRight') nextIdx = (idx + 1) % tabs.length;
   else if (e.key === 'ArrowLeft') nextIdx = (idx - 1 + tabs.length) % tabs.length;
   else if (e.key === 'Home') nextIdx = 0;
   else if (e.key === 'End') nextIdx = tabs.length - 1;
   if (nextIdx === undefined) return;
   e.preventDefault();
   const nextTab = tabs[nextIdx];
   nextTab?.focus();
   const nextId = TABS[nextIdx].id;
   if (nextId !== 'metrics') setActiveTab(nextId);
  }}
 >
 {TABS.map(tab => (
  <button key={tab.id}
  role="tab"
  aria-selected={activeTab === tab.id}
  tabIndex={activeTab === tab.id ? 0 : -1}
  onClick={() => tab.id === 'metrics' ? router.push(`/plataforma/evangelism/strategies/${id}/analytics`) : setActiveTab(tab.id)}
 className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border-b-2 transition-colors ${
 activeTab === tab.id
 ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] dark:border-[hsl(var(--primary))]'
 : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-[hsl(var(--text-secondary))]'
 }`}>
 <tab.icon size={14} />{tab.label}
 </button>
 ))}
 <div className="flex-1" />
 <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={FULL_VIEWS} />
 </div>

 {!canManageStrategySurface && (
 <div className="rounded-lg border border-[hsl(var(--info-muted))] bg-[hsl(var(--info-muted))] px-3 py-2 text-xs font-medium text-[hsl(var(--info))]">
  Vista en modo lectura. Las acciones de edición y gestión quedan reservadas para usuarios con `evangelism:manage`.
 </div>
 )}

  <StrategyViews
    strategy={strategy}
    id={id}
    token={token}
    canManage={canManageStrategySurface}
    activeTab={activeTab}
    viewType={viewType}
    tableSubTab={tableSubTab}
    onTableSubTabChange={setTableSubTab}
    groups={groups}
    sessions={sessions}
    groupsLoading={groupsLoading}
    sessionsLoading={sessionsLoading}
    groupName={groupName}
    formatDate={formatDate}
    onAddGroup={() => setIsGroupDrawerOpen(true)}
    onOpenPersona={openPersonaDrawer}
    onNavigateGroup={(gid) => router.push(`/plataforma/evangelism/groups/${gid}`)}
    shareGroupLink={shareGroupLink}
    onOpenAttendance={openAttendanceDrawer}
    onToggleHabilitacion={toggleSessionHabilitacion}
    onRequestDeleteSession={requestDeleteSession}
    onGroupsChanged={fetchGroups}
    onSessionsChanged={fetchSessions}
  />

 {viewType === 'dashboard' && activeTab === 'overview' && (
 <ErrorBoundary moduleName="Estrategia - General" compact>
   <StrategyOverviewForm
     editName={editName} setEditName={setEditName}
     editDesc={editDesc} setEditDesc={setEditDesc}
     editType={editType} setEditType={setEditType}
     editStatus={editStatus} setEditStatus={setEditStatus}
     editClaseRaiz={editClaseRaiz} setEditClaseRaiz={setEditClaseRaiz}
     editActiva={editActiva} setEditActiva={setEditActiva}
     editRecurrence={editRecurrence} setEditRecurrence={setEditRecurrence}
     editStartDate={editStartDate} setEditStartDate={setEditStartDate}
     editEndDate={editEndDate} setEditEndDate={setEditEndDate}
     canManage={canManageStrategySurface}
     saving={saving}
     onSave={handleSave}
   />
  </ErrorBoundary>
  )}

  {viewType === 'dashboard' && activeTab === 'sessions' && (
  <SessionsSection
    strategy={strategy}
    id={id}
    token={token}
    canManage={canManageStrategySurface}
    groups={groups}
    sessions={sessions}
    filteredSessions={filteredSessions}
    sessionsLoading={sessionsLoading}
    search={sessionSearch}
    onSearchChange={setSessionSearch}
    groupFilter={sessionGroupFilter}
    onGroupFilterChange={setSessionGroupFilter}
    habFilter={sessionHabFilter}
    onHabFilterChange={setSessionHabFilter}
    months={sessionMonths}
    monthFilter={sessionMonthFilter}
    onMonthFilterChange={setSessionMonthFilter}
    groupName={groupName}
    sessionMenuId={sessionMenuId}
    onMenuToggle={(sid) => setSessionMenuId(sessionMenuId === sid ? null : sid)}
    onToggleHabilitacion={toggleSessionHabilitacion}
    onOpenAttendance={openAttendanceDrawer}
    onRequestDelete={requestDeleteSession}
    onBlockAll={requestBlockAllSessions}
    onNewSession={() => {
      setSessionForm({ grupo_id: groups[0]?.id || '', session_date: formatLocalDate(new Date()), topic: '', offering_amount: '', report_notes: '' });
      setIsNewSessionDrawerOpen(true);
    }}
    onSessionsChanged={fetchSessions}
  />
  )}

   <StrategyDashboard
    strategy={strategy}
    id={id}
    token={token}
    canManage={canManageStrategySurface}
    activeTab={activeTab}
    groups={groups}
    metrics={metrics}
    sessionsLoading={sessionsLoading}
    attendanceByGroup={attendanceByGroup}
    formatDate={formatDate}
    onOpenGroupDrawer={openGroupDrawer}
    onOpenPersona={openPersonaDrawer}
    onRequestDeleteGroup={requestDeleteGroup}
    onOpenGroupAttendance={openGroupAttendance}
    onOpenAttendance={openAttendanceDrawer}
    onToggleHabilitacion={toggleSessionHabilitacion}
    shareMenuId={shareMenuId}
    onShareMenuToggle={(gid) => setShareMenuId(shareMenuId === gid ? null : gid)}
    shareGroupLink={shareGroupLink}
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
    onCreateRole={handleCreateRole}
    onRequestDeleteRole={requestDeleteRole}
    followUps={followUps}
    loadingFollowUps={loadingFollowUps}
    onFollowUpsChanged={fetchFollowUps}
  />

 {/* ── Group Creation Drawer ── */}
 <GroupCreationDrawer
   isOpen={isGroupDrawerOpen}
   onClose={() => setIsGroupDrawerOpen(false)}
   strategy={strategy}
   customRoles={customRoles}
   canManage={canManageStrategySurface}
   groupForm={groupForm}
   setGroupForm={setGroupForm}
   groupRoleAssignments={groupRoleAssignments}
   setGroupRoleAssignments={setGroupRoleAssignments}
   personaCache={personaCache}
   setPersonaCache={setPersonaCache}
   roleResults={roleResults}
   roleLoading={roleLoading}
   roleSearch={roleSearch}
   setRoleSearch={setRoleSearch}
   roleDropdown={roleDropdown}
   setRoleDropdown={setRoleDropdown}
   groupSaving={groupSaving}
   onCreateGroup={handleCreateGroup}
 />

  {/* Persona Management Drawer */}
  <PersonaManagementDrawer
    isOpen={isPersonaDrawerOpen && canManageStrategySurface}
    onClose={() => setIsPersonaDrawerOpen(false)}
    groupName={selectedGroup?.name || ''}
    personas={groupPersonas}
    saving={personaSaving}
    onSave={handleSavePersonas}
    splitRef={personaSplitRef}
    splitHeight={personaSplitHeight}
    onSplitDrag={handlePersonaSplitDrag}
    roleOptions={personaRoleOptions}
    getRoleColor={getRoleColor}
    onRoleChange={updateGroupPersonaRole}
    onRemove={removePersonaFromGroup}
    search={personaSearch}
    onSearchChange={setPersonaSearch}
    searchLoading={personaSearchLoading}
    searchResults={personaSearchResults}
    onAdd={addPersonaToGroup}
  />



  {/* New Session Drawer */}
  <NewSessionDrawer
    isOpen={isNewSessionDrawerOpen && canManageStrategySurface}
    onClose={() => setIsNewSessionDrawerOpen(false)}
    strategyName={strategy?.name || ''}
    groups={groups}
    form={sessionForm}
    setForm={setSessionForm}
    saving={sessionSaving}
    onSave={handleCreateSession}
  />


 {/* ── Attendance Drawer ── */}
 <AttendanceDrawer
   isOpen={isAttendanceDrawerOpen}
   onClose={() => setIsAttendanceDrawerOpen(false)}
   token={token}
   session={attendanceSession}
   personas={attendancePersonas}
   setPersonas={setAttendancePersonas}
   saving={attendanceSaving}
   canManage={canManageStrategySurface}
   onSave={handleSaveAttendance}
   onVisitorCreated={() => { fetchGroups(); fetchStrategy(); }}
   getRoleColor={getRoleColor}
   getRoleLabel={getRoleLabel}
 />
  <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
  </div>
  </EvangelismShell>
  );
}
