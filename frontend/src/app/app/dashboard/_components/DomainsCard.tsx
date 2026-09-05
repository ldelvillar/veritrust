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
  ok: {
    color: 'var(--color-verdict-real-ink)',
    background: 'var(--color-verdict-real-soft)',
  },
  warn: {
    color: 'var(--color-verdict-uncertain-ink)',
    background: 'var(--color-verdict-uncertain-soft)',
  },
  bad: {
    color: 'var(--color-verdict-fake-ink)',
    background: 'var(--color-verdict-fake-soft)',
  },
};

export default function DomainsCard({
  items,
}: {
  items: DashboardPayload['domain_breakdown'];
}) {
  const maxCount = Math.max(1, ...items.map(d => d.total));

  return (
    <section className="flex flex-col rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]">
      <div className="mb-5">
        <h2 className="text-lg leading-tight font-bold tracking-[-0.015em] text-ink">
          Dominios frecuentes
        </h2>
        <p className="mt-1 text-sm leading-snug text-muted">
          Top de enlaces analizados por frecuencia.
        </p>
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium text-muted">
          No hay dominios registrados todavía.
        </p>
      ) : (
        <div className="flex flex-col">
          {items.map(item => {
            const cred = domainCredibility(item.average_confidence);
            const init = item.domain[0]?.toUpperCase() ?? '?';
            return (
              <div
                key={item.domain}
                className="flex items-center gap-3.5 border-t border-line py-3.5 first:border-t-0 first:pt-0.5"
              >
                <div className="grid size-9 shrink-0 place-items-center rounded-lg border border-line bg-surface-subtle text-sm font-bold text-muted uppercase">
                  {init}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-sm font-bold text-ink">
                      {item.domain}
                    </span>
                    <span className="shrink-0 text-xs font-semibold text-faint">
                      · {item.total} análisis
                    </span>
                  </div>
                  <div
                    className="mt-2 h-1.5 overflow-hidden rounded-full"
                    style={{ background: 'var(--color-surface)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(item.total / maxCount) * 100}%`,
                        background: 'var(--color-primary)',
                      }}
                    />
                  </div>
                </div>
                <span
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.75 py-1.25 text-xs font-bold"
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
