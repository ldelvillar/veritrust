import Link from 'next/link';
import ArrowRightIcon from '@/assets/ArrowRight';
import { VERDICT_LABEL } from '@/components/analysis-result/format';
import type { DashboardAlertItem } from './types';

// Estas alertas ya vienen filtradas por el backend a veredicto 'fake': el
// texto es siempre el mismo, solo cambia el tono según la severidad.
function alertVerdict(item: DashboardAlertItem): {
  label: string;
  tone: 'bad' | 'warn';
} {
  const score = item.credibility ?? 0;
  const tone = item.label === 'falsa' || score < 40 ? 'bad' : 'warn';
  return { label: VERDICT_LABEL.fake, tone };
}

const ALERT_STYLES = {
  bad: {
    card: {
      background: 'var(--color-verdict-fake-soft)',
      borderColor: 'var(--color-verdict-fake-soft)',
    },
    score:
      'linear-gradient(150deg,var(--color-verdict-fake-g1),var(--color-verdict-fake-g2))',
    verdict: {
      color: 'var(--color-verdict-fake-ink)',
      background: 'var(--color-verdict-fake-soft)',
    },
  },
  warn: {
    card: {
      background: 'var(--color-verdict-uncertain-soft)',
      borderColor: 'var(--color-verdict-uncertain-soft)',
    },
    score:
      'linear-gradient(150deg,var(--color-verdict-uncertain-g1),var(--color-verdict-uncertain-g2))',
    verdict: {
      color: 'var(--color-verdict-uncertain-ink)',
      background: 'var(--color-verdict-uncertain-soft)',
    },
  },
};

function getAlertTitle(item: DashboardAlertItem): string {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
}

export default function AlertsCard({
  items,
  total,
}: {
  items: DashboardAlertItem[];
  total: number;
}) {
  return (
    <section className="flex flex-col rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg leading-tight font-bold tracking-[-0.015em] text-ink">
            Alertas recientes
          </h2>
          <p className="mt-1 text-sm leading-snug text-muted">
            Últimos análisis con baja credibilidad detectada.
          </p>
        </div>
        {total > 0 && (
          <span className="shrink-0 rounded-full border border-primary-soft-strong bg-surface px-2.75 py-1.5 text-2xs font-bold text-accent">
            {total} {total === 1 ? 'alerta' : 'alertas'}
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium text-muted">
          No hay alertas por ahora.
        </p>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {items.map(item => {
              const { label, tone } = alertVerdict(item);
              const st = ALERT_STYLES[tone];
              const score = item.credibility ?? 0;
              const date = new Date(item.created_at).toLocaleString('es-ES', {
                day: 'numeric',
                month: 'short',
                hour: '2-digit',
                minute: '2-digit',
              });
              return (
                <Link
                  key={item.id}
                  href={`/app/analisis/${item.id}`}
                  className="group flex items-start gap-3.5 rounded-xl border p-4.25 transition-all duration-150 hover:shadow-sm"
                  style={st.card}
                >
                  <div
                    className="flex size-12 shrink-0 flex-col items-center justify-center rounded-xl text-white"
                    style={{ background: st.score }}
                  >
                    <span className="text-lg leading-none font-bold">
                      {score}
                    </span>
                    <span className="mt-0.5 text-2xs font-semibold opacity-85">
                      /100
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-sm leading-[1.45] font-bold text-ink">
                      {getAlertTitle(item)}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2.5">
                      <span
                        className="rounded-md px-2.25 py-0.75 text-2xs font-bold tracking-[.05em] uppercase"
                        style={st.verdict}
                      >
                        {label}
                      </span>
                      <span className="text-xs font-semibold text-muted">
                        {date}
                      </span>
                    </div>
                  </div>

                  <div className="grid size-8.5 shrink-0 place-items-center self-center rounded-lg border border-line bg-white text-faint transition-transform duration-150 group-hover:translate-x-0.5">
                    <ArrowRightIcon className="size-4" strokeWidth={2.1} />
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="mt-4 flex justify-center">
            <Link
              href="/app/historial?verdict=fake"
              className="inline-flex items-center gap-2 text-sm font-semibold text-accent"
            >
              Ver todas las alertas{' '}
              <ArrowRightIcon className="size-4" strokeWidth={2.1} />
            </Link>
          </div>
        </>
      )}
    </section>
  );
}
