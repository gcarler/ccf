"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/", label: "Inicio", icon: "home" },
    { href: "/eventos", label: "Eventos", icon: "calendar_today" },
    { href: "/predicas", label: "Prédicas", icon: "play_circle" },
    { href: "/sedes", label: "Sedes", icon: "location_on" },
    { href: "/conocer-a-jesus", label: "Conectar", icon: "menu" },
];

export default function FaroMobileNav() {
    const pathname = usePathname();

    return (
        <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-center pb-8 z-50">
            <div
                className="backdrop-blur-2xl w-[90%] max-w-md rounded-[0.75rem] px-3 py-3 flex justify-between items-center"
                style={{
                    background: "var(--faro-mobile-nav-bg)",
                    boxShadow: "var(--faro-mobile-nav-shadow)",
                }}
            >
                {navItems.map(({ href, label, icon }) => {
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
                            <span className="material-symbols-outlined">{icon}</span>
                            <span className="font-body text-[10px] font-medium tracking-wide">{label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
