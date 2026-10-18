import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import {
  FULL_VIEWS,
  MINIMAL_VIEWS,
  OPERATIONAL_VIEWS,
  PMI_GOVERNANCE_VIEWS,
  TEMPORAL_VIEWS,
  getStoredView,
  useViewType,
} from './useViewType';

describe('useViewType & view presets', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('returns fallback when sessionStorage has no stored view and reads stored view when present', () => {
    expect(getStoredView('projects_main', 'list')).toBe('list');
    sessionStorage.setItem('ccf_view_projects_main', 'gantt');
    expect(getStoredView('projects_main', 'list')).toBe('gantt');
  });

  it('initializes from sessionStorage and persists updates via setViewType', () => {
    sessionStorage.setItem('ccf_view_portfolio', 'board');
    const { result } = renderHook(() => useViewType('portfolio', 'table'));

    expect(result.current.viewType).toBe('board');

    act(() => {
      result.current.setViewType('wiki');
    });

    expect(result.current.viewType).toBe('wiki');
    expect(sessionStorage.getItem('ccf_view_portfolio')).toBe('wiki');
  });

  it('exports canonical view presets including PMI_GOVERNANCE_VIEWS', () => {
    expect(PMI_GOVERNANCE_VIEWS).toEqual([
      'dashboard',
      'table',
      'list',
      'gantt',
      'board',
      'wiki',
    ]);
    expect(FULL_VIEWS).toContain('dashboard');
    expect(OPERATIONAL_VIEWS).toContain('kanban');
    expect(TEMPORAL_VIEWS).toContain('gantt');
    expect(MINIMAL_VIEWS).toEqual(['table', 'list', 'grid']);
  });
});
