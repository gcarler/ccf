import type { Meta, StoryObj } from '@storybook/react-webpack5';
import PersonaSelect from './PersonaSelect';

const meta: Meta<typeof PersonaSelect> = {
  tags: ['autodocs'],
  title: 'UI/PersonaSelect',
  component: PersonaSelect,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof PersonaSelect>;

export const Default: Story = {
  args: {
    value: '2',
    onChange: (value) => {
      console.log('Selected persona ID:', value);
    },
    placeholder: 'Seleccione una persona',
    showMetadata: true,
  },
};

export const WithPlaceholder: Story = {
  args: {
    value: null,
    onChange: (value) => {
      console.log('Selected persona ID:', value);
    },
    placeholder: 'Seleccione un líder de célula',
    showMetadata: true,
  },
};

export const WithoutMetadata: Story = {
  args: {
    value: '1',
    onChange: (value) => {
      console.log('Selected persona ID:', value);
    },
    placeholder: 'Seleccione una persona',
    showMetadata: false,
  },
};

export const ClearSelection: Story = {
  args: {
    value: null,
    onChange: (value) => {
      console.log('Selected persona ID:', value);
    },
    placeholder: 'Seleccione una persona',
    showMetadata: true,
  },
};

export const Disabled: Story = {
  args: {
    value: '2',
    onChange: (value) => {
      console.log('Selected persona ID:', value);
    },
    placeholder: 'Seleccione una persona',
    showMetadata: true,
  },
  // Note: PersonaSelect doesn't have a disabled prop, so we demonstrate
  // how it would look in a disabled context by wrapping it
  render: (args) => (
    <div className="pointer-events-none opacity-50">
      <PersonaSelect {...args} />
    </div>
  ),
};