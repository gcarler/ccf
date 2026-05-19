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
        { label: 'Academia', href: '/academy' },
        { label: 'Proyectos', href: '/projects' },
        { label: 'Prédicas', href: '/sermons' },
        { label: 'Libros', href: '/books' },
        { label: 'Testimonios', href: '/testimonials' },
        { label: 'Eventos', href: '/events' },
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
        <nav className={`fixed top-0 left-0 right-0 z-[100] transition-all duration-500 ${isScrolled ? 'py-4' : 'py-6'}`}>
            <div className="container mx-auto px-6">
                <div className={`glass-card flex items-center justify-between px-6 py-3 transition-all duration-500 rounded-2xl ${isScrolled 
                    ? 'bg-white/80 dark:bg-[#1E1F21]/80 backdrop-blur-xl shadow-xl border border-slate-200/50 dark:border-white/5' 
                    : 'bg-transparent border border-transparent'
                    }`}>
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="bg-blue-600 p-2 rounded-xl group-hover:scale-105 transition-transform shadow-lg shadow-blue-500/20">
                            <Church size={20} className="text-white" />
                        </div>
                        <span className="font-black text-xl tracking-tight text-slate-900 dark:text-white transition-colors">
                            CCF <span className="text-blue-500 items-baseline">Platform</span>
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
                    <div className="hidden md:flex items-center gap-4">
                        {isAuthenticated ? (
                            <div className="flex items-center gap-4">
                                <Link href="/admin" className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-[12px] font-bold transition-all bg-slate-100 text-slate-800 hover:bg-slate-200 dark:bg-white/10 dark:text-white dark:hover:bg-white/20">
                                    <LayoutDashboard size={16} />
                                    Panel
                                </Link>
                                <button
                                    onClick={logout}
                                    className="p-2.5 rounded-xl bg-rose-50 text-rose-600 hover:bg-rose-100 dark:bg-rose-500/10 dark:text-rose-400 dark:hover:bg-rose-500/20 transition-colors"
                                    title="Cerrar Sesión"
                                >
                                    <LogOut size={18} />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3">
                                <Link href="/login" className="px-5 py-2 rounded-lg text-[13px] font-bold text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors">
                                    Login
                                </Link>
                                <Link href="/register" className="px-5 py-2 rounded-lg bg-blue-600 text-white text-[13px] font-bold shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all">
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
                <div className="lg:hidden px-6 mt-4">
                    <div className="bg-white dark:bg-[#252528] rounded-2xl p-6 space-y-2 shadow-2xl border border-slate-200/50 dark:border-white/5 animate-in slide-in-from-top-4 duration-300 max-h-[70vh] overflow-y-auto">
                        {navItems.map((item: any) => (
                            <div key={item.label}>
                                {item.submenu ? (
                                    <div className="space-y-2 py-2">
                                        <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 px-3 mb-1">{item.label}</div>
                                        {item.submenu.map((sub: any) => (
                                            <Link
                                                key={sub.href}
                                                href={sub.href}
                                                className="block py-3 px-4 text-sm font-bold text-slate-900 dark:text-white bg-slate-50 dark:bg-white/5 rounded-xl"
                                                onClick={() => setMobileMenuOpen(false)}
                                            >
                                                {sub.label}
                                            </Link>
                                        ))}
                                    </div>
                                ) : (
                                    <Link
                                        href={item.href}
                                        className="block py-3 px-3 text-sm font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-white/5"
                                        onClick={() => setMobileMenuOpen(false)}
                                    >
                                        {item.label}
                                    </Link>
                                )}
                            </div>
                        ))}
                        <div className="pt-4 mt-2 border-t border-slate-100 dark:border-white/5">
                            <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="block py-3 text-sm font-bold text-blue-600 dark:text-blue-400">Iniciar Sesión</Link>
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
                className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all flex items-center gap-1.5 ${active
                    ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5'
                    }`}
            >
                {label}
                <ChevronDown size={14} className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            <div className={`absolute top-full left-0 mt-2 w-56 pt-2 transition-all duration-300 origin-top-left ${isOpen ? 'opacity-100 translate-y-0 scale-100 visible' : 'opacity-0 -translate-y-2 scale-95 invisible'}`}>
                <div className="bg-white dark:bg-[#252528] rounded-2xl shadow-2xl border border-slate-200/50 dark:border-white/5 p-2 overflow-hidden">
                    {items.map((sub) => (
                        <Link
                            key={sub.href}
                            href={sub.href}
                            className="flex items-center gap-3 px-4 py-2.5 rounded-xl text-[13px] font-bold text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-all"
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
            className={`px-4 py-2 rounded-lg text-[13px] font-bold transition-all relative group flex items-center ${active
                ? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10'
                : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-white/5'
                }`}
        >
            {children}
        </Link>
    );
}
