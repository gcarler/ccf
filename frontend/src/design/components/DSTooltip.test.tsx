import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { axe } from 'jest-axe';
import { DSTooltip } from './DSTooltip';

describe('DSTooltip', () => {
    it('renders children', () => {
        render(
            <DSTooltip content="Tooltip text">
                <button>Hover me</button>
            </DSTooltip>
        );
        expect(screen.getByText('Hover me')).toBeInTheDocument();
    });

    it('renders with default side', () => {
        render(
            <DSTooltip content="Tooltip">
                <button>Hover</button>
            </DSTooltip>
        );
        expect(screen.getByText('Hover')).toBeInTheDocument();
    });

    it('renders with custom side', () => {
        render(
            <DSTooltip content="Tooltip" side="right">
                <button>Hover</button>
            </DSTooltip>
        );
        expect(screen.getByText('Hover')).toBeInTheDocument();
    });

    it('renders with custom sideOffset', () => {
        render(
            <DSTooltip content="Tooltip" sideOffset={10}>
                <button>Hover</button>
            </DSTooltip>
        );
        expect(screen.getByText('Hover')).toBeInTheDocument();
    });

    it('renders with multiple children', () => {
        render(
            <DSTooltip content="Tooltip">
                <div>
                    <button>First</button>
                    <button>Second</button>
                </div>
            </DSTooltip>
        );
        expect(screen.getByText('First')).toBeInTheDocument();
        expect(screen.getByText('Second')).toBeInTheDocument();
    });

    it('renders with complex children', () => {
        render(
            <DSTooltip content="Tooltip">
                <div data-testid="complex-child">
                    <span>Complex</span>
                </div>
            </DSTooltip>
        );
        expect(screen.getByTestId('complex-child')).toBeInTheDocument();
    });

    it('has no accessibility violations', async () => {
        const { container } = render(
            <DSTooltip content="Tooltip">
                <button>Trigger</button>
            </DSTooltip>
        );
        expect(await axe(container)).toHaveNoViolations();
    });
});
