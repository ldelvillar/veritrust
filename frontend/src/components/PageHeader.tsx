import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  eyebrow?: string;
  subtitle?: string;
  actions?: ReactNode;
  actionsClassName?: string;
}

// Cabecera de página común al dashboard, historial e informe para un tipográfico uniforme.
export default function PageHeader({
  title,
  eyebrow,
  subtitle,
  actions,
  actionsClassName = '',
}: PageHeaderProps) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4">
      <div className="min-w-60 flex-1">
        {eyebrow && (
          <p className="mb-2 text-2xs font-bold tracking-[0.13em] text-accent uppercase">
            {eyebrow}
          </p>
        )}
        <h1 className="text-3xl leading-tight font-bold tracking-[-0.03em] text-ink">
          {title}
        </h1>
        {subtitle && (
          <p className="mt-1.5 max-w-xl text-sm leading-snug text-muted">
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div
          className={`flex flex-wrap items-center gap-2.5 ${actionsClassName}`}
        >
          {actions}
        </div>
      )}
    </header>
  );
}
