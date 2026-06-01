import Link from 'next/link';
import Arrow from '@/assets/Arrow';
import { container } from './container';

export default function Cta() {
  return (
    <section id="contacto" className="bg-white py-20">
      <div className={container}>
        <div className="relative overflow-hidden rounded-[28px] bg-[linear-gradient(150deg,#5a44e8,#432dd7_55%,#3722b8)] px-14 py-16 text-center text-white max-md:px-6 max-md:py-12">
          <div className="pointer-events-none absolute -top-30 -right-25 size-95 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
          <div className="relative z-[2] mx-auto max-w-160">
            <span className="inline-flex items-center gap-2.5 rounded-full border border-white/20 bg-white/15 px-3.5 py-2 text-[12.5px] font-extrabold tracking-[0.1em] whitespace-nowrap text-white uppercase">
              <span className="size-1.75 animate-pulse rounded-full bg-[#13b877] shadow-[0_0_0_4px_rgba(19,184,119,0.25)]" />
              Empieza hoy
            </span>
            <h2 className="mt-4.5 mb-4 text-[30px] font-bold tracking-[-0.02em] text-white md:text-[40px]">
              Frena la desinformación médica antes de que se difunda
            </h2>
            <p className="mb-8 text-lg leading-snug text-white/90">
              Solicita una demo para tu redacción o tu institución, o empieza a
              analizar gratis ahora mismo.
            </p>
            <div className="flex flex-wrap justify-center gap-3.5">
              <Link
                href="/demo"
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-4 text-base font-semibold text-primary shadow-[0_8px_22px_rgba(20,22,44,0.12)] transition hover:-translate-y-0.5 hover:shadow-[0_14px_30px_rgba(20,22,44,0.18)]"
              >
                Solicitar demo
              </Link>
              <Link
                href="/app/analisis"
                className="inline-flex items-center justify-center gap-2 rounded-xl border-[1.5px] border-white/40 px-7 py-4 text-base font-semibold text-white transition hover:border-white hover:bg-white/10"
              >
                Analizar gratis <Arrow className="size-4 rotate-270" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
