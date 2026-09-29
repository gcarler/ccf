"use client";

import React, { useMemo, useState, useCallback } from 'react';
import { Search, Star, BookOpen, FileText, Download } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import { useCourseLessons } from '@/hooks/useCourseLessons';
import AdminHero from '@/components/admin/AdminHero';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import { toast } from 'sonner';

type ResourceEntry = {
    id: string;
    lessonTitle: string;
    courseTitle: string;
    snippet: string;
    duration: string;
    href: string;
};

const filters = ['Todos', 'Lecciones', 'Materiales'];

export default function ResourcesLibrary() {
    const { token, isAuthenticated } = useAuth();
    const { enrollments, loading, error: enrollmentsError, refresh } = useStudentEnrollments();
    const { lessonsByCourse, loading: lessonsLoading, error: lessonsError } = useCourseLessons(
        enrollments.map((en) => en.course.id),
        token,
    );
    const [activeFilter, setActiveFilter] = useState('Todos');
    const [query, setQuery] = useState('');
    const [favorites, setFavorites] = useState<string[]>([]);
    const [showFavorites, setShowFavorites] = useState(false);

    const resources: ResourceEntry[] = useMemo(() => {
        return enrollments.flatMap((enrollment) => {
            const lessons = lessonsByCourse[enrollment.course.id] || [];
            return lessons.map((lesson) => ({
                id: `${enrollment.id}-${lesson.id}`,
                lessonTitle: lesson.title,
                courseTitle: enrollment.course.title,
                snippet: cleanSnippet(lesson.content),
                duration: lesson.duration_minutes ? `${lesson.duration_minutes} min` : enrollment.course.modality,
                href: `/plataforma/academy/course/${enrollment.course.id}`,
            }));
        });
    }, [enrollments, lessonsByCourse]);

    const filteredResources = resources.filter((resource) => {
        const matchesQuery = resource.lessonTitle.toLowerCase().includes(query.toLowerCase()) ||
            resource.courseTitle.toLowerCase().includes(query.toLowerCase());
        if (!matchesQuery) return false;
        if (activeFilter === 'Lecciones') return true;
        if (activeFilter === 'Materiales') return resource.snippet.length > 120;
        return true;
    }).filter((resource) => !showFavorites || favorites.includes(resource.id));

    const favoriteResources = resources.filter((resource) => favorites.includes(resource.id));

    const toggleFavorite = useCallback((id: string) => {
        setFavorites((prev) => prev.includes(id) ? prev.filter((fav) => fav !== id) : [...prev, id]);
    }, []);

    const handleRefresh = useCallback(async () => {
        await refresh();
        toast.success('Biblioteca sincronizada');
    }, [refresh]);

    if (!isAuthenticated) return null;

    return (
        <div className="space-y-3 px-4 py-1.5">
            <AdminHero
                eyebrow="Recursos"
                title="Biblioteca virtual"
                description="Filtra recursos por nivel y descarga materiales selectos."
                tags={['Lecciones', 'Materiales', 'Descargas']}
                watchers={['Equipo Recursos', 'Optimus Brain']}
                primaryAction={{ label: showFavorites ? 'Ver todos' : 'Favoritos', icon: Star, onClick: () => setShowFavorites((prev) => !prev) }}
            />
            <div className="relative group mb-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Search className="text-[hsl(var(--text-secondary))] group-focus-within:text-[hsl(var(--primary))]" size={20} />
                </div>
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full bg-transparent border border-[hsl(var(--border))] rounded-lg py-2 pl-12 pr-4 text-sm text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] focus:ring-2 focus:ring-[hsl(var(--primary)/0.5)] focus:border-[hsl(var(--primary)/0.5)]"
                    placeholder="Buscar lecciones o cursos"
                    type="text"
                />
                <div className="flex gap-2 mt-4">
                    {filters.map((filter) => (
                        <CommunityToolbarChip
                            key={filter}
                            label={filter}
                            active={activeFilter === filter}
                            variant={activeFilter === filter ? 'solid' : 'outline'}
                            onClick={() => setActiveFilter(filter)}
                        />
                    ))}
                    <button
                        onClick={handleRefresh}
                        className="ml-auto text-xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]"
                    >
                        Actualizar
                    </button>
                </div>
            </div>

            {(enrollmentsError || lessonsError) && (
                <p className="text-sm text-[hsl(var(--danger))] font-semibold">
                    {enrollmentsError || lessonsError}
                </p>
            )}

            {(loading || lessonsLoading) && (
                <p className="text-center text-[hsl(var(--text-secondary))] text-sm py-2">Buscando recursos de tus cursos...</p>
            )}

            {!loading && resources.length === 0 && (
                <div className="py-1.5 text-center text-[hsl(var(--text-secondary))] space-y-3">
                    <BookOpen className="w-12 h-8 mx-auto text-[hsl(var(--text-secondary))]" />
                    <p className="text-sm font-bold text-[hsl(var(--foreground))]">No hay material disponible aún</p>
                    <p className="text-sm">Cuando tus cursos publiquen material descargable aparecerá en esta biblioteca.</p>
                </div>
            )}

            {favoriteResources.length > 0 && (
                <section className="py-2 flex flex-col gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-[hsl(var(--warning))] flex items-center gap-2">
                            <Star size={14} /> Guardados
                        </h2>
                        <span className="font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">{favoriteResources.length}</span>
                    </div>
                    {favoriteResources.map((resource) => (
                        <ResourceRow key={`fav-${resource.id}`} resource={resource} isFavorite onToggleFavorite={toggleFavorite} />
                    ))}
                </section>
            )}

            <section className="py-2 flex flex-col gap-3 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                 <h2 className="text-base font-bold text-[hsl(var(--foreground))] tracking-tight">{filteredResources.length} recursos encontrados</h2>
                 {filteredResources.map((resource) => (
                     <ResourceRow key={resource.id} resource={resource} isFavorite={favorites.includes(resource.id)} onToggleFavorite={toggleFavorite} />
                 ))}
             </section>
        </div>
    );
}

