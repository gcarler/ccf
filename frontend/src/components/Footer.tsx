import React from 'react';
import Link from 'next/link';
import { Church, Heart, Mail, Globe } from 'lucide-react';

const footerLinks = [
    {
        title: 'Plataforma',
        links: [
            { label: 'Inicio', href: '/' },
            { label: 'Login', href: '/login' },
            { label: 'Sitio Público', href: '/faro' },
        ],
    },
    {
        title: 'Ministerio',
        links: [
            { label: 'CRM Pastoral', href: '/crm' },
            { label: 'Academia', href: '/academy' },
            { label: 'Proyectos', href: '/projects' },
        ],
    },
    {
        title: 'Conectar',
        links: [
            { label: 'comunicacionesministeriosfaro@gmail.com', href: 'mailto:comunicacionesministeriosfaro@gmail.com', icon: Mail },
            { label: 'elfarocc.tech', href: 'https://elfarocc.tech', icon: Globe },
        ],
    },
];

export default function Footer() {
    return (
        <footer className="w-full bg-[#020617] border-t border-white/5">
            <div className="w-full px-6 lg:px-16 py-16">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-10">
                    {/* Brand */}
                    <div className="md:col-span-1 space-y-4">
                        <div className="flex items-center gap-2 text-white">
                            <Church size={20} className="text-blue-400" />
                            <span className="text-sm font-black uppercase tracking-widest">CCF Ministerio</span>
                        </div>
                        <p className="text-sm text-slate-400 leading-relaxed max-w-xs">
                            Plataforma de inteligencia ministerial para la formación teológica, gestión pastoral y colaboración de equipos.
                        </p>
                        <div className="flex items-center gap-1 text-[11px] text-slate-500">
                            <Heart size={12} className="text-blue-400" />
                            Hecho con fe
                        </div>
                    </div>

                    {/* Links */}
                    {footerLinks.map((group) => (
                        <div key={group.title}>
                            <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 mb-4">
                                {group.title}
                            </h4>
                            <ul className="space-y-3">
                                {group.links.map((link) => (
                                    <li key={link.label}>
                                        <Link
                                            href={link.href}
                                            className="text-sm text-slate-400 hover:text-white transition-colors flex items-center gap-2"
                                        >
                                            {link.icon && <link.icon size={12} className="shrink-0" />}
                                            {link.label}
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>

            {/* Bottom bar */}
            <div className="w-full border-t border-white/5 px-6 lg:px-16 py-5">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-slate-500">
                    <span>&copy; {new Date().getFullYear()} CCF Ministerio. Todos los derechos reservados.</span>
                    <div className="flex items-center gap-4">
                        <Link href="/faro" className="hover:text-white transition-colors">Sitio público</Link>
                        <Link href="/login" className="hover:text-white transition-colors">Acceso interno</Link>
                    </div>
                </div>
            </div>
        </footer>
    );
}
