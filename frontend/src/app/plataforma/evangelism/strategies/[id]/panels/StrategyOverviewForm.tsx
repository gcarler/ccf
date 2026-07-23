import type { Dispatch, SetStateAction } from 'react';
import { motion } from 'framer-motion';
import { Save } from 'lucide-react';

interface OverviewFormProps {
  editName: string;
  setEditName: (v: string) => void;
  editDesc: string;
  setEditDesc: (v: string) => void;
  editType: string;
  setEditType: (v: string) => void;
  editStatus: 'active' | 'pending' | 'done';
  setEditStatus: Dispatch<SetStateAction<'active' | 'pending' | 'done'>>;
  editClaseRaiz: string;
  setEditClaseRaiz: (v: string) => void;
  editActiva: boolean;
  setEditActiva: (v: boolean) => void;
  editRecurrence: string | null;
  setEditRecurrence: (v: string | null) => void;
  editStartDate: string;
  setEditStartDate: (v: string) => void;
  editEndDate: string;
  setEditEndDate: (v: string) => void;
  canManage: boolean;
  saving: boolean;
  onSave: () => void;
}

const isStrategyStatus = (value: string): value is 'active' | 'pending' | 'done' =>
  ['active', 'pending', 'done'].includes(value);

export default function StrategyOverviewForm({
  editName,
  setEditName,
  editDesc,
  setEditDesc,
  editType,
  setEditType,
  editStatus,
  setEditStatus,
  editClaseRaiz,
  setEditClaseRaiz,
  editActiva,
  setEditActiva,
  editRecurrence,
  setEditRecurrence,
  editStartDate,
  setEditStartDate,
  editEndDate,
  setEditEndDate,
  canManage,
  saving,
  onSave,
}: OverviewFormProps) {
  return (
    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--surface-1))] border border-[hsl(var(--border-primary))] rounded-lg p-4 space-y-4">
      <div>
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Nombre</label>
        <input type="text" value={editName} onChange={e => setEditName(e.target.value)} readOnly={!canManage}
          className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
      </div>
      <div>
        <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Descripción</label>
        <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={3} readOnly={!canManage}
          className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors resize-none"
          placeholder="Detalles sobre la estrategia..." />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Tipo</label>
          <select value={editType} onChange={e => setEditType(e.target.value)} disabled={!canManage}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
            <option value="">General</option>
            <option value="Geográfica">Geográfica</option>
            <option value="Temática">Temática</option>
            <option value="Sectorial">Sectorial</option>
            <option value="Poblacional">Poblacional</option>
            <option value="Servicios (Cultos)">Servicios (Cultos)</option>
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Estado</label>
          <select value={editStatus} onChange={e => { if (isStrategyStatus(e.target.value)) setEditStatus(e.target.value); }} disabled={!canManage}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
            <option value="pending">No iniciada</option>
            <option value="active">Iniciada</option>
            <option value="done">Terminada</option>
          </select>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Clase Raíz</label>
          <div className="flex gap-2">
            {['relacional', 'evento_masivo', 'sectorial'].map(c => (
              <button key={c} onClick={() => canManage && setEditClaseRaiz(c)} disabled={!canManage}
                className={`flex-1 px-2 py-1.5 text-[10px] font-bold rounded-lg transition-all capitalize ${
                editClaseRaiz === c
                ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border-primary))]'
                }`}>
                {c === 'evento_masivo' ? 'Evento Masivo' : c}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Activa</label>
          <button onClick={() => canManage && setEditActiva(!editActiva)} disabled={!canManage}
            className={`w-full px-3 py-2 rounded-lg text-[12px] font-bold transition-all text-left ${
            editActiva
            ? 'bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success))]/30 text-success-text dark:text-success-text border border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]'
            : 'bg-[hsl(var(--bg-muted))] text-[hsl(var(--text-secondary))] border border-[hsl(var(--border-primary))]'
            }`}>
            {editActiva ? 'Activa' : 'Inactiva'}
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Recurrencia</label>
          <select value={editRecurrence || ''} onChange={e => setEditRecurrence(e.target.value || null)} disabled={!canManage}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors">
            <option value="">Sin recurrencia</option>
            <option value="SEMANAL">Semanal</option>
            <option value="QUINCENAL">Quincenal</option>
            <option value="MENSUAL">Mensual</option>
            <option value="BIMENSUAL">Bimensual</option>
            <option value="TRIMESTRAL">Trimestral</option>
            <option value="SEMESTRAL">Semestral</option>
            <option value="ANUAL">Anual</option>
            <option value="EVENTO_UNICO">Evento único</option>
          </select>
        </div>
        <div>
          <input type="date" value={editStartDate} onChange={e => setEditStartDate(e.target.value)} readOnly={!canManage}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
        </div>
        <div>
          <label className="block text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))] mb-1">Fecha de fin</label>
          <input type="date" value={editEndDate} onChange={e => setEditEndDate(e.target.value)} readOnly={!canManage}
            className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] text-sm text-[hsl(var(--text-primary))] focus:border-[hsl(var(--primary))] focus:outline-none transition-colors" />
        </div>
      </div>
      {canManage ? (
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-[hsl(var(--border-primary))]">
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
          onClick={onSave} disabled={saving}
          className="inline-flex items-center gap-2 px-4 h-9 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-semibold hover:bg-[hsl(var(--primary))] disabled:opacity-60 transition-colors">
          <Save size={14} />{saving ? 'Guardando...' : 'Guardar cambios'}
          </motion.button>
        </div>
      ) : null}
    </div>
  );
}
