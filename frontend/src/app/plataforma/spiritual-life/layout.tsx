"use client";

import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Heart, Calendar, Award, GraduationCap } from 'lucide-react';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import SpiritualTimelinePanel from '@/components/spiritual/SpiritualTimelinePanel';
import SpiritualCertificatesPanel from '@/components/spiritual/SpiritualCertificatesPanel';

export default function SpiritualLifeLayout({ children }: { children: React.ReactNode }) {
    const { pushSidebarPanel } = useSidebarLayers();

    const SPIRITUAL_SECTIONS = [
        {
            title: 'Mi Caminar',
            items: [
                { id: 'sl-home',  label: 'Panel Espiritual',  href: '/plataforma/spiritual-life', icon: Heart },
                { 
                    id: 'sl-tl',    
                    label: 'Línea de Tiempo',   
                    href: '/plataforma/spiritual-life/timeline',
                    icon: Calendar,
                    onClick: () => pushSidebarPanel({
                        id: 'spiritual-timeline',
                        title: 'Línea de Tiempo',
                        content: <SpiritualTimelinePanel />
                    })
                },
                { 
                    id: 'sl-certs', 
                    label: 'Mis Certificados',  
                    href: '/plataforma/spiritual-life/certificates',
                    icon: Award,
                    onClick: () => pushSidebarPanel({
                        id: 'spiritual-certs',
                        title: 'Certificados',
                        content: <SpiritualCertificatesPanel />
                    })
                },
            ]
        },
        {
            title: 'Formación',
            items: [
                { id: 'sl-academy', label: 'Academia CCF', href: '/plataforma/academy', icon: GraduationCap },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Vida Espiritual" sidebarSections={SPIRITUAL_SECTIONS} allowedPermissions={['spiritual_life:read']}>
            {children}
        </WorkspaceLayout>
    );
}

