"use client";

import React, { useState, useEffect, useMemo } from 'react';
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
    UserCircle
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
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
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState<'roles' | 'users'>('roles');
    const [roles, setRoles] = useState<any[]>([]);
    const [users, setUsers] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedEntity, setSelectedEntity] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return;
            setLoading(true);
            try {
                // Simplified endpoints for now
                const [usersData] = await Promise.all([
                    apiFetch('/admin/members/', { token })
                ]);
                setUsers(usersData as any[]);
                
                // Mock roles for UI development
                setRoles([
                    { id: 1, name: 'Pastor Principal', description: 'Acceso total a todos los módulos y sedes.', users_count: 2 },
                    { id: 2, name: 'Líder de Red', description: 'Gestión de miembros y casas en su zona.', users_count: 12 },
                    { id: 3, name: 'Administrador Academia', description: 'Control de cursos, notas y certificados.', users_count: 3 },
                    { id: 4, name: 'Staff Operativo', description: 'Gestión de tareas y soporte técnico.', users_count: 8 },
                ]);
            } catch (err) { console.error(err); }
            finally { setLoading(false); }
        };
        fetchData();
    }, [token]);

    const handleOpenEntity = (entity: any) => {
        setSelectedEntity(entity);
        setIsDrawerOpen(true);
    };

    const roleColumns = useMemo<ColumnDef<any>[]>(() => [
        { accessorKey: 'name', header: 'Nombre del Rol', cell: info => <span className="text-[13px] font-black text-slate-800 dark:text-white uppercase tracking-tight">{info.getValue() as string}</span> },
        { accessorKey: 'description', header: 'Descripción', cell: info => <span className="text-[12px] text-slate-500 font-medium line-clamp-1">{info.getValue() as string}</span> },
        { accessorKey: 'users_count', header: 'Usuarios', cell: info => <div className="flex items-center gap-2"><Users size={14} className="text-slate-400" /><span className="text-[11px] font-bold text-slate-600">{info.getValue() as number}</span></div> },
        { id: 'actions', header: '', cell: () => <button className="p-1 hover:bg-slate-100 dark:hover:bg-white/5 rounded-md text-slate-400"><MoreHorizontal size={16} /></button> }
    ], []);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Ajustes', icon: Settings }, { label: 'Gestión de Accesos', icon: Lock }]}
                viewType="table" setViewType={() => {}}
                rightActions={
                    <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                        <Plus size={14} /> Nuevo {activeTab === 'roles' ? 'Rol' : 'Usuario'}
                    </button>
                }
            />

            {/* Sub-navigation */}
            <div className="flex px-6 border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5 shrink-0">
                <button onClick={() => setActiveTab('roles')} className={clsx("px-6 py-4 text-[11px] font-black uppercase tracking-widest transition-all border-b-2", activeTab === 'roles' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600")}>Roles de Sistema</button>
                <button onClick={() => setActiveTab('users')} className={clsx("px-6 py-4 text-[11px] font-black uppercase tracking-widest transition-all border-b-2", activeTab === 'users' ? "text-blue-600 border-blue-600" : "text-slate-400 border-transparent hover:text-slate-600")}>Permisos de Usuario</button>
            </div>

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {loading ? (
                    <div className="p-8 space-y-4">
                        {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
                    </div>
                ) : (
                    <div className="h-full">
                        {activeTab === 'roles' ? (
                            <DataTable data={roles} columns={roleColumns} onRowClick={handleOpenEntity} />
                        ) : (
                            <div className="p-8 text-center text-slate-400">Selecciona un usuario para gestionar sus permisos específicos.</div>
                        )}
                    </div>
                )}
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedEntity?.name || 'Configurar Acceso'}
                subtitle={activeTab === 'roles' ? 'Definición de Privilegios' : 'Permisos Individuales'}
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-slate-500" onClick={() => setIsDrawerOpen(false)}>Cancelar</button><button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20">Guardar Cambios</button></>}
            >
                <div className="space-y-10 animate-fade-in">
                    {/* Module Permission Matrix */}
                    <section className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                <Layout size={14} className="text-blue-500" /> Permisos por Módulo
                            </h4>
                            <span className="text-[10px] font-bold text-slate-400">Heredado del Rol</span>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-3">
                            {MODULES.map((mod) => (
                                <PermissionRow key={mod.id} {...mod} />
                            ))}
                        </div>
                    </section>

                    {/* Granular Resource Access */}
                    <section className="space-y-6 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-[0.2em] flex items-center gap-2">
                            <Key size={14} className="text-amber-500" /> Accesos a Recursos Específicos
                        </h4>
                        
                        <div className="space-y-3">
                            <ResourceAccessItem label="Proyecto: Construcción Sede Norte" type="project" access="write" />
                            <ResourceAccessItem label="Curso: Liderazgo Avanzado" type="course" access="read" />
                            <button className="w-full py-3 border-2 border-dashed border-slate-100 dark:border-white/5 rounded-2xl flex items-center justify-center gap-2 text-[11px] font-black uppercase text-slate-400 hover:text-blue-600 transition-all">
                                <Plus size={14} /> Añadir Excepción de Acceso
                            </button>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>
        </div>
    );
}

function PermissionRow({ label, icon: Icon, color }: any) {
    const [level, setLevel] = useState<'none' | 'read' | 'write' | 'admin'>('read');

    return (
        <div className="p-4 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/30 transition-all">
            <div className="flex items-center gap-4">
                <div className={clsx("size-10 rounded-xl flex items-center justify-center bg-white dark:bg-black/20 shadow-sm", color)}>
                    <Icon size={20} />
                </div>
                <div>
                    <p className="text-[13px] font-bold text-slate-800 dark:text-slate-100 leading-tight">{label}</p>
                    <p className="text-[10px] text-slate-400 font-medium">Nivel actual: <span className="capitalize text-blue-500">{level}</span></p>
                </div>
            </div>
            <div className="flex bg-white dark:bg-black/40 p-1 rounded-xl border border-slate-200 dark:border-white/10">
                <LevelBtn active={level === 'none'} icon={XCircle} onClick={() => setLevel('none')} />
                <LevelBtn active={level === 'read'} icon={Eye} onClick={() => setLevel('read')} />
                <LevelBtn active={level === 'write'} icon={Edit3} onClick={() => setLevel('write')} />
                <LevelBtn active={level === 'admin'} icon={Shield} onClick={() => setLevel('admin')} />
            </div>
        </div>
    );
}

function LevelBtn({ active, icon: Icon, onClick }: any) {
    return (
        <button 
            onClick={onClick}
            className={clsx(
                "p-1.5 rounded-lg transition-all",
                active ? "bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-md" : "text-slate-400 hover:text-slate-600"
            )}
        >
            <Icon size={14} />
        </button>
    );
}

function ResourceAccessItem({ label, type, access }: any) {
    return (
        <div className="flex items-center justify-between p-4 bg-white dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5 shadow-sm">
            <div className="flex items-center gap-3">
                <div className="size-8 rounded-lg bg-slate-100 dark:bg-black/20 flex items-center justify-center text-slate-400">
                    {type === 'project' ? <ClipboardList size={16} /> : <BookOpen size={16} />}
                </div>
                <span className="text-[12px] font-bold text-slate-700 dark:text-slate-200">{label}</span>
            </div>
            <div className="flex items-center gap-3">
                <div className="px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded text-[9px] font-black uppercase">{access}</div>
                <button className="text-slate-300 hover:text-rose-500 transition-colors"><Trash2 size={14} /></button>
            </div>
        </div>
    );
}
