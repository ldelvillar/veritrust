'use client';

import { useState } from 'react';
import CheckIcon from '@/assets/Check';
import PublicButton from '@/components/PublicButton';
import { container } from './container';

type Audience = 'individual' | 'teams';

type Plan = {
  name: string;
  desc: string;
  price: string;
  unit: string;
  yearly?: string;
  badge?: string;
  intro?: string;
  items: string[];
  cta: { label: string; href: string; soft: boolean };
  featured: boolean;
};

const AUDIENCES: { value: Audience; label: string }[] = [
  { value: 'individual', label: 'Individual' },
  { value: 'teams', label: 'Equipos y empresas' },
];

const PLANS: Record<Audience, Plan[]> = {
  individual: [
    {
      name: 'Gratis',
      desc: 'Para curiosos y primeras verificaciones.',
      price: '0€',
      unit: '/ mes',
      items: [
        '10 análisis al mes',
        'Textos de hasta 3.000 caracteres',
        'Verifica contenidos de texto y enlaces',
        'Historial de los últimos 30 días',
        'Los mismos modelos y fuentes que Pro',
      ],
      cta: { label: 'Empezar con gratis', href: '/app', soft: true },
      featured: false,
    },
    {
      name: 'Pro',
      desc: 'Para periodistas y verificadores profesionales.',
      price: '29€',
      unit: '/ mes',
      yearly: 'o 290€ al año (2 meses gratis)',
      intro: 'Todo lo de Gratis, y además:',
      items: [
        '300 análisis al mes',
        'Textos de hasta 10.000 caracteres',
        'Verifica contenido de archivos',
        'Historial completo con búsqueda, filtros y dashboard',
        'Descarga de informes en PDF',
        'Exportación a CSV',
        'Enlaces públicos para compartir informes',
        'Úsalo desde asistentes de IA (MCP)',
      ],
      cta: { label: 'Acceso anticipado', href: '/demo?plan=pro', soft: false },
      featured: true,
    },
  ],
  teams: [
    {
      name: 'Equipo',
      desc: 'Para redacciones, verificadores y agencias de comunicación.',
      price: '35€',
      unit: '/ persona / mes',
      yearly: 'o 350€ por persona al año (2 meses gratis)',
      badge: '2-150 usuarios',
      intro: 'Todo lo de Pro, y además:',
      items: [
        '300 análisis al mes por persona, compartidos',
        'Acuerdo de tratamiento de datos',
        'Administración y cobro centralizado ',
        'Próximamente: historial y dashboard comunes del equipo',
      ],
      cta: {
        label: 'Acceso anticipado',
        href: '/demo?plan=equipo',
        soft: false,
      },
      featured: true,
    },
    {
      name: 'Institución',
      desc: 'Para organizaciones de salud pública e instituciones.',
      price: 'A medida',
      unit: '',
      badge: '+20 usuarios',
      intro: 'Todo lo de Equipo, y además:',
      items: [
        'Volumen de análisis adaptado a tu organización',
        'Acompañamiento en la puesta en marcha',
        'Acceso prioritario a nuevas funcionalidades',
        'Acceso por API con clave propia',
        'Próximamente: SSO, permisos por roles y límites de gasto',
      ],
      cta: { label: 'Hablemos', href: '/demo', soft: true },
      featured: false,
    },
  ],
};

export default function Pricing() {
  const [audience, setAudience] = useState<Audience>('individual');

  return (
    <section id="precios" className="py-24 max-md:py-18">
      <div className={container}>
        <div className="mx-auto mb-9 max-w-170 text-center">
          <span className="text-sm font-extrabold tracking-[0.12em] text-primary uppercase">
            Precios
          </span>
          <h2 className="my-4 font-display text-display-sm font-normal tracking-[-0.005em] text-ink md:text-display-md">
            Empieza gratis, crece cuando lo necesites
          </h2>
          <p className="text-lg leading-relaxed text-muted">
            Sin tarjeta para probar. Los planes de pago están en acceso
            anticipado: apúntate y te avisamos en cuanto abran.
          </p>
        </div>
        <div
          role="group"
          aria-label="Tipo de cliente"
          className="mx-auto mb-12 flex w-fit rounded-full border border-line bg-surface p-1"
        >
          {AUDIENCES.map(option => {
            const active = audience === option.value;
            return (
              <button
                key={option.value}
                type="button"
                aria-pressed={active}
                onClick={() => setAudience(option.value)}
                className={`rounded-full px-5 py-2 text-sm font-bold transition ${
                  active
                    ? 'bg-white text-ink shadow-sm'
                    : 'text-muted hover:text-ink'
                }`}
              >
                {option.label}
              </button>
            );
          })}
        </div>
        <div className="mx-auto grid max-w-5xl items-stretch gap-6 md:grid-cols-2">
          {PLANS[audience].map(plan => {
            return (
              <article
                key={plan.name}
                className={`relative flex flex-col rounded-2xl bg-white px-7.5 py-8.5 ${
                  plan.featured
                    ? 'border-2 border-primary shadow-[0_24px_60px_rgba(18,33,31,0.16)]'
                    : 'border border-line shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)]'
                }`}
              >
                {plan.featured && (
                  <span className="absolute -top-3.25 left-1/2 -translate-x-1/2 rounded-full bg-primary px-3.5 py-1.5 text-2xs font-extrabold tracking-wider text-white uppercase">
                    Más popular
                  </span>
                )}
                {plan.badge && (
                  <span className="absolute top-5 right-5 rounded-full bg-primary-soft px-2.75 py-1 text-2xs font-bold text-primary">
                    {plan.badge}
                  </span>
                )}
                <div className="text-xl font-bold text-ink">{plan.name}</div>
                <p className="mt-1.5 mb-5.5 min-h-10 text-sm leading-snug text-muted">
                  {plan.desc}
                </p>
                <div className="flex items-baseline gap-1.5">
                  <b className="text-5xl font-bold tracking-[-0.03em] text-ink">
                    {plan.price}
                  </b>
                  {plan.unit && (
                    <span className="text-base font-semibold text-muted">
                      {plan.unit}
                    </span>
                  )}
                </div>
                <p className="mt-1.5 mb-4 min-h-5 text-xs font-semibold text-muted">
                  {plan.yearly}
                </p>
                {plan.intro && (
                  <p className="mb-3.25 text-sm font-bold text-ink">
                    {plan.intro}
                  </p>
                )}
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
            );
          })}
        </div>
      </div>
    </section>
  );
}
