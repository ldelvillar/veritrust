import BookIcon from '@/assets/Book';
import ShieldIcon from '@/assets/Shield';
import { countBackedClaims } from '@/lib/evidence';
import CredibilityGauge from './CredibilityGauge';
import { confidenceLabel, getVerdictInfo } from './format';
import type { ReportView } from './types';

export default function ResultBand({ result }: { result: ReportView }) {
  const score = result.credibility ?? null;
  const verdict = getVerdictInfo(result.verdict);
  const confidence = confidenceLabel(result.confidence);
  const claimCount = result.claims?.length ?? 0;
  const sources = result.sources ?? [];
  const coverage = countBackedClaims(result.claims ?? [], sources);

  return (
    <div
      className="relative grid overflow-hidden rounded-3xl text-white shadow-[0_18px_44px_rgba(0,0,0,.16)] lg:grid-cols-[272px_1fr] print:break-inside-avoid"
      style={{ background: verdict.band }}
    >
      <div className="flex flex-col items-center justify-center gap-4 border-b border-white/20 bg-white/5 px-6 py-8 text-center lg:border-r lg:border-b-0">
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
              <ShieldIcon className="size-3.5 opacity-85" />
              {confidence}
            </span>
          )}
          {claimCount > 0 && (
            <span className="inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/15 px-3 py-1.5 text-xs font-bold">
              <BookIcon className="size-3.5 opacity-85" />
              {coverage.backed}/{claimCount}{' '}
              {claimCount === 1 ? 'afirmación' : 'afirmaciones'} con evidencia
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
