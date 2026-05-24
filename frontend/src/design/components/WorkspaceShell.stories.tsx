import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { Bell, Search, Settings } from 'lucide-react';
import { DSCard } from './DSCard';
import { DSSectionHeader } from './DSSectionHeader';
import { DSToolbarChip } from './DSToolbarChip';
import { DSMetric } from './DSMetric';
import { DSCommandEntry } from './DSCommandEntry';

const meta: Meta = {
  title: 'Design/Layouts/WorkspaceShell',
  parameters: { layout: 'fullscreen' },
};

export default meta;
type Story = StoryObj;

export const Preview: Story = {
  render: () => (
    <div className="min-h-screen bg-slate-100 p-3 md:p-4">
      <div className="mx-auto max-w-6xl space-y-3">
        <DSCard tone="light" className="p-4 md:p-3">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <DSToolbarChip label="CRM" active />
              <DSToolbarChip label="Projects" variant="soft" />
              <DSToolbarChip label="Academy" variant="soft" />
            </div>
            <div className="flex items-center gap-2">
              <DSToolbarChip label="Buscar" icon={Search} size="sm" />
              <DSToolbarChip label="Inbox" icon={Bell} size="sm" />
              <DSToolbarChip label="Settings" icon={Settings} size="sm" />
            </div>
          </div>
        </DSCard>

        <div className="grid grid-cols-1 gap-3 lg:grid-cols-12">
          <DSCard tone="light" className="space-y-4 lg:col-span-4">
            <DSSectionHeader eyebrow="Command" title="Quick Actions" description="Entradas del command palette listas para integracion." />
            <div className="space-y-2">
              <DSCommandEntry label="Ir a CRM Pastoral" shortcut="G C" active description="Pipeline, miembros y seguimiento." />
              <DSCommandEntry label="Abrir Projects" shortcut="G P" description="Tableros de tareas y recursos." />
              <DSCommandEntry label="Ver Academy" shortcut="G A" description="Cursos, progreso y certificados." />
            </div>
          </DSCard>

          <div className="grid grid-cols-1 gap-3 lg:col-span-8 md:grid-cols-3">
            <DSMetric label="TTFB" value="56 ms" trend="baseline" tone="blue" />
            <DSMetric label="LCP" value="2.86 s" trend="projects" tone="amber" />
            <DSMetric label="Graph Nodes" value="120" trend="snapshot" tone="emerald" />
          </div>
        </div>
      </div>
    </div>
  ),
};
