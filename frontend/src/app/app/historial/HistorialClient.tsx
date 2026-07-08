'use client';

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
import PlusBoxIcon from '@/assets/PlusBox';
import SortIcon from '@/assets/Sort';
import FunnelIcon from '@/assets/Funnel';
import CalendarIcon from '@/assets/Calendar';
import HistoryIcon from '@/assets/History';
import HistoryResultsTable from './_components/HistoryResultsTable';
import HistoryStatePanel from './_components/HistoryStatePanel';
import Button from '@/components/Button';
import ConfirmDialog from '@/components/ConfirmDialog';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';
import type { paths } from '@/types/api';

type SortOrder = 'recent' | 'oldest' | 'credibility_high' | 'credibility_low';
type DateRangeFilter = 'all' | '7d' | '30d' | '90d';
type SourceTypeFilter = 'all' | 'text' | 'file' | 'url';
type VerdictFilter = 'all' | 'real' | 'fake' | 'uncertain';
type StatusFilter = 'all' | 'done' | 'pending' | 'failed';

const PAGE_SIZE = 10;
const INITIAL_PATH = `/history?page=1&page_size=${PAGE_SIZE}&source_type=all&verdict=all&status=all&date_range=all&sort=recent`;

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
  { toneKey: 'ok', label: 'Verdaderos', verdictValue: 'real' as VerdictFilter },
  {
    toneKey: 'warn',
    label: 'Dudosos',
    verdictValue: 'uncertain' as VerdictFilter,
  },
  {
    toneKey: 'bad',
    label: 'Falsos',
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
    // Mientras haya análisis en curso, refrescamos para que pasen a hecho/fallido solos.
    refreshInterval: latest =>
      latest?.items?.some(item => item.status === 'pending') ? 5000 : 0,
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

  const handleSortOrderChange = useCallback(
    (value: SortOrder) => setFilter('sort', value, 'recent'),
    [setFilter]
  );

  const handleStatusFilterChange = useCallback(
    (value: StatusFilter) => setFilter('status', value, 'all'),
    [setFilter]
  );

  const handleDateRangeFilterChange = useCallback(
    (value: DateRangeFilter) => setFilter('date_range', value, 'all'),
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

  // Primera vez (sin análisis ni filtros): panel de bienvenida en vez de tabla vacía.
  const isFirstTimeEmpty =
    totalCount === 0 && !hasActiveFilters && !fetchError && !isLoading;

  if (isFirstTimeEmpty) {
    return (
      <>
        <div className="mb-6">
          <PageHeader
            eyebrow="Historial"
            title="Análisis anteriores"
            subtitle="Revisa, filtra y gestiona tus informes de credibilidad previos."
            actions={
              <Button href="/app/analisis">
                <PlusBoxIcon className="size-4.5" aria-hidden />
                Nuevo análisis
              </Button>
            }
          />
        </div>
        <HistoryStatePanel
          variant="violet"
          icon={<HistoryIcon className="size-9.5" />}
          eyebrow="Historial vacío"
          title="Aún no has analizado nada"
          lead={
            <>
              Cuando verifiques tu primer contenido, su informe de credibilidad
              aparecerá aquí, listo para revisar, filtrar y exportar cuando lo
              necesites.
            </>
          }
          actions={
            <>
              <Button href="/app/analisis" size="lg">
                <PlusBoxIcon className="size-4.5" aria-hidden />
                Analizar mi primer contenido
              </Button>
              <Button href="/ejemplo" variant="soft" size="lg" target="_blank">
                <DocumentIcon className="size-4.5" aria-hidden />
                Ver un informe de ejemplo
              </Button>
            </>
          }
        />
      </>
    );
  }

  return (
    <>
      {/* Page header */}
      <div className="mb-6">
        <PageHeader
          eyebrow="Historial"
          title="Análisis anteriores"
          subtitle="Revisa, filtra y gestiona tus informes de credibilidad previos."
          actions={
            <div className="flex w-full flex-wrap items-center gap-2.5 sm:w-auto">
              <div className="flex flex-1 flex-col items-end gap-1 sm:flex-none">
                <Button
                  variant="ghost"
                  onClick={handleExport}
                  disabled={isExporting || totalCount === 0}
                  aria-busy={isExporting}
                  className="w-full sm:w-auto"
                >
                  {isExporting ? (
                    <Spinner className="size-4 animate-spin" />
                  ) : (
                    <DownloadIcon className="size-4" aria-hidden />
                  )}
                  {isExporting ? 'Exportando…' : 'Exportar todo'}
                </Button>
                {exportError ? (
                  <p
                    role="alert"
                    className="text-xs font-semibold text-red-600"
                  >
                    {exportError}
                  </p>
                ) : null}
              </div>
              <Button href="/app/analisis" className="flex-1 sm:flex-none">
                <PlusBoxIcon className="size-4.5" aria-hidden />
                Nuevo análisis
              </Button>
            </div>
          }
        />
      </div>

      {/* Stat cards — clickable verdict filters */}
      <div className="mb-5.5 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
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

      {/* Toolbar: search + segmented type + status + date range + sort */}
      <div className="mb-4 flex flex-wrap items-center gap-2.5 md:gap-3">
        {/* Search */}
        <label className="relative flex h-11.5 min-w-0 flex-[1_1_100%] items-center gap-2.75 rounded-[13px] border border-line-strong bg-white px-3.5 text-faint transition focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10 md:min-w-55 md:flex-1">
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
          className="scrollbar-none flex h-11 flex-1 items-center gap-0.75 overflow-x-auto rounded-[13px] border border-line bg-surface p-1 md:h-11.5 md:flex-none md:overflow-visible"
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
                className={`inline-flex h-9 flex-1 items-center justify-center gap-1.75 rounded-[9px] px-2 text-[13.5px] font-semibold whitespace-nowrap transition md:h-9.5 md:flex-none md:px-3.5 ${
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

        {/* Status filter */}
        <div className="relative flex flex-[1_1_100%] items-center sm:flex-none">
          <span className="pointer-events-none absolute left-3 grid place-items-center text-faint">
            <FunnelIcon className="size-4" aria-hidden />
          </span>
          <select
            value={statusFilter}
            onChange={e =>
              handleStatusFilterChange(e.target.value as StatusFilter)
            }
            aria-label="Filtrar por estado"
            className="h-11.5 w-full cursor-pointer appearance-none rounded-[13px] border border-line-strong bg-white pr-10 pl-9.5 text-[13.5px] font-semibold text-body transition outline-none hover:border-primary hover:text-primary focus:border-primary focus:ring-4 focus:ring-primary/10 sm:w-auto"
          >
            <option value="all">Todos los estados</option>
            <option value="done">Completado</option>
            <option value="pending">En curso</option>
            <option value="failed">Fallido</option>
          </select>
          {/* Custom chevron */}
          <span
            className="pointer-events-none absolute top-1/2 right-3.75 size-2 -translate-y-[65%] rotate-45 rounded-[1px] border-r-2 border-b-2 border-faint"
            aria-hidden
          />
        </div>

        {/* Date range filter */}
        <div className="relative flex flex-[1_1_100%] items-center sm:flex-none">
          <span className="pointer-events-none absolute left-3 grid place-items-center text-faint">
            <CalendarIcon className="size-4" aria-hidden />
          </span>
          <select
            value={dateRangeFilter}
            onChange={e =>
              handleDateRangeFilterChange(e.target.value as DateRangeFilter)
            }
            aria-label="Filtrar por rango de fechas"
            className="h-11.5 w-full cursor-pointer appearance-none rounded-[13px] border border-line-strong bg-white pr-10 pl-9.5 text-[13.5px] font-semibold text-body transition outline-none hover:border-primary hover:text-primary focus:border-primary focus:ring-4 focus:ring-primary/10 sm:w-auto"
          >
            <option value="all">Todo el periodo</option>
            <option value="7d">Últimos 7 días</option>
            <option value="30d">Últimos 30 días</option>
            <option value="90d">Últimos 90 días</option>
          </select>
          {/* Custom chevron */}
          <span
            className="pointer-events-none absolute top-1/2 right-3.75 size-2 -translate-y-[65%] rotate-45 rounded-[1px] border-r-2 border-b-2 border-faint"
            aria-hidden
          />
        </div>

        {/* Sort select */}
        <div className="relative flex flex-[1_1_100%] items-center sm:flex-none">
          <span className="pointer-events-none absolute left-3 grid place-items-center text-faint">
            <SortIcon className="size-4" aria-hidden />
          </span>
          <select
            value={sortOrder}
            onChange={e => handleSortOrderChange(e.target.value as SortOrder)}
            aria-label="Ordenar"
            className="h-11.5 w-full cursor-pointer appearance-none rounded-[13px] border border-line-strong bg-white pr-10 pl-9.5 text-[13.5px] font-semibold text-body transition outline-none hover:border-primary hover:text-primary focus:border-primary focus:ring-4 focus:ring-primary/10 sm:w-auto"
          >
            <option value="recent">Más recientes</option>
            <option value="oldest">Más antiguos</option>
            <option value="credibility_high">Mayor credibilidad</option>
            <option value="credibility_low">Menor credibilidad</option>
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
