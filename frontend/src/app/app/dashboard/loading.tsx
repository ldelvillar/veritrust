import PageHeader from '@/components/PageHeader';

function Sk({ className }: { className: string }) {
  return <span className={`skeleton block rounded-lg ${className}`} />;
}

export default function Loading() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 px-4 py-8 md:px-6 lg:py-10">
      <PageHeader
        eyebrow="Panorama general"
        title="Dashboard"
        subtitle="Actividad, credibilidad y riesgos detectados en los últimos días."
        actions={<Sk className="h-11 w-47 rounded-xl" />}
      />

      {/* Loading strip */}
      <div className="flex items-center gap-2.5 text-[13px] font-semibold text-muted">
        <span className="size-4.5 shrink-0 animate-spin rounded-full border-[2.5px] border-line-strong border-t-accent" />
        <span>
          Calculando tus métricas…{' '}
          <b className="font-bold text-body">
            agregando los análisis del periodo
          </b>
        </span>
      </div>

      {/* KPI tier skeletons */}
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2.25">
          <Sk className="h-2.75 w-30 rounded-md" />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {Array.from({ length: 2 }, (_, i) => (
              <div
                key={i}
                className="flex items-center gap-5 rounded-[20px] border border-line bg-white p-5.5 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]"
              >
                <Sk className="size-11.5 shrink-0 rounded-[13px]" />
                <div className="flex flex-1 flex-col gap-2.5">
                  <Sk className="h-2.75 w-[48%] rounded-md" />
                  <Sk className="h-9.5 w-24 rounded-[9px]" />
                  <Sk className="h-2.75 w-[40%] rounded-md" />
                </div>
                <Sk className="h-8.5 w-22 shrink-0 rounded-lg" />
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2.25">
          <Sk className="h-2.75 w-37.5 rounded-md" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className="flex flex-col gap-2.75 rounded-[20px] border border-line bg-white p-5 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]"
              >
                <div className="flex items-center gap-2.75">
                  <Sk className="size-8.5 shrink-0 rounded-[10px]" />
                  <Sk className="h-2.75 w-[62%] rounded-md" />
                </div>
                <Sk className="h-7.5 w-18.5 rounded-[9px]" />
                <Sk className="h-2.75 w-[46%] rounded-md" />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trend + Sources skeleton row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1.62fr_1fr]">
        <div className="flex flex-col rounded-[20px] border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]">
          <div className="mb-5">
            <Sk className="mb-2.5 h-4.5 w-40 rounded-[7px]" />
            <Sk className="h-3 w-60 rounded-md" />
          </div>
          <Sk className="h-67.5 w-full rounded-[14px]" />
        </div>

        <div className="flex flex-col rounded-[20px] border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]">
          <div className="mb-5">
            <Sk className="mb-2.5 h-4.5 w-22.5 rounded-[7px]" />
            <Sk className="h-3 w-42.5 rounded-md" />
          </div>
          <Sk className="mb-5.5 h-3.5 rounded-full" />
          {Array.from({ length: 3 }, (_, i) => (
            <div
              key={i}
              className="flex items-center gap-3.5 border-t border-line py-3"
            >
              <Sk className="size-2.5 shrink-0 rounded" />
              <Sk className="h-3 w-13.5 rounded-md" />
              <Sk className="h-2 flex-1 rounded-full" />
              <Sk className="h-3 w-6 rounded-md" />
            </div>
          ))}
        </div>
      </div>

      {/* Domains + Alerts skeleton row */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[1fr_1.1fr]">
        {Array.from({ length: 2 }, (_, col) => (
          <div
            key={col}
            className="flex flex-col rounded-[20px] border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)]"
          >
            <div className="mb-5">
              <Sk className="mb-2.5 h-4.5 w-37.5 rounded-[7px]" />
              <Sk className="h-3 w-50 rounded-md" />
            </div>
            {Array.from({ length: 3 }, (_, i) => (
              <div
                key={i}
                className={`flex items-center gap-3.5 py-3.5 ${i > 0 ? 'border-t border-line' : ''}`}
              >
                <Sk className="size-9.5 shrink-0 rounded-[11px]" />
                <div className="flex flex-1 flex-col gap-2">
                  <Sk className="h-3 w-[62%] rounded-md" />
                  <Sk className="h-2.5 w-[40%] rounded-md" />
                </div>
                <Sk className="h-6 w-14 shrink-0 rounded-full" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
