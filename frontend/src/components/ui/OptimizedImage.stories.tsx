import type { Meta, StoryObj } from '@storybook/react-webpack5';
import OptimizedImage from './OptimizedImage';


const meta: Meta<typeof OptimizedImage> = {
  tags: ['autodocs'],
  title: 'UI/OptimizedImage',
  component: OptimizedImage,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof OptimizedImage>;

const sampleSrc = 'data:image/svg+xml,%3Csvg%20xmlns=%22http://www.w3.org/2000/svg%22%20width=%22300%22%20height=%22200%22%3E%3Crect%20width=%22300%22%20height=%22200%22%20fill=%22%23018abd%22/%3E%3Ctext%20x=%22150%22%20y=%22110%22%20font-size=%2220%22%20fill=%22white%22%20text-anchor=%22middle%22%3EImagen%20de%20ejemplo%3C/text%3E%3C/svg%3E';

export const Default: Story = {
  args: {
    src: sampleSrc,
    alt: 'Imagen de ejemplo',
    width: 300,
    height: 200,
  },
};

export const WithFill: Story = {
  args: {
    src: sampleSrc,
    alt: 'Imagen con fill',
    fill: true,
    sizes: '100vw',
    className: 'w-64 h-40 rounded-lg',
  },
  render: (args) => (
    <div className="relative w-64 h-40">
      <OptimizedImage {...args} />
    </div>
  ),
};

export const Fallback: Story = {
  args: {
    src: '',
    alt: 'Imagen no disponible',
    width: 300,
    height: 200,
    className: 'rounded-lg',
  },
};

export const ObjectContain: Story = {
  args: {
    src: sampleSrc,
    alt: 'Imagen con object-contain',
    width: 300,
    height: 200,
    objectFit: 'contain',
    className: 'bg-[hsl(var(--surface-2))] rounded-lg',
  },
};
