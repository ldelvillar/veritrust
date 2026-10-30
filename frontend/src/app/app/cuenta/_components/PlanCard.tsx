'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import CheckIcon from '@/assets/Check';
import SparkleIcon from '@/assets/Sparkle';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import { PLAN_LABEL, PRO_FEATURES, PRO_PRICE } from '@/config/plans';
import { useBillingRedirect } from '@/hooks/useBillingRedirect';
import { usePlan } from '@/hooks/usePlan';
import {
  formatCount,
  formatPlanDate,
  formatPlanFullDate,
  usedThisMonth,
  type BillingInterval,
  type PlanResponse,
} from '@/lib/plan';

// El webhook de Stripe puede llegar después de la vuelta del Checkout: se sondea un rato.
const ACTIVATION_POLL_MS = 2000;
const ACTIVATION_TIMEOUT_MS = 30_000;

const INTERVALS: { value: BillingInterval; label: string; price: string }[] = [
  { value: 'month', label: 'Mensual', price: `${PRO_PRICE.month} / mes` },
  { value: 'year', label: 'Anual', price: `${PRO_PRICE.year} / año` },
];

const INTERVAL_LABEL: Record<BillingInterval, string> = {
  month: 'Facturación mensual',
  year: 'Facturación anual',
};

const NOTICE_TONE = {
  neutral: 'bg-surface-subtle text-muted',
  info: 'bg-primary-soft text-primary-strong',
  success: 'bg-success-soft text-success-ink',
  warning: 'bg-warning-soft text-warning-ink',
  danger: 'bg-danger-soft text-danger-ink',
} as const;

const NOTICE_ICON = 'mt-px size-4 shrink-0';

function Notice({
  tone,
  icon,
  role = 'status',
  className = 'mt-4',
  children,
}: {
  tone: keyof typeof NOTICE_TONE;
  icon?: ReactNode;
  role?: 'status' | 'alert';
  className?: string;
  children: ReactNode;
}) {
  return (
    <p
      role={role}
      className={`flex items-start gap-2 rounded-xl px-3.5 py-3 text-sm font-semibold ${NOTICE_TONE[tone]} ${className}`}
    >
      {icon}
      {children}
    </p>
  );
}

function CheckoutNotice({
  checkout,
  isPro,
  timedOut,
}: {
  checkout: string | null;
  isPro: boolean;
  timedOut: boolean;
}) {
  if (checkout === 'cancelled') {
    return (
      <Notice tone="neutral">
        Has salido del pago sin suscribirte. No se ha hecho ningún cargo.
      </Notice>
    );
  }
  if (checkout !== 'success') return null;
  if (isPro) {
    return (
      <Notice
        tone="success"
        icon={<CheckIcon className={NOTICE_ICON} aria-hidden />}
      >
        ¡Ya tienes el plan Pro! Gracias por suscribirte.
      </Notice>
    );
  }
  if (timedOut) {
    return (
      <Notice
        tone="warning"
        icon={<WarningIcon className={NOTICE_ICON} aria-hidden />}
      >
        Tu plan Pro aún no se ha activado. Puede tardar unos minutos: recarga la
        página más tarde y, si no cambia, escríbenos.
      </Notice>
    );
  }
  return (
    <Notice
      tone="info"
      icon={<Spinner className={`${NOTICE_ICON} animate-spin`} aria-hidden />}
    >
      Activando tu plan Pro…
    </Notice>
  );
}

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-line bg-surface-subtle px-4 py-3.5">
      <dt className="text-2xs font-extrabold tracking-[0.08em] text-faint uppercase">
        {label}
      </dt>
      <dd className="mt-0.5 text-base font-bold text-body">{children}</dd>
    </div>
  );
}

