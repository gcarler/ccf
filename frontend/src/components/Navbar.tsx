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
    LogOut
} from 'lucide-react';
import { apiUrl } from '@/lib/api';

export default function Navbar() {
    const { isAuthenticated, logout } = useAuth();
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [navItems, setNavItems] = useState([
        { label: 'Inicio', href: '/' },
        { label: 'Academia', href: '/academy' },
        { label: 'Prédicas', href: '/sermons' },
        { label: 'Libros', href: '/books' },
        { label: 'Testimonios', href: '/testimonials' },
    ]);
    const pathname = usePathname();

    useEffect(() => {
        const fetchNav = async () => {
            try {
                const res = await fetch(apiUrl('/content/navbar_items'));
                if (res.ok) {
                    const data = await res.json();
                    setNavItems(JSON.parse(data.content).items);
                }
            } catch (e) {
                console.error("Error fetching nav items", e);
            }
        };
        fetchNav();
    }, []);

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
                        {navItems.map((item) => (
                            <NavLink
                                key={item.href}
                                href={item.href}
                                active={pathname === item.href}
                                isScrolled={isScrolled}
                            >
                                {item.label}
                            </NavLink>
                        ))}
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
                    <div className="glass-card bg-white p-6 space-y-4 shadow-2xl animate-in slide-in-from-top-4 duration-300">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="block py-3 text-lg font-bold text-slate-900 border-b border-slate-50"
                                onClick={() => setMobileMenuOpen(false)}
                            >
                                {item.label}
                            </Link>
                        ))}
                        <Link href="/login" className="block py-3 text-lg font-bold text-blue-600">Iniciar Sesión</Link>
                    </div>
                </div>
            )}
        </nav>
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
