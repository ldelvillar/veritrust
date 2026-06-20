import type { ReactNode } from 'react';

type Variant = 'violet' | 'red';

interface HistoryStatePanelProps {
  variant: Variant;
  icon: ReactNode;
  eyebrow: string;
  title: string;
  lead: ReactNode;
  actions?: ReactNode;
  footer?: ReactNode;
}

const ICON_STYLES: Record<Variant, string> = {
  violet:
    'bg-[linear-gradient(155deg,#7166ef,#5446dc)] shadow-[0_14px_30px_rgba(99,86,230,.34)]',
  red: 'bg-[linear-gradient(155deg,#e2607a,#d23c5d)] shadow-[0_14px_30px_rgba(210,60,93,.30)]',
};

const EYEBROW_STYLES: Record<Variant, string> = {
  violet: 'text-accent',
  red: 'text-[#c23552]',
};

// Patrón de puntos decorativo, atenuado hacia los bordes con una máscara radial.
const DOTS_STYLES: Record<Variant, string> = {
  violet:
    '[background-image:radial-gradient(rgba(99,86,230,0.10)_1.1px,transparent_1.1px)]',
  red: '[background-image:radial-gradient(rgba(224,85,107,0.10)_1.1px,transparent_1.1px)]',
};

const DOTS_MASK =
  '[background-size:22px_22px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_38%,#000,transparent_72%)] [-webkit-mask-image:radial-gradient(ellipse_60%_60%_at_50%_38%,#000,transparent_72%)]';

// Panel centrado para los estados de error y de historial vacío del diseño.
export default function HistoryStatePanel({
  variant,
  icon,
  eyebrow,
  title,
  lead,
  actions,
  footer,
}: HistoryStatePanelProps) {
  return (
    <div className="relative flex flex-col items-center overflow-hidden rounded-3xl border border-line bg-white px-6 py-16 text-center shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] sm:px-10 sm:py-20">
      <span
        aria-hidden
        className={`pointer-events-none absolute inset-0 ${DOTS_STYLES[variant]} ${DOTS_MASK}`}
      />
      <div className="relative flex flex-col items-center">
        <div
          className={`grid size-21 place-items-center rounded-3xl text-white ${ICON_STYLES[variant]}`}
        >
          {icon}
        </div>
        <p
          className={`mt-6 text-[11px] font-extrabold tracking-[0.14em] uppercase ${EYEBROW_STYLES[variant]}`}
        >
          {eyebrow}
        </p>
        <h2 className="mt-3.5 max-w-lg text-[clamp(22px,2.6vw,27px)] leading-tight font-bold tracking-[-0.025em] text-balance text-ink">
          {title}
        </h2>
        <div className="mt-3.5 max-w-md text-[15.5px] leading-relaxed font-medium text-pretty text-muted">
          {lead}
        </div>
        {actions && (
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            {actions}
          </div>
        )}
        {footer}
      </div>
    </div>
  );
}
