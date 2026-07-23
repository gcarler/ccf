import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TextPromptDrawer from './TextPromptDrawer';

const meta: Meta<typeof TextPromptDrawer> = {
  title: 'UI/TextPromptDrawer',
  component: TextPromptDrawer,
  parameters: {
    layout: 'fullscreen',
  },
};

export default meta;
type Story = StoryObj<typeof TextPromptDrawer>;

export const Default: Story = {
  args: {
    isOpen: true,
    title: 'Nueva Tarea',
    subtitle: 'Ingrese el nombre de la tarea a crear',
    label: 'Nombre de la tarea',
    value: '',
    onChange: (value: string) => console.log('Changed:', value),
    onClose: () => console.log('Closed'),
    onSubmit: () => console.log('Submitted'),
    placeholder: 'Ej: Preparar informe mensual',
    submitLabel: 'Guardar',
    cancelLabel: 'Cancelar',
  },
};

export const WithExistingValue: Story = {
  args: {
    isOpen: true,
    title: 'Editar nombre',
    subtitle: 'Modifique el nombre de la tarea',
    label: 'Nombre',
    value: 'Preparar informe mensual de finanzas',
    onChange: (value: string) => console.log('Changed:', value),
    onClose: () => console.log('Closed'),
    onSubmit: () => console.log('Submitted'),
    placeholder: 'Nombre de la tarea',
    submitLabel: 'Actualizar',
    cancelLabel: 'Cancelar',
  },
};

export const EmailInput: Story = {
  args: {
    isOpen: true,
    title: 'Agregar correo',
    subtitle: 'Ingrese el correo electrónico del destinatario',
    label: 'Correo electrónico',
    value: '',
    onChange: (value: string) => console.log('Changed:', value),
    onClose: () => console.log('Closed'),
    onSubmit: () => console.log('Submitted'),
    placeholder: 'correo@ejemplo.com',
    submitLabel: 'Enviar',
    cancelLabel: 'Cancelar',
    inputType: 'email',
  },
};

export const ClosedState: Story = {
  args: {
    isOpen: false,
    title: 'Drawer cerrado',
    subtitle: '',
    label: '',
    value: '',
    onChange: () => {},
    onClose: () => {},
    onSubmit: () => {},
    submitLabel: 'Guardar',
    cancelLabel: 'Cancelar',
  },
};