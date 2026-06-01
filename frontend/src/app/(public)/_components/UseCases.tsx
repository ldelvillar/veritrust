import BuildingIcon from '@/assets/Building';
import CheckIcon from '@/assets/Check';
import NewspaperIcon from '@/assets/Newspaper';
import { container } from './container';

const useCases = [
  {
    title: 'Periodistas y verificadores',
    body: 'Comprueba afirmaciones de salud antes de publicar y obtén un informe con fuentes citadas que respalda tu fact-check.',
    items: [
      'Verificación en segundos, no en horas',
      'Informe exportable como evidencia',
      'Historial de todo lo analizado',
    ],
    Icon: NewspaperIcon,
  },
  {
    title: 'Salud pública e instituciones',
    body: 'Monitoriza y desmiente bulos sanitarios a escala. Integra VeriTrust por API y exporta informes para tus campañas.',
    items: [
      'API para verificar a gran volumen',
      'Usuarios en equipo y SSO',
      'Acuerdos de tratamiento de datos',
    ],
    Icon: BuildingIcon,
  },
];

export default function UseCases() {
  return (
    <section id="casos" className="bg-[#16172e] py-24 text-white max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-[13px] font-extrabold tracking-[0.12em] text-[#bdb3ff] uppercase">
            Casos de uso
          </span>
          <h2 className="my-4 text-[32px] font-bold tracking-[-0.02em] text-white md:text-[40px]">
            Hecho para quienes combaten la desinformación
          </h2>
          <p className="text-[17px] leading-relaxed text-white/70">
            Desde redacciones hasta organismos de salud pública, VeriTrust
            acelera la verificación sin renunciar al rigor.
          </p>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {useCases.map(uc => (
            <article
              key={uc.title}
              className="rounded-[20px] border border-white/10 bg-white/5 p-8.5 transition hover:border-white/20 hover:bg-white/8"
            >
              <div className="mb-5 grid size-12.5 place-items-center rounded-[13px] bg-[rgba(124,110,240,0.22)] text-[#bdb3ff]">
                <uc.Icon className="size-6" />
              </div>
              <h3 className="mb-3 text-[22px] font-semibold text-white">
                {uc.title}
              </h3>
              <p className="mb-4.5 text-[14.5px] leading-relaxed text-white/70">
                {uc.body}
              </p>
              <ul className="flex flex-col gap-2.5">
                {uc.items.map(item => (
                  <li
                    key={item}
                    className="flex items-center gap-2.5 text-sm font-medium text-white/85"
                  >
                    <CheckIcon className="size-4.25 shrink-0 text-[#8effc8]" />
                    {item}
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
