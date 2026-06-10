import Link from 'next/link';
import ArrowRightIcon from '@/assets/ArrowRight';
import type { DashboardAlertItem } from './types';

function alertVerdict(item: DashboardAlertItem): {
  label: string;
  tone: 'bad' | 'warn';
} {
  const score = item.credibility ?? 0;
  if (item.label === 'falsa' || score < 40)
    return { label: 'Engañoso', tone: 'bad' };
  return { label: 'Dudoso', tone: 'warn' };
}

const ALERT_STYLES = {
  bad: {
    card: { background: '#fdf3f5', borderColor: '#f3d2da' },
    score: 'linear-gradient(150deg,#e2607a,#d23c5d)',
    verdict: { color: '#c23552', background: '#fbe4e8' },
  },
  warn: {
    card: { background: '#fdf8ef', borderColor: '#f1e2c2' },
    score: 'linear-gradient(150deg,#e8b057,#d98e29)',
    verdict: { color: '#b07a16', background: '#fbefda' },
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
    <section className="flex flex-col rounded-[20px] border border-[#e8e6f4] bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-[#15162c]">
            Alertas recientes
          </h2>
          <p
            className="mt-1 text-[13px] leading-snug"
            style={{ color: '#7e7f99' }}
          >
            Últimos análisis con baja credibilidad detectada.
          </p>
        </div>
        {total > 0 && (
          <span
            className="shrink-0 rounded-full border border-[#e7e3fb] bg-[#f4f2fd] px-[11px] py-[6px] text-[11.5px] font-bold"
            style={{ color: '#5446dc' }}
          >
            {total} {total === 1 ? 'alerta' : 'alertas'}
          </span>
        )}
      </div>

      {items.length === 0 ? (
        <p className="text-sm font-medium" style={{ color: '#7e7f99' }}>
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
                  className="group flex items-start gap-3.5 rounded-[14px] border p-[17px] transition-all duration-150 hover:shadow-sm"
                  style={st.card}
                >
                  <div
                    className="flex size-12 shrink-0 flex-col items-center justify-center rounded-[13px] text-white"
                    style={{ background: st.score }}
                  >
                    <span className="font-display text-[17px] leading-none font-bold">
                      {score}
                    </span>
                    <span className="mt-0.5 text-[9px] font-semibold opacity-85">
                      /100
                    </span>
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="line-clamp-2 text-[14px] leading-[1.45] font-bold text-[#15162c]">
                      {getAlertTitle(item)}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2.5">
                      <span
                        className="rounded-[6px] px-[9px] py-[3px] text-[10.5px] font-bold tracking-[.05em] uppercase"
                        style={st.verdict}
                      >
                        {label}
                      </span>
                      <span
                        className="text-[12px] font-semibold"
                        style={{ color: '#7e7f99' }}
                      >
                        {date}
                      </span>
                    </div>
                  </div>

                  <div
                    className="grid size-[34px] shrink-0 place-items-center self-center rounded-[10px] border border-[#e8e6f4] bg-white transition-transform duration-150 group-hover:translate-x-0.5"
                    style={{ color: '#a3a4ba' }}
                  >
                    <ArrowRightIcon className="size-4" strokeWidth={2.1} />
                  </div>
                </Link>
              );
            })}
          </div>

          <div className="mt-4 flex justify-center">
            <Link
              href="/app/historial"
              className="font-display inline-flex items-center gap-2 text-[13.5px] font-semibold"
              style={{ color: '#5446dc' }}
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
