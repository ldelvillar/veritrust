'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MarkdownHooks } from 'react-markdown';
import Check from '@/assets/Check';
import Cross from '@/assets/Cross';
import Heart from '@/assets/Heart';
import LanguageIcon from '@/assets/Language';
import ListIcon from '@/assets/List';
import Magnifier from '@/assets/Magnifier';
import MedicalCross from '@/assets/MedicalCross';
import Robot from '@/assets/Robot';
import ShieldIcon from '@/assets/Shield';
import WarningIcon from '@/assets/Warning';
import PendingAnalysis from '@/components/PendingAnalysis';
import { classifyVerdict } from '@/lib/credibility';
import type { paths } from '@/types/api';

type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];
type ClaimType = NonNullable<ResultType['claims']>[number];

interface ResultProps {
  result: ResultType;
  headerActions?: ReactNode;
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
};

const SOURCE_TAGS: Record<string, string> = {
  text: 'Texto',
  url: 'Enlace',
  file: 'Archivo',
};

const AGENTS = [
  {
    name: 'Agente Extractor',
    description:
      'Aísla las afirmaciones médicas verificables presentes en el texto original.',
    Icon: Magnifier,
    tile: 'bg-primary/10 text-primary',
  },
  {
    name: 'Agente Traductor',
    description:
      'Traduce las afirmaciones al inglés clínico para contrastarlas con el modelo.',
    Icon: LanguageIcon,
    tile: 'bg-sky-50 text-sky-600',
  },
  {
    name: 'Agente Médico',
    description:
      'Evalúa cada afirmación con el modelo BioBERT y redacta el informe médico.',
    Icon: Heart,
    tile: 'bg-emerald-50 text-emerald-600',
  },
];

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

function FailedView({ errorCode }: { errorCode: string | null | undefined }) {
  const message =
    (errorCode && FAILURE_MESSAGES[errorCode]) ?? FAILURE_MESSAGES.INTERNAL;

  return (
    <div className="flex w-full flex-col items-center gap-4 rounded-xl border border-red-100 bg-red-50 p-10 text-center shadow-sm">
      <WarningIcon className="size-10 text-red-500" />
      <h3 className="text-xl font-bold text-red-700">
        No se pudo completar el análisis
      </h3>
      <p className="max-w-md text-sm leading-relaxed text-red-600">{message}</p>
      <Link
        href="/app/analisis"
        className="mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white transition hover:bg-primary/90 focus:ring-4 focus:ring-primary/20 focus:outline-none"
      >
        Analizar otro contenido
      </Link>
    </div>
  );
}

function getVerdictInfo(label: string): {
  text: string;
  description: string;
  band: string;
} {
  const verdict = classifyVerdict(label);
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

function CredibilityGauge({ score }: { score: number }) {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    const clamped = Math.min(Math.max(score, 0), 100);
    const id = setTimeout(
      () => setOffset(circumference * (1 - clamped / 100)),
      160
    );
    return () => clearTimeout(id);
  }, [score, circumference]);

  return (
    <div className="relative size-[172px]">
      <svg width="172" height="172" className="-rotate-90">
        <circle
          cx="86"
          cy="86"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,.22)"
          strokeWidth="14"
        />
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
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl leading-none font-black text-white">
          {score}
        </span>
        <span className="mt-1 text-[13px] font-semibold tracking-wide text-white/80">
          / 100
        </span>
      </div>
    </div>
  );
}

function ResultBand({ result }: { result: ResultType }) {
  const score = result.credibility ?? 0;
  const verdict = getVerdictInfo(result.label ?? '');
  const segments = Math.max(0, Math.min(5, Math.round(score / 20)));
  const confidence = confidenceLabel(result.confidence);
  const claimCount = result.claims?.length ?? 0;
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
      className="relative grid overflow-hidden rounded-3xl text-white shadow-[0_18px_44px_rgba(0,0,0,.16)] lg:grid-cols-[272px_1fr]"
      style={{ background: verdict.band }}
    >
      <div className="flex flex-col items-center justify-center gap-4 border-b border-white/20 bg-white/5 px-6 py-8 text-center lg:border-r lg:border-b-0">
        <CredibilityGauge score={score} />
        <div className="flex items-center gap-1.5" aria-hidden="true">
          {[0, 1, 2, 3, 4].map(i => (
            <span
              key={i}
              className={`h-1.5 w-6.5 rounded-full ${
                i < segments ? 'bg-white' : 'bg-white/25'
              }`}
            />
          ))}
        </div>
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
      <div className="flex items-center gap-3.5 border-b border-slate-100 bg-gradient-to-b from-[#faf9fe] to-white px-6 py-5">
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

function getClaimStyle(label: string): {
  Icon: typeof Check;
  text: string;
  tile: string;
  pill: string;
} {
  const verdict = classifyVerdict(label);
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

function Claims({ claims }: { claims: ClaimType[] }) {
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

      {claims.map((claim, index) => {
        const style = getClaimStyle(claim.label);
        const ClaimIcon = style.Icon;
        const confidencePct = Math.round(
          normalizeFraction(claim.confidence) * 100
        );

        return (
          <div
            key={index}
            className="flex gap-3 border-t border-slate-100 py-4 first:border-t-0 first:pt-0.5"
          >
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
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AgentContributions() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
        <Robot className="size-4.5 text-primary" />
        Aportación de cada agente
      </h3>
      <p className="mt-1 mb-4 text-[13px] leading-relaxed text-slate-500">
        Qué hace cada especialista del sistema multiagente.
      </p>

      {AGENTS.map(agent => {
        const AgentIcon = agent.Icon;
        return (
          <div
            key={agent.name}
            className="flex gap-3 border-t border-slate-100 py-3.5 first:border-t-0 first:pt-0.5"
          >
            <div
              className={`grid size-9.5 shrink-0 place-items-center rounded-xl ${agent.tile}`}
            >
              <AgentIcon className="size-4.5" />
            </div>
            <div>
              <h4 className="text-[13.5px] font-bold text-slate-900">
                {agent.name}
              </h4>
              <p className="mt-0.5 text-[12.5px] leading-snug text-slate-500">
                {agent.description}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Disclaimer() {
  return (
    <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4">
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

export default function Result({ result, headerActions }: ResultProps) {
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
        <FailedView errorCode={result.error_code} />
      </div>
    );
  }

  const claims = result.claims ?? [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-wrap items-start gap-4">
        <div className="min-w-60 flex-1">
          <div className="text-[11px] font-bold tracking-wider text-primary uppercase">
            Informe de credibilidad
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-[25px]">
            Resultado del análisis
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-slate-500">
            Resultado global combinado de los tres agentes, con la explicación
            médica y el desglose afirmación por afirmación.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <Link href="/app/analisis" className={SOFT_BUTTON}>
            Nuevo análisis
          </Link>
          {headerActions}
        </div>
      </header>

      <ResultBand result={result} />

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr] lg:items-start">
        <div className="flex min-w-0 flex-col gap-6">
          {result.explanation && (
            <MedicalExplanation explanation={result.explanation} />
          )}
          {claims.length > 0 && <Claims claims={claims} />}
        </div>
        <div className="flex flex-col gap-6">
          <AgentContributions />
          <Disclaimer />
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link href="/app/analisis" className={SOFT_BUTTON}>
          Analizar otro contenido
        </Link>
        <Link href="/app/ayuda" className={SOFT_BUTTON}>
          Cómo leer este informe
        </Link>
      </div>
    </div>
  );
}
