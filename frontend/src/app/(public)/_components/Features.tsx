import type { SVGProps } from 'react';
import CodeIcon from '@/assets/Code';
import GlobeIcon from '@/assets/Globe';
import ListIcon from '@/assets/List';
import ShieldIcon from '@/assets/Shield';
import TypeIcon from '@/assets/Type';
import UploadIcon from '@/assets/Upload';
import { container } from './container';

type Feature = {
  accent: string;
  accentSoft: string;
  title: string;
  body: string;
  Icon: (props: SVGProps<SVGSVGElement>) => React.JSX.Element;
};

const features: Feature[] = [
  {
    accent: '#6356e6',
    accentSoft: '#eeebfc',
    title: 'Tres vías de entrada',
    body: 'Analiza texto pegado, enlaces de artículos o documentos (PDF, DOCX, TXT e imágenes) desde una sola herramienta.',
    Icon: TypeIcon,
  },
  {
    accent: '#2c97e8',
    accentSoft: '#e4f1fc',
    title: 'Análisis afirmación por afirmación',
    body: 'No una etiqueta genérica: cada frase verificable recibe su propio veredicto, con explicación y matices.',
    Icon: ListIcon,
  },
  {
    accent: '#13b877',
    accentSoft: '#def4ea',
    title: 'Fuentes médicas citadas',
    body: 'Cada veredicto enlaza las referencias usadas —OMS, Cochrane, NIH— para que puedas auditarlo y defenderlo.',
    Icon: GlobeIcon,
  },
  {
    accent: '#e0a13b',
    accentSoft: '#fbefda',
    title: 'Informes exportables',
    body: 'Descarga el informe completo en PDF para tu fact-check, tu campaña o tu archivo editorial.',
    Icon: UploadIcon,
  },
  {
    accent: '#7c4ddc',
    accentSoft: '#efe7fb',
    title: 'API e integración',
    body: 'Conecta VeriTrust a tu CMS o a tu flujo de monitorización para verificar a escala, sin trabajo manual.',
    Icon: CodeIcon,
  },
  {
    accent: '#13b877',
    accentSoft: '#def4ea',
    title: 'Privacidad por diseño',
    body: 'El contenido se procesa de forma privada y no se usa para entrenar modelos. Acuerdos de datos para instituciones.',
    Icon: ShieldIcon,
  },
];

export default function Features() {
  return (
    <section id="features" className="bg-[#eeedf8] py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-primary uppercase">
            Características
          </span>
          <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-[#15162c] md:text-[40px]">
            Todo lo que necesitas para verificar con rigor
          </h2>
          <p className="text-[17px] leading-relaxed text-[#6f7090]">
            Pensado para equipos que no pueden permitirse publicar o difundir un
            bulo médico.
          </p>
        </div>
        <div className="grid gap-5.5 md:grid-cols-2 lg:grid-cols-3">
          {features.map(feat => (
            <article
              key={feat.title}
              style={
                {
                  '--accent': feat.accent,
                  '--accent-soft': feat.accentSoft,
                } as React.CSSProperties
              }
              className="group relative overflow-hidden rounded-[18px] border border-[#e8e6f4] bg-white px-6.5 py-7 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)] transition duration-220 ease-in-out after:pointer-events-none after:absolute after:-top-11.5 after:-right-11.5 after:size-35 after:rounded-full after:bg-[radial-gradient(circle,var(--accent-soft),transparent_70%)] after:opacity-0 after:transition-opacity after:duration-250 after:content-[''] hover:-translate-y-1 hover:border-(--accent-soft) hover:shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)] hover:after:opacity-85"
            >
              <div className="relative z-2 mb-4.5 grid size-12.5 place-items-center rounded-[14px] bg-(--accent-soft) text-(--accent) transition duration-220 ease-in-out group-hover:-translate-y-0.5 group-hover:shadow-[0_10px_22px_color-mix(in_srgb,var(--accent)_26%,transparent)]">
                <feat.Icon className="size-5.75" />
              </div>
              <h3 className="relative z-2 mb-2 text-[17px] font-semibold text-[#15162c]">
                {feat.title}
              </h3>
              <p className="relative z-2 text-[14px] leading-[1.55] text-[#6f7090]">
                {feat.body}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
