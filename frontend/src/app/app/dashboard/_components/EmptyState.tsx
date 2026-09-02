import DocumentIcon from '@/assets/Document';
import GridIcon from '@/assets/Dashboard';
import PlusBoxIcon from '@/assets/PlusBox';
import Button from '@/components/Button';
import PageHeader from '@/components/PageHeader';

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

      <div className="relative overflow-hidden rounded-3xl border border-line bg-white px-10 py-20 text-center shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)] max-md:px-6 max-md:py-15">
        {/* Dot grid background */}
        <div
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(rgba(12,79,82,.10) 1.1px, transparent 1.1px)',
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
            <div className="grid size-21 place-items-center rounded-3xl bg-linear-to-br from-primary to-accent text-white shadow-[0_14px_30px_rgba(12,79,82,.34)]">
              <GridIcon className="size-9.5" />
            </div>
            <div className="pointer-events-none absolute -inset-3.5 -z-1 rounded-4xl bg-[radial-gradient(circle,rgba(12,79,82,.22),transparent_68%)]" />
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
            <Button href="/ejemplo" variant="soft" size="lg" target="_blank">
              <DocumentIcon className="size-4.5" />
              Ver una demostración
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
