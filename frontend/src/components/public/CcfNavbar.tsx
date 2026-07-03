"use client";


import { getCmsPublicMenu } from "@/lib/cms/v2";
import { SITE_KEY, SITE_NAME } from "@/lib/site-config";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { MapPin,Menu,Sun,X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect,useState } from "react";
import { useCcfTheme } from "./CcfThemeProvider";
import { useSiteBranding } from "@/lib/site-branding";

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

export default function CcfNavbar() {
    const { toggle, themeTokens } = useCcfTheme();
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [menuItemsV2, setMenuItemsV2] = useState<Array<{ id?: string; href: string; label: string; children?: Array<{ id?: string; href: string; label: string }> }>>([]);

    const ctaLabel = themeTokens["--site-header-cta-label"] || "Quiero conocer a Jesús";
    const ctaHref = themeTokens["--site-header-cta-href"] || "/conocer-a-jesus";

    const locationTitle = "Nuestras Sedes";
    const themeToggleTitle = "Cambiar tema";
    const fallbackLinks = DEFAULT_NAV_LINKS.map((item: any, index: number) => ({
        id: `fallback_${index}`,
        href: item.href,
        label: item.label,
        children: [],
    }));
    const _ensurePastores = (links: Array<{ id?: string; href: string; label: string; children?: any[] }>) => {
        const hasPastores = links.some(l => l.href === '/pastores');
        if (!hasPastores) {
            return [...links, { id: 'pastores', href: '/pastores', label: 'Pastores', children: [] }];
        }
        return links;
    };
    const navLinks = _ensurePastores(menuItemsV2.length > 0 ? menuItemsV2 : fallbackLinks);

    useEffect(() => {
        let mounted = true;
        const loadMenu = async () => {
            try {
                const data = await getCmsPublicMenu(SITE_KEY, "main");
                const all = (data?.items || [])
                    .filter((item) => item.visibility !== "hidden")
                    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));

                const mapByParent = new Map<string | null, typeof all>();
                all.forEach((item) => {
                    const key = item.parent_id ?? null;
                    const current = mapByParent.get(key) || [];
                    current.push(item);
                    mapByParent.set(key, current);
                });

                const roots = mapByParent.get(null) || [];
                const next = roots.map((item) => {
                    const children = (mapByParent.get(item.id.toString()) || []).map((child) => ({
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
                className="fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300"
                style={{
                    background: scrolled ? "var(--site-navbar-bg-scrolled)" : "var(--site-navbar-bg)",
                    backdropFilter: "blur(20px)",
                    borderBottom: scrolled ? "1px solid var(--site-navbar-border)" : "none",
                }}
            >
                <nav className="ccf-container max-w-[1400px] h-[88px] md:h-[96px] flex items-center justify-between gap-4">
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3.5 shrink-0">
                        {logoUrl ? (
                            <OptimizedImage src={logoUrl} alt={logoName} width={40} height={40} className="h-10 object-contain" />
                        ) : (
                            <div className="w-10 h-10 relative">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-site-primary">
                                    <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                    <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                </svg>
                            </div>
                        )}
                        {logoName && (
                            <span
                                className="font-black text-xl md:text-2xl tracking-tight"
                                style={{ color: "var(--site-on-background)" }}
                            >
                                {logoName}
                            </span>
                        )}
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden lg:flex items-center gap-1.5 flex-1 justify-center">
                        {navLinks.map(({ href, label, children }: any) => {
                            const active = pathname === href || (href !== "/" && pathname?.startsWith(href)) || (children || []).some((child: any) => pathname === child.href || pathname?.startsWith(child.href));
                            return (
                                <div key={href} className="relative group">
                                <Link
                                    key={href}
                                    href={href}
                                    className="relative px-5 py-2.5 text-[14px] font-semibold uppercase tracking-wide transition-colors duration-200 rounded-xl"
                                    style={{
                                        color: active
                                            ? "var(--site-primary)"
                                            : "var(--site-on-surface-variant)",
                                    }}
                                    onMouseEnter={(e) => (e.currentTarget.style.color = "var(--site-on-background)")}
                                    onMouseLeave={(e) => (e.currentTarget.style.color = active ? "var(--site-primary)" : "var(--site-on-surface-variant)")}
                                >
                                    {label}
                                    {(children || []).length > 0 && <span className="ml-1.5 text-[11px]">▾</span>}
                                    {active && (
                                        <span
                                            className="absolute bottom-1 left-1/2 -translate-x-1/2 w-5 h-0.5 rounded-full"
                                            style={{ background: "var(--site-primary)" }}
                                        />
                                    )}
                                </Link>
                                {(children || []).length > 0 && (
                                    <div className="absolute left-0 top-full mt-2 hidden group-hover:block min-w-[240px] rounded-2xl backdrop-blur-xl shadow-2xl p-2.5"
                                        style={{
                                            background: "var(--site-dropdown-bg)",
                                            border: "1px solid var(--site-dropdown-border)",
                                        }}>
                                        {(children || []).map((child: any) => (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                className="block rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-wider hover:bg-white/10"
                                                style={{ color: "var(--site-on-background)" }}
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
                            className="hidden md:flex items-center justify-center w-10 h-10 rounded-full transition-colors"
                            style={{ color: "var(--site-on-surface-variant)" }}
                            title={locationTitle}
                        >
                            <MapPin size={20} />
                        </Link>

                        {/* Theme Toggle */}
                        <button
                            onClick={toggle}
                            className="flex items-center justify-center w-10 h-10 rounded-full transition-all"
                            style={{
                                color: "var(--site-on-surface-variant)",
                                background: "var(--site-surface-container)",
                            }}
                            title={themeToggleTitle}
                        >
                            <Sun size={18} />
                        </button>

                        {/* CTA Principal */}
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                onClick={() => setMobileOpen && setMobileOpen(false)}
                                className="hidden lg:flex ccf-button"
                                style={{
                                    background: "var(--site-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--site-cta-shadow)",
                                }}
                            >
                                {ctaLabel}
                            </Link>
                        )}

                        {/* Mobile Menu Toggle */}
                        <button
                            onClick={() => setMobileOpen(!mobileOpen)}
                            className="lg:hidden flex items-center justify-center w-10 h-10"
                            style={{ color: "var(--site-on-background)" }}
                        >
                            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>
                </nav>
            </header>

            {/* Mobile Menu Drawer */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-40 lg:hidden flex flex-col pt-[88px]"
                    style={{
                        background: "var(--site-background)",
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
                                    style={{ color: pathname === href ? "var(--site-primary)" : "var(--site-on-background)" }}
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
                                                style={{ color: "var(--site-on-surface-variant)" }}
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
                                    background: "var(--site-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--site-cta-shadow)",
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

export const FaroNavbar = CcfNavbar;
