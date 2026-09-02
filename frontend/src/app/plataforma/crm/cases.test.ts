import { beforeEach, describe, expect, it, vi } from 'vitest';
import { apiFetch } from '@/lib/http';
import { fetchAllCrmCases } from './cases';

vi.mock('@/lib/http', () => ({
    apiFetch: vi.fn(),
}));

describe('fetchAllCrmCases', () => {
    const apiFetchMock = vi.mocked(apiFetch);

    beforeEach(() => {
        apiFetchMock.mockReset();
    });

    it('loads every paginated page instead of stopping at the first 50 cases', async () => {
        apiFetchMock
            .mockResolvedValueOnce({ cases: [{ id: 'case-1' }], total: 101, page: 1, page_size: 100, total_pages: 2 })
            .mockResolvedValueOnce({ cases: [{ id: 'case-2' }], total: 101, page: 2, page_size: 100, total_pages: 2 });

        const result = await fetchAllCrmCases<{ id: string }>('token-1');

        expect(result).toEqual([{ id: 'case-1' }, { id: 'case-2' }]);
        expect(apiFetchMock).toHaveBeenNthCalledWith(1, '/crm/casos?page=1&page_size=100', {
            token: 'token-1',
            cache: 'no-store',
            signal: undefined,
        });
        expect(apiFetchMock).toHaveBeenNthCalledWith(2, '/crm/casos?page=2&page_size=100', {
            token: 'token-1',
            cache: 'no-store',
            signal: undefined,
        });
    });

    it('returns an empty operational state when the API has no cases', async () => {
        apiFetchMock.mockResolvedValueOnce({ cases: [], total: 0, page: 1, page_size: 100, total_pages: 0 });

        await expect(fetchAllCrmCases('token-1')).resolves.toEqual([]);
        expect(apiFetchMock).toHaveBeenCalledTimes(1);
    });
});
