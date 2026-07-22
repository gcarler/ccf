import type { Dispatch, SetStateAction } from 'react';
import { Loader2, Plus, Search, X } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import type { Strategy } from '../../../types';
import { customRoleValue, type CustomRole, type SearchablePersona } from '../strategyDetailShared';

export type GroupForm = {
  name: string;
  zone: string;
  address: string;
  capacity: number;
  day_of_week: string;
  start_time: string;
  end_time: string;
};

export type RoleSearchPersona = SearchablePersona & { role_label?: string };

interface GroupCreationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  strategy: Strategy | null;
  customRoles: CustomRole[];
  canManage: boolean;
  groupForm: GroupForm;
  setGroupForm: Dispatch<SetStateAction<GroupForm>>;
  groupRoleAssignments: Record<string, string | null>;
  setGroupRoleAssignments: Dispatch<SetStateAction<Record<string, string | null>>>;
  personaCache: Record<string, RoleSearchPersona>;
  setPersonaCache: Dispatch<SetStateAction<Record<string, RoleSearchPersona>>>;
  roleResults: Record<string, RoleSearchPersona[]>;
  roleLoading: Record<string, boolean>;
  roleSearch: Record<string, string>;
  setRoleSearch: Dispatch<SetStateAction<Record<string, string>>>;
  roleDropdown: string | null;
  setRoleDropdown: Dispatch<SetStateAction<string | null>>;
  groupSaving: boolean;
  onCreateGroup: () => void;
}

