import type { Dispatch, SetStateAction } from 'react';
import { useEffect, useState } from 'react';
import { Loader2, Search, UserCheck, UserPlus, Users, X } from 'lucide-react';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import type { SessionRow } from '../../../types';
import { useRemotePersonaSearch } from '../useStrategyDetail';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { AttendancePersona, SearchablePersona } from '../strategyDetailShared';

export type NewVisitorForm = {
  first_name: string;
  last_name: string;
  phone: string;
  whatsapp: string;
  email: string;
  address: string;
};

const EMPTY_VISITOR_FORM: NewVisitorForm = {
  first_name: '',
  last_name: '',
  phone: '',
  whatsapp: '',
  email: '',
  address: '',
};

const getErrorMessage = (error: unknown, fallback: string) =>
  error instanceof Error && error.message ? error.message : fallback;

interface AttendanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  token: string | null;
  session: SessionRow | null;
  personas: AttendancePersona[];
  setPersonas: Dispatch<SetStateAction<AttendancePersona[]>>;
  saving: boolean;
  canManage: boolean;
  onSave: () => void;
  onVisitorCreated: () => void;
  getRoleColor: (role: string) => string;
  getRoleLabel: (value: string, fallback?: string) => string;
}

export default function AttendanceDrawer({
  isOpen,
  onClose,
  token,
  session,
  personas,
  setPersonas,
  saving,
  canManage,
  onSave,
  onVisitorCreated,
  getRoleColor,
  getRoleLabel,
}: AttendanceDrawerProps) {
  const [showVisitorSearch, setShowVisitorSearch] = useState(false);
  const [visitorSearch, setVisitorSearch] = useState('');
  const [visitorSearchLoading, setVisitorSearchLoading] = useState(false);
  const [visitorSearchResults, setVisitorSearchResults] = useState<SearchablePersona[]>([]);
  const [showNewVisitorForm, setShowNewVisitorForm] = useState(false);
  const [newVisitorForm, setNewVisitorForm] = useState<NewVisitorForm>(EMPTY_VISITOR_FORM);
  const [savingNewVisitor, setSavingNewVisitor] = useState(false);
  const { search: searchVisitors, cancel: cancelVisitorSearch } = useRemotePersonaSearch(token);

  // Reset visitor search state when the drawer opens (replicates the resets
  // previously performed by openAttendanceDrawer in page.tsx).
  useEffect(() => {
    if (!isOpen) return;
    setShowVisitorSearch(false);
    setVisitorSearch('');
    setVisitorSearchResults([]);
    setShowNewVisitorForm(false);
    setNewVisitorForm(EMPTY_VISITOR_FORM);
  }, [isOpen]);

  const open = isOpen && canManage;

  useEffect(() => {
    if (!token || !showVisitorSearch) return;
    const q = visitorSearch.trim();
    if (q.length < 3) {
    setVisitorSearchLoading(false);
    setVisitorSearchResults([]);
    cancelVisitorSearch();
    return;
    }
    setVisitorSearchLoading(true);
    const handle = setTimeout(() => {
    searchVisitors(q, 10)
    .then(results => {
    setVisitorSearchResults(results);
    })
    .catch(() => {
    setVisitorSearchResults([]);
    })
    .finally(() => {
    setVisitorSearchLoading(false);
    });
    }, 300);
    return () => {
    clearTimeout(handle);
    cancelVisitorSearch();
    };
  }, [cancelVisitorSearch, searchVisitors, showVisitorSearch, token, visitorSearch]);

  const handleCreateNewVisitor = async () => {
    if (!session) return;
    setSavingNewVisitor(true);
    try {
    const res = await apiFetch<{ status: string; persona_id: string; first_name?: string | null; last_name?: string | null }>('/evangelism/groups/visitors', {
    method: 'POST', token,
    body: {
    first_name: newVisitorForm.first_name || null,
    last_name: newVisitorForm.last_name || null,
    phone: newVisitorForm.phone || null,
    whatsapp: newVisitorForm.whatsapp || null,
    email: newVisitorForm.email || null,
    address: newVisitorForm.address || null,
    grupo_id: session.grupo_id,
    session_id: session.id,
    },
    });
    const realName = [res.first_name, res.last_name].filter(Boolean).join(' ') || 'Visitante';
    if (res.status === 'duplicate') {
    toast.info(`Ya existe una persona con ese teléfono: ${realName}`);
    } else {
    toast.success(`Visitante "${realName}" registrado`);
    }
    setPersonas(prev => {
    const nextPersona = {
    persona_id: res.persona_id,
    name: realName,
    role: 'visitante',
    role_label: 'Visitante',
    status: 'first_time' as const,
    notes: '',
    };
    if (prev.some(persona => persona.persona_id === res.persona_id)) {
    return prev.map(persona => persona.persona_id === res.persona_id ? { ...persona, ...nextPersona } : persona);
    }
    return [...prev, nextPersona];
    });
    setVisitorSearchResults(prev => {
    if (prev.some(persona => persona.id === res.persona_id)) return prev;
    return [
    ...prev,
    {
    id: res.persona_id,
    first_name: res.first_name || '',
    last_name: res.last_name || '',
    nombre_completo: realName,
    church_role: 'Visitante',
    },
    ];
    });
    setNewVisitorForm(EMPTY_VISITOR_FORM);
    setShowNewVisitorForm(false);
    onVisitorCreated();
    } catch (error: unknown) {
    toast.error('Error al registrar visitante: ' + getErrorMessage(error, 'Intente de nuevo'));
    } finally { setSavingNewVisitor(false); }
  };

  return (
    <WorkspaceDrawer isOpen={open} onClose={onClose}
    title="Registrar Asistencia"
    subtitle={session ? new Date(session.session_date.split('T')[0] + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : ''}
    actions={<>
    <button onClick={onClose}
    className="px-4 py-1.5 text-[12px] font-semibold text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] rounded-md transition-colors">Cancelar</button>
    <button onClick={onSave} disabled={saving}
    className="px-4 py-1.5 text-[12px] font-semibold text-white bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] disabled:opacity-50 rounded-md transition-colors flex items-center gap-2">
    {saving ? <><Loader2 size={14} className="animate-spin" />Guardando...</> : <><UserCheck size={14} />Guardar asistencia</>}
    </button>
    </>}>
    <div className="space-y-3">
    {personas.length === 0 && !showVisitorSearch ? (
    <div className="text-center py-8">
    <Users size={32} className="text-[hsl(var(--text-secondary))] mx-auto mb-2" />
    <p className="text-xs text-[hsl(var(--text-secondary))]">Este grupo no tiene personas asignadas</p>
    <p className="text-[11px] text-[hsl(var(--text-secondary))] mt-1">Agrega personas desde la pestaña Grupos</p>
    </div>
    ) : (
    <>
    {personas.length > 0 && (
    <div className="flex items-center gap-2 text-[11px] text-[hsl(var(--text-secondary))] mb-1">
    <span>{personas.filter(m => m.status === 'present').length} presentes</span>
    <span>·</span>
    <span>{personas.filter(m => m.status === 'absent').length} ausentes</span>
    <span>·</span>
    <span className="text-[hsl(var(--primary))]">{personas.filter(m => m.status === 'first_time').length} primera vez</span>
    </div>
    )}
    <div className="space-y-2">
    {personas.map((m, i) => (
    <div key={m.persona_id} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg ${m.status === 'first_time' ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800' : 'bg-[hsl(var(--bg-muted))]'}`}>
    <div className="flex-1 min-w-0">
    <div className="flex items-center gap-1.5">
    <p className="text-xs font-semibold text-[hsl(var(--text-primary))] ">{m.name}</p>
    {m.status === 'first_time' && <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-[hsl(var(--primary))] text-white">1ª vez</span>}
    </div>
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${getRoleColor(m.role)}`}>
    {getRoleLabel(m.role, m.role_label)}
    </span>
    </div>
    <div className="flex items-center gap-1">
    {([
    { status: 'present', label: 'P', cls: 'bg-green-100 text-[hsl(var(--secondary))] dark:bg-green-900/30 dark:text-[hsl(var(--secondary))]', activeCls: 'ring-2 ring-green-500' },
    { status: 'absent', label: 'A', cls: 'bg-red-100 text-[hsl(var(--destructive))] dark:bg-red-900/30 dark:text-[hsl(var(--destructive))]', activeCls: 'ring-2 ring-red-500' },
    { status: 'first_time', label: '1°', cls: 'bg-blue-100 text-[hsl(var(--primary))] dark:bg-blue-900/30 dark:text-[hsl(var(--primary))]', activeCls: 'ring-2 ring-blue-500' },
    ] as const).map(opt => (
    <button key={opt.status}
    onClick={() => setPersonas(prev => prev.map((x, j) => j === i ? { ...x, status: opt.status } : x))}
    className={`w-8 h-8 rounded-lg text-[11px] font-bold transition-all ${opt.cls} ${m.status === opt.status ? opt.activeCls : 'opacity-50 hover:opacity-100'}`}>
    {opt.label}
    </button>
    ))}
    {m.role === 'visitante' && (
    <button onClick={() => setPersonas(prev => prev.filter((_, j) => j !== i))}
    className="w-7 h-7 ml-1 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-red-50 hover:text-[hsl(var(--destructive))] dark:hover:bg-red-900/20 transition-colors">
    <X size={12} />
    </button>
    )}
    </div>
    </div>
    ))}
    </div>
    </>
    )}

    {/* Agregar visitante */}
    <div className="pt-2 border-t border-[hsl(var(--border-primary))]">
    {!showVisitorSearch && !showNewVisitorForm ? (
    <div className="flex gap-2">
    <button onClick={() => setShowVisitorSearch(true)}
    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-dashed border-[hsl(var(--border-primary))] dark:border-white/20 text-xs text-[hsl(var(--text-secondary))] hover:border-blue-400 hover:text-[hsl(var(--primary))] dark:hover:border-blue-700 dark:hover:text-[hsl(var(--primary))] transition-colors">
    <Search size={13} />Buscar existente
    </button>
    <button onClick={() => setShowNewVisitorForm(true)}
    className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg border border-dashed border-[hsl(var(--border-primary))] dark:border-white/20 text-xs text-[hsl(var(--text-secondary))] hover:border-green-400 hover:text-[hsl(var(--secondary))] dark:hover:border-green-700 dark:hover:text-[hsl(var(--secondary))] transition-colors">
    <UserPlus size={13} />Crear persona nueva
    </button>
    </div>
    ) : showVisitorSearch ? (
    <div className="space-y-2">
    <div className="flex items-center gap-2">
    <div className="relative flex-1">
    {visitorSearchLoading
    ? <Loader2 size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--primary))] animate-spin" />
    : <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />}
    <input
    autoFocus
    value={visitorSearch}
    onChange={e => setVisitorSearch(e.target.value)}
    placeholder="Buscar persona por nombre..."
    className="w-full pl-8 pr-3 py-2 text-[12px] bg-[hsl(var(--bg-muted))] border border-[hsl(var(--border-primary))] rounded-lg text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-[hsl(var(--primary))]"
    />
    </div>
    <button onClick={() => { setShowVisitorSearch(false); setVisitorSearch(''); }}
    className="w-8 h-8 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-muted))] dark:hover:bg-white/10">
    <X size={14} />
    </button>
    </div>
    {visitorSearch.trim().length >= 3 && (
    <div className="max-h-40 overflow-y-auto space-y-1 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] p-1">
    {visitorSearchResults
    .filter(m => !personas.find(a => a.persona_id === m.id))
    .map(m => (
    <button key={m.id}
    onClick={() => {
    setPersonas(prev => [...prev, {
    persona_id: m.id,
    name: m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim(),
    role: 'visitante',
    role_label: 'Visitante',
    status: 'first_time',
    notes: '',
    }]);
    setVisitorSearch('');
    setShowVisitorSearch(false);
    }}
    className="w-full text-left px-3 py-2 rounded-md text-xs text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--bg-muted))] flex items-center gap-2 transition-colors">
    <UserPlus size={12} className="text-[hsl(var(--primary))] shrink-0" />
    <span className="font-medium">{m.nombre_completo || `${m.first_name ?? ''} ${m.last_name ?? ''}`.trim()}</span>
    {m.church_role && <span className="text-[hsl(var(--text-secondary))] text-[10px]">({m.church_role})</span>}
    </button>
    ))}
    {!visitorSearchLoading && visitorSearchResults.filter(m => !personas.find(a => a.persona_id === m.id)).length === 0 && (
    <p className="text-center py-3 text-xs text-[hsl(var(--text-secondary))]">No se encontraron personas</p>
    )}
    </div>
    )}
    {visitorSearch.trim().length > 0 && visitorSearch.trim().length < 3 && (
    <p className="text-[11px] text-[hsl(var(--text-secondary))]">Escribe al menos 3 caracteres para buscar en la sede</p>
    )}
    </div>
    ) : (
    /* Formulario crear persona nueva */
    <div className="space-y-3 rounded-lg border border-[hsl(var(--border-primary))] bg-[hsl(var(--bg-muted))] dark:bg-black/20 p-3">
    <div className="flex items-center justify-between mb-1">
    <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] uppercase tracking-wide">Nueva persona visitante</span>
    <button onClick={() => { setShowNewVisitorForm(false); setNewVisitorForm(EMPTY_VISITOR_FORM); }}
    className="w-6 h-6 flex items-center justify-center rounded text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--bg-primary))] dark:hover:bg-white/10">
    <X size={13} />
    </button>
    </div>
    <div className="grid grid-cols-2 gap-2">
    <div>
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Nombres</label>
    <input value={newVisitorForm.first_name} onChange={e => setNewVisitorForm(p => ({ ...p, first_name: e.target.value }))}
    placeholder="Opcional"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    <div>
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Apellidos</label>
    <input value={newVisitorForm.last_name} onChange={e => setNewVisitorForm(p => ({ ...p, last_name: e.target.value }))}
    placeholder="Opcional"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    <div>
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Teléfono</label>
    <input value={newVisitorForm.phone} onChange={e => setNewVisitorForm(p => ({ ...p, phone: e.target.value }))}
    placeholder="Opcional" type="tel"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    <div>
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">WhatsApp</label>
    <input value={newVisitorForm.whatsapp} onChange={e => setNewVisitorForm(p => ({ ...p, whatsapp: e.target.value }))}
    placeholder="Opcional" type="tel"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    <div className="col-span-2">
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Email</label>
    <input value={newVisitorForm.email} onChange={e => setNewVisitorForm(p => ({ ...p, email: e.target.value }))}
    placeholder="Opcional" type="email"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    <div className="col-span-2">
    <label className="block text-[10px] text-[hsl(var(--text-secondary))] mb-0.5">Dirección</label>
    <input value={newVisitorForm.address} onChange={e => setNewVisitorForm(p => ({ ...p, address: e.target.value }))}
    placeholder="Opcional"
    className="w-full py-1.5 px-2 text-[12px] bg-[hsl(var(--bg-primary))] dark:bg-black/30 border border-[hsl(var(--border-primary))] rounded-md text-[hsl(var(--text-primary))] outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]" />
    </div>
    </div>
    <button onClick={handleCreateNewVisitor} disabled={savingNewVisitor}
    className="w-full py-2 rounded-lg text-[12px] font-semibold text-white bg-[hsl(var(--secondary))] hover:bg-[hsl(var(--secondary))] disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
    {savingNewVisitor ? <><Loader2 size={13} className="animate-spin" />Guardando...</> : <><UserPlus size={13} />Registrar visitante</>}
    </button>
    </div>
    )}
    </div>
    </div>
    </WorkspaceDrawer>
  );
}
