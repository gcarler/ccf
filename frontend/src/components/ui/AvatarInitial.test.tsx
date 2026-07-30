import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AvatarInitial } from './AvatarInitial';

describe('AvatarInitial', () => {
    it('renders the first two initials of the name in uppercase', () => {
        render(<AvatarInitial name="Alice Smith" />);
        expect(screen.getByText('AL')).toBeInTheDocument();
    });

    it('falls back to "U" when no name is provided', () => {
        render(<AvatarInitial name="" />);
        expect(screen.getByText('U')).toBeInTheDocument();
    });

    it('applies size classes', () => {
        const { rerender } = render(<AvatarInitial name="Bob" size="sm" />);
        expect(screen.getByText('BO')).toHaveClass('size-7');

        rerender(<AvatarInitial name="Bob" size="md" />);
        expect(screen.getByText('BO')).toHaveClass('size-8');

        rerender(<AvatarInitial name="Bob" size="lg" />);
        expect(screen.getByText('BO')).toHaveClass('size-10');
    });
});
