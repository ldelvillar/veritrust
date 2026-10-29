import type { Metadata } from 'next';
import Link from 'next/link';
import { SITE_CONFIG } from '@/config/site';
import {
  EmailLink,
  legalLinkClass,
  legalListClass,
} from '../_components/legal';

export const metadata: Metadata = {
  title: 'Política de Privacidad',
  alternates: { canonical: '/politica-de-privacidad' },
  description:
    'Conoce como VeriTrust recopila, utiliza y protege los datos personales de sus usuarios.',
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebPage',
  '@id': `${SITE_CONFIG.domain}/politica-de-privacidad/#webpage`,
  url: `${SITE_CONFIG.domain}/politica-de-privacidad`,
  name: 'Política de Privacidad | VeriTrust',
  description:
    'Conoce como VeriTrust recopila, utiliza y protege los datos personales de sus usuarios.',
  isPartOf: {
    '@id': `${SITE_CONFIG.domain}/#website`,
  },
  mainEntity: {
    '@type': 'WebPageElement',
    '@id': `${SITE_CONFIG.domain}/politica-de-privacidad/#content`,
  },
  publisher: {
    '@id': `${SITE_CONFIG.domain}/#organization`,
  },
};

export default function PoliticaDePrivacidadPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="animate-fade-in mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
        <h1 className="text-4xl font-extrabold tracking-tight text-ink md:text-5xl">
          Política de privacidad
        </h1>
        <p className="mt-4 text-base leading-7 text-body md:text-lg">
          En VeriTrust nos comprometemos a proteger tus datos personales y a
          tratarlos con transparencia, seguridad y conforme al Reglamento
          General de Protección de Datos (RGPD) y a la Ley Orgánica 3/2018
          (LOPDGDD).
        </p>
        <p className="mt-2 text-sm text-muted">
          Última actualización: 29 de octubre de 2026
        </p>

        <div className="mt-10 space-y-10">
          <section>
            <h2 className="text-2xl font-bold text-ink">
              1. Responsable del tratamiento
            </h2>
            <ul className={legalListClass}>
              <li>Responsable: {SITE_CONFIG.legal.holder}</li>
              <li>NIF: {SITE_CONFIG.legal.nif}</li>
              <li>Domicilio: {SITE_CONFIG.legal.address}</li>
              <li>
                Contacto para cualquier asunto de privacidad: <EmailLink />
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              2. Datos que tratamos
            </h2>
            <ul className={legalListClass}>
              <li>
                Datos de cuenta: tu nombre, tu correo electrónico, tu
                identificador de usuario y los datos de inicio de sesión, que
                gestiona nuestro proveedor de autenticación, además de tus
                claves de API y las conexiones que autorices desde asistentes de
                IA.
              </li>
              <li>
                Contenido que envías para analizar: textos, enlaces y el texto
                de las páginas enlazadas, y archivos (guardamos el original para
                que puedas verlo junto al informe), con los resultados de cada
                análisis y los enlaces públicos que crees.
              </li>
              <li>
                Valoraciones: si nos dices si un veredicto es correcto,
                guardamos tu valoración y tu comentario.
              </li>
              <li>
                Datos de facturación, si contratas el plan Pro: nombre,
                dirección de facturación, NIF si lo indicas y el estado de tu
                suscripción. Los datos de tu tarjeta los trata solo Stripe;
                nunca llegan a nuestros servidores.
              </li>
              <li>
                Registro de uso: la fecha y el tipo de cada análisis que cuenta
                para el límite mensual de tu plan.
              </li>
              <li>
                Formularios de contacto y de demo: tu nombre, correo,
                organización, cargo y mensaje.
              </li>
              <li>
                Datos técnicos: tu dirección IP y los registros técnicos del
                servidor, que usamos para limitar abusos y resolver errores.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">3. Datos de salud</h2>
            <p className="mt-3 text-base leading-7 text-body">
              VeriTrust analiza afirmaciones sobre salud en contenidos, no datos
              de pacientes. No incluyas en lo que envías datos de salud tuyos ni
              datos personales de otras personas identificables. Si aun así los
              incluyes, los trataremos solo para hacer el análisis que pides,
              sobre la base de tu consentimiento explícito al enviarlos
              (artículo 9.2.a del RGPD), y puedes borrarlos cuando quieras
              borrando ese análisis.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              4. Finalidades y base jurídica
            </h2>
            <ul className={legalListClass}>
              <li>
                Prestarte el servicio: tu cuenta, los análisis, tu historial,
                los enlaces públicos y el correo que te avisa cuando termina un
                análisis. Base: la ejecución del contrato (artículo 6.1.b del
                RGPD).
              </li>
              <li>
                Cobrar el plan Pro, emitir facturas y contar tu uso mensual.
                Base: la ejecución del contrato y el cumplimiento de nuestras
                obligaciones fiscales (artículo 6.1.c).
              </li>
              <li>
                Proteger la plataforma, prevenir abusos y resolver errores.
                Base: nuestro interés legítimo en mantener un servicio seguro
                (artículo 6.1.f).
              </li>
              <li>
                Mejorar la calidad de los análisis con tus valoraciones. Base:
                nuestro interés legítimo; puedes oponerte escribiéndonos.
              </li>
              <li>
                Responder a tus solicitudes de contacto o de demo. Base: tu
                consentimiento y, si lo pides, la aplicación de medidas
                precontractuales.
              </li>
            </ul>
            <p className="mt-3 text-base leading-7 text-body">
              No usamos tus datos para enviarte publicidad, no los vendemos, y
              ni nosotros ni nuestros proveedores usamos tu contenido para
              entrenar modelos de inteligencia artificial. El análisis es
              automático, pero evalúa el contenido, no a ti, así que no toma
              decisiones con efectos jurídicos sobre tu persona.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              5. Proveedores y destinatarios
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Estos proveedores tratan datos por nuestra cuenta, con un contrato
              de encargo del tratamiento:
            </p>
            <ul className={legalListClass}>
              <li>
                Contabo GmbH (Alemania): alojamiento del servidor y de la base
                de datos, en la Unión Europea.
              </li>
              <li>
                Mistral AI (Francia): modelos de inteligencia artificial que
                analizan el contenido que envías. Conserva los datos durante un
                periodo limitado, según sus condiciones, para vigilar abusos.
              </li>
              <li>
                Clerk, Inc. (Estados Unidos): registro, inicio de sesión,
                gestión de la cuenta, claves de API y conexiones de asistentes
                de IA.
              </li>
              <li>
                Resend (Estados Unidos): envío de los correos que te avisan de
                un análisis terminado y de los mensajes de los formularios de
                contacto y de demo.
              </li>
              <li>
                Stripe Payments Europe, Ltd. (Irlanda): pagos, suscripciones y
                facturas del plan Pro. Stripe también trata algunos datos como
                responsable independiente, por ejemplo para prevenir el fraude,
                según su propia política de privacidad.
              </li>
            </ul>
            <p className="mt-3 text-base leading-7 text-body">
              Para buscar evidencia, enviamos a bases de datos científicas
              públicas (PubMed y openFDA en Estados Unidos, Europe PMC en el
              Reino Unido y CIMA de la AEMPS en España) términos de búsqueda
              derivados de las afirmaciones del contenido, nunca tus datos de
              cuenta. Cuando analizas un enlace, nuestro servidor descarga esa
              página, que ve nuestra petición y no la tuya. Lo que nos escribes
              por correo y las solicitudes de los formularios de contacto y de
              demo llegan a un buzón de Gmail, cuyos mensajes trata Google
              Ireland Limited como responsable independiente, según sus propias
              condiciones. Solo cederemos datos a autoridades cuando una ley nos
              obligue.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              6. Transferencias internacionales
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Clerk, Resend, Stripe y Google pueden tratar datos en Estados
              Unidos. Esas transferencias se amparan en el Marco de Privacidad
              de Datos UE-EE. UU. cuando el proveedor está adherido o, si no, en
              las cláusulas contractuales tipo de la Comisión Europea. El Reino
              Unido cuenta con una decisión de adecuación de la Comisión.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              7. Conservación de datos
            </h2>
            <ul className={legalListClass}>
              <li>
                Tus análisis, archivos y valoraciones se conservan hasta que los
                borres o elimines tu cuenta. Con el plan Gratis, los de más de
                30 días dejan de verse en tu historial, pero no se borran.
              </li>
              <li>
                Al eliminar tu cuenta borramos tus análisis, archivos,
                valoraciones, tu registro de uso y los datos de tu suscripción,
                y cancelamos la suscripción en Stripe.
              </li>
              <li>
                Las facturas, con los datos de facturación que deben figurar en
                ellas, se conservan el tiempo que obliga la normativa fiscal y
                mercantil (hasta seis años), aunque elimines tu cuenta.
              </li>
              <li>
                Los mensajes de los formularios se conservan el tiempo necesario
                para atender tu solicitud y la relación que surja de ella.
              </li>
              <li>
                Los registros técnicos se sobrescriben automáticamente al rotar,
                y las copias de seguridad se renuevan de forma que lo que borras
                desaparece de ellas en un máximo de 30 días.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              8. Derechos del usuario
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Puedes ejercer tus derechos de acceso, rectificación, supresión,
              oposición, limitación y portabilidad, y retirar tu consentimiento
              en cualquier momento. Muchos los puedes ejercer tú mismo desde{' '}
              <Link href="/app/cuenta" className={legalLinkClass}>
                tu cuenta
              </Link>
              : descargar todos tus análisis con «Exportar todos mis datos»,
              borrar análisis sueltos o toda tu actividad, y eliminar tu cuenta
              desde el menú de tu perfil. Para todo lo demás, escríbenos a{' '}
              <EmailLink /> y te responderemos en el plazo de un mes. Si crees
              que no hemos atendido bien tu solicitud, puedes reclamar ante la
              Agencia Española de Protección de Datos (
              <a
                href="https://www.aepd.es"
                className={legalLinkClass}
                target="_blank"
                rel="noopener noreferrer"
              >
                www.aepd.es
              </a>
              ).
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">9. Cookies</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Solo usamos las cookies técnicas imprescindibles para iniciar y
              mantener tu sesión de forma segura, que gestiona Clerk. No usamos
              cookies de análisis ni de publicidad. La página de pago de Stripe
              usa sus propias cookies para procesar el pago y prevenir el
              fraude.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              10. Medidas de seguridad
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Aplicamos medidas técnicas y organizativas para proteger la
              confidencialidad, integridad y disponibilidad de la información:
              conexiones cifradas, acceso restringido al servidor, copias de
              seguridad cifradas fuera del servidor y aislamiento de los datos
              de cada usuario.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">11. Menores</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Necesitas al menos 14 años para crear una cuenta, y ser mayor de
              edad para contratar el plan Pro.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              12. Cambios en esta política
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Publicaremos en esta página cualquier cambio de esta política y,
              si te afecta de forma importante, te avisaremos por correo antes
              de que se aplique.
            </p>
          </section>
        </div>
      </section>
    </>
  );
}
