import type { components } from '@/types/api';

export type PlanResponse = components['schemas']['PlanResponse'];
type PlanLimits = PlanResponse['limits'];
export type PlanName = PlanResponse['plan'];
export type PlanUsage = PlanResponse['usage'];
export type BillingInterval =
  components['schemas']['CheckoutRequest']['interval'];

export const PLAN_PATH = '/billing/plan';

// Anchor of the Plan card in /app/cuenta, the target of every «Hazte Pro».
export const UPGRADE_HREF = '/app/cuenta#plan';

// API errors that reveal the Plan the client shows is no longer current.
const PLAN_ERROR_CODES = new Set<string>([
  'PLAN_REQUIRED',
  'ALLOWANCE_EXHAUSTED',
  'TEXT_TOO_LONG_FOR_PLAN',
  'ALREADY_SUBSCRIBED',
] satisfies components['schemas']['ErrorCode'][]);

export function isPlanError(code: string | null): boolean {
  return code !== null && PLAN_ERROR_CODES.has(code);
}

// Billing dates in Madrid time, since the Allowance renews there on the 1st at 00:00.
const dateFormatter = new Intl.DateTimeFormat('es-ES', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Europe/Madrid',
});

const fullDateFormatter = new Intl.DateTimeFormat('es-ES', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'Europe/Madrid',
});

export function formatPlanDate(iso: string): string {
  return dateFormatter.format(new Date(iso));
}

// With the year, since a yearly renewal or a cancellation can fall next year.
export function formatPlanFullDate(iso: string): string {
  return fullDateFormatter.format(new Date(iso));
}

// Always grouped, since es-ES leaves «3000» without a dot and the landing writes «3.000».
const countFormatter = new Intl.NumberFormat('es-ES', {
  useGrouping: 'always',
});

export const formatCount = (value: number): string =>
  countFormatter.format(value);

// Units already committed this month, the consumed ones plus those reserved by pending analyses.
export function usedThisMonth(limits: PlanLimits, usage: PlanUsage): number {
  return limits.analyses_per_month - usage.remaining;
}
