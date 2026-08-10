import { Loader2, Save } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import type { StrategyGroup } from '../../../types';

export type SessionFormState = {
  grupo_id: string | number;
  session_date: string;
  topic: string;
  offering_amount: string;
  report_notes: string;
};

interface NewSessionDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  strategyName: string;
  groups: StrategyGroup[];
  form: SessionFormState;
  setForm: (updater: (f: SessionFormState) => SessionFormState) => void;
  saving: boolean;
  onSave: () => void;
}

export default function NewSessionDrawer({
  isOpen,
  onClose,
  strategyName,
  groups,
  form,
  setForm,
  saving,
  onSave,
}: NewSessionDrawerProps) {
  return (
    <WorkspaceDrawer isOpen={isOpen} onClose={onClose}
      title="Registrar sesión" subtitle={`Estrategia: ${strategyName}`}
      actions={<>
        <button onClick={onClose}
          className="px-4 py-1.5 text-sm font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
        <button onClick={onSave} disabled={saving}
          className="px-4 py-1.5 text-sm font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
          {saving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><Save size={14} />Guardar</>}
        </button>
      </>}>
      <div className="space-y-4">
        <div>
          <label htmlFor="session-group" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Grupo *</label>
          <select id="session-group" value={form.grupo_id} onChange={e => setForm(f => ({ ...f, grupo_id: e.target.value }))}
            className="w-full px-3 py-2 text-base bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))]">
            <option value="">Seleccionar grupo...</option>
            {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="session-date" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Fecha de la sesión *</label>
          <input id="session-date" type="date" value={form.session_date} onChange={e => setForm(f => ({ ...f, session_date: e.target.value }))}
            className="w-full px-3 py-2 text-base bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))]" />
        </div>
        <div>
          <label htmlFor="session-topic" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Tema de la sesión</label>
          <input id="session-topic" value={form.topic} onChange={e => setForm(f => ({ ...f, topic: e.target.value }))}
            placeholder="Ej: La fe que mueve montañas"
            className="w-full px-3 py-2 text-base bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))]" />
        </div>
        <div>
          <label htmlFor="session-offering" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Ofrenda recogida</label>
          <input id="session-offering" type="number" value={form.offering_amount} onChange={e => setForm(f => ({ ...f, offering_amount: e.target.value }))}
            placeholder="0.00"
            className="w-full px-3 py-2 text-base bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))]" />
        </div>
        <div>
          <label htmlFor="session-notes" className="text-xs font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wider mb-2 block">Notas de la sesión</label>
          <textarea id="session-notes" value={form.report_notes} onChange={e => setForm(f => ({ ...f, report_notes: e.target.value }))} rows={3}
            placeholder="Observaciones, peticiones de oración, novedades..."
            className="w-full px-3 py-2 text-base bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-[hsl(var(--primary))/0.2] focus:border-[hsl(var(--primary))] resize-none" />
        </div>
      </div>
    </WorkspaceDrawer>
  );
}
