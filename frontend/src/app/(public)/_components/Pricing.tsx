import CheckIcon from '@/assets/Check';
import PublicButton from '@/components/PublicButton';
import { container } from './container';

const plans = [
  {
    name: 'Gratis',
    desc: 'Para curiosos y primeras verificaciones.',
    price: '0€',
    unit: '/ mes',
    items: [
      '10 análisis al mes',
      'Sistema multiagente de IA',
      'Texto, enlace y archivo',
      'Informe con fuentes',
    ],
    cta: { label: 'Analizar gratis', href: '/app/analisis', soft: true },
    featured: false,
  },
  {
    name: 'Pro',
    desc: 'Para periodistas y verificadores profesionales.',
    price: '29€',
    unit: '/ mes',
    items: [
      '500 análisis al mes',
      'Historial y panel completos',
      'Exportar informes en PDF',
      'API básica y prioridad',
    ],
    cta: { label: 'Empezar con Pro', href: '/demo', soft: false },
    featured: true,
  },
  {
    name: 'Clínica',
    desc: 'Para organizaciones de salud pública e instituciones.',
    price: 'A medida',
    unit: '',
    items: [
      'Análisis ilimitados',
      'Usuarios en equipo y SSO',
      'API completa e integración',
      'Soporte y acuerdos de datos',
    ],
    cta: { label: 'Solicitar demo', href: '/demo', soft: true },
    featured: false,
  },
];

export default function Pricing() {
  return (
    <section id="precios" className="py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-14 max-w-170 text-center">
          <span className="text-sm font-extrabold tracking-[0.12em] text-primary uppercase">
            Precios
          </span>
          <h2 className="my-4 font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md">
            Empieza gratis, crece cuando lo necesites
          </h2>
          <p className="text-lg leading-relaxed text-muted">
            Sin tarjeta para probar. Cambia o cancela tu plan cuando quieras.
          </p>
        </div>
        <div className="grid items-stretch gap-6 md:grid-cols-3">
          {plans.map(plan => (
            <article
              key={plan.name}
              className={`relative flex flex-col rounded-2xl bg-white px-7.5 py-8.5 ${
                plan.featured
                  ? 'border-2 border-primary shadow-[0_24px_60px_rgba(18,33,31,0.16)]'
                  : 'border border-line shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]'
              }`}
            >
              {plan.featured && (
                <span className="absolute -top-3.25 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3.5 py-1.5 text-2xs font-extrabold tracking-[0.05em] text-white uppercase">
                  Más popular
                </span>
              )}
              <div className="text-xl font-bold text-ink">{plan.name}</div>
              <p className="mt-1.5 mb-5.5 min-h-10 text-sm leading-snug text-muted">
                {plan.desc}
              </p>
              <div className="mb-5.5 flex items-baseline gap-1.5">
                <b className="text-5xl font-bold tracking-[-0.03em] text-ink">
                  {plan.price}
                </b>
                {plan.unit && (
                  <span className="text-base font-semibold text-muted">
                    {plan.unit}
                  </span>
                )}
              </div>
              <ul className="mb-6.5 flex flex-1 flex-col gap-3.25">
                {plan.items.map(item => (
                  <li
                    key={item}
                    className="flex items-start gap-2.5 text-sm font-medium text-body"
                  >
                    <CheckIcon className="mt-0.5 size-4.25 shrink-0 text-verdict-real" />
                    {item}
                  </li>
                ))}
              </ul>
              <PublicButton
                href={plan.cta.href}
                variant={plan.cta.soft ? 'soft' : 'primary'}
                className="w-full"
              >
                {plan.cta.label}
              </PublicButton>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
