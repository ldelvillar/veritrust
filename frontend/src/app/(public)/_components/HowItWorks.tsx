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
    title: 'Extractor de información',
    body: 'Lee el contenido y aísla cada afirmación médica, las cifras y las fuentes citadas, sin perder el contexto.',
    Icon: ExtractIcon,
  },
  {
    n: '02',
    title: 'Traductor',
    body: 'Normaliza el idioma y estandariza la terminología clínica para que cada afirmación se contraste sobre una base común.',
    Icon: TranslateIcon,
  },
  {
    n: '03',
    title: 'Investigador',
    body: 'Busca evidencia científica en la literatura biomédica y reúne las fuentes que respaldan o contradicen cada afirmación.',
    Icon: NewspaperIcon,
  },
  {
    n: '04',
    title: 'Experto en salud',
    body: 'Contrasta cada afirmación con el consenso médico y las fuentes de referencia, y calcula la puntuación de credibilidad.',
    Icon: MedicalCrossIcon,
  },
];

export default function HowItWorks() {
  return (
    <section id="como-funciona" className="py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Cómo funciona
          </span>
          <h2 className="my-4 font-display text-[34px] font-normal tracking-[-0.005em] text-ink md:text-[42px]">
            Agentes especializados, un veredicto fiable
          </h2>
          <p className="text-[17px] leading-relaxed text-muted">
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
          <span className="inline-flex items-center gap-2.25 rounded-full border border-line bg-white px-4 py-2.25 text-[13.5px] font-semibold whitespace-nowrap text-body shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]">
            <Document className="size-4.25 text-primary" />
            Entrada
          </span>
          <span
            aria-hidden="true"
            className="relative -mx-px h-0.5 flex-1 bg-[linear-gradient(90deg,var(--color-line-strong)_60%,transparent_0)] bg-size-[10px_2px] bg-repeat-x after:absolute after:top-1/2 after:-right-px after:size-0 after:-translate-y-1/2 after:border-y-[5px] after:border-l-[7px] after:border-y-transparent after:border-l-line-strong after:content-['']"
          />
          <span className="inline-flex items-center gap-2.25 rounded-full border border-verdict-real-soft bg-verdict-real-soft px-4 py-2.25 text-[13.5px] font-semibold whitespace-nowrap text-verdict-real-ink shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]">
            <ShieldIcon className="size-4.25" strokeWidth={2} />
            Veredicto
          </span>
        </div>

        <div className="grid gap-6.5 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map(step => (
            <article
              key={step.n}
              className="relative overflow-hidden rounded-[20px] border border-line bg-white px-7 pt-7.5 pb-7 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)] transition duration-200 before:absolute before:inset-x-0 before:top-0 before:h-1 before:bg-primary before:content-[''] hover:-translate-y-1.25 hover:border-primary-soft hover:shadow-[0_24px_60px_rgba(18,33,31,0.16)]"
            >
              <div className="relative z-2 mb-5 flex items-center justify-between">
                <div className="grid size-14.5 place-items-center rounded-2xl bg-primary-soft text-primary">
                  <step.Icon className="size-7" />
                </div>
                <span className="grid size-10.5 place-items-center rounded-full border-2 border-primary-soft bg-white text-[15px] font-bold text-primary">
                  {step.n}
                </span>
              </div>
              <h3 className="relative z-2 mb-2.5 text-xl font-semibold text-ink">
                {step.title}
              </h3>
              <p className="relative z-2 text-[14.5px] leading-relaxed text-muted">
                {step.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
