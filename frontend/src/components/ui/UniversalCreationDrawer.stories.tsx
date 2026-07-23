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
  // We'll need to mock the context and API calls for storybook
  decorators: [
    (Story) => {
      // Mock the auth and creation contexts
      const OriginalUseAuth = typeof window !== 'undefined' ? window.useAuth : undefined;
      const OriginalUseCreation = typeof window !== 'undefined' ? window.useCreation : undefined;
      
      // Set up mocks
      if (typeof window !== 'undefined') {
        window.useAuth = () => ({ token: 'fake-token-for-storybook' });
        window.useCreation = () => ({
          setCreationType: () => {},
          setCreationData: () => {},
          creationType: 'task',
          creationData: {},
        });
      }
      
      return <Story />;
    }
  ]
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