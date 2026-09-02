import { apiFetch } from '@/lib/http';

export interface CrmCaseListResponse<T> {
    cases: T[];
    total?: number;
    page?: number;
    page_size?: number;
    total_pages?: number;
}

/**
 * Reads the complete set of visible CRM cases for the current actor.
 * The API is paginated, so screens must not silently stop at its default page.
 */
export async function fetchAllCrmCases<T>(token: string, signal?: AbortSignal): Promise<T[]> {
    const allCases: T[] = [];
    let page = 1;

    while (true) {
        const response = await apiFetch<CrmCaseListResponse<T>>(
            `/crm/casos?page=${page}&page_size=100`,
            { token, cache: 'no-store', signal },
        );
        const cases = Array.isArray(response?.cases) ? response.cases : [];
        allCases.push(...cases);

        const totalPages = response?.total_pages ?? (cases.length < 100 ? page : page + 1);
        if (page >= totalPages || cases.length === 0) return allCases;
        page += 1;
    }
}
