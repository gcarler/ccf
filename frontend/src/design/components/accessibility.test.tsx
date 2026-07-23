import React from 'react';
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'jest-axe';

import { DSBadge } from './DSBadge';
import { DSButton } from './DSButton';
import { DSCard } from './DSCard';
import { DSChart } from './DSChart';
import { DSCommandEntry } from './DSCommandEntry';
import { DSInput } from './DSInput';
import { DSMetric } from './DSMetric';
import { DSModal } from './DSModal';
import { DSSectionHeader } from './DSSectionHeader';
import { DSSelect } from './DSSelect';
import { DSSkeleton } from './DSSkeleton';
import { DSTable } from './DSTable';
import { DSTabs } from './DSTabs';
import { DSToast } from './DSToast';
import { DSToolbarChip } from './DSToolbarChip';
import { DSTooltip } from './DSTooltip';

type A11yCase = {
    name: string;
    render: () => React.ReactElement;
};

const cases: A11yCase[] = [
    {
        name: 'DSBadge',
        render: () => <DSBadge label="Badge" tone="blue" />,
    },
    {
        name: 'DSButton',
        render: () => <DSButton>Click me</DSButton>,
    },
    {
        name: 'DSCard',
        render: () => <DSCard>Card content</DSCard>,
    },
    {
        name: 'DSChart',
        render: () => (
            <DSChart
                type="line"
                data={[
                    { label: 'A', value: 10 },
                    { label: 'B', value: 20 },
                ]}
            />
        ),
    },
    {
        name: 'DSCommandEntry',
        render: () => <DSCommandEntry label="Command" shortcut="G C" />,
    },
    {
        name: 'DSInput',
        render: () => <DSInput label="Name" placeholder="Enter name" />,
    },
    {
        name: 'DSMetric',
        render: () => <DSMetric label="Total" value="42" />,
    },
    {
        name: 'DSModal',
        render: () => (
            <DSModal open title="Modal" onClose={() => {}}>
                Modal content
            </DSModal>
        ),
    },
    {
        name: 'DSSectionHeader',
        render: () => <DSSectionHeader title="Section" />,
    },
    {
        name: 'DSSelect',
        render: () => (
            <DSSelect
                label="Option"
                options={[
                    { value: 'a', label: 'A' },
                    { value: 'b', label: 'B' },
                ]}
            />
        ),
    },
    {
        name: 'DSSkeleton',
        render: () => <DSSkeleton className="h-4 w-24" />,
    },
    {
        name: 'DSTable',
        render: () => (
            <DSTable
                data={[{ id: '1', name: 'Alice' }]}
                columns={[
                    {
                        header: 'Name',
                        accessorKey: 'name',
                    },
                ]}
            />
        ),
    },
    {
        name: 'DSTabs',
        render: () => (
            <DSTabs
                tabs={[
                    { id: 'tab1', label: 'Tab 1' },
                    { id: 'tab2', label: 'Tab 2' },
                ]}
            >
                Content
            </DSTabs>
        ),
    },
    {
        name: 'DSToast',
        render: () => <DSToast type="success" message="Saved" />,
    },
    {
        name: 'DSToolbarChip',
        render: () => <DSToolbarChip label="Chip" />,
    },
    {
        name: 'DSTooltip',
        render: () => (
            <DSTooltip content="Tooltip content">
                <span>Trigger</span>
            </DSTooltip>
        ),
    },
];

describe('Design System accessibility', () => {
    it.each(cases)('$name has no accessibility violations', async ({ render: renderComponent }) => {
        const { container } = render(renderComponent());
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
