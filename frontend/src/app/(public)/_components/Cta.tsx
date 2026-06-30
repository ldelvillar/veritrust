import Arrow from '@/assets/Arrow';
import Button from '@/components/Button';
import { container } from './container';

export default function Cta() {
  return (
    <section
      id="contacto"
      aria-labelledby="cta-title"
      className="bg-white py-20"
    >
      <div className={container}>
        <div className="relative overflow-hidden rounded-[28px] bg-[linear-gradient(150deg,#5a44e8,#432dd7_55%,#3722b8)] px-14 py-16 text-center text-white max-[560px]:px-6.5 max-[560px]:py-12">
          <div className="pointer-events-none absolute -top-30 -right-25 size-95 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
          <div className="relative z-2 mx-auto max-w-160">
            <h2
              id="cta-title"
              className="mb-4 text-[40px] font-bold tracking-[-0.02em] text-white max-[560px]:text-[30px]"
            >
              Frena la desinformación médica antes de que se difunda
            </h2>
            <p className="mb-8 text-lg leading-[1.55] text-white/88">
              Solicita una demo para tu redacción o tu institución, o empieza a
              analizar gratis ahora mismo.
            </p>
            <div className="flex flex-wrap justify-center gap-3.5">
              <Button href="/demo" variant="light" size="lg">
                Solicitar demo
              </Button>
              <Button href="/app/analisis" variant="outline" size="lg">
                Analizar gratis <Arrow className="size-4 rotate-270" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
