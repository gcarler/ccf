import { beforeEach, describe, expect, it, vi } from 'vitest';

const { apiFetch } = vi.hoisted(() => ({
    apiFetch: vi.fn(),
}));

vi.mock('@/lib/http', () => ({ apiFetch }));

import { getCmsPublicPage, getCmsPublicPost, getPublicPastoralTeam } from '@/lib/cms/v2';

describe('public CMS fetch wrappers', () => {
    beforeEach(() => {
        apiFetch.mockReset();
    });

    it('keeps public page fetches silent by default', async () => {
        apiFetch.mockResolvedValueOnce({});

        await getCmsPublicPage('ccf', 'home');

        expect(apiFetch).toHaveBeenCalledWith('/cms/v2/public/sites/ccf/pages/home', { silent: true });
    });

    it('fetches the canonical CMS page slugs used by public routes', async () => {
        const slugs = ['home', 'about', 'events', 'pastors', 'sermons', 'courses', 'locations', 'testimonials', 'newsletter', 'discover', 'privacy', 'blog'];
        for (const slug of slugs) {
            apiFetch.mockResolvedValueOnce({ slug });
            await getCmsPublicPage('ccf', slug);
        }

        expect(apiFetch).toHaveBeenCalledTimes(slugs.length);
        for (const slug of slugs) {
            expect(apiFetch).toHaveBeenCalledWith(`/cms/v2/public/sites/ccf/pages/${slug}`, { silent: true });
        }
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
