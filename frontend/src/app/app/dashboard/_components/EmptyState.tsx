import GridIcon from '@/assets/Dashboard';
import ListIcon from '@/assets/List';
import PlusBoxIcon from '@/assets/PlusBox';
import ShieldIcon from '@/assets/Shield';
import SparkleIcon from '@/assets/Sparkle';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import PageHeader from '@/components/PageHeader';

const HINTS = [
  { icon: ListIcon, label: 'Volumen de análisis' },
  { icon: ShieldIcon, label: 'Tasa de fiabilidad' },
  { icon: WarningIcon, label: 'Alertas de credibilidad' },
] as const;

export default function EmptyState() {
  return (
    <div className="flex w-full flex-col gap-5">
      <PageHeader
        eyebrow="Panorama general"
        title="Dashboard"
        subtitle="Actividad, credibilidad y riesgos detectados en los últimos días."
        actions={
          <Button href="/app/analisis" size="lg">
            <PlusBoxIcon className="size-4.5" />
            Nuevo análisis
          </Button>
        }
      />

      <div className="relative overflow-hidden rounded-3xl border border-line bg-white px-10 py-20 text-center shadow-[0_1px_2px_rgba(20,22,44,.04),0_10px_30px_rgba(92,80,200,.06)] max-md:px-6 max-md:py-15">
        {/* Dot grid background */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(rgba(99,86,230,.10) 1.1px, transparent 1.1px)',
            backgroundSize: '22px 22px',
            maskImage:
              'radial-gradient(ellipse 60% 60% at 50% 38%, #000 0%, transparent 72%)',
            WebkitMaskImage:
              'radial-gradient(ellipse 60% 60% at 50% 38%, #000 0%, transparent 72%)',
          }}
        />

        <div className="relative z-1 flex flex-col items-center">
          {/* Icon */}
          <div className="relative mb-6.5">
            <div className="grid size-21 place-items-center rounded-3xl bg-linear-to-br from-[#7166ef] to-accent text-white shadow-[0_14px_30px_rgba(99,86,230,.34)]">
              <GridIcon className="size-9.5" />
            </div>
            <div className="pointer-events-none absolute -inset-3.5 -z-1 rounded-4xl bg-[radial-gradient(circle,rgba(99,86,230,.22),transparent_68%)]" />
          </div>

          <p className="mb-3.5 text-[11px] font-extrabold tracking-[0.14em] text-accent uppercase">
            Sin datos todavía
          </p>
          <h2 className="mb-3 text-[clamp(22px,2.6vw,27px)] leading-tight font-bold tracking-[-0.025em] text-balance text-ink">
            Aún no hay nada que medir
          </h2>
          <p className="mx-auto mb-7.5 max-w-120 text-[15.5px] leading-relaxed font-medium text-pretty text-muted">
            Tu dashboard cobra vida con tu primer análisis. A medida que
            verifiques contenido, aquí verás tu volumen, la tasa de fiabilidad y
            las alertas de baja credibilidad.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap justify-center gap-3">
            <Button href="/app/analisis" size="lg">
              <PlusBoxIcon className="size-4.5" />
              Analizar mi primer contenido
            </Button>
            <Button href="/app/analisis?demo=true" variant="soft" size="lg">
              <SparkleIcon className="size-4.5" />
              Ver una demostración
            </Button>
          </div>

          {/* Hint badges */}
          <div className="mt-9.5 flex flex-wrap justify-center gap-2.5">
            {HINTS.map(({ icon: Icon, label }) => (
              <span
                key={label}
                className="inline-flex items-center gap-2.5 rounded-xl border border-line bg-surface-subtle px-4 py-2.5 text-[13px] font-semibold text-body"
              >
                <Icon className="size-4.25 shrink-0 text-accent" />
                {label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
