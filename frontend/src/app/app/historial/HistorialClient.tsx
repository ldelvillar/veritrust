'use client';

import { useAuth } from '@clerk/nextjs';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Spinner from '@/assets/Spinner';
import DownloadIcon from '@/assets/Download';
import HistoryFilters, {
  DateRangeFilter,
  DateSortOrder,
  SourceTypeFilter,
  StatusFilter,
  VerdictFilter,
} from './_components/HistoryFilters';
import HistoryResultsTable from './_components/HistoryResultsTable';
import ConfirmDialog from '@/components/ConfirmDialog';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

const PAGE_SIZE = 10;
const INITIAL_PATH = `/history?page=1&page_size=${PAGE_SIZE}&source_type=all&verdict=all&status=all&date_range=all&date_sort=desc`;

const SOURCE_TYPES = [
  'all',
  'text',
  'file',
  'url',
] as const satisfies readonly SourceTypeFilter[];
const STATUSES = [
  'all',
  'done',
  'pending',
  'failed',
] as const satisfies readonly StatusFilter[];
const VERDICTS = [
  'all',
  'real',
  'fake',
  'uncertain',
] as const satisfies readonly VerdictFilter[];
const DATE_RANGES = [
  'all',
  '7d',
  '30d',
  '90d',
] as const satisfies readonly DateRangeFilter[];
const DATE_SORTS = ['desc', 'asc'] as const satisfies readonly DateSortOrder[];

// Acota un parámetro de la URL al conjunto permitido; cae al valor por defecto si no encaja.
function parseParam<T extends string>(
  value: string | null,
  allowed: readonly T[],
  fallback: T
): T {
  return value !== null && allowed.includes(value as T)
    ? (value as T)
    : fallback;
}

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
type HistoryItem = HistoryPayload['items'][number];

interface HistorialClientProps {
  initialData: HistoryPayload;
}

export default function HistorialClient({ initialData }: HistorialClientProps) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  // La URL es la fuente de verdad: refrescar o compartir el enlace conserva la vista.
  const sourceTypeFilter = parseParam(
    searchParams.get('source_type'),
    SOURCE_TYPES,
    'all'
  );
  const statusFilter = parseParam(searchParams.get('status'), STATUSES, 'all');
  const verdictFilter = parseParam(
    searchParams.get('verdict'),
    VERDICTS,
    'all'
  );
  const dateRangeFilter = parseParam(
    searchParams.get('date_range'),
    DATE_RANGES,
    'all'
  );
  const dateSortOrder = parseParam(
    searchParams.get('date_sort'),
    DATE_SORTS,
    'desc'
  );
  const urlSearch = (searchParams.get('search') ?? '').trim();
  const parsedPage = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const currentPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  // El input se mantiene local para responder al instante; se confirma a la URL tras el debounce.
  const [searchQuery, setSearchQuery] = useState(urlSearch);
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

  // Mantiene el input en sintonía cuando la URL cambia desde fuera (limpiar filtros, atrás/adelante).
  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch]);

  // Confirma la búsqueda escrita a la URL cuando el usuario hace una pausa, y vuelve a la página 1.
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (trimmed === urlSearch) return;
    const handle = setTimeout(() => {
      updateParams({ search: trimmed || null, page: null });
    }, 300);
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
      date_sort: dateSortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history?${params.toString()}`;
  }, [
    currentPage,
    dateRangeFilter,
    dateSortOrder,
    sourceTypeFilter,
    statusFilter,
    urlSearch,
    verdictFilter,
  ]);

  const exportPath = useMemo(() => {
    const params = new URLSearchParams({
      source_type: sourceTypeFilter,
      verdict: verdictFilter,
      date_range: dateRangeFilter,
      date_sort: dateSortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history/export?${params.toString()}`;
  }, [
    dateRangeFilter,
    dateSortOrder,
    sourceTypeFilter,
    urlSearch,
    verdictFilter,
  ]);

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

  // El orden por fecha no acota resultados, así que no cuenta como filtro activo.
  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    sourceTypeFilter !== 'all' ||
    statusFilter !== 'all' ||
    verdictFilter !== 'all' ||
    dateRangeFilter !== 'all';

  // Los cambios de filtro vuelven a la página 1; los valores por defecto se omiten de la URL.
  const setFilter = useCallback(
    (key: string, value: string, defaultValue: string) => {
      updateParams({
        [key]: value === defaultValue ? null : value,
        page: null,
      });
    },
    [updateParams]
  );

  const handleSearchQueryChange = useCallback((value: string) => {
    setSearchQuery(value);
  }, []);

  const handleSourceTypeFilterChange = useCallback(
    (value: SourceTypeFilter) => setFilter('source_type', value, 'all'),
    [setFilter]
  );

  const handleStatusFilterChange = useCallback(
    (value: StatusFilter) => setFilter('status', value, 'all'),
    [setFilter]
  );

  const handleVerdictFilterChange = useCallback(
    (value: VerdictFilter) => setFilter('verdict', value, 'all'),
    [setFilter]
  );

  const handleDateRangeFilterChange = useCallback(
    (value: DateRangeFilter) => setFilter('date_range', value, 'all'),
    [setFilter]
  );

  const handleDateSortOrderChange = useCallback(
    (value: DateSortOrder) => setFilter('date_sort', value, 'desc'),
    [setFilter]
  );

  const handlePageChange = useCallback(
    (page: number) => {
      const next = Math.max(1, page);
      updateParams({ page: next === 1 ? null : String(next) });
    },
    [updateParams]
  );

  const handleClearFilters = useCallback(() => {
    // Reseteamos también el input para no esperar al debounce de 300 ms.
    setSearchQuery('');
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

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
      // Navegar de página dispara el refetch de SWR automáticamente.
      handlePageChange(currentPage - 1);
    } else {
      await fetchHistory();
    }
  }, [
    pendingDelete,
    history.length,
    deleteAnalysis,
    currentPage,
    handlePageChange,
    fetchHistory,
  ]);

  return (
    <>
      <div className="mb-6">
        <PageHeader
          title="Análisis anteriores"
          subtitle="Revisa y gestiona tus informes previos."
          actions={
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
          }
        />
      </div>

      <HistoryFilters
        searchQuery={searchQuery}
        onSearchQueryChange={handleSearchQueryChange}
        sourceTypeFilter={sourceTypeFilter}
        onSourceTypeFilterChange={handleSourceTypeFilterChange}
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
        verdictFilter={verdictFilter}
        onVerdictFilterChange={handleVerdictFilterChange}
        dateRangeFilter={dateRangeFilter}
        onDateRangeFilterChange={handleDateRangeFilterChange}
        dateSortOrder={dateSortOrder}
        onDateSortOrderChange={handleDateSortOrderChange}
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
        hasActiveFilters={hasActiveFilters}
        onClearFilters={handleClearFilters}
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
