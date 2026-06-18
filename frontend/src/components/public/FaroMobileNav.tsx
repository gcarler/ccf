"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Home, MapPin, Menu, PlayCircle } from "lucide-react";
import { useContentBlock } from "@/hooks/useContent";
import { SITE_KEY } from "@/lib/site-config";

const navItems = [
    { href: "/", label: "Inicio", icon: Home },
    { href: "/eventos", label: "Eventos", icon: CalendarDays },
    { href: "/predicas", label: "Prédicas", icon: PlayCircle },
    { href: "/sedes", label: "Sedes", icon: MapPin },
    { href: "/conocer-a-jesus", label: "Conectar", icon: Menu },
];

const ICONS = {
    home: Home,
    calendar: CalendarDays,
    play: PlayCircle,
    "map-pin": MapPin,
    menu: Menu,
};

export default function FaroMobileNav() {
    const pathname = usePathname();
    const { data: mobileNavContent } = useContentBlock(`${SITE_KEY}_mobile_nav`);
    const cmsItems = mobileNavContent?.parsed && typeof mobileNavContent.parsed === "object" && !Array.isArray(mobileNavContent.parsed)
        ? (mobileNavContent.parsed as { items?: Array<Record<string, unknown>> }).items
        : undefined;
    const items = Array.isArray(cmsItems) && cmsItems.length > 0
        ? cmsItems
            .map((item) => {
                const href = typeof item.href === "string" ? item.href : "";
                const label = typeof item.label === "string" ? item.label : "";
                const iconKey = typeof item.icon === "string" ? item.icon : "menu";
                return { href, label, icon: ICONS[iconKey as keyof typeof ICONS] || Menu };
            })
            .filter((item) => item.href && item.label)
        : navItems;

    return (
        <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-center z-50" style={{ paddingBottom: 'max(2rem, env(safe-area-inset-bottom))' }}>
            <div
                className="backdrop-blur-2xl w-[90%] max-w-md rounded-[0.75rem] px-3 py-3 flex justify-between items-center"
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
                            className="flex flex-col items-center justify-center rounded-[0.75rem] p-2 transition-all"
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
                            <Icon size={20} strokeWidth={2} aria-hidden="true" />
                            <span className="font-body text-[10px] font-medium tracking-wide">{label}</span>
                        </Link>
                    );
                })}
            </div>
        </nav>
    );
}
