'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { INITIAL_HISTORY_PATH, PAGE_SIZE } from '@/lib/historyQuery';

export type SortOrder =
  | 'recent'
  | 'oldest'
  | 'credibility_high'
  | 'credibility_low';
export type DateRangeFilter = 'all' | '7d' | '30d' | '90d';
export type SourceTypeFilter = 'all' | 'text' | 'file' | 'url';
export type VerdictFilter = 'all' | 'real' | 'fake' | 'uncertain';
export type StatusFilter = 'all' | 'done' | 'pending' | 'failed';

const SEARCH_DEBOUNCE_MS = 300;

const SOURCE_TYPES = [
  'all',
  'text',
  'file',
  'url',
] as const satisfies readonly SourceTypeFilter[];
const SORTS = [
  'recent',
  'oldest',
  'credibility_high',
  'credibility_low',
] as const satisfies readonly SortOrder[];
const VERDICTS = [
  'all',
  'real',
  'fake',
  'uncertain',
] as const satisfies readonly VerdictFilter[];
const STATUSES = [
  'all',
  'done',
  'pending',
  'failed',
] as const satisfies readonly StatusFilter[];
const DATE_RANGES = [
  'all',
  '7d',
  '30d',
  '90d',
] as const satisfies readonly DateRangeFilter[];

function parseParam<T extends string>(
  value: string | null,
  allowed: readonly T[],
  fallback: T
): T {
  return value !== null && allowed.includes(value as T)
    ? (value as T)
    : fallback;
}

export function useHistoryFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const sourceTypeFilter = parseParam(
    searchParams.get('source_type'),
    SOURCE_TYPES,
    'all'
  );
  const verdictFilter = parseParam(
    searchParams.get('verdict'),
    VERDICTS,
    'all'
  );
  const sortOrder = parseParam(searchParams.get('sort'), SORTS, 'recent');
  const statusFilter = parseParam(searchParams.get('status'), STATUSES, 'all');
  const dateRangeFilter = parseParam(
    searchParams.get('date_range'),
    DATE_RANGES,
    'all'
  );
  const urlSearch = (searchParams.get('search') ?? '').trim();
  const parsedPage = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const currentPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const [searchQuery, setSearchQuery] = useState(urlSearch);

  const updateParams = useCallback(
    (changes: Record<string, string | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(changes)) {
        if (value === null) params.delete(key);
        else params.set(key, value);
      }
      const query = params.toString();
      router.replace(query ? `${pathname}?${query}` : pathname, {
        scroll: false,
      });
    },
    [pathname, router, searchParams]
  );

  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch]);

  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed === urlSearch) return;
    const handle = setTimeout(() => {
      updateParams({ search: trimmed || null, page: null });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [searchQuery, updateParams, urlSearch]);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      page: String(currentPage),
      page_size: String(PAGE_SIZE),
      source_type: sourceTypeFilter,
      verdict: verdictFilter,
      status: statusFilter,
      date_range: dateRangeFilter,
      sort: sortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history?${params.toString()}`;
  }, [
    currentPage,
    sortOrder,
    sourceTypeFilter,
    verdictFilter,
    statusFilter,
    dateRangeFilter,
    urlSearch,
  ]);

  const exportPath = useMemo(() => {
    // /history/export no acepta 'status'; solo se propaga el rango de fechas.
    const params = new URLSearchParams({
      source_type: sourceTypeFilter,
      verdict: verdictFilter,
      date_range: dateRangeFilter,
      sort: sortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history/export?${params.toString()}`;
  }, [sortOrder, sourceTypeFilter, verdictFilter, dateRangeFilter, urlSearch]);

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    sourceTypeFilter !== 'all' ||
    verdictFilter !== 'all' ||
    statusFilter !== 'all' ||
    dateRangeFilter !== 'all';

  const setFilter = useCallback(
    (key: string, value: string, defaultValue: string) => {
      updateParams({
        [key]: value === defaultValue ? null : value,
        page: null,
      });
    },
    [updateParams]
  );

  const setSourceType = useCallback(
    (value: SourceTypeFilter) => setFilter('source_type', value, 'all'),
    [setFilter]
  );

  const setVerdict = useCallback(
    (value: VerdictFilter) => setFilter('verdict', value, 'all'),
    [setFilter]
  );

  const setSort = useCallback(
    (value: SortOrder) => setFilter('sort', value, 'recent'),
    [setFilter]
  );

  const setStatus = useCallback(
    (value: StatusFilter) => setFilter('status', value, 'all'),
    [setFilter]
  );

  const setDateRange = useCallback(
    (value: DateRangeFilter) => setFilter('date_range', value, 'all'),
    [setFilter]
  );

  const setPage = useCallback(
    (page: number) => {
      const next = Math.max(1, page);
      updateParams({ page: next === 1 ? null : String(next) });
    },
    [updateParams]
  );

  const clearFilters = useCallback(() => {
    setSearchQuery('');
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  return {
    searchQuery,
    sourceTypeFilter,
    verdictFilter,
    statusFilter,
    dateRangeFilter,
    sortOrder,
    currentPage,
    path,
    exportPath,
    isInitialQuery: path === INITIAL_HISTORY_PATH,
    hasActiveFilters,
    setSearchQuery,
    setSourceType,
    setVerdict,
    setStatus,
    setDateRange,
    setSort,
    setPage,
    clearFilters,
  };
}
