'use client';

import { useEffect, useState } from 'react';
import Spinner from '@/assets/Spinner';
import Check from '@/assets/Check';
import Scan from '@/assets/Scan';
import Magnifier from '@/assets/Magnifier';
import LanguageIcon from '@/assets/Language';
import Newspaper from '@/assets/Newspaper';
import Heart from '@/assets/Heart';

interface PendingAnalysisProps {
  createdAt: string;
  stage?: string | null;
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

export default function PendingAnalysis({
  createdAt,
  stage,
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

  // Sin etapa todavía (recién encolado): mostramos el primer paso como activo.
  const activeStep = stage != null ? (STAGE_INDEX[stage] ?? 0) : 0;

  const showReassurance = activeStep === STEPS.length - 1;

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
          · Tiempo estimado: 8 min
        </p>
      </div>

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

      {showReassurance && (
        <p className="rounded-lg bg-primary/5 px-3.5 py-2 text-sm font-semibold text-primary">
          Casi listo, redactando el informe…
        </p>
      )}
    </div>
  );
}
