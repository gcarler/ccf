import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSToast } from './DSToast';
import { toast } from '@/design';

const meta: Meta<typeof DSToast> = {
  title: 'Design/DSToast',
  component: DSToast,
  parameters: {
    layout: 'centered',
  },
  argTypes: {
    type: {
      control: { type: 'select' },
      options: ['success', 'error', 'warning', 'info'],
    },
    message: { control: 'text' },
  },
};

export default meta;
type Story = StoryObj<typeof DSToast>;

export const Default: Story = {
  args: {
    type: 'success',
    message: 'Operación completada exitosamente',
  },
};

export const Error: Story = {
  args: {
    type: 'error',
    message: 'Ocurrió un error al procesar la solicitud',
  },
};

export const Warning: Story = {
  args: {
    type: 'warning',
    message: 'Esta acción requiere confirmación',
  },
};

export const Info: Story = {
  args: {
    type: 'info',
    message: 'Información importante sobre el sistema',
  },
};

export const WithAction: Story = {
  args: {
    type: 'success',
    message: 'Tarea completada',
    action: {
      label: 'Ver detalle',
      onClick: () => {
        // Action handler
        alert('Ver detalle clicked');
      },
    },
  },
};

export const WithCloseButton: Story = {
  args: {
    type: 'info',
    message: 'Notificación con botón de cerrar',
    onClose: () => {
      // Close handler
      alert('Toast closed');
    },
  },
};

// Story for demonstrating the toast function
export const ToastFunction: Story = {
  render: () => (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
      <button 
        onClick={() => toast.success('Éxito: Operación completada')}
        className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded hover:bg-[hsl(var(--primary))]/90 transition-colors"
      >
        Success Toast
      </button>
      <button 
        onClick={() => toast.error('Error: Algo salió mal')}
        className="px-4 py-2 bg-[hsl(var(--danger))] text-white rounded hover:bg-[hsl(var(--danger))]/90 transition-colors"
      >
        Error Toast
      </button>
      <button 
        onClick={() => toast.warning('Advertencia: Verifique los datos')}
        className="px-4 py-2 bg-[hsl(var(--amber)-500)] text-white rounded hover:bg-[hsl(var(--amber)-500)]/90 transition-colors"
      >
        Warning Toast
      </button>
      <button 
        onClick={() => toast.info('Información: Nueva versión disponible')}
        className="px-4 py-2 bg-[hsl(var(--blue)-500)] text-white rounded hover:bg-[hsl(var(--blue)-500)]/90 transition-colors"
      >
        Info Toast
      </button>
    </div>
  ),
};