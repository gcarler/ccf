/* eslint-disable @typescript-eslint/no-explicit-any */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'jest-axe';
import type { ImageProps } from 'next/image';
import OptimizedImage from './OptimizedImage';

vi.mock('next/image', () => ({
    __esModule: true,
    default: (props: ImageProps) => {
        const { alt, src, ...rest } = props;
        return <img alt={alt} src={src as string} {...rest} />;
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

    it('has no accessibility violations', async () => {
        const { container } = render(<OptimizedImage src="/img.png" alt="Accessible" />);
        const results = await axe(container);
        expect(results.violations).toHaveLength(0);
    });
});
