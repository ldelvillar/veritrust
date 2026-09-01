'use client';

import { useCallback, useMemo, useState } from 'react';
import Spinner from '@/assets/Spinner';
import DownloadIcon from '@/assets/Download';
import CrossIcon from '@/assets/Cross';
import DocumentIcon from '@/assets/Document';
import PlusBoxIcon from '@/assets/PlusBox';
import HistoryIcon from '@/assets/History';
import HistoryResultsTable from './_components/HistoryResultsTable';
import HistoryStatCards from './_components/HistoryStatCards';
import HistoryStatePanel from './_components/HistoryStatePanel';
import HistoryToolbar from './_components/HistoryToolbar';
import Button from '@/components/Button';
import ConfirmDialog from '@/components/ConfirmDialog';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { useHistoryExport } from '@/hooks/useHistoryExport';
import { useHistoryFilters } from '@/hooks/useHistoryFilters';
import { PAGE_SIZE } from '@/lib/historyQuery';
import type { paths } from '@/types/api';

type HistoryPayload =
  paths['/history']['get']['responses']['200']['content']['application/json'];
type HistoryItem = HistoryPayload['items'][number];

interface HistorialClientProps {
  initialData: HistoryPayload;
}

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

      <HistoryStatCards
        verdictFilter={verdictFilter}
        verdictCounts={verdictFacets}
        onSelect={setVerdict}
      />

      <HistoryToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sourceTypeFilter={sourceTypeFilter}
        onSourceTypeChange={setSourceType}
        statusFilter={statusFilter}
        onStatusChange={setStatus}
        dateRangeFilter={dateRangeFilter}
        onDateRangeChange={setDateRange}
        sortOrder={sortOrder}
        onSortChange={setSort}
      />

      {/* Result summary line */}
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3.5">
        <div className="text-[13.5px] font-semibold text-muted">
          {history.length > 0 ? (
            <>
              <b className="font-bold text-ink">{totalCount}</b> análisis
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