export default function GroupCreationDrawer({
  isOpen,
  onClose,
  strategy,
  customRoles,
  canManage,
  groupForm,
  setGroupForm,
  groupRoleAssignments,
  setGroupRoleAssignments,
  personaCache,
  setPersonaCache,
  roleResults,
  roleLoading,
  roleSearch,
  setRoleSearch,
  roleDropdown,
  setRoleDropdown,
  groupSaving,
  onCreateGroup,
}: GroupCreationDrawerProps) {
  return (
    <WorkspaceDrawer isOpen={isOpen && canManage} onClose={onClose}
    title="Nuevo Grupo" subtitle={`Estrategia: ${strategy?.name}`}
    actions={<>
    <button onClick={onClose}
    className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
    <button onClick={onCreateGroup} disabled={groupSaving || !groupForm.name.trim()}
    className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
    {groupSaving ? <><Loader2 size={14} className="animate-spin" />Creando...</> : <><Plus size={14} />Crear Grupo</>}
    </button>
    </>}>
    <div className="space-y-4">
    {strategy?.typology === 'relacional' && (
    <div className="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg text-[11px] text-[hsl(var(--primary))] dark:text-blue-300">
    <p className="font-semibold">Config. heredada:</p>
    <p>Recurrencia: {strategy.recurrence} · Día: {strategy.day_of_week} · Hora: {strategy.start_time}</p>
    </div>
    )}
    {([
    { label: 'Nombre del grupo *', field: 'name', placeholder: 'Ej: Grupo Norte' },
    { label: 'Zona / Sector', field: 'zone', placeholder: 'Ej: Zona Norte' },
    { label: 'Dirección', field: 'address', placeholder: 'Dirección completa' },
    ] as const).map(({ label, field, placeholder }) => (
    <div key={field}>
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">{label}</label>
    <input value={groupForm[field]} onChange={e => setGroupForm(f => ({ ...f, [field]: e.target.value }))}
    placeholder={placeholder}
    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
    </div>
    ))}
    <div>
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Capacidad</label>
    <input type="number" value={groupForm.capacity} onChange={e => setGroupForm(f => ({ ...f, capacity: parseInt(e.target.value) || 15 }))}
    className="w-full px-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]" />
    </div>
    <div className="grid grid-cols-3 gap-2">
    <div>
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Día</label>
    <select value={groupForm.day_of_week} onChange={e => setGroupForm(f => ({ ...f, day_of_week: e.target.value }))}
    className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none">
    <option value="">—</option>
    {['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'].map(d => <option key={d} value={d}>{d}</option>)}
    </select>
    </div>
    <div>
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Inicio</label>
    <input type="time" value={groupForm.start_time} onChange={e => setGroupForm(f => ({ ...f, start_time: e.target.value }))}
    className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
    </div>
    <div>
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Fin</label>
    <input type="time" value={groupForm.end_time} onChange={e => setGroupForm(f => ({ ...f, end_time: e.target.value }))}
    className="w-full px-2 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
    </div>
    </div>
    {customRoles.length === 0 ? (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] font-medium text-amber-700 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300">
    Esta estrategia no tiene roles definidos. El grupo se creará sin cargos de servicio por defecto.
    </div>
    ) : customRoles.map((role) => {
    const field = customRoleValue(role);
    const label = role.nombre_rol;
    const selectedId = groupRoleAssignments[field] || null;
    const selectedPersona = selectedId ? personaCache[selectedId] : null;
    const selectedName = selectedPersona
    ? (selectedPersona.nombre_completo || `${selectedPersona.first_name ?? ''} ${selectedPersona.last_name ?? ''}`.trim())
    : '';
    const query = roleSearch[field] || '';
    const results = roleResults[field] || [];
    const isLoading = Boolean(roleLoading[field]);
    return (
    <div key={field} className="relative">
    <label className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">{label}</label>
    <div className="relative">
    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] pointer-events-none" />
    <input
    type="text"
    placeholder={selectedName || `Buscar ${label.toLowerCase()}...`}
    value={roleDropdown === field ? query : selectedName}
    onFocus={() => {
    setRoleDropdown(field);
    setRoleSearch(s => ({ ...s, [field]: '' }));
    }}
    onBlur={() => setTimeout(() => setRoleDropdown(null), 150)}
    onChange={e => setRoleSearch(s => ({ ...s, [field]: e.target.value }))}
    className="w-full pl-8 pr-3 py-2 text-[13px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]"
    />
    {selectedId && (
    <button
    type="button"
    onClick={() => { setGroupRoleAssignments(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
    className="absolute right-2 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] dark:hover:text-[hsl(var(--text-primary))]"
    >
    <X size={13} />
    </button>
    )}
    </div>
    {roleDropdown === field && (
    <div className="absolute z-50 mt-1 w-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border-primary))] rounded-lg shadow-xl max-h-48 overflow-y-auto">
    <button
    type="button"
    onMouseDown={() => { setGroupRoleAssignments(f => ({ ...f, [field]: null })); setRoleDropdown(null); }}
    className="w-full text-left px-3 py-2 text-[12px] text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 border-b border-[hsl(var(--border-primary))]"
    >
    Sin asignar
    </button>
    {isLoading ? (
    <div className="px-3 py-3 text-[12px] text-[hsl(var(--text-secondary))] text-center">Buscando...</div>
    ) : results.length === 0 ? (
    <div className="px-3 py-3 text-[12px] text-[hsl(var(--text-secondary))] text-center">Sin resultados</div>
    ) : results.map(m => {
    const name = m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim();
    return (
    <button
    key={m.id}
    type="button"
    onMouseDown={() => {
    setPersonaCache(c => ({ ...c, [m.id]: m }));
    setGroupRoleAssignments(f => ({ ...f, [field]: m.id }));
    setRoleDropdown(null);
    setRoleSearch(s => ({ ...s, [field]: '' }));
    }}
    className="w-full text-left px-3 py-2 text-[12px] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/5 flex items-center justify-between gap-2"
    >
    <span className="font-medium">{name}</span>
    {m.church_role && <span className="text-[10px] text-[hsl(var(--text-secondary))] shrink-0">{m.church_role}</span>}
    </button>
    );
    })}
    </div>
    )}
    </div>
    );
    })}
    </div>
    </WorkspaceDrawer>
  );
}
