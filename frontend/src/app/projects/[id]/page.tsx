"use client";

import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import clsx from 'clsx';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    DndContext, DragOverlay, closestCorners, KeyboardSensor, PointerSensor, useSensor, useSensors, DragEndEvent 
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { 
    List, Layout, Calendar, Plus, Search, Filter, MoreHorizontal, CheckCircle, UserCircle, 
    CalendarDays, Flag, ChevronDown, Layers, Folder, MessageSquare, Edit3, Trash2, 
    ChevronRight, CornerDownRight, Link2, Clock, Sparkles, BarChart2, Bot, FileText,
    GanttChart, Calendar as CalendarIcon, ChevronUp
} from 'lucide-react';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType } from '@/components/ViewSwitcher';
import InlineEdit from '@/components/ui/InlineEdit';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import Skeleton from '@/components/ui/Skeleton';
import UserPicker from '@/components/ui/UserPicker';
import DatePicker from '@/components/ui/DatePicker';
import { KanbanColumn } from '@/components/projects/KanbanColumn';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import UniversalCreationModal from '@/components/ui/UniversalCreationModal';
import Tooltip from '@/components/ui/Tooltip';
import GanttView from '@/components/projects/GanttView';
import ProjectCalendarView from '@/components/projects/ProjectCalendarView';
import { useConfig } from '@/context/ConfigContext';

