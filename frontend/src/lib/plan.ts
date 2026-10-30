import type { components } from '@/types/api';

export type PlanResponse = components['schemas']['PlanResponse'];
type PlanLimits = PlanResponse['limits'];
export type PlanName = PlanResponse['plan'];
export type PlanUsage = PlanResponse['usage'];
export type BillingInterval =
  components['schemas']['CheckoutRequest']['interval'];

export const PLAN_PATH = '/billing/plan';

// Ancla de la tarjeta del Plan en /app/cuenta: destino de todo «Hazte Pro».
export const UPGRADE_HREF = '/app/cuenta#plan';

// Errores de la API que delatan que el Plan que muestra el cliente ya no es el actual.
const PLAN_ERROR_CODES = new Set<string>([
  'PLAN_REQUIRED',
  'ALLOWANCE_EXHAUSTED',
  'TEXT_TOO_LONG_FOR_PLAN',
  'ALREADY_SUBSCRIBED',
] satisfies components['schemas']['ErrorCode'][]);

export function isPlanError(code: string | null): boolean {
  return code !== null && PLAN_ERROR_CODES.has(code);
}

// Fechas de facturación en hora de Madrid: el Allowance se renueva el día 1 a las 00:00 de allí.
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

// Con año: una renovación anual o una cancelación pueden caer el año que viene.
export function formatPlanFullDate(iso: string): string {
  return fullDateFormatter.format(new Date(iso));
}

// Con agrupación siempre: es-ES deja «3000» sin punto, y la landing escribe «3.000».
const countFormatter = new Intl.NumberFormat('es-ES', {
  useGrouping: 'always',
});

export const formatCount = (value: number): string =>
  countFormatter.format(value);

// Unidades ya comprometidas este mes: las consumidas más las reservadas por análisis en curso.
export function usedThisMonth(limits: PlanLimits, usage: PlanUsage): number {
  return limits.analyses_per_month - usage.remaining;
}
