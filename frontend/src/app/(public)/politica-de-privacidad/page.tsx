import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Política de privacidad | VeriTrust',
  description:
    'Conoce como VeriTrust recopila, utiliza y protege los datos personales de sus usuarios.',
};

export default function PoliticaDePrivacidadPage() {
  return (
    <section className="animate-fade-in mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
      <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 md:text-5xl">
        Política de privacidad
      </h1>
      <p className="mt-4 text-base leading-7 text-gray-600 md:text-lg">
        En VeriTrust nos comprometemos a proteger tus datos personales y a
        tratarlos con transparencia, seguridad y conforme a la normativa
        aplicable.
      </p>

      <div className="mt-10 space-y-10">
        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            1. Datos que recopilamos
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Podemos recopilar datos identificativos y de contacto, datos de uso
            de la plataforma, información técnica del dispositivo y contenido
            enviado para su análisis, siempre en el marco del servicio.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            2. Finalidad del tratamiento
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Utilizamos los datos para prestar el servicio, mejorar la calidad de
            la plataforma, garantizar la seguridad, prevenir abusos y cumplir
            obligaciones legales.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">3. Base jurídica</h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Tratamos tus datos con base en la ejecución contractual del
            servicio, en el consentimiento cuando sea necesario y en el interés
            legítimo para proteger y optimizar la plataforma.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            4. Conservación de datos
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Conservamos los datos durante el tiempo necesario para cumplir la
            finalidad para la que fueron recabados y durante los plazos exigidos
            por la normativa aplicable.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            5. Derechos del usuario
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Puedes ejercer tus derechos de acceso, rectificación, supresión,
            oposición, limitación y portabilidad de datos mediante los canales
            de contacto habilitados por VeriTrust.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-bold text-gray-900">
            6. Medidas de seguridad
          </h2>
          <p className="mt-3 text-base leading-7 text-gray-600">
            Aplicamos medidas técnicas y organizativas para proteger la
            confidencialidad, integridad y disponibilidad de la información,
            incluyendo controles de acceso y cifrado cuando corresponda.
          </p>
        </section>
      </div>
    </section>
  );
}
