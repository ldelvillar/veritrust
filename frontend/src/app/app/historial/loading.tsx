import HistorySkeleton from './_components/HistorySkeleton';

export default function Loading() {
  return (
    <section className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-8 md:px-6 lg:py-10">
      <HistorySkeleton />
    </section>
  );
}
