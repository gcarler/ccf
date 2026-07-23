import type { Meta, StoryObj } from '@storybook/react-webpack5';
import Tooltip from './Tooltip';


const meta: Meta<typeof Tooltip> = {
  tags: ['autodocs'],
  title: 'UI/Tooltip',
  component: Tooltip,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof Tooltip>;

export const Default: Story = {
  args: {
    children: 'Pasa el cursor sobre mí',
    content: 'Este es un tooltip de ejemplo',
  },
};

export const Positions: Story = {
  args: {
    children: 'Posición',
    content: 'Tooltip position',
  },
  render: (args) => (
    <div style={{ display: 'flex', gap: '2rem' }}>
      <Tooltip {...args} side="top">
        Top
      </Tooltip>
      <Tooltip {...args} side="right">
        Right
      </Tooltip>
      <Tooltip {...args} side="bottom">
        Bottom
      </Tooltip>
      <Tooltip {...args} side="left">
        Left
      </Tooltip>
    </div>
  ),
};

export const WithButton: Story = {
  args: {
    children: (
      <button className="px-4 py-2 bg-[hsl(var(--primary))] text-white rounded hover:bg-[hsl(var(--primary))]/90 transition-colors">
        Botón con tooltip
      </button>
    ),
    content: 'Esta es una descripción detallada del botón',
    side: 'top',
  },
};

export const WithIcon: Story = {
  args: {
    children: (
      <span className="inline-flex items-center justify-center w-10 h-10 bg-[hsl(var(--primary))] text-white rounded-full">
        <i className="fas fa-cog" />
      </span>
    ),
    content: 'Información de configuración',
    side: 'bottom',
  },
};

export const LongContent: Story = {
  args: {
    children: 'Texto largo',
    content: 'Este es un tooltip con contenido mucho más largo que demostrará cómo se comporta cuando tiene que mostrar múltiples líneas de texto. Puede ser útil para proporcionar ayuda contextual más detallada.',
    side: 'right',
  },
};