import type { Metadata } from 'next';
import Link from 'next/link';
import { FREE_FEATURES, PRO_FEATURES, PRO_PRICE } from '@/config/plans';
import { SITE_CONFIG } from '@/config/site';

export const metadata: Metadata = {
  title: 'Términos y Condiciones',
  alternates: { canonical: '/terminos-y-condiciones' },
  description:
    'Revisa los términos y condiciones de uso de la plataforma VeriTrust y de contratación del plan Pro.',
};

const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'AboutPage',
  '@id': `${SITE_CONFIG.domain}/terminos-y-condiciones/#webpage`,
  url: `${SITE_CONFIG.domain}/terminos-y-condiciones`,
  name: 'Términos y Condiciones | VeriTrust',
  description:
    'Revisa los términos y condiciones de uso de la plataforma VeriTrust y de contratación del plan Pro.',
  isPartOf: {
    '@id': `${SITE_CONFIG.domain}/#website`,
  },
  publisher: {
    '@id': `${SITE_CONFIG.domain}/#organization`,
  },
};

const linkClass = 'text-primary transition duration-300 hover:text-primary/90';
const listClass = 'mt-3 list-disc space-y-2 pl-6 text-base leading-7 text-body';

function EmailLink() {
  return (
    <a href={`mailto:${SITE_CONFIG.email}`} className={linkClass}>
      {SITE_CONFIG.email}
    </a>
  );
}

