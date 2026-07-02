"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, BookOpen, HeartHandshake, Sparkles } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import CmsPageOverride from "@/components/public/cms/CmsPageOverride";


const HIGHLIGHTS = [
    {
        title: "Discipulado Básico",
        description: "Empieza por la ruta de fundamentos para crecer con orden y acompañamiento.",
        href: "/cursos",
        cta: "Ver academia",
        icon: BookOpen,
    },
    {
        title: "Una nueva vida con Cristo",
        description: "Conoce el mensaje central del evangelio en una ruta pública y clara.",
        href: "/conocer-a-jesus",
        cta: "Abrir ruta",
        icon: HeartHandshake,
    },
] as const;

const ICONS = {
    book: BookOpen,
    heart: HeartHandshake,
};

export default function WelcomePage() {
    const [name, setName] = useState("amigo");
    const welcomePage = useCmsV2Page('welcome');
    const welcomeContent = welcomePage?.blocks?.welcome;
    const content = (welcomeContent?.parsed && typeof welcomeContent.parsed === "object" && !Array.isArray(welcomeContent.parsed))
        ? welcomeContent.parsed as Record<string, unknown>
        : {};
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const nameParam = params.get("name");
        if (typeof nameParam === "string" && nameParam.trim()) {
            setName(nameParam.trim());
        }
    }, []);

    const titleTemplate = typeof content.title_template === "string" ? content.title_template : "Hola, {name}.";
    const description = typeof content.description === "string"
        ? content.description
        : "No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía. Puedes empezar por la ruta pública de fe y crecimiento que preparamos para ti.";
    const primaryCta = content.primary_cta && typeof content.primary_cta === "object" ? content.primary_cta as Record<string, unknown> : {};
    const secondaryCta = content.secondary_cta && typeof content.secondary_cta === "object" ? content.secondary_cta as Record<string, unknown> : {};
    const highlights = Array.isArray(content.highlights) && content.highlights.length > 0
        ? content.highlights.map((item) => item && typeof item === "object" ? item as Record<string, unknown> : {}).map((item) => ({
            title: typeof item.title === "string" ? item.title : "",
            description: typeof item.description === "string" ? item.description : "",
            href: typeof item.href === "string" ? item.href : "/",
            cta: typeof item.cta === "string" ? item.cta : "Abrir",
            icon: ICONS[(typeof item.icon === "string" ? item.icon : "book") as keyof typeof ICONS] || BookOpen,
        })).filter((item) => item.title && item.description)
        : [...HIGHLIGHTS];

    return (
        <CmsPageOverride slug="bienvenida">
            <main className="min-h-screen pt-[96px] pb-8 px-3 md:px-6 lg:px-8 xl:px-12" style={{ background: "var(--site-background)" }}>
            <section className="mx-auto max-w-6xl rounded-[24px] border border-[color:var(--site-outline-variant)] overflow-hidden">
                <div className="grid lg:grid-cols-[1.15fr_0.85fr]">
                    <div className="p-6 md:p-10 lg:p-12" style={{ background: "linear-gradient(135deg, var(--site-surface-container-lowest), var(--site-surface-container-low))" }}>
                        <div className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wide mb-4" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                            <Sparkles size={14} />
                            {typeof content.eyebrow === "string" ? content.eyebrow : "Bienvenida"}
                        </div>
                        <h1 className="text-2xl md:text-4xl font-black tracking-tight mb-4" style={{ color: "var(--site-on-background)" }}>
                            {titleTemplate.replace("{name}", name)}
                        </h1>
                        <p className="text-lg md:text-xl leading-relaxed max-w-2xl mb-6" style={{ color: "var(--site-on-surface-variant)" }}>
                            {description}
                        </p>
                        <div className="flex flex-col sm:flex-row gap-3">
                            <Link
                                href={typeof primaryCta.href === "string" ? primaryCta.href : "/cursos"}
                                className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wide"
                                style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}
                            >
                                {typeof primaryCta.label === "string" ? primaryCta.label : "Discipulado Básico"}
                                <ArrowRight size={16} />
                            </Link>
                            <Link
                                href={typeof secondaryCta.href === "string" ? secondaryCta.href : "/conocer-a-jesus"}
                                className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wide border"
                                style={{ borderColor: "var(--site-outline-variant)", color: "var(--site-on-surface)" }}
                            >
                                {typeof secondaryCta.label === "string" ? secondaryCta.label : "Una nueva vida con Cristo"}
                                <ArrowRight size={16} />
                            </Link>
                        </div>
                    </div>

                    <div className="p-6 md:p-10 lg:p-12 border-t lg:border-t-0 lg:border-l" style={{ background: "var(--site-surface-container)" , borderColor: "var(--site-outline-variant)" }}>
                        <div className="space-y-4">
                            {highlights.map(({ title, description, href, cta, icon: Icon }) => (
                                <Link
                                    key={title}
                                    href={href}
                                    className="block rounded-[18px] border p-4 transition-transform hover:-translate-y-0.5"
                                    style={{ borderColor: "var(--site-outline-variant)", background: "var(--site-surface)" }}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                                            <Icon size={18} />
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-black" style={{ color: "var(--site-on-surface)" }}>{title}</p>
                                            <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--site-on-surface-variant)" }}>
                                                {description}
                                            </p>
                                            <span className="mt-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>
                                                {cta}
                                                <ArrowRight size={14} />
                                            </span>
                                        </div>
                                    </div>
                                </Link>
                            ))}
                        </div>
                    </div>
                </div>
            </section>
            </main>
        </CmsPageOverride>
    );
}
