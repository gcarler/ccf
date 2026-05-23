"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, Sparkles, ShieldCheck, Users, PlayCircle, GraduationCap, MapPinned } from "lucide-react";

type AuthMode = "login" | "register";

interface AuthShowcasePanelProps {
    mode?: AuthMode;
    className?: string;
}

const showcaseCopy: Record<AuthMode, {
    eyebrow: string;
    title: string;
    description: string;
    cta: { label: string; href: string };
    stats: { label: string; value: string; trend: string }[];
    milestones: { title: string; description: string }[];
    testimonials: { name: string; role: string; quote: string }[];
}> = {
    login: {
        eyebrow: "Ecosistema vivo",
        title: "Todo tu discipulado en un solo tablero.",
        description: "Automatizamos formación, grupos y seguimiento pastoral para que te enfoques en crecer.",
        cta: { label: "Explorar recorrido", href: "/onboarding" },
        stats: [
            { label: "Comunidades activas", value: "48", trend: "+5 este mes" },
            { label: "Procesos guiados", value: "1.2K", trend: "98% completados" }
        ],
        milestones: [
            { title: "Semana 1", description: "Fundamentos y bienvenida a tu campus." },
            { title: "Semana 4", description: "Mentor asignado y plan de servicio personalizado." },
            { title: "Semana 8", description: "Revisión de avance con tu líder y siguiente módulo." }
        ],
        testimonials: [
            { name: "Laura", role: "Mentora juvenil", quote: "Dirigir acompañamientos es más sencillo, todo queda registrado." },
            { name: "Daniel", role: "Equipo media", quote: "Las notificaciones inteligentes nos recuerdan a quién cuidar cada semana." },
            { name: "Pr. Ramiro", role: "Pastor campus sur", quote: "Ahora tenemos visibilidad total del crecimiento espiritual." }
        ]
    },
    register: {
        eyebrow: "Ingreso guiado",
        title: "Activa tu identidad digital congregacional.",
        description: "Recibe mentor, recursos premium y retos adaptados a tu temporada espiritual.",
        cta: { label: "Ver plan de bienvenida", href: "/onboarding" },
        stats: [
            { label: "Mentores disponibles", value: "126", trend: "24/7" },
            { label: "Rutas activas", value: "312", trend: "18 países" }
        ],
        milestones: [
            { title: "Paso 1", description: "Completa tu perfil y selecciona intereses." },
            { title: "Paso 2", description: "Conéctate a grupos presenciales o digitales." },
            { title: "Paso 3", description: "Recibe tu plan de formación personalizado." }
        ],
        testimonials: [
            { name: "Andrea", role: "Nueva voluntaria", quote: "Terminé onboarding en 10 minutos y ya sirvo en producción." },
            { name: "Julián", role: "Músico", quote: "La ruta musical me mostró talleres y ensayos cercanos." },
            { name: "Esteban", role: "Campus Kids", quote: "Finalmente tengo todo mi entrenamiento en el teléfono." }
        ]
    }
};

export function AuthShowcasePanel({ mode = "login", className }: AuthShowcasePanelProps) {
    const copy = showcaseCopy[mode];
    const [activeMilestone, setActiveMilestone] = useState(0);
    const [testimonialIndex, setTestimonialIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setTestimonialIndex(prev => (prev + 1) % copy.testimonials.length);
        }, 6000);
        return () => clearInterval(interval);
    }, [copy.testimonials.length]);

    const testimonial = useMemo(() => copy.testimonials[testimonialIndex], [copy, testimonialIndex]);

    return (
        <section
            className={`rounded-lg border border-white/10 bg-white/10 dark:bg-white/5 backdrop-blur-3xl shadow-[0_25px_100px_rgba(15,23,42,0.55)] text-white p-4 relative overflow-hidden ${className ?? ""}`}
        >
            <div className="absolute inset-0 pointer-events-none">
                <div className="absolute -top-16 right-[-40px] w-64 h-48 bg-primary/40 blur-[150px]"></div>
                <div className="absolute bottom-0 left-[-60px] w-72 h-48 bg-blue-500/30 blur-[180px]"></div>
                <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-[0.08]"></div>
            </div>

            <div className="relative space-y-3">
                <div>
                    <p className="text-slate-300 text-[11px] font-semibold uppercase tracking-[0.35em] mb-3 flex items-center gap-2">
                        <Sparkles className="w-4 h-4" /> {copy.eyebrow}
                    </p>
                    <h2 className="text-xl font-black leading-tight tracking-tight text-white mb-2">{copy.title}</h2>
                    <p className="text-slate-200 text-sm max-w-md">{copy.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    {copy.stats.map((stat) => (
                        <div key={stat.label} className="rounded-lg bg-white/5 border border-white/10 p-4">
                            <p className="text-xs uppercase tracking-wide text-slate-400 mb-1">{stat.label}</p>
                            <p className="text-lg font-black text-white">{stat.value}</p>
                            <p className="text-[11px] text-emerald-300 font-semibold mt-1">{stat.trend}</p>
                        </div>
                    ))}
                </div>

                <div className="rounded-lg border border-white/10 bg-slate-900/40 p-3 space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Ruta guiada</p>
                            <p className="text-white font-semibold">{copy.milestones[activeMilestone].title}</p>
                        </div>
                        <div className="flex items-center gap-2">
                            {copy.milestones.map((_, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => setActiveMilestone(idx)}
                                    className={`h-2 rounded-full transition-all ${
                                        idx === activeMilestone ? "w-8 bg-primary" : "w-2 bg-white/30"
                                    }`}
                                    aria-label={`Paso ${idx + 1}`}
                                />
                            ))}
                        </div>
                    </div>
                    <p className="text-slate-200 text-sm leading-relaxed">
                        {copy.milestones[activeMilestone].description}
                    </p>
                    <div className="flex items-center gap-3 text-xs uppercase tracking-wide text-slate-400">
                        <Activity className="w-4 h-4" /> Avance en vivo
                    </div>
                </div>

                <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-3">
                    <div className="flex items-center gap-3">
                        <ShieldCheck className="w-5 h-5 text-emerald-300" />
                        <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Testimonio real</p>
                    </div>
                    <p className="text-lg font-semibold leading-snug text-white">&ldquo;{testimonial.quote}&rdquo;</p>
                    <p className="text-sm text-slate-300">
                        {testimonial.name} · {testimonial.role}
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-200">
                        <Users className="w-4 h-4" /> Mentores 24/7
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-200">
                        <GraduationCap className="w-4 h-4" /> Academias premium
                    </div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-200">
                        <MapPinned className="w-4 h-4" /> Campus global
                    </div>
                </div>

                <div className="flex flex-col gap-3 rounded-lg border border-white/10 bg-slate-900/30 p-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                        <PlayCircle className="w-4 h-4" /> Demo guiada
                    </div>
                    <p className="text-sm text-slate-200 leading-relaxed">
                        Mira cómo luce una semana típica dentro de CCF Platform con recursos interactivos, recordatorios inteligentes y tableros compartidos.
                    </p>
                    <Link
                        href={copy.cta.href}
                        className="inline-flex items-center justify-center rounded-md bg-white/10 px-4 py-2 text-sm font-semibold text-white transition hover:bg-white/20"
                    >
                        {copy.cta.label}
                    </Link>
                </div>
            </div>
        </section>
    );
}

export default AuthShowcasePanel;
