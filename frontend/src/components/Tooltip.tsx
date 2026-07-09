'use client';

import { type ReactNode, useRef, useState } from 'react';

type TooltipProps = {
  ariaLabel: string;
  trigger: ReactNode;
  buttonClassName: string;
  panelClassName: string;
  className?: string;
  children: ReactNode;
};

// Tooltip accesible (WCAG 1.4.13): se descarta con Escape, es persistente y se puede pasar el ratón por encima.
export default function Tooltip({
  ariaLabel,
  trigger,
  buttonClassName,
  panelClassName,
  className = 'relative inline-flex shrink-0',
  children,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined
  );

  const show = () => {
    clearTimeout(closeTimer.current);
    setOpen(true);
  };

  // Cierre diferido para no perder el tooltip al cruzar el hueco hacia el panel.
  const hide = () => {
    closeTimer.current = setTimeout(() => setOpen(false), 120);
  };

  const dismiss = () => {
    clearTimeout(closeTimer.current);
    setOpen(false);
  };

  return (
    <span
      className={className}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onKeyDown={e => {
        if (e.key === 'Escape') dismiss();
      }}
    >
      <button type="button" aria-label={ariaLabel} className={buttonClassName}>
        {trigger}
      </button>
      <span
        role="tooltip"
        className={`${panelClassName} ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`}
      >
        {children}
      </span>
    </span>
  );
}
