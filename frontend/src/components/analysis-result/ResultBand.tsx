import BookIcon from '@/assets/Book';
import QuestionIcon from '@/assets/Question';
import ShieldIcon from '@/assets/Shield';
import Tooltip from '@/components/Tooltip';
import CredibilityGauge from './CredibilityGauge';
import { confidenceLabel, formatCoverage, getVerdictInfo } from './format';
import type { ReportView } from './types';

export default function ResultBand({ result }: { result: ReportView }) {
  const score = result.credibility ?? null;
  const verdict = getVerdictInfo(result.verdict);
  const confidence = confidenceLabel(result.confidence);
  const coverage = result.evidence_coverage ?? null;

  return (
    <div
      className="relative grid overflow-hidden rounded-3xl text-white shadow-[0_18px_44px_rgba(0,0,0,.16)] lg:grid-cols-[272px_1fr] print:break-inside-avoid"
      style={{ background: verdict.band }}
    >
      <div className="relative flex flex-col items-center justify-center gap-4 border-b border-white/20 bg-white/5 px-6 py-8 text-center lg:border-r lg:border-b-0">
        <h2 className="absolute top-3 left-5 z-10 flex h-7 items-center text-[13px] font-bold tracking-[.06em] text-white/92 uppercase">
          Veracidad
        </h2>
        <Tooltip
          className="absolute top-3 right-3 inline-flex print:hidden"
          ariaLabel="Qué es la puntuación de credibilidad"
          trigger={<QuestionIcon className="size-4.25" aria-hidden="true" />}
          buttonClassName="grid size-7 place-items-center rounded-full bg-white/15 text-white transition hover:bg-white/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/40"
          panelClassName="absolute top-full right-0 z-10 mt-2.25 w-65 rounded-xl bg-[#1c2434] px-3.5 py-3 text-left text-[12.5px] leading-normal font-medium text-[#e8edf6] shadow-[0_14px_34px_rgba(0,0,0,.32)] transition-opacity before:absolute before:right-3.25 before:bottom-full before:border-[7px] before:border-transparent before:border-b-[#1c2434] before:content-['']"
        >
          Puntuación de credibilidad (0-100): cuanto más alta, más probable es
          que el contenido sea veraz.
        </Tooltip>
        <CredibilityGauge score={score} />
      </div>

      <div className="flex flex-col justify-center px-7 py-8">
        <h2 className="mt-3.5 text-3xl leading-tight font-bold tracking-tight sm:text-[34px]">
          {verdict.text}
        </h2>
        <p className="mt-3 max-w-xl text-[15.5px] leading-relaxed font-medium text-white/90">
          {verdict.description}
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {confidence && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <ShieldIcon className="size-3.5 opacity-85" aria-hidden="true" />
              {confidence} en el veredicto
            </span>
          )}
          {coverage != null && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <BookIcon className="size-3.5 opacity-85" aria-hidden="true" />
              {formatCoverage(coverage)} cobertura de evidencia
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
