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
        { href: "https://facebook.com/comunidadfaro", label: "Facebook", icon: "public" },
        { href: "https://instagram.com/comunidadfaro", label: "Instagram", icon: "photo_camera" },
        { href: "https://youtube.com/comunidadfaro", label: "YouTube", icon: "smart_display" },
    ];

    return (
        <footer
            className="w-full"
            style={{
                background: "var(--faro-surface-container-lowest)",
                borderTop: "1px solid var(--faro-outline-variant)",
            }}
        >
            {/* Main footer */}
            <div className="px-3 md:px-6 lg:px-8 xl:px-12 py-3">
                <div className="w-full">
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-3 mb-3">
                        {/* Brand column */}
                        <div className="md:col-span-4 space-y-3">
                            <div className="flex items-center gap-3">
                                <div
                                    className="w-10 h-10 rounded-full flex items-center justify-center"
                                    style={{
                                        background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    }}
                                >
                                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" className="w-5 h-5">
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="white" />
                                    </svg>
                                </div>
                                <div>
                                    <div
                                        className="text-lg font-bold tracking-tight"
                                        style={{ color: "var(--faro-on-surface)" }}
                                    >
                                        FARO
                                    </div>
                                    <div
                                        className="text-[10px] uppercase tracking-wide"
                                        style={{ color: "var(--faro-on-surface-variant)" }}
                                    >
                                        Comunidad de Fe
                                    </div>
                                </div>
                            </div>
                            <p
                                className="text-sm leading-relaxed max-w-sm"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Iluminando el camino hacia una conexión profunda con lo divino
                                a través de la comunidad y la guía espiritual.
                            </p>
                            <div className="flex gap-2">
                                {socialLinks.map(({ href, label, icon }) => (
                                    <a
                                        key={label}
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="w-9 h-9 rounded-full flex items-center justify-center transition-all hover:scale-110"
                                        style={{
                                            background: "var(--faro-surface-container)",
                                            color: "var(--faro-on-surface-variant)",
                                        }}
                                        title={label}
                                    >
                                        <span className="material-symbols-outlined text-lg">{icon}</span>
                                    </a>
                                ))}
                            </div>
                        </div>

                        {/* Navegación */}
                        <div className="md:col-span-3">
                            <h4
                                className="text-[10px] font-bold uppercase tracking-widest mb-4"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Navegación
                            </h4>
                            <ul className="space-y-2">
                                {navLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link
                                            href={href}
                                            className="text-sm transition-colors duration-200"
                                            style={{
                                                color: "var(--faro-on-surface-variant)",
                                            }}
                                            onMouseEnter={(e) =>
                                                (e.currentTarget.style.color = "var(--faro-primary)")
                                            }
                                            onMouseLeave={(e) =>
                                                (e.currentTarget.style.color = "var(--faro-on-surface-variant)")
                                            }
                                        >
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Recursos */}
                        <div className="md:col-span-3">
                            <h4
                                className="text-[10px] font-bold uppercase tracking-widest mb-4"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Recursos
                            </h4>
                            <ul className="space-y-2">
                                {resourceLinks.map(({ href, label }) => (
                                    <li key={href}>
                                        <Link
                                            href={href}
                                            className="text-sm transition-colors duration-200"
                                            style={{
                                                color: "var(--faro-on-surface-variant)",
                                            }}
                                            onMouseEnter={(e) =>
                                                (e.currentTarget.style.color = "var(--faro-primary)")
                                            }
                                            onMouseLeave={(e) =>
                                                (e.currentTarget.style.color = "var(--faro-on-surface-variant)")
                                            }
                                        >
                                            {label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>

                        {/* Newsletter mini */}
                        <div className="md:col-span-2">
                            <h4
                                className="text-[10px] font-bold uppercase tracking-widest mb-4"
                                style={{ color: "var(--faro-primary)" }}
                            >
                                Mantente conectado
                            </h4>
                            <p
                                className="text-xs mb-3 leading-relaxed"
                                style={{ color: "var(--faro-on-surface-variant)" }}
                            >
                                Recibe meditaciones y novedades semanales.
                            </p>
                            <Link
                                href="/boletin"
                                className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wide transition-all hover:scale-105"
                                style={{
                                    background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                    color: "var(--faro-on-primary)",
                                    boxShadow: "0 4px 16px rgba(44, 96, 157, 0.3)",
                                }}
                            >
                                Suscríbete
                            </Link>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom bar */}
            <div
                className="px-3 md:px-6 lg:px-8 xl:px-12 py-2 border-t"
                style={{ borderColor: "var(--faro-outline-variant)" }}
            >
                <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
                    <p
                        className="text-xs"
                        style={{ color: "var(--faro-on-surface-variant)" }}
                    >
                        © {new Date().getFullYear()} FARO — La Luz que Guía tu Vida. Todos los derechos reservados.
                    </p>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/privacidad"
                            className="text-xs transition-colors hover:underline"
                            style={{
                                color: "var(--faro-on-surface-variant)",
                            }}
                            onMouseEnter={(e) =>
                                (e.currentTarget.style.color = "var(--faro-primary)")
                            }
                            onMouseLeave={(e) =>
                                (e.currentTarget.style.color = "var(--faro-on-surface-variant)")
                            }
                        >
                            Política de Privacidad
                        </Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
