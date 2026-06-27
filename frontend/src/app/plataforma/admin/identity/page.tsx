"use client";

import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import Skeleton from '@/components/ui/Skeleton';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';
import {
AlertTriangle,
BookOpen,Briefcase,
Clock,
Crown,
Eye,
HeartHandshake,
Key,
Loader2,
Save,
Search,
Shield,
UserCheck,
UserPlus,
Users,
Zap
} from 'lucide-react';
import { useCallback,useEffect,useState } from 'react';

const CHURCH_ROLES = [
    { value: 'LIDER', label: 'Líder', color: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400' },
    { value: 'SERVIDOR', label: 'Servidor', color: 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-[hsl(var(--primary))]' },
    { value: 'MIEMBRO_BAUTIZADO', label: 'Persona Bautizado', color: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400' },
    { value: 'SIMPATIZANTE', label: 'Simpatizante', color: 'bg-slate-50 text-slate-600 dark:bg-white/5 dark:text-slate-400' },
    { value: 'VISITANTE_SERVICIO', label: 'Visitante (Servicio)', color: 'bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-blue-400' },
    { value: 'VISITANTE_EVANGELISMO', label: 'Visitante (Evangelismo)', color: 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400' },
    { value: 'VISITANTE_ONLINE', label: 'Visitante (Online)', color: 'bg-cyan-50 text-cyan-600 dark:bg-cyan-500/10 dark:text-cyan-400' },
];

const MINISTRIES = ['APOSTOL', 'PROFETA', 'EVANGELISTA', 'PASTOR', 'MAESTRO'];

const PLATFORM_ROLES = ['ADMINISTRADOR', 'GESTOR', 'EDITOR', 'LECTOR', 'MIEMBRO'];

interface UserSummary {
    id: string;
    username: string;
    email: string;
    role: string;
    is_active: boolean;
}

interface KernelProfile {
    activity_status: string;
    church_role: string | null;
    church_role_history: Array<{ role: string; changed_at: string; reason: string }>;
    ministries: Array<{ ministry: string; is_primary: boolean }>;
    platform_roles: Array<{ role: string; assigned_at: string }>;
    effective_permissions: Record<string, string>;
}

export default function IdentityManagementPage() {
    const { token } = useAuth();
    const { addToast } = useToast();
    const [users, setUsers] = useState<UserSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [selectedUser, setSelectedUser] = useState<UserSummary | null>(null);
    const [profile, setProfile] = useState<KernelProfile | null>(null);
    const [profileLoading, setProfileLoading] = useState(false);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [isCreateOpen, setIsCreateOpen] = useState(false);

    // Form state
    const [activityStatus, setActivityStatus] = useState('ACTIVO');
    const [churchRole, setChurchRole] = useState('');
    const [churchRoleReason, setChurchRoleReason] = useState('');
    const [ministries, setMinistries] = useState<string[]>([]);
    const [primaryMinistry, setPrimaryMinistry] = useState('');
    const [platformRole, setPlatformRole] = useState('MIEMBRO');

    // New user form
    const [newUsername, setNewUsername] = useState('');
    const [newEmail, setNewEmail] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [newRole, setNewRole] = useState('MIEMBRO');

    const fetchUsers = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiFetch<UserSummary[]>('/admin/users', { token });
            setUsers(Array.isArray(data) ? data : []);
        } catch {
            addToast('Error al cargar usuarios', 'error');
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => { fetchUsers(); }, [fetchUsers]);

    const loadProfile = async (user: UserSummary) => {
        setProfileLoading(true);
        try {
            const data = await apiFetch<KernelProfile>(`/kernel/profile/${user.id}`, { token });
            setProfile(data);
            setActivityStatus(data.activity_status || 'ACTIVO');
            setChurchRole(data.church_role || '');
            setMinistries((data.ministries || []).map((m: any) => m.ministry));
            setPrimaryMinistry((data.ministries || []).find((m: any) => m.is_primary)?.ministry || '');
            setPlatformRole(data.platform_roles?.[0]?.role || 'MIEMBRO');
        } catch {
            addToast('Error al cargar perfil kernel', 'error');
        } finally {
            setProfileLoading(false);
        }
    };

    const handleSelectUser = (user: UserSummary) => {
        setSelectedUser(user);
        loadProfile(user);
        setIsDrawerOpen(true);
    };

    const handleSaveProfile = async () => {
        if (!selectedUser) return;
        setSaving(true);
        try {
            // Update activity status
            await apiFetch(`/kernel/status/${selectedUser.id}`, {
                method: 'PUT', token,
                body: { status: activityStatus },
            });

            // Update church role
            if (churchRole && churchRole !== profile?.church_role) {
                await apiFetch(`/kernel/church-role/${selectedUser.id}`, {
                    method: 'PUT', token,
                    body: { church_role: churchRole, reason: churchRoleReason || 'Cambio manual desde admin' },
                });
            }

            // Update ministries
            const currentMinistries = (profile?.ministries || []).map((m: any) => m.ministry);
            const toAdd = ministries.filter(m => !currentMinistries.includes(m));
            const toRemove = currentMinistries.filter(m => !ministries.includes(m));

            for (const ministry of toAdd) {
                await apiFetch(`/kernel/ministries/${selectedUser.id}`, {
                    method: 'POST', token,
                    body: { ministry, is_primary: ministry === primaryMinistry },
                });
            }
            for (const ministry of toRemove) {
                await apiFetch(`/kernel/ministries/${selectedUser.id}/${ministry}`, { method: 'DELETE', token });
            }
            if (primaryMinistry && ministries.includes(primaryMinistry)) {
                await apiFetch(`/kernel/ministries/${selectedUser.id}/${primaryMinistry}/primary`, { method: 'PUT', token });
            }

            const currentRole = profile?.platform_roles?.[0]?.role;
            if (platformRole !== currentRole) {
                await apiFetch(`/admin/users/${selectedUser.id}`, {
                    method: 'PATCH', token,
                    body: { role: platformRole },
                });
            }

            addToast('Perfil de identidad actualizado', 'success');
            setIsDrawerOpen(false);
            fetchUsers();
        } catch (e: any) {
            addToast('Error al guardar: ' + (e.message || 'Intente de nuevo'), 'error');
        } finally {
            setSaving(false);
        }
    };

    const handleCreateUser = async () => {
        if (!newUsername || !newEmail || !newPassword) {
            addToast('Todos los campos son requeridos', 'error');
            return;
        }
        setSaving(true);
        try {
            await apiFetch('/admin/users', {
                method: 'POST', token,
                body: { username: newUsername, email: newEmail, password: newPassword, role: newRole },
            });
            addToast('Usuario creado exitosamente', 'success');
            setIsCreateOpen(false);
            setNewUsername('');
            setNewEmail('');
            setNewPassword('');
            setNewRole('MIEMBRO');
            fetchUsers();
        } catch (e: any) {
            addToast('Error al crear: ' + (e.message || 'Intente de nuevo'), 'error');
        } finally {
            setSaving(false);
        }
    };

    const handleResetPassword = async () => {
        if (!selectedUser) return;
        const newPassword = prompt('Nueva contraseña para ' + selectedUser.username + ':');
        if (!newPassword || newPassword.length < 6) {
            addToast('La contraseña debe tener al menos 6 caracteres', 'error');
            return;
        }
        setSaving(true);
        try {
            await apiFetch(`/admin/users/${selectedUser.id}`, {
                method: 'PATCH', token,
                body: { password: newPassword },
            });
            addToast('Contraseña actualizada', 'success');
        } catch (e: any) {
            addToast('Error: ' + (e.message || 'Intente de nuevo'), 'error');
        } finally {
            setSaving(false);
        }
    };

    const toggleMinistry = (ministry: string) => {
        setMinistries(prev => prev.includes(ministry) ? prev.filter(m => m !== ministry) : [...prev, ministry]);
    };

    const filteredUsers = users.filter(u =>
        u.username.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()) ||
        u.role.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="flex flex-col h-full bg-[#f8fafc] dark:bg-[#0b0d11] overflow-hidden font-sans">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Administración', icon: Shield }, { label: 'Gestión de Identidad', icon: Users }]}
                onSearch={setSearch}
                rightActions={
                    <button onClick={() => setIsCreateOpen(true)} className="flex items-center gap-2 px-3 py-2 bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-[hsl(var(--primary))]">
                        <UserPlus size={14} /> Nuevo Usuario
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin p-4">
                <div className="space-y-4">
                    {/* Header */}
                    <div>
                        <h1 className="text-lg font-bold text-slate-800 dark:text-white tracking-tighter">
                            Identidad <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-sky-600">Integral.</span>
                        </h1>
                        <p className="text-slate-500 dark:text-slate-400 font-medium">
                            Gestiona el estado vital, roles ministeriales, oficio espiritual y permisos de plataforma de cada persona.
                        </p>
                    </div>

                    {/* Stats */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <StatCard icon={UserCheck} label="Usuarios Activos" value={users.filter(u => u.is_active).length} color="text-emerald-500" bg="bg-emerald-50 dark:bg-emerald-500/10" />
                        <StatCard icon={AlertTriangle} label="Usuarios Inactivos" value={users.filter(u => !u.is_active).length} color="text-slate-400" bg="bg-slate-50 dark:bg-white/5" />
                        <StatCard icon={Crown} label="Roles operativos" value={users.filter(u => u.role !== 'MIEMBRO').length} color="text-amber-500" bg="bg-amber-50 dark:bg-amber-500/10" />
                        <StatCard icon={Users} label="Total Usuarios" value={users.length} color="text-[hsl(var(--primary))]" bg="bg-blue-50 dark:bg-blue-500/10" />
                    </div>

                    {/* Users Table */}
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/20 dark:shadow-none overflow-x-auto">
                        {loading ? (
                            <div className="p-4 space-y-3">
                                {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-10 w-full rounded-lg" />)}
                            </div>
                        ) : filteredUsers.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 text-center">
                                <Search size={32} className="text-slate-300 mb-2" />
                                <p className="text-sm font-medium text-slate-400">Sin resultados</p>
                            </div>
                        ) : (
                            <table className="w-full min-w-[520px] text-left border-collapse">
                                <thead>
                                    <tr className="bg-slate-50/50 dark:bg-black/20 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                                        <th className="px-4 py-2">Persona</th>
                                        <th className="px-4 py-2">Email</th>
                                        <th className="px-4 py-2">Rol Plataforma</th>
                                        <th className="px-4 py-2">Estado</th>
                                        <th className="px-4 py-2 text-right">Acciones</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                    {filteredUsers.map((user) => (
                                        <tr
                                            key={user.id}
                                            className="group hover:bg-slate-50 dark:hover:bg-white/5 transition-all cursor-pointer"
                                            onClick={() => handleSelectUser(user)}
                                        >
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-3">
                                                    <div className="size-9 rounded-lg bg-gradient-to-tr from-blue-600 to-sky-600 flex items-center justify-center text-white font-semibold text-xs">
                                                        {user.username.substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <p className="text-sm font-bold text-slate-800 dark:text-white">{user.username}</p>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2 text-xs text-slate-500">{user.email}</td>
                                            <td className="px-4 py-2">
                                                <span className={clsx(
                                                    "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[9px] font-semibold uppercase",
                                                    user.role === 'admin' ? "bg-sky-50 text-sky-600 dark:bg-sky-500/10 dark:text-sky-400" :
                                                    user.role === 'pastor' ? "bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-500/10 dark:text-blue-400" :
                                                    "bg-slate-100 text-slate-500 dark:bg-white/5 dark:text-slate-400"
                                                )}>
                                                    {user.role}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2">
                                                <div className="flex items-center gap-2">
                                                    <div className={clsx("size-2 rounded-full", user.is_active ? "bg-emerald-500" : "bg-slate-300")} />
                                                    <span className="text-[10px] font-semibold uppercase text-slate-500">{user.is_active ? 'Activo' : 'Inactivo'}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-2 text-right">
                                                <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleSelectUser(user); }}
                                                        className="p-2 hover:bg-blue-50 dark:hover:bg-blue-500/10 rounded-md transition-all text-slate-400 hover:text-[hsl(var(--primary))]"
                                                    >
                                                        <Eye size={16} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </main>

            {/* Identity Profile Drawer */}
            <WorkspaceDrawer
                isOpen={isDrawerOpen}
                onClose={() => setIsDrawerOpen(false)}
                title={selectedUser?.username || 'Perfil de Identidad'}
                subtitle={`Gestión integral de ${selectedUser?.username || 'la persona'}`}
                actions={
                    <>
                        <button className="px-3 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors" onClick={() => setIsDrawerOpen(false)}>Cancelar</button>
                        <button
                            disabled={saving || profileLoading}
                            className="px-4 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={handleSaveProfile}
                        >
                            {saving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                            {saving ? 'Guardando...' : 'Guardar Cambios'}
                        </button>
                    </>
                }
            >
                {profileLoading ? (
                    <div className="p-4 space-y-3">
                        {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
                    </div>
                ) : (
                    <div className="space-y-5 p-2 animate-in fade-in slide-in-from-right-4 duration-500">
                        {/* Estado Vital */}
                        <section>
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                <HeartHandshake size={14} className="text-rose-500" /> Estado Vital
                            </h4>
                            <div className="grid grid-cols-2 gap-2">
                                {[
                                    { value: 'ACTIVO', label: 'Activo', color: 'bg-emerald-500' },
                                    { value: 'INACTIVO', label: 'Inactivo', color: 'bg-slate-300' },
                                ].map(s => (
                                    <button
                                        key={s.value}
                                        onClick={() => setActivityStatus(s.value)}
                                        className={clsx(
                                            "flex items-center gap-2 p-3 rounded-lg border-2 transition-all",
                                            activityStatus === s.value
                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                                : "border-slate-100 dark:border-white/5 hover:border-slate-300"
                                        )}
                                    >
                                        <div className={clsx("size-3 rounded-full", s.color)} />
                                        <span className="text-xs font-semibold">{s.label}</span>
                                    </button>
                                ))}
                            </div>
                        </section>

                        {/* Rol en la Iglesia (Dimensión B) */}
                        <section>
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                <Crown size={14} className="text-amber-500" /> Rol en la Iglesia
                            </h4>
                            <div className="grid grid-cols-1 gap-1.5">
                                {CHURCH_ROLES.map(r => (
                                    <button
                                        key={r.value}
                                        onClick={() => setChurchRole(r.value)}
                                        className={clsx(
                                            "flex items-center justify-between p-2.5 rounded-lg border-2 transition-all",
                                            churchRole === r.value
                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                                : "border-slate-100 dark:border-white/5 hover:border-slate-300"
                                        )}
                                    >
                                        <span className={clsx("px-2 py-0.5 rounded text-[10px] font-semibold uppercase", r.color)}>{r.label}</span>
                                        {churchRole === r.value && <UserCheck size={14} className="text-[hsl(var(--primary))]" />}
                                    </button>
                                ))}
                            </div>
                            {churchRole && churchRole !== profile?.church_role && (
                                <input
                                    value={churchRoleReason}
                                    onChange={e => setChurchRoleReason(e.target.value)}
                                    placeholder="Razón del cambio..."
                                    className="mt-2 w-full px-3 py-2 text-xs bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:border-blue-500"
                                />
                            )}
                            {profile?.church_role_history && profile.church_role_history.length > 0 && (
                                <div className="mt-3 space-y-1">
                                    <p className="text-[10px] font-semibold text-slate-400 uppercase">Historial:</p>
                                    {profile.church_role_history.slice(0, 3).map((h, i) => (
                                        <div key={i} className="flex items-center gap-2 text-[10px] text-slate-500">
                                            <Clock size={10} />
                                            <span>{h.role}</span>
                                            <span className="text-slate-300">→</span>
                                            <span>{new Date(h.changed_at).toLocaleDateString()}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </section>

                        {/* Ministerios (Dimensión A) */}
                        <section>
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                <BookOpen size={14} className="text-emerald-500" /> Oficio Espiritual (Efesios 4:11)
                            </h4>
                            <div className="grid grid-cols-1 gap-1.5">
                                {MINISTRIES.map(m => (
                                    <button
                                        key={m}
                                        onClick={() => toggleMinistry(m)}
                                        className={clsx(
                                            "flex items-center justify-between p-2.5 rounded-lg border-2 transition-all",
                                            ministries.includes(m)
                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                                : "border-slate-100 dark:border-white/5 hover:border-slate-300"
                                        )}
                                    >
                                        <span className="text-xs font-semibold">{m}</span>
                                        {ministries.includes(m) && (
                                            ministries.indexOf(m) === 0 ? <Crown size={14} className="text-amber-500" /> : <UserCheck size={14} className="text-[hsl(var(--primary))]" />
                                        )}
                                    </button>
                                ))}
                            </div>
                            {ministries.length > 1 && (
                                <div className="mt-2">
                                    <label className="text-[10px] font-semibold text-slate-400 uppercase">Oficio principal:</label>
                                    <select
                                        value={primaryMinistry}
                                        onChange={e => setPrimaryMinistry(e.target.value)}
                                        className="mt-1 w-full px-3 py-2 text-xs bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:border-blue-500"
                                    >
                                        <option value="">Seleccionar...</option>
                                        {ministries.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                </div>
                            )}
                        </section>

                        {/* Roles de Plataforma */}
                        <section>
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                <Briefcase size={14} className="text-[hsl(var(--primary))]" /> Roles de Plataforma
                            </h4>
                            <div className="grid grid-cols-2 gap-1.5">
                                {PLATFORM_ROLES.map(r => (
                                    <button
                                        key={r}
                                        onClick={() => setPlatformRole(r)}
                                        className={clsx(
                                            "flex items-center gap-2 p-2.5 rounded-lg border-2 transition-all",
                                            platformRole === r
                                                ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                                : "border-slate-100 dark:border-white/5 hover:border-slate-300"
                                        )}
                                    >
                                        <span className="text-[10px] font-semibold uppercase">{r}</span>
                                        {platformRole === r && <UserCheck size={12} className="text-[hsl(var(--primary))] ml-auto" />}
                                    </button>
                                ))}
                            </div>
                        </section>

                        {/* Seguridad */}
                        <section>
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                <Key size={14} className="text-amber-500" /> Seguridad de Cuenta
                            </h4>
                            <button
                                onClick={handleResetPassword}
                                disabled={saving}
                                className="w-full p-3 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-lg text-[11px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 hover:bg-slate-100 transition-all flex items-center justify-center gap-3 disabled:opacity-50"
                            >
                                <Zap size={16} className="text-amber-500" /> Resetear Contraseña
                            </button>
                        </section>

                        {/* Permisos Efectivos */}
                        {profile?.effective_permissions && Object.keys(profile.effective_permissions).length > 0 && (
                            <section>
                                <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2 mb-3">
                                    <Shield size={14} className="text-[hsl(var(--primary))]" /> Permisos Efectivos
                                </h4>
                                <div className="flex flex-wrap gap-1">
                                    {Object.entries(profile.effective_permissions).map(([key, val]) => (
                                        <span key={key} className="px-2 py-0.5 bg-blue-50 dark:bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] dark:text-blue-400 rounded text-[9px] font-semibold uppercase">
                                            {key}: {val}
                                        </span>
                                    ))}
                                </div>
                            </section>
                        )}
                    </div>
                )}
            </WorkspaceDrawer>

            {/* Create User Drawer */}
            <WorkspaceDrawer
                isOpen={isCreateOpen}
                onClose={() => { setIsCreateOpen(false); setNewUsername(''); setNewEmail(''); setNewPassword(''); }}
                title="Nuevo Usuario"
                subtitle="Crear acceso ministerial"
                actions={
                    <>
                        <button className="px-3 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors" onClick={() => setIsCreateOpen(false)}>Cancelar</button>
                        <button
                            disabled={saving}
                            className="px-4 py-2 bg-[hsl(var(--primary))] hover:bg-[hsl(var(--primary))] text-white rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            onClick={handleCreateUser}
                        >
                            {saving ? <Loader2 className="animate-spin" size={14} /> : <UserPlus size={14} />}
                            {saving ? 'Creando...' : 'Crear Usuario'}
                        </button>
                    </>
                }
            >
                <div className="space-y-4 p-2">
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1 block">Nombre de usuario</label>
                        <input
                            value={newUsername}
                            onChange={e => setNewUsername(e.target.value)}
                            placeholder="ej: juan.perez"
                            className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1 block">Email</label>
                        <input
                            type="email"
                            value={newEmail}
                            onChange={e => setNewEmail(e.target.value)}
                            placeholder="ej: juan@ccf.com"
                            className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1 block">Contraseña</label>
                        <input
                            type="password"
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            placeholder="Mínimo 6 caracteres"
                            className="w-full px-3 py-2 text-sm bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-lg outline-none focus:border-blue-500"
                        />
                    </div>
                    <div>
                        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1 block">Rol de plataforma</label>
                        <div className="grid grid-cols-2 gap-1.5">
                            {PLATFORM_ROLES.map(r => (
                                <button
                                    key={r}
                                    onClick={() => setNewRole(r)}
                                    className={clsx(
                                        "flex items-center gap-2 p-2.5 rounded-lg border-2 transition-all",
                                        newRole === r
                                            ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                                            : "border-slate-100 dark:border-white/5 hover:border-slate-300"
                                    )}
                                >
                                    <span className="text-[10px] font-semibold uppercase">{r}</span>
                                    {newRole === r && <UserCheck size={12} className="text-[hsl(var(--primary))] ml-auto" />}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function StatCard({ icon: Icon, label, value, color, bg }: any) {
    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#15171c] rounded-lg border border-slate-100 dark:border-white/5 p-4 flex items-center gap-3">
            <div className={clsx("size-10 rounded-lg flex items-center justify-center", bg)}>
                <Icon size={20} className={color} />
            </div>
            <div>
                <p className="text-2xl font-bold text-slate-800 dark:text-white">{value}</p>
                <p className="text-[10px] font-semibold text-slate-400 uppercase">{label}</p>
            </div>
        </div>
    );
}
