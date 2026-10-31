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
import UpgradePrompt, { ProLockedButton } from '@/components/UpgradePrompt';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { useHistoryExport } from '@/hooks/useHistoryExport';
import { useHistoryFilters } from '@/hooks/useHistoryFilters';
import { usePlan } from '@/hooks/usePlan';
import {
  PAGE_SIZE,
  isExportable,
  type HistoryItem,
  type HistoryPayload,
} from '@/lib/historyQuery';

interface HistorialClientProps {
  initialData: HistoryPayload;
}

export default function HistorialClient({ initialData }: HistorialClientProps) {
  const { limits } = usePlan();
  const toolsLocked = limits?.history_tools === false;
  const exportLocked = limits?.csv_export === false;
  const historyDays = limits?.history_days ?? null;

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
  } = useHistoryFilters(toolsLocked);

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
    // While analyses are pending, refresh so they turn done or failed on their own.
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
    // useAnalysisDeletion already refreshes the current page, so only step back if it became empty.
    if (wasLastOnPage && currentPage > 1) setPage(currentPage - 1);
  }, [pendingDelete, history.length, deleteAnalysis, currentPage, setPage]);

  // Global counts from the backend, independent of the page and of the filter itself.
  const verdictFacets = data?.verdict_counts ?? null;
  const canExport = isExportable(statusFilter);

  // Analyses older than the Plan's window are still stored, so the notice shows even with an empty list.
  const windowNote =
    historyDays !== null ? (
      <UpgradePrompt variant="inline" className="mb-4">
        Mostrando los últimos {historyDays} días. El historial completo, la
        búsqueda, los filtros y la exportación a CSV son del plan Pro.
      </UpgradePrompt>
    ) : null;

  // First time (no analyses or filters), a welcome panel instead of an empty table.
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
        {windowNote && <div className="mt-5">{windowNote}</div>}
      </>
    );
  }

  return (
    <>
      <div className="mb-6">
        <PageHeader
          eyebrow="Historial"
          title="Análisis anteriores"
          subtitle="Revisa, filtra y gestiona tus informes de credibilidad previos."
          actions={
            <div className="flex w-full flex-wrap items-center gap-2.5 sm:w-auto">
              <div className="flex flex-1 flex-col items-end gap-1 sm:flex-none">
                {exportLocked ? (
                  <ProLockedButton
                    title="Exportar a CSV es una función del plan Pro"
                    className="w-full sm:w-auto"
                  >
                    Exportar todo
                  </ProLockedButton>
                ) : (
                  <Button
                    variant="soft"
                    onClick={runExport}
                    disabled={isExporting || totalCount === 0 || !canExport}
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
                )}
                {exportError ? (
                  <p
                    role="alert"
                    className="text-xs font-semibold text-danger-ink"
                  >
                    {exportError}
                  </p>
                ) : !canExport ? (
                  <p className="text-xs font-semibold text-muted">
                    Solo se exportan análisis completados
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

      {windowNote}

      <HistoryStatCards
        verdictFilter={verdictFilter}
        verdictCounts={verdictFacets}
        onSelect={toolsLocked ? undefined : setVerdict}
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
        disabled={toolsLocked}
      />

      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-3.5">
        <div className="text-sm font-semibold text-muted">
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
            className="inline-flex items-center gap-1.75 rounded-lg bg-primary/8 px-3 py-1.5 text-sm font-semibold text-primary transition hover:bg-primary/15"
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
