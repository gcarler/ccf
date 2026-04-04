"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Heart, Calendar, Award, BookOpen, GraduationCap } from 'lucide-react';

const SPIRITUAL_SECTIONS = [
    {
        title: 'Mi Caminar',
        items: [
            { id: 'sl-home',  label: 'Panel Espiritual',  href: '/spiritual-life',              icon: Heart },
            { id: 'sl-tl',    label: 'Línea de Tiempo',   href: '/spiritual-life/timeline',     icon: Calendar },
            { id: 'sl-certs', label: 'Mis Certificados',  href: '/spiritual-life/certificates', icon: Award },
        ]
    },
    {
        title: 'Formación',
        items: [
            { id: 'sl-academy', label: 'Academia CCF', href: '/academy', icon: GraduationCap },
        ]
    }
];

export default function SpiritualLifeLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout sidebarTitle="Vida Espiritual" sidebarSections={SPIRITUAL_SECTIONS}>
            {children}
        </WorkspaceLayout>
    );
}
