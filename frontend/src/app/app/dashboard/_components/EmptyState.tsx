import Link from 'next/link';
import Magnifier from '@/assets/Magnifier';

export default function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-12">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-[#e8e6f4] bg-white p-8 text-center shadow-sm">
        <div className="mx-auto flex size-14 items-center justify-center rounded-2xl bg-[#eeebfc] text-[#6356e6]">
          <Magnifier className="size-7" />
        </div>
        <h1 className="mt-5 text-2xl font-black tracking-tight text-[#15162c]">
          Empieza tu primer análisis
        </h1>
        <p className="mt-2 text-sm font-medium" style={{ color: '#7e7f99' }}>
          Tu panel se llenará con métricas, tendencias y alertas en cuanto
          verifiques tu primer contenido médico.
        </p>
        <Link
          href="/app/analisis"
          className="mt-6 inline-flex items-center justify-center gap-2 rounded-xl bg-[#6356e6] px-5 py-3 text-sm font-bold text-white shadow-[0_8px_20px_rgba(99,86,230,.32)] transition hover:bg-[#5446dc] focus:ring-4 focus:ring-[#6356e6]/20 focus:outline-none"
        >
          Analizar contenido
        </Link>
      </div>
    </div>
  );
}
