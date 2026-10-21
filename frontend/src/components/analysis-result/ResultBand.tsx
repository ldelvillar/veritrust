import QuestionIcon from '@/assets/Question';
import Tooltip from '@/components/Tooltip';
import {
  CONFIDENCE_LEVEL_LABEL,
  VERDICT_META,
  formatCoverage,
  getVerdictInfo,
} from './format';
import type { ReportView } from './types';

// Barra sobre la banda oscura; el ancho se acota a 0-100 aunque el backend redondee fuera.
function Bar({
  percent,
  track,
  fill,
}: {
  percent: number;
  track: string;
  fill: string;
}) {
  return (
    <div className={`rounded-full bg-white/14 ${track}`}>
      <span
        className={`block h-full rounded-full ${fill}`}
        style={{ width: `${Math.min(Math.max(percent, 0), 100)}%` }}
      />
    </div>
  );
}

function Meter({
  label,
  value,
  percent,
}: {
  label: string;
  value: string;
  percent: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm text-white/60">{label}</span>
      <strong className="text-base font-bold">{value}</strong>
      <Bar percent={percent} track="h-0.75" fill="bg-white" />
    </div>
  );
}

export default function ResultBand({ result }: { result: ReportView }) {
  const score = result.credibility ?? null;
  const verdict = getVerdictInfo(result.verdict);
  const meta = VERDICT_META[result.verdict];
  const level = result.confidence_level ?? null;
  const confidence =
    result.confidence != null ? Math.round(result.confidence * 100) : null;
  const coverage = result.evidence_coverage ?? null;

  const ariaLabel =
    score === null
      ? 'Puntuación de credibilidad: sin puntuación suficiente'
      : `Puntuación de credibilidad: ${score} de 100`;

  return (
    <div className="@container print:break-inside-avoid">
      <div className="grid rounded-3xl bg-ink-deep text-white shadow-[0_18px_44px_rgba(10,43,46,.18)] @4xl:grid-cols-[300px_minmax(0,1fr)]">
        <div className="flex flex-col justify-between gap-5 border-b border-white/10 p-6 @lg:px-8 @lg:py-7 @4xl:border-r @4xl:border-b-0">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold tracking-[.06em] text-white/65 uppercase">
              Veracidad
            </h2>
            <Tooltip
              className="relative inline-flex print:hidden"
              ariaLabel="Qué es la puntuación de credibilidad"
              trigger={
                <QuestionIcon className="size-4.25" aria-hidden="true" />
              }
              buttonClassName="grid size-7 place-items-center rounded-full bg-white/15 text-white transition hover:bg-white/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
              panelClassName="absolute top-full right-0 z-10 mt-2.25 w-65 rounded-xl bg-ink-deep px-3.5 py-3 text-left text-xs leading-normal font-medium text-surface-subtle shadow-[0_14px_34px_rgba(0,0,0,.32)] ring-1 ring-white/10 transition-opacity before:absolute before:right-3.25 before:bottom-full before:border-[7px] before:border-transparent before:border-b-ink-deep before:content-['']"
            >
              Puntuación de credibilidad (0-100): cuanto más alta, más probable
              es que el contenido sea veraz.
            </Tooltip>
          </div>
          <div
            className="flex items-baseline gap-2"
            role="img"
            aria-label={ariaLabel}
          >
            <b className="text-7xl leading-[.9] font-black tracking-[-.05em] @4xl:text-8xl">
              {score === null ? '?' : score}
            </b>
            <small className="shrink-0 text-lg font-semibold whitespace-nowrap text-white/55">
              {score === null ? 'Sin puntuación' : '/ 100'}
            </small>
          </div>
          <Bar percent={score ?? 0} track="h-1" fill={meta.solid} />
        </div>

        <div className="flex flex-col gap-3 p-6 @lg:px-9 @lg:py-7">
          <span
            className={`inline-flex items-center gap-2 text-sm font-bold tracking-[.06em] uppercase ${meta.text}`}
          >
            <span
              className={`size-2.5 rounded-full ${meta.solid}`}
              aria-hidden="true"
            />
            {meta.label}
          </span>
          <h2 className="text-3xl leading-tight font-extrabold tracking-tight">
            {verdict.text}
          </h2>
          <p className="max-w-150 text-base leading-normal text-pretty text-white/78">
            {verdict.description}
          </p>
          {(level || coverage != null) && (
            <div className="mt-2 grid gap-4 @lg:grid-cols-[repeat(2,minmax(0,220px))] @lg:gap-7">
              {level && (
                <Meter
                  label="Confianza en el veredicto"
                  value={
                    confidence != null
                      ? `${CONFIDENCE_LEVEL_LABEL[level]} · ${confidence}%`
                      : CONFIDENCE_LEVEL_LABEL[level]
                  }
                  percent={confidence ?? 0}
                />
              )}
              {coverage != null && (
                <Meter
                  label="Cobertura de evidencia"
                  value={formatCoverage(coverage)}
                  percent={Math.round(coverage * 100)}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
