"use client";

import { useContentBlock } from "@/hooks/useContent";
import { getCmsPublicMenu } from "@/lib/cms/v2";
import { MapPin,Menu,Sun,X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect,useState } from "react";
import { useFaroTheme } from "./FaroThemeProvider";

const DEFAULT_NAV_LINKS = [
    { href: "/", label: "Inicio" },
    { href: "/nosotros", label: "Sobre Nosotros" },
    { href: "/pastores", label: "Pastores" },
    { href: "/testimonios", label: "Testimonios" },
    { href: "/eventos", label: "Eventos" },
    { href: "/predicas", label: "Prédicas" },
    { href: "/cursos", label: "Cursos" },
    { href: "/sedes", label: "Sedes" },
];

export default function FaroNavbar() {
    const { toggle, themeTokens } = useFaroTheme();
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [menuItemsV2, setMenuItemsV2] = useState<Array<{ id?: number; href: string; label: string; children?: Array<{ id?: number; href: string; label: string }> }>>([]);

    const logoUrl = themeTokens["--faro-logo-url"] || "";
    const logoName = themeTokens["--faro-logo-name"] || "FARO";
    const ctaLabel = themeTokens["--faro-header-cta-label"] || "Quiero conocer a Jesús";
    const ctaHref = themeTokens["--faro-header-cta-href"] || "/conocer-a-jesus";

    // Dinamización vía CMS
    const { data: navContent } = useContentBlock("faro_nav_items");
    const fallbackLinks = (Array.isArray(navContent?.items) ? navContent.items : DEFAULT_NAV_LINKS).map((item: any, index: number) => ({
        id: index,
        href: item.href,
        label: item.label,
        children: [],
    }));
    // Ensure /pastores is always in the nav, deduped by href
    const _ensurePastores = (links: Array<{ href: string; label: string; children?: any[] }>) => {
        const hasPastores = links.some(l => l.href === '/pastores');
        if (!hasPastores) {
            return [...links, { href: '/pastores', label: 'Pastores', children: [] }];
        }
        return links;
    };
    const navLinks = _ensurePastores(menuItemsV2.length > 0 ? menuItemsV2 : fallbackLinks);

    useEffect(() => {
        let mounted = true;
        const loadMenu = async () => {
            try {
                const data = await getCmsPublicMenu("faro", "main");
                const all = (data?.items || [])
                    .filter((item) => item.visibility !== "hidden")
                    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

                const mapByParent = new Map<number | null, typeof all>();
                all.forEach((item) => {
                    const key = item.parent_id ?? null;
                    const current = mapByParent.get(key) || [];
                    current.push(item);
                    mapByParent.set(key, current);
                });

                const roots = mapByParent.get(null) || [];
                const next = roots.map((item) => {
                    const children = (mapByParent.get(item.id) || []).map((child) => ({
                        id: child.id,
                        href: child.href,
                        label: child.label,
                    }));
                    return { id: item.id, href: item.href, label: item.label, children };
                });
                if (mounted && next.length > 0) {
                    setMenuItemsV2(next);
                }
            } catch {
                // Fallback automatico al bloque de contenido
            }
        };
        loadMenu();
        return () => {
            mounted = false;
        };
    }, []);

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
                    background: scrolled ? "var(--faro-navbar-bg-scrolled)" : "var(--faro-navbar-bg)",
                    backdropFilter: "blur(20px)",
                    borderBottom: scrolled ? "1px solid var(--faro-navbar-border)" : "none",
                }}
            >
                <nav className="max-w-[1400px] mx-auto px-3 md:px-4 h-[72px] flex items-center justify-between gap-3">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3 shrink-0">
                        {logoUrl ? (
                            <img src={logoUrl} alt={logoName} className="h-8 object-contain" />
                        ) : (
                            <div className="w-8 h-8 relative">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-faro-primary">
                                    <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                    <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                </svg>
                            </div>
                        )}
                        {logoName && (
                            <span
                                className="font-black text-xl tracking-tight"
                                style={{ color: "var(--faro-on-background)" }}
                            >
                                {logoName}
                            </span>
                        )}
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden lg:flex items-center gap-1 flex-1 justify-center">
                        {navLinks.map(({ href, label, children }: any) => {
                            const active = pathname === href || (href !== "/" && pathname?.startsWith(href)) || (children || []).some((child: any) => pathname === child.href || pathname?.startsWith(child.href));
                            return (
                                <div key={href} className="relative group">
                                <Link
                                    key={href}
                                    href={href}
                                    className="relative px-4 py-2 text-[13px] font-semibold uppercase tracking-wide transition-colors duration-200 rounded-lg"
                                    style={{
                                        color: active
                                            ? "var(--faro-primary)"
                                            : "var(--faro-on-surface-variant)",
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--faro-on-background)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.color = active ? "var(--faro-primary)" : "var(--faro-on-surface-variant)")}
                                >
                                    {label}
                                    {(children || []).length > 0 && <span className="ml-1 text-[10px]">▾</span>}
                                    {active && (
                                        <span
                                            className="absolute bottom-0 left-1/2 -translate-x-1/2 w-4 h-0.5 rounded-full"
                                            style={{ background: "var(--faro-primary)" }}
                                        />
                                    )}
                                </Link>
                                {(children || []).length > 0 && (
                                    <div className="absolute left-0 top-full mt-2 hidden group-hover:block min-w-[220px] rounded-lg backdrop-blur-xl shadow-2xl p-2"
                                        style={{
                                            background: "var(--faro-dropdown-bg)",
                                            border: "1px solid var(--faro-dropdown-border)",
                                        }}>
                                        {(children || []).map((child: any) => (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                className="block rounded-lg px-3 py-2 text-[11px] font-bold uppercase tracking-wider hover:bg-white/10"
                                                style={{ color: "var(--faro-on-background)" }}
                                            >
                                                {child.label}
                                            </Link>
                                        ))}
                                    </div>
                                )}
                                </div>
                            );
                        })}
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-3 shrink-0">
                        {/* Location */}
                        <Link
                            href="/sedes"
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
                            title="Cambiar tema"
                        >
                            <Sun size={16} />
                        </button>

                        {/* CTA Principal */}
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                onClick={() => setMobileOpen && setMobileOpen(false)}
                                className="hidden lg:flex items-center gap-2 px-3 py-2.5 rounded-full text-[11px] font-bold uppercase tracking-wider transition-all hover:scale-105"
                                style={{
                                    background: "var(--faro-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--faro-cta-shadow)",
                                }}
                            >
                                {ctaLabel}
                            </Link>
                        )}

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
                    <div className="flex flex-col items-center justify-center flex-1 gap-3 p-4">
                        {navLinks.map(({ href, label, children }: any) => (
                            <div key={href} className="text-center space-y-2">
                                <Link
                                    href={href}
                                    onClick={() => setMobileOpen(false)}
                                    className="text-xl font-bold uppercase tracking-wide transition-colors"
                                    style={{ color: pathname === href ? "var(--faro-primary)" : "var(--faro-on-background)" }}
                                >
                                    {label}
                                </Link>
                                {(children || []).length > 0 && (
                                    <div className="space-y-2">
                                        {(children || []).map((child: any) => (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                onClick={() => setMobileOpen(false)}
                                                className="block text-sm font-bold uppercase tracking-wider"
                                                style={{ color: "var(--faro-on-surface-variant)" }}
                                            >
                                                {child.label}
                                            </Link>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))}
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                onClick={() => setMobileOpen && setMobileOpen(false)}
                                className="flex items-center justify-center gap-2 px-3 py-3 mt-4 w-full rounded-full text-[12px] font-bold uppercase tracking-wider transition-all hover:scale-105"
                                style={{
                                    background: "var(--faro-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--faro-cta-shadow)",
                                }}
                            >
                                {ctaLabel}
                            </Link>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}

