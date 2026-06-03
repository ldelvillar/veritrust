import type { Metadata } from 'next';

import ContactForm from '@/components/ContactForm';
import { CONFIG } from '@/config';

export const metadata: Metadata = {
  title: 'Contacto | VeriTrust',
  description:
    'Ponte en contacto con el equipo de VeriTrust. Soporte, prensa, alianzas y ventas para el detector de noticias falsas de salud con IA.',
  openGraph: {
    type: 'website',
    title: 'Contacto | VeriTrust',
    description:
      'Habla con el equipo de VeriTrust: soporte, ventas, prensa y alianzas.',
    locale: 'es_ES',
  },
};

const container = 'mx-auto w-full max-w-295 px-5 md:px-8';

type IconProps = { className?: string };

function MailIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M3 8l9 6 9-6M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z" />
    </svg>
  );
}

function BellIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" />
    </svg>
  );
}

function PressIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M4 4h12a2 2 0 0 1 2 2v13a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2zM18 8h2a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2M7 8h7M7 12h7M7 16h4" />
    </svg>
  );
}

function PhoneIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3-8.6A2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" />
    </svg>
  );
}

function PinIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function ClockIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function ArrowIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

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
      label: CONFIG.email,
      href: `mailto:${CONFIG.email}`,
    },
  },
  {
    Icon: PressIcon,
    title: 'Prensa y alianzas',
    desc: 'Medios, organismos de salud y colaboraciones de investigación.',
    link: {
      label: CONFIG.email,
      href: `mailto:${CONFIG.email}`,
    },
  },
];

export default function ContactoPage() {
  return (
    <>
      {/* ===================== SUBHEAD ===================== */}
      <section className="relative overflow-hidden bg-[linear-gradient(165deg,#5a44e8_0%,#432dd7_50%,#3722b8_100%)] pt-16 pb-30 text-center text-white">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(rgba(255,255,255,0.07)_1px,transparent_1px)] bg-[length:26px_26px] opacity-60" />
        <div className="pointer-events-none absolute -top-45 -right-40 size-130 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.16),transparent_62%)]" />
        <div className="relative z-[2] mx-auto max-w-180 px-5">
          <span className="inline-flex items-center gap-2.5 rounded-full border border-white/20 bg-white/15 px-3.5 py-2 text-[12.5px] font-extrabold tracking-[0.1em] whitespace-nowrap text-white uppercase">
            <span className="size-1.75 rounded-full bg-[#13b877] shadow-[0_0_0_4px_rgba(19,184,119,0.25)]" />
            Estamos para ayudarte
          </span>
          <h1 className="mt-5 mb-4 text-[34px] font-bold tracking-[-0.03em] text-white md:text-[44px]">
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
      <section className={`${container} relative z-[5] -mt-21 pb-22.5`}>
        <div className="mb-8.5 grid gap-5.5 md:grid-cols-3">
          {channels.map(({ Icon, title, desc, link }) => (
            <div
              key={title}
              className="group rounded-[18px] border border-[#e8e6f4] bg-white px-6.5 py-7 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_4px_14px_rgba(92,80,200,0.05)] transition hover:-translate-y-[3px] hover:border-[#dcd9ee] hover:shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)]"
            >
              <div className="mb-4.5 grid size-12 place-items-center rounded-[13px] bg-[#efedfc] text-[#5446dc]">
                <Icon className="size-5.75" />
              </div>
              <h3 className="mb-1.75 text-[17px] font-bold text-[#15162c]">
                {title}
              </h3>
              <p className="mb-3.5 text-[13.5px] leading-snug text-[#7e7f99]">
                {desc}
              </p>
              <a
                href={link.href}
                className="inline-flex items-center gap-1.75 text-[14.5px] font-semibold text-[#5446dc] transition hover:text-primary"
              >
                {link.label}
                <ArrowIcon className="size-4 transition group-hover:translate-x-0.75" />
              </a>
            </div>
          ))}
        </div>

        <div className="grid items-start gap-6.5 md:grid-cols-2">
          <ContactForm />

          {/* info side */}
          <div className="rounded-[20px] border border-[#e8e6f4] bg-white px-8 py-8.5 shadow-[0_1px_2px_rgba(20,22,44,0.04),0_10px_30px_rgba(92,80,200,0.06)]">
            <h3 className="text-[19px] font-bold text-[#15162c]">
              Otras formas de encontrarnos
            </h3>
            <p className="mt-1.5 mb-6 text-[14px] leading-snug text-[#7e7f99]">
              Datos directos del equipo de VeriTrust.
            </p>

            <div className="flex items-start gap-3.5 pt-1 pb-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-[11px] bg-[#f4f2fd] text-[#5446dc]">
                <MailIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-[#15162c]">
                  Email general
                </h4>
                <a
                  href={`mailto:${CONFIG.email}`}
                  className="text-[13.5px] font-semibold text-[#5446dc] hover:underline"
                >
                  {CONFIG.email}
                </a>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-[#e8e6f4] py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-[11px] bg-[#f4f2fd] text-[#5446dc]">
                <PhoneIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-[#15162c]">
                  Teléfono
                </h4>
                <p className="text-[13.5px] text-[#7e7f99]">{CONFIG.phone}</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-[#e8e6f4] py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-[11px] bg-[#f4f2fd] text-[#5446dc]">
                <PinIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-[#15162c]">
                  Ubicación
                </h4>
                <p className="text-[13.5px] text-[#7e7f99]">Madrid, España.</p>
              </div>
            </div>

            <div className="flex items-start gap-3.5 border-t border-[#e8e6f4] py-4">
              <span className="grid size-10 shrink-0 place-items-center rounded-[11px] bg-[#f4f2fd] text-[#5446dc]">
                <ClockIcon className="size-4.75" />
              </span>
              <div>
                <h4 className="mb-0.5 text-[14.5px] font-bold text-[#15162c]">
                  Tiempo de respuesta
                </h4>
                <p className="text-[13.5px] text-[#7e7f99]">
                  Menos de 24&nbsp;h laborables en todos los canales
                </p>
              </div>
            </div>

            {/* schematic map */}
            <div
              role="img"
              aria-label="Mapa esquemático de la ubicación de la oficina en Madrid"
              className="relative mt-5.5 h-42.5 overflow-hidden rounded-2xl border border-[#e8e6f4] bg-[linear-gradient(0deg,rgba(67,45,215,0.06),rgba(67,45,215,0.06)),repeating-linear-gradient(0deg,#eee9fa_0_1px,transparent_1px_34px),repeating-linear-gradient(90deg,#eee9fa_0_1px,transparent_1px_34px),#f6f4fd]"
            >
              <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-full text-primary">
                <svg
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="size-8.5 drop-shadow-[0_6px_10px_rgba(67,45,215,0.35)]"
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
