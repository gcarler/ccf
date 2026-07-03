"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Home, MapPin, Menu, PlayCircle } from "lucide-react";

const navItems = [
    { href: "/", label: "Inicio", icon: Home },
    { href: "/eventos", label: "Eventos", icon: CalendarDays },
    { href: "/predicas", label: "Prédicas", icon: PlayCircle },
    { href: "/sedes", label: "Sedes", icon: MapPin },
    { href: "/conocer-a-jesus", label: "Conectar", icon: Menu },
];

export default function MobileNav() {
    const pathname = usePathname();
    const items = navItems;

    return (
        <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-center z-50" style={{ paddingBottom: 'max(1.75rem, env(safe-area-inset-bottom))' }}>
            <div
                className="backdrop-blur-2xl w-[92%] max-w-md rounded-[1rem] px-4 py-3.5 flex justify-between items-center"
                style={{
                    background: "var(--site-mobile-nav-bg)",
                    boxShadow: "var(--site-mobile-nav-shadow)",
                }}
            >
                {items.map(({ href, label, icon: Icon }) => {
                    const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href));
                    return (
                        <Link
                            key={href}
                            href={href}
                            className="flex flex-col items-center justify-center rounded-[0.875rem] px-2.5 py-2 transition-all"
                            style={isActive
                                ? {
                                      color: "var(--site-primary)",
                                      background: "var(--site-primary-container)",
                                      boxShadow: "var(--site-mobile-nav-glow)",
                                  }
                                : {
                                      color: "var(--site-mobile-nav-inactive)",
                                  }
                            }
                        >
                            <Icon size={22} strokeWidth={2} aria-hidden="true" />
                            <span className="font-body text-[11px] font-medium tracking-wide mt-1">{label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}

export const MobileNav_compat = MobileNav;
