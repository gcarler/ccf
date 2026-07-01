import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSSkeleton } from './DSSkeleton';

const meta: Meta<typeof DSSkeleton> = {
    title: 'Design/Skeleton',
    component: DSSkeleton,
    parameters: { layout: 'centered' },
    argTypes: {
        rounded: {
            control: 'select',
            options: ['sm', 'md', 'lg', 'xl', 'pill', 'none'],
        },
    },
};

export default meta;
type Story = StoryObj<typeof DSSkeleton>;

export const Line: Story = {
    args: { rounded: 'pill', className: 'h-4 w-64' },
};

export const Circle: Story = {
    args: { rounded: 'pill', className: 'size-10' },
};

export const Card: Story = {
    args: { rounded: 'lg', className: 'h-32 w-48' },
};

export const ProfileSkeleton: Story = {
    render: () => (
        <div className="flex items-center gap-4">
            <DSSkeleton rounded="pill" className="size-10" />
            <div className="space-y-2">
                <DSSkeleton rounded="pill" className="h-4 w-40" />
                <DSSkeleton rounded="pill" className="h-3 w-28" />
            </div>
        </div>
    ),
};

export const CardSkeleton: Story = {
    render: () => (
        <div className="w-64 space-y-3">
            <DSSkeleton rounded="lg" className="h-32 w-full" />
            <DSSkeleton rounded="pill" className="h-4 w-3/4" />
            <DSSkeleton rounded="pill" className="h-3 w-1/2" />
        </div>
    ),
};
