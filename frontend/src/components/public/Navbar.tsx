"use client";


import { getCmsPublicMenu } from "@/lib/cms/v2";
import { SITE_KEY, SITE_NAME } from "@/lib/site-config";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { ArrowRight, ChevronDown, MapPin, Menu, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect,useState } from "react";
import { useTheme } from "./ThemeProvider";
import { useSiteBranding } from "@/lib/site-branding";

type PublicNavItem = {
    id?: string;
    href: string;
    label: string;
    children?: PublicNavItem[];
};

export default function Navbar() {
    const { toggle, themeTokens } = useTheme();
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
    const pathname = usePathname();
    const [scrolled, setScrolled] = useState(false);
    const [mobileOpen, setMobileOpen] = useState(false);
    const [menuItemsV2, setMenuItemsV2] = useState<PublicNavItem[]>([]);

    const ctaLabel = themeTokens["--site-header-cta-label"] || "Quiero conocer a Jesús";
    const ctaHref = themeTokens["--site-header-cta-href"] || "/conocer-a-jesus";

    const locationTitle = "Nuestras Sedes";
    const themeToggleTitle = "Cambiar tema";
    const navLinks = menuItemsV2;
    const isActiveHref = (href: string) => pathname === href || (href !== "/" && Boolean(pathname?.startsWith(href)));
    const isActiveItem = (item: PublicNavItem) => isActiveHref(item.href) || Boolean(item.children?.some((child) => isActiveHref(child.href)));

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
                if (mounted) {
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

    useEffect(() => {
        if (!mobileOpen) return;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") setMobileOpen(false);
        };
        window.addEventListener("keydown", onKeyDown);
        return () => {
            document.body.style.overflow = previousOverflow;
            window.removeEventListener("keydown", onKeyDown);
        };
    }, [mobileOpen]);

    useEffect(() => {
        setMobileOpen(false);
    }, [pathname]);

    return (
        <>
            <header
                aria-hidden={mobileOpen}
                className="fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300"
                style={{
                    background: scrolled ? "var(--site-navbar-bg-scrolled)" : "var(--site-navbar-bg)",
                    backdropFilter: "blur(20px)",
                    borderBottom: scrolled ? "1px solid var(--site-navbar-border)" : "none",
                }}
            >
                <nav className="ccf-container max-w-[1400px] h-[78px] md:h-[88px] flex items-center justify-between gap-4">
                    {/* Logo */}
                    <Link href="/" className="flex min-w-0 items-center gap-3 shrink-0 rounded-full pr-2 transition-opacity hover:opacity-90">
                        {logoUrl ? (
                            <OptimizedImage src={logoUrl} alt={logoName} width={42} height={42} className="h-10 w-10 md:h-11 md:w-11 object-contain" />
                        ) : (
                            <div className="w-10 h-10 md:w-11 md:h-11 relative">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-site-primary">
                                    <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                    <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                </svg>
                            </div>
                        )}
                        {logoName && (
                            <span
                                className="max-w-[11rem] truncate font-black text-lg md:max-w-[15rem] md:text-xl tracking-tight"
                                style={{ color: "var(--site-on-background)" }}
                            >
                                {logoName}
                            </span>
                        )}
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden lg:flex min-w-0 flex-1 justify-center px-2">
                        <div
                            className="flex max-w-full items-center gap-1 rounded-full border px-2 py-1.5 shadow-sm backdrop-blur-2xl"
                            style={{
                                background: "color-mix(in srgb, var(--site-surface-container-low) 88%, transparent)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                        >
                        {navLinks.map((item) => {
                            const { href, label, children } = item;
                            const active = isActiveItem(item);
                            const hasChildren = Boolean(children?.length);
                            return (
                                <div key={href} className="relative group">
                                <Link
                                    key={href}
                                    href={href}
                                    className="relative inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-bold uppercase tracking-wide transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
                                    style={{
                                        color: active
                                            ? "var(--site-primary)"
                                            : "var(--site-on-surface-variant)",
                                        background: active ? "var(--site-primary-container)" : "transparent",
                                        boxShadow: active ? "0 12px 28px color-mix(in srgb, var(--site-primary) 18%, transparent)" : "none",
                                    }}
                                >
                                    <span className="max-w-[8.5rem] truncate">{label}</span>
                                    {hasChildren && (
                                        <ChevronDown
                                            size={14}
                                            strokeWidth={2.4}
                                            className="transition-transform duration-200 group-hover:rotate-180 group-focus-within:rotate-180"
                                            aria-hidden="true"
                                        />
                                    )}
                                </Link>
                                {hasChildren && (
                                    <div
                                        className="invisible absolute left-0 top-full z-50 mt-3 min-w-[260px] translate-y-2 rounded-[1.25rem] border p-2.5 opacity-0 shadow-2xl backdrop-blur-2xl transition-all duration-200 group-hover:visible group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:visible group-focus-within:translate-y-0 group-focus-within:opacity-100"
                                        style={{
                                            background: "var(--site-dropdown-bg)",
                                            border: "1px solid var(--site-dropdown-border)",
                                        }}
                                    >
                                        {children?.map((child) => {
                                            const childActive = isActiveHref(child.href);
                                            return (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                className="group/item flex items-center justify-between gap-4 rounded-xl px-4 py-3 text-sm font-bold transition-colors"
                                                style={{
                                                    color: childActive ? "var(--site-primary)" : "var(--site-on-background)",
                                                    background: childActive ? "var(--site-primary-container)" : "transparent",
                                                }}
                                            >
                                                <span className="truncate">{child.label}</span>
                                                <ArrowRight size={14} className="opacity-0 transition-opacity group-hover/item:opacity-100" aria-hidden="true" />
                                            </Link>
                                            );
                                        })}
                                    </div>
                                )}
                                </div>
                            );
                        })}
                        </div>
                    </div>

                    {/* Right Actions */}
                    <div className="flex items-center gap-2.5 shrink-0">
                        {/* Location */}
                        <Link
                            href="/sedes"
                            className="hidden md:flex items-center justify-center w-10 h-10 rounded-full border transition-all hover:-translate-y-0.5"
                            style={{
                                color: "var(--site-on-surface-variant)",
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                            title={locationTitle}
                            aria-label={locationTitle}
                        >
                            <MapPin size={20} />
                        </Link>

                        {/* Theme Toggle */}
                        <button
                            onClick={toggle}
                            className="flex items-center justify-center w-10 h-10 rounded-full border transition-all hover:-translate-y-0.5"
                            style={{
                                color: "var(--site-on-surface-variant)",
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                            title={themeToggleTitle}
                            aria-label={themeToggleTitle}
                        >
                            <Sun size={18} />
                        </button>

                        {/* CTA Principal */}
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                onClick={() => setMobileOpen && setMobileOpen(false)}
                                className="hidden lg:inline-flex items-center gap-2 rounded-full px-5 py-3 text-[12px] font-black uppercase tracking-wider transition-transform hover:-translate-y-0.5"
                                style={{
                                    background: "var(--site-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--site-cta-shadow)",
                                }}
                            >
                                <span className="max-w-[13rem] truncate">{ctaLabel}</span>
                                <ArrowRight size={15} aria-hidden="true" />
                            </Link>
                        )}

                        {/* Mobile Menu Toggle */}
                        <button
                            onClick={() => setMobileOpen(!mobileOpen)}
                            className="lg:hidden flex items-center justify-center w-10 h-10 rounded-full border"
                            style={{
                                color: "var(--site-on-background)",
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                            aria-expanded={mobileOpen}
                            aria-label={mobileOpen ? "Cerrar menu" : "Abrir menu"}
                        >
                            {mobileOpen ? <X size={24} /> : <Menu size={24} />}
                        </button>
                    </div>
                </nav>
            </header>

            {/* Mobile Menu Drawer */}
            {mobileOpen && (
                <div
                    className="fixed inset-0 z-[60] lg:hidden flex flex-col"
                    style={{
                        background: "var(--site-background)",
                        opacity: 0.98,
                        backdropFilter: "blur(20px)",
                    }}
                >
                    <div className="flex h-[78px] items-center justify-between px-5">
                        <Link href="/" className="flex min-w-0 items-center gap-3" onClick={() => setMobileOpen(false)}>
                            {logoUrl ? (
                                <OptimizedImage src={logoUrl} alt={logoName} width={40} height={40} className="h-10 w-10 object-contain" />
                            ) : (
                                <div className="h-10 w-10 text-site-primary">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-full w-full">
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                    </svg>
                                </div>
                            )}
                            <span className="truncate text-lg font-black" style={{ color: "var(--site-on-background)" }}>{logoName}</span>
                        </Link>
                        <button
                            onClick={() => setMobileOpen(false)}
                            className="flex h-10 w-10 items-center justify-center rounded-full border"
                            style={{
                                color: "var(--site-on-background)",
                                background: "var(--site-surface-container-low)",
                                borderColor: "var(--site-outline-variant)",
                            }}
                            aria-label="Cerrar menu"
                        >
                            <X size={22} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto px-5 pb-8 pt-4">
                        <div className="space-y-2">
                        {navLinks.map((item) => {
                            const { href, label, children } = item;
                            const active = isActiveItem(item);
                            return (
                            <div
                                key={href}
                                className="rounded-[1.25rem] border p-1.5"
                                style={{
                                    background: active ? "var(--site-primary-container)" : "var(--site-surface-container-low)",
                                    borderColor: "var(--site-outline-variant)",
                                }}
                            >
                                    <Link
                                        href={href}
                                        onClick={() => setMobileOpen(false)}
                                        className="flex items-center justify-between gap-4 rounded-2xl px-4 py-3.5 text-base font-black"
                                        style={{ color: active ? "var(--site-primary)" : "var(--site-on-background)" }}
                                    >
                                        <span>{label}</span>
                                        <ArrowRight size={17} aria-hidden="true" />
                                    </Link>
                                {Boolean(children?.length) && (
                                    <div className="grid gap-1 px-2 pb-2">
                                        {children?.map((child) => {
                                            const childActive = isActiveHref(child.href);
                                            return (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                onClick={() => setMobileOpen(false)}
                                                className="rounded-xl px-3 py-2.5 text-sm font-bold"
                                                style={{
                                                    color: childActive ? "var(--site-primary)" : "var(--site-on-surface-variant)",
                                                    background: childActive ? "color-mix(in srgb, var(--site-primary) 12%, transparent)" : "transparent",
                                                }}
                                            >
                                                {child.label}
                                            </Link>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                            );
                        })}
                        </div>
                        {ctaLabel && ctaHref && (
                            <Link
                                href={ctaHref}
                                onClick={() => setMobileOpen && setMobileOpen(false)}
                                className="mt-6 flex w-full items-center justify-center gap-2 rounded-full px-5 py-4 text-[13px] font-black uppercase tracking-wider"
                                style={{
                                    background: "var(--site-cta-gradient)",
                                    backgroundSize: "200% auto",
                                    color: "white",
                                    boxShadow: "var(--site-cta-shadow)",
                                }}
                            >
                                <span className="truncate">{ctaLabel}</span>
                                <ArrowRight size={16} aria-hidden="true" />
                            </Link>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}

export const Navbar_compat = Navbar;
