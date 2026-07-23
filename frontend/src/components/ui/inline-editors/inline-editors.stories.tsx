import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { InlineTextInput } from './InlineTextInput';
import { InlineTextArea } from './InlineTextArea';
import { InlineStatusPicker } from './InlineStatusPicker';
import { InlinePriorityPicker } from './InlinePriorityPicker';

const meta = {
  title: 'UI/Inline Editors',
  parameters: {
    layout: 'centered',
  },
} satisfies Meta;

export default meta;

// ── InlineTextInput ──

export const TextInputDefault: StoryObj<typeof InlineTextInput> = {
  name: 'InlineTextInput - Default',
  render: () => <InlineTextInput value="Juan Pérez" onChange={(v) => console.log(v)} />,
};

export const TextInputEmpty: StoryObj<typeof InlineTextInput> = {
  name: 'InlineTextInput - Empty',
  render: () => <InlineTextInput value="" placeholder="Haz clic para editar..." onChange={(v) => console.log(v)} />,
};

export const TextInputDisabled: StoryObj<typeof InlineTextInput> = {
  name: 'InlineTextInput - Disabled',
  render: () => <InlineTextInput value="Valor bloqueado" disabled onChange={(v) => console.log(v)} />,
};

// ── InlineTextArea ──

export const TextAreaDefault: StoryObj<typeof InlineTextArea> = {
  name: 'InlineTextArea - Default',
  render: () => (
    <InlineTextArea
      value="Descripción detallada de la tarea con información relevante para el equipo."
      onChange={(v) => console.log(v)}
    />
  ),
};

export const TextAreaEmpty: StoryObj<typeof InlineTextArea> = {
  name: 'InlineTextArea - Empty',
  render: () => (
    <InlineTextArea value="" placeholder="Añade una descripción..." onChange={(v) => console.log(v)} rows={4} />
  ),
};

export const TextAreaDisabled: StoryObj<typeof InlineTextArea> = {
  name: 'InlineTextArea - Disabled',
  render: () => (
    <InlineTextArea value="Descripción bloqueada" disabled onChange={(v) => console.log(v)} />
  ),
};

// ── InlineStatusPicker ──

export const StatusPickerDefault: StoryObj<typeof InlineStatusPicker> = {
  name: 'InlineStatusPicker - Default',
  render: () => <InlineStatusPicker value="in_progress" onChange={(v) => console.log(v)} />,
};

export const StatusPickerSmall: StoryObj<typeof InlineStatusPicker> = {
  name: 'InlineStatusPicker - Small',
  render: () => <InlineStatusPicker value="todo" onChange={(v) => console.log(v)} size="sm" />,
};

export const StatusPickerAll: StoryObj<typeof InlineStatusPicker> = {
  name: 'InlineStatusPicker - All States',
  render: () => (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      <InlineStatusPicker value="todo" onChange={(v) => console.log(v)} />
      <InlineStatusPicker value="in_progress" onChange={(v) => console.log(v)} />
      <InlineStatusPicker value="review" onChange={(v) => console.log(v)} />
      <InlineStatusPicker value="completed" onChange={(v) => console.log(v)} />
    </div>
  ),
};

// ── InlinePriorityPicker ──

export const PriorityPickerDefault: StoryObj<typeof InlinePriorityPicker> = {
  name: 'InlinePriorityPicker - Default',
  render: () => <InlinePriorityPicker value="high" onChange={(v) => console.log(v)} />,
};

export const PriorityPickerSmall: StoryObj<typeof InlinePriorityPicker> = {
  name: 'InlinePriorityPicker - Small',
  render: () => <InlinePriorityPicker value="medium" onChange={(v) => console.log(v)} size="sm" />,
};

export const PriorityPickerAll: StoryObj<typeof InlinePriorityPicker> = {
  name: 'InlinePriorityPicker - All Levels',
  render: () => (
    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
      <InlinePriorityPicker value="low" onChange={(v) => console.log(v)} />
      <InlinePriorityPicker value="medium" onChange={(v) => console.log(v)} />
      <InlinePriorityPicker value="high" onChange={(v) => console.log(v)} />
      <InlinePriorityPicker value="urgent" onChange={(v) => console.log(v)} />
    </div>
  ),
};