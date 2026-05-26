"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import ViewSwitcher, { ViewType } from "@/components/ViewSwitcher";
import { useViewType, MINIMAL_VIEWS } from "@/hooks/useViewType";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { GraduationCap, Search, UserRound, BookOpen, BarChart3 } from "lucide-react";

type StudentRow = {
    id: number | string;
    name?: string;
    full_name?: string;
    email?: string;
    role?: string;
    status?: string;
    course_count?: number;
    progress?: number;
};

export default function AcademyStudentsPage() {
    const router = useRouter();
    const { token } = useAuth();
    const { viewType, setViewType } = useViewType('academy_students', 'table');
    const [students, setStudents] = useState<StudentRow[]>([]);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const load = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<StudentRow[]>("/academy/users/?role=student", {
                    token,
                    cache: "no-store",
                });
                setStudents(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error("Error loading academy students", error);
                setStudents([]);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

    const filtered = useMemo(() => {
        const value = query.trim().toLowerCase();
        if (!value) return students;
        return students.filter((student) =>
            [student.name, student.full_name, student.email, student.status]
                .some((field) => String(field ?? "").toLowerCase().includes(value))
        );
    }, [query, students]);

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#0f1114]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Academia", icon: GraduationCap, href: "/plataforma/academy" },
                    { label: "Estudiantes", icon: UserRound },
                ]}
                rightActions={
                    <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                            {filtered.length} activos
                        </span>
                        <ViewSwitcher viewType={viewType} setViewType={setViewType} availableViews={MINIMAL_VIEWS} />
                    </div>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3">
                <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <Metric icon={UserRound} label="Estudiantes" value={students.length} />
                    <Metric icon={BookOpen} label="Inscripciones" value={students.reduce((sum, row) => sum + (row.course_count ?? 0), 0)} />
                    <Metric icon={BarChart3} label="Progreso prom." value={`${Math.round(students.reduce((sum, row) => sum + (row.progress ?? 0), 0) / Math.max(students.length, 1))}%`} />
                </section>

                <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/5">
                    <header className="flex flex-col gap-4 border-b border-slate-100 p-3 dark:border-white/10 md:flex-row md:items-center md:justify-between">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-500">Directorio academico</p>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Estudiantes</h1>
                        </div>
                        <div className="relative w-full md:max-w-sm">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
                            <input
                                value={query}
                                onChange={(event) => setQuery(event.target.value)}
                                placeholder="Buscar estudiante..."
                                className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-11 pr-4 text-sm font-semibold outline-none focus:border-blue-400 dark:border-white/10 dark:bg-black/20"
                            />
                        </div>
                    </header>

                    <div className="overflow-x-auto">
                        {viewType === 'list' ? (
                            <div className="space-y-1">
                                {filtered.map(s => (
                                    <div key={s.id} onClick={() => router.push(`/academy/profile?student=${s.id}`)} className="flex items-center gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-white/5 cursor-pointer transition-all">
                                        <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center shrink-0 text-blue-600 dark:text-blue-400 font-bold text-xs">
                                            {(s.full_name || s.name || 'E')[0]}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-semibold text-slate-900 dark:text-white truncate">{s.full_name || s.name || "Estudiante"}</p>
                                            <p className="text-xs text-slate-400">{s.email || 'Sin correo'}</p>
                                        </div>
                                        <span className="text-xs text-slate-500">{s.course_count ?? 0} cursos</span>
                                        <span className="text-xs text-slate-500 w-16">{s.progress ?? 0}%</span>
                                    </div>
                                ))}
                                {!loading && filtered.length === 0 && (
                                    <div className="py-8 text-center text-sm font-semibold text-slate-400">No hay estudiantes registrados.</div>
                                )}
                            </div>
                        ) : viewType === 'grid' ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-3">
                                {filtered.map(s => (
                                    <div key={s.id} onClick={() => router.push(`/academy/profile?student=${s.id}`)} className="rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-[#1a1b1e] p-4 hover:shadow-md cursor-pointer transition-all">
                                        <h3 className="text-sm font-bold text-slate-900 dark:text-white">{s.full_name || s.name || "Estudiante"}</h3>
                                        <p className="text-xs text-slate-400 mt-1">{s.email || 'Sin correo'}</p>
                                        <div className="flex items-center justify-between mt-3">
                                            <span className="text-xs text-slate-500">{s.course_count ?? 0} cursos</span>
                                            <span className="text-xs text-slate-500">{s.progress ?? 0}% progreso</span>
                                        </div>
                                    </div>
                                ))}
                                {!loading && filtered.length === 0 && (
                                    <div className="col-span-full py-8 text-center text-sm font-semibold text-slate-400">No hay estudiantes registrados.</div>
                                )}
                            </div>
                        ) : (
                        <table className="min-w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-100 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:border-white/10">
                                    <th className="px-4 py-1.5">Nombre</th>
                                    <th className="px-4 py-1.5">Correo</th>
                                    <th className="px-4 py-1.5">Cursos</th>
                                    <th className="px-4 py-1.5">Progreso</th>
                                    <th className="px-4 py-1.5">Estado</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((student) => (
                                    <tr
                                        key={student.id}
                                        className="cursor-pointer border-b border-slate-50 transition-colors hover:bg-slate-50 dark:border-white/5 dark:hover:bg-white/[0.03]"
                                        onClick={() => router.push(`/academy/profile?student=${student.id}`)}
                                    >
                                        <td className="px-4 py-1.5 font-bold text-slate-900 dark:text-white">{student.full_name || student.name || "Estudiante"}</td>
                                        <td className="px-4 py-1.5 text-slate-500">{student.email || "Sin correo"}</td>
                                        <td className="px-4 py-1.5 text-slate-500">{student.course_count ?? 0}</td>
                                        <td className="px-4 py-1.5 text-slate-500">{student.progress ?? 0}%</td>
                                        <td className="px-4 py-1.5">
                                            <span className="rounded-full bg-emerald-50 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-emerald-600">
                                                {student.status || "Activo"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                                {!loading && filtered.length === 0 && (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-1.5 text-center text-sm font-semibold text-slate-400">
                                            No hay estudiantes registrados para mostrar.
                                        </td>
                                    </tr>
                                )}
                                {loading && (
                                    <tr>
                                        <td colSpan={5} className="px-4 py-1.5 text-center text-sm font-semibold text-slate-400">
                                            Cargando estudiantes...
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                        )}
                    </div>
                </section>
            </main>
        </div>
    );
}

function Metric({ icon: Icon, label, value }: { icon: any; label: string; value: number | string }) {
    return (
        <div className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm dark:border-white/10 dark:bg-white/5">
            <div className="mb-3 flex size-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-500/10">
                <Icon size={20} />
            </div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
            <p className="text-lg font-bold text-slate-900 dark:text-white">{value}</p>
        </div>
    );
}
