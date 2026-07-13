"use client";


import { getCmsPublicMenu } from "@/lib/cms/v2";
import { SITE_KEY, SITE_NAME } from "@/lib/site-config";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { ArrowRight, ChevronDown, MapPin, Menu, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
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
            <header aria-hidden={mobileOpen} className="fixed left-0 right-0 top-0 z-50 w-full px-3 pt-3 transition-all duration-300 md:px-5 md:pt-4">
                <nav
                    className="ccf-container flex h-[70px] max-w-[1360px] items-center justify-between gap-4 rounded-[2rem] border px-3 shadow-sm transition-all duration-300 md:h-[76px] md:px-4"
                    style={{
                        background: scrolled
                            ? "color-mix(in srgb, var(--site-navbar-bg-scrolled) 92%, transparent)"
                            : "color-mix(in srgb, var(--site-navbar-bg) 82%, transparent)",
                        borderColor: scrolled ? "var(--site-navbar-border)" : "color-mix(in srgb, var(--site-outline-variant) 58%, transparent)",
                        backdropFilter: "blur(24px)",
                        boxShadow: scrolled ? "0 22px 60px rgba(0, 0, 0, 0.14)" : "0 14px 40px rgba(0, 0, 0, 0.08)",
                    }}
                >
                    {/* Logo */}
                    <Link href="/" className="group flex min-w-0 shrink-0 items-center gap-3 rounded-full pr-2 transition-opacity hover:opacity-90">
                        {logoUrl ? (
                            <span
                                className="grid h-11 w-11 place-items-center rounded-full border md:h-12 md:w-12"
                                style={{
                                    background: "var(--site-surface-container-low)",
                                    borderColor: "var(--site-outline-variant)",
                                }}
                            >
                                <OptimizedImage src={logoUrl} alt={logoName} width={42} height={42} className="h-8 w-8 object-contain md:h-9 md:w-9" />
                            </span>
                        ) : (
                            <div
                                className="relative h-11 w-11 rounded-full border p-2 md:h-12 md:w-12"
                                style={{
                                    background: "var(--site-surface-container-low)",
                                    borderColor: "var(--site-outline-variant)",
                                }}
                            >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-full h-full text-site-primary">
                                    <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                    <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                </svg>
                            </div>
                        )}
                        {logoName && (
                            <span className="flex min-w-0 flex-col leading-none">
                                <span
                                    className="max-w-[10rem] truncate text-[15px] font-semibold md:max-w-[14rem] md:text-[17px]"
                                    style={{ color: "var(--site-on-background)" }}
                                >
                                    {logoName}
                                </span>
                                <span className="hidden pt-1 text-[10px] font-semibold uppercase tracking-[0.18em] md:block" style={{ color: "var(--site-on-surface-variant)" }}>
                                    Comunidad cristiana
                                </span>
                            </span>
                        )}
                    </Link>

                    {/* Desktop Nav */}
                    <div className="hidden min-w-0 flex-1 justify-center px-4 lg:flex">
                        <div className="flex max-w-full items-center gap-1">
                        {navLinks.map((item) => {
                            const { href, label, children } = item;
                            const active = isActiveItem(item);
                            const hasChildren = Boolean(children?.length);
                            return (
                                <div key={href} className="group relative">
                                <Link
                                    key={href}
                                    href={href}
                                    className="relative inline-flex h-11 items-center gap-1.5 rounded-full px-4 text-[14px] font-semibold transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent xl:px-5"
                                    style={{
                                        color: active
                                            ? "var(--site-on-background)"
                                            : "var(--site-on-surface-variant)",
                                        background: active ? "color-mix(in srgb, var(--site-primary-container) 72%, transparent)" : "transparent",
                                    }}
                                >
                                    <span className="max-w-[8.75rem] truncate">{label}</span>
                                    {hasChildren && (
                                        <ChevronDown
                                            size={14}
                                            strokeWidth={2.25}
                                            className="transition-transform duration-200 group-hover:rotate-180 group-focus-within:rotate-180"
                                            aria-hidden="true"
                                        />
                                    )}
                                    <span
                                        className="absolute bottom-1.5 left-4 right-4 h-0.5 origin-center rounded-full transition-transform duration-200 group-hover:scale-x-100"
                                        style={{
                                            background: "var(--site-primary)",
                                            transform: active ? "scaleX(1)" : "scaleX(0)",
                                        }}
                                    />
                                </Link>
                                {hasChildren && (
                                    <div
                                        className="invisible absolute left-1/2 top-full z-50 mt-4 w-[320px] -translate-x-1/2 translate-y-2 rounded-[1.35rem] border p-3 opacity-0 shadow-2xl backdrop-blur-2xl transition-all duration-200 group-hover:visible group-hover:translate-y-0 group-hover:opacity-100 group-focus-within:visible group-focus-within:translate-y-0 group-focus-within:opacity-100"
                                        style={{
                                            background: "var(--site-dropdown-bg)",
                                            border: "1px solid var(--site-dropdown-border)",
                                        }}
                                    >
                                        <div className="px-3 pb-2 pt-1 text-[11px] font-semibold uppercase tracking-[0.18em]" style={{ color: "var(--site-on-surface-variant)" }}>
                                            Explorar
                                        </div>
                                        {children?.map((child) => {
                                            const childActive = isActiveHref(child.href);
                                            return (
                                            <Link
                                                key={`${href}-${child.href}`}
                                                href={child.href}
                                                className="group/item flex items-center justify-between gap-4 rounded-2xl px-4 py-3.5 text-sm font-semibold transition-colors"
                                                style={{
                                                    color: childActive ? "var(--site-on-background)" : "var(--site-on-background)",
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
                    <div className="flex shrink-0 items-center gap-2">
                        {/* Location */}
                        <Link
                            href="/sedes"
                            className="hidden h-11 w-11 items-center justify-center rounded-full border transition-all hover:-translate-y-0.5 md:flex"
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
                            className="flex h-11 w-11 items-center justify-center rounded-full border transition-all hover:-translate-y-0.5"
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
                                className="hidden h-11 items-center gap-2 rounded-full px-4 text-[13px] font-semibold transition-transform hover:-translate-y-0.5 xl:inline-flex xl:px-5"
                                style={{
                                    background: "var(--site-primary)",
                                    color: "var(--site-on-primary)",
                                    boxShadow: "0 14px 34px color-mix(in srgb, var(--site-primary) 24%, transparent)",
                                }}
                            >
                                <span className="max-w-[13rem] truncate">{ctaLabel}</span>
                                <ArrowRight size={15} aria-hidden="true" />
                            </Link>
                        )}

                        {/* Mobile Menu Toggle */}
                        <button
                            onClick={() => setMobileOpen(!mobileOpen)}
                            className="flex h-11 w-11 items-center justify-center rounded-full border lg:hidden"
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
                    className="fixed inset-0 z-[60] flex flex-col lg:hidden"
                    style={{
                        background: "var(--site-background)",
                        opacity: 0.98,
                        backdropFilter: "blur(20px)",
                    }}
                >
                    <div className="flex h-[82px] items-center justify-between px-5">
                        <Link href="/" className="flex min-w-0 items-center gap-3" onClick={() => setMobileOpen(false)}>
                            {logoUrl ? (
                                <span
                                    className="grid h-11 w-11 place-items-center rounded-full border"
                                    style={{
                                        background: "var(--site-surface-container-low)",
                                        borderColor: "var(--site-outline-variant)",
                                    }}
                                >
                                    <OptimizedImage src={logoUrl} alt={logoName} width={40} height={40} className="h-8 w-8 object-contain" />
                                </span>
                            ) : (
                                <div className="h-11 w-11 rounded-full border p-2 text-site-primary" style={{ borderColor: "var(--site-outline-variant)" }}>
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-full w-full">
                                        <path d="M8 22L10 6L12 2L14 6L16 22H8Z" strokeLinejoin="round" />
                                        <circle cx="12" cy="4" r="1.5" fill="currentColor" />
                                    </svg>
                                </div>
                            )}
                            <span className="truncate text-base font-semibold" style={{ color: "var(--site-on-background)" }}>{logoName}</span>
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

                    <div className="flex-1 overflow-y-auto px-5 pb-8 pt-3">
                        <div className="mb-6">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--site-on-surface-variant)" }}>
                                Menu principal
                            </p>
                        </div>
                        <div className="space-y-3">
                        {navLinks.map((item) => {
                            const { href, label, children } = item;
                            const active = isActiveItem(item);
                            return (
                            <div
                                key={href}
                                className="rounded-[1.35rem] border p-1.5"
                                style={{
                                    background: active ? "var(--site-primary-container)" : "color-mix(in srgb, var(--site-surface-container-low) 92%, transparent)",
                                    borderColor: "var(--site-outline-variant)",
                                }}
                            >
                                    <Link
                                        href={href}
                                        onClick={() => setMobileOpen(false)}
                                        className="flex items-center justify-between gap-4 rounded-2xl px-4 py-4 text-[17px] font-semibold"
                                        style={{ color: active ? "var(--site-on-background)" : "var(--site-on-background)" }}
                                    >
                                        <span>{label}</span>
                                        <ArrowRight size={18} aria-hidden="true" />
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
                                                className="rounded-xl px-3 py-2.5 text-sm font-semibold"
                                                style={{
                                                    color: childActive ? "var(--site-on-background)" : "var(--site-on-surface-variant)",
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
                                className="mt-7 flex w-full items-center justify-center gap-2 rounded-full px-5 py-4 text-sm font-semibold"
                                style={{
                                    background: "var(--site-primary)",
                                    color: "var(--site-on-primary)",
                                    boxShadow: "0 18px 42px color-mix(in srgb, var(--site-primary) 28%, transparent)",
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