function cleanSnippet(html: string) {
    if (!html) return '';
    return html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 160) + '...';
}

function ResourceRow({ resource, isFavorite, onToggleFavorite }: { resource: ResourceEntry; isFavorite?: boolean; onToggleFavorite: (id: string) => void; }) {
    return (
        <article className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] hover:border-[hsl(var(--primary)/0.3)] rounded-md p-3 flex items-center gap-3 shadow-xl transition-all">
            <div className="size-8 rounded-lg bg-[hsl(var(--primary)/0.1)] flex items-center justify-center shrink-0 border border-[hsl(var(--primary)/0.2)] text-[hsl(var(--primary))]">
                {resource.snippet.length > 120 ? <FileText size={28} /> : <BookOpen size={28} />}
            </div>
            <div className="flex flex-col flex-1 min-w-0">
                <p className="text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mb-1">{resource.courseTitle}</p>
                <h3 className="text-base font-bold text-[hsl(var(--foreground))] truncate">{resource.lessonTitle}</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1 line-clamp-2">{resource.snippet}</p>
                <p className="text-2xs text-[hsl(var(--text-secondary))] font-semibold uppercase tracking-wide mt-3">{resource.duration}</p>
            </div>
            <div className="flex items-center gap-3">
                <button
                    onClick={() => onToggleFavorite(resource.id)}
                    className={`size-8 rounded-full border ${isFavorite ? 'border-[hsl(var(--warning)/40%)] text-[hsl(var(--warning))] bg-[hsl(var(--warning)/0.1)]' : 'border-[hsl(var(--border))] text-[hsl(var(--muted-foreground))] bg-[hsl(var(--surface-1))]'} hover:scale-105 transition-transform`}
                >
                    <Star size={18} fill={isFavorite ? 'currentColor' : 'none'} />
                </button>
                <a
                    href={resource.href}
                    className="shrink-0 size-9 rounded-full bg-[hsl(var(--surface-1))] flex items-center justify-center border border-[hsl(var(--border))] hover:bg-[hsl(var(--primary))] hover:border-[hsl(var(--primary)/0.4)] transition-colors text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--primary-foreground))]"
                >
                    <Download size={20} />
                </a>
            </div>
        </article>
    );
}
