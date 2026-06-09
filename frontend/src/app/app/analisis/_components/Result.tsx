'use client';

import type { ReactNode } from 'react';
import { useEffect, useId, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import Link from 'next/link';
import { MarkdownHooks } from 'react-markdown';
import Check from '@/assets/Check';
import Chevron from '@/assets/Chevron';
import Cross from '@/assets/Cross';
import DocumentIcon from '@/assets/Document';
import DownloadIcon from '@/assets/Download';
import GlobeIcon from '@/assets/Globe';
import ListIcon from '@/assets/List';
import MedicalCross from '@/assets/MedicalCross';
import ShieldIcon from '@/assets/Shield';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import PendingAnalysis from './PendingAnalysis';
import PdfViewer from '@/components/PdfViewer';
import { fetchBlobWithAuth } from '@/lib/apiClient';
import { countBackedClaims, groupSourcesByClaim } from '@/lib/evidence';
import type { paths } from '@/types/api';

type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
type ClaimType = NonNullable<ResultType['claims']>[number];
type SourceType = NonNullable<ResultType['sources']>[number];
type Verdict = ResultType['verdict'];

// Vista común al informe propio (autenticado) y al público compartido: este
// último no trae datos de identidad, así que analysis_id es opcional.
type ReportView = Omit<ResultType, 'user_id' | 'analysis_id'> & {
  analysis_id?: string;
};

interface ResultProps {
  result: ReportView;
  headerActions?: ReactNode;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
  isPublic?: boolean;
}

const FAILURE_MESSAGES: Record<string, string> = {
  NO_MEDICAL_CLAIMS:
    'No se detectaron afirmaciones médicas verificables en el contenido proporcionado.',
  URL_EXTRACTION:
    'No se pudo extraer el contenido de la URL. Comprueba que el enlace sea válido y accesible.',
  CONNECTION:
    'No se pudo conectar con el motor de análisis. Inténtalo de nuevo en unos minutos.',
  SERVICE_UNAVAILABLE:
    'El servicio de análisis no estaba disponible y no se pudo procesar la noticia. Inténtalo de nuevo.',
  INTERNAL:
    'Ocurrió un error inesperado al procesar el análisis. Inténtalo de nuevo.',
  PDF_EXTRACTION:
    'No se pudo extraer texto del PDF. Puede estar protegido, dañado o ser un documento escaneado sin texto seleccionable.',
};

const SOURCE_TAGS: Record<string, string> = {
  text: 'Texto',
  url: 'Enlace',
  file: 'Archivo',
  pdf: 'PDF',
};

function ClockIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function BookIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H11v15H5.5A1.5 1.5 0 0 0 4 20.5z" />
      <path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H13v15h5.5a1.5 1.5 0 0 1 1.5 1.5z" />
    </svg>
  );
}

function FailedView({
  errorCode,
  onRetry,
  isRetrying,
  retryError,
}: {
  errorCode: string | null | undefined;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryError?: string | null;
}) {
  const message =
    (errorCode && FAILURE_MESSAGES[errorCode]) ?? FAILURE_MESSAGES.INTERNAL;

  return (
    <div className="flex w-full flex-col items-center gap-4 rounded-xl border border-red-100 bg-red-50 p-10 text-center shadow-sm">
      <WarningIcon className="size-10 text-red-500" />
      <h3 className="text-xl font-bold text-red-700">
        No se pudo completar el análisis
      </h3>
      <p className="max-w-md text-sm leading-relaxed text-red-600">{message}</p>
      <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            aria-busy={isRetrying}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-4 focus:ring-primary/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isRetrying && <Spinner className="size-4 animate-spin" />}
            {isRetrying ? 'Reintentando…' : 'Reintentar análisis'}
          </button>
        )}
        <Link
          href="/app/analisis"
          className={
            onRetry
              ? 'inline-flex items-center justify-center gap-2 rounded-xl border border-red-200 bg-white px-5 py-3 text-sm font-bold text-red-600 transition hover:bg-red-100 focus:ring-4 focus:ring-red-200 focus:outline-none'
              : 'inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-4 focus:ring-primary/20 focus:outline-none'
          }
        >
          Analizar otro contenido
        </Link>
      </div>
      {retryError && (
        <p role="alert" className="text-xs font-semibold text-red-600">
          {retryError}
        </p>
      )}
    </div>
  );
}

