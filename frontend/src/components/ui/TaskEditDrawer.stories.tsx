import type { Meta, StoryObj } from '@storybook/react-webpack5';
import TaskEditDrawer from './TaskEditDrawer';


const meta: Meta<typeof TaskEditDrawer> = {
  tags: ['autodocs'],
  title: 'UI/TaskEditDrawer',
  component: TaskEditDrawer,
  parameters: {
    layout: 'centered',
  },
};

export default meta;
type Story = StoryObj<typeof TaskEditDrawer>;

const sampleTask = {
  id: 'task-001',
  title: 'Revisar propuesta de proyecto',
  status: 'in_progress',
  priority: 'high',
  due_date: '2026-07-30',
  project_id: 'proj-123',
  project_title: 'Plataforma CCF',
  description: 'Analizar alcance, costos y cronograma entregados por el cliente.',
  done: false,
};

export const Default: Story = {
  args: {
    task: sampleTask,
    onClose: () => {},
    onTaskUpdated: () => {},
    onTaskDeleted: () => {},
  },
};

export const EmptyTask: Story = {
  args: {
    task: null,
    onClose: () => {},
    onTaskUpdated: () => {},
    onTaskDeleted: () => {},
  },
};
