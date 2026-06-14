import ChevronDownIcon from '@/assets/ChevronDown';
import ChevronUpIcon from '@/assets/ChevronUp';
import InfoHint from './InfoHint';
import Sparkline from './Sparkline';

interface KpiCardProps {
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

export default function KpiCard({
  label,
  value,
  sub,
  icon,
  tint,
  color,
  delta,
  spark,
  hint,
}: KpiCardProps) {
  return (
    <article className="relative flex flex-col gap-3 overflow-hidden rounded-[20px] border border-line bg-white p-5 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(60,50,140,.16)]">
      <div className="flex items-center gap-3">
        <div
          className="grid size-9.5 shrink-0 place-items-center rounded-[11px]"
          style={{ background: tint, color }}
        >
          {icon}
        </div>
        <p className="text-[11px] leading-tight font-bold tracking-[.09em] text-faint uppercase">
          {label}
        </p>
        <div className="ml-auto">
          <InfoHint label={label} text={hint} />
        </div>
      </div>

      <p className="font-display text-[34px] leading-none font-bold tracking-[-0.03em] text-ink">
        {value}
      </p>

      <div className="mt-0.5 flex items-end justify-between gap-2">
        <div className="flex flex-col gap-1.5">
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
          <span className="text-[11.5px] font-semibold text-faint">{sub}</span>
        </div>
        {spark && <Sparkline data={spark} color={color} />}
      </div>
    </article>
  );
}
