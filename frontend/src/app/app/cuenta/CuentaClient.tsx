'use client';

import { useCallback, useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import PageHeader from '@/components/PageHeader';
import { ApiError, fetchBlobWithAuth } from '@/lib/apiClient';
import { useAllAnalysesDeletion } from '@/hooks/useAllAnalysesDeletion';

import AccountSummaryCard from './_components/AccountSummaryCard';
import ExportDataCard from './_components/ExportDataCard';
import DangerZoneCard from './_components/DangerZoneCard';
import DeleteAllDialog from './_components/DeleteAllDialog';

interface CuentaClientProps {
  initialCount: number;
}

const EXPORT_ALL_PATH =
  '/history/export?source_type=all&verdict=all&sort=recent';

const EXPORT_FALLBACK_ERROR =
  'No se pudieron exportar tus datos. Inténtalo de nuevo.';

export default function CuentaClient({ initialCount }: CuentaClientProps) {
  const { getToken } = useAuth();

  const [count, setCount] = useState(initialCount);

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
  const [deletedCount, setDeletedCount] = useState<number | null>(null);

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
    const removed = count;
    const ok = await removeAll();
    if (!ok) return;
    setIsDialogOpen(false);
    setDeletedCount(removed);
    setCount(0);
  }, [count, removeAll]);

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
        <AccountSummaryCard totalCount={count} />

        <ExportDataCard
          totalCount={count}
          isExporting={isExporting}
          errorMessage={exportError}
          onExport={handleExport}
        />

        <DangerZoneCard
          totalCount={count}
          deletedCount={deletedCount}
          onRequestDelete={openDeleteDialog}
        />
      </div>

      <DeleteAllDialog
        open={isDialogOpen}
        count={count}
        isConfirming={isDeleting}
        errorMessage={deleteError}
        onConfirm={handleDeleteConfirm}
        onCancel={closeDeleteDialog}
      />
    </>
  );
}
