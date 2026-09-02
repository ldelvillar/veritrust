import type { SVGProps } from 'react';
import CodeIcon from '@/assets/Code';
import GlobeIcon from '@/assets/Globe';
import ListIcon from '@/assets/List';
import ShieldIcon from '@/assets/Shield';
import TypeIcon from '@/assets/Type';
import UploadIcon from '@/assets/Upload';
import { container } from './container';

type Feature = {
  title: string;
  body: string;
  Icon: (props: SVGProps<SVGSVGElement>) => React.JSX.Element;
};

const features: Feature[] = [
  {
    title: 'Tres vías de entrada',
    body: 'Analiza texto pegado, enlaces de artículos o documentos (PDF, TXT y MD) desde una sola herramienta.',
    Icon: TypeIcon,
  },
  {
    title: 'Análisis afirmación por afirmación',
    body: 'No una etiqueta genérica: cada frase verificable recibe su propio veredicto, con explicación y matices.',
    Icon: ListIcon,
  },
  {
    title: 'Fuentes médicas citadas',
    body: 'Cada veredicto enlaza las referencias usadas —OMS, Cochrane, NIH— para que puedas auditarlo y defenderlo.',
    Icon: GlobeIcon,
  },
  {
    title: 'Informes exportables',
    body: 'Descarga el informe completo en PDF para tu fact-check, tu campaña o tu archivo editorial.',
    Icon: UploadIcon,
  },
  {
    title: 'API e integración',
    body: 'Conecta VeriTrust a tu CMS o a tu flujo de monitorización para verificar a escala, sin trabajo manual.',
    Icon: CodeIcon,
  },
  {
    title: 'Privacidad por diseño',
    body: 'El contenido se procesa de forma privada y no se usa para entrenar modelos. Acuerdos de datos para instituciones.',
    Icon: ShieldIcon,
  },
];

export default function Features() {
  return (
    <section id="features" className="bg-surface py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Características
          </span>
          <h2 className="my-4 font-display text-[34px] font-normal tracking-[-0.005em] text-ink md:text-[42px]">
            Todo lo que necesitas para verificar con rigor
          </h2>
          <p className="text-[17px] leading-relaxed text-muted">
            Pensado para equipos que no pueden permitirse publicar o difundir un
            bulo médico.
          </p>
        </div>
        <div className="grid gap-5.5 md:grid-cols-2 lg:grid-cols-3">
          {features.map(feat => (
            <article
              key={feat.title}
              className="group relative overflow-hidden rounded-[18px] border border-line bg-white px-6.5 py-7 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)] transition duration-220 ease-in-out hover:-translate-y-1 hover:border-primary-soft hover:shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]"
            >
              <div className="relative z-2 mb-4.5 grid size-12.5 place-items-center rounded-[14px] bg-primary-soft text-primary transition duration-220 ease-in-out group-hover:-translate-y-0.5">
                <feat.Icon className="size-5.75" />
              </div>
              <h3 className="relative z-2 mb-2 text-[17px] font-semibold text-ink">
                {feat.title}
              </h3>
              <p className="relative z-2 text-[14px] leading-[1.55] text-muted">
                {feat.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
