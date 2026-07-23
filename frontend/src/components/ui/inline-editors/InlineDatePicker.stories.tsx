import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { InlineDatePicker } from './InlineDatePicker';

const meta: Meta<typeof InlineDatePicker> = {
  title: 'UI/Inline DatePicker',
  component: InlineDatePicker,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof InlineDatePicker>;

export const Default: Story = {
  args: {
    value: null,
    onChange: (v) => console.log('Date selected:', v),
  },
};

export const WithDate: Story = {
  args: {
    value: '2026-07-25',
    onChange: (v) => console.log('Date selected:', v),
  },
};

export const Overdue: Story = {
  args: {
    value: '2026-07-20',
    onChange: (v) => console.log('Date selected:', v),
  },
};

export const Disabled: Story = {
  args: {
    value: '2026-08-01',
    onChange: (v) => console.log('Date selected:', v),
    disabled: true,
  },
};