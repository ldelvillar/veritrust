// Hueso del esqueleto: una barra con barrido, sobre fondo claro u oscuro.
function Bone({
  className = '',
  dark = false,
}: {
  className?: string;
  dark?: boolean;
}) {
  // Alto y radio por defecto solo si el hueso no trae los suyos, para no chocar en la cascada.
  const height = /\b(h|size)-/.test(className) ? '' : 'h-3';
  const radius = /\brounded-/.test(className) ? '' : 'rounded-md';
  return (
    <span
      className={`block ${height} ${radius} ${dark ? 'skeleton-dark' : 'skeleton'} ${className}`}
    />
  );
}

export default function Loading() {
  return (
    <div
      role="status"
      aria-busy="true"
      className="mx-auto flex w-full max-w-6xl flex-col gap-6"
    >
      <span className="sr-only">Cargando análisis...</span>

      <div
        className="flex flex-wrap items-start justify-between gap-4"
        aria-hidden="true"
      >
        <div className="flex min-w-60 flex-1 flex-col gap-2.5">
          <Bone className="h-8 w-[46%]" />
          <Bone className="w-[78%]" />
          <Bone className="w-[52%]" />
        </div>
        <div className="flex flex-wrap gap-2.5">
          {['w-30', 'w-38', 'w-28', 'w-24'].map(width => (
            <Bone key={width} className={`h-9.5 rounded-xl ${width}`} />
          ))}
        </div>
      </div>

      <div className="@container" aria-hidden="true">
        <div className="grid min-h-59 rounded-3xl bg-ink-deep @4xl:grid-cols-[300px_minmax(0,1fr)]">
          <div className="flex flex-col justify-between gap-5 border-b border-white/10 px-8 py-7 @4xl:border-r @4xl:border-b-0">
            <Bone dark className="w-21" />
            <Bone dark className="h-20 w-33 rounded-xl" />
            <Bone dark className="h-1 w-full" />
          </div>
          <div className="flex flex-col gap-3 px-9 py-7">
            <Bone dark className="w-24" />
            <Bone dark className="h-7.5 w-[48%]" />
            <Bone dark className="w-[86%]" />
            <Bone dark className="w-[64%]" />
            <div className="mt-2.5 grid grid-cols-[repeat(2,minmax(0,220px))] gap-7">
              {[0, 1].map(key => (
                <div key={key} className="flex flex-col gap-2">
                  <Bone dark className="w-[70%]" />
                  <Bone dark className="h-4 w-[45%]" />
                  <Bone dark className="h-0.75 w-full" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-6" aria-hidden="true">
        <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
          <Bone className="h-4.5 w-45" />
          <Bone className="w-35" />
          <Bone className="mt-1.5 h-65 w-full rounded-lg" />
        </div>
        <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
          <Bone className="h-4.5 w-50" />
          {['w-[96%]', 'w-[92%]', 'w-[98%]', 'w-[70%]'].map(width => (
            <Bone key={width} className={width} />
          ))}
        </div>
        <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
          <Bone className="h-4.5 w-55" />
          {[0, 1, 2].map(key => (
            <div
              key={key}
              className="flex items-center gap-3 border-t border-line py-2.5"
            >
              <Bone className="size-5.5 rounded-full" />
              <Bone className="flex-1" />
              <Bone className="h-5.5 w-21 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
