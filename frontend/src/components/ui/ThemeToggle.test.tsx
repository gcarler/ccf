import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ThemeToggle from './ThemeToggle';

vi.mock('@/design', () => ({
    DSTooltip: ({ children }: any) => <div>{children}</div>,
}));

const mockToggleTheme = vi.fn();
let currentTheme: 'day' | 'night' = 'day';

vi.mock('@/app/plataforma/theme/ThemeContext', () => ({
    useTheme: () => ({
        theme: currentTheme,
        toggleTheme: () => {
            currentTheme = currentTheme === 'day' ? 'night' : 'day';
            mockToggleTheme();
        },
    }),
}));

describe('ThemeToggle', () => {
    beforeEach(() => {
        currentTheme = 'day';
        mockToggleTheme.mockClear();
    });

    it('renders the toggle button', () => {
        render(<ThemeToggle />);
        const button = screen.getAllByRole('button')[0];
        expect(button).toBeInTheDocument();
    });

    it('calls toggleTheme on click (icon variant)', () => {
        render(<ThemeToggle variant="icon" />);
        const button = screen.getAllByRole('button')[0];
        fireEvent.click(button);
        expect(mockToggleTheme).toHaveBeenCalledTimes(1);
    });

    it('shows correct label in row variant for day theme', () => {
        render(<ThemeToggle variant="row" />);
        expect(screen.getByText('Modo Claro')).toBeInTheDocument();
    });
});
