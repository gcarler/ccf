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
        <nav className={`fixed top-0 left-0 right-0 z-[100] transition-all duration-500 ${isScrolled ? 'py-4' : 'py-6'
            }`}>
            <div className="container mx-auto px-6">
                <div className={`glass-card flex items-center justify-between px-6 py-3 transition-all duration-500 ${isScrolled ? 'bg-white/70 shadow-xl' : 'bg-white/10 border-white/5'
                    }`}>
                    {/* Logo */}
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="bg-blue-600 p-2 rounded-xl group-hover:rotate-12 transition-transform shadow-lg shadow-blue-500/20">
                            <Church size={22} className="text-white" />
                        </div>
                        <span className={`font-black text-xl tracking-tight transition-colors ${isScrolled ? 'text-slate-900' : 'text-white'
                            }`}>
                            CCF <span className="text-blue-500 items-baseline">Platform</span>
                        </span>
                    </Link>

                    {/* Desktop Menu */}
                    <div className="hidden md:flex items-center gap-1">
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
                                        isScrolled={isScrolled}
                                        active={isActive}
                                    />
                                );
                            }

                            return (
                                <NavLink
                                    key={item.href}
                                    href={item.href}
                                    active={isActive}
                                    isScrolled={isScrolled}
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
                                <Link href="/admin" className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${isScrolled
                                    ? 'bg-slate-900 text-white hover:bg-slate-800'
                                    : 'bg-white/10 text-white hover:bg-white/20'
                                    }`}>
                                    <LayoutDashboard size={18} />
                                    Dashboard
                                </Link>
                                <button
                                    onClick={logout}
                                    className="p-2.5 rounded-xl bg-red-50 text-red-600 hover:bg-red-100 transition-colors"
                                    title="Cerrar Sesión"
                                >
                                    <LogOut size={20} />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-3">
                                <Link href="/login" className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-colors ${isScrolled ? 'text-slate-600 hover:text-slate-900' : 'text-slate-300 hover:text-white'
                                    }`}>
                                    Login
                                </Link>
                                <Link href="/register" className="px-6 py-2.5 rounded-xl bg-blue-600 text-white text-sm font-bold shadow-lg shadow-blue-500/20 hover:bg-blue-700 hover:shadow-blue-500/40 transition-all active:scale-95">
                                    Empezar
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Mobile Toggle */}
                    <button
                        className="md:hidden p-2 text-slate-500"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        {mobileMenuOpen ? <X size={28} /> : <Menu size={28} />}
                    </button>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <div className="md:hidden px-6 mt-4">
                    <div className="glass-card bg-white p-6 space-y-2 shadow-2xl animate-in slide-in-from-top-4 duration-300 max-h-[70vh] overflow-y-auto">
                        {navItems.map((item: any) => (
                            <div key={item.label}>
                                {item.submenu ? (
                                    <div className="space-y-2 py-2">
                                        <div className="text-xs font-black uppercase tracking-widest text-slate-400 px-3 mb-1">{item.label}</div>
                                        {item.submenu.map((sub: any) => (
                                            <Link
                                                key={sub.href}
                                                href={sub.href}
                                                className="block py-3 px-4 text-base font-bold text-slate-900 bg-slate-50 rounded-xl"
                                                onClick={() => setMobileMenuOpen(false)}
                                            >
                                                {sub.label}
                                            </Link>
                                        ))}
                                    </div>
                                ) : (
                                    <Link
                                        href={item.href}
                                        className="block py-3 px-3 text-lg font-bold text-slate-900 border-b border-slate-50"
                                        onClick={() => setMobileMenuOpen(false)}
                                    >
                                        {item.label}
                                    </Link>
                                )}
                            </div>
                        ))}
                        <div className="pt-4 border-t border-slate-100">
                            <Link href="/login" onClick={() => setMobileMenuOpen(false)} className="block py-3 text-lg font-bold text-blue-600">Iniciar Sesión</Link>
                        </div>
                    </div>
                </div>
            )}
        </nav>
    );
}

function NavDropdown({ label, items, isScrolled, active }: { label: string, items: any[], isScrolled: boolean, active: boolean }) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div 
            className="relative group"
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
        >
            <button
                className={`px-5 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-1.5 ${active
                    ? (isScrolled ? 'text-blue-600 bg-blue-50' : 'text-white bg-white/10')
                    : (isScrolled ? 'text-slate-500 hover:text-slate-900 hover:bg-slate-50' : 'text-slate-400 hover:text-white hover:bg-white/5')
                    }`}
            >
                {label}
                <ChevronDown size={14} className={`transition-transform duration-300 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            <div className={`absolute top-full left-0 mt-2 w-56 pt-2 transition-all duration-300 origin-top-left ${isOpen ? 'opacity-100 translate-y-0 scale-100 visible' : 'opacity-0 -translate-y-2 scale-95 invisible'}`}>
                <div className="bg-white dark:bg-slate-900 rounded-[1.5rem] shadow-2xl border border-slate-200 dark:border-white/5 p-2 overflow-hidden">
                    {items.map((sub) => (
                        <Link
                            key={sub.href}
                            href={sub.href}
                            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold text-slate-600 dark:text-slate-400 hover:text-blue-600 dark:hover:text-white hover:bg-blue-50 dark:hover:bg-white/5 transition-all"
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
    isScrolled = false
}: {
    href: string;
    children: React.ReactNode;
    active?: boolean;
    isScrolled?: boolean;
}) {
    return (
        <Link
            href={href}
            className={`px-5 py-2 rounded-xl text-sm font-bold transition-all relative group ${active
                ? (isScrolled ? 'text-blue-600 bg-blue-50' : 'text-white bg-white/10')
                : (isScrolled ? 'text-slate-500 hover:text-slate-900 hover:bg-slate-50' : 'text-slate-400 hover:text-white hover:bg-white/5')
                }`}
        >
            {children}
            {active && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-current opacity-50"></span>
            )}
        </Link>
    );
}
