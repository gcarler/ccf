import { describe, expect, it, vi } from 'vitest';

const { apiFetch } = vi.hoisted(() => ({
    apiFetch: vi.fn(),
}));

vi.mock('@/lib/http', () => ({ apiFetch }));

import { getCmsPublicPage, getCmsPublicPost, getPublicPastoralTeam } from '@/lib/cms/v2';

describe('public CMS fetch wrappers', () => {
    it('keeps public page fetches silent by default', async () => {
        apiFetch.mockResolvedValueOnce({});

        await getCmsPublicPage('ccf', 'home');

        expect(apiFetch).toHaveBeenCalledWith('/cms/v2/public/sites/ccf/pages/home', { silent: true });
    });

    it('keeps public post and pastoral team fetches silent', async () => {
        apiFetch.mockResolvedValueOnce({});
        await getCmsPublicPost('ccf', 'testimonio');
        expect(apiFetch).toHaveBeenCalledWith('/cms/v2/public/sites/ccf/posts/testimonio', { silent: true });

        apiFetch.mockResolvedValueOnce([]);
        await getPublicPastoralTeam('ccf');
        expect(apiFetch).toHaveBeenCalledWith('/cms/v2/public/sites/ccf/pastoral-team', { silent: true });
    });
});
