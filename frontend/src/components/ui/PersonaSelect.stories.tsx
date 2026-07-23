import type { Meta, StoryObj } from '@storybook/react-webpack5';
import PersonaSelect from './PersonaSelect';

const mockPersonas = [
  {
    id: '1',
    first_name: 'Juan',
    last_name: 'Pérez',
    nombre_completo: 'Juan Pérez',
    church_role: 'Líder de Jóvenes',
    spiritual_status: 'Maduro',
  },
  {
    id: '2',
    first_name: 'María',
    last_name: 'González',
    nombre_completo: 'María González',
    church_role: 'Madre de Célula',
    spiritual_status: 'Maduro',
  },
  {
    id: '3',
    first_name: 'Carlos',
    last_name: 'López',
    nombre_completo: 'Carlos López',
    church_role: 'Ejecutivo',
    spiritual_status: 'En crecimiento',
  },
];

const meta: Meta<typeof PersonaSelect> = {
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