import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
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
});