function getVerdictInfo(verdict: Verdict): {
  text: string;
  description: string;
  band: string;
} {
  if (verdict === 'real') {
    return {
      text: 'Noticia verdadera',
      description:
        'El contenido muestra alta consistencia factual con fuentes médicas reputadas y bajos indicadores de información errónea.',
      band: 'linear-gradient(135deg,#2bc488,#10a566 70%,#0c9059)',
    };
  }
  if (verdict === 'fake') {
    return {
      text: 'Noticia falsa',
      description:
        'El contenido contiene afirmaciones que contradicen o no pueden ser verificadas con fuentes médicas reconocidas.',
      band: 'linear-gradient(135deg,#e2607a,#d23c5d 70%,#c33051)',
    };
  }
  return {
    text: 'Resultado incierto',
    description:
      'No se ha podido determinar con certeza la veracidad del contenido. Se recomienda consultar fuentes adicionales.',
    band: 'linear-gradient(135deg,#e8b057,#d98e29 70%,#c97e1c)',
  };
}

function normalizeFraction(value: number): number {
  return value <= 1 ? value : value / 100;
}

function confidenceLabel(confidence: number | null | undefined): string | null {
  if (confidence == null) return null;
  const fraction = normalizeFraction(confidence);
  if (fraction >= 0.85) return 'Confianza alta';
  if (fraction >= 0.6) return 'Confianza media';
  return 'Confianza baja';
}

