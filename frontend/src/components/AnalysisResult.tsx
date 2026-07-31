'use client';

import type { ReactNode } from 'react';
import ClockIcon from '@/assets/Clock';
import DownloadIcon from '@/assets/Download';
import Button from './Button';
import PageHeader from './PageHeader';
import PendingAnalysis from './PendingAnalysis';
import AnalyzedContent from './analysis-result/AnalyzedContent';
import ClaimsEvidence from './analysis-result/ClaimsEvidence';
import Disclaimer from './analysis-result/Disclaimer';
import FailedView from './analysis-result/FailedView';
import FeedbackCard from './analysis-result/FeedbackCard';
import MedicalExplanation from './analysis-result/MedicalExplanation';
import PrintFooter from './analysis-result/PrintFooter';
import PrintHeader from './analysis-result/PrintHeader';
import ResultBand from './analysis-result/ResultBand';
import { formatDuration } from './analysis-result/format';
import type { ReportView } from './analysis-result/types';

interface ResultProps {
  result: ReportView;
  headerActions?: ReactNode;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
  pollError?: string | null;
  onRetryPoll?: () => void;
  isPublic?: boolean;
}

export default function AnalysisResult({
  result,
  headerActions,
  onRetry,
  isRetrying,
  retryError,
  pollError,
  onRetryPoll,
  isPublic = false,
}: ResultProps) {
  if (result.status === 'pending') {
    return (
      <div className="mx-auto w-full max-w-2xl">
        {headerActions && (
          <div className="mb-4 flex justify-end">{headerActions}</div>
        )}
        <PendingAnalysis
          createdAt={result.created_at}
          stage={result.stage ?? null}
          connectionError={pollError ?? null}
          onRetry={onRetryPoll}
        />
      </div>
    );
  }

  if (result.status === 'failed') {
    return (
      <div className="mx-auto w-full max-w-2xl">
        {headerActions && (
          <div className="mb-4 flex justify-end">{headerActions}</div>
        )}
        <FailedView
          errorCode={result.error_code}
          onRetry={onRetry}
          isRetrying={isRetrying}
          retryError={retryError}
        />
      </div>
    );
  }

  const claims = result.claims ?? [];
  const sources = result.sources ?? [];
  const analyzedAt = new Date(
    result.completed_at ?? result.created_at
  ).toLocaleString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
  const duration = formatDuration(result.created_at, result.completed_at);

  // Imprime el informe
  const handleExport = () => {
    const formattedDate = new Date(result.created_at).toLocaleDateString(
      'es-ES'
    );
    const originalTitle = document.title;
    document.title = `Informe VeriTrust - ${formattedDate}`;
    window.addEventListener(
      'afterprint',
      () => {
        document.title = originalTitle;
      },
      { once: true }
    );
    window.print();
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <PrintHeader createdAt={result.created_at} />

      <PageHeader
        title="Resultado del análisis"
        subtitle="Resultado global combinado del sistema multiagente, con la explicación médica y el desglose afirmación por afirmación."
        actionsClassName="print:hidden"
        actions={
          <>
            <Button variant="soft" onClick={handleExport}>
              <DownloadIcon className="size-4" />
              Exportar PDF
            </Button>
            {headerActions}
          </>
        }
      />

      <ResultBand result={result} />

      <div className="flex min-w-0 flex-col gap-6">
        <AnalyzedContent result={result} isPublic={isPublic} />
        {result.explanation && (
          <MedicalExplanation explanation={result.explanation} />
        )}
        <ClaimsEvidence claims={claims} sources={sources} />
        {/* Solo el dueño valora su informe: la vista pública y el ejemplo no la muestran. */}
        {!isPublic && result.analysis_id && (
          <FeedbackCard
            analysisId={result.analysis_id}
            initialFeedback={result.feedback ?? null}
          />
        )}
        <Disclaimer />
      </div>

      {/* Los enlaces a /app/* requieren cuenta: se ocultan en la vista pública. */}
      {!isPublic && (
        <div className="flex flex-wrap gap-3 print:hidden">
          <Button href="/app/analisis" variant="soft">
            Analizar otro contenido
          </Button>
          <Button href="/app/ayuda" variant="soft">
            Cómo leer este informe
          </Button>
        </div>
      )}

      <p className="flex items-center gap-1.5 text-xs text-faint print:hidden">
        <ClockIcon className="size-3.5" />
        Analizado el {analyzedAt}
        {duration && ` · duró ${duration}`}
      </p>

      <PrintFooter />
    </div>
  );
}
