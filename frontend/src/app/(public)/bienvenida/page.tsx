import Link from "next/link";
import { ArrowRight, BookOpen, HeartHandshake, Sparkles } from "lucide-react";

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

export default async function WelcomePage({
    searchParams,
}: {
    searchParams?: Promise<{ name?: string; reason?: string }>;
}) {
    const params = searchParams ? await searchParams : undefined;
    const name = typeof params?.name === "string" && params.name.trim() ? params.name.trim() : "amigo";

    return (
        <main className="min-h-screen pt-[96px] pb-8 px-3 md:px-6 lg:px-8 xl:px-12" style={{ background: "var(--faro-background)" }}>
            <section className="mx-auto max-w-6xl rounded-[24px] border border-[color:var(--faro-outline-variant)] overflow-hidden">
                <div className="grid lg:grid-cols-[1.15fr_0.85fr]">
                    <div className="p-6 md:p-10 lg:p-12" style={{ background: "linear-gradient(135deg, var(--faro-surface-container-lowest), var(--faro-surface-container-low))" }}>
                        <div className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-xs font-bold uppercase tracking-wide mb-4" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
                            <Sparkles size={14} />
                            Bienvenida
                        </div>
                        <h1 className="text-2xl md:text-4xl font-black tracking-tight mb-4" style={{ color: "var(--faro-on-background)" }}>
                            Hola, {name}.
                        </h1>
                        <p className="text-lg md:text-xl leading-relaxed max-w-2xl mb-6" style={{ color: "var(--faro-on-surface-variant)" }}>
                            No encontramos una cuenta registrada todavía, pero no te dejamos en una pantalla vacía.
                            Puedes empezar por la ruta pública de fe y crecimiento que preparamos para ti.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-3">
                            <Link
                                href="/cursos"
                                className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wide"
                                style={{ background: "var(--faro-primary)", color: "var(--faro-on-primary)" }}
                            >
                                Discipulado Básico
                                <ArrowRight size={16} />
                            </Link>
                            <Link
                                href="/conocer-a-jesus"
                                className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-bold uppercase tracking-wide border"
                                style={{ borderColor: "var(--faro-outline-variant)", color: "var(--faro-on-surface)" }}
                            >
                                Una nueva vida con Cristo
                                <ArrowRight size={16} />
                            </Link>
                        </div>
                    </div>

                    <div className="p-6 md:p-10 lg:p-12 border-t lg:border-t-0 lg:border-l" style={{ background: "var(--faro-surface-container)" , borderColor: "var(--faro-outline-variant)" }}>
                        <div className="space-y-4">
                            {HIGHLIGHTS.map(({ title, description, href, cta, icon: Icon }) => (
                                <Link
                                    key={title}
                                    href={href}
                                    className="block rounded-[18px] border p-4 transition-transform hover:-translate-y-0.5"
                                    style={{ borderColor: "var(--faro-outline-variant)", background: "var(--faro-surface)" }}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className="mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl" style={{ background: "var(--faro-primary-container)", color: "var(--faro-primary)" }}>
                                            <Icon size={18} />
                                        </div>
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-black" style={{ color: "var(--faro-on-surface)" }}>{title}</p>
                                            <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--faro-on-surface-variant)" }}>
                                                {description}
                                            </p>
                                            <span className="mt-3 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide" style={{ color: "var(--faro-primary)" }}>
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
    );
}
