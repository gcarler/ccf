import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import { DSTabs } from './DSTabs';

const sampleTabs = [
    { id: 'tab1', label: 'Tab 1' },
    { id: 'tab2', label: 'Tab 2' },
    { id: 'tab3', label: 'Tab 3' },
];

describe('DSTabs', () => {
    it('renders all tabs', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Content</div>
            </DSTabs>
        );
        expect(screen.getByText('Tab 1')).toBeInTheDocument();
        expect(screen.getByText('Tab 2')).toBeInTheDocument();
        expect(screen.getByText('Tab 3')).toBeInTheDocument();
    });

    it('renders first tab as active by default', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Content</div>
            </DSTabs>
        );
        const tab1 = screen.getByText('Tab 1');
        expect(tab1).toHaveAttribute('aria-selected', 'true');
    });

    it('switches tab on click', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Content</div>
            </DSTabs>
        );

        fireEvent.click(screen.getByText('Tab 2'));
        const tab2 = screen.getByText('Tab 2');
        expect(tab2).toHaveAttribute('aria-selected', 'true');
    });

    it('calls onChange when tab is clicked', () => {
        const handleChange = vi.fn();
        render(
            <DSTabs tabs={sampleTabs} onChange={handleChange}>
                <div>Content</div>
            </DSTabs>
        );

        fireEvent.click(screen.getByText('Tab 2'));
        expect(handleChange).toHaveBeenCalledWith('tab2');
    });

    it('renders with default tab', () => {
        render(
            <DSTabs tabs={sampleTabs} defaultTab="tab2">
                <div>Content</div>
            </DSTabs>
        );
        const tab2 = screen.getByText('Tab 2');
        expect(tab2).toHaveAttribute('aria-selected', 'true');
    });

    it('renders tab with icon', () => {
        const TestIcon = () => <span data-testid="icon">Icon</span>;
        render(
            <DSTabs tabs={[{ id: 'tab1', label: 'Tab', icon: TestIcon }]}>
                <div>Content</div>
            </DSTabs>
        );
        expect(screen.getByTestId('icon')).toBeInTheDocument();
    });

    it('disables tab when disabled prop is true', () => {
        render(
            <DSTabs tabs={[{ id: 'tab1', label: 'Tab', disabled: true }]}>
                <div>Content</div>
            </DSTabs>
        );
        const tab = screen.getByText('Tab');
        expect(tab).toBeDisabled();
    });

    it('has correct aria attributes', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Content</div>
            </DSTabs>
        );

        const tablist = screen.getByRole('tablist');
        expect(tablist).toHaveAttribute('aria-orientation', 'horizontal');

        const tab1 = screen.getByText('Tab 1');
        expect(tab1).toHaveAttribute('role', 'tab');
        expect(tab1).toHaveAttribute('aria-controls', 'panel-tab1');
        expect(tab1).toHaveAttribute('id', 'tab-tab1');
    });

    it('renders tab panels', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Panel Content</div>
            </DSTabs>
        );

        const panel = screen.getByRole('tabpanel');
        expect(panel).toHaveAttribute('id', 'panel-tab1');
        expect(panel).toHaveAttribute('aria-labelledby', 'tab-tab1');
    });

    it('has no accessibility violations', async () => {
        const { container } = render(
            <DSTabs tabs={sampleTabs}>
                <div>Content</div>
            </DSTabs>
        );
        expect(await axe(container)).toHaveNoViolations();
    });

    it('renders distinct content per tab when panels prop is provided', () => {
        render(
            <DSTabs tabs={sampleTabs} panels={{ tab1: <div>Tab 1 Content</div>, tab2: <div>Tab 2 Content</div>, tab3: <div>Tab 3 Content</div> }} />
        );
        expect(screen.getByText('Tab 1 Content')).toBeInTheDocument();
        expect(screen.queryByText('Tab 2 Content')).not.toBeInTheDocument();
        expect(screen.queryByText('Tab 3 Content')).not.toBeInTheDocument();

        fireEvent.click(screen.getByText('Tab 2'));
        expect(screen.getByText('Tab 2 Content')).toBeInTheDocument();
    });

    it('uses renderPanel to compute panel content on the fly', () => {
        render(
            <DSTabs tabs={sampleTabs} renderPanel={(id) => <div>Rendered: {id}</div>} />
        );
        expect(screen.getByText('Rendered: tab1')).toBeInTheDocument();

        fireEvent.click(screen.getByText('Tab 3'));
        expect(screen.getByText('Rendered: tab3')).toBeInTheDocument();
    });

    it('falls back to children (compatibilidad con API anterior) when neither panels nor renderPanel are passed', () => {
        render(
            <DSTabs tabs={sampleTabs}>
                <div>Shared Content</div>
            </DSTabs>
        );
        expect(screen.getByText('Shared Content')).toBeInTheDocument();
    });
});
