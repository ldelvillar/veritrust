// Skeleton bone, a bar with a shimmer whose height and radius each use sets.
function Bone({ className }: { className: string }) {
  return <span className={`skeleton block ${className}`} />;
}

export default function Loading() {
  return (
    <div
      role="status"
      aria-busy="true"
      className="flex flex-1 flex-col px-4 py-8 md:py-10"
    >
      <span className="sr-only">Cargando análisis...</span>
      {/* Same frame as page.tsx and AnalysisResult, so nothing jumps when the report arrives. */}
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div
          className="flex flex-wrap items-start justify-between gap-4"
          aria-hidden="true"
        >
          <div className="flex min-w-60 flex-1 flex-col gap-2.5">
            <Bone className="h-8 w-[46%] rounded-md" />
            <Bone className="h-3 w-[78%] rounded-md" />
            <Bone className="h-3 w-[52%] rounded-md" />
          </div>
          <div className="flex flex-wrap gap-2.5">
            {['w-30', 'w-38', 'w-28', 'w-24'].map(width => (
              <Bone key={width} className={`h-9.5 rounded-xl ${width}`} />
            ))}
          </div>
        </div>

        <div className="@container" aria-hidden="true">
          <div className="skeleton-on-dark grid min-h-59 rounded-3xl bg-ink-deep @4xl:grid-cols-[300px_minmax(0,1fr)]">
            <div className="flex flex-col justify-between gap-5 border-b border-white/10 px-8 py-7 @4xl:border-r @4xl:border-b-0">
              <Bone className="h-3 w-21 rounded-md" />
              <Bone className="h-20 w-33 rounded-xl" />
              <Bone className="h-1 w-full rounded-md" />
            </div>
            <div className="flex flex-col gap-3 px-9 py-7">
              <Bone className="h-3 w-24 rounded-md" />
              <Bone className="h-7.5 w-[48%] rounded-md" />
              <Bone className="h-3 w-[86%] rounded-md" />
              <Bone className="h-3 w-[64%] rounded-md" />
              <div className="mt-2.5 grid grid-cols-[repeat(2,minmax(0,220px))] gap-7">
                {[0, 1].map(key => (
                  <div key={key} className="flex flex-col gap-2">
                    <Bone className="h-3 w-[70%] rounded-md" />
                    <Bone className="h-4 w-[45%] rounded-md" />
                    <Bone className="h-0.75 w-full rounded-md" />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-6" aria-hidden="true">
          <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
            <Bone className="h-4.5 w-45 rounded-md" />
            <Bone className="h-3 w-35 rounded-md" />
            <Bone className="mt-1.5 h-65 w-full rounded-lg" />
          </div>
          <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
            <Bone className="h-4.5 w-50 rounded-md" />
            {['w-[96%]', 'w-[92%]', 'w-[98%]', 'w-[70%]'].map(width => (
              <Bone key={width} className={`h-3 rounded-md ${width}`} />
            ))}
          </div>
          <div className="flex flex-col gap-3 rounded-xl border border-line bg-white p-6 shadow-sm">
            <Bone className="h-4.5 w-55 rounded-md" />
            {[0, 1, 2].map(key => (
              <div
                key={key}
                className="flex items-center gap-3 border-t border-line py-2.5"
              >
                <Bone className="size-5.5 rounded-full" />
                <Bone className="h-3 flex-1 rounded-md" />
                <Bone className="h-5.5 w-21 rounded-full" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
