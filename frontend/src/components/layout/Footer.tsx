import Image from 'next/image';
import Link from 'next/link';

const columns = [
  {
    title: 'Producto',
    links: [
      { label: 'Cómo funciona', href: '/#como-funciona' },
      { label: 'Características', href: '/#features' },
      { label: 'Precios', href: '/#precios' },
      { label: 'Analizar', href: '/app/analisis' },
    ],
  },
  {
    title: 'Casos de uso',
    links: [
      { label: 'Periodistas', href: '/#casos' },
      { label: 'Salud pública', href: '/#casos' },
      { label: 'Instituciones', href: '/#casos' },
      { label: 'FAQ', href: '/#faq' },
    ],
  },
  {
    title: 'Empresa',
    links: [
      { label: 'Contacto', href: '/contacto' },
      { label: 'Solicitar demo', href: '/demo' },
      { label: 'Privacidad', href: '/politica-de-privacidad' },
      { label: 'Términos', href: '/terminos-y-condiciones' },
    ],
  },
];

const bottomLinks = [
  { label: 'Aviso legal', href: '/aviso-legal' },
  { label: 'Términos y condiciones', href: '/terminos-y-condiciones' },
  { label: 'Política de privacidad', href: '/politica-de-privacidad' },
];

export default function Footer() {
  return (
    <footer className="bg-[#16172e] pt-16 pb-[30px] text-white">
      <div className="mx-auto w-full max-w-[1180px] px-5 md:px-8">
        <div className="mb-12 grid gap-10 md:grid-cols-2 lg:grid-cols-[1.6fr_1fr_1fr_1fr]">
          <div>
            <Link href="/" className="flex items-center gap-2">
              <Image
                src="/images/logo.webp"
                alt="Logo de VeriTrust"
                width={20}
                height={20}
              />
              <span className="text-lg font-semibold text-white">
                VeriTrust
              </span>
            </Link>
            <p className="mt-4 max-w-[280px] text-sm leading-relaxed text-white/60">
              El detector de noticias falsas de salud impulsado por un sistema
              multiagente de IA. Verifica con rigor, cita tus fuentes.
            </p>
          </div>

          {columns.map(column => (
            <div key={column.title}>
              <h5 className="mb-4 text-[13px] font-bold tracking-[0.06em] text-white uppercase">
                {column.title}
              </h5>
              {column.links.map(link =>
                link.href.startsWith('mailto:') ? (
                  <a
                    key={link.label}
                    href={link.href}
                    className="mb-[11px] block text-sm text-white/60 transition duration-150 hover:text-white"
                  >
                    {link.label}
                  </a>
                ) : (
                  <Link
                    key={link.label}
                    href={link.href}
                    className="mb-[11px] block text-sm text-white/60 transition duration-150 hover:text-white"
                  >
                    {link.label}
                  </Link>
                )
              )}
            </div>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3.5 border-t border-white/10 pt-6">
          <p className="text-[13px] text-white/50">
            © 2026 VeriTrust. Información orientativa; no sustituye el consejo
            médico profesional.
          </p>
          <div className="flex flex-wrap gap-x-[22px] gap-y-2">
            {bottomLinks.map(link => (
              <Link
                key={link.label}
                href={link.href}
                className="text-[13px] text-white/50 transition duration-150 hover:text-white"
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