function CredibilityGauge({ score }: { score: number | null }) {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    // Incierto (score null): aro sin rellenar. Con puntuación: animamos al valor.
    const target =
      score === null
        ? circumference
        : circumference * (1 - Math.min(Math.max(score, 0), 100) / 100);
    const id = setTimeout(() => setOffset(target), 160);
    return () => clearTimeout(id);
  }, [score, circumference]);

  return (
    <div className="relative size-43">
      <svg width="172" height="172" className="-rotate-90">
        <circle
          cx="86"
          cy="86"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,.22)"
          strokeWidth="14"
        />
        {score !== null && (
          <circle
            cx="86"
            cy="86"
            r={radius}
            fill="none"
            stroke="#fff"
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-[stroke-dashoffset] duration-1000 ease-out"
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        {score === null ? (
          <>
            <span className="text-5xl leading-none font-black text-white">
              ?
            </span>
            <span className="mt-1 text-[13px] font-semibold tracking-wide text-white/80">
              Sin puntuación
            </span>
          </>
        ) : (
          <>
            <span className="text-5xl leading-none font-black text-white">
              {score}
            </span>
            <span className="mt-1 text-[13px] font-semibold tracking-wide text-white/80">
              / 100
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function ResultBand({ result }: { result: ReportView }) {
  const score = result.credibility ?? null;
  const verdict = getVerdictInfo(result.verdict);
  const confidence = confidenceLabel(result.confidence);
  const claimCount = result.claims?.length ?? 0;
  const sources = result.sources ?? [];
  const coverage = countBackedClaims(result.claims ?? [], sources);
  // Solo con fuentes (investigador ejecutado): los análisis antiguos no se cuentan.
  const showCoverage = coverage.total > 0 && sources.length > 0;
  const sourceText =
    result.source_type === 'url' ? result.input_url : result.input_text;
  const formattedDate = new Date(result.created_at).toLocaleString('es-ES', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className="relative grid overflow-hidden rounded-3xl text-white shadow-[0_18px_44px_rgba(0,0,0,.16)] lg:grid-cols-[272px_1fr] print:break-inside-avoid"
      style={{ background: verdict.band }}
    >
      <div className="flex flex-col items-center justify-center gap-4 border-b border-white/20 bg-white/5 px-6 py-8 text-center lg:border-r lg:border-b-0">
        <CredibilityGauge score={score} />
      </div>

      <div className="flex flex-col justify-center px-7 py-8">
        <span className="inline-flex w-fit items-center gap-2 rounded-full bg-white/20 px-3.5 py-1.5 text-xs font-bold tracking-wide uppercase">
          <WarningIcon className="size-3.75" />
          Veredicto global
        </span>
        <h2 className="mt-3.5 text-3xl leading-tight font-bold tracking-tight sm:text-[34px]">
          {verdict.text}
        </h2>
        <p className="mt-3 max-w-xl text-[15.5px] leading-relaxed font-medium text-white/90">
          {verdict.description}
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {confidence && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <ShieldIcon className="size-3.5 opacity-85" />
              {confidence}
            </span>
          )}
          {claimCount > 0 && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <ListIcon className="size-3.5 opacity-85" />
              {claimCount} {claimCount === 1 ? 'afirmación' : 'afirmaciones'}
            </span>
          )}
          {showCoverage && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <BookIcon className="size-3.5 opacity-85" />
              {coverage.backed}/{coverage.total} con evidencia
            </span>
          )}
          <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
            <ClockIcon className="size-3.5 opacity-85" />
            {formattedDate}
          </span>
        </div>

        {sourceText && (
          <div className="mt-4 flex max-w-xl items-center gap-2.5 rounded-xl bg-black/15 px-3.5 py-2.5">
            <span className="shrink-0 rounded-md bg-white/90 px-2 py-0.5 text-[11px] font-bold text-slate-900">
              {SOURCE_TAGS[result.source_type] ?? 'Texto'}
            </span>
            <span className="truncate text-[13px] font-medium text-white/90">
              {sourceText}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function MedicalExplanation({ explanation }: { explanation: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-3.5 border-b border-slate-100 bg-linear-to-b from-[#faf9fe] to-white px-6 py-5">
        <div className="relative grid size-12 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-emerald-600">
          <MedicalCross className="size-6" />
          <span className="absolute -right-0.5 -bottom-0.5 size-3.5 rounded-full border-[2.5px] border-white bg-emerald-500" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 text-base font-bold text-slate-900">
            Experto en salud
            <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-bold tracking-wide text-primary uppercase">
              Agente IA
            </span>
          </div>
          <p className="mt-0.5 text-[12.5px] text-slate-500">
            Contrasta cada afirmación con el consenso médico actual
          </p>
        </div>
      </div>

      <div className="px-6 py-5">
        <div className="prose max-w-none text-slate-700 prose-slate">
          <MarkdownHooks>{explanation}</MarkdownHooks>
        </div>
      </div>

      <div className="flex items-center gap-2.5 px-6 pt-1 pb-5 text-xs leading-relaxed text-slate-400">
        <ShieldIcon className="size-3.75 shrink-0" />
        <span>
          Explicación generada por el agente médico a partir del análisis. Tiene
          carácter orientativo y no sustituye el consejo de un profesional
          sanitario.
        </span>
      </div>
    </div>
  );
}

function getClaimStyle(verdict: Verdict): {
  Icon: typeof Check;
  text: string;
  tile: string;
  pill: string;
} {
  if (verdict === 'fake') {
    return {
      Icon: Cross,
      text: 'Falsa',
      tile: 'bg-red-50 text-red-700',
      pill: 'bg-red-50 text-red-700',
    };
  }
  if (verdict === 'real') {
    return {
      Icon: Check,
      text: 'Verdadera',
      tile: 'bg-emerald-50 text-emerald-700',
      pill: 'bg-emerald-50 text-emerald-700',
    };
  }
  return {
    Icon: WarningIcon,
    text: 'Dudosa',
    tile: 'bg-amber-50 text-amber-700',
    pill: 'bg-amber-50 text-amber-700',
  };
}

function SourceRow({ source }: { source: SourceType }) {
  const meta = sourceMeta(source);

  return (
    <li className="flex gap-3 border-t border-slate-100 py-3.5 first:border-t-0 first:pt-0.5 print:break-inside-avoid">
      <div className="grid size-7 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
        <BookIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm leading-snug font-bold text-slate-900 underline-offset-2 hover:text-primary hover:underline focus:ring-2 focus:ring-primary/20 focus:outline-none"
        >
          {source.title}
        </a>
        {meta && (
          <p className="mt-1 text-[11.5px] font-semibold text-slate-400">
            {meta}
          </p>
        )}
      </div>
    </li>
  );
}

function ClaimRow({
  claim,
  sources,
  showEvidence,
}: {
  claim: ClaimType;
  sources: SourceType[];
  showEvidence: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const style = getClaimStyle(claim.verdict);
  const ClaimIcon = style.Icon;
  const confidencePct = Math.round(normalizeFraction(claim.confidence) * 100);
  const sourceCount = sources.length;

  return (
    <div className="flex gap-3 border-t border-slate-100 py-4 first:border-t-0 first:pt-0.5 print:break-inside-avoid">
      <div
        className={`grid size-7 shrink-0 place-items-center rounded-lg ${style.tile}`}
      >
        <ClaimIcon className="size-4" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm leading-snug font-bold text-slate-900">
          {claim.text}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2.5">
          <span
            className={`rounded-md px-2 py-1 text-[10.5px] font-bold tracking-wide uppercase ${style.pill}`}
          >
            {style.text}
          </span>
          <span className="text-[11.5px] font-semibold text-slate-400">
            {confidencePct}% de confianza
          </span>
        </div>

        {showEvidence &&
          (sourceCount > 0 ? (
            <>
              <button
                type="button"
                onClick={() => setOpen(value => !value)}
                aria-expanded={open}
                aria-controls={panelId}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none print:hidden"
              >
                <BookIcon className="size-3.5" />
                {open ? 'Ocultar' : 'Ver'} {sourceCount}{' '}
                {sourceCount === 1 ? 'fuente' : 'fuentes'}
                <Chevron
                  className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
                  aria-hidden
                />
              </button>
              {/* Siempre en el DOM y colapsado con clases, para que el PDF
                  (print:block) muestre toda la evidencia aunque esté oculta. */}
              <ul
                id={panelId}
                aria-label="Fuentes que respaldan esta afirmación"
                className={`mt-2.5 rounded-xl border border-slate-100 bg-slate-50/70 px-3.5 ${
                  open ? 'block' : 'hidden print:block'
                }`}
              >
                {sources.map((source, index) => (
                  <SourceRow key={`${source.url}-${index}`} source={source} />
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-3 flex items-center gap-2 text-[12px] font-medium text-slate-400">
              <BookIcon className="size-3.5 shrink-0" />
              Sin evidencia directa en Europe PMC para esta afirmación.
            </p>
          ))}
      </div>
    </div>
  );
}

function sourceMeta(source: SourceType): string | null {
  const parts = [source.source, source.year].filter((part): part is string =>
    Boolean(part)
  );
  return parts.length > 0 ? parts.join(' · ') : null;
}

function SourcesCard({
  sources,
  title,
  caption,
}: {
  sources: SourceType[];
  title: string;
  caption: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <BookIcon className="size-4.5 text-primary" />
        {title}
      </h3>
      <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
        {caption}
      </p>

      <ul>
        {sources.map((source, index) => (
          <SourceRow key={`${source.url}-${index}`} source={source} />
        ))}
      </ul>

      <p className="mt-4 flex items-center gap-2 text-xs leading-relaxed text-slate-400">
        <ShieldIcon className="size-3.5 shrink-0" />
        Fuentes sugeridas automáticamente; verifica siempre la referencia
        original.
      </p>
    </div>
  );
}

const FLAT_SOURCES_CAPTION =
  'Literatura biomédica recuperada de Europe PMC para respaldar el análisis. La confianza del veredicto se ajusta según cuántas afirmaciones encuentran respaldo en estas fuentes.';

function ClaimsEvidence({
  claims,
  sources,
}: {
  claims: ClaimType[];
  sources: SourceType[];
}) {
  const hasEvidence = sources.length > 0;

  // Caso defensivo: fuentes sin afirmaciones → lista plana, sin perder nada.
  if (claims.length === 0) {
    return hasEvidence ? (
      <SourcesCard
        sources={sources}
        title="Fuentes"
        caption={FLAT_SOURCES_CAPTION}
      />
    ) : null;
  }

  // Análisis antiguos (previos al investigador) no tienen fuentes: no decimos
  // "sin evidencia" porque nunca llegó a buscarse.
  if (!hasEvidence) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <ListIcon className="size-4.5 text-primary" />
          Afirmaciones detectadas
        </h3>
        <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
          Cada afirmación verificable se evalúa por separado con el modelo
          BioBERT.
        </p>
        {claims.map((claim, index) => (
          <ClaimRow
            key={index}
            claim={claim}
            sources={[]}
            showEvidence={false}
          />
        ))}
      </div>
    );
  }

  const { groups, unmatched } = groupSourcesByClaim(claims, sources);
  const backed = groups.filter(group => group.sources.length > 0).length;

  return (
    <>
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <ListIcon className="size-4.5 text-primary" />
          Afirmaciones y evidencia
        </h3>
        <p className="mt-1 mb-3 text-[13px] leading-relaxed text-slate-500">
          Cada afirmación se evalúa con BioBERT y se enlaza con la literatura
          biomédica de Europe PMC que la respalda.
        </p>
        <p className="mb-4 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-[13px] font-semibold text-primary">
          <BookIcon className="size-4 shrink-0" />
          {backed} de {claims.length}{' '}
          {claims.length === 1
            ? 'afirmación respaldada'
            : 'afirmaciones respaldadas'}{' '}
          por literatura biomédica
        </p>
        {groups.map((group, index) => (
          <ClaimRow
            key={index}
            claim={group.claim}
            sources={group.sources}
            showEvidence
          />
        ))}
      </div>

      {unmatched.length > 0 && (
        <SourcesCard
          sources={unmatched}
          title="Otras fuentes relacionadas"
          caption="Fuentes recuperadas para el conjunto del texto que no se han asignado a una afirmación concreta."
        />
      )}
    </>
  );
}

function AnalyzedPdf({
  analysisId,
  filename,
}: {
  analysisId: string;
  filename?: string | null;
}) {
  const { getToken } = useAuth();
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    fetchBlobWithAuth(getToken, `/analysis/${analysisId}/pdf`)
      .then(blob => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setFailed(true);
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [analysisId, getToken]);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:hidden">
      <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <DocumentIcon className="size-4.5 text-primary" />
        Documento analizado
      </h3>
      <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
        {filename ?? 'PDF original que se verificó.'}
      </p>
      {failed ? (
        <p className="flex items-center gap-2 text-[13px] font-medium text-slate-400">
          <WarningIcon className="size-4 shrink-0 text-amber-500" />
          No se pudo cargar el PDF.
        </p>
      ) : url ? (
        <PdfViewer file={url} />
      ) : (
        <div className="flex min-h-40 items-center justify-center">
          <Spinner className="size-6 animate-spin text-primary" />
        </div>
      )}
    </div>
  );
}

function AnalyzedContent({
  result,
  isPublic,
}: {
  result: ReportView;
  isPublic: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();

  // Análisis por PDF: el binario requiere auth, así que en la vista pública
  // mostramos el texto extraído (cae a la rama de texto de abajo).
  if (result.source_type === 'pdf' && !isPublic && result.analysis_id) {
    return (
      <AnalyzedPdf
        analysisId={result.analysis_id}
        filename={result.pdf_filename}
      />
    );
  }

  // Análisis por URL: mostramos el enlace en lugar del texto completo.
  if (result.source_type === 'url') {
    if (!result.input_url) return null;
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:break-inside-avoid">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <GlobeIcon className="size-4.5 text-primary" />
          Contenido analizado
        </h3>
        <p className="mt-1 mb-3 text-[13px] leading-relaxed text-slate-500">
          Enlace de la noticia que se verificó.
        </p>
        <a
          href={result.input_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-semibold break-all text-primary underline-offset-2 hover:underline focus:ring-2 focus:ring-primary/20 focus:outline-none"
        >
          {result.input_url}
        </a>
      </div>
    );
  }

  const text = result.input_text;
  if (!text) return null;

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm print:break-inside-avoid">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <DocumentIcon className="size-4.5 text-primary" />
          Contenido analizado
        </h3>
        <button
          type="button"
          onClick={() => setOpen(value => !value)}
          aria-expanded={open}
          aria-controls={panelId}
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 bg-primary/5 px-2.5 py-1.5 text-[12px] font-bold text-primary transition hover:bg-primary/10 focus:ring-2 focus:ring-primary/20 focus:outline-none print:hidden"
        >
          {open ? 'Ocultar' : 'Ver'} texto analizado
          <Chevron
            className={`size-3.5 transition-transform ${open ? 'rotate-180' : ''}`}
            aria-hidden
          />
        </button>
      </div>
      <p className="mt-1 text-[13px] leading-relaxed text-slate-500">
        El texto original tal y como se envió a verificar.
      </p>
      {/* Siempre en el DOM y colapsado con clases, para que el PDF (print:block)
          imprima el texto completo aunque esté oculto en pantalla. */}
      <div id={panelId} className={open ? 'block' : 'hidden print:block'}>
        <p className="mt-4 max-h-96 overflow-y-auto rounded-xl border border-slate-100 bg-slate-50/70 p-4 text-sm leading-relaxed whitespace-pre-wrap text-slate-700 print:max-h-none print:overflow-visible print:border-0 print:bg-transparent print:p-0">
          {text}
        </p>
      </div>
    </div>
  );
}

function Disclaimer() {
  return (
    <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 print:break-inside-avoid">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl border border-amber-200 bg-white text-amber-700">
        <WarningIcon className="size-4.5" />
      </div>
      <div>
        <h4 className="text-[13.5px] font-bold text-amber-800">
          Herramienta orientativa
        </h4>
        <p className="mt-0.5 text-[12.5px] leading-relaxed text-amber-700">
          Veritrust evalúa la credibilidad de la información. No emite
          diagnósticos ni sustituye la consulta con un profesional sanitario.
        </p>
      </div>
    </div>
  );
}

const SOFT_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-xl border border-[#dcd9ee] bg-white px-4 py-2.5 text-sm font-semibold text-[#33344c] transition hover:border-primary hover:text-primary focus:ring-2 focus:ring-primary/20 focus:outline-none';

// Cabecera/pie con marca que solo aparecen al imprimir (PDF), no en pantalla.
function PrintHeader({ createdAt }: { createdAt: string }) {
  const formattedDate = new Date(createdAt).toLocaleDateString('es-ES', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="hidden items-center justify-between border-b border-slate-200 pb-4 print:flex">
      <div className="flex items-center gap-2">
        {/* eslint-disable-next-line @next/next/no-img-element -- the SVG Logo embeds a pattern image that Chromium prints blank; a raster <img> prints reliably */}
        <img
          src="/images/logo-1316x1316-no-bg.png"
          alt="VeriTrust"
          width={24}
          height={24}
          className="h-6 w-6"
        />
        <span className="text-lg font-bold tracking-tight text-slate-900">
          VeriTrust
        </span>
      </div>
      <span className="text-xs font-semibold text-slate-500">
        Informe de credibilidad · {formattedDate}
      </span>
    </div>
  );
}

function PrintFooter() {
  return (
    <div className="hidden border-t border-slate-200 pt-4 text-[11px] leading-relaxed text-slate-400 print:block">
      Informe generado por VeriTrust ·{' '}
      <a
        href="https://tfg-hazel.vercel.app"
        className="font-semibold text-slate-500 underline-offset-2 hover:underline"
      >
        tfg-hazel.vercel.app
      </a>
      . Herramienta orientativa de credibilidad: no emite diagnósticos ni
      sustituye el consejo de un profesional sanitario.
    </div>
  );
}

export default function Result({
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
          <div className="text-[11px] font-bold tracking-wider text-primary uppercase">
            Informe de credibilidad
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-[25px]">
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
