import Link from "next/link";
import React from "react";

export default function FaroFooter() {
    const navLinks = [
        { href: "/", label: "Inicio" },
        { href: "/nosotros", label: "Sobre Nosotros" },
        { href: "/pastores", label: "Pastores" },
        { href: "/eventos", label: "Eventos" },
        { href: "/predicas", label: "Prédicas" },
        { href: "/cursos", label: "Cursos" },
    ];

    const resourceLinks = [
        { href: "/conocer-a-jesus", label: "Conocer a Jesús" },
        { href: "/testimonios", label: "Testimonios" },
        { href: "/sedes", label: "Sedes" },
        { href: "/boletin", label: "Boletín" },
    ];

    const socialLinks = [
        {
            href: "https://facebook.com/comunidadfaro",
            label: "Facebook",
            svg: (
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z" />
                </svg>
            ),
        },
        {
            href: "https://instagram.com/comunidadfaro",
            label: "Instagram",
            svg: (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
                    <circle cx="12" cy="12" r="4" />
                    <circle cx="17.5" cy="6.5" r="0.5" fill="currentColor" stroke="none" />
                </svg>
            ),
        },
        {
            href: "https://youtube.com/comunidadfaro",
            label: "YouTube",
            svg: (
                <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                    <path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58 2.78 2.78 0 0 0 1.95 1.96C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.96A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z" />
                    <polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02" fill="white" />
                </svg>
            ),
        },
    ];

    return (
        <footer
            className="w-full"
            style={{
                background: "var(--faro-surface-container-lowest)",
                borderTop: "1px solid var(--faro-outline-variant)",
            }}
        >
            {/* Newsletter banner — full width */}
            <div className="px-4 md:px-6 lg:px-8 xl:px-12 pt-12 md:pt-16 pb-10">
                <div
                    className="rounded-2xl px-8 py-10 md:px-14 md:py-12 flex flex-col md:flex-row items-center justify-between gap-8"
                    style={{
                        background: "var(--faro-surface-container)",
                        border: "1px solid var(--faro-outline-variant)",
                    }}
                >
                    <div className="flex-1 text-center md:text-left">
                        <h3
                            className="text-2xl md:text-3xl font-black tracking-tight mb-3"
                            style={{ color: "var(--faro-on-surface)" }}
                        >
                            ¿Quieres recibir nuestras novedades?
                        </h3>
                        <p
                            className="text-base leading-relaxed max-w-xl"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                        >
                            Meditaciones semanales, eventos exclusivos y más.{" "}
                            <span style={{ color: "var(--faro-primary)" }}>Directo a tu correo.</span>
                        </p>
                    </div>
                    <Link
                        href="/boletin"
                        className="shrink-0 inline-flex items-center gap-2 px-8 py-3.5 rounded-full text-sm font-black uppercase tracking-wider transition-all hover:scale-105"
                        style={{
                            background: "var(--faro-cta-gradient)",
                            color: "white",
                            boxShadow: "var(--faro-cta-shadow)",
                        }}
                    >
                        Suscribirme
                    </Link>
                </div>
            </div>

            {/* Main footer */}
            <div className="px-4 md:px-6 lg:px-8 xl:px-12 pb-12 md:pb-16">
                <div className="w-full">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-12">
                        {/* Brand column */}
                        <div className="md:col-span-5 space-y-5">
                            <div className="flex items-center gap-4">
                                <div
                                    className="w-14 h-14 rounded-full flex items-center justify-center"
                                    style={{
                                        background: "var(--faro-cta-gradient)",
                                    }}
                                >
                                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" className="w-7 h-7">
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="white" />
                                    </svg>
                                </div>
                                <div>
                                    <div
                                        className="text-2xl font-bold tracking-tight"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        FARO
                                    </div>
                                    <div
                                        className="text-xs uppercase tracking-widest"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        Comunidad Cristiana El Faro
                                    </div>
                                </div>
                            </div>
                            <p
                                className="text-sm leading-relaxed max-w-sm"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Iluminando el camino hacia una conexión profunda con lo divino
                                a través de la comunidad y la guía espiritual.
                                Una casa de fe abierta para toda la familia.
                            </p>
                            <div className="flex gap-3 pt-1">
                                {socialLinks.map(({ href, label, svg }) => (
                                    <a
                                        key={label}
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="w-10 h-10 rounded-full flex items-center justify-center transition-all hover:scale-110"
                                        style={{
                                            background: "var(--faro-surface-container)",
                                            color: "var(--faro-on-surface-variant)",
                                        }}
                                        title={label}
                                    >
                                        {svg}
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* Navegación */}
                        <div className="md:col-span-3 md:col-start-7">
                            <h4
                                className="text-[10px] font-bold uppercase tracking-widest mb-6"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Navegación
                            </h4>
                            <ul className="space-y-3">
                                {navLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link
                                            href={href}
                                            className="text-sm transition-colors duration-200 hover:text-[var(--faro-primary)]"
                                            style={{ color: "var(--faro-on-surface-variant)" }}
                                        >
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Recursos */}
                        <div className="md:col-span-2">
                            <h4
                                className="text-[10px] font-bold uppercase tracking-widest mb-6"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Recursos
                            </h4>
                            <ul className="space-y-3">
                                {resourceLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link
                                            href={href}
                                            className="text-sm transition-colors duration-200 hover:text-[var(--faro-primary)]"
                                            style={{ color: "var(--faro-on-surface-variant)" }}
                                        >
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom bar */}
            <div
                className="px-4 md:px-6 lg:px-8 xl:px-12 py-5 border-t"
                style={{ borderColor: "var(--faro-outline-variant)" }}
            >
                <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
                    <p
                        className="text-xs"
                        style={{ color: "var(--faro-on-surface-variant)" }}
                    >
                        © {new Date().getFullYear()}{" "}
                        <a
                            href="https://ples.com.co"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline hover:text-[var(--faro-primary)] transition-colors"
                        >
                            PLES SAS
                        </a>
                        {" "}— El uso inteligente de la experiencia. Todos los derechos reservados.
                    </p>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/privacidad"
                            className="text-xs transition-colors hover:text-[var(--faro-primary)] hover:underline"
                            style={{
                                color: "var(--faro-on-surface-variant)",
                            }}
                        >
                            Política de Privacidad
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
