import type { Meta, StoryObj } from '@storybook/react-webpack5';
import EmptyState from './EmptyState';
import { Ghost, Plus, CheckCircle, AlertTriangle, Info } from 'lucide-react';

const meta: Meta<typeof EmptyState> = {
  title: 'UI/EmptyState',
  component: EmptyState,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

export const Default: Story = {
  args: {
    title: 'No hay datos disponibles',
    description: 'No se encontraron registros que coincidan con los criterios de búsqueda.',
  },
};

export const WithAction: Story = {
  args: {
    title: 'No hay tareas pendientes',
    description: 'Cree una nueva tarea para comenzar a trabajar en sus proyectos.',
    actionLabel: 'Nueva Tarea',
    onAction: () => {
      alert('Crear nueva tarea clicked');
    },
    icon: Plus,
  },
};

export const WithDifferentIcons: Story = {
  args: {
    title: 'Estado del sistema',
    description: 'Todos los servicios están funcionando correctamente.',
  },
  // This will show different icons based on context - we'll demonstrate with overrides
};

export const SuccessState: Story = {
  args: {
    title: 'Todo completado',
    description: 'No hay tareas pendientes en este momento.',
    icon: CheckCircle,
  },
};

export const WarningState: Story = {
  args: {
    title: 'Atención requerida',
    description: 'Hay elementos que necesitan su revisión.',
    icon: AlertTriangle,
  },
};

export const InfoState: Story = {
  args: {
    title: 'Información del sistema',
    description: 'Versión actual: v2.1.0 - Última actualización: hoy',
    icon: Info,
  },
};

export const CustomSize: Story = {
  args: {
    title: 'Perfil incompleto',
    description: 'Complete su información para acceder a todas las funciones.',
  },
  render: (args) => (
    <div style={{ textAlign: 'center', maxWidth: '400px' }}>
      <EmptyState {...args} className="w-full" />
    </div>
  ),
};