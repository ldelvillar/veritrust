'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import DownloadIcon from '@/assets/Download';
import PendingAnalysis from './PendingAnalysis';
import AnalyzedContent from './analysis-result/AnalyzedContent';
import ClaimsEvidence from './analysis-result/ClaimsEvidence';
import Disclaimer from './analysis-result/Disclaimer';
import FailedView from './analysis-result/FailedView';
import MedicalExplanation from './analysis-result/MedicalExplanation';
import PrintFooter from './analysis-result/PrintFooter';
import PrintHeader from './analysis-result/PrintHeader';
import ResultBand from './analysis-result/ResultBand';
import type { ReportView } from './analysis-result/types';

interface ResultProps {
  result: ReportView;
  headerActions?: ReactNode;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
  isPublic?: boolean;
}

const SOFT_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-[#dcd9ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#33344c] transition hover:border-primary hover:text-primary focus:ring-2 focus:ring-primary/20 focus:outline-none';

export default function AnalysisResult({
  result,
  headerActions,
  onRetry,
  isRetrying,
  retryError,
  isPublic = false,
}: ResultProps) {
  if (result.status === 'pending') {
    return (
      <div className="mx-auto w-full max-w-2xl">
        {headerActions && (
          <div className="mb-4 flex justify-end">{headerActions}</div>
        )}
        <PendingAnalysis createdAt={result.created_at} />
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

      <header className="flex flex-wrap items-start gap-4">
        <div className="min-w-60 flex-1">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-[25px]">
            Resultado del análisis
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-slate-500">
            Resultado global combinado del sistema multiagente, con la
            explicación médica y el desglose afirmación por afirmación.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5 print:hidden">
          <button type="button" onClick={handleExport} className={SOFT_BUTTON}>
            <DownloadIcon className="size-4" />
            Exportar PDF
          </button>
          {headerActions}
        </div>
      </header>

      <ResultBand result={result} />

      <div className="flex min-w-0 flex-col gap-6">
        <AnalyzedContent result={result} isPublic={isPublic} />
        {result.explanation && (
          <MedicalExplanation explanation={result.explanation} />
        )}
        <ClaimsEvidence claims={claims} sources={sources} />
        <Disclaimer />
      </div>

      {/* Los enlaces a /app/* requieren cuenta: se ocultan en la vista pública. */}
      {!isPublic && (
        <div className="flex flex-wrap gap-3 print:hidden">
          <Link href="/app/analisis" className={SOFT_BUTTON}>
            Analizar otro contenido
          </Link>
          <Link href="/app/ayuda" className={SOFT_BUTTON}>
            Cómo leer este informe
          </Link>
        </div>
      )}

      <PrintFooter />
    </div>
  );
}
