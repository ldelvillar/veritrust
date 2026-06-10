import type { DashboardPayload } from './types';

function domainCredibility(avgConf: number): {
  label: string;
  cls: 'ok' | 'warn' | 'bad';
} {
  if (avgConf >= 75) return { label: 'Alta', cls: 'ok' };
  if (avgConf >= 50) return { label: 'Media', cls: 'warn' };
  return { label: 'Baja', cls: 'bad' };
}

const CRED_STYLES = {
  ok: { color: '#0e8e5b', background: '#def4ea' },
  warn: { color: '#b07a16', background: '#fbefda' },
  bad: { color: '#c23552', background: '#fbe4e8' },
};

export default function DomainsCard({
  items,
}: {
  items: DashboardPayload['domain_breakdown'];
}) {
  const maxCount = Math.max(1, ...items.map(d => d.total));

  return (
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5">
        <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
          Dominios frecuentes
        </h2>
        <p
          className="mt-1 text-[13px] leading-snug"
          style={{ color: '#7e7f99' }}
        >
          Top de enlaces analizados por frecuencia.
        </p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium" style={{ color: '#7e7f99' }}>
          No hay dominios registrados todavía.
        </p>
      ) : (
        <div className="flex flex-col">
          {items.map((item, idx) => {
            const cred = domainCredibility(item.average_confidence);
            const init = item.domain[0]?.toUpperCase() ?? '?';
            return (
              <div
                key={item.domain}
                className="flex items-center gap-3.5 py-3.5"
                style={{
                  borderTop: idx === 0 ? 'none' : '1px solid #e8e6f4',
                  paddingTop: idx === 0 ? 2 : undefined,
                }}
              >
                <div
                  className="font-display grid size-9 shrink-0 place-items-center rounded-[10px] border border-[#e8e6f4] text-[14px] font-bold uppercase"
                  style={{ background: '#faf9fe', color: '#7e7f99' }}
                >
                  {init}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-[14px] font-bold text-[#15162c]">
                      {item.domain}
                    </span>
                    <span
                      className="shrink-0 text-[12px] font-semibold"
                      style={{ color: '#a3a4ba' }}
                    >
                      · {item.total} análisis
                    </span>
                  </div>
                  <div
                    className="mt-2 h-1.5 overflow-hidden rounded-full"
                    style={{ background: '#eeedf8' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(item.total / maxCount) * 100}%`,
                        background: 'linear-gradient(90deg,#8579f0,#5e50e0)',
                      }}
                    />
                  </div>
                </div>
                <span
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-[11px] py-[5px] text-[12px] font-bold"
                  style={CRED_STYLES[cred.cls]}
                >
                  <span
                    className="size-2 rounded-full"
                    style={{ background: 'currentColor' }}
                  />
                  {cred.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
