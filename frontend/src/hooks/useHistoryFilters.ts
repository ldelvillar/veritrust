'use client';

import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  DEFAULT_HISTORY_FILTERS,
  INITIAL_HISTORY_PATH,
  historyExportPath,
  historyPath,
  parseHistoryFilters,
  parseHistoryPage,
  type DateRangeFilter,
  type SortOrder,
  type SourceTypeFilter,
  type StatusFilter,
  type VerdictFilter,
} from '@/lib/historyQuery';

const SEARCH_DEBOUNCE_MS = 300;

export function useHistoryFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const filters = useMemo(
    () => parseHistoryFilters(searchParams),
    [searchParams]
  );
  const currentPage = parseHistoryPage(searchParams);
  const urlSearch = filters.search;

  const [searchQuery, setSearchQuery] = useState(urlSearch);
  const [syncedUrlSearch, setSyncedUrlSearch] = useState(urlSearch);

  // Back/forward or a filter reset changes the URL: the input follows it during render.
  if (urlSearch !== syncedUrlSearch) {
    setSyncedUrlSearch(urlSearch);
    setSearchQuery(urlSearch);
  }

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
    const trimmed = searchQuery.trim();
    if (trimmed === urlSearch) return;
    const handle = setTimeout(() => {
      updateParams({ search: trimmed || null, page: null });
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [searchQuery, updateParams, urlSearch]);

  const path = useMemo(
    () => historyPath(filters, currentPage),
    [filters, currentPage]
  );
  const exportPath = useMemo(() => historyExportPath(filters), [filters]);

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    filters.sourceType !== 'all' ||
    filters.verdict !== 'all' ||
    filters.status !== 'all' ||
    filters.dateRange !== 'all';

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
    (value: SourceTypeFilter) =>
      setFilter('source_type', value, DEFAULT_HISTORY_FILTERS.sourceType),
    [setFilter]
  );

  const setVerdict = useCallback(
    (value: VerdictFilter) =>
      setFilter('verdict', value, DEFAULT_HISTORY_FILTERS.verdict),
    [setFilter]
  );

  const setSort = useCallback(
    (value: SortOrder) =>
      setFilter('sort', value, DEFAULT_HISTORY_FILTERS.sort),
    [setFilter]
  );

  const setStatus = useCallback(
    (value: StatusFilter) =>
      setFilter('status', value, DEFAULT_HISTORY_FILTERS.status),
    [setFilter]
  );

  const setDateRange = useCallback(
    (value: DateRangeFilter) =>
      setFilter('date_range', value, DEFAULT_HISTORY_FILTERS.dateRange),
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
    sourceTypeFilter: filters.sourceType,
    verdictFilter: filters.verdict,
    statusFilter: filters.status,
    dateRangeFilter: filters.dateRange,
    sortOrder: filters.sort,
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
