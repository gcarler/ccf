"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import OptimizedImage from "@/components/ui/OptimizedImage";
import { useSiteBranding } from '@/lib/site-branding';
import {
    Menu,
    X,
    Church,
    LayoutDashboard,
    LogOut,
    ChevronDown
} from 'lucide-react';
import { SITE_NAME } from '@/lib/site-config';

export default function Navbar() {
    const { isAuthenticated, logout } = useAuth();
    const { logoUrl, logoName } = useSiteBranding({ logoName: SITE_NAME });
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const navItems = [
        { label: 'Inicio', href: '/' },
        { label: 'Academia', href: '/plataforma/academy' },
        { label: 'Proyectos', href: '/plataforma/projects/list#projects-list' },
        { label: 'Prédicas', href: '/predicas' },
        { label: 'Libros', href: '/books' },
        { label: 'Testimonios', href: '/testimonios' },
        { label: 'Eventos', href: '/eventos' },
        { label: 'Donaciones', href: '/donate' },
    ];
    const pathname = usePathname() ?? '/';
    const siteName: string = logoName || SITE_NAME;

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <nav className={`fixed top-0 left-0 right-0 z-[100] transition-all duration-300 ${isScrolled ? 'py-2' : 'py-3'}`}>
            <div className="container mx-auto px-4">
                <div className={`glass-card flex items-center justify-between px-4 py-2 transition-all duration-300 rounded-lg ${isScrolled
                    ? 'bg-white/80 dark:bg-[#1E1F21]/80 backdrop-blur-xl shadow-lg border border-[hsl(var(--border))]/50 dark:border-white/5'
                    : 'bg-transparent border border-transparent'
                    }`}>
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="bg-[hsl(var(--primary))] p-1.5 rounded-md group-hover:scale-105 transition-transform shadow-md shadow-blue-500/20 overflow-hidden">
                            {logoUrl ? (
                                <OptimizedImage src={logoUrl} alt={siteName} width={16} height={16} className="w-4 h-4 object-contain" />
                            ) : (
                                <Church size={16} className="text-white" />
                            )}
                        </div>
                        <span className="font-bold text-sm tracking-tight text-[hsl(var(--text-primary))] dark:text-white transition-colors">
                            {siteName}
                        </span>
                    </Link>

                    {/* Desktop Menu */}
                    <div className="hidden lg:flex items-center gap-1">
                        {navItems.map((item: any) => {
                            const isActive = item.href === '/' 
                                ? (pathname || '') === '/' 
                                : (pathname || '').startsWith(item.href);
                            
                            if (item.submenu && Array.isArray(item.submenu)) {
                                return (
                                    <NavDropdown
                                        key={item.label}
                                        label={item.label}
                                        items={item.submenu}
                                        active={isActive}
                                    />
                                );
                            }

                            return (
                                <NavLink
                                    key={item.href}
                                    href={item.href}
                                    active={isActive}
                                >
                                    {item.label}
                                </NavLink>
                            );
                        })}
                    </div>

                    {/* User Actions */}
                    <div className="hidden md:flex items-center gap-2">
                        {isAuthenticated ? (
                            <div className="flex items-center gap-2">
                                <Link href="/plataforma/admin" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all bg-[hsl(var(--surface-2))] text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-3))] dark:bg-white/10 dark:text-white dark:hover:bg-white/20">
                                    <LayoutDashboard size={13} />
                                    Panel
                                </Link>
                                <button
                                    onClick={logout}
                                    className="p-1.5 rounded-md bg-rose-50 text-rose-600 hover:bg-rose-100 dark:bg-rose-500/10 dark:text-rose-400 dark:hover:bg-rose-500/20 transition-colors"
                                    title="Cerrar Sesión"
                                >
                                    <LogOut size={14} />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2">
                                <Link href="/login" className="px-3 py-1.5 rounded-md text-xs font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors">
                                    Login
                                </Link>
                                <Link href="/register" className="px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-white text-xs font-semibold shadow-md shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
                                    Empezar
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Mobile Toggle */}
                    <button
                        className="lg:hidden p-2 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <div className="lg:hidden px-4 mt-2">
                    <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg p-4 space-y-1.5 shadow-xl border border-[hsl(var(--border))]/50 dark:border-white/5 animate-in slide-in-from-top-4 duration-200 max-h-[70vh] overflow-y-auto">
                        {navItems.map((item: any) => (
                            <div key={item.label}>
                                {item.submenu ? (
                                    <div className="space-y-1 py-1">
                                        <div className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] px-2 mb-0.5">{item.label}</div>
                                        {item.submenu.map((sub: any) => (
                                            <Link
                                                key={sub.href}
                                                href={sub.href}
                                                className="block py-2 px-3 text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-md"
                                                onClick={() => setMobileMenuOpen(false)}
                                            >
                                                {sub.label}
                                            </Link>
                                        ))}
                                    </div>
                                ) : (
                                    <Link
                                        href={item.href}
                                        className="block py-2 px-2 text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white border-b border-[hsl(var(--border))] dark:border-white/5"
                                        onClick={() => setMobileMenuOpen(false)}
                                    >
                                        {item.label}
                                    </Link>
                                )}
                            </div>
                        ))}
                        <div className="pt-2 mt-1 border-t border-[hsl(var(--border))] dark:border-white/5">
                            <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-xs font-semibold text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]">Iniciar Sesión</Link>
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}

function NavDropdown({ label, items, active }: { label: string, items: any[], active: boolean }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div 
            className="relative group"
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
        >
            <button
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all flex items-center gap-1 ${active
                    ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10'
                    : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                    }`}
            >
                {label}
                <ChevronDown size={12} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            <div className={`absolute top-full left-0 mt-1 w-48 pt-1 transition-all duration-200 origin-top-left ${isOpen ? 'opacity-100 translate-y-0 scale-100 visible' : 'opacity-0 -translate-y-1 scale-95 invisible'}`}>
                <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#252528] rounded-lg shadow-lg border border-[hsl(var(--border))]/50 dark:border-white/5 p-1 overflow-hidden">
                    {items.map((sub) => (
                        <Link
                            key={sub.href}
                            href={sub.href}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))] dark:hover:text-[hsl(var(--primary))] hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all"
                        >
                            {sub.label}
                        </Link>
                    ))}
                </div>
            </div>
        </div>
    );
}

function NavLink({
    href,
    children,
    active = false,
}: {
    href: string;
    children: React.ReactNode;
    active?: boolean;
}) {
    return (
        <Link
            href={href}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all relative group flex items-center ${active
                ? 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10'
                : 'text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5'
                }`}
        >
            {children}
        </Link>
    );
}
