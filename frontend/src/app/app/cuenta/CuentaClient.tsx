'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import PageHeader from '@/components/PageHeader';
import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';
import { useAllAnalysesDeletion } from '@/hooks/useAllAnalysesDeletion';
import { usePlan } from '@/hooks/usePlan';

import AccountSummaryCard from './_components/AccountSummaryCard';
import ExportDataCard from './_components/ExportDataCard';
import DangerZoneCard from './_components/DangerZoneCard';
import DeleteAllDialog from './_components/DeleteAllDialog';
import PlanCard from './_components/PlanCard';

interface CuentaClientProps {
  initialCount: number;
}

// Exportación completa de cualquier Plan (RGPD art. 20): incluye los análisis que la History oculta.
const EXPORT_ALL_PATH = '/account/export';

const EXPORT_FALLBACK_ERROR =
  'No se pudieron exportar tus datos. Inténtalo de nuevo.';

export default function CuentaClient({ initialCount }: CuentaClientProps) {
  const { getToken } = useAuth();

  const [count, setCount] = useState(initialCount);
  const { limits } = usePlan();
  const historyDays = limits?.history_days ?? null;

  // --- Exportar ---
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    setExportError(null);
    setIsExporting(true);
    try {
      const blob = await fetchBlobWithAuth(getToken, EXPORT_ALL_PATH);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'veritrust-mis-datos.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(
        err instanceof ApiError ? err.message : EXPORT_FALLBACK_ERROR
      );
    } finally {
      setIsExporting(false);
    }
  }, [getToken]);

  // --- Eliminar toda la actividad ---
  const {
    removeAll,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAllAnalysesDeletion();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  // 'all': se borró todo, pero el total no se conocía.
  const [deletedCount, setDeletedCount] = useState<number | 'all' | null>(null);
  // Con ventana de History, /history solo cuenta lo visible: el total real es desconocido hasta borrarlo todo.
  const knownCount =
    historyDays === null || deletedCount !== null ? count : null;

  const openDeleteDialog = useCallback(() => {
    setDeleteError(null);
    setIsDialogOpen(true);
  }, [setDeleteError]);

  const closeDeleteDialog = useCallback(() => {
    if (isDeleting) return;
    setDeleteError(null);
    setIsDialogOpen(false);
  }, [isDeleting, setDeleteError]);

  const handleDeleteConfirm = useCallback(async () => {
    const removed = knownCount;
    const ok = await removeAll();
    if (!ok) return;
    setIsDialogOpen(false);
    setDeletedCount(removed ?? 'all');
    setCount(0);
  }, [knownCount, removeAll]);

  return (
    <>
      <div className="mb-7">
        <PageHeader
          eyebrow="Datos"
          title="Datos personales"
          subtitle="Consulta tu cuenta y gestiona tus datos personales. Tienes control total sobre la información que VeriTrust guarda sobre ti."
        />
      </div>

      <div className="flex flex-col gap-5">
        <PlanCard />

        <AccountSummaryCard totalCount={count} historyDays={historyDays} />

        <ExportDataCard
          totalCount={knownCount}
          isExporting={isExporting}
          errorMessage={exportError}
          onExport={handleExport}
        />

        <DangerZoneCard
          totalCount={knownCount}
          deletedCount={deletedCount}
          onRequestDelete={openDeleteDialog}
        />
      </div>

      <DeleteAllDialog
        open={isDialogOpen}
        count={knownCount}
        isConfirming={isDeleting}
        errorMessage={deleteError}
        onConfirm={handleDeleteConfirm}
        onCancel={closeDeleteDialog}
      />
    </>
  );
}
