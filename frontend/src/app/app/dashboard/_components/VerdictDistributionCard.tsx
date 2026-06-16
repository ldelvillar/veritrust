import type { DashboardPayload } from './types';

// Etiquetas y colores alineados con las tarjetas de veredicto del historial.
const VERDICT_META = [
  { key: 'real', label: 'Fiables', color: '#13b877' },
  { key: 'uncertain', label: 'Dudosos', color: '#e0a13b' },
  { key: 'fake', label: 'No fiables', color: '#e0556b' },
] as const;

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
        {VERDICT_META.map(v => {
          const count = distribution[v.key];
          if (count === 0) return null;
          return (
            <div key={v.key} style={{ flex: count, background: v.color }} />
          );
        })}
      </div>

      {/* Legend */}
      <div className="grid grid-cols-3 gap-3">
        {VERDICT_META.map(v => {
          const count = distribution[v.key];
          const pct = Math.round((count / safeTotal) * 100);
          return (
            <div
              key={v.key}
              className="rounded-xl border border-line bg-surface-subtle/60 p-3.5"
            >
              <div className="flex items-center gap-2">
                <span
                  className="size-2.75 shrink-0 rounded-sm"
                  style={{ background: v.color }}
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
