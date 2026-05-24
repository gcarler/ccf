"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import WorkspaceToolbar from "@/components/WorkspaceToolbar";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { BookOpen, GraduationCap, Search, ShieldCheck, Users } from "lucide-react";

type TeacherRow = {
    id: number | string;
    name?: string;
    full_name?: string;
    email?: string;
    specialty?: string;
    course_count?: number;
    active_students?: number;
};

export default function AcademyTeachersPage() {
    const router = useRouter();
    const { token } = useAuth();
    const [teachers, setTeachers] = useState<TeacherRow[]>([]);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!token) return;
        const load = async () => {
            try {
                setLoading(true);
                const data = await apiFetch<TeacherRow[]>("/academy/users/?role=teacher", {
                    token,
                    cache: "no-store",
                });
                setTeachers(Array.isArray(data) ? data : []);
            } catch (error) {
                console.error("Error loading academy teachers", error);
                setTeachers([]);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [token]);

    const filtered = useMemo(() => {
        const value = query.trim().toLowerCase();
        if (!value) return teachers;
        return teachers.filter((teacher) =>
            [teacher.name, teacher.full_name, teacher.email, teacher.specialty]
                .some((field) => String(field ?? "").toLowerCase().includes(value))
        );
    }, [query, teachers]);

    return (
        <div className="flex h-full flex-col overflow-hidden bg-[#f8fafc] dark:bg-[#0f1114]">
            <WorkspaceToolbar
                breadcrumbs={[
                    { label: "Academia", icon: GraduationCap, href: "/plataforma/academy" },
                    { label: "Facilitadores", icon: ShieldCheck },
                ]}
                rightActions={
                    <button
                        onClick={() => router.push("/academy/teacher")}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide text-white shadow-lg shadow-blue-500/20"
                    >
                        Panel docente
                    </button>
                }
            />

            <main className="flex-1 overflow-y-auto p-4 lg:p-4 space-y-3">
                <section className="grid grid-cols-1 gap-3 md:grid-cols-3">
                    <Metric icon={ShieldCheck} label="Facilitadores" value={teachers.length} />
                    <Metric icon={BookOpen} label="Cursos asignados" value={teachers.reduce((sum, row) => sum + (row.course_count ?? 0), 0)} />
                    <Metric icon={Users} label="Estudiantes activos" value={teachers.reduce((sum, row) => sum + (row.active_students ?? 0), 0)} />
                </section>

                <section className="rounded-lg border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-white/5">
                    <header className="flex flex-col gap-4 border-b border-slate-100 p-3 dark:border-white/10 md:flex-row md:items-center md:justify-between">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-blue-500">Equipo academico</p>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Facilitadores</h1>
                        </div>
                        <div className="relative w-full md:max-w-sm">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={17} />
                            <input
                                value={query}
                                onChange={(event) => setQuery(event.target.value)}
                                placeholder="Buscar facilitador..."
                                className="w-full rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-11 pr-4 text-sm font-semibold outline-none focus:border-blue-400 dark:border-white/10 dark:bg-black/20"
                            />
                        </div>
                    </header>

                    <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2 xl:grid-cols-3">
                        {filtered.map((teacher) => (
                            <article
                                key={teacher.id}
                                className="cursor-pointer rounded-lg border border-slate-200 bg-slate-50 p-3 transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:bg-white dark:border-white/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.06]"
                                onClick={() => router.push(`/academy/teacher?teacher=${teacher.id}`)}
                            >
                                <div className="mb-3 flex items-center gap-3">
                                    <div className="flex size-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-semibold text-white">
                                        {(teacher.full_name || teacher.name || "F").slice(0, 2).toUpperCase()}
                                    </div>
                                    <div>
                                        <h2 className="font-bold text-slate-900 dark:text-white">{teacher.full_name || teacher.name || "Facilitador"}</h2>
                                        <p className="text-xs font-semibold text-slate-400">{teacher.email || "Sin correo"}</p>
                                    </div>
                                </div>
                                <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">{teacher.specialty || "Formacion ministerial"}</p>
                                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                                    <span className="font-semibold text-slate-500 dark:bg-black/20">{teacher.course_count ?? 0} cursos</span>
                                    <span className="font-semibold text-slate-500 dark:bg-black/20">{teacher.active_students ?? 0} alumnos</span>
                                </div>
                            </article>
                        ))}
                        {!loading && filtered.length === 0 && (
                            <div className="col-span-full py-1.5 text-center text-sm font-semibold text-slate-400">
                                No hay facilitadores registrados para mostrar.
                            </div>
                        )}
                        {loading && (
                            <div className="col-span-full py-1.5 text-center text-sm font-semibold text-slate-400">
                                Cargando facilitadores...
                            </div>
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
