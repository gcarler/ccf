"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { ViewType } from '@/components/ViewSwitcher';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import InlineEdit from '@/components/ui/InlineEdit';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import DatePicker from '@/components/ui/DatePicker';
import Skeleton from '@/components/ui/Skeleton';
import EmptyState from '@/components/ui/EmptyState';
import { 
    ClipboardList, 
    CheckCircle, 
    Layout
} from 'lucide-react';
import clsx from 'clsx';
import { AnimatePresence } from 'framer-motion';

const TASK_STATUS_OPTIONS: StatusOption[] = [
    { label: 'PENDIENTE', value: 'PENDIENTE', color: 'bg-slate-400', text: 'text-slate-600 dark:text-slate-400', bg: 'bg-slate-100 dark:bg-slate-900/30' },
    { label: 'EN CURSO', value: 'EN CURSO', color: 'bg-indigo-500', text: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-50 dark:bg-indigo-900/30' },
    { label: 'COMPLETADA', value: 'COMPLETADA', color: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/30' },
    { label: 'BLOQUEADA', value: 'BLOQUEADA', color: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-50 dark:bg-rose-900/30' },
];

export default function MyTasksPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const [viewType, setViewType] = useState<ViewType>('table');
    const [tasks, setTasks] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');

    useEffect(() => {
        const fetchMyTasks = async () => {
            if (!token || !user) return;
            try {
                // Fetching all tasks for now. In a real scenario, API filters by user.id
                const data = await apiFetch(`/projects/1/tasks`, { token });
                if (Array.isArray(data)) {
                    setTasks(data.map((t: any) => ({
                        id: t.id,
                        title: t.title,
                        status: t.status,
                        dueDate: t.due_date,
                        priority: t.priority === 'high' ? 'Alta' : 'Media',
                        project: 'Proyecto 1'
                    })));
                }
            } catch (err) {
                console.error("Error fetching my tasks:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchMyTasks();
    }, [token, user]);

    const updateTaskTitle = useCallback(async (id: number, newTitle: string) => {
        setTasks(prev => prev.map(t => t.id === id ? { ...t, title: newTitle } : t));
        try { 
            await apiFetch(`/projects/tasks/${id}`, { method: 'PATCH', token, body: { title: newTitle } }); 
            addToast('Título actualizado', 'success');
        } catch (err) { addToast('Error al actualizar', 'error'); }
    }, [token, addToast]);

    const updateTaskStatus = useCallback(async (id: number, newStatus: string) => {
        setTasks(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));
        try { 
            await apiFetch(`/projects/tasks/${id}`, { method: 'PATCH', token, body: { status: newStatus } }); 
            addToast(`Estado: ${newStatus}`, 'success');
        } catch (err) { addToast('Error al cambiar estado', 'error'); }
    }, [token, addToast]);

    const updateTaskDate = useCallback(async (id: number, date: Date) => {
        const dateStr = date.toISOString();
        setTasks(prev => prev.map(t => t.id === id ? { ...t, dueDate: dateStr } : t));
        try {
            await apiFetch(`/projects/tasks/${id}`, { method: 'PATCH', token, body: { due_date: dateStr } });
            addToast('Fecha actualizada', 'success');
        } catch (err) { addToast('Error al actualizar fecha', 'error'); }
    }, [token, addToast]);

    const filteredTasks = useMemo(() => {
        return tasks.filter(t => t.title.toLowerCase().includes(search.toLowerCase()));
    }, [tasks, search]);

    const columns = useMemo<ColumnDef<any>[]>(() => [
        { accessorKey: 'id', header: '#', size: 60, cell: info => <span className="text-[11px] font-bold text-slate-400">#{info.getValue() as number}</span> },
        { 
            accessorKey: 'title', 
            header: 'Nombre de la Tarea', 
            size: 400,
            cell: ({ row }) => (
                <div onClick={(e) => e.stopPropagation()}>
                    <InlineEdit value={row.original.title} onSave={(val) => updateTaskTitle(row.original.id, val)} textClassName="text-[13px] font-bold text-slate-700 dark:text-slate-200" />
                    <p className="text-[10px] text-slate-400 font-medium mt-0.5">{row.original.project}</p>
                </div>
            ) 
        },
        { 
            accessorKey: 'status', 
            header: 'Estado', 
            cell: ({ row }) => (
                <div onClick={(e) => e.stopPropagation()}>
                    <StatusPicker currentValue={row.original.status} options={TASK_STATUS_OPTIONS} onSelect={(val) => updateTaskStatus(row.original.id, val)} />
                </div>
            ) 
        },
        { 
            accessorKey: 'dueDate', 
            header: 'Límite', 
            cell: ({ row }) => (
                <div onClick={(e) => e.stopPropagation()}>
                    <DatePicker currentDate={row.original.dueDate} onSelect={(date) => updateTaskDate(row.original.id, date)} />
                </div>
            ) 
        },
        { 
            accessorKey: 'priority', 
            header: 'Prioridad', 
            cell: ({ row }) => { 
                const p = row.original.priority; 
                return p ? <span className={clsx("text-[10px] font-black px-1.5 py-0.5 rounded uppercase tracking-widest", p === 'Alta' ? 'bg-rose-50 text-rose-500 dark:bg-rose-900/20' : 'bg-slate-50 text-slate-500 dark:bg-white/5')}>{p}</span> : <span className="text-slate-300">-</span>; 
            } 
        }
    ], [updateTaskTitle, updateTaskStatus, updateTaskDate]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Inicio', icon: Layout },
                    { label: 'Mis Tareas', icon: ClipboardList }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['table']}
                onSearch={setSearch}
            />

            <main className="flex-1 overflow-hidden flex flex-col">
                <AnimatePresence mode="wait">
                    {loading ? (
                        <div className="p-8 space-y-4">
                            {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
                        </div>
                    ) : filteredTasks.length > 0 ? (
                        <div className="flex-1 overflow-auto">
                            <DataTable data={filteredTasks} columns={columns} />
                        </div>
                    ) : (
                        <div className="p-12">
                            <EmptyState 
                                title="Día libre" 
                                description="No tienes tareas asignadas. Tómate un descanso o revisa otros proyectos."
                                icon={CheckCircle}
                            />
                        </div>
                    )}
                </AnimatePresence>
            </main>
        </div>
    );
}
