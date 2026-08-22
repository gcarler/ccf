'use client';

import type { ViewType } from '@/components/ViewSwitcher';
import ConfirmActionDrawer from '@/components/evangelism/ConfirmActionDrawer';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { DSSkeleton } from '@/design';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import TextPromptDrawer from '@/components/ui/TextPromptDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import EventViews from './EventViews';
import EventQrDrawer from './EventQrDrawer';
import EventCardViews from './panels/EventCardViews';
import EventCreateDrawer from './panels/EventCreateDrawer';
import EventAttendanceDrawer from './panels/EventAttendanceDrawer';
import EventEditDrawer from './panels/EventEditDrawer';
import EventDeleteDrawer from './panels/EventDeleteDrawer';
import { useEventsPage } from './useEventsPage';

const ALL_VIEWS: ViewType[] = ['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar', 'wiki'];

const EVENT_TYPE_LABEL: Record<string, string> = {
 PERMANENT: 'Semanal',
 MONTHLY: 'Mensual',
 ANNUAL: 'Anual',
 ONCE: 'Única Vez',
 SPECIAL: 'Especial',
 GROUPS: 'Temporada - fuera del templo',
 ONLINE: 'En Línea',
};

const EVENT_TYPE_COLOR: Record<string, string> = {
 PERMANENT: 'badge-info group-hover:badge-info',
 MONTHLY: 'badge-info group-hover:badge-info',
 ANNUAL: 'badge-warning group-hover:badge-warning',
 ONCE: 'badge-danger group-hover:badge-danger',
 SPECIAL: 'badge-warning group-hover:badge-warning',
 GROUPS: 'badge-success group-hover:badge-success',
 ONLINE: 'badge-info group-hover:badge-info',
};

