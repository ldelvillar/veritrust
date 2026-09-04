import type { Metadata } from 'next';

import ArrowRightIcon from '@/assets/ArrowRight';
import BellIcon from '@/assets/Bell';
import ClockIcon from '@/assets/Clock';
import MailIcon from '@/assets/Mail';
import NewspaperIcon from '@/assets/Newspaper';
import PhoneIcon from '@/assets/Phone';
import PinIcon from '@/assets/Pin';
import ContactForm from './_components/ContactForm';
import { SITE_CONFIG } from '@/config/site';

export const metadata: Metadata = {
  title: 'Contacto',
  alternates: { canonical: '/contacto' },
  description:
    'Ponte en contacto con el equipo de VeriTrust. Soporte, prensa, alianzas y ventas para el detector de noticias falsas de salud con IA.',
};

const container = 'mx-auto w-full max-w-345 px-5 md:px-8';

const channels = [
  {
    Icon: MailIcon,
    title: 'Ventas y demos',
    desc: 'Para equipos e instituciones que quieren verificar a escala.',
    link: { label: 'Solicitar demo', href: '/demo' },
  },
  {
    Icon: BellIcon,
    title: 'Soporte',
    desc: '¿Algo no funciona o tienes dudas sobre tu cuenta? Te ayudamos.',
    link: {
      label: SITE_CONFIG.email,
      href: `mailto:${SITE_CONFIG.email}`,
    },
  },
  {
    Icon: NewspaperIcon,
    title: 'Prensa y alianzas',
    desc: 'Medios, organismos de salud y colaboraciones de investigación.',
    link: {
      label: SITE_CONFIG.email,
      href: `mailto:${SITE_CONFIG.email}`,
    },
  },
];

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'ContactPage',
  '@id': `${SITE_CONFIG.domain}/contacto/#webpage`,
  url: `${SITE_CONFIG.domain}/contacto`,
  name: 'Contacto VeriTrust',
  description:
    'Contacta con VeriTrust para soporte general, prensa, alianzas de verificación de salud o preguntas.',
  isPartOf: {
    '@id': `${SITE_CONFIG.domain}/#website`,
  },
  mainEntity: [
    {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      email: SITE_CONFIG.email,
      telephone: SITE_CONFIG.phone,
      name: 'Atención al Cliente VeriTrust',
      availableLanguage: ['Spanish', 'English'],
    },
    {
      '@type': 'ContactPoint',
      contactType: 'public relations',
      email: SITE_CONFIG.email,
      name: 'Prensa y Alianzas VeriTrust',
      availableLanguage: ['Spanish', 'English'],
    },
  ],
};

export default function ContactoPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      {/* ===================== SUBHEAD ===================== */}
      <section className="relative overflow-hidden bg-primary pt-16 pb-30 text-center text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.07)_1px,transparent_1px)] bg-size-[26px_26px] opacity-60" />
        <div className="pointer-events-none absolute -top-45 -right-40 size-130 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
        <div className="relative z-2 mx-auto max-w-180 px-5">
          <h1 className="mt-5 mb-4 font-display text-[34px] font-normal tracking-[-0.01em] text-white md:text-[46px]">
            Hablemos
          </h1>
          <p className="mx-auto max-w-150 text-[18px] leading-relaxed text-white/90">
            ¿Tienes una pregunta sobre VeriTrust, una propuesta de alianza o
            necesitas soporte? Elige el canal que mejor encaje o escríbenos
            directamente.
          </p>
        </div>
      </section>

      {/* ===================== CHANNELS + FORM ===================== */}
      <section className={`${container} relative z-5 -mt-21 pb-22.5`}>
        <div className="mb-8.5 grid gap-5.5 md:grid-cols-3">
          {channels.map(({ Icon, title, desc, link }) => (
            <div
              key={title}
              className="group rounded-xs border border-line-strong bg-white px-6.5 py-7 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_4px_14px_rgba(18,33,31,0.04)] transition hover:-translate-y-0.75 hover:border-line-strong hover:shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]"
            >
              <div className="mb-4.5 grid size-12 place-items-center rounded-xs bg-primary-soft text-accent">
                <Icon className="size-5.75" />
              </div>
              <h3 className="mb-1.75 text-[17px] font-bold text-ink">
                {title}
              </h3>
              <p className="mb-3.5 text-[13.5px] leading-snug text-muted">
                {desc}
              </p>
              <a
                href={link.href}
                className="inline-flex items-center gap-1.75 text-[14.5px] font-semibold text-accent transition hover:text-primary"
              >
                {link.label}
                <ArrowRightIcon
                  className="size-4 transition group-hover:translate-x-0.75"
                  strokeWidth={2.1}
                />
              </a>
            </div>
          ))}
        </div>

        <div className="grid items-start gap-6.5 md:grid-cols-2">
          <ContactForm />

          {/* info side */}
          <div className="rounded-xs border border-line-strong bg-white px-8 py-8.5 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]">
            <h3 className="font-display text-[26px] leading-[1.1] font-normal tracking-[-0.005em] text-ink">
              Otras formas de encontrarnos
            </h3>
            <p className="mt-1.5 mb-6 text-[14px] leading-snug text-muted">
              Datos directos del equipo de VeriTrust.
            </p>

            <div className="flex items-start gap-3.5 pt-1 pb-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-xs bg-surface text-accent">
                <MailIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-ink">
                  Email general
                </h4>
                <a
                  href={`mailto:${SITE_CONFIG.email}`}
                  className="text-[13.5px] font-semibold text-accent hover:underline"
                >
                  {SITE_CONFIG.email}
                </a>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-line py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-xs bg-surface text-accent">
                <PhoneIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-ink">
                  Teléfono
                </h4>
                <p className="text-[13.5px] text-muted">{SITE_CONFIG.phone}</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-line py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-xs bg-surface text-accent">
                <PinIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-ink">
                  Ubicación
                </h4>
                <p className="text-[13.5px] text-muted">Madrid, España.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-line py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-xs bg-surface text-accent">
                <ClockIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-ink">
                  Tiempo de respuesta
                </h4>
                <p className="text-[13.5px] text-muted">
                  Menos de 24&nbsp;h laborables en todos los canales
                </p>
              </div>
            </div>

            {/* schematic map */}
            <div
              role="img"
              aria-label="Mapa esquemático de la ubicación de la oficina en Madrid"
              className="relative mt-5.5 h-42.5 overflow-hidden rounded-xs border border-line-strong bg-[linear-gradient(0deg,rgba(12,79,82,0.06),rgba(12,79,82,0.06)),repeating-linear-gradient(0deg,var(--color-line)_0_1px,transparent_1px_34px),repeating-linear-gradient(90deg,var(--color-line)_0_1px,transparent_1px_34px),var(--color-surface-subtle)]"
            >
              <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full text-primary">
                <svg
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-8.5 drop-shadow-[0_6px_10px_rgba(12,79,82,0.35)]"
                >
                  <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z" />
                </svg>
              </span>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
