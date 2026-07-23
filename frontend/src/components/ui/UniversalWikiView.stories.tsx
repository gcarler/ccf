import type { Meta, StoryObj } from '@storybook/react-webpack5';
import UniversalWikiView from './UniversalWikiView';

const meta: Meta<typeof UniversalWikiView> = {
  title: 'UI/UniversalWikiView',
  component: UniversalWikiView,
  parameters: {
    layout: 'padded',
  },
};

export default meta;
type Story = StoryObj<typeof UniversalWikiView>;

export const Default: Story = {
  args: {
    moduleName: 'Finanzas',
    storageKey: 'wiki_finanzas',
  },
};

export const Academy: Story = {
  args: {
    moduleName: 'Academia',
    storageKey: 'wiki_academy',
  },
};

export const Evangelism: Story = {
  args: {
    moduleName: 'Evangelismo',
    storageKey: 'wiki_evangelism',
  },
};

export const WithSave: Story = {
  args: {
    moduleName: 'Notas',
    storageKey: 'wiki_notas',
    onSave: (content: string) => console.log('Saved:', content),
  },
};