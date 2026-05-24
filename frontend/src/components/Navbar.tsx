"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import {
    Menu,
    X,
    Church,
    LayoutDashboard,
    LogOut,
    ChevronDown
} from 'lucide-react';
import { useContentBlock } from '@/hooks/useContent';

export default function Navbar() {
    const { isAuthenticated, logout } = useAuth();
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [navItems, setNavItems] = useState([
        { label: 'Inicio', href: '/' },
        { label: 'Academia', href: '/plataforma/academy' },
        { label: 'Proyectos', href: '/plataforma/projects' },
        { label: 'Prédicas', href: '/predicas' },
        { label: 'Libros', href: '/books' },
        { label: 'Testimonios', href: '/testimonios' },
        { label: 'Eventos', href: '/eventos' },
        { label: 'Donaciones', href: '/donate' },
    ]);
    const pathname = usePathname() ?? '/';
    const { data: navContent } = useContentBlock('navbar_items');

    useEffect(() => {
        if (navContent?.items && Array.isArray(navContent.items)) {
            setNavItems(navContent.items);
        }
    }, [navContent]);

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
                    ? 'bg-white/80 dark:bg-[#1E1F21]/80 backdrop-blur-xl shadow-lg border border-slate-200/50 dark:border-white/5'
                    : 'bg-transparent border border-transparent'
                    }`}>
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="bg-blue-600 p-1.5 rounded-md group-hover:scale-105 transition-transform shadow-md shadow-blue-500/20">
                            <Church size={16} className="text-white" />
                        </div>
                        <span className="font-bold text-sm tracking-tight text-slate-900 dark:text-white transition-colors">
                            CCF <span className="text-blue-500">Platform</span>
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
                                <Link href="/plataforma/admin" className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all bg-slate-100 text-slate-800 hover:bg-slate-200 dark:bg-white/10 dark:text-white dark:hover:bg-white/20">
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
                                <Link href="/login" className="px-3 py-1.5 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors">
                                    Login
                                </Link>
                                <Link href="/register" className="px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs font-semibold shadow-md shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
                                    Empezar
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Mobile Toggle */}
                    <button
                        className="lg:hidden p-2 text-slate-500 dark:text-slate-400"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <div className="lg:hidden px-4 mt-2">
                    <div className="bg-white dark:bg-[#252528] rounded-lg p-4 space-y-1.5 shadow-xl border border-slate-200/50 dark:border-white/5 animate-in slide-in-from-top-4 duration-200 max-h-[70vh] overflow-y-auto">
                        {navItems.map((item: any) => (
                            <div key={item.label}>
                                {item.submenu ? (
                                    <div className="space-y-1 py-1">
                                        <div className="text-[9px] font-semibold uppercase tracking-wide text-slate-400 px-2 mb-0.5">{item.label}</div>
                                        {item.submenu.map((sub: any) => (
                                            <Link
                                                key={sub.href}
                                                href={sub.href}
                                                className="block py-2 px-3 text-xs font-semibold text-slate-900 dark:text-white bg-slate-50 dark:bg-white/5 rounded-md"
                                                onClick={() => setMobileMenuOpen(false)}
                                            >
                                                {sub.label}
                                            </Link>
                                        ))}
                                    </div>
                                ) : (
                                    <Link
                                        href={item.href}
                                        className="block py-2 px-2 text-xs font-semibold text-slate-900 dark:text-white border-b border-slate-100 dark:border-white/5"
                                        onClick={() => setMobileMenuOpen(false)}
                                    >
                                        {item.label}
                                    </Link>
                                )}
                            </div>
                        ))}
                        <div className="pt-2 mt-1 border-t border-slate-100 dark:border-white/5">
                            <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="block py-2 text-xs font-semibold text-blue-600 dark:text-blue-400">Iniciar Sesión</Link>
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
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5'
                    }`}
            >
                {label}
                <ChevronDown size={12} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            <div className={`absolute top-full left-0 mt-1 w-48 pt-1 transition-all duration-200 origin-top-left ${isOpen ? 'opacity-100 translate-y-0 scale-100 visible' : 'opacity-0 -translate-y-1 scale-95 invisible'}`}>
                <div className="bg-white dark:bg-[#252528] rounded-lg shadow-lg border border-slate-200/50 dark:border-white/5 p-1 overflow-hidden">
                    {items.map((sub) => (
                        <Link
                            key={sub.href}
                            href={sub.href}
                            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all"
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
                ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5'
                }`}
        >
            {children}
        </Link>
    );
}
