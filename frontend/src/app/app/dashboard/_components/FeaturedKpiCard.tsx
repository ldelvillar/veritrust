import ChevronDownIcon from '@/assets/ChevronDown';
import ChevronUpIcon from '@/assets/ChevronUp';
import InfoHint from './InfoHint';
import Sparkline from './Sparkline';

interface FeaturedKpiCardProps {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  tint: string;
  color: string;
  delta?: { dir: 'up' | 'down'; value: string };
  spark?: number[];
  hint: string;
}

export default function FeaturedKpiCard({
  label,
  value,
  sub,
  icon,
  tint,
  color,
  delta,
  spark,
  hint,
}: FeaturedKpiCardProps) {
  return (
    <article className="relative flex items-center gap-5 rounded-[20px] border border-line bg-white p-5.5 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(60,50,140,.16)]">
      <div
        className="grid size-11.5 shrink-0 place-items-center rounded-[13px]"
        style={{ background: tint, color }}
      >
        {icon}
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1.5 flex items-center gap-2.5">
          <span className="text-[11px] leading-tight font-bold tracking-[.09em] text-faint uppercase">
            {label}
          </span>
          {delta && (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2.25 py-1 text-[12px] font-bold"
              style={
                delta.dir === 'up'
                  ? { color: '#0e8e5b', background: '#def4ea' }
                  : { color: '#c23552', background: '#fbe4e8' }
              }
            >
              {delta.dir === 'up' ? (
                <ChevronUpIcon className="size-3" />
              ) : (
                <ChevronDownIcon className="size-3" />
              )}
              {delta.value}
              <span style={{ fontWeight: 600, opacity: 0.8 }}>sem.</span>
            </span>
          )}
        </div>
        <p className="text-[40px] leading-none font-bold tracking-[-0.03em] text-ink">
          {value}
        </p>
        <p className="mt-1.75 text-[11.5px] font-semibold text-faint">{sub}</p>
      </div>

      {spark && <Sparkline data={spark} color={color} />}

      <div className="absolute top-4 right-4.5">
        <InfoHint label={label} text={hint} />
      </div>
    </article>
  );
}
