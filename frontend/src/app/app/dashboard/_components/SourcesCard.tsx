import type { DashboardPayload } from './types';

const SOURCE_META: Record<string, { label: string; color: string }> = {
  text: { label: 'Texto', color: '#6356e6' },
  url: { label: 'Enlace', color: '#2c97e8' },
  file: { label: 'Archivo', color: '#13b877' },
  pdf: { label: 'Archivo', color: '#13b877' },
};

export default function SourcesCard({
  items,
}: {
  items: DashboardPayload['source_breakdown'];
}) {
  const total = items.reduce((a, s) => a + s.total, 0) || 1;
  const wavg = Math.round(
    items.reduce((a, s) => a + s.average_confidence * s.total, 0) / total
  );

  return (
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
            Fuentes
          </h2>
          <p
            className="mt-1 text-[13px] leading-snug"
            style={{ color: '#7e7f99' }}
          >
            Reparto por tipo de entrada.
          </p>
        </div>
        <span
          className="shrink-0 rounded-full border border-[#e7e3fb] bg-[#f4f2fd] px-[11px] py-[6px] text-[11.5px] font-bold"
          style={{ color: '#5446dc' }}
        >
          {total} análisis
        </span>
      </div>

      {/* Segmented bar */}
      <div className="mb-5 flex h-[14px] gap-0.5 overflow-hidden rounded-full">
        {items.map(s => {
          const meta = SOURCE_META[s.source_type] ?? {
            label: s.source_type,
            color: '#9698b1',
          };
          return (
            <div
              key={s.source_type}
              style={{ flex: s.total, background: meta.color }}
            />
          );
        })}
      </div>

      <div className="flex flex-col">
        {items.map((s, idx) => {
          const meta = SOURCE_META[s.source_type] ?? {
            label: s.source_type,
            color: '#9698b1',
          };
          return (
            <div
              key={s.source_type}
              className="flex items-center gap-3.5 py-3"
              style={{ borderTop: idx === 0 ? 'none' : '1px solid #e8e6f4' }}
            >
              <span
                className="size-[11px] shrink-0 rounded-[4px]"
                style={{ background: meta.color }}
              />
              <span className="shrink-0 text-[14px] font-bold text-[#15162c]">
                {meta.label}
              </span>
              <div
                className="h-2 flex-1 overflow-hidden rounded-full"
                style={{ background: '#eeedf8' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(s.total / total) * 100}%`,
                    background: meta.color,
                  }}
                />
              </div>
              <span className="font-display w-7 shrink-0 text-right text-[14px] font-bold text-[#15162c]">
                {s.total}
              </span>
            </div>
          );
        })}
      </div>

      {items.length > 0 && (
        <div className="mt-4 flex items-center justify-between border-t border-[#e8e6f4] pt-4">
          <span
            className="text-[12.5px] font-semibold"
            style={{ color: '#7e7f99' }}
          >
            Confianza media del periodo
          </span>
          <span className="text-[13.5px] font-bold text-[#15162c]">
            {wavg}%
          </span>
        </div>
      )}
    </section>
  );
}
