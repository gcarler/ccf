"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MapPin, Menu, X, ChevronRight, Sun, Moon, Zap } from "lucide-react";
import { useFaroTheme } from "./FaroThemeProvider";
import { useContentBlock } from "@/hooks/useContent";

const DEFAULT_NAV_LINKS = [
    { href: "/faro", label: "Inicio" },
    { href: "/faro/nosotros", label: "Sobre Nosotros" },
    { href: "/faro/testimonios", label: "Testimonios" },
    { href: "/faro/eventos", label: "Eventos" },
    { href: "/faro/predicas", label: "Prédicas" },
    { href: "/faro/cursos", label: "Cursos" },
    { href: "/faro/sedes", label: "Sedes" },
];

export default function FaroNavbar() {
    const { theme, toggle } = useFaroTheme();
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);

    // Dinamización vía CMS
    const { data: navContent } = useContentBlock("faro_nav_items");
    const navLinks = Array.isArray(navContent?.items) ? navContent.items : DEFAULT_NAV_LINKS;

    useEffect(() => {
        const handler = () => setScrolled(window.scrollY > 20);
        window.addEventListener("scroll", handler);
        return () => window.removeEventListener("scroll", handler);
    }, []);

    return (
        <>
            <header
                className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
                style={{
                    background: scrolled
                        ? theme === "dark"
                            ? "rgba(0, 13, 42, 0.92)"
                            : "rgba(248, 249, 255, 0.92)"
                        : "rgba(0, 13, 42, 0.6)",
                    backdropFilter: "blur(20px)",
                    borderBottom: scrolled ? "1px solid rgba(165, 200, 255, 0.08)" : "none",
                }}
            >
                <nav className="max-w-[1400px] mx-auto px-6 md:px-10 h-[72px] flex items-center justify-between gap-8">
                    {/* Logo */}
                    <Link href="/faro" className="flex items-center gap-3 shrink-0">
                        <div className="w-8 h-8 relative">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-faro-primary">
                                <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                            </svg>
                        </div>
                        <span
                            className="font-black text-xl tracking-tight"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            FARO
                        </span>
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden lg:flex items-center gap-1 flex-1 justify-center">
                        {navLinks.map(({ href, label }: any) => {
                            const active = pathname === href || (href !== "/faro" && pathname?.startsWith(href));
                            return (
                                <Link
                                    key={href}
                                    href={href}
                                    className="relative px-4 py-2 text-[13px] font-semibold uppercase tracking-[0.1em] transition-colors duration-200 rounded-lg"
                                    style={{
                                        color: active
                                            ? "var(--faro-primary)"
                                            : "var(--faro-on-surface-variant)",
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--faro-on-background)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.color = active ? "var(--faro-primary)" : "var(--faro-on-surface-variant)")}
                                >
                                    {label}
                                    {active && (
                                        <span
                                            className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full"
                                            style={{ background: "var(--faro-primary)" }}
                                        />
                                    )}
                                </Link>
                            );
                        })}
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-3 shrink-0">
                        {/* Location */}
                        <Link
                            href="/faro/sedes"
                            className="hidden md:flex items-center justify-center w-9 h-9 rounded-full transition-colors"
                            style={{ color: "var(--faro-on-surface-variant)" }}
                            title="Nuestras Sedes"
                        >
                            <MapPin size={18} />
                        </Link>

                        {/* Theme Toggle */}
                        <button
                            onClick={toggle}
                            className="flex items-center justify-center w-9 h-9 rounded-full transition-all"
                            style={{
                                color: "var(--faro-on-surface-variant)",
                                background: "var(--faro-surface-container)",
                            }}
                            title={`Cambiar tema (Actual: ${theme})`}
                        >
                            {theme === "institutional" && <Sun size={16} className="text-blue-500" />}
                            {theme === "light" && <Moon size={16} />}
                            {theme === "dark" && <Zap size={16} className="text-amber-500" />}
                        </button>

                        {/* CTA Principal */}
                        <Link
                            href="/faro/conocer-a-jesus"
                            className="hidden md:flex items-center gap-2 px-5 py-2.5 rounded-full text-[11px] font-black uppercase tracking-[0.15em] transition-all hover:scale-105"
                            style={{
                                background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                                color: "white",
                                boxShadow: "0 4px 20px rgba(44, 96, 157, 0.35)",
                            }}
                        >
                            Quiero conocer a Jesús
                        </Link>

                        {/* Mobile Menu Toggle */}
                        <button
                            onClick={() => setMobileOpen(!mobileOpen)}
                            className="lg:hidden flex items-center justify-center w-9 h-9"
                            style={{ color: "var(--faro-on-background)" }}
                        >
                            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
                        </button>
                    </div>
                </nav>
            </header>

            {/* Mobile Menu Drawer */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-40 lg:hidden flex flex-col pt-[72px]"
                    style={{
                        background: "var(--faro-background)",
                        opacity: 0.98,
                        backdropFilter: "blur(20px)",
                    }}
                >
                    <div className="flex flex-col items-center justify-center flex-1 gap-6 p-8">
                        {navLinks.map(({ href, label }: any) => (
                            <Link
                                key={href}
                                href={href}
                                onClick={() => setMobileOpen(false)}
                                className="text-2xl font-black uppercase tracking-widest transition-colors"
                                style={{ color: pathname === href ? "var(--faro-primary)" : "var(--faro-on-background)" }}
                            >
                                {label}
                            </Link>
                        ))}
                        <Link
                            href="/faro/conocer-a-jesus"
                            onClick={() => setMobileOpen(false)}
                            className="mt-6 px-8 py-4 rounded-full text-sm font-black uppercase tracking-widest text-white"
                            style={{
                                background: "linear-gradient(135deg, var(--faro-primary), var(--faro-secondary))",
                            }}
                        >
                            Quiero conocer a Jesús
                        </Link>
                    </div>
                </div>
            )}
        </>
    );
}
