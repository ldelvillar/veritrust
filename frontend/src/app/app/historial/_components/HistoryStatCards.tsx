import type { HistoryPayload, VerdictFilter } from '@/lib/historyQuery';

type VerdictCounts = HistoryPayload['verdict_counts'];

const STAT_CARDS = [
  {
    toneKey: 'all',
    label: 'Análisis totales',
    verdictValue: 'all' as VerdictFilter,
  },
  { toneKey: 'ok', label: 'Verdaderos', verdictValue: 'real' as VerdictFilter },
  {
    toneKey: 'warn',
    label: 'Dudosos',
    verdictValue: 'uncertain' as VerdictFilter,
  },
  {
    toneKey: 'partial',
    label: 'Parcialmente falsos',
    verdictValue: 'mixed' as VerdictFilter,
  },
  {
    toneKey: 'bad',
    label: 'Falsos',
    verdictValue: 'fake' as VerdictFilter,
  },
];

const STAT_TONE_STYLES = {
  all: {
    numClass: 'text-primary',
    barStyle: 'var(--color-primary)',
    ringColor: 'var(--color-primary)',
  },
  ok: {
    numClass: 'text-verdict-real-ink',
    barStyle: 'var(--color-verdict-real)',
    ringColor: 'var(--color-verdict-real)',
  },
  warn: {
    numClass: 'text-verdict-uncertain-ink',
    barStyle: 'var(--color-verdict-uncertain)',
    ringColor: 'var(--color-verdict-uncertain)',
  },
  partial: {
    numClass: 'text-verdict-mixed-ink',
    barStyle: 'var(--color-verdict-mixed)',
    ringColor: 'var(--color-verdict-mixed)',
  },
  bad: {
    numClass: 'text-verdict-fake-ink',
    barStyle: 'var(--color-verdict-fake)',
    ringColor: 'var(--color-verdict-fake)',
  },
} as const;

// Cada tarjeta mapea a su conteo global por veredicto en la respuesta del historial.
const FACET_KEY: Record<VerdictFilter, keyof VerdictCounts> = {
  all: 'total',
  real: 'real',
  uncertain: 'uncertain',
  mixed: 'mixed',
  fake: 'fake',
};

interface HistoryStatCardsProps {
  verdictFilter: VerdictFilter;
  verdictCounts: VerdictCounts | null;
  onSelect: (verdict: VerdictFilter) => void;
}

// Tarjetas de conteo por veredicto; cada una filtra la tabla al pulsarla.
export default function HistoryStatCards({
  verdictFilter,
  verdictCounts,
  onSelect,
}: HistoryStatCardsProps) {
  return (
    <div className="mb-5.5 grid grid-cols-2 gap-3.5 lg:grid-cols-5">
      {STAT_CARDS.map(card => {
        const isActive = verdictFilter === card.verdictValue;
        const styles =
          STAT_TONE_STYLES[card.toneKey as keyof typeof STAT_TONE_STYLES];
        const count = verdictCounts
          ? verdictCounts[FACET_KEY[card.verdictValue]]
          : 0;

        return (
          <button
            key={card.toneKey}
            type="button"
            onClick={() => onSelect(card.verdictValue)}
            aria-pressed={isActive}
            className={`relative overflow-hidden rounded-2xl border bg-white p-[18px_20px_20px] text-left shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
              isActive ? 'border-transparent' : 'border-line'
            } ${card.verdictValue === 'all' ? 'col-span-2 lg:col-span-1' : ''}`}
            style={
              isActive
                ? {
                    boxShadow: `0 0 0 2px ${styles.ringColor}, 0 1px 2px rgba(18,33,31,.05), 0 10px 30px rgba(18,33,31,.06)`,
                  }
                : undefined
            }
          >
            <div
              className={`text-[clamp(26px,3vw,32px)] leading-none font-bold tracking-tight ${styles.numClass}`}
            >
              {count}
            </div>
            <div className="mt-2 text-xs font-bold text-muted">
              {card.label}
            </div>
            <span
              className={`absolute inset-x-0 bottom-0 transition-all ${isActive ? 'h-1' : 'h-0.75'}`}
              style={{ background: styles.barStyle }}
              aria-hidden
            />
          </button>
        );
      })}
    </div>
  );
}
