import React from 'react';
import { render } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('next/link', () => ({
    default: ({ href, children }: { href: string; children: ReactNode }) => <a href={href}>{children}</a>,
}));

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: { children: ReactNode }) => <div {...props}>{children}</div>,
    },
}));

vi.mock('@/context/AuthContext', () => ({
    useAuth: () => ({
        hasModuleAccess: () => true,
        hasPermission: () => false,
    }),
}));

import DashboardOverviewClient from '@/app/plataforma/dashboard/DashboardOverviewClient';

describe('DashboardOverviewClient links', () => {
    it('routes the projects tile to the projects workspace list', () => {
        const { container } = render(<DashboardOverviewClient />);

        const link = container.querySelector('a[href="/plataforma/projects/list"]');
        expect(link).toBeTruthy();
    });
});
