"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { 
    HelpCircle, 
    Book, 
    MessageSquare, 
    LifeBuoy,
    FileText,
    History
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
    {
        title: 'Asistencia',
        items: [
            { id: 'center', label: 'Centro de Ayuda', href: '/plataforma/support', icon: HelpCircle },
            { id: 'tickets', label: 'Mis Tickets', href: '/plataforma/support/tickets', icon: MessageSquare },
        ]
    },
    {
        title: 'Recursos',
        items: [
            { id: 'knowledge', label: 'Base de Conocimientos', href: '/plataforma/support/kb', icon: Book },
            { id: 'tutorials', label: 'Tutoriales', href: '/plataforma/support/tutorials', icon: FileText },
        ]
    },
    {
        title: 'Gestión',
        items: [
            { id: 'contact', label: 'Contacto Directo', href: '/plataforma/support/contact', icon: LifeBuoy },
            { id: 'history', label: 'Historial', href: '/plataforma/support/history', icon: History },
        ]
    }
];

export default function SupportLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ModuleErrorBoundary moduleName="Soporte">
            <WorkspaceLayout
                sidebarTitle="Soporte / Ayuda"
                sidebarSections={SIDEBAR_SECTIONS}
            >
                <div className="bg-[#f8f9fb] dark:bg-[#020617] min-h-full">
                    {children}
                </div>
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}