export default function TerminosYCondicionesPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <section className="animate-fade-in mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
        <h1 className="text-4xl font-extrabold tracking-tight text-ink md:text-5xl">
          Términos y condiciones
        </h1>
        <p className="mt-4 text-base leading-7 text-body md:text-lg">
          Estos términos regulan el uso de VeriTrust y la contratación de su
          plan Pro. El servicio lo presta {SITE_CONFIG.legal.holder}, cuyos
          datos figuran en el{' '}
          <Link href="/aviso-legal" className={linkClass}>
            aviso legal
          </Link>
          . Los aceptas al crear tu cuenta y, para el plan Pro, de nuevo al
          suscribirte.
        </p>
        <p className="mt-2 text-sm text-muted">
          Última actualización: 29 de octubre de 2026
        </p>

        <div className="mt-10 space-y-10">
          <section>
            <h2 className="text-2xl font-bold text-ink">
              1. Objeto y finalidad prevista
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              VeriTrust analiza afirmaciones sobre salud en textos, enlaces y
              documentos y las contrasta con literatura científica y bases de
              datos públicas (PubMed, Europe PMC, openFDA y CIMA de la AEMPS),
              para ayudar a detectar posible desinformación en contenidos
              publicados o por publicar.
            </p>
            <p className="mt-3 text-base leading-7 text-body">
              VeriTrust no es un producto sanitario. No está pensado para el
              diagnóstico, la prevención, el seguimiento ni el tratamiento de
              pacientes concretos, ni para tomar decisiones clínicas, y no
              sustituye el consejo de un profesional sanitario, legal ni de
              ningún otro tipo.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              2. Resultados generados por inteligencia artificial
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Los veredictos, la credibilidad, la explicación y la selección de
              fuentes de cada informe los generan de forma automática modelos de
              inteligencia artificial. Pueden contener errores u omisiones, así
              que debes revisarlos antes de tomar cualquier decisión relevante.
              Si publicas un resultado o parte de él, indica que se ha generado
              con inteligencia artificial o revísalo y asúmelo bajo tu propia
              responsabilidad editorial.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              3. Registro y cuenta
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Necesitas al menos 14 años para crear una cuenta, y ser mayor de
              edad para contratar el plan Pro. Eres responsable de la veracidad
              de los datos aportados y de mantener la confidencialidad de tus
              credenciales, de tus claves de API y de las conexiones que
              autorices desde asistentes de IA (MCP). Toda actividad realizada
              con ellas se entenderá efectuada por ti y consume el plan de tu
              cuenta.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">4. Planes</h2>
            <p className="mt-3 text-base leading-7 text-body">
              El plan Gratis incluye:
            </p>
            <ul className={listClass}>
              {FREE_FEATURES.map(feature => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
            <p className="mt-3 text-base leading-7 text-body">
              El plan Pro incluye:
            </p>
            <ul className={listClass}>
              {PRO_FEATURES.map(feature => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
            <p className="mt-3 text-base leading-7 text-body">
              Un análisis cuenta para el límite mensual cuando termina con
              éxito; los que fallan no cuentan, ni tampoco reintentarlos. Cada
              reanálisis que termina con éxito cuenta como uno más, igual que
              cada búsqueda de evidencia correcta desde un asistente de IA. El
              límite se renueva el día 1 de cada mes a las 00:00, hora
              peninsular española, y los análisis que no uses no se acumulan.
            </p>
            <p className="mt-3 text-base leading-7 text-body">
              Con el plan Gratis, los análisis de más de 30 días dejan de verse
              en tu historial, pero no se borran: vuelven a estar disponibles si
              te pasas a Pro, y siempre puedes descargarlos todos con «Exportar
              todos mis datos» en tu cuenta. Los planes Equipo e Institución
              están en acceso anticipado y se contratan por separado, con sus
              propias condiciones.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">5. Precio y pago</h2>
            <p className="mt-3 text-base leading-7 text-body">
              El plan Pro cuesta {PRO_PRICE.month} al mes o {PRO_PRICE.year} al
              año, IVA incluido. El pago se hace con tarjeta a través de Stripe,
              nuestro proveedor de pagos; nunca vemos ni guardamos los datos de
              tu tarjeta. Al suscribirte indicas tu dirección de facturación y,
              si contratas como empresa o profesional, puedes añadir tu NIF.
              Cada cobro genera una factura, en la que se desglosa el IVA, y que
              puedes descargar desde «Gestionar suscripción» en tu cuenta.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              6. Renovación, cambios y cancelación
            </h2>
            <ul className={listClass}>
              <li>
                La suscripción se renueva automáticamente al final de cada
                periodo, mensual o anual, y se cobra a la tarjeta que tengas
                registrada.
              </li>
              <li>
                Puedes cancelarla cuando quieras desde «Gestionar suscripción»
                en tu cuenta. La cancelación tiene efecto al final del periodo
                ya pagado: hasta entonces mantienes el plan Pro y después pasas
                al plan Gratis, sin perder tus análisis.
              </li>
              <li>
                Desde el mismo sitio puedes cambiar entre el pago mensual y el
                anual, actualizar tu tarjeta y tus datos de facturación. El
                importe del cambio de periodo se prorratea, y lo verás antes de
                confirmarlo.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">7. Impago</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Si el cobro de una renovación falla, te avisaremos por correo y lo
              reintentaremos durante unas dos semanas, en las que conservas el
              plan Pro. Si todos los reintentos fallan, o si un pago que exige
              tu confirmación (por ejemplo, con 3D Secure) no se confirma en 15
              días, la suscripción se cancela y tu cuenta pasa al plan Gratis.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              8. Derecho de desistimiento
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Si contratas como consumidor, puedes desistir de la suscripción en
              los 14 días naturales siguientes a su contratación, sin indicar el
              motivo. Al suscribirte nos pides expresamente que el servicio
              empiece de inmediato, por lo que, si desistes, te devolveremos lo
              que pagaste menos la parte proporcional al servicio ya prestado
              hasta que nos lo comuniques (artículo 108.3 del Texto Refundido de
              la Ley General para la Defensa de los Consumidores y Usuarios).
              Este derecho cubre la contratación inicial, no las renovaciones
              posteriores, y no se aplica a quien contrata para su actividad
              empresarial o profesional.
            </p>
            <p className="mt-3 text-base leading-7 text-body">
              Para ejercerlo, envíanos una declaración clara a <EmailLink />,
              por ejemplo con este modelo. Te devolveremos el importe en un
              plazo máximo de 14 días desde que la recibamos, por el mismo medio
              de pago que usaste.
            </p>
            <div className="mt-3 rounded-lg border border-line bg-surface-subtle p-4 text-sm leading-6 text-body">
              <p>
                A la atención de {SITE_CONFIG.legal.holder},{' '}
                {SITE_CONFIG.legal.address}, {SITE_CONFIG.email}:
              </p>
              <p className="mt-2">
                Por la presente le comunico que desisto de mi contrato de
                prestación del servicio VeriTrust Pro (mensual / anual),
                contratado el [fecha], con la cuenta [correo electrónico].
              </p>
              <p className="mt-2">
                Nombre del consumidor: [nombre]. Domicilio del consumidor:
                [domicilio]. Firma (solo si el formulario se presenta en papel).
                Fecha: [fecha].
              </p>
            </div>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">9. Reembolsos</h2>
            <p className="mt-3 text-base leading-7 text-body">
              Fuera del desistimiento, no se reembolsan los periodos ya
              iniciados, tampoco al cancelar la suscripción, salvo que la ley lo
              exija. Si eliminas tu cuenta, la suscripción se cancela en ese
              momento, sin reembolso del periodo restante; si estás dentro del
              plazo de desistimiento, ejércelo antes de eliminarla.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              10. Cambios de precio
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Si cambiamos el precio del plan Pro, te avisaremos por correo al
              menos 30 días antes de la renovación a la que se aplique. Si no
              estás de acuerdo, puedes cancelar la suscripción antes de esa
              fecha y no se te cobrará el nuevo precio.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">11. Uso permitido</h2>
            <p className="mt-3 text-base leading-7 text-body">
              No está permitido:
            </p>
            <ul className={listClass}>
              <li>
                Utilizar la plataforma para actividades ilícitas, para difundir
                contenido ofensivo o para vulnerar derechos de propiedad
                intelectual y privacidad de terceros.
              </li>
              <li>
                Enviar datos personales de terceros ni datos de salud de
                personas identificables (consulta la{' '}
                <Link href="/politica-de-privacidad" className={linkClass}>
                  política de privacidad
                </Link>
                ).
              </li>
              <li>
                Crear varias cuentas o usar cualquier otro medio para eludir los
                límites de tu plan, o revender el servicio sin nuestro acuerdo
                por escrito.
              </li>
              <li>
                Intentar acceder a datos de otros usuarios, sobrecargar el
                servicio o probar su seguridad sin nuestra autorización.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">12. Tu contenido</h2>
            <p className="mt-3 text-base leading-7 text-body">
              El contenido que envías sigue siendo tuyo. Nos autorizas a
              tratarlo solo para prestarte el servicio, y no lo usamos para
              entrenar modelos de inteligencia artificial. Debes tener derecho a
              usar lo que envías. Un enlace público de un informe lo puede ver
              cualquiera que lo tenga, hasta que lo revoques; si dejas de tener
              el plan Pro, tus enlaces dejan de funcionar y vuelven a hacerlo si
              lo recuperas.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              13. Disponibilidad y soporte
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Intentamos que el servicio esté siempre disponible, pero no
              garantizamos un nivel de servicio concreto. Podemos actualizar,
              modificar o suspender funcionalidades por motivos técnicos, de
              seguridad o de mejora, intentando minimizar el impacto. El soporte
              se presta por correo en <EmailLink />, en la medida de lo posible.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">14. Responsabilidad</h2>
            <p className="mt-3 text-base leading-7 text-body">
              No garantizamos que los resultados sean exactos en todos los
              casos, y el usuario asume la responsabilidad de validar la
              información antes de tomar decisiones relevantes basadas en ella.
              Si contratas para tu actividad empresarial o profesional, nuestra
              responsabilidad se limita a lo que hayas pagado en los 12 meses
              anteriores al hecho que la cause. Nada de lo anterior limita la
              responsabilidad por dolo o culpa grave ni los derechos que la ley
              reconoce a los consumidores.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              15. Baja y suspensión
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Puedes eliminar tu cuenta en cualquier momento desde la gestión de
              cuenta del menú de tu perfil; al hacerlo se borran tus análisis
              como explica la{' '}
              <Link href="/politica-de-privacidad" className={linkClass}>
                política de privacidad
              </Link>
              . Podemos suspender o cerrar una cuenta que incumpla gravemente
              estos términos, avisándote antes cuando sea posible.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              16. Vigencia y modificaciones
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Estos términos pueden actualizarse periódicamente. Las nuevas
              versiones se publicarán en esta página y entrarán en vigor desde
              su publicación; si un cambio te afecta de forma importante, te
              avisaremos por correo antes de que se aplique.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-bold text-ink">
              17. Ley aplicable y reclamaciones
            </h2>
            <p className="mt-3 text-base leading-7 text-body">
              Estos términos se rigen por la legislación española. Si tienes una
              queja, escríbenos primero a <EmailLink /> y te responderemos lo
              antes posible. No estamos adheridos a ningún sistema de resolución
              alternativa de litigios de consumo. Si eres consumidor, podrás
              acudir a los juzgados y tribunales de tu domicilio.
            </p>
          </section>
        </div>
      </section>
    </>
  );
}
