'use client';

import { useCallback, useMemo, useState } from 'react';
import Spinner from '@/assets/Spinner';
import DownloadIcon from '@/assets/Download';
import CrossIcon from '@/assets/Cross';
import Magnifier from '@/assets/Magnifier';
import DocumentIcon from '@/assets/Document';
import PlusBoxIcon from '@/assets/PlusBox';
import SortIcon from '@/assets/Sort';
import FunnelIcon from '@/assets/Funnel';
import CalendarIcon from '@/assets/Calendar';
import HistoryIcon from '@/assets/History';
import HistoryResultsTable from './_components/HistoryResultsTable';
import HistoryStatePanel from './_components/HistoryStatePanel';
import FilterSelect from './_components/FilterSelect';
import Button from '@/components/Button';
import ConfirmDialog from '@/components/ConfirmDialog';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { useHistoryExport } from '@/hooks/useHistoryExport';
import {
  useHistoryFilters,
  type DateRangeFilter,
  type SortOrder,
  type SourceTypeFilter,
  type StatusFilter,
  type VerdictFilter,
} from '@/hooks/useHistoryFilters';
import { PAGE_SIZE } from '@/lib/historyQuery';
import type { paths } from '@/types/api';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
type HistoryItem = HistoryPayload['items'][number];

interface HistorialClientProps {
  initialData: HistoryPayload;
}

const SOURCE_TYPE_OPTIONS = [
  { value: 'all' as SourceTypeFilter, label: 'Todos los tipos' },
  { value: 'text' as SourceTypeFilter, label: 'Texto' },
  { value: 'url' as SourceTypeFilter, label: 'Enlace' },
  { value: 'file' as SourceTypeFilter, label: 'Archivo' },
];

const STATUS_OPTIONS = [
  { value: 'all' as StatusFilter, label: 'Todos los estados' },
  { value: 'done' as StatusFilter, label: 'Completado' },
  { value: 'pending' as StatusFilter, label: 'En curso' },
  { value: 'failed' as StatusFilter, label: 'Fallido' },
];

const DATE_RANGE_OPTIONS = [
  { value: 'all' as DateRangeFilter, label: 'Todo el periodo' },
  { value: '7d' as DateRangeFilter, label: 'Últimos 7 días' },
  { value: '30d' as DateRangeFilter, label: 'Últimos 30 días' },
  { value: '90d' as DateRangeFilter, label: 'Últimos 90 días' },
];

const SORT_OPTIONS = [
  { value: 'recent' as SortOrder, label: 'Más recientes' },
  { value: 'oldest' as SortOrder, label: 'Más antiguos' },
  { value: 'credibility_high' as SortOrder, label: 'Mayor credibilidad' },
  { value: 'credibility_low' as SortOrder, label: 'Menor credibilidad' },
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
  ok: {
    numClass: 'text-verdict-real-ink',
    barStyle: 'var(--color-verdict-real)',
    ringColor: 'var(--color-verdict-real)',
  },
  warn: {
    numClass: 'text-verdict-uncertain-ink',
    barStyle: 'var(--color-verdict-uncertain)',
    ringColor: 'var(--color-verdict-uncertain)',
  },
  bad: {
    numClass: 'text-verdict-fake-ink',
    barStyle: 'var(--color-verdict-fake)',
    ringColor: 'var(--color-verdict-fake)',
  },
} as const;

type VerdictCounts = HistoryPayload['verdict_counts'];

// Cada tarjeta mapea a su conteo global por veredicto en la respuesta del historial.
const FACET_KEY: Record<VerdictFilter, keyof VerdictCounts> = {
  all: 'total',
  real: 'real',
  uncertain: 'uncertain',
  fake: 'fake',
};

