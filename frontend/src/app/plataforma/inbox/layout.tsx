"use client";


import WorkspaceLayout from '@/components/WorkspaceLayout';
import { Bell, AtSign, CheckCircle2, Bot, MessageSquare } from 'lucide-react';

const INBOX_SECTIONS = [
    {
        title: 'Módulos',
        items: [
            { id: 'inbox-all',      label: 'Todo',      href: '/inbox',           icon: Bell },
            { id: 'inbox-mentions', label: 'Menciones', href: '/inbox#menciones', icon: AtSign },
            { id: 'inbox-tasks',    label: 'Tareas',    href: '/inbox#tareas',    icon: CheckCircle2 },
            { id: 'inbox-ai',       label: 'MESH AI',   href: '/inbox#ai',        icon: Bot },
            { id: 'inbox-messages', label: 'Mensajes',  href: '/inbox/messages',  icon: MessageSquare },
        ],
    },
];

export default function InboxLayout({ children }: { children: React.ReactNode }) {
    return (
        <WorkspaceLayout sidebarTitle="Bandeja de Entrada" sidebarSections={INBOX_SECTIONS}>
            {children}
        </WorkspaceLayout>
    );
}

