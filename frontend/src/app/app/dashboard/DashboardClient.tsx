'use client';

import { useMemo, useState } from 'react';
import BookIcon from '@/assets/Book';
import ListIcon from '@/assets/List';
import RefreshIcon from '@/assets/Refresh';
import ShieldIcon from '@/assets/Shield';
import SparkleIcon from '@/assets/Sparkle';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import PageHeader from '@/components/PageHeader';
import { useApiQuery } from '@/hooks/useApiQuery';
import AlertsCard from './_components/AlertsCard';
import CompactKpiCard from './_components/CompactKpiCard';
import DomainsCard from './_components/DomainsCard';
import EmptyState from './_components/EmptyState';
import FeaturedKpiCard from './_components/FeaturedKpiCard';
import RangeSelector, {
  RANGE_DAYS,
  type DashboardRange,
} from './_components/RangeSelector';
import SourcesCard from './_components/SourcesCard';
import TrendChart from './_components/TrendChart';
import VerdictDistributionCard from './_components/VerdictDistributionCard';
import type { DashboardPayload } from './_components/types';

interface DashboardClientProps {
  initialData: DashboardPayload;
}

// El SSR carga el rango por defecto (14 d); solo ese reusa initialData como fallback.
const DEFAULT_RANGE: DashboardRange = '14d';

export default function DashboardClient({ initialData }: DashboardClientProps) {
  const [range, setRange] = useState<DashboardRange>(DEFAULT_RANGE);
  const days = RANGE_DAYS[range];

  const { data, error, refetch } = useApiQuery<DashboardPayload>(
    `/dashboard/summary?trend_days=${days}`,
    { fallbackData: range === DEFAULT_RANGE ? initialData : undefined }
  );

  const dashboard = data ?? initialData;

  const sparkTotal = useMemo(
    () => dashboard.trend.slice(-7).map(t => t.total),
    [dashboard.trend]
  );
  const delta = dashboard.kpis.week_over_week_delta;
  const deltaStr = delta >= 0 ? `+${delta}%` : `${delta}%`;

  // Un cambio de rango que falla no tiene datos propios: avisamos en vez de
  // mostrar en silencio las métricas del rango inicial como si fueran de este.
  if (!data && error) {
    return (
      <div className="flex w-full flex-col gap-5">
        <PageHeader
          eyebrow="Panorama general"
          title="Dashboard"
          subtitle="Actividad, credibilidad y riesgos detectados en el conjunto de tus análisis."
          actions={<RangeSelector value={range} onChange={setRange} />}
        />
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-line bg-white px-8 py-16 text-center shadow-sm">
          <div className="grid size-14 place-items-center rounded-2xl bg-danger-soft text-danger-ink">
            <WarningIcon className="size-7" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-ink">
              No se pudieron cargar las métricas de este periodo
            </h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted">
              Ha sido un problema temporal al calcular tus métricas. Prueba con
              otro periodo o inténtalo de nuevo.
            </p>
          </div>
          <Button onClick={() => refetch()}>
            <RefreshIcon className="size-4.5" aria-hidden />
            Reintentar
          </Button>
        </div>
      </div>
    );
  }

  if (dashboard.kpis.total_analyses === 0) return <EmptyState />;

  return (
    <div className="flex w-full flex-col gap-5">
      <PageHeader
        eyebrow="Panorama general"
        title="Dashboard"
        subtitle="Actividad, credibilidad y riesgos detectados en el conjunto de tus análisis."
        actions={<RangeSelector value={range} onChange={setRange} />}
      />

      {/* KPI tiers */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2.25">
          <p className="pl-0.5 text-2xs font-extrabold tracking-[.11em] text-faint uppercase">
            Volumen y riesgo
          </p>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <FeaturedKpiCard
              label="Análisis totales"
              value={String(dashboard.kpis.total_analyses)}
              sub="en total"
              icon={<ListIcon className="size-5.75" />}
              tint="var(--color-primary-soft)"
              color="var(--color-primary)"
              delta={{ dir: delta >= 0 ? 'up' : 'down', value: deltaStr }}
              spark={sparkTotal.length >= 2 ? sparkTotal : undefined}
              hint="Número total de análisis que has completado."
            />
            <FeaturedKpiCard
              label="Alertas detectadas"
              value={String(dashboard.kpis.active_alerts)}
              sub="veredicto «falso»"
              icon={<WarningIcon className="size-5.75" strokeWidth={2.2} />}
              tint="var(--color-verdict-fake-soft)"
              color="var(--color-verdict-fake-ink)"
              hint="Número total de tus análisis con veredicto «falso» (contenido no fiable)."
            />
          </div>
        </div>

        <div className="flex flex-col gap-2.25">
          <p className="pl-0.5 text-2xs font-extrabold tracking-[.11em] text-faint uppercase">
            Calidad de la evidencia
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <CompactKpiCard
              label="Tasa de fiabilidad"
              value={`${dashboard.kpis.reliable_rate}%`}
              sub="veredicto «verdadero»"
              icon={<ShieldIcon className="size-4.75" strokeWidth={2.1} />}
              tint="var(--color-verdict-real-soft)"
              color="var(--color-verdict-real-ink)"
              hint="Porcentaje de tus análisis con veredicto «verdadero» sobre el total completado."
            />
            <CompactKpiCard
              label="Credibilidad media"
              value={`${dashboard.kpis.average_confidence}%`}
              sub="excluye los dudosos"
              icon={<SparkleIcon className="size-4.75" />}
              tint="var(--color-primary-soft)"
              color="var(--color-primary)"
              hint="Credibilidad media de tu contenido (0 = falso, 100 = verdadero), sobre los análisis con veredicto verdadero o falso."
            />
            <CompactKpiCard
              label="Cobertura de evidencia"
              value={`${dashboard.kpis.average_evidence_coverage}%`}
              sub="media con literatura"
              icon={<BookIcon className="size-4.75" />}
              tint="var(--color-primary-soft)"
              color="var(--color-primary)"
              hint="Porcentaje medio de afirmaciones con literatura biomédica relacionada, sobre tus análisis completados."
            />
          </div>
        </div>
      </div>

      {/* Verdict distribution */}
      <VerdictDistributionCard distribution={dashboard.verdict_distribution} />

      {/* Trend + Sources row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.62fr_1fr]">
        <section className="flex flex-col rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg leading-tight font-bold tracking-[-0.015em] text-ink">
                Tendencia ({days} días)
              </h2>
              <p className="mt-1 text-sm leading-snug text-muted">
                Volumen diario de análisis y credibilidad media del periodo.
              </p>
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-xs font-semibold text-muted">
                <span
                  className="size-3.25 rounded-sm"
                  style={{
                    background: 'var(--color-primary)',
                  }}
                />
                Volumen
              </span>
              <span className="flex items-center gap-1.5 text-xs font-semibold text-muted">
                <span className="inline-block h-0.75 w-4.5 rounded-full bg-accent" />
                Credibilidad
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
