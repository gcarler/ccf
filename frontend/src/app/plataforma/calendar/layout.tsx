"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import {
  CalendarDays, Calendar, ListTodo, HelpCircle,
  Megaphone, Users, FolderKanban, User, Cake,
} from 'lucide-react';

const SIDEBAR_SECTIONS = [
  {
    title: 'Vistas',
    items: [
      {
        id: 'todo',
        label: 'Todo',
        icon: CalendarDays,
        href: '/plataforma/calendar',
      },
      {
        id: 'evangelismo',
        label: 'Evangelismo',
        icon: Megaphone,
        href: '/plataforma/calendar?view=evangelismo',
      },
      {
        id: 'crm',
        label: 'Consolidación',
        icon: Users,
        href: '/plataforma/calendar?view=crm',
      },
      {
        id: 'proyectos',
        label: 'Proyectos',
        icon: FolderKanban,
        href: '/plataforma/calendar?view=proyectos',
      },
      {
        id: 'personal',
        label: 'Personal',
        icon: User,
        href: '/plataforma/calendar?view=personal',
      },
      {
        id: 'cumpleanos',
        label: 'Cumpleaños',
        icon: Cake,
        href: '/plataforma/calendar?view=cumpleanos',
      },
    ],
  },
  {
    title: 'Módulos',
    items: [
      {
        id: 'agenda',
        label: 'Agenda',
        icon: Calendar,
        href: '/plataforma/agenda/events',
      },
      {
        id: 'tasks',
        label: 'Tareas',
        icon: ListTodo,
        href: '/plataforma/tasks',
      },
      {
        id: 'help',
        label: 'Ayuda',
        icon: HelpCircle,
        href: '/plataforma/support',
      },
    ],
  },
];

export default function CalendarLayout({ children }: { children: React.ReactNode }) {
  return (
    <ModuleErrorBoundary moduleName="Calendario">
      <WorkspaceLayout
        sidebarTitle="Calendario"
        sidebarSections={SIDEBAR_SECTIONS}
      >
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] h-full flex overflow-hidden">
          {children}
        </div>
      </WorkspaceLayout>
    </ModuleErrorBoundary>
  );
}
