import type { Metadata } from 'next';

import CodeIcon from '@/assets/Code';
import ScanIcon from '@/assets/Scan';
import ShieldIcon from '@/assets/Shield';
import UploadIcon from '@/assets/Upload';
import DemoForm from './_components/DemoForm';

export const metadata: Metadata = {
  title: 'Solicitar demo | VeriTrust',
  description:
    'Solicita una demo de VeriTrust, el detector de noticias falsas de salud con IA. Te mostramos cómo verificar afirmaciones médicas a escala para tu redacción o institución.',
  openGraph: {
    type: 'website',
    title: 'Solicitar demo | VeriTrust',
    description:
      'Descubre cómo VeriTrust verifica afirmaciones médicas con un sistema multiagente de IA. Pide tu demo personalizada.',
    locale: 'es_ES',
  },
};

const container = 'mx-auto w-full max-w-295 px-5 md:px-8';

const benefits = [
  {
    Icon: ScanIcon,
    title: 'El sistema multiagente en vivo',
    desc: 'Cómo el extractor, el traductor, el investigador y el experto en salud llegan a un veredicto.',
  },
  {
    Icon: CodeIcon,
    title: 'Integración por API',
    desc: 'Cómo conectar VeriTrust a tu CMS o flujo de monitorización.',
  },
  {
    Icon: UploadIcon,
    title: 'Informes y exportación',
    desc: 'El formato de informe que respaldará tu fact-check o tu campaña.',
  },
  {
    Icon: ShieldIcon,
    title: 'Privacidad y cumplimiento',
    desc: 'Acuerdos de tratamiento de datos y opciones de despliegue dedicado.',
  },
];

export default function DemoPage() {
  return (
    <>
      {/* ===================== SUBHEAD ===================== */}
      <section className="relative overflow-hidden bg-[linear-gradient(165deg,#5a44e8_0%,#432dd7_50%,#3722b8_100%)] pt-16 pb-30 text-center text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.07)_1px,transparent_1px)] bg-size-[26px_26px] opacity-60" />
        <div className="pointer-events-none absolute -top-45 -right-40 size-130 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
        <div className="relative z-2 mx-auto max-w-180 px-5">
          <h1 className="mt-5 mb-4 text-[34px] font-bold tracking-[-0.03em] text-white md:text-[44px]">
            Solicita una demo de VeriTrust
          </h1>
          <p className="mx-auto max-w-150 text-[18px] leading-relaxed text-white/90">
            Te mostramos cómo verificar afirmaciones médicas a escala con el
            sistema multiagente, adaptado al flujo de tu redacción o
            institución.
          </p>
        </div>
      </section>

      {/* ===================== FORM CARD ===================== */}
      <section className={`${container} relative z-5 -mt-21 pb-22.5`}>
        <div className="grid overflow-hidden rounded-3xl border border-[#e8e6f4] bg-white shadow-[0_24px_60px_rgba(60,50,140,0.18)] md:grid-cols-[1.35fr_0.95fr]">
          <DemoForm />

          {/* benefits aside */}
          <aside className="relative order-first overflow-hidden bg-[#16172e] px-9.5 py-11 text-white md:order-0">
            <div className="pointer-events-none absolute -right-30 -bottom-30 size-80 rounded-full bg-[radial-gradient(circle,rgba(124,110,240,0.4),transparent_62%)]" />
            <div className="relative z-2">
              <h3 className="mb-2 text-[21px] font-bold text-white">
                Qué verás en la demo
              </h3>
              <p className="mb-7 text-[14.5px] leading-relaxed text-white/70">
                30 minutos, en directo, con tus propios ejemplos de contenido.
              </p>
              <ul className="flex flex-col gap-5">
                {benefits.map(({ Icon, title, desc }) => (
                  <li key={title} className="flex items-start gap-3.5">
                    <span className="grid size-9.5 shrink-0 place-items-center rounded-[11px] bg-[rgba(124,110,240,0.22)] text-[#bdb3ff]">
                      <Icon className="size-4.75" />
                    </span>
                    <div>
                      <h4 className="mb-0.75 text-[15px] font-bold text-white">
                        {title}
                      </h4>
                      <p className="text-[13px] leading-snug text-white/66">
                        {desc}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="mt-8 border-t border-white/[0.14] pt-7">
                <p className="text-[14.5px] leading-relaxed text-white/90 italic">
                  «Pasamos de tardar una mañana en verificar un bulo a tener un
                  informe con fuentes en minutos.»
                </p>
                <div className="mt-4 flex items-center gap-2.75">
                  <span className="grid size-9.5 place-items-center rounded-full bg-[linear-gradient(150deg,#8b7ff2,#6356e6)] text-[14px] font-bold text-white">
                    MR
                  </span>
                  <div>
                    <div className="text-[13.5px] font-bold text-white">
                      Marta Ruiz
                    </div>
                    <div className="text-[12px] text-white/60">
                      Editora de verificación, redacción nacional
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>
    </>
  );
}
