import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'jest-axe';
import { UserMenuDropdown } from './WorkspaceLayout';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
    usePathname: () => '/plataforma/dashboard',
    useRouter: () => ({
        push: mockPush,
    }),
}));

describe('UserMenuDropdown Component', () => {
    const mockLogout = vi.fn();
    const mockOpenAppearance = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders user trigger button with initials', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        expect(screen.getByText('Pastor Carlos')).toBeInTheDocument();
        expect(screen.getByText('PA')).toBeInTheDocument();
    });

    it('opens dropdown menu on click', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        const trigger = screen.getByRole('button');
        fireEvent.click(trigger);

        expect(screen.getByText('Mi perfil')).toBeInTheDocument();
        expect(screen.getByText('Configuración')).toBeInTheDocument();
        expect(screen.getByText('Pantalla, Densidad y Color')).toBeInTheDocument();
        expect(screen.getByText('Cerrar sesión')).toBeInTheDocument();
    });

    it('navigates to /plataforma/account when clicking "Mi perfil"', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        fireEvent.click(screen.getByRole('button'));
        fireEvent.click(screen.getByText('Mi perfil'));

        expect(mockPush).toHaveBeenCalledWith('/plataforma/account');
    });

    it('navigates to /plataforma/settings when clicking "Configuración"', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        fireEvent.click(screen.getByRole('button'));
        fireEvent.click(screen.getByText('Configuración'));

        expect(mockPush).toHaveBeenCalledWith('/plataforma/settings');
    });

    it('calls onOpenAppearance when clicking "Pantalla, Densidad y Color"', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        fireEvent.click(screen.getByRole('button'));
        fireEvent.click(screen.getByText('Pantalla, Densidad y Color'));

        expect(mockOpenAppearance).toHaveBeenCalledTimes(1);
    });

    it('calls logout when clicking "Cerrar sesión"', () => {
        render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        fireEvent.click(screen.getByRole('button'));
        fireEvent.click(screen.getByText('Cerrar sesión'));

        expect(mockLogout).toHaveBeenCalledTimes(1);
    });

    it('has zero accessibility violations when menu is open', async () => {
        const { container } = render(
            <UserMenuDropdown
                displayName="Pastor Carlos"
                username="pastor.carlos"
                logout={mockLogout}
                onOpenAppearance={mockOpenAppearance}
            />
        );

        fireEvent.click(screen.getByRole('button'));
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });

    it('renders with default values when props are omitted', () => {
        render(<UserMenuDropdown />);
        expect(screen.getByText('Usuario')).toBeInTheDocument();
        expect(screen.getByText('US')).toBeInTheDocument();
    });
});
