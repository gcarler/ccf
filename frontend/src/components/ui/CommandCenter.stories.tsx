import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { CommandCenter } from './CommandCenter';

const meta: Meta<typeof CommandCenter> = {
  title: 'UI/CommandCenter',
  component: CommandCenter,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    (Story) => {
      if (typeof window !== 'undefined') {
        (window as any).useCommandCenter = () => ({
          commands: [],
        });
        (window as any).useCreation = () => ({
          openModal: () => {},
        });
        (window as any).useAuth = () => ({
          token: 'fake-token',
        });
        (window as any).useRouter = () => ({
          push: (path: string) => console.log('Navigate:', path),
        });
      }
      return (
        <div className="w-full h-[600px] bg-[hsl(var(--bg-primary))] dark:bg-[#0a0f16] flex items-center justify-center">
          <p className="text-xs text-[hsl(var(--text-secondary))]">Presiona Ctrl+K para abrir la paleta de comandos</p>
          <Story />
        </div>
      );
    },
  ],
};

export default meta;
type Story = StoryObj<typeof CommandCenter>;

export const Default: Story = {
  args: {},
};