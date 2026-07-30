"use client";


import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { Bell, AtSign, CheckCircle2, Bot, MessageSquare } from 'lucide-react';

const INBOX_SECTIONS = [
    {
        title: 'Módulos',
        items: [
            { id: 'inbox-all',      label: 'Todo',      href: '/plataforma/inbox',           icon: Bell },
            { id: 'inbox-mentions', label: 'Menciones', href: '/plataforma/inbox#menciones', icon: AtSign },
            { id: 'inbox-tasks',    label: 'Tareas',    href: '/plataforma/inbox#tareas',    icon: CheckCircle2 },
            { id: 'inbox-ai',       label: 'MESH AI',   href: '/plataforma/inbox#ai',        icon: Bot },                { id: 'inbox-messages', label: 'Mensajes',  href: '/plataforma/inbox/messages',  icon: MessageSquare },
                { id: 'inbox-chat',       label: 'Chat directo', href: '/plataforma/inbox/chat',       icon: MessageSquare },

        ],
    },
    {
        title: 'Comentarios',
        items: [
            { id: 'inbox-comments-created', label: 'Mis comentarios', href: '/plataforma/inbox/comments?tab=created',  icon: MessageSquare },
            { id: 'inbox-comments-mentions', label: 'Menciones',      href: '/plataforma/inbox/comments?tab=mentions', icon: AtSign },
        ],
    },
];

export default function InboxLayout({ children }: { children: React.ReactNode }) {
    return (
        <ModuleErrorBoundary moduleName="Bandeja de Entrada">
            <WorkspaceLayout sidebarTitle="Bandeja de Entrada" sidebarSections={INBOX_SECTIONS} allowedPermissions={['messaging:read']}>
                {children}
            </WorkspaceLayout>
        </ModuleErrorBoundary>
    );
}

