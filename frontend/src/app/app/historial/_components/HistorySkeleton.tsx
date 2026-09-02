import PageHeader from '@/components/PageHeader';

const HISTORY_SUBTITLE =
  'Revisa, filtra y gestiona tus informes de credibilidad previos.';

// Filas esqueleto con la misma silueta que una tarjeta de resultado.
export function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="relative flex items-center gap-4.5 overflow-hidden rounded-2xl border border-line bg-white py-4.5 pr-5.5 pl-6 shadow-sm"
        >
          <span
            className="absolute inset-y-0 left-0 w-1 bg-line-strong"
            aria-hidden
          />
          <div className="skeleton size-12.5 shrink-0 rounded-full" />
          <div className="flex min-w-0 flex-1 flex-col gap-2.25">
            <div className="skeleton h-3 w-30 rounded-md" />
            <div className="skeleton h-3.5 w-[70%] rounded-md" />
            <div className="skeleton h-3 w-[38%] rounded-md" />
          </div>
          <div className="skeleton h-7 w-23 shrink-0 rounded-full" />
          <div className="skeleton h-8.5 w-26 shrink-0 rounded-[9px]" />
        </div>
      ))}
    </div>
  );
}

// Pantalla de carga completa del historial (cabecera + estadísticas + lista).
export default function HistorySkeleton() {
  return (
    <div>
      <div className="mb-6">
        <PageHeader
          eyebrow="Historial"
          title="Análisis anteriores"
          subtitle={HISTORY_SUBTITLE}
        />
      </div>

      <div className="mb-5 flex items-center gap-2.75 text-[13px] font-semibold text-muted">
        <span
          className="size-4.5 shrink-0 animate-spin rounded-full border-[2.5px] border-primary/20 border-t-primary"
          aria-hidden
        />
        <span>Cargando tu historial…</span>
      </div>

      <div className="mb-5.5 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="relative overflow-hidden rounded-[18px] border border-line bg-white p-[18px_20px_20px] shadow-sm"
          >
            <div className="skeleton mb-3.5 h-7.5 w-11.5 rounded-[9px]" />
            <div className="skeleton h-3.25 w-[72%] rounded-md" />
            <span
              className="absolute inset-x-0 bottom-0 h-0.75 bg-line"
              aria-hidden
            />
          </div>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="skeleton h-11.5 min-w-55 flex-1 rounded-[13px]" />
        <div className="skeleton h-11.5 w-70 rounded-[13px]" />
        <div className="skeleton h-11.5 w-37.5 rounded-[13px]" />
      </div>

      <SkeletonRows count={5} />
    </div>
  );
}
