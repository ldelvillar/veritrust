'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import HistoryFilters, {
  DateRangeFilter,
  ScoreSortOrder,
  SourceTypeFilter,
} from '@/components/HistoryFilters';
import HistoryResultsTable from '@/components/HistoryResultsTable';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { paths } from '@/types/api';

const PAGE_SIZE = 10;

type HistoryItem =
  paths['/history']['get']['responses']['200']['content']['application/json']['items'][number];
interface HistoryResponse {
  items?: HistoryItem[];
  count?: number;
}

export default function HistorialPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] =
    useState<SourceTypeFilter>('all');
  const [dateRangeFilter, setDateRangeFilter] =
    useState<DateRangeFilter>('all');
  const [scoreSortOrder, setScoreSortOrder] = useState<ScoreSortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      page: String(currentPage),
      page_size: String(PAGE_SIZE),
      source_type: sourceTypeFilter,
      date_range: dateRangeFilter,
      score_sort: scoreSortOrder,
    });
    const trimmedQuery = searchQuery.trim();
    if (trimmedQuery) params.set('search', trimmedQuery);
    return `/history?${params.toString()}`;
  }, [currentPage, dateRangeFilter, scoreSortOrder, searchQuery, sourceTypeFilter]);

  const {
    data,
    isLoading,
    error: fetchError,
    refetch: fetchHistory,
  } = useApiQuery<HistoryResponse>(path);

  const rawItems = data?.items;
  const history: HistoryItem[] = Array.isArray(rawItems) ? rawItems : [];
  const totalCount =
    typeof data?.count === 'number' ? data.count : history.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const effectivePage = Math.min(currentPage, totalPages);

  useEffect(() => {
    document.title = 'Historial de Análisis | VeriTrust';
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute(
        'content',
        'Revisa tu historial de análisis realizados en VeriTrust, con detalles de cada análisis y resultados obtenidos.'
      );
  }, []);

  const handleSearchQueryChange = useCallback((value: string) => {
    setCurrentPage(1);
    setSearchQuery(value);
  }, []);

  const handleSourceTypeFilterChange = useCallback(
    (value: SourceTypeFilter) => {
      setCurrentPage(1);
      setSourceTypeFilter(value);
    },
    []
  );

  const handleDateRangeFilterChange = useCallback((value: DateRangeFilter) => {
    setCurrentPage(1);
    setDateRangeFilter(value);
  }, []);

  const handleScoreSortOrderChange = useCallback((value: ScoreSortOrder) => {
    setCurrentPage(1);
    setScoreSortOrder(value);
  }, []);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(Math.max(1, page));
  }, []);

  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Análisis anteriores
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Revisa y gestiona tus informes previos.
          </p>
        </div>

        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-primary/8 px-4 py-2 text-sm font-bold text-primary"
        >
          <span aria-hidden>↓</span>
          Exportar todo
        </button>
      </div>

      <HistoryFilters
        searchQuery={searchQuery}
        onSearchQueryChange={handleSearchQueryChange}
        sourceTypeFilter={sourceTypeFilter}
        onSourceTypeFilterChange={handleSourceTypeFilterChange}
        dateRangeFilter={dateRangeFilter}
        onDateRangeFilterChange={handleDateRangeFilterChange}
        scoreSortOrder={scoreSortOrder}
        onScoreSortOrderChange={handleScoreSortOrderChange}
      />

      <HistoryResultsTable
        history={history}
        totalCount={totalCount}
        currentPage={effectivePage}
        pageSize={PAGE_SIZE}
        isLoading={isLoading}
        errorMessage={fetchError?.message ?? null}
        onRetry={fetchHistory}
        onPageChange={handlePageChange}
      />
    </section>
  );
}
