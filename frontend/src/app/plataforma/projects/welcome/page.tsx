"use client";

import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { useRouter } from 'next/navigation';
import ProjectsShell from '@/components/projects/ProjectsShell';
import type { ViewType } from '@/components/ViewSwitcher';
import type { ProjectRecord } from '@/types/projects';
import { Hash, Layout, Plus } from 'lucide-react';
import { toast } from 'sonner';
import TextPromptDrawer from '@/components/ui/TextPromptDrawer';

export default function ProjectsWelcomePage() {
    const { token } = useAuth();
    const router = useRouter();
    const [creating, setCreating] = useState(false);
    const [viewType, setViewType] = useState<ViewType>('grid');
    const [projectNameDraft, setProjectNameDraft] = useState('');
    const [createProjectOpen, setCreateProjectOpen] = useState(false);
    const quickStarts = [
        { title: 'Crear proyecto', description: 'Inicia un proyecto y define su alcance.' },
        { title: 'Organizar tareas', description: 'Usa Kanban para mover el trabajo del equipo.' },
        { title: 'Monitorear respuestas', description: 'Revisa comentarios y decisiones en un solo lugar.' },
    ];

    const handleCreate = () => {
        setProjectNameDraft('');
        setCreateProjectOpen(true);
    };

    const submitCreate = async () => {
        const title = projectNameDraft.trim();
        if (!title) return;
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
            router.push(`/plataforma/projects/${project.id}`);
        } catch (error) {
            toast.error("Error inesperado");
            toast.error('Error al crear proyecto');
        } finally {
            setCreating(false);
            setCreateProjectOpen(false);
        }
    };

    return (
        <ProjectsShell
            breadcrumbs={[{ label: 'Proyectos', icon: Layout }, { label: 'Welcome', icon: Hash }]}
            viewType={viewType}
            onViewChange={setViewType}
            viewOptions={['grid', 'list', 'table']}
        >
            <TextPromptDrawer
                isOpen={createProjectOpen}
                onClose={() => setCreateProjectOpen(false)}
                onSubmit={submitCreate}
                title="Crear primer proyecto"
                subtitle="Usa un nombre corto y claro"
                label="Nombre del proyecto"
                value={projectNameDraft}
                onChange={setProjectNameDraft}
                placeholder="Ej. Campaña de visitas"
                submitLabel={creating ? 'Creando…' : 'Crear'}
            />
            <main className="flex-1 overflow-y-auto p-3">
                {viewType === 'list' && (
                    <div className="max-w-3xl space-y-3">
                        {quickStarts.map((item) => (
                            <article key={item.title} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-3 dark:border-white/10 dark:bg-white/5">
                                <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white">{item.title}</h3>
                                <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">{item.description}</p>
                            </article>
                        ))}
                    </div>
                )}
                {viewType === 'table' && (
                    <div className="max-w-4xl overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-white/5">
                        <table className="w-full text-left">
                            <thead className="bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                <tr><th className="px-3 py-2">Recurso</th><th className="px-3 py-2">Descripción</th></tr>
                            </thead>
                            <tbody>
                                {quickStarts.map((item) => (
                                    <tr key={item.title} className="border-t border-[hsl(var(--border))] dark:border-white/5">
                                        <td className="px-3 py-2 font-medium text-[hsl(var(--text-primary))] dark:text-white">{item.title}</td>
                                        <td className="px-3 py-2 text-[hsl(var(--text-secondary))]">{item.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {viewType === 'grid' && (
                <section className="max-w-3xl rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-gradient-to-br from-blue-50 to-white dark:from-blue-900/20 dark:to-transparent">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))]">Workspace de proyectos</p>
                    <h1 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white mt-2 tracking-tight">Bienvenido al espacio de coordinacion</h1>
                    <p className="text-[hsl(var(--text-secondary))] mt-2">Desde aqui puedes crear proyectos, mover tareas en Kanban y monitorear respuestas del equipo en un solo flujo.</p>
                    <button
                        onClick={handleCreate}
                        disabled={creating}
                        className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-white text-xs font-bold uppercase tracking-wide disabled:opacity-60"
                    >
                        <Plus size={16} /> {creating ? 'Creando...' : 'Crear primer proyecto'}
                    </button>
                </section>
                )}
            </main>
        </ProjectsShell>
    );
}
