"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { Hash, Layout, Plus } from 'lucide-react';

export default function ProjectsWelcomePage() {
    const { token } = useAuth();
    const router = useRouter();
    const [creating, setCreating] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const quickStarts = [
        { title: 'Crear proyecto', description: 'Inicia un proyecto y define su alcance.' },
        { title: 'Organizar tareas', description: 'Usa Kanban para mover el trabajo del equipo.' },
        { title: 'Monitorear respuestas', description: 'Revisa comentarios y decisiones en un solo lugar.' },
    ];

    const handleCreate = async () => {
        const title = window.prompt('Nombre del primer proyecto');
        if (!title || !title.trim()) return;
        setCreating(true);
        try {
            const project = await apiFetch<ProjectRecord>('/projects', {
                method: 'POST',
                token,
                body: {
                    title: title.trim(),
                    description: 'Creado desde la vista Welcome de Proyectos.',
                    status: 'planning',
                },
            });
            router.push(`/projects/${project.id}`);
        } catch (error) {
            console.error(error);
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in font-display">
            <WorkspaceToolbar
                breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Welcome', icon: Hash }]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'list', 'table']}
            />
            <main className="flex-1 overflow-y-auto p-6 lg:p-8">
                {viewType === 'list' && (
                    <div className="max-w-3xl space-y-4">
                        {quickStarts.map((item) => (
                            <article key={item.title} className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-white/10 dark:bg-white/5">
                                <h3 className="font-black text-slate-900 dark:text-white">{item.title}</h3>
                                <p className="mt-2 text-sm text-slate-500">{item.description}</p>
                            </article>
                        ))}
                    </div>
                )}
                {viewType === 'table' && (
                    <div className="max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-slate-50 dark:bg-white/5 text-[10px] font-black uppercase tracking-widest text-slate-400">
                                <tr><th className="px-6 py-4">Recurso</th><th className="px-6 py-4">Descripción</th></tr>
                            </thead>
                            <tbody>
                                {quickStarts.map((item) => (
                                    <tr key={item.title} className="border-t border-slate-100 dark:border-white/5">
                                        <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">{item.title}</td>
                                        <td className="px-6 py-4 text-slate-500">{item.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {viewType === 'grid' && (
                <section className="max-w-3xl rounded-[2.5rem] border border-slate-200 dark:border-white/10 p-8 bg-gradient-to-br from-blue-50 to-white dark:from-blue-900/20 dark:to-transparent">
                    <p className="text-[10px] font-black uppercase tracking-[0.25em] text-blue-600">Workspace de proyectos</p>
                    <h1 className="text-4xl font-black text-slate-800 dark:text-white mt-3 tracking-tight">Bienvenido al espacio de coordinacion</h1>
                    <p className="text-slate-500 mt-4">Desde aqui puedes crear proyectos, mover tareas en Kanban y monitorear respuestas del equipo en un solo flujo.</p>
                    <button
                        onClick={handleCreate}
                        disabled={creating}
                        className="mt-6 inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 text-white text-xs font-black uppercase tracking-widest disabled:opacity-60"
                    >
                        <Plus size={16} /> {creating ? 'Creando...' : 'Crear primer proyecto'}
                    </button>
                </section>
                )}
            </main>
        </div>
    );
}

