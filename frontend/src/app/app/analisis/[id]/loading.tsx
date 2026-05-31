import Spinner from '@/assets/Spinner';

export default function Loading() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-12">
      <div className="flex flex-col items-center gap-4 text-gray-500">
        <Spinner className="size-10 animate-spin text-primary" />
        <p className="text-lg font-medium">Cargando análisis...</p>
      </div>
    </div>
  );
}
