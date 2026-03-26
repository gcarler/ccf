"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
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
            { id: 'center', label: 'Centro de Ayuda', href: '/support', icon: HelpCircle },
            { id: 'tickets', label: 'Mis Tickets', href: '/support/tickets', icon: MessageSquare },
        ]
    },
    {
        title: 'Recursos',
        items: [
            { id: 'knowledge', label: 'Base de Conocimientos', href: '/support/kb', icon: Book },
            { id: 'tutorials', label: 'Tutoriales', href: '/support/tutorials', icon: FileText },
        ]
    },
    {
        title: 'Gestión',
        items: [
            { id: 'contact', label: 'Contacto Directo', href: '/support/contact', icon: LifeBuoy },
            { id: 'history', label: 'Historial', href: '/support/history', icon: History },
        ]
    }
];

export default function SupportLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <WorkspaceLayout 
            sidebarTitle="Soporte / Ayuda" 
            sidebarSections={SIDEBAR_SECTIONS}
        >
            <div className="bg-[#f8f9fb] dark:bg-[#020617] min-h-full">
                {children}
            </div>
        </WorkspaceLayout>
    );
}
