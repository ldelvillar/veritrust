import BookIcon from '@/assets/Book';
import ClockIcon from '@/assets/Clock';
import ListIcon from '@/assets/List';
import ShieldIcon from '@/assets/Shield';
import WarningIcon from '@/assets/Warning';
import { countBackedClaims } from '@/lib/evidence';
import CredibilityGauge from './CredibilityGauge';
import { confidenceLabel, getVerdictInfo } from './format';
import type { ReportView } from './types';

const SOURCE_TAGS: Record<string, string> = {
  text: 'Texto',
  url: 'Enlace',
  file: 'Archivo',
};

export default function ResultBand({ result }: { result: ReportView }) {
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