const TASK_STATUS_OPTIONS: StatusOption[] = [
    { label: 'PENDIENTE', value: 'PENDIENTE', color: 'bg-slate-400', text: 'text-slate-600 dark:text-slate-400', bg: 'bg-slate-100 dark:bg-slate-900/30' },
    { label: 'EN CURSO', value: 'EN CURSO', color: 'bg-indigo-500', text: 'text-indigo-600 dark:text-indigo-400', bg: 'bg-indigo-50 dark:bg-indigo-900/30' },
    { label: 'COMPLETADA', value: 'COMPLETADA', color: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/30' },
    { label: 'BLOQUEADA', value: 'BLOQUEADA', color: 'bg-rose-500', text: 'text-rose-600 dark:text-rose-400', bg: 'bg-rose-50 dark:bg-rose-900/30' },
];

export default function ProjectDetailPage() {
    const params = useParams<{ id: string }>();
    const projectId = params?.id ?? '';
    const { token } = useAuth();
    const { addToast } = useToast();
    const { isFeatureEnabled } = useConfig();
    const [viewType, setViewType] = useState<ViewType>('list');
    const [selectedTask, setSelectedTask] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [tasks, setTasks] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState('');

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    const fetchTasks = useCallback(async () => {
        if (!token || !projectId) return;
        try {
            const data = await apiFetch(`/projects/${projectId}/tasks`, { token });
            if (Array.isArray(data)) {
                setTasks(data.map((t: any) => ({
                    id: t.id, title: t.title, status: t.status, assignee_id: t.assignee_id,
                    dueDate: t.due_date, priority: t.priority === 'high' ? 'Alta' : 'Media',
                    description: t.description || '',
                    subtasks: t.subtasks || []
                })));
            }
        } catch (err) { console.error(err); }
        finally { setIsLoading(false); }
    }, [token, projectId]);

    useEffect(() => { fetchTasks(); }, [fetchTasks]);

    const updateTaskStatus = async (id: number, newStatus: string) => {
        setTasks(prev => {
            const updateNested = (list: any[]): any[] => {
                return list.map(t => {
                    if (t.id === id) return { ...t, status: newStatus };
                    if (t.subtasks) return { ...t, subtasks: updateNested(t.subtasks) };
                    return t;
                });
            };
            return updateNested(prev);
        });
        try { 
            await apiFetch(`/projects/tasks/${id}`, { method: 'PATCH', token, body: { status: newStatus } }); 
            addToast(`Estado: ${newStatus}`, 'success');
        } catch (err) { addToast('Error', 'error'); }
    };

    const filteredTasks = useMemo(() => tasks.filter(t => t.title.toLowerCase().includes(search.toLowerCase())), [tasks, search]);

    const groups = useMemo(() => ([
        { id: 'en-curso', name: 'EN CURSO', color: '#664dfc', tasks: filteredTasks.filter(t => t.status === 'EN CURSO') },
        { id: 'pendiente', name: 'PENDIENTE', color: '#87909e', tasks: filteredTasks.filter(t => t.status === 'PENDIENTE' || t.status === 'todo') },
        { id: 'completada', name: 'COMPLETADA', color: '#10b981', tasks: filteredTasks.filter(t => t.status === 'COMPLETADA') },
    ]), [filteredTasks]);

    const handleOpenTask = (task: any) => { setSelectedTask(task); setIsDrawerOpen(true); };

    const hasGantt = isFeatureEnabled('gantt');
    const hasCalendar = isFeatureEnabled('calendar');
    const availableViews = useMemo(() => {
        const views: ViewType[] = ['list', 'kanban', 'table'];
        if (hasGantt) views.push('gantt');
        if (hasCalendar) views.push('calendar');
        return views;
    }, [hasGantt, hasCalendar]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar 
                breadcrumbs={[{ label: 'Portfolio', icon: Layers }, { label: `Proyecto #${projectId}`, icon: Layout }]}
                viewType={viewType} setViewType={setViewType} 
                availableViews={availableViews}
                onSearch={setSearch} onAdd={() => setIsCreateModalOpen(true)}
            />

            <main className="flex-1 overflow-hidden relative flex flex-col">
                <AnimatePresence mode="wait">
                    {viewType === 'list' && (
                        <motion.div key="list" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 overflow-y-auto scrollbar-thin pb-20">
                            {groups.map(group => (
                                <div key={group.id} className="mb-8">
                                    <div className="flex items-center gap-3 px-8 py-3 bg-slate-50/50 dark:bg-white/5 border-y border-slate-100 dark:border-white/5 sticky top-0 z-10 backdrop-blur-sm">
                                        <ChevronDown size={14} className="text-slate-400" />
                                        <div className="px-2 py-0.5 rounded text-[10px] font-black text-white shadow-sm uppercase tracking-widest" style={{ backgroundColor: group.color }}>{group.name}</div>
                                        <span className="text-[12px] font-bold text-slate-400">{group.tasks.length}</span>
                                    </div>
                                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                                        {group.tasks.map((task) => (
                                            <TaskTreeItem key={task.id} task={task} onOpen={handleOpenTask} onUpdateStatus={updateTaskStatus} />
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </motion.div>
                    )}

                    {viewType === 'kanban' && (
                        <motion.div key="kanban" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                            <DndContext sensors={sensors} collisionDetection={closestCorners}>
                                <div className="flex h-full gap-6 p-6 overflow-x-auto bg-slate-50 dark:bg-[#141517] items-start scrollbar-thin">
                                    {groups.map(col => (
                                        <KanbanColumn key={col.id} id={col.id} name={col.name} color={col.color} tasks={col.tasks} onOpenTask={handleOpenTask} onAddTask={() => setIsCreateModalOpen(true)} />
                                    ))}
                                </div>
                            </DndContext>
                        </motion.div>
                    )}

                    {viewType === 'gantt' && (
                        <motion.div key="gantt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                            <GanttView tasks={filteredTasks} onTaskClick={handleOpenTask} />
                        </motion.div>
                    )}

                    {viewType === 'calendar' && (
                        <motion.div key="calendar" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
                            <ProjectCalendarView tasks={filteredTasks} onTaskClick={handleOpenTask} />
                        </motion.div>
                    )}
                </AnimatePresence>
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} onClose={() => setIsDrawerOpen(false)}
                title={selectedTask?.title || 'Detalles'} subtitle={`Gestión de Proyecto #${projectId}`}
                actions={<><button className="px-4 py-2 text-[11px] font-bold text-slate-500">Eliminar</button><button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg">Guardar</button></>}
            >
                <div className="space-y-10 animate-fade-in">
                    <section className="grid grid-cols-2 gap-6">
                        <div className="space-y-2">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><CheckCircle size={14} /> Estado</span>
                            <StatusPicker currentValue={selectedTask?.status} options={TASK_STATUS_OPTIONS} onSelect={(val) => updateTaskStatus(selectedTask.id, val)} />
                        </div>
                        <div className="space-y-2">
                            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><Flag size={14} /> Prioridad</span>
                            <div className="px-3 py-1.5 bg-rose-50 dark:bg-rose-900/20 rounded-lg text-[11px] font-black text-rose-600 uppercase">{selectedTask?.priority}</div>
                        </div>
                    </section>

                    {/* Subtasks in Drawer */}
                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <div className="flex items-center justify-between px-2">
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2"><CornerDownRight size={14} /> Subtareas</h4>
                            <span className="text-[10px] font-bold text-blue-600">{selectedTask?.subtasks?.length || 0}</span>
                        </div>
                        <div className="space-y-2">
                            {selectedTask?.subtasks?.map((st: any) => (
                                <div key={st.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-100 dark:border-white/5 group">
                                    <div className="flex items-center gap-3">
                                        <CheckCircle size={14} className="text-slate-300 group-hover:text-blue-500 cursor-pointer" />
                                        <span className="text-[13px] font-medium text-slate-700 dark:text-slate-200">{st.title}</span>
                                    </div>
                                    <UserCircle size={16} className="text-slate-300" />
                                </div>
                            ))}
                            <button className="w-full py-2 border border-dashed border-slate-200 dark:border-white/10 rounded-xl text-[11px] font-black uppercase text-slate-400 hover:text-blue-600 transition-all">+ Añadir Subtarea</button>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>

            <UniversalCreationModal isOpen={isCreateModalOpen} onClose={() => setIsCreateModalOpen(false)} onSubmit={() => {}} />
        </div>
    );
}

function TaskTreeItem({ task, onOpen, onUpdateStatus, level = 0 }: any) {
    const [isExpanded, setIsExpanded] = useState(true);
    const hasSubtasks = task.subtasks && task.subtasks.length > 0;

    return (
        <div className="flex flex-col">
            <div 
                onClick={() => onOpen(task)}
                className="grid grid-cols-[1fr_auto] gap-4 px-8 py-3 hover:bg-blue-50/50 dark:hover:bg-blue-500/5 transition-all cursor-pointer group items-center relative"
                style={{ paddingLeft: `${32 + (level * 24)}px` }}
            >
                {/* Visual Connector Line */}
                {level > 0 && (
                    <div className="absolute left-10 top-0 bottom-0 w-[1px] bg-slate-100 dark:bg-white/5" />
                )}
                {level > 0 && (
                    <div className="absolute left-10 top-1/2 w-4 h-[1px] bg-slate-100 dark:bg-white/5" />
                )}

                <div className="flex items-center gap-3 overflow-hidden">
                    <div className="flex items-center gap-1 shrink-0">
                        {hasSubtasks ? (
                            <button 
                                onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                                className="p-1 hover:bg-slate-100 dark:hover:bg-white/10 rounded transition-all text-slate-400"
                            >
                                {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                            </button>
                        ) : (
                            <div className="size-6" />
                        )}
                        <div className="size-4 rounded-full border-2 border-slate-200 dark:border-slate-700 flex items-center justify-center shrink-0 group-hover:border-blue-500 transition-colors">
                            <div className={clsx("size-2 rounded-full bg-blue-500 opacity-0 group-hover:opacity-100 transition-opacity", task.status === 'COMPLETADA' && "opacity-100 bg-emerald-500")} />
                        </div>
                    </div>
                    <span className={clsx("text-[13px] font-bold tracking-tight truncate", task.status === 'COMPLETADA' ? "text-slate-400 line-through" : "text-slate-700 dark:text-slate-200")}>
                        {task.title}
                    </span>
                    {hasSubtasks && !isExpanded && (
                        <span className="text-[9px] font-black bg-blue-50 dark:bg-blue-900/30 text-blue-600 px-1.5 py-0.5 rounded uppercase tracking-widest">{task.subtasks.length} Subtareas</span>
                    )}
                </div>

                <div className="flex items-center gap-4 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="size-7 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400 hover:text-blue-600 transition-all shadow-sm"><UserCircle size={16} /></div>
                    <button className="p-1.5 hover:bg-slate-100 dark:hover:bg-white/10 rounded-lg text-slate-400 transition-all"><MoreHorizontal size={16} /></button>
                </div>
            </div>

            {/* Render Subtasks Recursively */}
            <AnimatePresence>
                {isExpanded && hasSubtasks && (
                    <motion.div 
                        initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden"
                    >
                        {task.subtasks.map((st: any) => (
                            <TaskTreeItem key={st.id} task={st} onOpen={onOpen} onUpdateStatus={onUpdateStatus} level={level + 1} />
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
