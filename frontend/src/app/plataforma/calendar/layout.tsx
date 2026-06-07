"use client";

import React from 'react';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { ModuleErrorBoundary } from '@/components/ModuleErrorBoundary';
import { CalendarDays, Calendar, ListTodo, HelpCircle } from 'lucide-react';

const SIDEBAR_SECTIONS = [
  {
    title: 'Planificación',
    items: [
      {
        id: 'calendar',
        label: 'Calendario',
        icon: CalendarDays,
        href: '/plataforma/calendar',
      },
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
    ],
  },
  {
    title: 'Soporte',
    items: [
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
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] h-full">
          {children}
        </div>
      </WorkspaceLayout>
    </ModuleErrorBoundary>
  );
}
