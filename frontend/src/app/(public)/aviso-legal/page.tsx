import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE_CONFIG } from '@/config/site';
import { EmailLink, legalLinkClass } from '../_components/legal';

export const metadata: Metadata = {
  title: 'Aviso Legal',
  alternates: { canonical: '/aviso-legal' },
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
        <p className="mt-2 text-sm text-muted">
          Última actualización: 29 de octubre de 2026
        </p>

        <div className="mt-10 space-y-10">
          <section>
            <h2 className="text-2xl font-bold text-ink">
              1. Datos identificativos
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              En cumplimiento del artículo 10 de la Ley 34/2002, de servicios de
              la sociedad de la información y de comercio electrónico (LSSI),
              estos son los datos del titular de este sitio web y del servicio
              VeriTrust:
            </p>
            <ul className="mt-3 list-disc space-y-2 pl-6 text-base leading-7 text-body">
              <li>Titular: {SITE_CONFIG.legal.holder}</li>
              <li>NIF: {SITE_CONFIG.legal.nif}</li>
              <li>Domicilio: {SITE_CONFIG.legal.address}</li>
              <li>
                Correo electrónico: <EmailLink />
              </li>
              <li>Teléfono: {SITE_CONFIG.phone}</li>
              <li>
                Actividad: plataforma de verificación de información médica
                mediante inteligencia artificial, bajo el nombre comercial
                VeriTrust.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">2. Uso del sitio</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Te comprometes a hacer un uso adecuado del contenido y de los
              servicios, de conformidad con la ley, la buena fe y el orden
              público. Queda prohibido utilizar la web con fines ilícitos,
              fraudulentos o que perjudiquen derechos de terceros. El uso de la
              plataforma y la contratación del plan Pro se rigen además por los{' '}
              <Link href="/terminos-y-condiciones" className={legalLinkClass}>
                términos y condiciones
              </Link>
              , y el tratamiento de tus datos por la{' '}
              <Link href="/politica-de-privacidad" className={legalLinkClass}>
                política de privacidad
              </Link>
              .
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              3. Propiedad intelectual e industrial
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Los contenidos propios del sitio, incluidos textos, diseños,
              logotipos, código y elementos gráficos, son titularidad de{' '}
              {SITE_CONFIG.legal.holder} o de terceros que han autorizado su
              uso. Queda prohibida su reproducción total o parcial sin
              autorización previa y expresa. Los resúmenes, títulos y enlaces de
              publicaciones científicas que se citan en los informes pertenecen
              a sus autores y editores, y se muestran solo como referencia de su
              fuente.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              4. Limitación de responsabilidad
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              No se garantiza la ausencia de errores en los contenidos ni la
              disponibilidad ininterrumpida del servicio. La información
              proporcionada tiene carácter informativo y no sustituye el
              criterio médico profesional.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              5. Enlaces a otros sitios
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Los informes enlazan a bases de datos y publicaciones de terceros,
              como PubMed, Europe PMC, openFDA o CIMA de la AEMPS. No
              controlamos esos sitios ni respondemos de sus contenidos, que se
              rigen por sus propias condiciones.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              6. Legislación aplicable
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Este aviso legal se rige por la legislación española. Si eres
              consumidor, podrás acudir a los juzgados y tribunales de tu
              domicilio; en los demás casos, las partes se someten a los
              juzgados y tribunales que correspondan conforme a derecho.
            </p>
          </section>
        </div>
      </section>
    </>
  );
}
