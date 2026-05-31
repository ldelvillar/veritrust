import Spinner from '@/assets/Spinner';

export default function Loading() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <div className="flex items-center justify-center gap-3 rounded-2xl border border-border bg-white px-5 py-12 text-sm font-semibold text-slate-500">
        <Spinner className="size-5 animate-spin text-primary" />
        Cargando dashboard...
      </div>
    </section>
  );
}
