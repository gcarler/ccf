"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
    Shield, 
    Users, 
    Lock, 
    Key, 
    ChevronRight, 
    Plus, 
    Search, 
    Filter, 
    MoreHorizontal,
    CheckCircle2,
    XCircle,
    Eye,
    Edit3,
    Trash2,
    Settings,
    Layout,
    Globe,
    BookOpen,
    ClipboardList,
    AlertCircle,
    UserCircle,
    Loader2,
    Save,
    X
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import Skeleton from '@/components/ui/Skeleton';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

const MODULES = [
    { id: 'crm', label: 'CRM Pastoral', icon: Users, color: 'text-blue-500' },
    { id: 'academy', label: 'Academia Faro', icon: BookOpen, color: 'text-emerald-500' },
    { id: 'projects', label: 'Proyectos', icon: ClipboardList, color: 'text-indigo-500' },
    { id: 'admin', label: 'Panel Administrativo', icon: Shield, color: 'text-rose-500' },
];

export default function AccessManagementPage() {
    const { token, isAuthenticated } = useAuth();
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState<'roles' | 'users'>('roles');
    const [roles, setRoles] = useState<any[]>([]);
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedEntity, setSelectedEntity] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isSaving, setIsAssigning] = useState(false);

    // State for local permission editing
    const [localPermissions, setLocalPermissions] = useState<Record<string, string>>({});

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const [rolesData, usersData] = await Promise.all([
                apiFetch<any[]>('/admin/roles', { token, cache: 'no-store' }),
                apiFetch<any[]>('/admin/users', { token, cache: 'no-store' })
            ]);
            setRoles(Array.isArray(rolesData) ? rolesData : []);
            setUsers(Array.isArray(usersData) ? usersData : []);
        } catch (err) { 
            console.error(err);
            addToast("Error al cargar configuraciones de acceso", "error");
        } finally { 
            setLoading(false); 
        }
    }, [token, addToast]);

    useEffect(() => {
        if (isAuthenticated) fetchData();
    }, [isAuthenticated, fetchData]);

    const handleOpenEntity = (entity: any) => {
        setSelectedEntity(entity);
        setLocalPermissions(entity.permissions || {});
        setIsDrawerOpen(true);
    };

    const handleSavePermissions = async () => {
        if (!selectedEntity || !token) return;
        setIsAssigning(true);
        try {
            if (activeTab === 'roles') {
                await apiFetch(`/admin/roles/${selectedEntity.id}`, {
                    method: 'PATCH',
                    token,
                    body: localPermissions
                });
                addToast("Permisos del rol actualizados", "success");
            } else {
                // User logic can be added here if we want per-user overrides
                addToast("Función en desarrollo para usuarios", "info");
            }
            setIsDrawerOpen(false);
            fetchData();
        } catch (err) {
            addToast("Error al guardar cambios", "error");
        } finally {
            setIsAssigning(false);
        }
    };

    const roleColumns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'name', 
            header: 'Nombre del Rol', 
            cell: info => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center text-blue-600 shadow-sm">
                        <Shield size={16} />
                    </div>
                    <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-tight">{info.getValue() as string}</span>
                </div>
            ) 
        },
        { 
            accessorKey: 'users_count', 
            header: 'Usuarios', 
            cell: info => (
                <div className="flex items-center gap-2">
                    <div className="flex -space-x-2">
                        {[1,2,3].slice(0, info.getValue() as number).map(i => (
                            <div key={i} className="size-6 rounded-full border-2 border-white dark:border-slate-800 bg-slate-100 flex items-center justify-center text-[8px] font-bold text-slate-400 uppercase">U</div>
                        ))}
                    </div>
                    <span className="text-[11px] font-bold text-slate-500 ml-2">{info.getValue() as number} vinculados</span>
                </div>
            ) 
        },
        { 
            id: 'actions', 
            header: '', 
            cell: () => <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400 opacity-0 group-hover:opacity-100 transition-all"><ChevronRight size={18} /></button> 
        }
    ], []);

    const userColumns = useMemo<ColumnDef<any>[]>(() => [
        { 
            accessorKey: 'username', 
            header: 'Usuario', 
            cell: info => (
                <div className="flex items-center gap-3">
                    <div className="size-8 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 border border-slate-200 dark:border-white/10 shadow-inner">
                        <UserCircle size={18} />
                    </div>
                    <div className="flex flex-col">
                        <span className="text-[13px] font-bold text-slate-800 dark:text-slate-100">{info.getValue() as string}</span>
                        <span className="text-[10px] text-slate-400 font-medium">#{info.row.original.id}</span>
                    </div>
                </div>
            ) 
        },
        { accessorKey: 'email', header: 'Email', cell: info => <span className="text-[12px] text-slate-500">{info.getValue() as string}</span> },
        { 
            accessorKey: 'role', 
            header: 'Rol Asignado', 
            cell: info => (
                <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-lg text-[9px] font-black uppercase tracking-widest border border-blue-100 dark:border-blue-800">
                    {info.getValue() as string}
                </span>
            ) 
        },
        { 
            accessorKey: 'is_active', 
            header: 'Estado', 
            cell: info => (
                <div className="flex items-center gap-2">
                    <div className={clsx("size-2 rounded-full", info.getValue() ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-slate-300")} />
                    <span className="text-[10px] font-black uppercase text-slate-400 tracking-widest">{info.getValue() ? 'Activo' : 'Inactivo'}</span>
                </div>
            ) 
        }
    ], []);

    if (!isAuthenticated) return null;

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <style jsx global>{`
                .permission-card {
                    transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
                }
                .permission-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.03);
                }
            `}</style>

            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'CCF Platform', icon: Settings }, { label: 'Seguridad y Accesos', icon: Lock }]}
                viewType="table" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all hover:bg-blue-700">
                        <Plus size={14} /> Crear Nuevo
                    </button>
                }
            />

            {/* Cinematic Tab Navigation */}
            <div className="flex px-8 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0 relative overflow-hidden">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_#1973f005_0%,_transparent_50%)] pointer-events-none" />
                <button onClick={() => setActiveTab('roles')} className={clsx("px-8 py-5 text-[11px] font-black uppercase tracking-widest transition-all border-b-2 relative z-10", activeTab === 'roles' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600 hover:bg-white/50")}>Roles Ministeriales</button>
                <button onClick={() => setActiveTab('users')} className={clsx("px-8 py-5 text-[11px] font-black uppercase tracking-widest transition-all border-b-2 relative z-10", activeTab === 'users' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600 hover:bg-white/50")}>Auditoría de Usuarios</button>
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin p-6 lg:p-10">
                <div className="max-w-[1400px] mx-auto">
                    {loading ? (
                        <div className="space-y-6">
                            {[1,2,3,4,5,6].map(i => <Skeleton key={i} className="h-16 w-full rounded-2xl" />)}
                        </div>
                    ) : (
                        <motion.div 
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-white dark:bg-white/5 rounded-[2.5rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm"
                        >
                            <DataTable 
                                data={activeTab === 'roles' ? roles : users} 
                                columns={activeTab === 'roles' ? roleColumns : userColumns} 
                                onRowClick={handleOpenEntity} 
                            />
                        </motion.div>
                    )}
                </div>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedEntity?.name || selectedEntity?.username || 'Configurar Acceso'}
                subtitle={activeTab === 'roles' ? 'Matriz de Privilegios por Módulo' : 'Control de Identidad Individual'}
                actions={
                    <div className="flex gap-3">
                        <button className="px-6 py-2.5 bg-slate-100 dark:bg-white/5 text-slate-500 rounded-xl text-[11px] font-black uppercase tracking-widest hover:bg-slate-200 transition-all" onClick={() => setIsDrawerOpen(false)}>Cerrar</button>
                        <button 
                            disabled={isSaving}
                            className="px-8 py-2.5 bg-blue-600 text-white rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 flex items-center gap-2 hover:bg-blue-700 active:scale-95 transition-all" 
                            onClick={handleSavePermissions}
                        >
                            {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />} Guardar Cambios
                        </button>
                    </div>
                }
            >
                <div className="space-y-10 animate-in fade-in slide-in-from-right-4 duration-500">
                    {/* Module Permission Matrix */}
                    <section className="space-y-8">
                        <div className="flex items-center justify-between px-2">
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.3em] flex items-center gap-3">
                                <Layout size={16} className="text-blue-500" /> Matriz de Operaciones
                            </h4>
                            <div className="flex items-center gap-2 px-3 py-1 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-100 dark:border-amber-800">
                                <Shield size={10} className="text-amber-600" />
                                <span className="text-[9px] font-black text-amber-700 uppercase">Seguridad v3.9</span>
                            </div>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-4">
                            {MODULES.map((mod) => (
                                <PermissionRow 
                                    key={mod.id} 
                                    {...mod} 
                                    level={localPermissions[mod.id] || 'none'}
                                    onChange={(newLevel: string) => setLocalPermissions({ ...localPermissions, [mod.id]: newLevel })}
                                />
                            ))}
                        </div>
                    </section>

                    {/* Industrial Disclaimer */}
                    <section className="p-8 bg-slate-900 rounded-[2.5rem] text-white relative overflow-hidden group shadow-2xl">
                        <div className="absolute top-0 right-0 p-6 opacity-10 group-hover:rotate-12 transition-transform duration-1000"><Lock size={80} /></div>
                        <div className="relative z-10 space-y-4">
                            <div className="flex items-center gap-3 text-blue-400 font-black uppercase tracking-widest text-[10px]">
                                <AlertCircle size={14} /> Protocolo de Seguridad
                            </div>
                            <p className="text-xs text-slate-300 leading-relaxed font-medium">
                                Los cambios realizados en esta matriz afectarán inmediatamente el acceso de todos los usuarios vinculados a este rol. Asegúrese de validar el impacto antes de confirmar la misión.
                            </p>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function PermissionRow({ label, icon: Icon, color, level, onChange }: any) {
    return (
        <div className="permission-card p-5 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/10 flex items-center justify-between group">
            <div className="flex items-center gap-5">
                <div className={clsx("size-12 rounded-[1.25rem] flex items-center justify-center bg-white dark:bg-black/40 shadow-sm border border-slate-100 dark:border-white/5 transition-all group-hover:scale-110 group-hover:rotate-3", color)}>
                    <Icon size={24} strokeWidth={1.5} />
                </div>
                <div>
                    <p className="text-[14px] font-black text-slate-800 dark:text-slate-100 uppercase tracking-tight leading-none mb-1">{label}</p>
                    <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Estado: <span className="text-blue-500">{level === 'none' ? 'Bloqueado' : level}</span></p>
                </div>
            </div>
            <div className="flex bg-white dark:bg-black/40 p-1.5 rounded-2xl border border-slate-200 dark:border-white/10 shadow-inner">
                <LevelBtn active={level === 'none'} icon={XCircle} tooltip="Sin Acceso" onClick={() => onChange('none')} />
                <LevelBtn active={level === 'read'} icon={Eye} tooltip="Solo Lectura" onClick={() => onChange('read')} />
                <LevelBtn active={level === 'write'} icon={Edit3} tooltip="Escritura" onClick={() => onChange('write')} />
                <LevelBtn active={level === 'admin'} icon={Shield} tooltip="Administrador" onClick={() => onChange('admin')} />
            </div>
        </div>
    );
}

function LevelBtn({ active, icon: Icon, tooltip, onClick }: any) {
    return (
        <button 
            title={tooltip}
            onClick={onClick}
            className={clsx(
                "p-2 rounded-xl transition-all duration-300 relative group/btn",
                active ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-xl scale-110" : "text-slate-300 hover:text-slate-600 dark:hover:text-slate-200"
            )}
        >
            <Icon size={16} />
            {active && <motion.div layoutId="level-indicator" className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 bg-current rounded-full" />}
        </button>
    );
}
