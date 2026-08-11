'use client';

import { Suspense, useEffect } from 'react';
import ConfirmActionDrawer from '@/components/evangelism/ConfirmActionDrawer';
import ErrorBoundary from '@/components/ErrorBoundary';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import { Activity, Calendar, CheckCircle2, Home, Trash2, X } from 'lucide-react';
import GroupForm from './panels/GroupForm';
import GroupPersonasSection from './panels/GroupPersonasSection';
import GroupQuickAssign from './panels/GroupQuickAssign';
import GroupSidebarList from './panels/GroupSidebarList';
import { GridView, KanbanView, ListView, TableView } from './GroupViews';
import { MODE_CONFIG, useGroupsPage } from './useGroupsPage';

function GroupsContent() {
  const {
    // State - data
    houses,
    personas,
    summary,
    loading,
    // State - UI
    searchQuery, setSearchQuery,
    viewType, setViewType,
    mode,
    // State - selection/form
    selectedHouse,
    setSelectedHouse,
    isCreating, setIsCreating,
    isAddingPersonas, setIsAddingPersonas,
    formData, setFormData,
    selectedPersonaIds, setSelectedPersonaIds,
    personaSearchQuery, setPersonaSearchQuery,
    personaRoleFilter, setPersonaRoleLinkFilter,
    personaAssignmentFilter, setPersonaAssignmentFilter,
    confirmAction, setConfirmAction,
    quickAssignmentTargets, setQuickAssignmentTargets,
    saving,
    // Derived
    filteredHouses,
    filteredPersonasList,
    uniqueRoles,
    showPanel,
    getPersonaName,
    // Handlers
    handleSave,
    handleSelectHouse,
    requestDeleteHouse,
    handleQuickAssignPersona,
    // Sidebar context passthrough
    pushSidebarPanel, resetSidebarStack,
    router,
    token,
  } = useGroupsPage();

  // Clean up sidebar when unmounting
  useEffect(() => {
    return () => resetSidebarStack();
  }, [resetSidebarStack]);

  return (
    <>
      <GroupSidebarList
        pushSidebarPanel={pushSidebarPanel}
        filteredHouses={filteredHouses}
        loading={loading}
        selectedHouse={selectedHouse}
        isCreating={isCreating}
        mode={mode}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        getPersonaName={getPersonaName}
        requestDeleteHouse={requestDeleteHouse}
        setIsCreating={setIsCreating}
        setSelectedHouse={setSelectedHouse}
        setFormData={setFormData}
        setSelectedPersonaIds={setSelectedPersonaIds}
        token={token}
      />

      <EvangelismShell
        breadcrumbs={[
          { label: 'Grupos en Casa', href: '/plataforma/evangelism/groups', icon: Home },
          { label: 'Grupos', icon: Home },
        ]}
        viewType={viewType}
        onViewChange={setViewType}
        viewOptions={['list', 'kanban', 'grid', 'table']}
        onSearch={setSearchQuery}
      >
        <div className="flex h-full p-4 lg:p-4 bg-[hsl(var(--bg-muted))]/50 dark:bg-surface-card/50">
          {/* Detail/Edit Panel */}
          {showPanel ? (
            <ErrorBoundary moduleName="Grupos - Detalle" compact>
              <div className="flex-1 bg-[hsl(var(--bg-primary))] dark:bg-surface-card rounded-lg border border-[hsl(var(--border-primary))] shadow-sm flex flex-col overflow-hidden animate-in fade-in slide-in-from-right-4 duration-300">
                <div className="px-3 py-2 border-b border-[hsl(var(--border-primary))]/80 flex items-center justify-between shrink-0 bg-[hsl(var(--bg-secondary))]">
                  <h2 className="text-base font-bold text-[hsl(var(--text-primary))]">
                    {isCreating ? 'Nuevo Grupo' : MODE_CONFIG[mode].title}
                  </h2>
                  <div className="flex items-center gap-1">
                    {!isCreating && selectedHouse && (
                      <button
                        onClick={() => router.push(`/plataforma/evangelism/groups/sessions/${selectedHouse.id}`)}
                        className="size-8 rounded-lg bg-success-soft flex items-center justify-center text-[hsl(var(--secondary))] dark:text-[hsl(var(--secondary))] dark:hover:bg-[hsl(var(--success)/0.15)] transition-colors"
                        title="Reportar sesión"
                      >
                        <Calendar size={15} />
                      </button>
                    )}
                    {!isCreating && selectedHouse && (
                      <button
                        onClick={() => requestDeleteHouse(selectedHouse)}
                        className="size-8 rounded-lg bg-danger-soft flex items-center justify-center text-[hsl(var(--destructive))] dark:hover:bg-[hsl(var(--danger)/0.15)] transition-colors"
                        title="Eliminar grupo"
                      >
                        <Trash2 size={15} />
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setIsCreating(false);
                        setSelectedHouse(null);
                        setSelectedPersonaIds(new Set());
                        setFormData({ capacity: 15, status: 'Activo' });
                      }}
                      className="size-8 rounded-lg bg-[hsl(var(--bg-muted))] flex items-center justify-center text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors"
                    >
                      <X size={15} />
                    </button>
                  </div>
                </div>

                {selectedHouse || isCreating ? (
                  <>
                    <div className="flex-1 overflow-y-auto px-3 py-2 scrollbar-thin">
                      {!isCreating && (
                        <div className="mb-5 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 px-4 py-1.5 flex items-start justify-between gap-4">
                          <div>
                            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                              {MODE_CONFIG[mode].title}
                            </p>
                            <p className="text-sm font-medium text-[hsl(var(--text-secondary))] mt-1">
                              {MODE_CONFIG[mode].description}
                            </p>
                          </div>
                          <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            Edición
                          </span>
                        </div>
                      )}
                      <GroupForm
                        formData={formData}
                        setFormData={setFormData}
                        personas={personas}
                        onSubmit={handleSave}
                        formId="groups-form"
                      />
                      {selectedHouse && (
                        <GroupPersonasSection
                          selectedHouse={selectedHouse}
                          selectedPersonaIds={selectedPersonaIds}
                          setSelectedPersonaIds={setSelectedPersonaIds}
                          personas={personas}
                          isAddingPersonas={isAddingPersonas}
                          setIsAddingPersonas={setIsAddingPersonas}
                          personaSearchQuery={personaSearchQuery}
                          setPersonaSearchQuery={setPersonaSearchQuery}
                          personaRoleFilter={personaRoleFilter}
                          setPersonaRoleLinkFilter={setPersonaRoleLinkFilter}
                          personaAssignmentFilter={personaAssignmentFilter}
                          setPersonaAssignmentFilter={setPersonaAssignmentFilter}
                          filteredPersonasList={filteredPersonasList}
                          uniqueRoles={uniqueRoles as Array<string | undefined>}
                        />
                      )}
                    </div>

                    <div className="px-3 py-2 border-t border-[hsl(var(--border-primary))] shrink-0 flex justify-end gap-2">
                      <button
                        onClick={() => {
                          setIsCreating(false);
                          setSelectedHouse(null);
                          setSelectedPersonaIds(new Set());
                          setFormData({ capacity: 15, status: 'Activo' });
                        }}
                        className="px-4 py-2 rounded-lg text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] transition-colors"
                      >
                        Cancelar
                      </button>
                      <button
                        type="submit"
                        form="groups-form"
                        disabled={saving}
                        className="px-3 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-semibold uppercase tracking-wide transition-all shadow-lg shadow-primary active:scale-95 disabled:opacity-50 flex items-center gap-2"
                      >
                        {saving ? (
                          <Activity className="animate-spin" size={13} />
                        ) : (
                          <CheckCircle2 size={13} />
                        )}
                        Guardar Grupo
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex-1 overflow-y-auto bg-[hsl(var(--bg-primary))] dark:bg-surface-card">
                    {mode === 'personas' && summary ? (
                      <GroupQuickAssign
                        summary={summary}
                        houses={houses}
                        quickAssignmentTargets={quickAssignmentTargets}
                        setQuickAssignmentTargets={setQuickAssignmentTargets}
                        onAssign={handleQuickAssignPersona}
                        saving={saving}
                      />
                    ) : (
                      <div className="flex-1 flex items-center justify-center text-[hsl(var(--text-secondary))]/20 h-full">
                        <div className="text-center">
                          <Home size={40} className="mx-auto mb-3 opacity-40" />
                          <p className="text-sm font-bold">
                            Selecciona un grupo o crea uno nuevo
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </ErrorBoundary>
          ) : (
            <ErrorBoundary moduleName="Grupos - Listado" compact>
              <>
                {viewType === 'list' && <ListView houses={filteredHouses} onSelectHouse={handleSelectHouse} getPersonaName={getPersonaName} onDeleteHouse={requestDeleteHouse} />}
                {viewType === 'grid' && <GridView houses={filteredHouses} onSelectHouse={handleSelectHouse} getPersonaName={getPersonaName} onDeleteHouse={requestDeleteHouse} />}
                {viewType === 'kanban' && <KanbanView houses={filteredHouses} onSelectHouse={handleSelectHouse} getPersonaName={getPersonaName} onDeleteHouse={requestDeleteHouse} />}
                {viewType === 'table' && <TableView houses={filteredHouses} onSelectHouse={handleSelectHouse} getPersonaName={getPersonaName} onDeleteHouse={requestDeleteHouse} />}
              </>
            </ErrorBoundary>
          )}
        </div>
        <ConfirmActionDrawer action={confirmAction} onClose={() => setConfirmAction(null)} />
      </EvangelismShell>
    </>
  );
}

export default function GroupsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-4 text-center text-[hsl(var(--text-secondary))]">Cargando grupos...</div>
      }
    >
      <GroupsContent />
    </Suspense>
  );
}
