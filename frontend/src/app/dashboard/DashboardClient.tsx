'use client';

import Link from 'next/link';
import { useMemo } from 'react';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { paths } from '@/types/api';

type DashboardPayload =
  paths['/dashboard/summary']['get']['responses']['200']['content']['application/json'];
type DashboardAlertItem = DashboardPayload['alerts'][number];

const SOURCE_TYPE_LABELS: Record<string, string> = {
  text: 'Texto pegado',
  file: 'Carga de archivo',
  url: 'Enlace',
};

const getAlertTitle = (item: DashboardAlertItem): string => {
  if (item.source_type === 'url' && item.input_url) return item.input_url;
  if (item.input_text) return item.input_text;
  return 'Análisis sin título';
};

const formatSignedPercentage = (value: number): string => {
  if (value > 0) return `+${value}%`;
  return `${value}%`;
};

interface DashboardClientProps {
  initialData: DashboardPayload;
}

export default function DashboardClient({ initialData }: DashboardClientProps) {
  const { data } = useApiQuery<DashboardPayload>('/dashboard/summary', {
    fallbackData: initialData,
  });
  const dashboard = data ?? initialData;

  const trendMax = useMemo(() => {
    if (!dashboard.trend.length) return 1;
    return Math.max(1, ...dashboard.trend.map(point => point.total));
  }, [dashboard]);

  return (
    <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Dashboard
          </h1>
          <p className="mt-2 text-sm font-medium text-slate-500">
            Panorama general de actividad, credibilidad y riesgos recientes.
          </p>
        </div>
        <Link
          href="/historial"
          className="inline-flex items-center rounded-xl border border-primary/20 bg-primary/8 px-4 py-2 text-sm font-bold text-primary"
        >
          Ver historial completo
        </Link>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <p className="text-xs font-bold tracking-wider text-slate-400 uppercase">
            Análisis totales
          </p>
          <p className="mt-3 text-3xl font-black text-slate-900">
            {dashboard.kpis.total_analyses}
          </p>
        </article>

        <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <p className="text-xs font-bold tracking-wider text-slate-400 uppercase">
            Tasa de fiabilidad
          </p>
          <p className="mt-3 text-3xl font-black text-emerald-600">
            {dashboard.kpis.reliable_rate}%
          </p>
        </article>

        <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <p className="text-xs font-bold tracking-wider text-slate-400 uppercase">
            Confianza media
          </p>
          <p className="mt-3 text-3xl font-black text-slate-900">
            {dashboard.kpis.average_confidence}%
          </p>
        </article>

        <article className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <p className="text-xs font-bold tracking-wider text-slate-400 uppercase">
            Variación semanal
          </p>
          <p
            className={`mt-3 text-3xl font-black ${
              dashboard.kpis.week_over_week_delta >= 0
                ? 'text-sky-600'
                : 'text-amber-600'
            }`}
          >
            {formatSignedPercentage(dashboard.kpis.week_over_week_delta)}
          </p>
        </article>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[2fr_1fr]">
        <section className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">
            Tendencia (14 días)
          </h2>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Volumen diario de análisis y confianza media del periodo.
          </p>

          <div className="mt-6 flex min-h-44 items-end gap-2 overflow-x-auto pb-2">
            {dashboard.trend.map(point => {
              const barHeight = `${Math.max(12, (point.total / trendMax) * 150)}px`;
              const label = new Date(point.date).toLocaleDateString('es-ES', {
                day: '2-digit',
                month: '2-digit',
              });

              return (
                <div
                  key={point.date}
                  className="flex min-w-10 flex-col items-center"
                >
                  <div
                    className="w-8 rounded-t-md bg-primary/80"
                    style={{ height: barHeight }}
                    title={`${label}: ${point.total} análisis`}
                  />
                  <span className="mt-2 text-[10px] font-semibold text-slate-400">
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">Fuentes</h2>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Reparto por tipo de entrada.
          </p>

          <div className="mt-4 space-y-4">
            {dashboard.source_breakdown.length === 0 ? (
              <p className="text-sm font-medium text-slate-500">
                Aún no hay datos para mostrar.
              </p>
            ) : (
              dashboard.source_breakdown.map(item => {
                const label =
                  SOURCE_TYPE_LABELS[item.source_type] ?? item.source_type;
                return (
                  <article key={item.source_type}>
                    <div className="flex items-center justify-between text-sm font-semibold text-slate-600">
                      <span>{label}</span>
                      <span>{item.total}</span>
                    </div>
                    <p className="mt-1 text-xs font-medium text-slate-400">
                      Confianza media: {item.average_confidence}%
                    </p>
                  </article>
                );
              })
            )}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <section className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">
            Dominios frecuentes
          </h2>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Top de enlaces analizados por frecuencia.
          </p>

          <div className="mt-4 space-y-3">
            {dashboard.domain_breakdown.length === 0 ? (
              <p className="text-sm font-medium text-slate-500">
                No hay dominios registrados todavía.
              </p>
            ) : (
              dashboard.domain_breakdown.map(item => (
                <article
                  key={item.domain}
                  className="rounded-xl border border-border/70 bg-slate-50 px-3 py-2"
                >
                  <p className="truncate text-sm font-bold text-slate-700">
                    {item.domain}
                  </p>
                  <p className="mt-1 text-xs font-medium text-slate-500">
                    {item.total} análisis · Confianza media{' '}
                    {item.average_confidence}%
                  </p>
                </article>
              ))
            )}
          </div>
        </section>

        <section className="rounded-2xl border border-border bg-white p-5 shadow-sm">
          <h2 className="text-xl font-black text-slate-900">
            Alertas recientes
          </h2>
          <p className="mt-1 text-sm font-medium text-slate-500">
            Últimos análisis con baja credibilidad detectada.
          </p>

          <div className="mt-4 space-y-3">
            {dashboard.alerts.length === 0 ? (
              <p className="text-sm font-medium text-slate-500">
                No hay alertas por ahora.
              </p>
            ) : (
              dashboard.alerts.map(item => (
                <article
                  key={item.id}
                  className="rounded-xl border border-red-100 bg-red-50/70 px-3 py-3"
                >
                  <p className="truncate text-sm font-bold text-red-700">
                    {getAlertTitle(item)}
                  </p>
                  <p className="mt-1 text-xs font-semibold text-red-600">
                    Credibilidad: {Math.round(item.confidence * 100)}% ·{' '}
                    {new Date(item.created_at).toLocaleString('es-ES', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                  <Link
                    href={`/analisis/${item.id}`}
                    className="mt-2 inline-flex text-xs font-bold text-red-700 hover:underline"
                  >
                    Ver informe
                  </Link>
                </article>
              ))
            )}
          </div>
        </section>
      </div>
    </>
  );
}
