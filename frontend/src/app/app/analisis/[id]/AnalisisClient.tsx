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
import { usePlan } from '@/hooks/usePlan';
import UpgradePrompt from '@/components/UpgradePrompt';
import { formatPlanDate, type PlanUsage } from '@/lib/plan';
import type { paths } from '@/types/api';

type AnalysisDetail =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
type AnalysisStatus =
  paths['/analysis/{analysis_id}/status']['get']['responses']['200']['content']['application/json'];

interface AnalisisClientProps {
  id: string;
  initialData: AnalysisDetail;
}

// An Analysis older than the Plan's History window, still stored but hidden.
export function HiddenAnalysis() {
  const days = usePlan().limits?.history_days ?? null;
  return (
    <UpgradePrompt
      title={
        days === null
          ? 'Este análisis no está en tu historial visible'
          : `Este análisis tiene más de ${days} días`
      }
      className="mx-auto w-full max-w-2xl py-12"
    >
      {days !== null &&
        `Con el plan Gratis ves los análisis de los últimos ${days} días. `}
      No se ha borrado nada: con Pro recuperas todo tu historial.
    </UpgradePrompt>
  );
}

const REANALYZE_DESCRIPTION =
  'Se generará un informe nuevo con la evidencia médica más reciente. El resultado actual se reemplazará y esta acción no se puede deshacer.';

// Reanalyzing consumes one Allowance unit if it ends well, and the dialog says so.
function reanalyzeDescription(usage: PlanUsage | null): string {
  if (!usage) return REANALYZE_DESCRIPTION;
  if (usage.remaining === 0)
    return `${REANALYZE_DESCRIPTION} No te quedan análisis este mes; se renuevan el ${formatPlanDate(usage.resets_at)}.`;
  return `${REANALYZE_DESCRIPTION} Usará uno de los ${usage.remaining} análisis que te quedan este mes.`;
}

export default function AnalisisClient({
  id,
  initialData,
}: AnalisisClientProps) {
  const router = useRouter();
  const { limits, usage } = usePlan();
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
    error: detailError,
    refetch,
  } = useApiQuery<AnalysisDetail>(`/analysis/${id}`, {
    fallbackData: initialData,
  });

  const detail = data ?? initialData;
  const isPending = detail.status === 'pending';

  // While still 'pending', only status and stage are polled every 2s, and the report is fetched once at the end.
  const {
    data: statusData,
    error: statusError,
    refetch: refetchStatus,
  } = useApiQuery<AnalysisStatus>(isPending ? `/analysis/${id}/status` : null, {
    refreshInterval: 2000,
    onSuccess: latest => {
      if (latest.status !== 'pending') void refetch();
    },
  });

  const current =
    isPending && statusData?.status === 'pending'
      ? { ...detail, stage: statusData.stage }
      : detail;
  const pollError = statusError ?? detailError;
  // A polling failure freezes the waiting screen, so it is shown.
  const pollErrorMessage =
    current.status === 'pending' && pollError
      ? pollError instanceof ApiError
        ? pollError.message
        : 'Sin conexión con el servidor. Seguiremos reintentando automáticamente.'
      : null;
  // Notify when the Analysis finishes with the tab in the background.
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

  // origin is '' during SSR, and the dialog only renders after interaction (client).
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
    // Reopening returns the row to 'pending', so refetch to resume polling.
    if (success) await refetch();
  };

  const handleReanalyzeConfirm = async () => {
    const success = await reanalyze(id);
    // The row returns to 'pending', so close and refetch to resume polling.
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
    // Once the row is deleted, go back to the History (the page unmounts).
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

  // Only a finished report can be reanalyzed or shared.
  const headerActions = (
    <>
      {current.status === 'done' && reanalyzeButton}
      {current.status === 'done' && shareButton}
      {deleteButton}
    </>
  );

  // The Plan dropped to Free with the report open and the Analysis fell outside its window.
  if (detailError instanceof ApiError && detailError.code === 'PLAN_REQUIRED')
    return <HiddenAnalysis />;

  return (
    <>
      <AnalysisResult
        result={current}
        pdfLocked={limits?.pdf === false}
        headerActions={headerActions}
        onRetry={handleRetry}
        isRetrying={isRetrying}
        retryError={retryError}
        pollError={pollErrorMessage}
        onRetryPoll={refetchStatus}
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
        description={reanalyzeDescription(usage)}
        confirmDisabled={usage?.remaining === 0}
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
        locked={limits?.share === false}
      />
    </>
  );
}
