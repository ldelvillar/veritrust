import { MarkdownHooks } from 'react-markdown';
import Link from 'next/link';
import Magnifier from '@/assets/Magnifier';
import LanguageIcon from '@/assets/Language';
import Heart from '@/assets/Heart';
import Robot from '@/assets/Robot';
import Document from '@/assets/Document';

interface ResultProps {
  result: {
    label: string;
    confidence: string | number;
    explanation: string;
  };
}

function parseScore(confidence: string | number): number {
  const n = parseFloat(String(confidence));
  if (isNaN(n)) return 0;
  return Math.round(n <= 1 ? n * 100 : n);
}

function getVerdictInfo(label: string): {
  text: string;
  description: string;
  textColor: string;
  bgColor: string;
} {
  const l = label.toLowerCase();
  if (l.includes('verdadera') || l.includes('real') || l.includes('true')) {
    return {
      text: 'Noticia verdadera',
      description:
        'El contenido muestra alta consistencia factual con fuentes médicas reputadas y bajos indicadores de información errónea.',
      textColor: 'text-emerald-700',
      bgColor: 'bg-emerald-100',
    };
  }
  if (l.includes('falsa') || l.includes('fake') || l.includes('false')) {
    return {
      text: 'Noticia falsa',
      description:
        'El contenido contiene afirmaciones que contradicen o no pueden ser verificadas con fuentes médicas reconocidas.',
      textColor: 'text-red-700',
      bgColor: 'bg-red-100',
    };
  }
  return {
    text: 'Resultado incierto',
    description:
      'No se ha podido determinar con certeza la veracidad del contenido. Se recomienda consultar fuentes adicionales.',
    textColor: 'text-yellow-700',
    bgColor: 'bg-yellow-100',
  };
}

function CredibilityGauge({ score }: { score: number }) {
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
            stroke="var(--color-primary)"
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
  const score = parseScore(result.confidence);
  const verdict = getVerdictInfo(result.label);

  return (
    <div className="flex w-full max-w-6xl flex-col gap-6 lg:items-start">
      <div className="flex w-full shrink-0 flex-col gap-8 lg:flex-row">
        {/* Puntuación de credibilidad */}
        <div className="flex flex-col rounded-xl border border-slate-200 bg-white p-6 shadow-sm lg:w-1/3">
          <h3 className="mb-4 text-center text-lg font-bold text-slate-600">
            Puntuación de credibilidad
          </h3>

          <div className="flex justify-center">
            <CredibilityGauge score={score} />
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

      <div className="mx-auto mt-4 flex w-fit items-center gap-2">
        <Link
          href="/"
          className="rounded-lg bg-primary px-3 py-2 text-white transition duration-300 hover:bg-primary/90"
        >
          Analizar otro texto
        </Link>
      </div>
    </div>
  );
}
