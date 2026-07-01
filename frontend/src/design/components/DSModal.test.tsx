import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { DSModal } from './DSModal';

describe('DSModal', () => {
    it('does not render when closed', () => {
        render(<DSModal open={false} onClose={vi.fn()}>Content</DSModal>);
        expect(screen.queryByText('Content')).not.toBeInTheDocument();
    });

    it('renders when open', () => {
        render(<DSModal open={true} onClose={vi.fn()}>Content</DSModal>);
        expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('renders title when provided', () => {
        render(
            <DSModal open={true} onClose={vi.fn()} title="Test Title">
                Content
            </DSModal>
        );
        expect(screen.getByText('Test Title')).toBeInTheDocument();
    });

    it('calls onClose when pressing Escape', () => {
        const handleClose = vi.fn();
        render(<DSModal open={true} onClose={handleClose}>Content</DSModal>);
        
        fireEvent.keyDown(document, { key: 'Escape' });
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('renders close button', () => {
        render(<DSModal open={true} onClose={vi.fn()}>Content</DSModal>);
        expect(screen.getByLabelText('Cerrar')).toBeInTheDocument();
    });

    it('calls onClose when clicking close button', () => {
        const handleClose = vi.fn();
        render(<DSModal open={true} onClose={handleClose}>Content</DSModal>);
        
        fireEvent.click(screen.getByLabelText('Cerrar'));
        expect(handleClose).toHaveBeenCalledTimes(1);
    });

    it('hides close button when showClose is false', () => {
        render(
            <DSModal open={true} onClose={vi.fn()} showClose={false}>
                Content
            </DSModal>
        );
        expect(screen.queryByLabelText('Cerrar')).not.toBeInTheDocument();
    });

    it('applies small size', () => {
        render(
            <DSModal open={true} onClose={vi.fn()} size="sm">
                Content
            </DSModal>
        );
        const modal = screen.getByRole('dialog');
        expect(modal.className).toContain('max-w-sm');
    });

    it('applies large size', () => {
        render(
            <DSModal open={true} onClose={vi.fn()} size="lg">
                Content
            </DSModal>
        );
        const modal = screen.getByRole('dialog');
        expect(modal.className).toContain('max-w-lg');
    });

    it('has correct aria attributes', () => {
        render(
            <DSModal open={true} onClose={vi.fn()} title="Test">
                Content
            </DSModal>
        );
        const modal = screen.getByRole('dialog');
        expect(modal).toHaveAttribute('aria-modal', 'true');
        expect(modal).toHaveAttribute('aria-labelledby', 'modal-title');
    });

    it('renders backdrop', () => {
        render(<DSModal open={true} onClose={vi.fn()}>Content</DSModal>);
        const backdrop = document.querySelector('[aria-hidden="true"]');
        expect(backdrop).toBeInTheDocument();
    });

    it('calls onClose when clicking backdrop', () => {
        const handleClose = vi.fn();
        render(<DSModal open={true} onClose={handleClose}>Content</DSModal>);
        
        const backdrop = document.querySelector('[aria-hidden="true"]');
        if (backdrop) {
            fireEvent.click(backdrop);
            expect(handleClose).toHaveBeenCalledTimes(1);
        }
    });
});
