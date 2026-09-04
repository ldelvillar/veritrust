import Button from '@/components/Button';
import NewIcon from '@/assets/New';
import HistoryIcon from '@/assets/History';

export default function AppNotFound() {
  const radius = 78;
  const circumference = 2 * Math.PI * radius;
  const dash = 14;

  return (
    <div className="flex flex-1 flex-col items-center justify-center px-5 py-8 min-[881px]:px-12 min-[881px]:py-14">
      <div className="animate-fade-in flex w-full flex-col items-center">
        <div className="flex w-full max-w-210 flex-col overflow-hidden rounded-[20px] border border-line bg-white shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)] min-[1180px]:flex-row">
          <div className="flex flex-col items-center justify-center gap-3.5 border-b border-line bg-surface-subtle px-5 py-7 min-[1180px]:basis-68 min-[1180px]:border-r min-[1180px]:border-b-0 min-[1180px]:py-8.5">
            <div className="relative size-43">
              <svg
                width="172"
                height="172"
                viewBox="0 0 172 172"
                className="animate-spin-slow"
                aria-hidden="true"
              >
                <circle
                  cx="86"
                  cy="86"
                  r={radius}
                  fill="none"
                  stroke="var(--color-line)"
                  strokeWidth="9"
                />
                <circle
                  cx="86"
                  cy="86"
                  r={radius}
                  fill="none"
                  stroke="var(--color-verdict-uncertain)"
                  strokeWidth="9"
                  strokeLinecap="round"
                  strokeDasharray={`${dash} ${circumference / 8 - dash}`}
                  opacity={0.85}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-display text-[52px] leading-none font-normal tracking-[0.01em] text-ink">
                  404
                </span>
              </div>
            </div>
            <div className="text-center">
              <div className="text-[11px] font-extrabold tracking-[0.12em] text-faint uppercase">
                Credibilidad
              </div>
              <div className="mt-0.75 text-[13.5px] font-bold text-body">
                Sin datos
              </div>
            </div>
          </div>
          <div className="min-w-0 flex-1 px-5.5 py-6.5 min-[1180px]:px-9.5 min-[1180px]:pt-9.5 min-[1180px]:pb-8.5">
            <h1 className="mb-2.5 font-display text-[30px] leading-[1.1] font-normal tracking-[-0.015em] text-balance text-ink min-[1180px]:text-[40px] min-[1180px]:leading-[1.06]">
              No hay nada que analizar en esta dirección
            </h1>
            <p className="mb-6.5 max-w-[38ch] text-[14.5px] leading-relaxed text-muted">
              La página que has abierto no existe, ha cambiado de sitio o el
              enlace se copió incompleto.
            </p>
            <div className="flex flex-wrap gap-2.5">
              <Button href="/app/analisis" size="lg">
                <NewIcon /> Analizar contenido
              </Button>
              <Button href="/app/historial" variant="soft" size="lg">
                <HistoryIcon /> Ver mis análisis
              </Button>
            </div>
          </div>
        </div>
        <p className="mt-8.5 text-[11.5px] font-bold tracking-[0.11em] text-faint uppercase">
          Error 404 · Recurso no encontrado
        </p>
      </div>
    </div>
  );
}
