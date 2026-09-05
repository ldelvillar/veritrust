import Link from 'next/link';
import type { ComponentProps, ReactNode, Ref } from 'react';

export type PublicButtonVariant = 'primary' | 'light' | 'outline' | 'soft';
export type PublicButtonSize = 'md' | 'lg';

const base =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xs uppercase tracking-[0.09em] cursor-pointer font-bold no-underline transition-colors duration-150 [&_svg]:size-3.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current disabled:cursor-not-allowed disabled:opacity-50';

const sizes: Record<PublicButtonSize, string> = {
  md: 'px-5 py-2 text-2xs',
  lg: 'px-[22px] py-[9px] text-xs',
};

const variants: Record<PublicButtonVariant, string> = {
  primary: 'bg-primary text-white hover:bg-primary-strong',
  light: 'bg-white text-primary-strong hover:bg-surface-subtle',
  outline:
    'border border-white/45 text-white hover:border-white hover:bg-white/12',
  soft: 'bg-white text-body border border-line-strong hover:border-primary hover:text-primary-strong',
};

const cx = (...classes: (string | undefined | false)[]) =>
  classes.filter(Boolean).join(' ');

interface CommonProps {
  variant?: PublicButtonVariant;
  size?: PublicButtonSize;
  className?: string;
  children: ReactNode;
}

type PublicButtonAsButton = CommonProps &
  Omit<ComponentProps<'button'>, keyof CommonProps> & {
    href?: undefined;
    ref?: Ref<HTMLButtonElement>;
  };

type PublicButtonAsLink = CommonProps &
  Omit<ComponentProps<typeof Link>, keyof CommonProps> & {
    href: ComponentProps<typeof Link>['href'];
    ref?: Ref<HTMLAnchorElement>;
  };

type PublicButtonProps = PublicButtonAsButton | PublicButtonAsLink;

export default function PublicButton({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: PublicButtonProps) {
  const classes = cx(base, sizes[size], variants[variant], className);

  if (props.href !== undefined) {
    return (
      <Link className={classes} {...props}>
        {children}
      </Link>
    );
  }

  const { type = 'button', ...buttonProps } = props;
  return (
    <button type={type} className={classes} {...buttonProps}>
      {children}
    </button>
  );
}
