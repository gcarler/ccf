"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { 
    Bell, 
    Calendar, 
    Heart,
    HeartHandshake,
    MessageSquare, 
    Users, 
    Megaphone,
    Search,
    Star
} from 'lucide-react';

export default function CommunityLayout({ children }: { children: React.ReactNode }) {
    const sidebarSections = [
        {
            title: "Canales",
            items: [
                { label: "Notificaciones", icon: Bell, href: "/community/notifications" },
                { label: "Anuncios", icon: Megaphone, href: "/community/announcements" },
                { label: "Mensajes", icon: MessageSquare, href: "/community/messages" }
            ]
        },
        {
            title: "Interacción",
            items: [
                { label: "Calendario", icon: Calendar, href: "/community/events" },
                { label: "Ofrendas", icon: HeartHandshake, href: "/community/give" },
                { label: "Muro de Oración", icon: Heart, href: "/community/prayer" },
                { label: "Testimonios", icon: Star, href: "/community/testimonies" }
            ]
        },
        {
            title: "Grupos",
            items: [
                { label: "Grupos Pequeños", icon: Users, href: "/community/grupos" },
                { label: "Descubrir", icon: Search, href: "/community/discover" }
            ]
        }
    ];

    return (
        <ModuleErrorBoundary moduleName="Comunidad">
            <WorkspaceLayout
                sidebarTitle="Comunidad"
                sidebarSections={sidebarSections}
                allowedPermissions={['community:read']}
            >
                {children}
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}