export default function HistorialClient({ initialData }: HistorialClientProps) {
  const {
    searchQuery,
    sourceTypeFilter,
    verdictFilter,
    statusFilter,
    dateRangeFilter,
    sortOrder,
    currentPage,
    path,
    exportPath,
    isInitialQuery,
    hasActiveFilters,
    setSearchQuery,
    setSourceType,
    setVerdict,
    setStatus,
    setDateRange,
    setSort,
    setPage,
    clearFilters,
  } = useHistoryFilters();

  const [pendingDelete, setPendingDelete] = useState<HistoryItem | null>(null);

  const {
    runExport,
    isExporting,
    error: exportError,
  } = useHistoryExport(exportPath);

  const {
    remove: deleteAnalysis,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAnalysisDeletion();

  const {
    data,
    isLoading,
    error: fetchError,
    refetch: fetchHistory,
  } = useApiQuery<HistoryPayload>(path, {
    fallbackData: isInitialQuery ? initialData : undefined,
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
      setPage(currentPage - 1);
    } else {
      await fetchHistory();
    }
  }, [
    pendingDelete,
    history.length,
    deleteAnalysis,
    currentPage,
    setPage,
    fetchHistory,
  ]);

  // Conteos globales del backend, independientes de la página y del propio filtro.
  const verdictFacets = data?.verdict_counts ?? null;

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
                  variant="soft"
                  onClick={runExport}
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
                    className="text-xs font-semibold text-danger-ink"
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
              onClick={() => setVerdict(card.verdictValue)}
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

      {/* Toolbar: search + type + status + date range + sort */}
      <div className="mb-4 flex flex-wrap items-center gap-2.5 md:gap-3">
        {/* Search */}
        <label className="relative flex h-11.5 min-w-0 flex-[1_1_100%] items-center gap-2.75 rounded-[13px] border border-line-strong bg-white px-3.5 text-faint transition focus-within:border-primary focus-within:ring-4 focus-within:ring-primary/10 md:min-w-55 md:flex-1">
          <Magnifier className="size-4.5 shrink-0 text-faint" aria-hidden />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Buscar por título o fuente…"
            className="min-w-0 flex-1 border-none bg-transparent text-[14.5px] text-ink outline-none placeholder:text-faint"
          />
          {searchQuery ? (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              aria-label="Limpiar búsqueda"
              className="grid size-6 shrink-0 place-items-center rounded-[7px] transition hover:bg-primary/8 hover:text-body"
            >
              <CrossIcon className="size-3.75" />
            </button>
          ) : null}
        </label>

        {/* Source type filter */}
        <FilterSelect
          value={sourceTypeFilter}
          onChange={setSourceType}
          options={SOURCE_TYPE_OPTIONS}
          icon={<FunnelIcon className="size-4" aria-hidden />}
          ariaLabel="Filtrar por tipo"
          className="flex-[1_1_100%] sm:flex-none"
        />

        {/* Status filter */}
        <FilterSelect
          value={statusFilter}
          onChange={setStatus}
          options={STATUS_OPTIONS}
          icon={<FunnelIcon className="size-4" aria-hidden />}
          ariaLabel="Filtrar por estado"
          className="flex-[1_1_100%] sm:flex-none"
        />

        {/* Date range filter */}
        <FilterSelect
          value={dateRangeFilter}
          onChange={setDateRange}
          options={DATE_RANGE_OPTIONS}
          icon={<CalendarIcon className="size-4" aria-hidden />}
          ariaLabel="Filtrar por rango de fechas"
          className="flex-[1_1_100%] sm:flex-none"
        />

        {/* Sort select */}
        <FilterSelect
          value={sortOrder}
          onChange={setSort}
          options={SORT_OPTIONS}
          icon={<SortIcon className="size-4" aria-hidden />}
          ariaLabel="Ordenar"
          className="flex-[1_1_100%] sm:flex-none"
        />
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
            onClick={clearFilters}
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
        onPageChange={setPage}
        onDelete={handleDeleteRequest}
        deletingId={isDeleting ? (pendingDelete?.analysis_id ?? null) : null}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={clearFilters}
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
