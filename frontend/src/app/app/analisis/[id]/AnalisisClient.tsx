'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import AnalysisResult from '@/components/AnalysisResult';
import ConfirmDialog from '@/components/ConfirmDialog';
import ShareDialog from '@/components/ShareDialog';
import Trash from '@/assets/Trash';
import LinkIcon from '@/assets/Link';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { useAnalysisRetry } from '@/hooks/useAnalysisRetry';
import { useAnalysisShare } from '@/hooks/useAnalysisShare';
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
  const [shareOpen, setShareOpen] = useState(false);
  const {
    remove: deleteAnalysis,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAnalysisDeletion();
  const { retry, isRetrying, error: retryError } = useAnalysisRetry();
  const {
    createShare,
    removeShare,
    isSharing,
    error: shareError,
    setError: setShareError,
  } = useAnalysisShare();

  const { data, refetch } = useApiQuery<AnalysisDetail>(`/analysis/${id}`, {
    fallbackData: initialData,
    // Hacemos polling cada 2s mientras el análisis siga 'pending'
    refreshInterval: latest => (latest?.status === 'pending' ? 2000 : 0),
  });

  const current = data ?? initialData;
  // origin es '' en SSR; el diálogo solo se renderiza tras interacción (cliente).
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const shareToken = current.share_token ?? null;
  const shareUrl = shareToken ? `${origin}/r/${shareToken}` : null;

  const handleShareCreate = async () => {
    const token = await createShare(id);
    if (token) await refetch();
  };

  const handleShareRemove = async () => {
    const success = await removeShare(id);
    if (success) await refetch();
  };

  const handleShareOpen = () => {
    setShareError(null);
    setShareOpen(true);
  };

  const handleShareClose = () => {
    if (isSharing) return;
    setShareError(null);
    setShareOpen(false);
  };

  const handleRetry = async () => {
    const success = await retry(id);
    // Al reabrirse la fila vuelve a 'pending': refrescamos para reanudar el polling.
    if (success) await refetch();
  };

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

  const shareButton = (
    <button
      type="button"
      onClick={handleShareOpen}
      className="inline-flex items-center gap-2 rounded-xl border border-[#dcd9ee] bg-white px-3 py-2.5 text-sm font-bold text-[#33344c] transition hover:border-primary hover:text-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
    >
      <LinkIcon className="size-4" />
      Compartir
    </button>
  );

  const deleteButton = (
    <button
      type="button"
      onClick={() => {
        setDeleteError(null);
        setConfirmOpen(true);
      }}
      className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-white px-3 py-2.5 text-sm font-bold text-red-600 transition hover:bg-red-50 focus:ring-2 focus:ring-red-200 focus:outline-none"
    >
      <Trash className="size-4" />
      Eliminar
    </button>
  );

  // Solo se puede compartir un informe terminado.
  const headerActions = (
    <>
      {current.status === 'done' && shareButton}
      {deleteButton}
    </>
  );

  return (
    <>
      <AnalysisResult
        result={current}
        headerActions={headerActions}
        onRetry={handleRetry}
        isRetrying={isRetrying}
        retryError={retryError}
      />

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

      <ShareDialog
        open={shareOpen}
        shareUrl={shareUrl}
        isSharing={isSharing}
        error={shareError}
        onCreate={handleShareCreate}
        onRemove={handleShareRemove}
        onClose={handleShareClose}
      />
    </>
  );
}
