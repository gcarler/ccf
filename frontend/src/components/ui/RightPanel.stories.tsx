import type { Meta, StoryObj } from '@storybook/react-webpack5';
import RightPanel from './RightPanel';


const meta: Meta<typeof RightPanel> = {
  tags: ['autodocs'],
  title: 'UI/RightPanel',
  component: RightPanel,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    (Story) => (
      <div className="w-full h-[400px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-elevated))] relative overflow-hidden">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof RightPanel>;

export const Default: Story = {
  args: {
    title: 'Actividad',
    open: true,
    onClose: () => console.log('Close panel'),
    width: 320,
    children: (
      <div className="p-4 space-y-3">
        <div className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
          <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">Juan Pérez</p>
          <p className="text-[10px] text-[hsl(var(--text-secondary))]">Se unió al grupo &quot;Jóvenes&quot;</p>
        </div>
        <div className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
          <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">María González</p>
          <p className="text-[10px] text-[hsl(var(--text-secondary))]">Completó la lección 5</p>
        </div>
        <div className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
          <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">Carlos López</p>
          <p className="text-[10px] text-[hsl(var(--text-secondary))]">Actualizó su perfil</p>
        </div>
      </div>
    ),
  },
};

export const WidePanel: Story = {
  args: {
    title: 'Historial completo',
    open: true,
    onClose: () => console.log('Close panel'),
    width: 480,
    children: (
      <div className="p-4 space-y-3">
        <div className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10">
          <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">Cambio reciente</p>
          <p className="text-[10px] text-[hsl(var(--text-secondary))]">Detalles adicionales del cambio realizado en el sistema</p>
        </div>
      </div>
    ),
  },
};

export const WithTrigger: Story = {
  args: {
    title: 'Notificaciones',
    open: true,
    onClose: () => console.log('Close panel'),
    width: 320,
    showTrigger: true,
    trigger: <button className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded-lg text-xs font-bold">Mostrar panel</button>,
    children: (
      <div className="p-4">
        <p className="text-xs text-[hsl(var(--text-secondary))]">Contenido del panel con trigger visible.</p>
      </div>
    ),
  },
};

export const EmptyContent: Story = {
  args: {
    title: 'Sin contenido',
    open: true,
    onClose: () => console.log('Close panel'),
    width: 320,
    children: (
      <div className="p-4 text-center">
        <p className="text-xs text-[hsl(var(--text-secondary))]">No hay actividad reciente.</p>
      </div>
    ),
  },
};