function FreePlan({
  isRedirecting,
  onCheckout,
}: {
  isRedirecting: boolean;
  onCheckout: (interval: BillingInterval) => void;
}) {
  const [interval, setBillingInterval] = useState<BillingInterval>('month');

  return (
    <>
      <div className="mt-6 border-t border-line pt-6">
        <p className="text-sm font-bold text-ink">Con Pro tienes:</p>
        <ul className="mt-3 grid gap-2.5 sm:grid-cols-2">
          {PRO_FEATURES.map(item => (
            <li
              key={item}
              className="flex items-start gap-2 text-sm font-medium text-body"
            >
              <CheckIcon className="mt-0.5 size-4 shrink-0 text-primary" />
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div
        role="group"
        aria-label="Periodo de facturación"
        className="mt-6 grid grid-cols-2 gap-2 rounded-xl border border-line bg-surface-subtle p-1"
      >
        {INTERVALS.map(option => {
          const active = interval === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => setBillingInterval(option.value)}
              className={`rounded-lg px-3 py-2 text-sm font-bold transition ${
                active
                  ? 'bg-white text-ink shadow-sm'
                  : 'text-muted hover:text-ink'
              }`}
            >
              {option.label}
              <span className="block text-xs font-semibold text-muted">
                {option.price}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <p className="min-w-50 flex-1 text-xs font-medium text-muted">
          IVA incluido. Cancela cuando quieras: mantienes Pro hasta el final del
          periodo pagado.
        </p>
        <Button
          onClick={() => onCheckout(interval)}
          disabled={isRedirecting}
          aria-busy={isRedirecting}
        >
          {isRedirecting ? (
            <Spinner className="size-4 animate-spin" aria-hidden />
          ) : (
            <SparkleIcon className="size-4" aria-hidden />
          )}
          Hazte Pro
        </Button>
      </div>
    </>
  );
}

function ProPlan({
  plan,
  isRedirecting,
  onManage,
}: {
  plan: PlanResponse;
  isRedirecting: boolean;
  onManage: () => void;
}) {
  return (
    <>
      {plan.status === 'past_due' && (
        <Notice
          tone="warning"
          role="alert"
          className="mt-5"
          icon={<WarningIcon className={NOTICE_ICON} aria-hidden />}
        >
          No hemos podido cobrar tu suscripción, actualiza tu método de pago.
        </Notice>
      )}

      <dl className="mt-6 grid grid-cols-1 gap-3 border-t border-line pt-6 sm:grid-cols-2">
        {plan.interval && (
          <Detail label="Periodo">{INTERVAL_LABEL[plan.interval]}</Detail>
        )}
        {plan.cancel_at ? (
          <Detail label="Cancelación">
            Se cancelará el {formatPlanFullDate(plan.cancel_at)}
          </Detail>
        ) : (
          plan.current_period_end && (
            <Detail label="Próxima renovación">
              {formatPlanFullDate(plan.current_period_end)}
            </Detail>
          )
        )}
      </dl>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-3">
        <p className="min-w-50 flex-1 text-xs font-medium text-muted">
          Cambia de periodo, actualiza tu tarjeta, descarga tus facturas o
          cancela desde el portal de pagos.
        </p>
        <Button
          variant="ghost"
          onClick={onManage}
          disabled={isRedirecting}
          aria-busy={isRedirecting}
        >
          {isRedirecting && (
            <Spinner className="size-4 animate-spin" aria-hidden />
          )}
          Gestionar suscripción
        </Button>
      </div>
    </>
  );
}

export default function PlanCard() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  // El resultado del Checkout se lee una vez: recargar la página no repite el aviso ni el sondeo.
  const [checkout] = useState(() => searchParams.get('checkout'));
  const [timedOut, setTimedOut] = useState(false);
  const { startCheckout, openPortal, isRedirecting, error } =
    useBillingRedirect();

  useEffect(() => {
    if (searchParams.has('checkout'))
      router.replace(`${pathname}#plan`, { scroll: false });
  }, [pathname, router, searchParams]);
  const awaitingPro = checkout === 'success' && !timedOut;

  const { plan } = usePlan({
    refreshInterval: latest =>
      awaitingPro && latest?.plan !== 'pro' ? ACTIVATION_POLL_MS : 0,
  });

  useEffect(() => {
    if (checkout !== 'success') return;
    const timer = setTimeout(() => setTimedOut(true), ACTIVATION_TIMEOUT_MS);
    return () => clearTimeout(timer);
  }, [checkout]);

  if (!plan) return null;
  const isPro = plan.plan === 'pro';

  return (
    <section
      id="plan"
      aria-labelledby="cuenta-plan-title"
      className="scroll-mt-6 rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)] md:p-7"
    >
      <div className="flex items-start justify-between gap-4">
        <h2
          id="cuenta-plan-title"
          className="text-lg font-bold tracking-tight text-ink"
        >
          Tu plan
        </h2>
        <span
          className={`shrink-0 rounded-full px-3 py-1 text-xs font-extrabold tracking-wide uppercase ${
            isPro ? 'bg-primary text-white' : 'bg-surface text-body'
          }`}
        >
          {PLAN_LABEL[plan.plan]}
        </span>
      </div>

      <CheckoutNotice checkout={checkout} isPro={isPro} timedOut={timedOut} />

      <p className="mt-1 text-sm font-medium text-muted">
        {formatCount(usedThisMonth(plan.limits, plan.usage))} de{' '}
        {formatCount(plan.limits.analyses_per_month)} análisis usados este mes ·
        se renuevan el {formatPlanDate(plan.usage.resets_at)}
      </p>

      {isPro ? (
        <ProPlan
          plan={plan}
          isRedirecting={isRedirecting}
          onManage={() => void openPortal()}
        />
      ) : (
        <FreePlan
          isRedirecting={isRedirecting}
          onCheckout={interval => void startCheckout(interval)}
        />
      )}

      {error && (
        <Notice
          tone="danger"
          role="alert"
          icon={<WarningIcon className={NOTICE_ICON} aria-hidden />}
        >
          {error}
        </Notice>
      )}
    </section>
  );
}
