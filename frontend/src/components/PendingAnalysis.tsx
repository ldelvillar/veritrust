'use client';

import {
  type ComponentType,
  type ReactNode,
  type SVGProps,
  useEffect,
  useState,
  useSyncExternalStore,
} from 'react';
import Button from '@/components/Button';
import Bell from '@/assets/Bell';
import Check from '@/assets/Check';
import Chevron from '@/assets/Chevron';
import ClockIcon from '@/assets/Clock';
import DocumentIcon from '@/assets/Document';
import GlobeIcon from '@/assets/Globe';
import Heart from '@/assets/Heart';
import LanguageIcon from '@/assets/Language';
import Magnifier from '@/assets/Magnifier';
import Newspaper from '@/assets/Newspaper';
import RefreshIcon from '@/assets/Refresh';
import Scan from '@/assets/Scan';
import ShieldIcon from '@/assets/Shield';
import WarningIcon from '@/assets/Warning';
import { displayHostname } from '@/components/analysis-result/format';
import type {
  AnalysisStage,
  ReportView,
} from '@/components/analysis-result/types';

interface PendingAnalysisProps {
  createdAt: string;
  stage?: AnalysisStage | null;
  sourceType?: ReportView['source_type'];
  inputText?: string | null;
  inputUrl?: string | null;
  fileFilename?: string | null;
  connectionError?: string | null;
  onRetry?: () => void;
  actions?: ReactNode;
}

const STEPS = [
  {
    name: 'Preparando el contenido',
    description: 'Obteniendo y preparando el texto a analizar.',
    done: 'Contenido preparado',
    Icon: Scan,
  },
  {
    name: 'Agente Extractor',
    description: 'Extrayendo las afirmaciones médicas del texto.',
    done: 'Afirmaciones médicas extraídas',
    Icon: Magnifier,
  },
  {
    name: 'Agente Traductor',
    description: 'Traduciendo las afirmaciones al inglés clínico.',
    done: 'Afirmaciones traducidas al inglés clínico',
    Icon: LanguageIcon,
  },
  {
    name: 'Agente Investigador',
    description: 'Buscando evidencia en nuestras fuentes biomédicas.',
    done: 'Evidencia reunida de nuestras fuentes biomédicas',
    Icon: Newspaper,
  },
  {
    name: 'Agente Médico',
    description: 'Sopesando la evidencia y redactando el informe.',
    done: 'Informe redactado',
    Icon: Heart,
  },
] as const;

// Links and files replace the first step's description with their own.
const SOURCE_COPY: Record<
  ReportView['source_type'],
  { meta: string; prep?: string }
> = {
  text: { meta: 'Análisis de texto' },
  url: {
    meta: 'Análisis de enlace',
    prep: 'Descargando el artículo y extrayendo su texto.',
  },
  file: {
    meta: 'Análisis de archivo',
    prep: 'Leyendo el archivo y extrayendo su texto.',
  },
};

// Usual estimate for the full pipeline, in seconds.
const ESTIMATED_SECONDS = 480;
const ESTIMATED_MINUTES = ESTIMATED_SECONDS / 60;

// Once the estimate is passed with margin, warn and offer a way out.
const SLOW_AFTER_SECONDS = 600;

// The worker reports the real stage, translated here to the visible step.
const STAGE_INDEX: Record<AnalysisStage, number> = {
  preparing: 0,
  extractor: 1,
  translator: 2,
  investigator: 3,
  health_expert: 4,
};

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Local time only exists in the browser, so it is not drawn during SSR to avoid a hydration mismatch.
const subscribeNever = () => () => {};
const SENT_AT_FORMAT = new Intl.DateTimeFormat('es-ES', {
  hour: '2-digit',
  minute: '2-digit',
});

function formatSentAt(createdAt: string): string | null {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? null : SENT_AT_FORMAT.format(date);
}

type NotifyPermission = NotificationPermission | 'unsupported';

// Notification.permission has no native event, so a minimal store reads it safely during SSR and refreshes the UI when the user grants permission.
const notifyListeners = new Set<() => void>();

