'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import AnalysisResult from '@/components/AnalysisResult';
import { ApiError } from '@/lib/apiClient';
import Button from '@/components/Button';
import ConfirmDialog from '@/components/ConfirmDialog';
import ShareDialog from '@/components/ShareDialog';
import Trash from '@/assets/Trash';
import LinkIcon from '@/assets/Link';
import RefreshIcon from '@/assets/Refresh';
import { SITE_CONFIG } from '@/config/site';
import { useApiQuery } from '@/hooks/useApiQuery';
import { useAnalysisDeletion } from '@/hooks/useAnalysisDeletion';
import { useAnalysisReanalysis } from '@/hooks/useAnalysisReanalysis';
import { useAnalysisRetry } from '@/hooks/useAnalysisRetry';
import { useAnalysisShare } from '@/hooks/useAnalysisShare';
import { useCompletionNotification } from '@/hooks/useCompletionNotification';
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
  const [reanalyzeOpen, setReanalyzeOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const {
    remove: deleteAnalysis,
    isDeleting,
    error: deleteError,
    setError: setDeleteError,
  } = useAnalysisDeletion();
  const { retry, isRetrying, error: retryError } = useAnalysisRetry();
  const {
    reanalyze,
    isReanalyzing,
    error: reanalyzeError,
    setError: setReanalyzeError,
  } = useAnalysisReanalysis();
  const {
    createShare,
    removeShare,
    isSharing,
    error: shareError,
    setError: setShareError,
  } = useAnalysisShare();

  const {
    data,
    error: pollError,
    refetch,
  } = useApiQuery<AnalysisDetail>(`/analysis/${id}`, {
    fallbackData: initialData,
    // Hacemos polling cada 2s mientras el análisis siga 'pending'
    refreshInterval: latest => (latest?.status === 'pending' ? 2000 : 0),
  });

  const current = data ?? initialData;
  // Un fallo de polling deja la pantalla de espera congelada: lo mostramos.
  const pollErrorMessage =
    current.status === 'pending' && pollError
      ? pollError instanceof ApiError
        ? pollError.message
        : 'Sin conexión con el servidor. Seguiremos reintentando automáticamente.'
      : null;
  // Avisa por notificación si el análisis termina con la pestaña en segundo plano.
  useCompletionNotification(id, current.status);

  useEffect(() => {
    if (current.status !== 'pending' && current.status !== 'failed') return;
    const originalTitle = document.title;
    document.title =
      current.status === 'pending'
        ? `Analizando... | ${SITE_CONFIG.name}`
        : `Análisis fallido | ${SITE_CONFIG.name}`;
    return () => {
      document.title = originalTitle;
    };
  }, [current.status]);

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

  const handleReanalyzeConfirm = async () => {
    const success = await reanalyze(id);
    // La fila vuelve a 'pending': cerramos y refrescamos para reanudar el polling.
    if (success) {
      setReanalyzeOpen(false);
      await refetch();
    }
  };

  const handleReanalyzeCancel = () => {
    if (isReanalyzing) return;
    setReanalyzeError(null);
    setReanalyzeOpen(false);
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

  const reanalyzeButton = (
    <Button
      variant="soft"
      onClick={() => {
        setReanalyzeError(null);
        setReanalyzeOpen(true);
      }}
    >
      <RefreshIcon className="size-4" />
      Volver a analizar
    </Button>
  );

  const shareButton = (
    <Button variant="soft" onClick={handleShareOpen}>
      <LinkIcon className="size-4" />
      Compartir
    </Button>
  );

  const deleteButton = (
    <Button
      variant="danger"
      onClick={() => {
        setDeleteError(null);
        setConfirmOpen(true);
      }}
    >
      <Trash className="size-4" />
      Eliminar
    </Button>
  );

  // Solo un informe terminado se puede volver a analizar o compartir.
  const headerActions = (
    <>
      {current.status === 'done' && reanalyzeButton}
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
        pollError={pollErrorMessage}
        onRetryPoll={refetch}
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

      <ConfirmDialog
        open={reanalyzeOpen}
        title="¿Volver a analizar este contenido?"
        description="Se generará un informe nuevo con la evidencia médica más reciente. El resultado actual se reemplazará y esta acción no se puede deshacer."
        confirmLabel="Volver a analizar"
        isConfirming={isReanalyzing}
        errorMessage={reanalyzeError}
        onConfirm={handleReanalyzeConfirm}
        onCancel={handleReanalyzeCancel}
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
