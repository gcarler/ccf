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

export default function FaroMobileNav() {
    const pathname = usePathname();

    return (
        <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-center z-50" style={{ paddingBottom: 'max(2rem, env(safe-area-inset-bottom))' }}>
            <div
                className="backdrop-blur-2xl w-[90%] max-w-md rounded-[0.75rem] px-3 py-3 flex justify-between items-center"
                style={{
                    background: "var(--faro-mobile-nav-bg)",
                    boxShadow: "var(--faro-mobile-nav-shadow)",
                }}
            >
                {navItems.map(({ href, label, icon: Icon }) => {
                    const isActive = pathname === href || (href !== "/" && pathname?.startsWith(href));
                    return (
                        <Link
                            key={href}
                            href={href}
                            className="flex flex-col items-center justify-center rounded-[0.75rem] p-2 transition-all"
                            style={isActive
                                ? {
                                      color: "var(--faro-primary)",
                                      background: "var(--faro-primary-container)",
                                      boxShadow: "var(--faro-mobile-nav-glow)",
                                  }
                                : {
                                      color: "var(--faro-mobile-nav-inactive)",
                                  }
                            }
                        >
                            <Icon size={20} strokeWidth={2} aria-hidden="true" />
                            <span className="font-body text-[10px] font-medium tracking-wide">{label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
