'use client';

import { useMemo } from 'react';
import ListIcon from '@/assets/List';
import ShieldIcon from '@/assets/Shield';
import SparkleIcon from '@/assets/Sparkle';
import WarningIcon from '@/assets/Warning';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import AlertsCard from './_components/AlertsCard';
import DomainsCard from './_components/DomainsCard';
import EmptyState from './_components/EmptyState';
import KpiCard from './_components/KpiCard';
import SourcesCard from './_components/SourcesCard';
import TrendChart from './_components/TrendChart';
import type { DashboardPayload } from './_components/types';

interface DashboardClientProps {
  initialData: DashboardPayload;
}

export default function DashboardClient({ initialData }: DashboardClientProps) {
  const { data } = useApiQuery<DashboardPayload>('/dashboard/summary', {
    fallbackData: initialData,
  });
  const dashboard = data ?? initialData;

  const sparkTotal = useMemo(
    () => dashboard.trend.slice(-7).map(t => t.total),
    [dashboard.trend]
  );
  const sparkConf = useMemo(
    () => dashboard.trend.slice(-7).map(t => t.average_confidence),
    [dashboard.trend]
  );
  const delta = dashboard.kpis.week_over_week_delta;
  const deltaStr = delta >= 0 ? `+${delta}%` : `${delta}%`;

  if (dashboard.kpis.total_analyses === 0) return <EmptyState />;

  return (
    <div className="flex w-full flex-col gap-5">
      <PageHeader
        eyebrow="Panorama general"
        title="Dashboard"
        subtitle="Actividad, credibilidad y riesgos detectados en los últimos 14 días."
      />

      {/* KPI row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label="Análisis totales"
          value={String(dashboard.kpis.total_analyses)}
          sub="este mes"
          icon={<ListIcon className="size-5" />}
          tint="#eeebfc"
          color="#6356e6"
          delta={{ dir: delta >= 0 ? 'up' : 'down', value: deltaStr }}
          spark={sparkTotal.length >= 2 ? sparkTotal : undefined}
          hint="Número total de análisis que has completado."
        />
        <KpiCard
          label="Tasa de fiabilidad"
          value={`${dashboard.kpis.reliable_rate}%`}
          sub="veredicto «fiable»"
          icon={<ShieldIcon className="size-5" strokeWidth={2.1} />}
          tint="#def4ea"
          color="#13b877"
          spark={sparkConf.length >= 2 ? sparkConf : undefined}
          hint="Porcentaje de tus análisis con veredicto «Verdadera» sobre el total completado."
        />
        <KpiCard
          label="Confianza media"
          value={`${dashboard.kpis.average_confidence}%`}
          sub="media ponderada"
          icon={<SparkleIcon className="size-5" />}
          tint="#e4f1fc"
          color="#2c97e8"
          spark={sparkConf.length >= 2 ? sparkConf : undefined}
          hint="Seguridad media del modelo en sus veredictos, promediada sobre todos tus análisis."
        />
        <KpiCard
          label="Alertas activas"
          value={String(dashboard.kpis.active_alerts)}
          sub="baja credibilidad"
          icon={<WarningIcon className="size-5" strokeWidth={2.2} />}
          tint="#fbe4e8"
          color="#e0556b"
          spark={sparkTotal.length >= 2 ? sparkTotal : undefined}
          hint="Análisis recientes con puntuación de credibilidad baja que requieren atención."
        />
      </div>

      {/* Trend + Sources row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.62fr_1fr]">
        <section className="flex flex-col rounded-[20px] border border-line bg-white p-6 shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)]">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-[18px] leading-tight font-bold tracking-[-0.015em] text-ink">
                Tendencia (14 días)
              </h2>
              <p className="mt-1 text-[13px] leading-snug text-muted">
                Volumen diario de análisis y confianza media del periodo.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-[12px] font-semibold text-muted">
                <span
                  className="size-3.25 rounded-sm"
                  style={{
                    background: 'linear-gradient(180deg,#8579f0,#5e50e0)',
                  }}
                />
                Volumen
              </span>
              <span className="flex items-center gap-1.5 text-[12px] font-semibold text-muted">
                <span className="inline-block h-0.75 w-4.5 rounded-full bg-accent" />
                Confianza
              </span>
            </div>
          </div>
          {dashboard.trend.length > 0 ? (
            <TrendChart data={dashboard.trend} />
          ) : (
            <div className="flex min-h-44 items-center justify-center">
              <p className="text-sm font-medium text-muted">
                Sin datos de tendencia todavía.
              </p>
            </div>
          )}
        </section>

        <SourcesCard items={dashboard.source_breakdown} />
      </div>

      {/* Domains + Alerts row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1.1fr]">
        <DomainsCard items={dashboard.domain_breakdown} />
        <AlertsCard
          items={dashboard.alerts}
          total={dashboard.kpis.active_alerts}
        />
      </div>
    </div>
  );
}
