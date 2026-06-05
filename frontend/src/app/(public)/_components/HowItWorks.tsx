import Document from '@/assets/Document';
import ExtractIcon from '@/assets/Extract';
import MedicalCrossIcon from '@/assets/MedicalCross';
import NewspaperIcon from '@/assets/Newspaper';
import ShieldIcon from '@/assets/Shield';
import TranslateIcon from '@/assets/Translate';
import { container } from './container';

const steps = [
  {
    n: '01',
    accent: '#6356e6',
    accentSoft: '#eeebfc',
    title: 'Extractor de información',
    body: 'Lee el contenido y aísla cada afirmación médica, las cifras y las fuentes citadas, sin perder el contexto.',
    chips: ['Afirmaciones', 'Cifras', 'Referencias'],
    Icon: ExtractIcon,
  },
  {
    n: '02',
    accent: '#2c97e8',
    accentSoft: '#e4f1fc',
    title: 'Traductor',
    body: 'Normaliza el idioma y estandariza la terminología clínica para que cada afirmación se contraste sobre una base común.',
    chips: ['Idioma', 'Terminología', 'Normalización'],
    Icon: TranslateIcon,
  },
  {
    n: '03',
    accent: '#e0922e',
    accentSoft: '#fbeede',
    title: 'Investigador',
    body: 'Busca evidencia científica en la literatura biomédica y reúne las fuentes que respaldan o contradicen cada afirmación.',
    chips: ['Evidencia', 'Fuentes', 'Literatura'],
    Icon: NewspaperIcon,
  },
  {
    n: '04',
    accent: '#13b877',
    accentSoft: '#def4ea',
    title: 'Experto en salud',
    body: 'Contrasta cada afirmación con el consenso médico y las fuentes de referencia, y calcula la puntuación de credibilidad.',
    chips: ['Consenso', 'Fuentes', 'Puntuación'],
    Icon: MedicalCrossIcon,
  },
];

function ConnectorNode({
  from,
  to,
  className,
}: {
  from: string;
  to: string;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      style={{ '--from': from, '--to': to } as React.CSSProperties}
      className={`absolute top-16 z-3 hidden size-8.5 place-items-center lg:grid ${className ?? ''}`}
    >
      <span className="absolute size-2.5 animate-ping rounded-full bg-(--from) opacity-60" />
      <span className="relative size-2.5 rounded-full bg-[linear-gradient(135deg,var(--from),var(--to))] shadow-[0_0_12px_2px_color-mix(in_srgb,var(--from)_45%,transparent)]" />
    </span>
  );
}

export default function HowItWorks() {
  return (
    <section id="como-funciona" className="py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Cómo funciona
          </span>
          <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
            Agentes especializados, un veredicto fiable
          </h2>
          <p className="text-[17px] leading-relaxed text-[#6f7090]">
            VeriTrust no es una caja negra. Cada afirmación pasa por una cadena
            de especialistas de IA que se complementan, y verás exactamente qué
            aportó cada uno.
          </p>
        </div>
        {/* pipeline flow */}
        <div
          role="presentation"
          className="mx-auto mb-7.5 flex max-w-190 items-center"
        >
          <span className="inline-flex items-center gap-2.25 rounded-full border border-[#e8e6f4] bg-white px-4 py-2.25 text-[13.5px] font-semibold whitespace-nowrap text-[#33344c] shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]">
            <Document className="size-4.25 text-primary" />
            Entrada
          </span>
          <span
            aria-hidden="true"
            className="relative -mx-px h-0.5 flex-1 bg-[linear-gradient(90deg,#dcd9ee_60%,transparent_0)] bg-size-[10px_2px] bg-repeat-x after:absolute after:top-1/2 after:-right-px after:size-0 after:-translate-y-1/2 after:border-y-[5px] after:border-l-[7px] after:border-y-transparent after:border-l-[#dcd9ee] after:content-['']"
          />
          <span className="inline-flex items-center gap-2.25 rounded-full border border-[#bfe8d4] bg-[#def4ea] px-4 py-2.25 text-[13.5px] font-semibold whitespace-nowrap text-[#0e8e5b] shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)]">
            <ShieldIcon className="size-4.25" strokeWidth={2} />
            Veredicto
          </span>
        </div>

        <div className="relative grid gap-6.5 sm:grid-cols-2 lg:grid-cols-4">
          {/* connector nodes (desktop) */}
          <ConnectorNode
            from="#6356e6"
            to="#2c97e8"
            className="left-[calc(25%-17px)]"
          />
          <ConnectorNode
            from="#2c97e8"
            to="#e0922e"
            className="left-[calc(50%-17px)]"
          />
          <ConnectorNode
            from="#e0922e"
            to="#13b877"
            className="left-[calc(75%-17px)]"
          />

          {steps.map(step => (
            <article
              key={step.n}
              style={
                {
                  '--accent': step.accent,
                  '--accent-soft': step.accentSoft,
                } as React.CSSProperties
              }
              className="relative overflow-hidden rounded-[20px] border border-[#e8e6f4] bg-white px-7 pt-7.5 pb-7 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)] transition duration-200 before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-(--accent) before:content-[''] after:pointer-events-none after:absolute after:-top-10 after:-right-10 after:size-37.5 after:rounded-full after:bg-[radial-gradient(circle,var(--accent-soft),transparent_70%)] after:opacity-70 after:content-[''] hover:-translate-y-1.25 hover:border-(--accent-soft) hover:shadow-[0_24px_60px_rgba(60,50,140,0.18)]"
            >
              <div className="relative z-2 mb-5 flex items-center justify-between">
                <div className="grid size-14.5 place-items-center rounded-2xl bg-(--accent-soft) text-(--accent) shadow-[0_8px_18px_color-mix(in_srgb,var(--accent)_22%,transparent)]">
                  <step.Icon className="size-7" />
                </div>
                <span className="grid size-10.5 place-items-center rounded-full border-2 border-(--accent-soft) bg-white text-[15px] font-bold text-(--accent)">
                  {step.n}
                </span>
              </div>
              <h3 className="relative z-2 mb-2.5 text-xl font-semibold text-[#15162c]">
                {step.title}
              </h3>
              <p className="relative z-2 text-[14.5px] leading-relaxed text-[#6f7090]">
                {step.body}
              </p>
              <div className="relative z-2 mt-4.5 flex flex-wrap gap-1.75">
                {step.chips.map(chip => (
                  <span
                    key={chip}
                    className="rounded-lg border border-[#e8e6f4] bg-[#faf9fe] px-2.75 py-1.5 text-[11.5px] font-bold text-[#33344c]"
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
