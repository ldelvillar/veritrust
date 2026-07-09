import { VERDICT_META } from '@/components/analysis-result/format';
import type { Verdict } from '@/components/analysis-result/types';
import type { DashboardPayload } from './types';

// Etiquetas en plural de cada categoría; el color procede del token de veredicto compartido.
const VERDICT_SEGMENTS: { key: Verdict; label: string }[] = [
  { key: 'real', label: 'Verdaderos' },
  { key: 'uncertain', label: 'Dudosos' },
  { key: 'fake', label: 'Falsos' },
];

export default function VerdictDistributionCard({
  distribution,
}: {
  distribution: DashboardPayload['verdict_distribution'];
}) {
  const total = distribution.real + distribution.uncertain + distribution.fake;
  const safeTotal = total || 1;

  return (
    <section className="flex flex-col rounded-[20px] border border-line bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-ink">
            Distribución de veredictos
          </h2>
          <p className="mt-1 text-[13px] leading-snug text-muted">
            Reparto de tus análisis completados por veracidad.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[#e7e3fb] bg-surface px-2.75 py-1.5 text-[11.5px] font-bold text-accent">
          {total} análisis
        </span>
      </div>

      {/* Segmented bar */}
      <div
        className="mb-5 flex h-3.5 gap-0.5 overflow-hidden rounded-full"
        style={{ background: '#eeedf8' }}
      >
        {VERDICT_SEGMENTS.map(v => {
          const count = distribution[v.key];
          if (count === 0) return null;
          return (
            <div
              key={v.key}
              className={VERDICT_META[v.key].solid}
              style={{ flex: count }}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-3 gap-3">
        {VERDICT_SEGMENTS.map(v => {
          const count = distribution[v.key];
          const pct = Math.round((count / safeTotal) * 100);
          return (
            <div
              key={v.key}
              className="rounded-xl border border-line bg-surface-subtle/60 p-3.5"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`size-2.75 shrink-0 rounded-sm ${VERDICT_META[v.key].solid}`}
                />
                <span className="text-[13px] font-bold text-muted">
                  {v.label}
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-1.5">
                <span className="text-[24px] leading-none font-bold tracking-tight text-ink">
                  {count}
                </span>
                <span className="text-[12.5px] font-semibold text-faint">
                  {pct}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
