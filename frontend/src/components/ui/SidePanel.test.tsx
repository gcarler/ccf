import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import SidePanel from './SidePanel';

describe('SidePanel', () => {
    it('does not render content when closed', () => {
        render(
            <SidePanel isOpen={false} onClose={() => {}} title="Título">
                <div data-testid="content">Contenido</div>
            </SidePanel>
        );
        expect(screen.queryByText('Título')).not.toBeInTheDocument();
        expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('renders title, subtitle and children when open', () => {
        render(
            <SidePanel isOpen onClose={() => {}} title="Título" subtitle="Subtítulo">
                <div data-testid="content">Contenido</div>
            </SidePanel>
        );
        expect(screen.getByText('Título')).toBeInTheDocument();
        expect(screen.getByText('Subtítulo')).toBeInTheDocument();
        expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('fires onClose when clicking the close button', async () => {
        const handleClose = vi.fn();
        render(
            <SidePanel isOpen onClose={handleClose} title="Título">
                <div>Contenido</div>
            </SidePanel>
        );
        const closeButton = screen.getByRole('button', { name: /cerrar/i });
        fireEvent.click(closeButton);
        await waitFor(() => expect(handleClose).toHaveBeenCalledTimes(1));
    });

    it('fires onPrev and onNext when navigation buttons are present', async () => {
        const handlePrev = vi.fn();
        const handleNext = vi.fn();
        render(
            <SidePanel isOpen onClose={() => {}} title="Título" onPrev={handlePrev} onNext={handleNext}>
                <div>Contenido</div>
            </SidePanel>
        );
        const prevButton = screen.getByRole('button', { name: /anterior/i });
        const nextButton = screen.getByRole('button', { name: /siguiente/i });
        fireEvent.click(prevButton);
        await waitFor(() => expect(handlePrev).toHaveBeenCalledTimes(1));
        fireEvent.click(nextButton);
        await waitFor(() => expect(handleNext).toHaveBeenCalledTimes(1));
    });

    it('renders full view link when provided', () => {
        render(
            <SidePanel isOpen onClose={() => {}} title="Título" fullViewHref="/details/1">
                <div>Contenido</div>
            </SidePanel>
        );
        const link = screen.getByRole('link', { name: /vista completa/i });
        expect(link).toHaveAttribute('href', '/details/1');
    });

    it('has no accessibility violations', async () => {
        const { container } = render(
            <SidePanel isOpen onClose={() => {}} title="Título" subtitle="Subtítulo">
                <div>Contenido</div>
            </SidePanel>
        );
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
