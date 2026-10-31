import Link from 'next/link';
import type { ReactNode } from 'react';

import LockIcon from '@/assets/Lock';
import SparkleIcon from '@/assets/Sparkle';
import Button from '@/components/Button';
import { UPGRADE_HREF } from '@/lib/plan';

interface UpgradePromptProps {
  title?: string;
  children: ReactNode;
  variant?: 'card' | 'inline';
  className?: string;
}

// Invitation to go Pro where the Free Plan does not reach, always leading to the Plan card.
export default function UpgradePrompt({
  title,
  children,
  variant = 'card',
  className = '',
}: UpgradePromptProps) {
  if (variant === 'inline') {
    return (
      <p
        className={`flex flex-wrap items-center gap-x-2 gap-y-1 text-sm font-medium text-muted ${className}`}
      >
        <LockIcon className="size-4 shrink-0 text-faint" aria-hidden />
        <span>{children}</span>
        <Link
          href={UPGRADE_HREF}
          className="font-bold text-primary underline-offset-2 hover:underline"
        >
          Hazte Pro
        </Link>
      </p>
    );
  }

  return (
    <div
      className={`flex flex-col items-center rounded-2xl border border-primary/20 bg-primary-soft p-6 text-center ${className}`}
    >
      <span className="grid size-11 place-items-center rounded-xl bg-white text-primary">
        <SparkleIcon className="size-5" aria-hidden />
      </span>
      {title && <h2 className="mt-3.5 text-lg font-bold text-ink">{title}</h2>}
      <p className="mt-1.5 max-w-md text-sm leading-relaxed text-muted">
        {children}
      </p>
      <Button href={UPGRADE_HREF} className="mt-4">
        Hazte Pro
      </Button>
    </div>
  );
}

// Button for a feature the Plan lacks, same look with a padlock, leading to the Plan card.
export function ProLockedButton({
  title,
  children,
  className,
}: {
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Button
      variant="soft"
      href={UPGRADE_HREF}
      title={title}
      className={className}
    >
      <LockIcon className="size-4" aria-hidden />
      {children}
    </Button>
  );
}
