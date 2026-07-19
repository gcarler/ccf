"use client";

/**
 * CourseCatalog — Orquestador (ACAD-TKT-043 refactor 2026-07-19).
 *
 * Antes: 389 LOC monolíticos con tipos + constantes + 8 vistas inline.
 * Después: ~95 LOC de orquestación que importa de ``./course-catalog/``.
 *
 * Estructura del split:
 * - ``course-catalog/types.ts`` — Course, Modality, AccessLevel, CourseCatalogProps
 * - ``course-catalog/constants.ts`` — ACCESS_LABEL, ACCESS_COLOR, COURSE_CATALOG_AVAILABLE_VIEWS
 * - ``course-catalog/views.tsx`` — GridView, ListView, TableView, BoardView,
 *   CalendarView, GanttView, WikiView (cada vista como sub-componente React)
 *
 * El default export sigue siendo ``CourseCatalog`` para backward-compat. Las
 * props y el comportamiento se preservan 1:1.
 */
import { useEffect, useState } from "react";
import { useToast } from "@/context/ToastContext";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/http";
import ViewSwitcher, { getStoredView } from "@/components/ViewSwitcher";
import type { ViewType } from "@/components/ViewSwitcher";
import { useWikiDocument } from "@/hooks/useWikiDocument";
import { COURSE_CATALOG_AVAILABLE_VIEWS } from "./course-catalog/constants";
import {
    GridView,
    ListView,
    TableView,
    BoardView,
    CalendarView,
    GanttView,
    WikiView,
} from "./course-catalog/views";
import type { Course, CourseCatalogProps, Modality } from "./course-catalog/types";

export default function CourseCatalog({
    token,
    enrolledCourseIds = [],
    initialCourses,
    viewType,
    onViewTypeChange,
    showViewSwitcher = true,
}: CourseCatalogProps) {
    const { addToast } = useToast();
    const router = useRouter();

    const [courses, setCourses] = useState<Course[]>(initialCourses ?? []);
    const [loading, setLoading] = useState(!initialCourses);
    const [filterModality, setFilterModality] = useState<Modality | "all">("all");
    const [internalViewType, setInternalViewType] = useState<ViewType>(() =>
        getStoredView("academy_catalog_view", "grid"),
    );
    const { content: wikiNotes, setContent: setWikiNotes } = useWikiDocument(
        "academy_catalog_wiki_notes",
        { title: "Wiki del catalogo academico" },
    );
    const resolvedViewType = viewType ?? internalViewType;

    const handleViewTypeChange = (nextView: ViewType) => {
        if (onViewTypeChange) {
            onViewTypeChange(nextView);
            return;
        }
        setInternalViewType(nextView);
    };

    useEffect(() => {
        if (initialCourses && filterModality === "all") {
            setCourses(initialCourses);
            setLoading(false);
            return;
        }
        const loadCourses = async () => {
            if (!token) {
                setCourses(initialCourses ?? []);
                setLoading(false);
                return;
            }
            setLoading(true);
            try {
                const data = await apiFetch<Course[]>("/academy/courses/", {
                    token,
                    cache: "no-store",
                    query: filterModality === "all" ? undefined : { modality: filterModality },
                });
                setCourses(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error("Error loading courses", error);
                addToast("No pudimos cargar los cursos", "error");
                setCourses([]);
            } finally {
                setLoading(false);
            }
        };
        loadCourses();
    }, [filterModality, token, addToast, initialCourses]);

    const handleEnrollClick = (courseId: string) => {
        if (enrolledCourseIds.includes(courseId)) {
            router.push(`/plataforma/academy/course/${courseId}`);
        } else {
            router.push(`/plataforma/academy/enroll/${courseId}`);
        }
    };

    const viewProps = { courses, enrolledCourseIds, onEnrollClick: handleEnrollClick };

    return (
        <div className="space-y-3">
            <div className="flex items-center gap-3 overflow-x-auto hide-scrollbar pb-2 px-4">
                <div className="flex gap-3 flex-1">
                    {(["all", "formal", "no_formal"] as const).map((m) => (
                        <button
                            key={m}
                            onClick={() => setFilterModality(m)}
                            className={`px-3 py-2.5 rounded-full text-sm font-bold whitespace-nowrap transition-all ${
                                filterModality === m
                                    ? "bg-primary text-white shadow-lg shadow-primary/20"
                                    : "glass text-[hsl(var(--text-secondary))]"
                            }`}
                        >
                            {m === "all" ? "Todos" : m === "formal" ? "Teología" : "Liderazgo"}
                        </button>
                    ))}
                </div>
                {showViewSwitcher && (
                    <ViewSwitcher
                        viewType={resolvedViewType}
                        setViewType={handleViewTypeChange}
                        availableViews={[...COURSE_CATALOG_AVAILABLE_VIEWS]}
                        storageKey="academy_catalog_view"
                    />
                )}
            </div>

            {loading ? (
                <div className="flex justify-center py-1.5">
                    <div className="w-8 h-8 animate-spin border-4 border-primary border-t-transparent rounded-full" />
                </div>
            ) : (
                <>
                    {resolvedViewType === "grid" && <GridView {...viewProps} />}
                    {resolvedViewType === "list" && <ListView {...viewProps} />}
                    {resolvedViewType === "table" && <TableView {...viewProps} />}
                    {(resolvedViewType === "board" || resolvedViewType === "kanban") && (
                        <BoardView {...viewProps} />
                    )}
                    {resolvedViewType === "calendar" && <CalendarView {...viewProps} />}
                    {resolvedViewType === "gantt" && <GanttView {...viewProps} />}
                    {resolvedViewType === "wiki" && (
                        <WikiView
                            wikiNotes={wikiNotes}
                            onWikiNotesChange={setWikiNotes}
                        />
                    )}
                </>
            )}
        </div>
    );
}
