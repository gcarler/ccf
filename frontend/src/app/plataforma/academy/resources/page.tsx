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
                href: `/academy/course/${enrollment.course.id}`,
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
            <div className="relative group mb-3 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                    <Search className="text-slate-500 group-focus-within:text-primary" size={20} />
                </div>
                <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full bg-transparent border border-slate-200 dark:border-white/10 rounded-lg py-2 pl-12 pr-4 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-primary/50 focus:border-primary/50"
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
                        className="ml-auto text-[11px] font-semibold uppercase tracking-wide text-slate-400 hover:text-primary"
                    >
                        Actualizar
                    </button>
                </div>
            </div>

            {(enrollmentsError || lessonsError) && (
                <p className="text-sm text-rose-400 font-semibold">
                    {enrollmentsError || lessonsError}
                </p>
            )}

            {(loading || lessonsLoading) && (
                <p className="text-center text-slate-400 text-sm py-2">Buscando recursos de tus cursos...</p>
            )}

            {!loading && resources.length === 0 && (
                <div className="py-1.5 text-center text-slate-400 space-y-3">
                    <BookOpen className="w-12 h-8 mx-auto text-slate-600" />
                    <p className="text-sm font-bold text-white">No hay material disponible aún</p>
                    <p className="text-sm">Cuando tus cursos publiquen material descargable aparecerá en esta biblioteca.</p>
                </div>
            )}

            {favoriteResources.length > 0 && (
                <section className="py-2 flex flex-col gap-3 rounded-md border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-[#16191d] p-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-sm font-semibold uppercase tracking-wide text-amber-500 flex items-center gap-2">
                            <Star size={14} /> Guardados
                        </h2>
                        <span className="font-semibold text-slate-400 uppercase tracking-wide">{favoriteResources.length}</span>
                    </div>
                    {favoriteResources.map((resource) => (
                        <ResourceRow key={`fav-${resource.id}`} resource={resource} isFavorite onToggleFavorite={toggleFavorite} />
                    ))}
                </section>
            )}

            <section className="py-2 flex flex-col gap-3 rounded-md border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4">
                 <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">{filteredResources.length} recursos encontrados</h2>
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
        <article className="bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 hover:border-primary/30 rounded-md p-3 flex items-center gap-3 shadow-xl transition-all">
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 border border-primary/20 text-primary">
                {resource.snippet.length > 120 ? <FileText size={28} /> : <BookOpen size={28} />}
            </div>
            <div className="flex flex-col flex-1 min-w-0">
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wide mb-1">{resource.courseTitle}</p>
                <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">{resource.lessonTitle}</h3>
                <p className="text-[12px] text-slate-500 dark:text-slate-300 mt-1 line-clamp-2">{resource.snippet}</p>
                <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wide mt-3">{resource.duration}</p>
            </div>
            <div className="flex items-center gap-3">
                <button
                    onClick={() => onToggleFavorite(resource.id)}
                    className={`size-8 rounded-full border ${isFavorite ? 'border-amber-400 text-amber-400 bg-amber-50' : 'border-slate-200 dark:border-white/10 text-slate-400 bg-white dark:bg-white/10'} hover:scale-105 transition-transform`}
                >
                    <Star size={18} fill={isFavorite ? 'currentColor' : 'none'} />
                </button>
                <a
                    href={resource.href}
                    className="shrink-0 size-9 rounded-full bg-white dark:bg-white/10 flex items-center justify-center border border-slate-200 dark:border-white/10 hover:bg-primary hover:border-primary/40 transition-colors text-slate-400 hover:text-white"
                >
                    <Download size={20} />
                </a>
            </div>
        </article>
    );
}

