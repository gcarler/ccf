import type { Dispatch, SetStateAction } from 'react';
import { Plus, X } from 'lucide-react';
import type { CustomRole } from '../strategyDetailShared';

interface CustomRolesPanelProps {
  customRoles: CustomRole[];
  loadingRoles: boolean;
  showRoleForm: boolean;
  setShowRoleForm: Dispatch<SetStateAction<boolean>>;
  newRoleName: string;
  setNewRoleName: (v: string) => void;
  newRoleDesc: string;
  setNewRoleDesc: (v: string) => void;
  editDefaultRoleId: string | null | undefined;
  setEditDefaultRoleId: Dispatch<SetStateAction<string | null | undefined>>;
  canManage: boolean;
  onCreateRole: () => void;
  onRequestDeleteRole: (role: CustomRole) => void;
}

export default function CustomRolesPanel({
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
  canManage,
  onCreateRole,
  onRequestDeleteRole,
}: CustomRolesPanelProps) {
  return (
    <div className="bg-[hsl(var(--bg-secondary))] border border-[hsl(var(--border-primary))] rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">Roles Personalizados</h3>
        {canManage ? (
          <button onClick={() => setShowRoleForm(!showRoleForm)}
          className="text-[11px] font-bold text-[hsl(var(--primary))] hover:text-[hsl(var(--primary))] flex items-center gap-1">
          <Plus size={12} />{showRoleForm ? 'Cancelar' : 'Agregar'}
          </button>
        ) : null}
      </div>

      <div className="mb-3">
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Rol por defecto</label>
        <select
          value={editDefaultRoleId ?? ''}
          onChange={e => setEditDefaultRoleId(e.target.value || null)}
          disabled={customRoles.length === 0 || !canManage}
          className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors disabled:opacity-60"
        >
          <option value="">Sin rol por defecto</option>
          {customRoles.map(role => (
            <option key={role.id} value={role.id}>
              {role.nombre_rol}
            </option>
          ))}
        </select>
        <p className="mt-1 text-[10px] text-[hsl(var(--text-secondary))]">
          Este rol se usa como base al agregar personas al grupo.
        </p>
      </div>

      {canManage && showRoleForm && (
        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg space-y-2">
          <input value={newRoleName} onChange={e => setNewRoleName(e.target.value)}
          placeholder="Nombre del rol (ej: Coordinador de zona)"
          className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
          <input value={newRoleDesc} onChange={e => setNewRoleDesc(e.target.value)}
          placeholder="Descripción (opcional)"
          className="w-full px-2.5 py-1.5 text-[12px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none" />
          <button onClick={onCreateRole} disabled={!newRoleName.trim()}
          className="px-3 py-1.5 text-[11px] font-bold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-lg transition-colors">
          Crear Rol
          </button>
        </div>
      )}

      {loadingRoles ? (
        <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Cargando...</p>
      ) : customRoles.length === 0 ? (
        <p className="text-[11px] text-[hsl(var(--text-secondary))] italic">Sin roles personalizados</p>
      ) : (
        <div className="space-y-1.5">
          {customRoles.map(r => (
            <div key={r.id} className="flex items-center justify-between px-2.5 py-1.5 bg-[hsl(var(--bg-primary))] rounded-lg border border-[hsl(var(--border-primary))]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[12px] font-semibold text-[hsl(var(--text-primary))] ">{r.nombre_rol}</span>
                  {editDefaultRoleId === r.id && (
                  <span className="px-1.5 py-0.5 rounded bg-blue-100 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-blue-300">
                  Defecto
                  </span>
                  )}
                </div>
                {r.descripcion && <p className="text-[10px] text-[hsl(var(--text-secondary))]">{r.descripcion}</p>}
              </div>
              {canManage ? (
                <button onClick={() => onRequestDeleteRole(r)} className="p-1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--destructive))] rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors">
                  <X size={12} />
                </button>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
