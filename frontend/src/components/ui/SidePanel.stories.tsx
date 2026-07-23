import type { Meta, StoryObj } from '@storybook/react-webpack5';
import SidePanel from './SidePanel';


const meta: Meta<typeof SidePanel> = {
  tags: ['autodocs'],
  title: 'UI/SidePanel',
  component: SidePanel,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    (Story) => (
      <div className="w-full h-[500px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-elevated))] relative overflow-hidden">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof SidePanel>;

export const Default: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log('Close'),
    title: 'Detalles de Persona',
    subtitle: 'Información completa de la persona',
    children: (
      <div className="space-y-3 p-1">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5">
          <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] w-24">Nombre:</span>
          <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">Juan Pérez</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5">
          <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] w-24">Email:</span>
          <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">juan@ejemplo.com</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5">
          <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] w-24">Rol:</span>
          <span className="text-[11px] font-semibold text-[hsl(var(--text-primary))] dark:text-white">Líder de Jóvenes</span>
        </div>
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5">
          <span className="text-[11px] font-semibold text-[hsl(var(--text-secondary))] w-24">Estado:</span>
          <span className="text-[11px] font-semibold text-[hsl(var(--success))]">Activo</span>
        </div>
      </div>
    ),
  },
};

export const WithNavigation: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log('Close'),
    title: 'Tarea #42',
    subtitle: 'Preparar informe mensual',
    onPrev: () => console.log('Previous'),
    onNext: () => console.log('Next'),
    children: (
      <div className="p-1">
        <p className="text-xs text-[hsl(var(--text-secondary))]">Contenido con navegación entre elementos.</p>
      </div>
    ),
  },
};

export const WithExternalLink: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log('Close'),
    title: 'Vista completa disponible',
    subtitle: 'Panel con enlace a vista completa',
    fullViewHref: '/plataforma/detalle',
    children: (
      <div className="p-1">
        <p className="text-xs text-[hsl(var(--text-secondary))]">Este panel tiene un enlace de vista completa en la cabecera.</p>
      </div>
    ),
  },
};

export const CustomWidth: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log('Close'),
    title: 'Panel ancho',
    subtitle: '600px de ancho',
    width: 'w-[600px]',
    children: (
      <div className="p-1">
        <p className="text-xs text-[hsl(var(--text-secondary))]">Panel más ancho para contenido extenso.</p>
      </div>
    ),
  },
};

export const LongContent: Story = {
  args: {
    isOpen: true,
    onClose: () => console.log('Close'),
    title: 'Registro de cambios',
    subtitle: 'Historial de modificaciones',
    children: (
      <div className="space-y-2 p-1">
        {Array.from({ length: 15 }, (_, i) => (
          <div key={i} className="px-3 py-2 rounded-lg bg-[hsl(var(--surface-1))] dark:bg-white/5">
            <p className="text-xs font-semibold text-[hsl(var(--text-primary))] dark:text-white">Cambio #{i + 1}</p>
            <p className="text-[10px] text-[hsl(var(--text-secondary))]">Descripción del cambio realizado en el sistema.</p>
          </div>
        ))}
      </div>
    ),
  },
};