function subscribeNotifyPermission(callback: () => void): () => void {
  notifyListeners.add(callback);
  return () => notifyListeners.delete(callback);
}

function getNotifyPermission(): NotifyPermission {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission;
}

function requestNotifyPermission(): Promise<void> {
  if (!('Notification' in window)) return Promise.resolve();
  return Notification.requestPermission().then(() => {
    for (const listener of notifyListeners) listener();
  });
}

const NOTICE_TONE = {
  danger: 'border-danger/30 bg-danger-soft text-danger-ink',
  warning: 'border-warning/30 bg-warning-soft text-warning-ink',
} as const;

// Notice inside the reply, a connection error or a slower than usual Analysis.
function Notice({
  tone,
  Icon,
  title,
  children,
  actions,
  role,
}: {
  tone: keyof typeof NOTICE_TONE;
  Icon: ComponentType<SVGProps<SVGSVGElement>>;
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  role?: 'alert';
}) {
  return (
    <div
      role={role}
      className={`flex items-start gap-3.5 rounded-xl border px-4 py-3.5 ${NOTICE_TONE[tone]}`}
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-white">
        <Icon className="size-4.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold">{title}</p>
        <div className="mt-0.5 text-sm leading-relaxed">{children}</div>
        {actions ? (
          <div className="mt-3 flex flex-wrap gap-2">{actions}</div>
        ) : null}
      </div>
    </div>
  );
}

