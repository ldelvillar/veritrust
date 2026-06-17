export default function Loading() {
  return (
    <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="mb-7 animate-pulse">
        <div className="h-3 w-16 rounded bg-surface" />
        <div className="mt-3 h-8 w-56 rounded bg-surface" />
        <div className="mt-3 h-3 w-full max-w-md rounded bg-surface" />
      </div>
      <div className="flex animate-pulse flex-col gap-5">
        <div className="h-56 rounded-2xl border border-line bg-white" />
        <div className="h-40 rounded-2xl border border-line bg-white" />
        <div className="h-40 rounded-2xl border border-red-200 bg-white" />
      </div>
    </section>
  );
}
