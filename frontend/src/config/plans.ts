import type { BillingInterval, PlanName } from '@/lib/plan';

// Pro prices including VAT, as Stripe charges them, shared by the landing and /app/cuenta.
export const PRO_PRICE: Record<BillingInterval, string> = {
  month: '29€',
  year: '290€',
};

export const PLAN_LABEL: Record<PlanName, string> = {
  free: 'Gratis',
  pro: 'Pro',
};

export const FREE_FEATURES = [
  '10 análisis al mes',
  'Textos de hasta 3.000 caracteres',
  'Verifica contenidos de texto y enlaces',
  'Historial de los últimos 30 días',
  'Los mismos modelos y fuentes que Pro',
];

export const PRO_FEATURES = [
  '300 análisis al mes',
  'Textos de hasta 10.000 caracteres',
  'Verifica contenido de archivos',
  'Historial completo con búsqueda, filtros y dashboard',
  'Descarga de informes en PDF',
  'Exportación a CSV',
  'Enlaces públicos para compartir informes',
  'Úsalo desde asistentes de IA (MCP)',
];