// The submitted content is shown as the user's message in the conversation.
function SubmittedContent({
  sourceType,
  inputText,
  inputUrl,
  fileFilename,
}: Pick<
  PendingAnalysisProps,
  'sourceType' | 'inputText' | 'inputUrl' | 'fileFilename'
>) {
  const bubble =
    'self-end border border-line bg-white rounded-tl-3xl rounded-tr-3xl rounded-br-md rounded-bl-3xl';

  if (sourceType === 'url' && inputUrl) {
    return (
      <a
        href={inputUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={`${bubble} flex w-105 max-w-full items-center gap-3.5 px-4 py-3.5 transition-colors hover:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none`}
      >
        <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-primary-soft text-primary">
          <GlobeIcon className="size-4.5" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <b className="text-sm font-bold text-ink">
            {displayHostname(inputUrl)}
          </b>
          <span className="truncate text-xs text-primary">{inputUrl}</span>
        </span>
      </a>
    );
  }

  if (sourceType === 'file' && fileFilename) {
    const extension = fileFilename.split('.').pop()?.toUpperCase() ?? '';
    return (
      <div
        className={`${bubble} flex w-105 max-w-full items-center gap-3.5 px-4 py-3.5`}
      >
        <span className="grid h-12 w-10 shrink-0 place-items-center rounded-lg bg-danger-soft text-2xs font-extrabold tracking-wide text-danger-ink">
          {extension}
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <b className="truncate text-sm font-bold text-ink">{fileFilename}</b>
          <span className="text-xs font-semibold text-muted">
            Archivo subido
          </span>
        </span>
      </div>
    );
  }

  if (!inputText) return null;
  return (
    <div
      className={`${bubble} max-h-60 max-w-140 overflow-y-auto px-4.5 py-3.5 text-base leading-relaxed whitespace-pre-wrap text-body`}
    >
      {inputText}
    </div>
  );
}

export default function PendingAnalysis({
  createdAt,
  stage,
  sourceType = 'text',
  inputText,
  inputUrl,
  fileFilename,
  connectionError,
  onRetry,
  actions,
}: PendingAnalysisProps) {
  const [elapsed, setElapsed] = useState(0);
  const [trailOpen, setTrailOpen] = useState(true);

  useEffect(() => {
    const parsed = new Date(createdAt).getTime();
    const startMs = Number.isNaN(parsed) ? Date.now() : parsed;
    const tick = () =>
      setElapsed(Math.max(0, Math.floor((Date.now() - startMs) / 1000)));

    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [createdAt]);

  const notifyPermission = useSyncExternalStore(
    subscribeNotifyPermission,
    getNotifyPermission,
    () => 'unsupported' as NotifyPermission
  );
  const sentAt = useSyncExternalStore(
    subscribeNever,
    () => formatSentAt(createdAt),
    () => null
  );

  // No stage yet (just enqueued), so the first step shows as active.
  const activeStep = stage != null ? STAGE_INDEX[stage] : 0;

  // Only time the steps whose start this tab has seen.
  const [seenStep, setSeenStep] = useState(activeStep);
  const [stepStarts, setStepStarts] = useState<Record<number, number>>({});
  if (activeStep !== seenStep) {
    setSeenStep(activeStep);
    setStepStarts(starts => ({ ...starts, [activeStep]: elapsed }));
  }
  const stepDuration = (index: number): string | null => {
    const start = stepStarts[index];
    const end = stepStarts[index + 1];
    return start != null && end != null ? formatElapsed(end - start) : null;
  };

  const copy = SOURCE_COPY[sourceType];
  const descriptionOf = (index: number) =>
    (index === 0 && copy.prep) || STEPS[index].description;
  const lastStep = STEPS.length - 1;
  const stepsLeft = lastStep - activeStep;

  const isSlow = elapsed >= SLOW_AFTER_SECONDS;
  const status = isSlow
    ? 'Está tardando más de lo habitual…'
    : `${descriptionOf(activeStep).replace(/\.$/, '')}…`;

  const minutesLeft = Math.ceil((ESTIMATED_SECONDS - elapsed) / 60);
  const eta =
    activeStep === lastStep || minutesLeft <= 0
      ? 'Casi listo'
      : minutesLeft === 1
        ? 'Queda ~1 min'
        : `Quedan ~${minutesLeft} min`;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col">
      <div className="flex flex-1 flex-col gap-7">
        <p className="flex items-center justify-center gap-2 text-sm font-semibold whitespace-nowrap text-muted">
          <DocumentIcon className="size-4" />
          {copy.meta}
          {sentAt && ` · enviado a las ${sentAt}`}
        </p>

        <SubmittedContent
          sourceType={sourceType}
          inputText={inputText}
          inputUrl={inputUrl}
          fileFilename={fileFilename}
        />

        <div className="flex items-start gap-3.5">
          <div
            aria-hidden="true"
            className="animate-pulse-ring relative isolate grid size-8.5 shrink-0 place-items-center rounded-xl bg-primary text-white"
          >
            <ShieldIcon className="size-4.5" />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-3 pt-0.5">
            <p className="-mb-2 text-sm leading-7.5 font-bold text-ink">
              VeriTrust
            </p>

            {connectionError ? (
              <Notice
                role="alert"
                tone="danger"
                Icon={WarningIcon}
                title="Se ha interrumpido la conexión"
                actions={
                  onRetry ? (
                    <Button variant="soft" onClick={onRetry}>
                      <RefreshIcon />
                      Reintentar ahora
                    </Button>
                  ) : null
                }
              >
                {connectionError}
              </Notice>
            ) : null}

            <div className="flex max-w-full items-center gap-2.5 py-1">
              <p
                role="status"
                className="animate-thinking text-base font-semibold"
              >
                {status}
              </p>
              <span className="text-sm font-semibold text-muted tabular-nums">
                {formatElapsed(elapsed)}
              </span>
              <button
                type="button"
                aria-label="Pasos del análisis"
                aria-expanded={trailOpen}
                aria-controls="pending-trail"
                onClick={() => setTrailOpen(open => !open)}
                className="grid size-6 cursor-pointer place-items-center rounded-md text-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              >
                <Chevron
                  aria-hidden
                  className={`size-3.5 transition-transform ${trailOpen ? 'rotate-180' : ''}`}
                />
              </button>
            </div>

            <ol
              id="pending-trail"
              hidden={!trailOpen}
              className="flex flex-col border-l-2 border-line py-0.5 pl-4"
            >
              {STEPS.map((step, index) => {
                if (index > activeStep) return null;
                const isDone = index < activeStep;
                const StepIcon = isDone ? Check : step.Icon;
                return (
                  <li
                    key={step.name}
                    aria-current={isDone ? undefined : 'step'}
                    className="grid grid-cols-[22px_minmax(0,1fr)_auto] items-start gap-2.5 py-1.75"
                  >
                    <span
                      className={`grid size-5.5 place-items-center rounded-full ${
                        isDone
                          ? 'bg-success-soft text-success-ink'
                          : 'bg-primary-soft text-primary'
                      }`}
                    >
                      <StepIcon className="size-3.25" />
                    </span>
                    <span className="flex flex-col gap-px text-sm leading-snug text-muted">
                      <b
                        className={`text-sm font-bold ${isDone ? 'text-body' : 'text-ink'}`}
                      >
                        {step.name}
                      </b>
                      {isDone ? step.done : descriptionOf(index)}
                    </span>
                    <span
                      className={`pt-0.5 text-xs font-semibold tabular-nums ${isDone ? 'text-muted' : 'text-primary'}`}
                    >
                      {isDone ? stepDuration(index) : 'en curso'}
                    </span>
                  </li>
                );
              })}
              {stepsLeft > 0 && (
                <li className="grid grid-cols-[22px_minmax(0,1fr)] items-start gap-2.5 py-1.75">
                  <span className="size-5.5 rounded-full border-[1.5px] border-dashed border-line-strong" />
                  <span className="text-sm leading-snug text-muted">
                    {stepsLeft} {stepsLeft === 1 ? 'paso más' : 'pasos más'}{' '}
                    antes del informe
                  </span>
                </li>
              )}
            </ol>

            {isSlow && (
              <Notice
                tone="warning"
                Icon={ClockIcon}
                title="Está tardando más de lo habitual"
                actions={
                  <>
                    <Button href="/app/historial" variant="soft">
                      Ir al historial
                    </Button>
                    <Button href="/app/analisis" variant="soft">
                      Analizar otro contenido
                    </Button>
                  </>
                }
              >
                El análisis sigue en marcha y esta página se actualizará sola al
                terminar. Puedes esperar aquí o volver más tarde: lo guardamos
                en tu historial. Si no llegara a completarse, se marcará como
                fallido y podrás reintentarlo.
              </Notice>
            )}

            <div className="flex gap-1.25 pt-1.5" aria-hidden="true">
              {['', '[animation-delay:.15s]', '[animation-delay:.3s]'].map(
                delay => (
                  <i
                    key={delay}
                    className={`animate-typing-dot size-1.75 rounded-full bg-primary ${delay}`}
                  />
                )
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="sticky bottom-6 mt-8 flex flex-wrap items-center gap-3 rounded-3xl border border-line-strong bg-white py-3.5 pr-3.5 pl-5 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.08)]">
        <div className="min-w-0 flex-[1_1_300px]">
          <p className="text-sm font-semibold text-ink">
            El informe aparecerá aquí en cuanto termine el análisis
          </p>
          <p className="mt-0.5 text-xs leading-snug text-muted">
            {isSlow
              ? `Lo normal son unos ${ESTIMATED_MINUTES} min.`
              : `Tiempo estimado: ${ESTIMATED_MINUTES} min · ${eta}.`}{' '}
            Puedes cerrar esta pestaña; lo guardamos en tu historial.
          </p>
        </div>
        {notifyPermission === 'granted' ? (
          <span className="inline-flex items-center gap-1.75 px-1 py-2.25 text-sm font-semibold whitespace-nowrap text-success-ink">
            <Check className="size-3.75" />
            Te avisaremos cuando termine
          </span>
        ) : notifyPermission === 'default' ? (
          <Button variant="soft" onClick={() => void requestNotifyPermission()}>
            <Bell />
            Avísame al terminar
          </Button>
        ) : null}
        {actions}
      </div>
    </div>
  );
}
