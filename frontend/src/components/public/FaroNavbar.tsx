"use client";

import Link from "next/link";
import React from "react";
import { useContentBlock } from "@/hooks/useContent";

const FALLBACK_ITEMS = [
    { label: "Sobre Nosotros", href: "/faro/nosotros" },
    { label: "Testimonios", href: "/faro/testimonios" },
    { label: "Eventos", href: "/faro/eventos" },
    { label: "Prédicas", href: "/faro/predicas" },
    { label: "Cursos", href: "/faro/cursos" },
    { label: "Sedes", href: "/faro/sedes" }
];

export default function FaroNavbar() {
    const { data: navContent } = useContentBlock("faro_nav_items");
    const navItems = Array.isArray(navContent?.items) ? navContent.items : FALLBACK_ITEMS;

    return (
        <nav className="fixed top-0 w-full z-50 bg-faro-surface/70 dark:bg-[#001134]/70 backdrop-blur-xl shadow-[0_20px_40px_rgba(0,17,52,0.1)]">
            <div className="flex justify-between items-center px-8 md:px-12 py-6 max-w-[1440px] mx-auto">
                <div className="text-2xl font-black tracking-tighter text-faro-primary uppercase font-headline">
                    <Link href="/faro">FARO</Link>
                </div>
                <div className="hidden md:flex gap-8 items-center">
                    {navItems.map((item: { label: string; href: string }) => (
                        <Link
                            key={item.href}
                            className="font-headline tracking-tight font-bold text-sm uppercase text-faro-on-surface-variant hover:text-faro-primary transition-all duration-300"
                            href={item.href}
                        >
                            {item.label}
                        </Link>
                    ))}
                </div>
                <div className="flex items-center gap-6">
                    <div className="hidden lg:flex gap-4">
                        <span className="material-symbols-outlined text-faro-primary cursor-pointer hover:scale-110 transition-transform">location_on</span>
                        <span className="material-symbols-outlined text-faro-primary cursor-pointer hover:scale-110 transition-transform">dark_mode</span>
                    </div>
                    <button className="bg-gradient-to-br from-faro-primary to-faro-primary-container text-faro-on-primary px-6 py-2.5 rounded-[0.75rem] font-headline font-bold text-xs uppercase tracking-widest scale-95 active:scale-90 transition-transform hidden sm:block">
                        Quiero conocer a Jesús
                    </button>
                    <button className="sm:hidden material-symbols-outlined text-faro-primary text-2xl scale-95 active:scale-90 transition-transform">account_circle</button>
                </div>
            </div>
        </nav>
    );
}
