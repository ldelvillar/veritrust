'use client';

import { useAuth } from '@clerk/nextjs';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Spinner from '@/assets/Spinner';
import DownloadIcon from '@/assets/Download';
import HistoryFilters, {
  DateRangeFilter,
  ScoreSortOrder,
  SourceTypeFilter,
} from '@/components/HistoryFilters';
import HistoryResultsTable from '@/components/HistoryResultsTable';
import ConfirmDialog from '@/components/ConfirmDialog';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

const PAGE_SIZE = 10;
const INITIAL_PATH = `/history?page=1&page_size=${PAGE_SIZE}&source_type=all&date_range=all&score_sort=desc`;

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
type HistoryItem = HistoryPayload['items'][number];

interface HistorialClientProps {
  initialData: HistoryPayload;
}

export default function HistorialClient({ initialData }: HistorialClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sourceTypeFilter, setSourceTypeFilter] =
    useState<SourceTypeFilter>('all');
  const [dateRangeFilter, setDateRangeFilter] =
    useState<DateRangeFilter>('all');
  const [scoreSortOrder, setScoreSortOrder] = useState<ScoreSortOrder>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<HistoryItem | null>(null);

  const { getToken } = useAuth();
  const {
    remove: deleteAnalysis,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAnalysisDeletion();

  // Evita refrescar en cada pulsación
  useEffect(() => {
    const handle = setTimeout(() => {
      setDebouncedSearch(searchQuery);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(handle);
  }, [searchQuery]);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      page: String(currentPage),
      page_size: String(PAGE_SIZE),
      source_type: sourceTypeFilter,
      date_range: dateRangeFilter,
      score_sort: scoreSortOrder,
    });
    const trimmedQuery = debouncedSearch.trim();
    if (trimmedQuery) params.set('search', trimmedQuery);
    return `/history?${params.toString()}`;
  }, [
    currentPage,
    dateRangeFilter,
    scoreSortOrder,
    debouncedSearch,
    sourceTypeFilter,
  ]);

  const exportPath = useMemo(() => {
    const params = new URLSearchParams({
      source_type: sourceTypeFilter,
      date_range: dateRangeFilter,
      score_sort: scoreSortOrder,
    });
    const trimmedQuery = debouncedSearch.trim();
    if (trimmedQuery) params.set('search', trimmedQuery);
    return `/history/export?${params.toString()}`;
  }, [dateRangeFilter, scoreSortOrder, debouncedSearch, sourceTypeFilter]);

  const handleExport = useCallback(async () => {
    setExportError(null);
    setIsExporting(true);
    try {
      const blob = await fetchBlobWithAuth(getToken, exportPath);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'historial-veritrust.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(
        err instanceof ApiError
          ? err.message
          : 'No se pudo exportar el historial. Inténtalo de nuevo.'
      );
    } finally {
      setIsExporting(false);
    }
  }, [exportPath, getToken]);

  const {
    data,
    isLoading,
    error: fetchError,
    refetch: fetchHistory,
  } = useApiQuery<HistoryPayload>(path, {
    fallbackData: path === INITIAL_PATH ? initialData : undefined,
  });

  const rawItems = data?.items;
  const history: HistoryItem[] = Array.isArray(rawItems) ? rawItems : [];
  const totalCount =
    typeof data?.count === 'number' ? data.count : history.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const effectivePage = Math.min(currentPage, totalPages);

  const handleSearchQueryChange = useCallback((value: string) => {
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

  const handleDeleteRequest = useCallback(
    (item: HistoryItem) => {
      setDeleteError(null);
      setPendingDelete(item);
    },
    [setDeleteError]
  );

  const handleDeleteCancel = useCallback(() => {
    if (isDeleting) return;
    setDeleteError(null);
    setPendingDelete(null);
  }, [isDeleting, setDeleteError]);

  const handleDeleteConfirm = useCallback(async () => {
    if (!pendingDelete) return;
    // history.length se evalúa antes del refetch: refleja la página actual.
    const wasLastOnPage = history.length === 1;
    const success = await deleteAnalysis(pendingDelete.analysis_id);
    if (!success) return;
    setPendingDelete(null);
    if (wasLastOnPage && currentPage > 1) {
      // Cambiar de página dispara el refetch de SWR automáticamente.
      setCurrentPage(page => page - 1);
    } else {
      await fetchHistory();
    }
  }, [
    pendingDelete,
    history.length,
    deleteAnalysis,
    currentPage,
    fetchHistory,
  ]);

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Análisis anteriores
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Revisa y gestiona tus informes previos.
          </p>
        </div>

        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting || totalCount === 0}
            aria-busy={isExporting}
            className="inline-flex items-center gap-2 rounded-xl border border-primary/15 bg-primary/8 px-4 py-2 text-sm font-bold text-primary transition hover:bg-primary/15 focus:ring-2 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isExporting ? (
              <Spinner className="size-4 animate-spin text-primary" />
            ) : (
              <DownloadIcon className="size-4" aria-hidden />
            )}
            {isExporting ? 'Exportando…' : 'Exportar todo'}
          </button>
          {exportError ? (
            <p role="alert" className="text-xs font-semibold text-red-600">
              {exportError}
            </p>
          ) : null}
        </div>
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
        onDelete={handleDeleteRequest}
        deletingId={isDeleting ? (pendingDelete?.analysis_id ?? null) : null}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        title="¿Eliminar este análisis?"
        description="Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
        isConfirming={isDeleting}
        errorMessage={deleteError}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
    </>
  );
}
