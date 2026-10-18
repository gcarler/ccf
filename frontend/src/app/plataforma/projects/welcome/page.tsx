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

    const handleCreateWithTemplate = (templateTitle: string) => {
        setProjectNameDraft(templateTitle);
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
            router.push(`/plataforma/projects/${project.id}?view=list`);
        } catch {
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
            <main className="flex-1 overflow-y-auto p-3 space-y-3">
                <section
                    data-testid="projects-welcome-pmi-banner"
                    aria-label="Iniciación Metodológica y Gobernanza PMI §4.1"
                    className="max-w-4xl rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2)/0.45)] p-3 space-y-2.5"
                >
                    <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">
                        Iniciación Metodológica y Gobernanza PMI §4.1
                    </p>
                    <div className="flex flex-wrap gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--foreground))]">
                        <span className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1">
                            1. Acta de Constitución (Project Charter §4.1)
                        </span>
                        <span className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1">
                            2. Estructura de Desglose del Trabajo (WBS 0/50/100 §5.4)
                        </span>
                        <span className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2.5 py-1">
                            3. Control de Valor Ganado (EVM CPI×SPI §7.4)
                        </span>
                    </div>
                    <div
                        data-testid="projects-welcome-pmi-templates"
                        className="flex flex-wrap items-center gap-2 pt-1"
                    >
                        <button
                            type="button"
                            data-testid="welcome-template-charter"
                            onClick={() => handleCreateWithTemplate('Iniciativa Ministerial — Línea Base PMI')}
                            disabled={creating}
                            className="px-2.5 py-1 rounded-md border border-[hsl(var(--primary)/0.35)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] text-2xs font-semibold uppercase tracking-wide hover:bg-[hsl(var(--primary)/0.2)] transition-colors disabled:opacity-60"
                        >
                            Iniciar con Plantilla Charter PMI
                        </button>
                        <button
                            type="button"
                            data-testid="welcome-template-wbs"
                            onClick={() => handleCreateWithTemplate('Despliegue Operativo de Sede — WBS')}
                            disabled={creating}
                            className="px-2.5 py-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] text-2xs font-semibold uppercase tracking-wide hover:bg-[hsl(var(--surface-2))] transition-colors disabled:opacity-60"
                        >
                            Iniciar Despliegue WBS de Sede
                        </button>
                    </div>
                </section>
                {viewType === 'list' && (
                    <div className="max-w-3xl space-y-3">
                        {quickStarts.map((item) => (
                            <article key={item.title} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3">
                                <h3 className="font-bold text-[hsl(var(--foreground))]">{item.title}</h3>
                                <p className="mt-1 text-sm text-[hsl(var(--muted-foreground))]">{item.description}</p>
                            </article>
                        ))}
                    </div>
                )}
                {viewType === 'table' && (
                    <div className="max-w-4xl overflow-hidden rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                        <table className="w-full text-left">
                            <thead className="bg-[hsl(var(--surface-2))] text-2xs font-bold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
                                <tr><th className="px-3 py-2">Recurso</th><th className="px-3 py-2">Descripción</th></tr>
                            </thead>
                            <tbody>
                                {quickStarts.map((item) => (
                                    <tr key={item.title} className="border-t border-[hsl(var(--border))]">
                                        <td className="px-3 py-2 font-medium text-[hsl(var(--foreground))]">{item.title}</td>
                                        <td className="px-3 py-2 text-[hsl(var(--muted-foreground))]">{item.description}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
                {viewType === 'grid' && (
                <section className="max-w-3xl rounded-lg border border-[hsl(var(--border))] p-3 bg-[hsl(var(--surface-1))]">
                    <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--primary))]">Workspace de proyectos</p>
                    <h1 className="text-lg font-bold text-[hsl(var(--foreground))] mt-2 tracking-tight">Bienvenido al espacio de coordinación</h1>
                    <p className="text-[hsl(var(--muted-foreground))] mt-2">Desde aquí puedes crear proyectos, mover tareas en Kanban y monitorear respuestas del equipo en un solo flujo.</p>
                    <button
                        onClick={handleCreate}
                        disabled={creating}
                        className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-bold uppercase tracking-wide disabled:opacity-60"
                    >
                        <Plus size={16} /> {creating ? 'Creando...' : 'Crear primer proyecto'}
                    </button>
                </section>
                )}
            </main>
        </ProjectsShell>
    );
}
