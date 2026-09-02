import Link from 'next/link';
import type { ComponentProps, ReactNode, Ref } from 'react';

export type ButtonVariant =
  | 'primary'
  | 'ghost'
  | 'light'
  | 'outline'
  | 'soft'
  | 'danger';
export type ButtonSize = 'md' | 'lg';

// Fuente única de verdad para los botones del producto: estilo «Plano compacto».
const base =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap cursor-pointer font-semibold no-underline transition-colors duration-150 [&_svg]:size-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current disabled:cursor-not-allowed disabled:opacity-50';

const sizes: Record<ButtonSize, string> = {
  md: 'px-[17px] py-[9px] text-[14px] rounded-[10px]',
  lg: 'px-[22px] py-[12px] text-[15px] rounded-[11px]',
};

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-white hover:bg-primary-strong',
  ghost: 'bg-primary-soft text-primary-strong hover:bg-primary-soft-strong',
  light: 'bg-white text-primary-strong hover:bg-surface-subtle',
  outline:
    'border-[1.5px] border-white/40 text-white hover:border-white hover:bg-white/12',
  soft: 'bg-white text-body border border-line-strong hover:border-primary hover:text-primary-strong',
  // Variante autónoma: incluye su propia geometría, tipografía y foco, sin base ni size.
  danger:
    'inline-flex items-center gap-2 rounded-xl border border-danger/30 bg-white px-4 py-2 text-sm font-bold text-danger-ink transition hover:bg-danger-soft focus:ring-2 focus:ring-danger-soft focus:outline-none disabled:cursor-not-allowed disabled:opacity-50',
};

const cx = (...classes: (string | undefined | false)[]) =>
  classes.filter(Boolean).join(' ');

interface CommonProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
  children: ReactNode;
}

type ButtonAsButton = CommonProps &
  Omit<ComponentProps<'button'>, keyof CommonProps> & {
    href?: undefined;
    ref?: Ref<HTMLButtonElement>;
  };

type ButtonAsLink = CommonProps &
  Omit<ComponentProps<typeof Link>, keyof CommonProps> & {
    href: ComponentProps<typeof Link>['href'];
    ref?: Ref<HTMLAnchorElement>;
  };

type ButtonProps = ButtonAsButton | ButtonAsLink;

export default function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  const classes =
    variant === 'danger'
      ? cx(variants.danger, className)
      : cx(base, sizes[size], variants[variant], className);

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
