import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { Layers, Search } from 'lucide-react';
import { DSCommandEntry } from './DSCommandEntry';

const meta: Meta<typeof DSCommandEntry> = {
  title: 'Design/CommandEntry',
  component: DSCommandEntry,
  parameters: { layout: 'centered' },
  args: {
    label: 'Ir a CRM Pastoral',
    description: 'Abre el panel de seguimiento y pipeline.',
    shortcut: 'G C',
    icon: Search,
  },
};

export default meta;
type Story = StoryObj<typeof DSCommandEntry>;

export const Base: Story = {};

export const Active: Story = {
  args: {
    active: true,
    label: 'Abrir Projects Inbox',
    shortcut: 'G P',
    icon: Layers,
  },
};
