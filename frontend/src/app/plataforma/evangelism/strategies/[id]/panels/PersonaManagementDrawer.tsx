import type { RefObject } from 'react';
import { Loader2, Plus, Search, UserCheck, UserMinus } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { RoleSelect } from './RoleSelect';

export type PersonaManagementRow = {
  id: string;
  name: string;
  email: string;
  role: string;
  role_label?: string;
};

export type PersonaSearchResult = {
  id: string;
  nombre_completo?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  church_role?: string;
};

interface PersonaManagementDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  groupName: string;
  personas: PersonaManagementRow[];
  saving: boolean;
  onSave: () => void;
  splitRef: RefObject<HTMLDivElement>;
  splitHeight: number;
  onSplitDrag: (e: React.MouseEvent) => void;
  roleOptions: { value: string; label: string }[];
  getRoleColor: (role: string) => string;
  onRoleChange: (personaId: string, role: string) => void;
  onRemove: (personaId: string) => void;
  search: string;
  onSearchChange: (v: string) => void;
  searchLoading: boolean;
  searchResults: PersonaSearchResult[];
  onAdd: (persona: PersonaSearchResult) => void;
}

export default function PersonaManagementDrawer({
  isOpen,
  onClose,
  groupName,
  personas,
  saving,
  onSave,
  splitRef,
  splitHeight,
  onSplitDrag,
  roleOptions,
  getRoleColor,
  onRoleChange,
  onRemove,
  search,
  onSearchChange,
  searchLoading,
  searchResults,
  onAdd,
}: PersonaManagementDrawerProps) {
  return (
    <WorkspaceDrawer isOpen={isOpen} onClose={onClose}
      title="Gestionar Personas" subtitle={groupName || ''}
      actions={<>
        <button onClick={onClose}
          className="px-4 py-1.5 text-sm font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
        <button onClick={onSave} disabled={saving}
          className="px-4 py-1.5 text-sm font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
          {saving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar ({personas.length})</>}
        </button>
      </>}>
      <div ref={splitRef} className="flex flex-col" style={{ height: 'calc(100vh - 16rem)' }}>
        {/* Panel superior: personas asignadas */}
        <div id="persona-list" className="overflow-y-auto shrink-0 pb-2" style={{ height: splitHeight }}>
          <label htmlFor="persona-list" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider block mb-2">
            Personas ({personas.length})
          </label>
          {personas.length === 0 ? (
            <p className="text-xs text-[hsl(var(--text-secondary))] italic py-2">Sin personas asignadas</p>
          ) : (
            <div className="space-y-1.5">
              {personas.map(m => (
                <div key={m.id} className="flex items-center gap-2 px-2 py-1.5 bg-[hsl(var(--bg-muted))] rounded-md">
                  <div className="flex-1 min-w-0">
                    <span className="text-xs font-medium text-[hsl(var(--text-primary))] truncate block">{m.name}</span>
                  </div>
                  <RoleSelect
                    value={m.role}
                    options={roleOptions}
                    colorClass={getRoleColor(m.role)}
                    onChange={v => onRoleChange(m.id, v)}
                  />
                  <button onClick={() => onRemove(m.id)}
                    className="p-1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.08)] dark:hover:bg-[hsl(var(--destructive)/0.15)] rounded transition-colors">
                    <UserMinus size={13} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Divisor arrastrable */}
        <div
          tabIndex={0}
          role="separator"
          aria-label="Ajustar tamaño del panel"
          onMouseDown={onSplitDrag}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.preventDefault(); }}
          className="shrink-0 h-4 flex items-center justify-center cursor-row-resize group select-none border-y border-[hsl(var(--border-primary))] hover:border-[hsl(var(--info)/30%)] dark:hover:border-[hsl(var(--info)/100%)]/40 transition-colors"
          title="Arrastra para ajustar el espacio"
        >
          <div className="w-12 h-1 rounded-full bg-[hsl(var(--bg-muted))] group-hover:bg-[hsl(var(--primary))] dark:group-hover:bg-[hsl(var(--primary))] transition-colors" />
        </div>

        {/* Panel inferior: agregar personas */}
        <div className="flex-1 min-h-0 flex flex-col pt-3">
          <label htmlFor="persona-search" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block shrink-0">Agregar personas</label>
          <div className="relative mb-2 shrink-0">
            {searchLoading
              ? <Loader2 size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--primary))] animate-spin" />
              : <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />}
            <input id="persona-search" value={search}
              onChange={e => onSearchChange(e.target.value)}
              placeholder="Filtrar por nombre..."
              className="w-full pl-9 pr-3 py-2 text-sm bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))]" />
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto space-y-1">
            {(() => {
              if (searchLoading) return (
                <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-3">Cargando personas...</p>
              );
              const q = search.trim();
              const available = searchResults.filter(m => !personas.find(gm => String(gm.id) === String(m.id)));
              if (q.length < 1) return (
                <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-3">Escribe una letra para buscar</p>
              );
              if (available.length === 0) return (
                <p className="text-xs text-[hsl(var(--text-secondary))] text-center py-3">
                  Sin coincidencias
                </p>
              );
              return available.map(m => (
                <button key={m.id} onClick={() => onAdd(m)}
                  className="w-full flex items-center justify-between px-2 py-1.5 hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 rounded-md text-xs text-left transition-colors group/add">
                  <span className="font-medium text-[hsl(var(--text-primary))]">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}
                    {m.email && <span className="text-[hsl(var(--text-secondary))] ml-2">{m.email}</span>}
                  </span>
                  <Plus size={14} className="text-[hsl(var(--text-secondary))] group-hover/add:text-[hsl(var(--primary))] transition-colors" />
                </button>
              ));
            })()}
          </div>
        </div>
      </div>
    </WorkspaceDrawer>
  );
}
