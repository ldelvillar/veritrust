import type { paths } from '@/types/api';

export type DashboardPayload =
  paths['/dashboard/summary']['get']['responses']['200']['content']['application/json'];
export type DashboardAlertItem = DashboardPayload['alerts'][number];
