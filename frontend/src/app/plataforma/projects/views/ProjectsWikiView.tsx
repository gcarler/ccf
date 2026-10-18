'use client';

import { BookOpen, Sparkles } from 'lucide-react';
import UniversalWikiView from '@/components/ui/UniversalWikiView';

const OPA_TAXONOMY_ITEMS = [
    'Políticas, Estándares y Plantillas PMO',
    'Registro Histórico de Lecciones Aprendidas',
    'Criterios de Salida Stage-Gate y DoD',
];

export default function ProjectsWikiView() {
    return (
        <div className="space-y-3 pb-4">
            {/* Banner de Gobernanza Documental y Activos OPA PMI §4.4 */}
            <div
                data-testid="projects-wiki-pmi-opa-banner"
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-3"
            >
                <div className="space-y-0.5">
                    <div className="flex items-center gap-2">
                        <BookOpen size={15} className="text-[hsl(var(--primary))]" />
                        <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--foreground))]">
                            Repositorio Central de Activos de Procesos de la Organización (OPA) · PMI §4.4
                        </h3>
                    </div>
                    <p className="text-xs text-[hsl(var(--muted-foreground))]">
                        Base de conocimiento histórica, estándares metodológicos y lecciones aprendidas del portafolio
                    </p>
                </div>

                <div
                    data-testid="projects-wiki-opa-taxonomy"
                    className="flex flex-wrap items-center gap-1.5"
                >
                    {OPA_TAXONOMY_ITEMS.map((item) => (
                        <span
                            key={item}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-bold border border-[hsl(var(--primary)/0.3)] bg-[hsl(var(--primary)/0.08)] text-[hsl(var(--primary))]"
                        >
                            <Sparkles size={10} />
                            {item}
                        </span>
                    ))}
                </div>
            </div>

            <UniversalWikiView moduleName="Proyectos" storageKey="wiki_projects_portfolio" />
        </div>
    );
}

