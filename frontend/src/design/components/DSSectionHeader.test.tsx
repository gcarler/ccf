import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { DSSectionHeader } from './DSSectionHeader';

describe('DSSectionHeader', () => {
    it('renders with title', () => {
        render(<DSSectionHeader title="Section Title" />);
        expect(screen.getByText('Section Title')).toBeInTheDocument();
    });

    it('renders with eyebrow', () => {
        render(<DSSectionHeader eyebrow="Eyebrow" title="Title" />);
        expect(screen.getByText('Eyebrow')).toBeInTheDocument();
    });

    it('renders with description', () => {
        render(<DSSectionHeader title="Title" description="Description text" />);
        expect(screen.getByText('Description text')).toBeInTheDocument();
    });

    it('renders with actions', () => {
        render(
            <DSSectionHeader 
                title="Title" 
                actions={<button>Action</button>} 
            />
        );
        expect(screen.getByText('Action')).toBeInTheDocument();
    });

    it('applies left alignment by default', () => {
        render(<DSSectionHeader title="Title" />);
        const title = screen.getByText('Title');
        const container = title.closest('div')?.parentElement;
        expect(container?.className).toContain('flex-col');
    });

    it('applies center alignment', () => {
        render(<DSSectionHeader title="Title" align="center" />);
        const title = screen.getByText('Title');
        const container = title.closest('div')?.parentElement;
        expect(container?.className).toContain('text-center');
    });

    it('renders eyebrow with correct styling', () => {
        render(<DSSectionHeader eyebrow="Eyebrow" title="Title" />);
        const eyebrow = screen.getByText('Eyebrow');
        expect(eyebrow.className).toContain('text-[10px]');
        expect(eyebrow.className).toContain('uppercase');
    });

    it('renders title with correct styling', () => {
        render(<DSSectionHeader title="Title" />);
        const title = screen.getByText('Title');
        expect(title.className).toContain('text-base');
        expect(title.className).toContain('font-bold');
    });
});
