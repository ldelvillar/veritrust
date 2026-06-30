import Link from 'next/link';
import type { ComponentProps, ReactNode, Ref } from 'react';

export type ButtonVariant = 'primary' | 'ghost' | 'light' | 'outline' | 'soft';
export type ButtonSize = 'md' | 'lg';

// Fuente única de verdad para los botones del producto: estilo «Plano compacto».
const base =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap cursor-pointer font-semibold no-underline transition-colors duration-150 [&_svg]:size-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-current disabled:cursor-not-allowed disabled:opacity-50';

const sizes: Record<ButtonSize, string> = {
  md: 'px-[17px] py-[9px] text-[14px] rounded-[10px]',
  lg: 'px-[22px] py-[12px] text-[15px] rounded-[11px]',
};

const variants: Record<ButtonVariant, string> = {
  primary: 'bg-primary text-white hover:bg-[#3722b8]',
  ghost: 'bg-[#efedfc] text-[#3722b8] hover:bg-[#e7e3fb]',
  light: 'bg-white text-[#3722b8] hover:bg-[#f3f1fc]',
  outline:
    'border-[1.5px] border-white/40 text-white hover:border-white hover:bg-white/12',
  soft: 'bg-white text-body border border-line-strong hover:border-primary hover:text-[#3722b8]',
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