function EventsPage() {
 const router = useRouter();
 const {
  canManageEvents,
  viewType, setViewType,
  events,
  loading,
  wikiNotes, setWikiNotes,
  isCreateDrawerOpen, setIsCreateDrawerOpen,
  isAttendanceDrawerOpen, setIsAttendanceDrawerOpen,
  isQrDrawerOpen, setIsQrDrawerOpen,
  confirmAction, setConfirmAction,
  selectedEvent,
  showScanner, setShowScanner,
  scannerToken, setScannerToken,
  isScanning,
  newEvent, setNewEvent,
  sedes,
  roles,
  editingEvent, setEditingEvent,
  deletingEventId, setDeletingEventId,
  menuOpenId, setMenuOpenId,
  savingCreateEvent,
  savingAttendance,
  updatingEventId,
  deletingEventLoadingId,
  attendanceDate, setAttendanceDate,
  attendedPersonaIds,
  attendanceSearch, setAttendanceSearch,
  attendanceLoading,
  attendanceRoleFilter, setAttendanceRoleFilter,
  attendanceStatusFilter, setAttendanceStatusFilter,
  createManualSearch, setCreateManualSearch,
  editManualSearch, setEditManualSearch,
  audiencePresets,
  audiencePresetNameOpen, setAudiencePresetNameOpen,
  audiencePresetNameDraft, setAudiencePresetNameDraft,
  handleScanToken,
  getTargetRoleIds,
  getTargetRoleLabel,
  createManualPersonas,
  editManualPersonas,
  applyPresetToCreateEvent,
  applyPresetToEditingEvent,
  saveAudiencePreset,
  submitAudiencePreset,
  deleteAudiencePreset,
  addSuggestedAudiencePresets,
  handleCreateEvent,
  getEventAttendanceStat,
  openQr,
  openAttendance,
  saveAttendance,
  toggleAttendance,
  expectedUniversePersonas,
  attendanceRoleOptions,
  filteredPersonas,
  markFilteredPersonas,
  clearFilteredPersonas,
  getVisualDate,
  calendarEvents,
  ganttItems,
  boardColumns,
  handleDeleteEvent,
  handleUpdateEvent,
 } = useEventsPage();

 if (loading) {
 return (
 <EvangelismShell breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'Eventos' }]}>
 <div className="p-4 space-y-3">
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
 {[1, 2, 3, 4, 5, 6].map(i => <DSSkeleton key={i} className="h-48 rounded-lg" />)}
 </div>
 </div>
 </EvangelismShell>
 );
 }
 return (
 <>
 <TextPromptDrawer
 isOpen={audiencePresetNameOpen}
 onClose={() => setAudiencePresetNameOpen(false)}
 onSubmit={submitAudiencePreset}
 title="Guardar plantilla de audiencia"
 subtitle="Define un nombre corto"
 label="Nombre de la plantilla"
 value={audiencePresetNameDraft}
 onChange={setAudiencePresetNameDraft}
 placeholder="Ej. Jóvenes del sábado"
 submitLabel="Guardar plantilla"
 />
 <EvangelismShell
 breadcrumbs={[{ label: 'Evangelismo', href: '/plataforma/evangelism' }, { label: 'Eventos' }]}
 viewOptions={ALL_VIEWS}
 viewType={viewType}
 onViewChange={(view) => setViewType(view as ViewType)}
 onAdd={canManageEvents ? () => setIsCreateDrawerOpen(true) : undefined}
 >
  <div className="p-4 space-y-3">
  <ErrorBoundary moduleName="Eventos - Listado">
  <EventCardViews
    viewType={viewType}
    events={events}
    onOpenEvent={(eventId) => router.push(`/plataforma/evangelism/events/${eventId}`)}
    getTargetRoleLabel={getTargetRoleLabel}
    getEventAttendanceStat={getEventAttendanceStat}
    getVisualDate={getVisualDate}
    eventTypeLabel={EVENT_TYPE_LABEL}
    eventTypeColor={EVENT_TYPE_COLOR}
    onOpenQr={openQr}
    onOpenAttendance={openAttendance}
    menuOpenId={menuOpenId}
    onMenuToggle={(id) => setMenuOpenId(menuOpenId === id ? null : id)}
    onEdit={(ev) => { setEditingEvent({ ...ev, target_role_ids: getTargetRoleIds(ev) }); setMenuOpenId(null); }}
    onDelete={(id) => { setDeletingEventId(id); setMenuOpenId(null); }}
  />


 <EventViews
  viewType={viewType}
  boardColumns={boardColumns}
  calendarEvents={calendarEvents}
  ganttItems={ganttItems}
  wikiNotes={wikiNotes}
  onWikiNotesChange={setWikiNotes}
  onOpenEvent={(eventId) => router.push(`/plataforma/evangelism/events/${eventId}`)}
  eventTypeLabel={EVENT_TYPE_LABEL}
  getTargetRoleLabel={(event) => getTargetRoleLabel(event)}
  getEventAttendanceStat={getEventAttendanceStat}
 />
  </ErrorBoundary>
  </div>

  <EventCreateDrawer
    isOpen={isCreateDrawerOpen && canManageEvents}
    onClose={() => setIsCreateDrawerOpen(false)}
    saving={savingCreateEvent}
    onSubmit={handleCreateEvent}
    form={newEvent}
    setForm={setNewEvent}
       roles={roles}
       sedes={sedes}
    presets={audiencePresets}
    onApplyPreset={applyPresetToCreateEvent}
    onDeletePreset={deleteAudiencePreset}
    onAddSuggestions={addSuggestedAudiencePresets}
    onSavePreset={saveAudiencePreset}
    manualSearch={createManualSearch}
    setManualSearch={setCreateManualSearch}
    manualPersonas={createManualPersonas}
  />

  <EventAttendanceDrawer
    isOpen={isAttendanceDrawerOpen}
    onClose={() => setIsAttendanceDrawerOpen(false)}
    event={selectedEvent}
    date={attendanceDate}
    setDate={setAttendanceDate}
    saving={savingAttendance}
    onSave={saveAttendance}
    loading={attendanceLoading}
    showScanner={showScanner}
    setShowScanner={setShowScanner}
    scannerToken={scannerToken}
    setScannerToken={setScannerToken}
    onScan={handleScanToken}
    isScanning={isScanning}
    search={attendanceSearch}
    setSearch={setAttendanceSearch}
    roleFilter={attendanceRoleFilter}
    setRoleFilter={setAttendanceRoleFilter}
    roleOptions={attendanceRoleOptions}
    statusFilter={attendanceStatusFilter}
    setStatusFilter={setAttendanceStatusFilter}
    onMarkFiltered={markFilteredPersonas}
    onClearFiltered={clearFilteredPersonas}
    filteredPersonas={filteredPersonas}
    attendedIds={attendedPersonaIds}
    onToggle={toggleAttendance}
    universe={expectedUniversePersonas}
    getTargetRoleLabel={getTargetRoleLabel}
  />

  {/* Drawer: Generar QR */}
  <EventQrDrawer
    isOpen={isQrDrawerOpen}
    selectedEvent={selectedEvent}
    onClose={() => setIsQrDrawerOpen(false)}
  />

  <EventDeleteDrawer
    deletingId={deletingEventId}
    deletingLoadingId={deletingEventLoadingId}
    onDelete={handleDeleteEvent}
    onClose={() => setDeletingEventId(null)}
  />

  <EventEditDrawer
    event={editingEvent}
    setEvent={setEditingEvent}
    updatingId={updatingEventId}
    onSave={handleUpdateEvent}
    roles={roles}
    getTargetRoleIds={getTargetRoleIds}
    manualSearch={editManualSearch}
    setManualSearch={setEditManualSearch}
    manualPersonas={editManualPersonas}
    presets={audiencePresets}
    onApplyPreset={applyPresetToEditingEvent}
    onDeletePreset={deleteAudiencePreset}
    onAddSuggestions={addSuggestedAudiencePresets}
    onSavePreset={saveAudiencePreset}
  />
 <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
 </EvangelismShell>
 </>
 );

}

export default dynamic(() => Promise.resolve(EventsPage), { ssr: false });
