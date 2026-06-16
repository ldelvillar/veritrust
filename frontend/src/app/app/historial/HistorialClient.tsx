'use client';

import Link from 'next/link';
import { useAuth } from '@clerk/nextjs';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Spinner from '@/assets/Spinner';
import DownloadIcon from '@/assets/Download';
import CrossIcon from '@/assets/Cross';
import Magnifier from '@/assets/Magnifier';
import TypeIcon from '@/assets/Type';
import LinkIcon from '@/assets/Link';
import DocumentIcon from '@/assets/Document';
import PlusIcon from '@/assets/Plus';
import SortIcon from '@/assets/Sort';
import type {
  DateSortOrder,
  SourceTypeFilter,
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
const DATE_SORTS = ['desc', 'asc'] as const satisfies readonly DateSortOrder[];
const VERDICTS = [
  'all',
  'real',
  'fake',
  'uncertain',
] as const satisfies readonly VerdictFilter[];

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

const SOURCE_TYPE_OPTIONS = [
  { id: 'all' as SourceTypeFilter, label: 'Todos' },
  { id: 'text' as SourceTypeFilter, label: 'Texto', Icon: TypeIcon },
  { id: 'url' as SourceTypeFilter, label: 'Enlace', Icon: LinkIcon },
  { id: 'file' as SourceTypeFilter, label: 'Archivo', Icon: DocumentIcon },
];

const STAT_CARDS = [
  {
    toneKey: 'all',
    label: 'Análisis totales',
    verdictValue: 'all' as VerdictFilter,
  },
  { toneKey: 'ok', label: 'Fiables', verdictValue: 'real' as VerdictFilter },
  {
    toneKey: 'warn',
    label: 'Dudosos',
    verdictValue: 'uncertain' as VerdictFilter,
  },
  {
    toneKey: 'bad',
    label: 'No fiables',
    verdictValue: 'fake' as VerdictFilter,
  },
];

const STAT_TONE_STYLES = {
  all: {
    numClass: 'text-primary',
    barStyle: 'linear-gradient(90deg,#7166ef,#5446dc)',
    activeRing: 'box-shadow: 0 0 0 2px #6356e6, var(--shadow-card)',
    ringColor: '#6356e6',
  },
  ok: { numClass: 'text-[#0e8e5b]', barStyle: '#13b877', ringColor: '#13b877' },
  warn: {
    numClass: 'text-[#b07a16]',
    barStyle: '#e0a13b',
    ringColor: '#e0a13b',
  },
  bad: {
    numClass: 'text-[#c23552]',
    barStyle: '#e0556b',
    ringColor: '#e0556b',
  },
} as const;

type VerdictCounts = HistoryPayload['verdict_counts'];
type SourceTypeCounts = HistoryPayload['source_type_counts'];

// Cada tarjeta mapea a su conteo global por veredicto en la respuesta del historial.
const FACET_KEY: Record<VerdictFilter, keyof VerdictCounts> = {
  all: 'total',
  real: 'real',
  uncertain: 'uncertain',
  fake: 'fake',
};

// Cada chip de tipo mapea a su conteo global por tipo de fuente.
const SOURCE_FACET_KEY: Record<SourceTypeFilter, keyof SourceTypeCounts> = {
  all: 'total',
  text: 'text',
  url: 'url',
  file: 'file',
};

export default function HistorialClient({ initialData }: HistorialClientProps) {
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
  const dateSortOrder = parseParam(
    searchParams.get('date_sort'),
    DATE_SORTS,
    'desc'
  );
  const urlSearch = (searchParams.get('search') ?? '').trim();
  const parsedPage = Number.parseInt(searchParams.get('page') ?? '1', 10);
  const currentPage =
    Number.isFinite(parsedPage) && parsedPage > 0 ? parsedPage : 1;

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

  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch]);

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
      status: 'all',
      date_range: 'all',
      date_sort: dateSortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history?${params.toString()}`;
  }, [currentPage, dateSortOrder, sourceTypeFilter, verdictFilter, urlSearch]);

  const exportPath = useMemo(() => {
    const params = new URLSearchParams({
      source_type: sourceTypeFilter,
      verdict: verdictFilter,
      date_sort: dateSortOrder,
    });
    if (urlSearch) params.set('search', urlSearch);
    return `/history/export?${params.toString()}`;
  }, [dateSortOrder, sourceTypeFilter, verdictFilter, urlSearch]);

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

  const history = useMemo<HistoryItem[]>(
    () => (Array.isArray(data?.items) ? data.items : []),
    [data]
  );
  const totalCount =
    typeof data?.count === 'number' ? data.count : history.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));
  const effectivePage = Math.min(currentPage, totalPages);

  const hasActiveFilters =
    searchQuery.trim() !== '' ||
    sourceTypeFilter !== 'all' ||
    verdictFilter !== 'all';

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

  const handleVerdictFilterChange = useCallback(
    (value: VerdictFilter) => setFilter('verdict', value, 'all'),
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
    const wasLastOnPage = history.length === 1;
    const success = await deleteAnalysis(pendingDelete.analysis_id);
    if (!success) return;
    setPendingDelete(null);
    if (wasLastOnPage && currentPage > 1) {
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

  // Conteos globales del backend, independientes de la página y del propio filtro.
  const verdictFacets = data?.verdict_counts ?? null;
  const sourceFacets = data?.source_type_counts ?? null;

  return (
    <>
      {/* Page header */}
      <div className="mb-6">
        <PageHeader
          title="Análisis anteriores"
          subtitle="Revisa, filtra y gestiona tus informes de credibilidad previos."
          actions={
            <div className="flex flex-wrap items-center gap-2.5">
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
                  <p
                    role="alert"
                    className="text-xs font-semibold text-red-600"
                  >
                    {exportError}
                  </p>
                ) : null}
              </div>
              <Link
                href="/app/analisis"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white shadow-[0_6px_16px_rgba(99,86,230,.28)] transition hover:bg-accent focus:ring-2 focus:ring-primary/20 focus:outline-none"
              >
                <PlusIcon className="size-4" aria-hidden />
                Nuevo análisis
              </Link>
            </div>
          }
        />
      </div>

      {/* Stat cards — clickable verdict filters */}
      <div className="mb-5.5 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
        {STAT_CARDS.map(card => {
          const isActive =
            verdictFilter === card.verdictValue ||
            (card.verdictValue === 'all' && verdictFilter === 'all');
          const styles =
            STAT_TONE_STYLES[card.toneKey as keyof typeof STAT_TONE_STYLES];
          const count = verdictFacets
            ? verdictFacets[FACET_KEY[card.verdictValue]]
            : 0;

          return (
            <button
              key={card.toneKey}
              type="button"
              onClick={() => handleVerdictFilterChange(card.verdictValue)}
              aria-pressed={isActive}
              className={`relative overflow-hidden rounded-[18px] border bg-white p-[18px_20px_20px] text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
                isActive ? 'border-transparent' : 'border-line'
              }`}
              style={
                isActive
                  ? {
                      boxShadow: `0 0 0 2px ${styles.ringColor}, 0 1px 2px rgba(20,22,44,.04), 0 10px 30px rgba(92,80,200,.06)`,
                    }
                  : undefined
              }
            >
              <div
                className={`text-[clamp(26px,3vw,32px)] leading-none font-bold tracking-tight ${styles.numClass}`}
              >
                {count}
              </div>
              <div className="mt-2 text-[12.5px] font-bold text-muted">
                {card.label}
              </div>
              <span
                className={`absolute inset-x-0 bottom-0 transition-all ${isActive ? 'h-1' : 'h-0.75'}`}
                style={{ background: styles.barStyle }}
                aria-hidden
              />
            </button>
          );
        })}
      </div>

      {/* Toolbar: search + segmented type + sort */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {/* Search */}
        <label className="relative flex h-11.5 min-w-55 flex-1 items-center gap-2.75 rounded-[13px] border border-line-strong bg-white px-3.5 text-faint transition focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10">
          <Magnifier className="size-4.5 shrink-0 text-faint" aria-hidden />
          <input
            type="text"
            value={searchQuery}
            onChange={e => handleSearchQueryChange(e.target.value)}
            placeholder="Buscar por título o fuente…"
            className="min-w-0 flex-1 border-none bg-transparent text-[14.5px] text-ink outline-none placeholder:text-faint"
          />
          {searchQuery ? (
            <button
              type="button"
              onClick={() => handleSearchQueryChange('')}
              aria-label="Limpiar búsqueda"
              className="grid size-6 shrink-0 place-items-center rounded-[7px] transition hover:bg-primary/8 hover:text-body"
            >
              <CrossIcon className="size-3.75" />
            </button>
          ) : null}
        </label>

        {/* Segmented source type filter */}
        <div
          className="flex h-11.5 items-center gap-0.75 rounded-[13px] border border-line bg-surface p-1"
          role="tablist"
          aria-label="Filtrar por tipo"
        >
          {SOURCE_TYPE_OPTIONS.map(opt => {
            const isActive = sourceTypeFilter === opt.id;
            const count = sourceFacets
              ? sourceFacets[SOURCE_FACET_KEY[opt.id]]
              : 0;
            return (
              <button
                key={opt.id}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => handleSourceTypeFilterChange(opt.id)}
                className={`inline-flex h-9.5 items-center gap-1.75 rounded-[9px] px-3.5 text-[13.5px] font-semibold whitespace-nowrap transition ${
                  isActive
                    ? 'bg-white text-primary shadow-sm'
                    : 'text-muted hover:text-body'
                }`}
              >
                {opt.label}
                <span
                  className={`min-w-5 rounded-full px-1.75 py-px text-center text-[11px] font-bold ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'bg-primary/5 text-faint'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Sort select */}
        <div className="relative flex items-center">
          <span className="pointer-events-none absolute left-3 grid place-items-center text-faint">
            <SortIcon className="size-4" aria-hidden />
          </span>
          <select
            value={dateSortOrder}
            onChange={e =>
              handleDateSortOrderChange(e.target.value as DateSortOrder)
            }
            aria-label="Ordenar por fecha"
            className="h-11.5 cursor-pointer appearance-none rounded-[13px] border border-line-strong bg-white pr-10 pl-9.5 text-[13.5px] font-semibold text-body transition outline-none hover:border-primary hover:text-primary focus:border-primary focus:ring-4 focus:ring-primary/10"
          >
            <option value="desc">Más recientes</option>
            <option value="asc">Más antiguos</option>
          </select>
          {/* Custom chevron */}
          <span
            className="pointer-events-none absolute top-1/2 right-3.75 size-2 -translate-y-[65%] rotate-45 rounded-[1px] border-r-2 border-b-2 border-faint"
            aria-hidden
          />
        </div>
      </div>

      {/* Result summary line */}
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3.5">
        <div className="text-[13.5px] font-semibold text-muted">
          {history.length > 0 ? (
            <>
              <b className="font-bold text-ink">{totalCount}</b>{' '}
              {totalCount === 1 ? 'análisis' : 'análisis'}
              {hasActiveFilters ? ' que coinciden' : ''}
            </>
          ) : isLoading ? null : (
            <span>Ningún análisis coincide</span>
          )}
        </div>
        {hasActiveFilters ? (
          <button
            type="button"
            onClick={handleClearFilters}
            className="inline-flex items-center gap-1.75 rounded-[9px] bg-primary/8 px-3 py-1.5 text-[13px] font-semibold text-primary transition hover:bg-primary/15"
          >
            <CrossIcon className="size-3.5" aria-hidden />
            Limpiar filtros
          </button>
        ) : null}
      </div>

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
