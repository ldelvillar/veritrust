import Arrow from '@/assets/Arrow';
import PublicButton from '@/components/PublicButton';
import { container } from './container';

export default function Cta() {
  return (
    <section
      id="contacto"
      aria-labelledby="cta-title"
      className="bg-white py-20"
    >
      <div className={container}>
        <div className="relative overflow-hidden rounded-3xl bg-primary px-14 py-16 text-center text-white max-[560px]:px-6.5 max-[560px]:py-12">
          <div className="relative z-2 mx-auto max-w-160">
            <h2
              id="cta-title"
              className="mb-4 font-display text-display-md font-normal tracking-[-0.005em] text-white max-[560px]:text-3xl"
            >
              Frena la desinformación médica antes de que se difunda
            </h2>
            <p className="mb-8 text-lg leading-[1.55] text-white/88">
              Solicita una demo para tu redacción o tu institución, o empieza a
              analizar gratis ahora mismo.
            </p>
            <div className="flex flex-wrap justify-center gap-3.5">
              <PublicButton href="/demo" variant="light" size="lg">
                Solicitar demo
              </PublicButton>
              <PublicButton href="/app/analisis" variant="outline" size="lg">
                Analizar gratis <Arrow className="size-4 rotate-270" />
              </PublicButton>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
