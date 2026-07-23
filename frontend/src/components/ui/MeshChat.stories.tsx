import type { Meta, StoryObj } from '@storybook/react-webpack5';
import MeshChat from './MeshChat';


const meta: Meta<typeof MeshChat> = {
  tags: ['autodocs'],
  title: 'UI/MeshChat',
  component: MeshChat,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof MeshChat>;

export const Open: Story = {
  args: {
    isOpen: true,
    onClose: () => {},
  },
};

export const Closed: Story = {
  args: {
    isOpen: false,
    onClose: () => {},
  },
};
