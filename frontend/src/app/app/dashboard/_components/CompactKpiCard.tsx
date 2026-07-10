import InfoHint from './InfoHint';

interface CompactKpiCardProps {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  tint: string;
  color: string;
  hint: string;
}

export default function CompactKpiCard({
  label,
  value,
  sub,
  icon,
  tint,
  color,
  hint,
}: CompactKpiCardProps) {
  return (
    <article className="flex flex-col gap-2.75 rounded-[20px] border border-line bg-white p-5 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_12px_40px_rgba(60,50,140,.16)]">
      <div className="flex items-center gap-2.75">
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
      <p className="text-[30px] leading-none font-bold tracking-[-0.03em] text-ink">
        {value}
      </p>
      <p className="text-[11.5px] font-semibold text-faint">{sub}</p>
    </article>
  );
}
