import type { SignIn } from '@clerk/nextjs';
import { esES } from '@clerk/localizations';
import type { ComponentProps } from 'react';

type ClerkAppearance = NonNullable<ComponentProps<typeof SignIn>['appearance']>;

export const clerkAppearance: ClerkAppearance = {
  options: {
    socialButtonsVariant: 'blockButton',
    logoPlacement: 'inside',
    logoImageUrl: '/images/logo-1316x1316-no-bg.png',
    showOptionalFields: true,
  },
  variables: {
    colorPrimary: 'var(--color-primary)',
    colorForeground: 'var(--color-ink)',
    colorMutedForeground: 'var(--color-muted)',
    colorBackground: 'white',
    colorInput: 'var(--color-surface-subtle)',
    colorInputForeground: 'var(--color-ink)',
    colorBorder: 'var(--color-line-strong)',
    colorRing: 'var(--color-primary-soft-strong)',
    colorDanger: 'var(--color-danger)',
    colorSuccess: 'var(--color-success)',
    borderRadius: '2px',
  },
  elements: {
    cardBox:
      'w-full max-w-101 rounded-xs border border-line-strong shadow-[0_1px_2px_rgba(18,33,31,.05),0_18px_48px_rgba(18,33,31,.08)]',
    card: 'px-9 pt-8.5 pb-7.5 shadow-none max-[460px]:px-5.5',
    headerTitle: 'font-display text-3xl leading-tight font-normal text-ink',
    headerSubtitle: 'text-sm text-muted',
    socialButtonsBlockButton:
      'h-10.5 rounded-xs border border-line-strong shadow-none hover:border-primary hover:bg-surface-subtle',
    dividerLine: 'bg-line',
    dividerText: 'text-2xs font-bold tracking-[0.12em] text-faint uppercase',
    formFieldLabel: 'text-sm font-semibold text-ink',
    formFieldInput:
      'h-10.5 rounded-xs border border-line-strong bg-surface-subtle shadow-none focus:border-primary focus:bg-white focus:ring-3 focus:ring-primary-soft-strong',
    formButtonPrimary:
      'h-10.5 rounded-xs bg-primary text-xs font-bold tracking-[0.09em] uppercase shadow-none after:hidden hover:bg-primary-strong',
    otpCodeFieldInput: 'rounded-xs',
    footer: 'bg-surface-subtle',
    footerActionLink: 'font-semibold text-primary hover:text-primary-strong',
  },
};

// Overrides of Clerk's translations.
export const clerkLocalization: typeof esES = {
  ...esES,
  formFieldLabel__emailAddress: 'Dirección de correo electrónico',
  formFieldLabel__lastName: 'Apellidos',
  formFieldInputPlaceholder__emailAddress: 'Introduce tu correo electrónico',
  formFieldInputPlaceholder__firstName: 'Nombre',
  formFieldInputPlaceholder__lastName: 'Apellidos',
  formFieldInputPlaceholder__password: 'Introduce tu contraseña',
  formFieldInputPlaceholder__signUpPassword: 'Introduce tu contraseña',
  signIn: {
    ...esES.signIn,
    start: {
      ...esES.signIn?.start,
      title: 'Iniciar sesión en {{applicationName}}',
      subtitle: '¡Bienvenido de nuevo! Por favor inicia sesión para continuar',
      actionText: '¿No tienes una cuenta?',
      actionLink: 'Regístrate',
    },
  },
  signUp: {
    ...esES.signUp,
    start: {
      ...esES.signUp?.start,
      subtitle: '¡Bienvenido! Por favor completa los datos para comenzar.',
      subtitleCombined:
        '¡Bienvenido! Por favor completa los datos para comenzar.',
    },
  },
};
