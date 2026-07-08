'use client';

import { useEffect, useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import Spinner from '@/assets/Spinner';
import Check from '@/assets/Check';
import Scan from '@/assets/Scan';
import Magnifier from '@/assets/Magnifier';
import LanguageIcon from '@/assets/Language';
import Newspaper from '@/assets/Newspaper';
import Heart from '@/assets/Heart';
import Bell from '@/assets/Bell';

interface PendingAnalysisProps {
  createdAt: string;
  stage?: string | null;
  connectionError?: string | null;
  onRetry?: () => void;
}

const STEPS = [
  {
    name: 'Preparando el contenido',
    description: 'Obteniendo y preparando el texto a analizar.',
    Icon: Scan,
  },
  {
    name: 'Agente Extractor',
    description: 'Extrayendo las afirmaciones médicas del texto.',
    Icon: Magnifier,
  },
  {
    name: 'Agente Traductor',
    description: 'Traduciendo las afirmaciones al inglés clínico.',
    Icon: LanguageIcon,
  },
  {
    name: 'Agente Investigador',
    description: 'Buscando evidencia en nuestras fuentes biomédicas.',
    Icon: Newspaper,
  },
  {
    name: 'Agente Médico',
    description: 'Evaluando con BioBERT y redactando el informe.',
    Icon: Heart,
  },
] as const;

// Pasado el límite duro del pipeline (10 min), un análisis aún pendiente está
// claramente atascado: dejamos de dar falsas garantías y ofrecemos una salida.
const SLOW_AFTER_SECONDS = 600;

// El worker reporta la etapa real; aquí la traducimos al paso visible.
const STAGE_INDEX: Record<string, number> = {
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

type NotifyPermission = NotificationPermission | 'unsupported';

// Notification.permission no tiene evento nativo; un store mínimo lo lee de forma
// segura en SSR y refresca la UI cuando el usuario concede el permiso.
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

export default function PendingAnalysis({
  createdAt,
  stage,
  connectionError,
  onRetry,
}: PendingAnalysisProps) {
  const [elapsed, setElapsed] = useState(0);

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

  // Sin etapa todavía (recién encolado): mostramos el primer paso como activo.
  const activeStep = stage != null ? (STAGE_INDEX[stage] ?? 0) : 0;

  const isSlow = elapsed >= SLOW_AFTER_SECONDS;
  const showReassurance = !isSlow && activeStep === STEPS.length - 1;

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex w-full max-w-2xl flex-col items-center gap-6 rounded-xl border border-line bg-white p-8 text-center shadow-sm md:p-10"
    >
      <div className="flex flex-col items-center gap-3">
        <Spinner className="size-10 animate-spin text-primary" />
        <h3 className="text-xl font-bold text-ink">Analizando contenido…</h3>
        <p className="max-w-md text-sm leading-relaxed text-muted">
          Nuestros agentes están analizando el contenido, buscando evidencia y
          evaluando las afirmaciones médicas. La página se actualizará
          automáticamente al terminar.
        </p>
        <p className="text-xs font-medium text-faint">
          <span className="tabular-nums" aria-hidden="true">
            {formatElapsed(elapsed)}
          </span>{' '}
          · {isSlow ? 'Tardando más de lo habitual' : 'Tiempo estimado: 8 min'}
        </p>
      </div>

      {connectionError ? (
        <div
          role="alert"
          className="w-full rounded-xl border border-red-200 bg-red-50 p-4 text-left"
        >
          <p className="text-sm font-bold text-red-800">
            Se ha interrumpido la conexión
          </p>
          <p className="mt-1 text-xs leading-relaxed text-red-700">
            {connectionError}
          </p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center justify-center rounded-lg border border-red-300 bg-white px-3.5 py-2 text-xs font-bold text-red-800 transition hover:bg-red-100 focus:ring-2 focus:ring-red-300 focus:outline-none"
            >
              Reintentar ahora
            </button>
          ) : null}
        </div>
      ) : null}

      <ol className="flex w-full flex-col gap-2.5 text-left">
        {STEPS.map((step, index) => {
          const isDone = index < activeStep;
          const isActive = index === activeStep;
          const StepIcon = step.Icon;

          return (
            <li
              key={step.name}
              aria-current={isActive ? 'step' : undefined}
              className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                isDone
                  ? 'border-emerald-100 bg-emerald-50'
                  : isActive
                    ? 'border-primary/30 bg-primary/5'
                    : 'border-line bg-white'
              }`}
            >
              <span
                className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                  isDone
                    ? 'bg-emerald-100 text-emerald-600'
                    : isActive
                      ? 'bg-primary/10 text-primary'
                      : 'bg-surface text-faint'
                }`}
              >
                {isDone ? (
                  <Check className="size-4" />
                ) : isActive ? (
                  <Spinner className="size-4 animate-spin" />
                ) : (
                  <StepIcon className="size-4" />
                )}
              </span>
              <div className="min-w-0">
                <p
                  className={`text-sm font-bold ${
                    isDone || isActive ? 'text-ink' : 'text-faint'
                  }`}
                >
                  {step.name}
                </p>
                <p
                  className={`text-xs leading-snug ${
                    isDone || isActive ? 'text-muted' : 'text-faint'
                  }`}
                >
                  {step.description}
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      {isSlow ? (
        <div className="w-full rounded-xl border border-amber-200 bg-amber-50 p-4 text-left">
          <p className="text-sm font-bold text-amber-800">
            Está tardando más de lo habitual
          </p>
          <p className="mt-1 text-xs leading-relaxed text-amber-700">
            El análisis sigue en marcha y esta página se actualizará sola al
            terminar. Puedes esperar aquí o volver más tarde: lo guardamos en tu
            historial. Si no llegara a completarse, se marcará como fallido y
            podrás reintentarlo.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link
              href="/app/historial"
              className="inline-flex items-center justify-center rounded-lg border border-amber-300 bg-white px-3.5 py-2 text-xs font-bold text-amber-800 transition hover:bg-amber-100 focus:ring-2 focus:ring-amber-300 focus:outline-none"
            >
              Ir al historial
            </Link>
            <Link
              href="/app/analisis"
              className="inline-flex items-center justify-center rounded-lg border border-amber-200 bg-white px-3.5 py-2 text-xs font-bold text-amber-700 transition hover:bg-amber-100 focus:ring-2 focus:ring-amber-200 focus:outline-none"
            >
              Analizar otro contenido
            </Link>
          </div>
        </div>
      ) : (
        <div className="w-full rounded-xl border border-line bg-surface-subtle p-4 text-left">
          {showReassurance && (
            <p className="mb-3 flex items-center gap-2 rounded-lg bg-primary/5 px-3 py-2 text-sm font-semibold text-primary">
              <Spinner className="size-4 animate-spin" />
              Casi listo, redactando el informe…
            </p>
          )}
          <p className="text-sm font-bold text-ink">
            Puedes cerrar esta pestaña
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            Seguimos analizando en segundo plano y guardamos el informe en tu
            historial; no perderás el resultado.
          </p>
          {notifyPermission === 'granted' ? (
            <p className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-emerald-700">
              <Bell className="size-3.5 shrink-0" />
              Te avisaremos cuando termine.
            </p>
          ) : notifyPermission === 'default' ? (
            <button
              type="button"
              onClick={() => void requestNotifyPermission()}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-line-strong bg-white px-3 py-2 text-xs font-bold text-body transition hover:border-primary hover:text-primary focus:ring-2 focus:ring-primary/20 focus:outline-none"
            >
              <Bell className="size-3.5 shrink-0" />
              Avísame al terminar
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
