/**
 * Tipos compartidos del módulo CourseCatalog (ACAD-TKT-043 refactor).
 *
 * Antes viven en ``CourseCatalog.tsx`` (389 LOC monolítico). Se extraen aquí
 * para que las 8 vistas inline + el orquestador puedan tipar de forma consistente.
 */
import type { ViewType } from "@/components/ViewSwitcher";

export type Modality = "formal" | "no_formal";

export type AccessLevel = "open" | "persona" | "advanced";

export interface Course {
    id: string;
    code: string;
    title: string;
    description: string;
    modality: Modality;
    duration_hours: number;
    is_self_paced: boolean;
    cohort_name?: string | null;
    certificate_type?: string | null;
    lesson_count: number;
    total_minutes: number;
    access_level?: AccessLevel;
}

export interface CourseCatalogProps {
    token: string;
    enrolledCourseIds?: string[];
    initialCourses?: Course[];
    viewType?: ViewType;
    onViewTypeChange?: (view: ViewType) => void;
    showViewSwitcher?: boolean;
}
