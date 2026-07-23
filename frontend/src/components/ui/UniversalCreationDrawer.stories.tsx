import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalCreationDrawer from './UniversalCreationDrawer';

// Mock data for the creation drawer
const mockProject: any = {
  id: '1',
  title: 'Proyecto de muestra',
};

const meta: Meta<typeof UniversalCreationDrawer> = {
  title: 'UI/UniversalCreationDrawer',
  component: UniversalCreationDrawer,
  parameters: {
    layout: 'fullscreen',
  },
  // Note: This component requires AuthContext and CreationContext which aren't available in Storybook.
  // This story is for documentation/reference purposes; interactive use requires the full app context.
};

export default meta;
type Story = StoryObj<typeof UniversalCreationDrawer>;

export const Default: Story = {
  args: {
    isOpen: true,
    onClose: () => {
      console.log('Close drawer');
    },
    initialType: 'task',
  },
};

export const ProjectType: Story = {
  args: {
    isOpen: true,
    onClose: () => {
      console.log('Close drawer');
    },
    initialType: 'project',
  },
};

export const EventType: Story = {
  args: {
    isOpen: true,
    onClose: () => {
      console.log('Close drawer');
    },
    initialType: 'event',
  },
};

export const DocumentType: Story = {
  args: {
    isOpen: true,
    onClose: () => {
      console.log('Close drawer');
    },
    initialType: 'doc',
  },
};

export const ClosedState: Story = {
  args: {
    isOpen: false,
    onClose: () => {
      console.log('Close drawer');
    },
    initialType: 'task',
  },
};