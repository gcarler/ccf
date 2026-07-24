import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import OptimizedImage from './OptimizedImage';

vi.mock('next/image', () => ({
    __esModule: true,
    default: (props: any) => {
        const { alt, ...rest } = props;
        // eslint-disable-next-line @next/next/no-img-element
        return <img alt={alt} {...rest} />;
    },
}));

vi.mock('@/lib/cms/media', () => ({
    getCmsMediaUrl: (url: string) => url,
}));

describe('OptimizedImage', () => {
    it('renders an img with the correct src', () => {
        render(<OptimizedImage src="/api/static/course/test.webp" alt="Test image" />);
        const img = screen.getByRole('img');
        expect(img).toHaveAttribute('src', '/api/static/course/test.webp');
    });

    it('renders an img with the correct alt', () => {
        render(<OptimizedImage src="/img.png" alt="My photo" />);
        expect(screen.getByAltText('My photo')).toBeInTheDocument();
    });

    it('renders fallback when src is empty', () => {
        render(<OptimizedImage src="" alt="Missing" />);
        expect(screen.queryByRole('img')).not.toBeInTheDocument();
        expect(screen.getByLabelText('Missing')).toBeInTheDocument();
    });
});
