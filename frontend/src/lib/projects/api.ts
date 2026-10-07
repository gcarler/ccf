import { apiFetch } from '@/lib/http';
import type {
  ProjectRecord,
  ProjectSummaryPageResponse,
  ProjectSummaryRecord,
  ProjectTaskRecord,
} from '@/types/projects';

const PROJECTS_PAGE_SIZE = 100;

type ProjectsCollectionPath = '/projects/page' | '/projects/summary-page' | '/projects/tasks/page';
type PageResponse<T> = { items: T[]; total: number; skip: number; limit: number };

async function getAllPages<T>(
  path: ProjectsCollectionPath,
  token: string,
  options: { cache?: RequestCache; signal?: AbortSignal },
  resourceName: string,
  initialPage?: PageResponse<T>,
): Promise<T[]> {
  const rows: T[] = [];
  let offset = 0;
  let total = Number.POSITIVE_INFINITY;

  if (initialPage) {
    if (
      !Array.isArray(initialPage.items) ||
      !Number.isInteger(initialPage.total) ||
      initialPage.total < 0 ||
      !Number.isInteger(initialPage.skip) ||
      initialPage.skip !== 0 ||
      initialPage.items.length > initialPage.total ||
      !Number.isInteger(initialPage.limit) ||
      initialPage.limit < 1 ||
      initialPage.items.length > initialPage.limit ||
      (initialPage.total > 0 && initialPage.items.length === 0)
    ) {
      throw new Error(`Invalid or incomplete ${resourceName} page response`);
    }
    rows.push(...initialPage.items);
    offset = initialPage.items.length;
    total = initialPage.total;
  }

  while (offset < total) {
    const page = await apiFetch<PageResponse<T>>(path, {
      token,
      cache: options.cache,
      signal: options.signal,
      query: { offset, limit: PROJECTS_PAGE_SIZE },
    });
    if (
      !Array.isArray(page.items) ||
      !Number.isInteger(page.total) ||
      page.total < 0 ||
      !Number.isInteger(page.skip) ||
      page.skip !== offset ||
      (Number.isFinite(total) && page.total !== total) ||
      !Number.isInteger(page.limit) ||
      page.limit < 1 ||
      page.items.length > page.limit ||
      (page.total > offset && page.items.length === 0)
    ) {
      throw new Error(`Invalid or incomplete ${resourceName} page response`);
    }
    rows.push(...page.items);
    offset += page.items.length;
    total = page.total;
  }

  return rows;
}

/** Load every project without relying on an unbounded list endpoint. */
export async function getAllProjects(
  token: string,
  options: { cache?: RequestCache; signal?: AbortSignal } = {},
): Promise<ProjectRecord[]> {
  return getAllPages<ProjectRecord>('/projects/page', token, options, 'projects');
}

/** Load project summaries without repeating a server-rendered first page. */
export async function getAllProjectSummaries(
  token: string,
  options: {
    cache?: RequestCache;
    signal?: AbortSignal;
    initialPage?: ProjectSummaryPageResponse;
  } = {},
): Promise<ProjectSummaryRecord[]> {
  return getAllPages<ProjectSummaryRecord>(
    '/projects/summary-page',
    token,
    options,
    'project summaries',
    options.initialPage,
  );
}

export async function getAllAssignedProjectTasks(
  token: string,
  options: { cache?: RequestCache; signal?: AbortSignal } = {},
): Promise<ProjectTaskRecord[]> {
  return getAllPages<ProjectTaskRecord>('/projects/tasks/page', token, options, 'project tasks');
}
