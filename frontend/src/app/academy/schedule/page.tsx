"use client";

import React, { useMemo, useState, useCallback } from 'react';
import { CalendarDays, MoreHorizontal, Video, Users, MapPin, Download } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useStudentEnrollments } from '@/hooks/useStudentEnrollments';
import { useCourseLessons } from '@/hooks/useCourseLessons';
import AdminHero from '@/components/admin/AdminHero';
import { toast } from 'sonner';

const DAYS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'];
const TIMES = ['08:00', '10:00', '13:00', '15:00'];

export default function StudentSchedule() {
    const { token, isAuthenticated } = useAuth();
    const { enrollments, loading, error: enrollmentError } = useStudentEnrollments();
    const { lessonsByCourse, loading: lessonsLoading, error: lessonsError } = useCourseLessons(
        enrollments.map((en) => en.course.id),
        token,
    );
    const [activeDay, setActiveDay] = useState(0);
    const [icsGenerating, setIcsGenerating] = useState(false);

    const sessions = useMemo(() => {
        const items: Array<{
            id: string;
            dayIndex: number;
            time: string;
            title: string;
            course: string;
            modality: string;
            location: string;
            instructor: string;
            isVirtual: boolean;
        }> = [];
        enrollments.forEach((enrollment, enrollmentIndex) => {
            const lessons = lessonsByCourse[enrollment.course.id] || [];
            lessons.slice(0, 3).forEach((lesson, lessonIndex) => {
                const dayIndex = (enrollmentIndex + lessonIndex) % DAYS.length;
                const time = TIMES[(lessonIndex + enrollmentIndex) % TIMES.length];
                items.push({
                    id: `${enrollment.id}-${lesson.id}`,
                    dayIndex,
                    time,
                    title: lesson.title,
                    course: enrollment.course.title,
                    modality: enrollment.course.modality,
                    location: enrollment.course.is_self_paced ? 'Campus Virtual' : enrollment.course.cohort_name || 'Sala principal',
                    instructor: enrollment.course.cohort_name || 'Mentor designado',
                    isVirtual: enrollment.course.is_self_paced,
                });
            });
        });
        return items;
    }, [enrollments, lessonsByCourse]);

    const filteredSessions = sessions.filter((session) => session.dayIndex === activeDay);

    const exportCalendar = useCallback(() => {
        if (!sessions.length) {
            toast.info('No hay sesiones para exportar');
            return;
        }
        setIcsGenerating(true);
        try {
            const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//CCF//Academy Schedule//ES'];
            sessions.forEach((session) => {
                const start = buildDate(session.dayIndex, session.time);
                const end = buildDate(session.dayIndex, nextSlot(session.time));
                lines.push('BEGIN:VEVENT');
                lines.push(`UID:${session.id}@ccf.local`);
                lines.push(`DTSTAMP:${formatDate(start)}Z`);
                lines.push(`DTSTART:${formatDate(start)}Z`);
                lines.push(`DTEND:${formatDate(end)}Z`);
                lines.push(`SUMMARY:${session.title}`);
                lines.push(`DESCRIPTION:${session.course} · ${session.modality}`);
                lines.push(`LOCATION:${session.location}`);
                lines.push('END:VEVENT');
            });
            lines.push('END:VCALENDAR');
            const blob = new Blob([lines.join('\n')], { type: 'text/calendar' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'ccf-schedule.ics';
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
            toast.success('Calendario exportado');
        } catch (err) {
            console.error(err);
            toast.error('No pudimos generar el calendario');
        } finally {
            setIcsGenerating(false);
        }
    }, [sessions]);

    if (!isAuthenticated) return null;

    return (
        <div className="space-y-8 px-4 py-8">
            <AdminHero
                eyebrow="Horario"
                title="Horario académico"
                description="Visualiza y administra tus sesiones presenciales y virtuales."
                tags={['Presencial', 'Virtual', 'IA Coach']}
                watchers={['Equipo Horarios', 'Optimus Brain']}
                primaryAction={{ label: icsGenerating ? 'Generando...' : 'Exportar .ics', icon: Download, onClick: exportCalendar }}
            />
            <div className="rounded-[2.5rem] border border-slate-200 dark:border-white/5 bg-white dark:bg-[#111418] shadow-xl overflow-hidden">
            <div className="flex gap-4 pb-4 overflow-x-auto hide-scrollbar p-6 border-b border-slate-100 dark:border-white/5">
                {DAYS.map((day, index) => (
                    <button
                        key={day}
                            onClick={() => setActiveDay(index)}
                            className={`flex flex-col items-center gap-3 cursor-pointer group shrink-0 transition-all ${
                                activeDay === index ? 'text-white' : 'text-slate-500 opacity-60'
                            }`}
                        >
                            <div
                                className={`flex h-14 w-14 items-center justify-center rounded-2xl border text-sm font-bold uppercase tracking-widest ${
                                    activeDay === index
                                        ? 'bg-primary border-primary/50 shadow-xl shadow-primary/30'
                                        : 'bg-slate-900 border-white/10 hover:border-primary/30'
                                }`}
                            >
                                {day.substring(0, 3)}
                            </div>
                            {activeDay === index && <div className="w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_8px_rgba(66,66,240,0.8)]"></div>}
                        </button>
                    ))}
                </div>

            <div className="flex-1 overflow-y-auto pb-12 px-6">
                    {(enrollmentError || lessonsError) && (
                        <p className="text-center text-rose-400 text-sm py-4">{enrollmentError || lessonsError}</p>
                    )}

                    {(loading || lessonsLoading) && (
                        <p className="text-center text-slate-400 text-sm py-8">Actualizando calendario...</p>
                    )}

                    {!loading && sessions.length === 0 && (
                        <p className="text-center text-slate-400 text-sm py-8">
                            Aún no hay sesiones programadas. Revisa tus cursos para obtener horarios oficiales.
                        </p>
                    )}

                    {filteredSessions.length > 0 && (
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-primary text-xs font-black uppercase tracking-widest">{DAYS[activeDay]}</h3>
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-widest border border-white/10 px-2 py-1 rounded">
                                {filteredSessions.length} sesiones
                            </span>
                        </div>
                    )}

                    <div className="relative">
                        <div className="absolute left-[11px] top-4 bottom-4 w-[2px] bg-white/5 rounded-full" />
                        {filteredSessions.map((session) => (
                            <div key={session.id} className="relative z-10 grid grid-cols-[24px_1fr] gap-x-6 mb-8">
                                <div className="flex justify-center pt-3">
                                    <div
                                        className={`w-3 h-3 rounded-full ${
                                            session.isVirtual ? 'bg-emerald-400 ring-4 ring-emerald-400/20' : 'bg-primary ring-4 ring-primary/20'
                                        }`}
                                    ></div>
                                </div>
                                <div className="bg-slate-900/50 backdrop-blur-xl p-6 rounded-[2rem] shadow-xl border border-white/5 hover:border-primary/30 transition-all">
                                    <div className="flex justify-between items-start mb-4">
                                        <span className="text-slate-300 text-xs font-black uppercase tracking-widest px-3 py-1.5 bg-slate-800 rounded-xl border border-white/5">
                                            {session.time} - {nextSlot(session.time)}
                                        </span>
                                        <button className="text-slate-500 hover:text-white p-1">
                                            <MoreHorizontal size={20} />
                                        </button>
                                    </div>
                                    <h4 className="text-white text-xl font-bold mb-3 tracking-tight">{session.title}</h4>
                                    <p className="text-slate-400 text-sm mb-4">{session.course}</p>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex items-center gap-3 text-slate-400 text-sm">
                                            <div className="p-1.5 rounded-lg bg-white/5">
                                                <Users size={14} className="text-primary-300" />
                                            </div>
                                            <span className="font-medium">{session.instructor}</span>
                                        </div>
                                        <div className="flex items-center gap-3 text-slate-400 text-sm">
                                            <div className="p-1.5 rounded-lg bg-white/5">
                                                <MapPin size={14} className="text-rose-400" />
                                            </div>
                                            <span className="font-medium">{session.location}</span>
                                        </div>
                                        {session.isVirtual && (
                                            <button className="flex items-center gap-3 text-emerald-400 text-sm font-bold mt-2 bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors w-fit">
                                                <Video size={16} className="fill-current" />
                                                <span className="uppercase tracking-widest text-[10px]">Unirse a sesión</span>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
            </div>
            </div>
        </div>
    );
}

function nextSlot(startTime: string) {
    const [hours, minutes] = startTime.split(':').map(Number);
    const date = new Date();
    date.setHours(hours);
    date.setMinutes(minutes + 90);
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
}

function buildDate(dayIndex: number, time: string) {
    const [hours, minutes] = time.split(':').map(Number);
    const now = new Date();
    const monday = new Date(now);
    const currentDay = now.getDay() === 0 ? 6 : now.getDay() - 1;
    const diff = dayIndex - currentDay;
    monday.setDate(now.getDate() + diff);
    monday.setHours(hours, minutes, 0, 0);
    return monday;
}

function formatDate(date: Date) {
    return `${date.getUTCFullYear()}${(date.getUTCMonth() + 1).toString().padStart(2, '0')}${date.getUTCDate().toString().padStart(2, '0')}T${date.getUTCHours().toString().padStart(2, '0')}${date.getUTCMinutes().toString().padStart(2, '0')}00`;
}

