import type { Metadata } from 'next';
import { SITE_CONFIG } from '@/config/site';

export const metadata: Metadata = {
  title: 'Aviso Legal',
  description:
    'Consulta el aviso legal de VeriTrust con la información del titular, condiciones de uso y responsabilidades.',
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'AboutPage',
  '@id': `${SITE_CONFIG.domain}/aviso-legal/#webpage`,
  url: `${SITE_CONFIG.domain}/aviso-legal`,
  name: 'Aviso Legal | VeriTrust',
  description:
    'Consulta el aviso legal de VeriTrust con la información del titular, condiciones de uso y responsabilidades.',
  isPartOf: {
    '@id': `${SITE_CONFIG.domain}/#website`,
  },
  publisher: {
    '@id': `${SITE_CONFIG.domain}/#organization`,
  },
};

export default function AvisoLegalPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="animate-fade-in mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
        <h1 className="text-4xl font-extrabold tracking-tight text-ink md:text-5xl">
          Aviso legal
        </h1>
        <p className="mt-4 text-base leading-7 text-body md:text-lg">
          Este aviso legal regula el acceso y uso del sitio web de VeriTrust. Al
          navegar por esta web, asumes la condición de usuario y aceptas las
          disposiciones aquí descritas.
        </p>

        <div className="mt-10 space-y-10">
          <section>
            <h2 className="text-2xl font-bold text-ink">
              1. Datos identificativos
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Titular: VeriTrust. Finalidad del sitio: ofrecer una plataforma de
              análisis y verificación de información médica mediante
              inteligencia artificial. Contacto: puedes escribir al creador del
              proyecto a través de su correo electrónico:{' '}
              <a
                href={`mailto:${SITE_CONFIG.email}`}
                className="text-primary transition duration-300 hover:text-primary/90"
              >
                {SITE_CONFIG.email}
              </a>
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">2. Uso del sitio</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Te comprometes a hacer un uso adecuado del contenido y de los
              servicios, de conformidad con la ley, la buena fe y el orden
              público. Queda prohibido utilizar la web con fines ilícitos,
              fraudulentos o que perjudiquen derechos de terceros.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              3. Propiedad intelectual e industrial
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Todos los contenidos del sitio, incluyendo textos, diseños,
              logotipos, código y elementos gráficos, son titularidad de
              VeriTrust o de terceros autorizados. Queda prohibida su
              reproducción total o parcial sin autorización previa y expresa.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              4. Limitación de responsabilidad
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              VeriTrust no garantiza la ausencia de errores en los contenidos ni
              la disponibilidad ininterrumpida del servicio. La información
              proporcionada tiene carácter informativo y no sustituye el
              criterio médico profesional.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              5. Legislación aplicable
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Este aviso legal se rige por la normativa vigente aplicable. Para
              la resolución de conflictos, las partes se someten a los juzgados
              y tribunales competentes conforme a derecho.
            </p>
          </section>
        </div>
      </section>
    </>
  );
}
