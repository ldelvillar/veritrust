import Link from 'next/link';
import { MarkdownHooks } from 'react-markdown';
import Magnifier from '@/assets/Magnifier';
import LanguageIcon from '@/assets/Language';
import Heart from '@/assets/Heart';
import Robot from '@/assets/Robot';
import Document from '@/assets/Document';
import WarningIcon from '@/assets/Warning';
import PendingAnalysis from '@/components/PendingAnalysis';
import { classifyVerdict } from '@/lib/credibility';
import type { paths } from '@/types/api';

type ResultType =
  paths['/analysis/{analysis_id}']['get']['responses']['200']['content']['application/json'];

interface ResultProps {
  result: ResultType;
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

function FailedView({ errorCode }: { errorCode: string | null | undefined }) {
  const message =
    (errorCode && FAILURE_MESSAGES[errorCode]) ?? FAILURE_MESSAGES.INTERNAL;

  return (
    <div className="flex w-full max-w-2xl flex-col items-center gap-4 rounded-xl border border-red-100 bg-red-50 p-10 text-center shadow-sm">
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
  textColor: string;
  bgColor: string;
  gaugeColor: string;
} {
  const verdict = classifyVerdict(label);
  if (verdict === 'real') {
    return {
      text: 'Noticia verdadera',
      description:
        'El contenido muestra alta consistencia factual con fuentes médicas reputadas y bajos indicadores de información errónea.',
      textColor: 'text-emerald-700',
      bgColor: 'bg-emerald-100',
      gaugeColor: '#10b981',
    };
  }
  if (verdict === 'fake') {
    return {
      text: 'Noticia falsa',
      description:
        'El contenido contiene afirmaciones que contradicen o no pueden ser verificadas con fuentes médicas reconocidas.',
      textColor: 'text-red-700',
      bgColor: 'bg-red-100',
      gaugeColor: '#ef4444',
    };
  }
  return {
    text: 'Resultado incierto',
    description:
      'No se ha podido determinar con certeza la veracidad del contenido. Se recomienda consultar fuentes adicionales.',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
    gaugeColor: '#f59e0b',
  };
}

function CredibilityGauge({ score, color }: { score: number; color: string }) {
  const r = 70;
  const cx = 96;
  const cy = 96;
  const circumference = 2 * Math.PI * r;
  const gaugeArc = circumference * 0.75;
  const progressArc = (Math.min(Math.max(score, 0), 100) / 100) * gaugeArc;

  return (
    <div className="relative size-48">
      <svg viewBox="0 0 192 192" className="size-full">
        <g transform={`rotate(135, ${cx}, ${cy})`}>
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke="#f1f5f9"
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${gaugeArc} ${circumference}`}
          />
          <circle
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="round"
            strokeDasharray={`${progressArc} ${circumference}`}
          />
        </g>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-5xl leading-none font-black text-slate-900">
          {score}
        </span>
        <span className="text-base font-bold text-slate-400">/ 100</span>
      </div>
    </div>
  );
}

const AGENTS = [
  {
    name: 'Agente Extractor',
    description:
      'Identifica y extrae las afirmaciones médicas presentes en el texto original.',
    icon: <Magnifier className="size-4" />,
  },
  {
    name: 'Agente Traductor',
    description:
      'Traduce las afirmaciones al inglés para asegurar la compatibilidad con el modelo de análisis.',
    icon: <LanguageIcon className="size-4" />,
  },
  {
    name: 'Agente Médico',
    description:
      'Evalúa las afirmaciones con el modelo BioBERT y redacta el informe médico final.',
    icon: <Heart className="size-4" />,
  },
];

export default function Result({ result }: ResultProps) {
  if (result.status === 'pending') {
    return <PendingAnalysis createdAt={result.created_at} />;
  }

  if (result.status === 'failed') {
    return <FailedView errorCode={result.error_code} />;
  }

  const score = result.credibility ?? 0;
  const verdict = getVerdictInfo(result.label ?? '');

  return (
    <div className="flex w-full max-w-6xl flex-col gap-6 lg:items-start">
      <div className="flex w-full shrink-0 flex-col gap-8 lg:flex-row">
        {/* Puntuación de credibilidad */}
        <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:w-1/3">
          <h3 className="mb-4 text-center text-lg font-bold text-slate-600">
            Puntuación de credibilidad
          </h3>

          <div className="flex justify-center">
            <CredibilityGauge score={score} color={verdict.gaugeColor} />
          </div>

          <div
            className={`mx-auto mt-4 flex w-fit items-center gap-2 rounded-full px-4 py-1.5 ${verdict.bgColor}`}
          >
            <span className={`text-sm font-bold ${verdict.textColor}`}>
              {verdict.text}
            </span>
          </div>

          <p className="mt-4 text-center text-sm leading-relaxed text-slate-500">
            {verdict.description}
          </p>
        </div>

        {/* Pipeline de agentes */}
        <div className="flex w-full flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:w-2/3">
          <div className="mb-5 flex items-center gap-2">
            <Robot className="size-5 text-primary" />
            <h3 className="text-xl font-bold text-slate-900">
              Pipeline de agentes
            </h3>
          </div>
          <div className="grid flex-1 grid-cols-1 gap-4 sm:grid-cols-3">
            {AGENTS.map(agent => (
              <div
                key={agent.name}
                className="flex flex-col gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4"
              >
                <div className="flex items-center gap-2 text-primary">
                  {agent.icon}
                  <span className="text-sm font-bold text-slate-900">
                    {agent.name}
                  </span>
                </div>
                <p className="flex-1 text-sm leading-snug text-slate-500">
                  {agent.description}
                </p>
                <span className="text-xs font-bold text-primary">
                  COMPLETADO
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-6">
        {/* Explicación Markdown */}
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-2 border-b border-slate-100 pb-4">
            <Document className="size-5 text-primary" />
            <h3 className="text-xl font-bold text-slate-900">
              Informe del agente médico
            </h3>
          </div>
          <div className="prose max-w-none text-slate-700 prose-slate">
            {result.explanation && (
              <MarkdownHooks>{result.explanation}</MarkdownHooks>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
