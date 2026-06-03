'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Result from '@/components/Result';
import ConfirmDialog from '@/components/ConfirmDialog';
import Trash from '@/assets/Trash';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import type { paths } from '@/types/api';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface AnalisisClientProps {
  id: string;
  initialData: AnalysisDetail;
}

export default function AnalisisClient({
  id,
  initialData,
}: AnalisisClientProps) {
  const router = useRouter();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const {
    remove: deleteAnalysis,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAnalysisDeletion();

  const { data } = useApiQuery<AnalysisDetail>(`/analysis/${id}`, {
    fallbackData: initialData,
    // El worker procesa el análisis en segundo plano: hacemos polling cada 2s
    // mientras siga 'pending' y paramos en cuanto termina ('done' o 'failed').
    refreshInterval: latest => (latest?.status === 'pending' ? 2000 : 0),
  });

  const handleDeleteConfirm = async () => {
    const success = await deleteAnalysis(id);
    // Al borrarse la fila, volvemos al historial (la página se desmonta).
    if (success) router.push('/app/historial');
  };

  const handleDeleteCancel = () => {
    if (isDeleting) return;
    setDeleteError(null);
    setConfirmOpen(false);
  };

  return (
    <>
      <div className="flex w-full max-w-2xl justify-end">
        <button
          type="button"
          onClick={() => {
            setDeleteError(null);
            setConfirmOpen(true);
          }}
          className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-3 py-2 text-sm font-bold text-red-600 transition hover:bg-red-50 focus:ring-2 focus:ring-red-200 focus:outline-none"
        >
          <Trash className="size-4" />
          Eliminar
        </button>
      </div>

      <Result result={data ?? initialData} />

      <ConfirmDialog
        open={confirmOpen}
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
