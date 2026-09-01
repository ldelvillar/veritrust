import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { INITIAL_HISTORY_PATH } from '@/lib/historyQuery';
import { useHistoryFilters } from './useHistoryFilters';

const PATHNAME = '/app/historial';

let currentQuery = '';
const replace = vi.fn();

// Next devuelve la misma instancia mientras no se navega; el debounce depende de ello.
const paramsCache = new Map<string, URLSearchParams>();

function searchParamsFor(query: string): URLSearchParams {
  const cached = paramsCache.get(query);
  if (cached) return cached;
  const params = new URLSearchParams(query);
  paramsCache.set(query, params);
  return params;
}

vi.mock('next/navigation', () => ({
  useSearchParams: () => searchParamsFor(currentQuery),
  useRouter: () => ({ replace }),
  usePathname: () => PATHNAME,
}));

describe('useHistoryFilters', () => {
  beforeEach(() => {
    currentQuery = '';
    replace.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('builds the path the server precharges when no filters are set', () => {
    const { result } = renderHook(() => useHistoryFilters());

    expect(result.current.path).toBe(INITIAL_HISTORY_PATH);
    expect(result.current.isInitialQuery).toBe(true);
    expect(result.current.hasActiveFilters).toBe(false);
  });

  it('carries every URL filter into the query path', () => {
    currentQuery =
      'page=3&source_type=url&verdict=fake&status=done&date_range=30d&sort=oldest&search=gripe';

    const { result } = renderHook(() => useHistoryFilters());

    expect(result.current.path).toBe(
      '/history?page=3&page_size=10&source_type=url&verdict=fake&status=done&date_range=30d&sort=oldest&search=gripe'
    );
    expect(result.current.isInitialQuery).toBe(false);
    expect(result.current.hasActiveFilters).toBe(true);
  });

  it('falls back to the defaults when the URL carries values off-contract', () => {
    currentQuery = 'sort=bogus&verdict=maybe&status=&page=-2';

    const { result } = renderHook(() => useHistoryFilters());

    expect(result.current.sortOrder).toBe('recent');
    expect(result.current.verdictFilter).toBe('all');
    expect(result.current.currentPage).toBe(1);
    expect(result.current.path).toBe(INITIAL_HISTORY_PATH);
  });

  it('omits status from the export path, which the endpoint does not accept', () => {
    currentQuery = 'status=failed&verdict=real&page=2';

    const { result } = renderHook(() => useHistoryFilters());

    expect(result.current.exportPath).toBe(
      '/history/export?source_type=all&verdict=real&date_range=all&sort=recent'
    );
  });

  it('drops the page when a filter changes', () => {
    currentQuery = 'page=4';

    const { result } = renderHook(() => useHistoryFilters());
    act(() => result.current.setVerdict('fake'));

    expect(replace).toHaveBeenCalledWith(`${PATHNAME}?verdict=fake`, {
      scroll: false,
    });
  });

  it('removes a filter from the URL when it goes back to its default', () => {
    currentQuery = 'verdict=fake';

    const { result } = renderHook(() => useHistoryFilters());
    act(() => result.current.setVerdict('all'));

    expect(replace).toHaveBeenCalledWith(PATHNAME, { scroll: false });
  });

  it('keeps the first page out of the URL', () => {
    currentQuery = 'page=5';

    const { result } = renderHook(() => useHistoryFilters());
    act(() => result.current.setPage(1));

    expect(replace).toHaveBeenCalledWith(PATHNAME, { scroll: false });
  });

  it('debounces the search before it reaches the URL', () => {
    vi.useFakeTimers();

    const { result } = renderHook(() => useHistoryFilters());
    act(() => result.current.setSearchQuery('gripe aviar'));

    expect(replace).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(300));

    expect(replace).toHaveBeenCalledWith(`${PATHNAME}?search=gripe+aviar`, {
      scroll: false,
    });
  });

  it('clears every filter at once', () => {
    currentQuery = 'verdict=fake&status=done&page=2&search=gripe';

    const { result } = renderHook(() => useHistoryFilters());
    act(() => result.current.clearFilters());

    expect(replace).toHaveBeenCalledWith(PATHNAME, { scroll: false });
    expect(result.current.searchQuery).toBe('');
  });
});
